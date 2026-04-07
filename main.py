import customtkinter as ctk
import yt_dlp
import threading
import os
from tkinter import filedialog
import imageio_ffmpeg
import concurrent.futures

# --- Window Setup ---
ctk.set_appearance_mode("Dark")
app = ctk.CTk()
app.geometry("1000x700")
app.title("ElmarakbyTube Downloader")

# Global variables to manage video data and fetching state
video_rows = []
is_fetching_sizes = False 
consecutive_errors = 0 
error_lock = threading.Lock() # To safely update errors in multithreading

# --- Custom Logger to hide YouTube errors in the Terminal ---
class SilentLogger:
    def debug(self, msg): pass
    def warning(self, msg): pass
    def error(self, msg): pass

# ==================== Top Section ====================
top_frame = ctk.CTkFrame(app, fg_color="transparent")
top_frame.pack(fill="x", padx=20, pady=20)

# Save Path Input
save_path_frame = ctk.CTkFrame(top_frame, fg_color="transparent")
save_path_frame.pack(side="left", fill="x", expand=True, padx=(0, 10))
ctk.CTkLabel(save_path_frame, text="Save Path:", font=("Arial", 12, "bold")).pack(anchor="w")

path_input_layout = ctk.CTkFrame(save_path_frame, fg_color="transparent")
path_input_layout.pack(fill="x")
path_entry = ctk.CTkEntry(path_input_layout, placeholder_text="/Downloads/Playlists...")
path_entry.pack(side="left", fill="x", expand=True, padx=(0, 5))

def browse_save_path():
    """Open Windows folder selection window"""
    folder_path = filedialog.askdirectory(title="Select Save Folder")
    if folder_path:
        path_entry.delete(0, 'end')
        path_entry.insert(0, folder_path)

ctk.CTkButton(path_input_layout, text="Browse", width=80, fg_color="#840284", hover_color="#6b016b", command=browse_save_path).pack(side="left")

# URL Input
url_frame = ctk.CTkFrame(top_frame, fg_color="transparent")
url_frame.pack(side="left", fill="x", expand=True)
ctk.CTkLabel(url_frame, text="Video or Playlist URL:", font=("Arial", 12, "bold")).pack(anchor="w")

url_input_layout = ctk.CTkFrame(url_frame, fg_color="transparent")
url_input_layout.pack(fill="x")
url_entry = ctk.CTkEntry(url_input_layout, placeholder_text="Paste your YouTube link here...")
url_entry.pack(side="left", fill="x", expand=True, padx=(0, 5))

def handle_hardware_shortcuts(event):
    """Enable copy and paste shortcuts for non-English keyboards"""
    if event.state & 4 or event.state & 12:
        if event.keycode == 86: # V key
            try: event.widget.event_generate("<<Paste>>")
            except: pass
            return "break"
        elif event.keycode == 67: # C key
            try: event.widget.event_generate("<<Copy>>")
            except: pass
            return "break"
        elif event.keycode == 65: # A key
            try:
                event.widget.select_range(0, 'end')
                event.widget.icursor('end')
            except: pass
            return "break"

url_entry.bind("<KeyPress>", handle_hardware_shortcuts)
path_entry.bind("<KeyPress>", handle_hardware_shortcuts)

# ==================== Toolbar Section ====================
toolbar_frame = ctk.CTkFrame(app, fg_color="transparent")
toolbar_frame.pack(fill="x", padx=20, pady=(0, 10))

# Left Buttons
ctk.CTkButton(toolbar_frame, text="Select All", width=90, fg_color="#333", hover_color="#444", command=lambda: toggle_all(True)).pack(side="left", padx=(0, 5))
ctk.CTkButton(toolbar_frame, text="Deselect All", width=90, fg_color="#333", hover_color="#444", command=lambda: toggle_all(False)).pack(side="left", padx=(0, 5))
ctk.CTkButton(toolbar_frame, text="Remove Selected", width=110, fg_color="#8b0000", hover_color="#660000", command=lambda: remove_selected()).pack(side="left")

# Dashboard (Time and Size)
dashboard_frame = ctk.CTkFrame(toolbar_frame, fg_color="transparent")
dashboard_frame.pack(side="left", padx=20)

ctk.CTkLabel(dashboard_frame, text="Total Time:", font=("Arial", 12, "bold")).pack(side="left", padx=(0, 5))
total_time_label = ctk.CTkLabel(dashboard_frame, text="0s", font=("Arial", 12, "bold"), text_color="#FF6600", width=80, anchor="w")
total_time_label.pack(side="left", padx=(0, 15))

ctk.CTkLabel(dashboard_frame, text="Total Size:", font=("Arial", 12, "bold")).pack(side="left", padx=(0, 5))
total_size_label = ctk.CTkLabel(dashboard_frame, text="0.0 MB", font=("Arial", 12, "bold"), text_color="#FF6600", width=80, anchor="w")
total_size_label.pack(side="left")

# Quality & Fetch Actions
quality_layout = ctk.CTkFrame(toolbar_frame, fg_color="transparent")
quality_layout.pack(side="right")

def on_quality_change(choice):
    """Clear old sizes if user changes the quality"""
    for row in video_rows:
        row['bytes_size'] = -1 
        safe_ui_update(row['size_label'], text="N/A", text_color="white")
    update_dynamic_totals()

def on_fetch_sizes_click():
    """Start background process to fetch sizes"""
    threading.Thread(target=fetch_all_sizes_worker, daemon=True).start()

def on_stop_fetch_click():
    """Manually stop the fetching process"""
    global is_fetching_sizes
    is_fetching_sizes = False
    update_global_status("Stopping fetch... please wait.", "orange")

# Container for swapping Fetch and Stop buttons
fetch_action_frame = ctk.CTkFrame(quality_layout, fg_color="transparent")
fetch_action_frame.pack(side="left", padx=(0, 10))

fetch_btn = ctk.CTkButton(fetch_action_frame, text="Fetch Sizes", width=90, fg_color="#840284", hover_color="#6b016b", command=on_fetch_sizes_click)
fetch_btn.pack(side="left")

stop_fetch_btn = ctk.CTkButton(fetch_action_frame, text="Stop Fetch", width=90, fg_color="#ff4444", hover_color="#cc0000", command=on_stop_fetch_click)
# Note: stop_fetch_btn is not shown on start

ctk.CTkLabel(quality_layout, text="Quality:").pack(side="left", padx=(0, 5))
quality_combo = ctk.CTkComboBox(quality_layout, values=["Waiting for link..."], width=130, command=on_quality_change)
quality_combo.set("Select Quality")
quality_combo.pack(side="left")

# ==================== Table Header ====================
header_frame = ctk.CTkFrame(app, fg_color="#1e1e1e", height=40, corner_radius=5)
header_frame.pack(fill="x", padx=20, pady=(0, 5))

ctk.CTkLabel(header_frame, text="", width=30).pack(side="left", padx=5)
ctk.CTkLabel(header_frame, text="#", width=30, font=("Arial", 12, "bold")).pack(side="left", padx=(5, 0))
ctk.CTkLabel(header_frame, text="Video Title", width=250, anchor="w", font=("Arial", 12, "bold")).pack(side="left")
ctk.CTkLabel(header_frame, text="Duration", width=70, font=("Arial", 12, "bold")).pack(side="left")
ctk.CTkLabel(header_frame, text="Size", width=80, font=("Arial", 12, "bold")).pack(side="left")
ctk.CTkLabel(header_frame, text="Status", width=100, font=("Arial", 12, "bold")).pack(side="left")
ctk.CTkLabel(header_frame, text="Progress", width=120, font=("Arial", 12, "bold")).pack(side="left", padx=(10, 5))
ctk.CTkLabel(header_frame, text="%", width=40, font=("Arial", 12, "bold")).pack(side="left")

# ==================== List Area ====================
list_frame = ctk.CTkScrollableFrame(app, fg_color="#2b2b2b")
list_frame.pack(fill="both", expand=True, padx=20, pady=(0, 10))

# ==================== Status Bar ====================
status_bar = ctk.CTkFrame(app, height=30, fg_color="#1e1e1e", corner_radius=0)
status_bar.pack(fill="x", side="bottom")

# Main status text (Green or White)
global_status_label = ctk.CTkLabel(status_bar, text="Status: Ready", font=("Arial", 12))
global_status_label.pack(side="left", padx=(20, 5))

# Secondary warning text (Red)
global_warning_label = ctk.CTkLabel(status_bar, text="", font=("Arial", 12, "bold"), text_color="#ff4444")
global_warning_label.pack(side="left")

# ==================== Bottom Section ====================
bottom_frame = ctk.CTkFrame(app, fg_color="transparent")
bottom_frame.pack(pady=10, side="bottom")

def on_download_click():
    threading.Thread(target=download_worker, daemon=True).start()

ctk.CTkButton(bottom_frame, text="Download Selected", width=150, height=40, font=("Arial", 14, "bold"), fg_color="#840284", hover_color="#6b016b", command=on_download_click).pack(side="left", padx=10)
ctk.CTkButton(bottom_frame, text="Cancel Download", width=150, height=40, font=("Arial", 14, "bold"), fg_color="#FF6600", hover_color="#cc5200").pack(side="left", padx=10)

# ==================== UI Safety Helpers ====================
def safe_ui_update(widget, **kwargs):
    """Safely update UI to prevent errors if user deletes a row"""
    if widget and widget.winfo_exists():
        widget.configure(**kwargs)

def safe_progress_update(widget, value):
    """Safely update progress bar"""
    if widget and widget.winfo_exists():
        widget.set(value)

# ==================== Core Functions ====================
def update_global_status(msg, color="white", warning_msg=""):
    """Update status bar. Allows a secondary red warning message."""
    global_status_label.configure(text=f"Status: {msg}", text_color=color)
    global_warning_label.configure(text=warning_msg)

def update_dynamic_totals():
    """Calculate and update total time and size instantly in memory"""
    total_bytes = 0
    total_seconds = 0
    all_fetched = True 

    for row in video_rows:
        if row["checkbox"].get() == 1: 
            
            # 1. Add size
            if row['bytes_size'] > 0:
                total_bytes += row['bytes_size']
            elif row['bytes_size'] == -1: 
                all_fetched = False

            # 2. Add time
            dur_str = row["duration"]
            if dur_str != "--:--" and dur_str != "N/A":
                parts = dur_str.split(":")
                if len(parts) == 2:
                    total_seconds += int(parts[0]) * 60 + int(parts[1])
                elif len(parts) == 3:
                    total_seconds += int(parts[0]) * 3600 + int(parts[1]) * 60 + int(parts[2])

    # Convert seconds to Hour, Minute, Second
    h, r = divmod(total_seconds, 3600)
    m, s = divmod(r, 60)
    
    if h > 0: time_text = f"{int(h)}h {int(m)}m {int(s)}s"
    elif m > 0: time_text = f"{int(m)}m {int(s)}s"
    else: time_text = f"{int(s)}s"
        
    if total_seconds == 0: time_text = "0s"
    total_time_label.configure(text=time_text)

    # Convert bytes to MB or GB
    if total_bytes > 0:
        mb_size = total_bytes / (1024 * 1024)
        if mb_size >= 1024:
            gb_size = mb_size / 1024
            size_text = f"{gb_size:.2f} GB"
        else:
            size_text = f"{mb_size:.1f} MB"
    else:
        size_text = "0.0 MB"

    # Add '+' if some videos are still N/A
    if not all_fetched and total_bytes > 0:
        size_text += "+"
    
    total_size_label.configure(text=size_text)

def toggle_all(state):
    """Select or deselect all items in the list"""
    for row_data in video_rows:
        if state: row_data["checkbox"].select()
        else: row_data["checkbox"].deselect()
    update_dynamic_totals()

def remove_selected():
    """Remove checked rows and update dashboard"""
    global video_rows
    for row_data in reversed(video_rows):
        if row_data["checkbox"].get() == 1:
            row_data["frame"].destroy()
            video_rows.remove(row_data)
            
    total_time_label.configure(text="0s", text_color="#aaaaaa")
    update_dynamic_totals()
    try: app.after(10, lambda: list_frame._parent_canvas.yview_moveto(0.0))
    except: pass

def format_duration(seconds):
    if not seconds: return "00:00"
    m, s = divmod(int(seconds), 60)
    h, m = divmod(m, 60)
    if h > 0: return f"{h}:{m:02d}:{s:02d}"
    return f"{m:02d}:{s:02d}"

def clear_list():
    """Clear the screen before a new search"""
    global video_rows
    for widget in list_frame.winfo_children():
        widget.destroy()
    video_rows.clear()
    update_dynamic_totals()

def add_video_row(index, title, duration, vid_url, status="Ready", status_color="#28a745"):
    """Create a UI row for a single video"""
    row = ctk.CTkFrame(list_frame, fg_color="#333333", height=50)
    row.pack(side="top", fill="x", pady=2, anchor="n") 
    
    # Checkbox click updates dashboard instantly
    cb = ctk.CTkCheckBox(row, text="", width=30, command=update_dynamic_totals)
    cb.select()
    cb.pack(side="left", padx=5)

    ctk.CTkLabel(row, text=str(index), width=30).pack(side="left", padx=(5, 0))
    
    title_entry = ctk.CTkEntry(row, width=250, fg_color="transparent", border_width=0, text_color="white", font=("Arial", 12))
    title_entry.insert(0, title)
    title_entry.configure(state="readonly")
    title_entry.pack(side="left")

    ctk.CTkLabel(row, text=duration, width=70).pack(side="left")
    
    size_lbl = ctk.CTkLabel(row, text="N/A", width=80)
    size_lbl.pack(side="left")
    
    status_lbl = ctk.CTkLabel(row, text=status, text_color=status_color, width=100)
    status_lbl.pack(side="left")
    
    prog_bar = ctk.CTkProgressBar(row, width=120, progress_color="#FF6600")
    prog_bar.set(0)
    prog_bar.pack(side="left", padx=(10, 5))
    
    percent_lbl = ctk.CTkLabel(row, text="0%", width=40, font=("Arial", 12))
    percent_lbl.pack(side="left")

    # Save important widgets to use them later in downloading
    video_rows.append({
        "frame": row, "checkbox": cb, "title": title, 
        "duration": duration, "progress": prog_bar, 
        "size_label": size_lbl, "status_label": status_lbl,
        "percent_label": percent_lbl,
        "url": vid_url,
        "bytes_size": -1 # -1 means N/A
    })

# ==================== Size Calculation Engine ====================
def get_ydl_format_string(quality):
    """Return the correct yt-dlp format code"""
    if "Audio Only" in quality: return 'bestaudio/best'
    if "Medium" in quality or "720" in quality: return 'bestvideo[height<=720]+bestaudio/best'
    if "Low" in quality or "480" in quality: return 'bestvideo[height<=480]+bestaudio/best'
    height = ''.join(filter(str.isdigit, quality))
    if height: return f'bestvideo[height<={height}]+bestaudio/best'
    return 'bestvideo+bestaudio/best'

def fetch_size_for_single_video(row_data, quality):
    """Task for one thread: Fetch size of one video and handle errors"""
    global is_fetching_sizes, consecutive_errors
    
    if not is_fetching_sizes: return 
    if not row_data['frame'].winfo_exists(): return
    if row_data['bytes_size'] != -1: return # Skip if size is already known

    app.after(0, lambda: safe_ui_update(row_data['size_label'], text="...", text_color="#FF6600"))

    ydl_opts = {
        'quiet': True, 
        'no_warnings': True, 
        'noplaylist': True, 
        'ignoreerrors': True,
        'logger': SilentLogger(),
        'format': get_ydl_format_string(quality)
    }
    
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(row_data['url'], download=False)
            
            # Check flag again in case user stopped it during the network call
            if not is_fetching_sizes: 
                app.after(0, lambda: safe_ui_update(row_data['size_label'], text="N/A", text_color="white"))
                return
                
            # If info is missing, it's blocked or private
            if not info:
                row_data['bytes_size'] = 0
                app.after(0, lambda: safe_ui_update(row_data['size_label'], text="Blocked", text_color="#ff4444"))
                
                # Circuit Breaker Logic: Increase error count
                with error_lock:
                    consecutive_errors += 1
                    if consecutive_errors >= 10:
                        is_fetching_sizes = False # Trigger Auto-Stop
                return

            # Success! Find the file size
            file_size = info.get('filesize') or info.get('filesize_approx')
            if not file_size and 'requested_formats' in info:
                file_size = sum([f.get('filesize') or f.get('filesize_approx') or 0 for f in info['requested_formats']])
            
            if file_size and file_size > 0:
                row_data['bytes_size'] = file_size
                mb_size = file_size / (1024 * 1024)
                app.after(0, lambda: safe_ui_update(row_data['size_label'], text=f"{mb_size:.1f} MB", text_color="white"))
                
                # Circuit Breaker Logic: Reset counter on success
                with error_lock:
                    consecutive_errors = 0
            else:
                row_data['bytes_size'] = 0
                app.after(0, lambda: safe_ui_update(row_data['size_label'], text="Unknown", text_color="#aaaaaa"))
                
    except Exception:
        row_data['bytes_size'] = 0
        app.after(0, lambda: safe_ui_update(row_data['size_label'], text="Error", text_color="#ff4444"))
        
        # Circuit Breaker Logic: Increase error count on crash
        with error_lock:
            consecutive_errors += 1
            if consecutive_errors >= 10:
                is_fetching_sizes = False # Trigger Auto-Stop
    
    app.after(0, update_dynamic_totals)

def fetch_all_sizes_worker():
    """Main worker to fetch sizes using multiple threads"""
    global is_fetching_sizes, consecutive_errors
    
    quality = quality_combo.get()
    if quality in ["Select Quality", "Waiting for link...", "Loading..."]:
        app.after(0, lambda: update_global_status("Error: Please select a quality first!", "red"))
        return
        
    # ONLY fetch sizes for selected videos
    selected_rows = [r for r in video_rows if r["checkbox"].get() == 1]
    if not selected_rows:
        app.after(0, lambda: update_global_status("Error: No videos selected!", "red"))
        return

    # Reset globals and setup UI
    consecutive_errors = 0
    is_fetching_sizes = True
    app.after(0, lambda: update_global_status(f"Fetching sizes for {quality}...", "#FF6600", ""))
    app.after(0, lambda: fetch_btn.pack_forget())
    app.after(0, lambda: stop_fetch_btn.pack(side="left"))

    # Threading setup (5 workers max for safety)
    MAX_CONCURRENT_WORKERS = 5 
    
    with concurrent.futures.ThreadPoolExecutor(max_workers=MAX_CONCURRENT_WORKERS) as executor:
        futures = [executor.submit(fetch_size_for_single_video, row, quality) for row in selected_rows]
        concurrent.futures.wait(futures)

    # Restore UI when done
    app.after(0, lambda: stop_fetch_btn.pack_forget())
    app.after(0, lambda: fetch_btn.pack(side="left"))
    
    # Check finish status
    if consecutive_errors >= 10:
        # Auto-Stopped by Circuit Breaker
        app.after(0, lambda: update_global_status("Fetching stopped automatically: YouTube blocked the connection.", "#ff4444", ""))
    elif is_fetching_sizes:
        # Finished naturally
        blocked_count = sum(1 for r in selected_rows if r['bytes_size'] == 0)
        if blocked_count > 0:
            app.after(0, lambda: update_global_status("Sizes fetched.", "#28a745", f"({blocked_count} video(s) might be blocked or failed)"))
        else:
            app.after(0, lambda: update_global_status("All sizes fetched successfully.", "#28a745", ""))
    else:
        # Manually Stopped by user
        app.after(0, lambda: update_global_status("Fetching stopped by user.", "orange", ""))
        
    is_fetching_sizes = False

# ==================== Video Data Fetching ====================
def render_chunk(entries_data, current_idx, qualities, chunk_size=15):
    """Load items into UI in chunks to prevent freezing"""
    end_idx = min(current_idx + chunk_size, len(entries_data))
    
    for i in range(current_idx, end_idx):
        data = entries_data[i]
        add_video_row(data['idx'], data['title'], data['dur'], data['url'])
        
    app.after(0, lambda: update_global_status(f"Rendering videos... ({end_idx}/{len(entries_data)})", "#FF6600", ""))

    if end_idx < len(entries_data):
        app.after(10, lambda: render_chunk(entries_data, end_idx, qualities, chunk_size))
    else:
        quality_combo.configure(values=qualities)
        if qualities: quality_combo.set(qualities[0])
        app.after(0, update_dynamic_totals) 
        app.after(0, lambda: update_global_status("Data fetched successfully. Ready to use.", "#28a745", ""))

def fetch_video_data():
    """Get playlist or video info from YouTube"""
    url = url_entry.get()
    if not url:
        app.after(0, lambda: update_global_status("Error: Please enter a valid YouTube URL!", "red", ""))
        return

    app.after(0, clear_list)
    app.after(0, lambda: update_global_status("Connecting to YouTube... Please wait.", "#FF6600", ""))
    app.after(0, lambda: quality_combo.set("Loading..."))

    is_single_video = ("watch?v=" in url) or ("youtu.be/" in url)
    
    ydl_opts = {
        'quiet': True, 
        'no_warnings': True,
        'extract_flat': 'in_playlist',
        'noplaylist': is_single_video
    }
    
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            qualities = []
            entries_data = [] 

            if 'entries' in info:
                for idx, entry in enumerate(info['entries'], start=1):
                    title = entry.get('title', 'Unknown Title')
                    dur = format_duration(entry.get('duration', 0))
                    vid_url = entry.get('url')
                    if not vid_url: vid_url = f"https://www.youtube.com/watch?v={entry.get('id')}"
                    entries_data.append({'idx': idx, 'title': title, 'dur': dur, 'url': vid_url})
                qualities = ["Best Quality", "Medium", "Low", "Audio Only (MP3)"]
            else:
                title = info.get('title', 'Unknown Title')
                dur = format_duration(info.get('duration', 0))
                vid_url = info.get('webpage_url', url)
                entries_data.append({'idx': 1, 'title': title, 'dur': dur, 'url': vid_url})
                
                formats = info.get('formats', [])
                q_set = set()
                for f in formats:
                    h = f.get('height')
                    if h and h > 0: q_set.add(f"{h}p")
                
                qualities = sorted(list(q_set), key=lambda x: int(x.replace('p', '')), reverse=True)
                if not qualities: qualities = ["Best Quality"]
                qualities.append("Audio Only (MP3)")
            
            app.after(0, lambda: render_chunk(entries_data, 0, qualities))

    except Exception as e:
        app.after(0, lambda e=e: update_global_status(f"Error: {str(e)[:80]}...", "red", ""))

def on_search_click():
    threading.Thread(target=fetch_video_data, daemon=True).start()

ctk.CTkButton(url_input_layout, text="🔍", width=40, fg_color="#840284", hover_color="#6b016b", command=on_search_click).pack(side="left")

# ==================== Download Engine ====================
def download_worker():
    save_path = path_entry.get()
    if not save_path or not os.path.isdir(save_path):
        app.after(0, lambda: update_global_status("Error: Please select a valid Save Path first!", "red", ""))
        return

    selected_rows = [r for r in video_rows if r["checkbox"].get() == 1]
    if not selected_rows:
        app.after(0, lambda: update_global_status("Error: No videos selected to download!", "red", ""))
        return

    quality = quality_combo.get()
    if quality in ["Select Quality", "Waiting for link...", "Loading..."]:
        app.after(0, lambda: update_global_status("Error: Please select a quality first!", "red", ""))
        return

    app.after(0, lambda: update_global_status(f"Starting download for {len(selected_rows)} videos...", "#FF6600", ""))

    format_str = get_ydl_format_string(quality)
    postprocessors = []

    if "Audio Only" in quality:
        postprocessors = [{'key': 'FFmpegExtractAudio', 'preferredcodec': 'mp3', 'preferredquality': '192'}]

    for row_data in selected_rows:
        if not row_data['frame'].winfo_exists(): continue 

        app.after(0, lambda r=row_data: safe_ui_update(r['status_label'], text="Preparing...", text_color="#FF6600"))
        
        def progress_hook(d, r=row_data):
            if not r['frame'].winfo_exists(): return 
            
            if d['status'] == 'downloading':
                total = d.get('total_bytes') or d.get('total_bytes_estimate', 0)
                downloaded = d.get('downloaded_bytes', 0)
                if total > 0:
                    percent = downloaded / total
                    
                    app.after(0, lambda: safe_progress_update(r['progress'], percent))
                    app.after(0, lambda: safe_ui_update(r['percent_label'], text=f"{int(percent*100)}%"))
                    
                    if r['bytes_size'] == -1: 
                        mb_size = total / (1024 * 1024)
                        app.after(0, lambda: safe_ui_update(r['size_label'], text=f"{mb_size:.1f} MB"))
                    
                    app.after(0, lambda: safe_ui_update(r['status_label'], text="Downloading...", text_color="#FF6600"))
            
            elif d['status'] == 'finished':
                app.after(0, lambda: safe_progress_update(r['progress'], 1.0))
                app.after(0, lambda: safe_ui_update(r['percent_label'], text="100%", text_color="#28a745"))
                app.after(0, lambda: safe_ui_update(r['status_label'], text="Processing...", text_color="#FFCC00"))

        ydl_opts = {
            'outtmpl': os.path.join(save_path, '%(title)s.%(ext)s'),
            'format': format_str,
            'progress_hooks': [progress_hook],
            'noplaylist': True,
            'quiet': True,
            'no_warnings': True,
            'ignoreerrors': True,
            'logger': SilentLogger(),
            'ffmpeg_location': imageio_ffmpeg.get_ffmpeg_exe() 
        }
        if postprocessors:
            ydl_opts['postprocessors'] = postprocessors

        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.download([row_data['url']])
            app.after(0, lambda r=row_data: safe_ui_update(r['status_label'], text="Completed", text_color="#28a745"))
        except Exception:
            app.after(0, lambda r=row_data: safe_ui_update(r['status_label'], text="Failed", text_color="#ff4444"))

    app.after(0, lambda: update_global_status("Downloads finished.", "#28a745", ""))

app.mainloop()