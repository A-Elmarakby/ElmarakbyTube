import customtkinter as ctk
import yt_dlp
from yt_dlp.utils import sanitize_filename
import threading
import os
import glob
import subprocess
from tkinter import filedialog
import imageio_ffmpeg
import concurrent.futures
import winsound  # لمكتبة الأصوات

# --- Window Setup ---
ctk.set_appearance_mode("Dark")
app = ctk.CTk()
app.geometry("1000x700")
app.title("ElmarakbyTube Downloader")

# Global variables
video_rows = []
is_fetching_sizes = False 
consecutive_errors = 0 
error_lock = threading.Lock()
is_downloading = False 
is_converting = False
current_ffmpeg_process = None

# --- Custom Logger to hide YouTube errors in the Terminal ---
class SilentLogger:
    def debug(self, msg): pass
    def warning(self, msg): pass
    def error(self, msg): pass

# ==================== Top Section ====================
top_frame = ctk.CTkFrame(app, fg_color="transparent")
top_frame.pack(fill="x", padx=20, pady=20)

save_path_frame = ctk.CTkFrame(top_frame, fg_color="transparent")
save_path_frame.pack(side="left", fill="x", expand=True, padx=(0, 10))
ctk.CTkLabel(save_path_frame, text="Save Path:", font=("Arial", 12, "bold")).pack(anchor="w")

path_input_layout = ctk.CTkFrame(save_path_frame, fg_color="transparent")
path_input_layout.pack(fill="x")
path_entry = ctk.CTkEntry(path_input_layout, placeholder_text="/Downloads/Playlists...")
path_entry.pack(side="left", fill="x", expand=True, padx=(0, 5))

def browse_save_path():
    folder_path = filedialog.askdirectory(title="Select Save Folder")
    if folder_path:
        path_entry.delete(0, 'end')
        path_entry.insert(0, folder_path)

ctk.CTkButton(path_input_layout, text="Browse", width=80, fg_color="#840284", hover_color="#6b016b", command=browse_save_path).pack(side="left")

url_frame = ctk.CTkFrame(top_frame, fg_color="transparent")
url_frame.pack(side="left", fill="x", expand=True)
ctk.CTkLabel(url_frame, text="Video or Playlist URL:", font=("Arial", 12, "bold")).pack(anchor="w")

url_input_layout = ctk.CTkFrame(url_frame, fg_color="transparent")
url_input_layout.pack(fill="x")
url_entry = ctk.CTkEntry(url_input_layout, placeholder_text="Paste your YouTube link here...")
url_entry.pack(side="left", fill="x", expand=True, padx=(0, 5))

def handle_hardware_shortcuts(event):
    if event.state & 4 or event.state & 12:
        if event.keycode == 86: 
            try: event.widget.event_generate("<<Paste>>")
            except: pass
            return "break"
        elif event.keycode == 67: 
            try: event.widget.event_generate("<<Copy>>")
            except: pass
            return "break"
        elif event.keycode == 65: 
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

ctk.CTkButton(toolbar_frame, text="Select All", width=90, fg_color="#333", hover_color="#444", command=lambda: toggle_all(True)).pack(side="left", padx=(0, 5))
ctk.CTkButton(toolbar_frame, text="Deselect All", width=90, fg_color="#333", hover_color="#444", command=lambda: toggle_all(False)).pack(side="left", padx=(0, 5))
ctk.CTkButton(toolbar_frame, text="Remove Selected", width=110, fg_color="#8b0000", hover_color="#660000", command=lambda: remove_selected()).pack(side="left")

dashboard_frame = ctk.CTkFrame(toolbar_frame, fg_color="transparent")
dashboard_frame.pack(side="left", padx=20)

ctk.CTkLabel(dashboard_frame, text="Total Time:", font=("Arial", 12, "bold")).pack(side="left", padx=(0, 5))
# Text Color Changed to Gray (#aaaaaa)
total_time_label = ctk.CTkLabel(dashboard_frame, text="0s", font=("Arial", 12, "bold"), text_color="#aaaaaa", width=80, anchor="w")
total_time_label.pack(side="left", padx=(0, 15))

ctk.CTkLabel(dashboard_frame, text="Total Size:", font=("Arial", 12, "bold")).pack(side="left", padx=(0, 5))
# Text Color Changed to Gray (#aaaaaa)
total_size_label = ctk.CTkLabel(dashboard_frame, text="0.0 MB", font=("Arial", 12, "bold"), text_color="#aaaaaa", width=80, anchor="w")
total_size_label.pack(side="left")

quality_layout = ctk.CTkFrame(toolbar_frame, fg_color="transparent")
quality_layout.pack(side="right")

def on_quality_change(choice):
    for row in video_rows:
        row['bytes_size'] = -1 
        safe_ui_update(row['size_label'], text="N/A", text_color="white")
    update_dynamic_totals()

def on_fetch_sizes_click():
    threading.Thread(target=fetch_all_sizes_worker, daemon=True).start()

def on_stop_fetch_click():
    global is_fetching_sizes
    is_fetching_sizes = False
    update_global_status("Stopping fetch... please wait.", "orange", "")

fetch_action_frame = ctk.CTkFrame(quality_layout, fg_color="transparent")
fetch_action_frame.pack(side="left", padx=(0, 10))

fetch_btn = ctk.CTkButton(fetch_action_frame, text="Fetch Sizes", width=90, fg_color="#840284", hover_color="#6b016b", command=on_fetch_sizes_click)
fetch_btn.pack(side="left")

stop_fetch_btn = ctk.CTkButton(fetch_action_frame, text="Stop Fetch", width=90, fg_color="#ff4444", hover_color="#cc0000", command=on_stop_fetch_click)

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

global_status_label = ctk.CTkLabel(status_bar, text="Status: Ready", font=("Arial", 12))
global_status_label.pack(side="left", padx=(20, 5))

global_warning_label = ctk.CTkLabel(status_bar, text="", font=("Arial", 12, "bold"), text_color="#ff4444")
global_warning_label.pack(side="left")

# ==================== UI Safety Helpers ====================
def safe_ui_update(widget, **kwargs):
    if widget and widget.winfo_exists():
        widget.configure(**kwargs)

def safe_progress_update(widget, value):
    if widget and widget.winfo_exists():
        widget.set(value)

# ==================== Core Functions & Custom Popups ====================
def center_toplevel(top, width, height):
    app.update_idletasks()
    x = app.winfo_x() + (app.winfo_width() // 2) - (width // 2)
    y = app.winfo_y() + (app.winfo_height() // 2) - (height // 2)
    top.geometry(f"{width}x{height}+{x}+{y}")

def custom_msg_box(title, message, msg_type="error"):
    """Displays a styled popup with Windows system sounds, Emojis, and an OK button"""
    dialog = ctk.CTkToplevel(app)
    dialog.title(title)
    center_toplevel(dialog, 450, 200)
    dialog.transient(app)
    dialog.grab_set()
    
    color = "#ff4444" 
    icon = "🛑"
    if msg_type == "error":
        winsound.MessageBeep(winsound.MB_ICONHAND)
    elif msg_type == "warning":
        color = "#FFCC00" 
        icon = "⚠️"
        winsound.MessageBeep(winsound.MB_ICONEXCLAMATION)
    elif msg_type == "success":
        color = "#28a745"
        icon = "✅"
        winsound.MessageBeep(winsound.MB_ICONASTERISK)
    elif msg_type == "info":
        color = "#0086cc"
        icon = "ℹ️"
        winsound.MessageBeep(winsound.MB_ICONASTERISK)
        
    lbl_title = ctk.CTkLabel(dialog, text=f"{icon} {title}", font=("Arial", 16, "bold"), text_color=color)
    lbl_title.pack(pady=(20, 5))
    
    lbl_msg = ctk.CTkLabel(dialog, text=message, font=("Arial", 14), wraplength=400)
    lbl_msg.pack(pady=(0, 20), padx=20)
    
    ctk.CTkButton(dialog, text="OK", fg_color="#555", hover_color="#333", width=100, command=dialog.destroy).pack(pady=(0, 20))
    app.wait_window(dialog)

def format_size(bytes_size):
    """Smart formatter to convert MB to GB if it exceeds 1000 MB"""
    if bytes_size <= 0: return "0.0 MB"
    mb = bytes_size / (1024 * 1024)
    if mb >= 1000:
        gb = mb / 1024
        return f"{gb:.2f} GB"
    return f"{mb:.1f} MB"

def update_global_status(msg, color="white", warning_msg=""):
    global_status_label.configure(text=f"Status: {msg}", text_color=color)
    global_warning_label.configure(text=warning_msg)

def update_dynamic_totals():
    total_bytes = 0
    total_seconds = 0
    all_fetched = True 

    for row in video_rows:
        if row["checkbox"].get() == 1: 
            if row['bytes_size'] > 0:
                total_bytes += row['bytes_size']
            elif row['bytes_size'] == -1: 
                all_fetched = False

            dur_str = row["duration"]
            if dur_str != "--:--" and dur_str != "N/A":
                parts = dur_str.split(":")
                if len(parts) == 2:
                    total_seconds += int(parts[0]) * 60 + int(parts[1])
                elif len(parts) == 3:
                    total_seconds += int(parts[0]) * 3600 + int(parts[1]) * 60 + int(parts[2])

    h, r = divmod(total_seconds, 3600)
    m, s = divmod(r, 60)
    
    if h > 0: time_text = f"{int(h)}h {int(m)}m {int(s)}s"
    elif m > 0: time_text = f"{int(m)}m {int(s)}s"
    else: time_text = f"{int(s)}s"
        
    if total_seconds == 0: time_text = "0s"
    total_time_label.configure(text=time_text)

    size_text = format_size(total_bytes)
    if not all_fetched and total_bytes > 0:
        size_text += "+"
    total_size_label.configure(text=size_text)

def toggle_all(state):
    for row_data in video_rows:
        if state: row_data["checkbox"].select()
        else: row_data["checkbox"].deselect()
    update_dynamic_totals()

def remove_selected():
    global video_rows
    for row_data in reversed(video_rows):
        if row_data["checkbox"].get() == 1:
            row_data["frame"].destroy()
            video_rows.remove(row_data)
            
    total_time_label.configure(text="0s")
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
    global video_rows
    for widget in list_frame.winfo_children():
        widget.destroy()
    video_rows.clear()
    update_dynamic_totals()

def add_video_row(index, title, duration, vid_url, status="Ready", status_color="#28a745"):
    row = ctk.CTkFrame(list_frame, fg_color="#333333", height=50)
    row.pack(side="top", fill="x", pady=2, anchor="n") 
    
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

    video_rows.append({
        "frame": row, "checkbox": cb, "title": title, 
        "duration": duration, "progress": prog_bar, 
        "size_label": size_lbl, "status_label": status_lbl,
        "percent_label": percent_lbl,
        "url": vid_url,
        "bytes_size": -1,
        "dl_state": "ready" 
    })

# ==================== Size Calculation Engine ====================
def get_ydl_format_string(quality):
    if "Audio Only" in quality: return 'bestaudio/best'
    if "Medium" in quality or "720" in quality: return 'bestvideo[height<=720]+bestaudio/best'
    if "Low" in quality or "480" in quality: return 'bestvideo[height<=480]+bestaudio/best'
    height = ''.join(filter(str.isdigit, quality))
    if height: return f'bestvideo[height<={height}]+bestaudio/best'
    return 'bestvideo+bestaudio/best'

def fetch_size_for_single_video(row_data, quality):
    global is_fetching_sizes, consecutive_errors
    
    if not is_fetching_sizes: return 
    if not row_data['frame'].winfo_exists(): return
    if row_data['bytes_size'] != -1: return 

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
            
            if not is_fetching_sizes: 
                app.after(0, lambda: safe_ui_update(row_data['size_label'], text="N/A", text_color="white"))
                return
                
            if not info:
                row_data['bytes_size'] = 0
                app.after(0, lambda: safe_ui_update(row_data['size_label'], text="Blocked", text_color="#ff4444"))
                with error_lock:
                    consecutive_errors += 1
                    if consecutive_errors >= 10:
                        is_fetching_sizes = False 
                return

            file_size = info.get('filesize') or info.get('filesize_approx')
            if not file_size and 'requested_formats' in info:
                file_size = sum([f.get('filesize') or f.get('filesize_approx') or 0 for f in info['requested_formats']])
            
            if file_size and file_size > 0:
                row_data['bytes_size'] = file_size
                size_str = format_size(file_size)
                app.after(0, lambda: safe_ui_update(row_data['size_label'], text=size_str, text_color="white"))
                with error_lock:
                    consecutive_errors = 0
            else:
                row_data['bytes_size'] = 0
                app.after(0, lambda: safe_ui_update(row_data['size_label'], text="Unknown", text_color="#aaaaaa"))
                
    except Exception:
        row_data['bytes_size'] = 0
        app.after(0, lambda: safe_ui_update(row_data['size_label'], text="Error", text_color="#ff4444"))
        with error_lock:
            consecutive_errors += 1
            if consecutive_errors >= 10:
                is_fetching_sizes = False 
    
    app.after(0, update_dynamic_totals)

def fetch_all_sizes_worker():
    global is_fetching_sizes, consecutive_errors
    
    quality = quality_combo.get()
    if quality in ["Select Quality", "Waiting for link...", "Loading..."]:
        app.after(0, lambda: custom_msg_box("Missing Selection", "Please select a Quality first!", "warning"))
        return
        
    selected_rows = [r for r in video_rows if r["checkbox"].get() == 1]
    if not selected_rows:
        app.after(0, lambda: custom_msg_box("No Videos", "Please select at least one video to fetch sizes.", "warning"))
        return

    consecutive_errors = 0
    is_fetching_sizes = True
    app.after(0, lambda: update_global_status(f"Fetching sizes for {quality}...", "#FF6600", ""))
    app.after(0, lambda: fetch_btn.pack_forget())
    app.after(0, lambda: stop_fetch_btn.pack(side="left"))

    MAX_CONCURRENT_WORKERS = 5 
    
    with concurrent.futures.ThreadPoolExecutor(max_workers=MAX_CONCURRENT_WORKERS) as executor:
        futures = [executor.submit(fetch_size_for_single_video, row, quality) for row in selected_rows]
        concurrent.futures.wait(futures)

    app.after(0, lambda: stop_fetch_btn.pack_forget())
    app.after(0, lambda: fetch_btn.pack(side="left"))
    
    if consecutive_errors >= 10:
        app.after(0, lambda: update_global_status("Fetching stopped automatically: YouTube blocked the connection.", "#ff4444", ""))
        app.after(0, lambda: custom_msg_box("Connection Blocked", "YouTube temporarily blocked the connection (Too many requests).", "error"))
    elif is_fetching_sizes:
        blocked_count = sum(1 for r in selected_rows if r['bytes_size'] == 0)
        if blocked_count > 0:
            app.after(0, lambda: update_global_status("Sizes fetched.", "#28a745", f"({blocked_count} video(s) might be blocked or failed)"))
        else:
            app.after(0, lambda: update_global_status("All sizes fetched successfully.", "#28a745", ""))
    else:
        app.after(0, lambda: update_global_status("Fetching stopped by user.", "orange", ""))
        
    is_fetching_sizes = False

# ==================== Video Data Fetching ====================
def render_chunk(entries_data, current_idx, qualities, chunk_size=15):
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
    url = url_entry.get()
    if not url:
        app.after(0, lambda: custom_msg_box("Missing URL", "Please enter a valid YouTube URL to search!", "error"))
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
        app.after(0, lambda: update_global_status("Search Failed.", "red", ""))
        app.after(0, lambda e=e: custom_msg_box("Connection Error", f"Failed to connect or fetch data from YouTube.\n\nCheck URL or connection.", "error"))

def on_search_click():
    threading.Thread(target=fetch_video_data, daemon=True).start()

ctk.CTkButton(url_input_layout, text="🔍", width=40, fg_color="#840284", hover_color="#6b016b", command=on_search_click).pack(side="left")

# ==================== Core Download / Convert Helpers ====================
def find_downloaded_file(save_path, title):
    sanitized = sanitize_filename(title)
    
    for ext in ['.mkv', '.webm', '.mp4', '.m4a', '.mp3']:
        p = os.path.join(save_path, f"{sanitized}{ext}")
        if os.path.exists(p): return p
        
    try:
        safe_prefix = sanitized[:15] 
        search_pattern = os.path.join(save_path, f"*{safe_prefix}*")
        files = glob.glob(search_pattern)
        for f in files:
            if any(f.endswith(e) for e in ['.mkv', '.webm', '.mp4', '.m4a', '.mp3']) and not f.endswith('.part'):
                return f
    except: pass
    return None

def _download_process(rows_to_download, quality, save_path):
    global is_downloading
    
    format_str = get_ydl_format_string(quality)
    postprocessors = []
    if "Audio Only" in quality:
        postprocessors = [{'key': 'FFmpegExtractAudio', 'preferredcodec': 'mp3', 'preferredquality': '192'}]

    for row_data in rows_to_download:
        if not is_downloading: break 
        if not row_data['frame'].winfo_exists(): continue 
        
        row_data['dl_state'] = 'preparing'
        app.after(0, lambda r=row_data: safe_ui_update(r['status_label'], text="Preparing...", text_color="#FF6600"))
        
        class DownloadLogger:
            def debug(self, msg):
                if "has already been downloaded" in msg or "already exists" in msg:
                    row_data['dl_state'] = 'already_exists'
                    app.after(0, lambda r=row_data: safe_ui_update(r['status_label'], text="Already Exists", text_color="#28a745"))
                    app.after(0, lambda r=row_data: safe_progress_update(r['progress'], 1.0))
                    app.after(0, lambda r=row_data: safe_ui_update(r['percent_label'], text="100%", text_color="#28a745"))
            def warning(self, msg): pass
            def error(self, msg): pass

        def progress_hook(d, r=row_data):
            global is_downloading
            if not is_downloading:
                raise ValueError("DOWNLOAD_CANCELLED") # Abort instantly
                
            if not r['frame'].winfo_exists(): return 
            
            if d['status'] == 'downloading':
                total = d.get('total_bytes') or d.get('total_bytes_estimate', 0)
                downloaded = d.get('downloaded_bytes', 0)
                if total > 0:
                    percent = downloaded / total
                    app.after(0, lambda: safe_progress_update(r['progress'], percent))
                    app.after(0, lambda: safe_ui_update(r['percent_label'], text=f"{int(percent*100)}%"))
                    
                    if r['bytes_size'] == -1: 
                        size_str = format_size(total)
                        app.after(0, lambda: safe_ui_update(r['size_label'], text=size_str))
                    
                    if r.get('dl_state') not in ['canceled', 'already_exists']:
                        r['dl_state'] = 'downloading'
                        app.after(0, lambda: safe_ui_update(r['status_label'], text="Downloading...", text_color="#FF6600"))
            
            elif d['status'] == 'finished':
                if r.get('dl_state') != 'already_exists':
                    r['dl_state'] = 'processing'
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
            'continuedl': True, 
            'logger': DownloadLogger(), 
            'ffmpeg_location': imageio_ffmpeg.get_ffmpeg_exe() 
        }
        if postprocessors:
            ydl_opts['postprocessors'] = postprocessors

        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.download([row_data['url']])
                
            if is_downloading and row_data.get('dl_state') not in ['canceled', 'already_exists', 'failed']:
                row_data['dl_state'] = 'completed'
                app.after(0, lambda r=row_data: safe_ui_update(r['status_label'], text="Completed", text_color="#28a745"))
                app.after(0, lambda r=row_data: safe_progress_update(r['progress'], 1.0))
                app.after(0, lambda r=row_data: safe_ui_update(r['percent_label'], text="100%", text_color="#28a745"))
                
        except Exception:
            if not is_downloading:
                pass # Instant update handled in the Cancel button
            else:
                row_data['dl_state'] = 'failed'
                app.after(0, lambda r=row_data: safe_ui_update(r['status_label'], text="Failed", text_color="#ff4444"))

def download_worker():
    global is_downloading
    save_path = path_entry.get()
    
    if not save_path or not os.path.isdir(save_path):
        app.after(0, lambda: custom_msg_box("Invalid Path", "Please select a valid Save Path folder first!", "error"))
        return

    selected_rows = [r for r in video_rows if r["checkbox"].get() == 1]
    if not selected_rows:
        app.after(0, lambda: custom_msg_box("No Selection", "Please select at least one video to download!", "warning"))
        return

    quality = quality_combo.get()
    if quality in ["Select Quality", "Waiting for link...", "Loading..."]:
        app.after(0, lambda: custom_msg_box("Quality Not Selected", "Please select a Download Quality first!", "warning"))
        return

    is_downloading = True
    app.after(0, lambda: update_global_status(f"Starting download for {len(selected_rows)} videos...", "#FF6600", ""))

    _download_process(selected_rows, quality, save_path)

    if is_downloading:
        app.after(0, lambda: update_global_status("Downloads finished.", "#28a745", ""))
        winsound.MessageBeep(winsound.MB_ICONASTERISK) # Success sound
    else:
        app.after(0, lambda: update_global_status("Downloads canceled by user.", "orange", ""))
        
    is_downloading = False

# ==================== Custom Centered Dialogs (Yes/No/Speed) ====================
def ask_conversion_speed():
    dialog = ctk.CTkToplevel(app)
    dialog.title("Conversion Speed")
    center_toplevel(dialog, 350, 150)
    dialog.transient(app) 
    dialog.grab_set() 
    
    winsound.MessageBeep(winsound.MB_ICONASTERISK)
    result = ["cancel"] 
    def set_res(val):
        result[0] = val
        dialog.destroy()
        
    lbl = ctk.CTkLabel(dialog, text="⚡ Choose conversion speed:", font=("Arial", 14, "bold"))
    lbl.pack(pady=20)
    
    btn_frame = ctk.CTkFrame(dialog, fg_color="transparent")
    btn_frame.pack()
    
    ctk.CTkButton(btn_frame, text="Fast", fg_color="#28a745", hover_color="#218838", width=90, command=lambda: set_res("fast")).pack(side="left", padx=10)
    ctk.CTkButton(btn_frame, text="Slow", fg_color="#ff4444", hover_color="#cc0000", width=90, command=lambda: set_res("slow")).pack(side="left", padx=10)
    ctk.CTkButton(btn_frame, text="Cancel", fg_color="#555", hover_color="#333", width=90, command=lambda: set_res("cancel")).pack(side="left", padx=10)
    
    app.wait_window(dialog)
    return result[0]

def custom_ask_yes_no(title, message, icon="⚠️"):
    dialog = ctk.CTkToplevel(app)
    dialog.title(title)
    center_toplevel(dialog, 450, 180)
    dialog.transient(app)
    dialog.grab_set()
    
    winsound.MessageBeep(winsound.MB_ICONEXCLAMATION)
    result = [False]
    def set_res(val):
        result[0] = val
        dialog.destroy()
        
    lbl = ctk.CTkLabel(dialog, text=f"{icon} {message}", font=("Arial", 14, "bold"), wraplength=400)
    lbl.pack(pady=20, padx=20)
    
    btn_frame = ctk.CTkFrame(dialog, fg_color="transparent")
    btn_frame.pack()
    
    ctk.CTkButton(btn_frame, text="Yes", fg_color="#28a745", hover_color="#218838", width=90, command=lambda: set_res(True)).pack(side="left", padx=10)
    ctk.CTkButton(btn_frame, text="No", fg_color="#ff4444", hover_color="#cc0000", width=90, command=lambda: set_res(False)).pack(side="left", padx=10)
    
    app.wait_window(dialog)
    return result[0]

# ==================== The New Convert Worker ====================
def convert_worker(speed_choice, selected_rows, save_path, quality, do_download_first):
    global is_converting, current_ffmpeg_process
    
    if do_download_first:
        global is_downloading
        is_downloading = True
        app.after(0, lambda: update_global_status("Downloading missing files...", "#FF6600", ""))
        _download_process(selected_rows, quality, save_path)
        is_downloading = False
        
        if not is_converting: 
            app.after(0, lambda: update_global_status("Conversion canceled.", "orange", ""))
            return
            
    app.after(0, lambda: convert_btn.pack_forget())
    app.after(0, lambda: stop_convert_btn.pack(side="left", padx=10))
    
    files_to_delete = []
    app.after(0, lambda: update_global_status("Starting conversion...", "#00a8ff", ""))
    
    for row_data in selected_rows:
        if not is_converting: break 
        if not row_data['frame'].winfo_exists(): continue 
        
        input_file = find_downloaded_file(save_path, row_data['title'])
        if not input_file:
            app.after(0, lambda r=row_data: safe_ui_update(r['status_label'], text="Not Found", text_color="#ff4444"))
            continue
            
        if input_file.endswith(('.mp4')):
            app.after(0, lambda r=row_data: safe_ui_update(r['status_label'], text="Already MP4", text_color="#28a745"))
            app.after(0, lambda r=row_data: safe_progress_update(r['progress'], 1.0))
            app.after(0, lambda r=row_data: safe_ui_update(r['percent_label'], text="100%", text_color="#28a745"))
            continue
            
        # Ignore Audio files gracefully
        if input_file.endswith(('.mp3', '.m4a', '.wav')):
            app.after(0, lambda r=row_data: safe_ui_update(r['status_label'], text="Audio File", text_color="#28a745"))
            app.after(0, lambda r=row_data: safe_progress_update(r['progress'], 1.0))
            app.after(0, lambda r=row_data: safe_ui_update(r['percent_label'], text="100%", text_color="#28a745"))
            continue
            
        output_file = os.path.splitext(input_file)[0] + '.mp4'
        
        app.after(0, lambda r=row_data: safe_ui_update(r['status_label'], text="Converting...", text_color="#00a8ff"))
        app.after(0, lambda r=row_data: safe_ui_update(r['percent_label'], text="---", text_color="#00a8ff"))
        app.after(0, lambda r=row_data: r['progress'].configure(mode="indeterminate", progress_color="#00a8ff"))
        app.after(0, lambda r=row_data: r['progress'].start())
        
        update_status_msg = "Remuxing" if speed_choice == "fast" else "Re-encoding"
        app.after(0, lambda: update_global_status(f"Converting ({update_status_msg})...", "#00a8ff", ""))
        
        cmd = [imageio_ffmpeg.get_ffmpeg_exe(), '-y', '-i', input_file]
        if speed_choice == "fast":
            cmd.extend(['-c', 'copy'])
        else:
            cmd.extend(['-c:v', 'libx264', '-preset', 'fast', '-c:a', 'aac'])
        cmd.append(output_file)
        
        try:
            current_ffmpeg_process = subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            current_ffmpeg_process.wait() 
            
            if not is_converting: 
                raise Exception("KILLED_BY_USER")
                
            if current_ffmpeg_process.returncode != 0:
                raise Exception("FFMPEG_ERROR")
            
            app.after(0, lambda r=row_data: r['progress'].stop())
            app.after(0, lambda r=row_data: r['progress'].configure(mode="determinate", progress_color="#FF6600"))
            app.after(0, lambda r=row_data: safe_progress_update(r['progress'], 1.0))
            app.after(0, lambda r=row_data: safe_ui_update(r['percent_label'], text="100%", text_color="#28a745"))
            app.after(0, lambda r=row_data: safe_ui_update(r['status_label'], text="Converted", text_color="#28a745"))
            
            files_to_delete.append(input_file)
        except Exception:
            app.after(0, lambda r=row_data: r['progress'].stop())
            app.after(0, lambda r=row_data: r['progress'].configure(mode="determinate", progress_color="#FF6600"))
            if not is_converting:
                app.after(0, lambda r=row_data: safe_ui_update(r['status_label'], text="Canceled", text_color="#ff4444"))
                app.after(0, lambda r=row_data: safe_progress_update(r['progress'], 0))
                app.after(0, lambda r=row_data: safe_ui_update(r['percent_label'], text="0%", text_color="#ff4444"))
            else:
                app.after(0, lambda r=row_data: safe_ui_update(r['status_label'], text="Convert Failed", text_color="#ff4444"))
        finally:
            current_ffmpeg_process = None
            
    app.after(0, lambda: stop_convert_btn.pack_forget())
    app.after(0, lambda: convert_btn.pack(side="left", padx=10))
    
    if is_converting:
        app.after(0, lambda: update_global_status("All conversions completed.", "#28a745", ""))
        winsound.MessageBeep(winsound.MB_ICONASTERISK)
        if files_to_delete:
            def ask_cleanup():
                if custom_ask_yes_no("Cleanup", "Conversion completed successfully!\nDo you want to delete the old original files?", icon="🗑️"):
                    for f in files_to_delete:
                        try: os.remove(f)
                        except: pass
                    update_global_status("Conversion complete. Old files deleted.", "#28a745", "")
            app.after(0, ask_cleanup)
    else:
        app.after(0, lambda: update_global_status("Conversion stopped by user.", "orange", ""))

# ==================== Bottom Section (Download, Convert & Cancel) ====================
bottom_frame = ctk.CTkFrame(app, fg_color="transparent")
bottom_frame.pack(pady=10, side="bottom") 

center_actions_frame = ctk.CTkFrame(bottom_frame, fg_color="transparent")
center_actions_frame.pack()

def on_download_click():
    threading.Thread(target=download_worker, daemon=True).start()

def on_cancel_download_click():
    global is_downloading
    if is_downloading:
        is_downloading = False
        update_global_status("Canceling download... please wait.", "orange", "")
        # Force Instant UI Update for all downloading files bypassing yt-dlp block delay
        for r in video_rows:
            if r.get('dl_state') in ['preparing', 'downloading']:
                r['dl_state'] = 'canceled'
                safe_ui_update(r['status_label'], text="Canceled", text_color="#ff4444")
                safe_progress_update(r['progress'], 0)
                safe_ui_update(r['percent_label'], text="0%", text_color="#ff4444")

def on_convert_click():
    global is_converting
    save_path = path_entry.get()
    if not save_path or not os.path.isdir(save_path):
        custom_msg_box("Invalid Path", "Please select a valid Save Path folder first!", "error")
        return

    selected_rows = [r for r in video_rows if r["checkbox"].get() == 1]
    if not selected_rows:
        custom_msg_box("No Selection", "Please select at least one video to convert!", "warning")
        return
        
    quality = quality_combo.get()
    if quality in ["Select Quality", "Waiting for link...", "Loading..."]:
        custom_msg_box("Quality Not Selected", "Please select a Quality first!", "warning")
        return

    speed_choice = ask_conversion_speed()
    if speed_choice == "cancel":
        update_global_status("Conversion canceled by user.", "orange", "")
        return
    
    needs_download = False
    for r in selected_rows:
        if not find_downloaded_file(save_path, r['title']):
            needs_download = True
            break
            
    do_download_first = False
    if needs_download:
        dl_choice = custom_ask_yes_no("Download Required", "Some selected videos are not downloaded yet.\nDo you want to download them first?", icon="⚠️")
        if not dl_choice:
            update_global_status("Conversion canceled by user.", "orange", "")
            return
        do_download_first = True
        
    is_converting = True
    threading.Thread(target=convert_worker, args=(speed_choice, selected_rows, save_path, quality, do_download_first), daemon=True).start()

def on_stop_convert_click():
    global is_converting, current_ffmpeg_process
    is_converting = False
    if current_ffmpeg_process:
        try: current_ffmpeg_process.terminate()
        except: pass
    update_global_status("Stopping conversion... please wait.", "orange", "")

ctk.CTkButton(center_actions_frame, text="Download Selected", width=150, height=40, font=("Arial", 14, "bold"), fg_color="#840284", hover_color="#6b016b", command=on_download_click).pack(side="left", padx=10)
ctk.CTkButton(center_actions_frame, text="Cancel Download", width=150, height=40, font=("Arial", 14, "bold"), fg_color="#FF6600", hover_color="#cc5200", command=on_cancel_download_click).pack(side="left", padx=10)

convert_action_frame = ctk.CTkFrame(center_actions_frame, fg_color="transparent")
convert_action_frame.pack(side="left")

convert_btn = ctk.CTkButton(convert_action_frame, text="Convert to MP4", width=150, height=40, font=("Arial", 14, "bold"), fg_color="#0086cc", hover_color="#006bb3", command=on_convert_click)
convert_btn.pack(side="left", padx=10)

stop_convert_btn = ctk.CTkButton(convert_action_frame, text="Stop Convert", width=150, height=40, font=("Arial", 14, "bold"), fg_color="#ff4444", hover_color="#cc0000", command=on_stop_convert_click)

app.mainloop()