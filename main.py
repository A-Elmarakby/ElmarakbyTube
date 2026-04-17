# Import necessary tools for the app to work
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

# Import our custom settings and messages files
import config
import messages
# ==================== NEW V2 UPDATES (Start) ====================
import json
import webbrowser
# ==================== NEW V2 UPDATES (End) ====================
# --- Window Setup ---
# Make the app dark, set its size, and give it a title
ctk.set_appearance_mode("Dark")
app = ctk.CTk()
app.geometry("1000x700")
app.title(config.APP_TITLE)

# Set the app icon
try:
    app.iconbitmap(default=config.ICON_FILE)
except:
    pass

# Global variables
# These remember the app's current state (e.g., is it downloading? converting?)
video_rows = []
is_fetching_sizes = False 
consecutive_errors = 0 
error_lock = threading.Lock()
is_downloading = False 
is_converting = False
current_ffmpeg_process = None

# Variables for the buttons so we can hide/show them later
convert_btn = None
stop_convert_btn = None

# --- Custom Logger ---
# This controls if we see yt-dlp text in the terminal or not based on config
class SilentLogger:
    def debug(self, msg): 
        if config.SHOW_TERMINAL_LOGS: print(msg)
    def warning(self, msg): 
        if config.SHOW_TERMINAL_LOGS: print(msg)
    def error(self, msg): 
        if config.SHOW_TERMINAL_LOGS: print(msg)

# ==================== Top Section ====================
# This area holds the Save Path and YouTube URL inputs

top_frame = ctk.CTkFrame(app, fg_color="transparent")
top_frame.pack(fill="x", padx=20, pady=20)

# Save Path input area
save_path_frame = ctk.CTkFrame(top_frame, fg_color="transparent")
save_path_frame.pack(side="left", fill="x", expand=True, padx=(0, 10))
ctk.CTkLabel(save_path_frame, text="Save Path:", font=(messages.FONT_FAMILY, messages.FONT_SIZE_MAIN, "bold")).pack(anchor="w")

path_input_layout = ctk.CTkFrame(save_path_frame, fg_color="transparent")
path_input_layout.pack(fill="x")
path_entry = ctk.CTkEntry(path_input_layout, placeholder_text="/Downloads/Playlists...")
path_entry.pack(side="left", fill="x", expand=True, padx=(0, 5))

# Function to open a window to choose a folder
def browse_save_path():
    folder_path = filedialog.askdirectory(title="Select Save Folder")
    if folder_path:
        path_entry.delete(0, 'end')
        path_entry.insert(0, folder_path)

ctk.CTkButton(path_input_layout, text="Browse", width=80, fg_color=config.COLOR_MAGENTA, hover_color=config.COLOR_MAGENTA_HOVER, command=browse_save_path).pack(side="left")

# YouTube URL input area
url_frame = ctk.CTkFrame(top_frame, fg_color="transparent")
url_frame.pack(side="left", fill="x", expand=True)
ctk.CTkLabel(url_frame, text="Video or Playlist URL:", font=(messages.FONT_FAMILY, messages.FONT_SIZE_MAIN, "bold")).pack(anchor="w")

url_input_layout = ctk.CTkFrame(url_frame, fg_color="transparent")
url_input_layout.pack(fill="x")
url_entry = ctk.CTkEntry(url_input_layout, placeholder_text="Paste your YouTube link here...")
url_entry.pack(side="left", fill="x", expand=True, padx=(0, 5))

# Function to make keyboard shortcuts (Copy, Paste, Select All) work
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
# Buttons to select/remove videos and show total size/time

toolbar_frame = ctk.CTkFrame(app, fg_color="transparent")
toolbar_frame.pack(fill="x", padx=20, pady=(0, 10))

ctk.CTkButton(toolbar_frame, text="Select All", width=90, fg_color="#333", hover_color="#444", command=lambda: toggle_all(True)).pack(side="left", padx=(0, 5))
ctk.CTkButton(toolbar_frame, text="Deselect All", width=90, fg_color="#333", hover_color="#444", command=lambda: toggle_all(False)).pack(side="left", padx=(0, 5))
ctk.CTkButton(toolbar_frame, text="Remove Selected", width=110, fg_color=config.COLOR_RED, hover_color=config.COLOR_RED_HOVER, command=lambda: remove_selected()).pack(side="left")

# Dashboard showing totals
dashboard_frame = ctk.CTkFrame(toolbar_frame, fg_color="transparent")
dashboard_frame.pack(side="left", padx=20)

ctk.CTkLabel(dashboard_frame, text="Total Time:", font=(messages.FONT_FAMILY, messages.FONT_SIZE_MAIN, "bold")).pack(side="left", padx=(0, 5))
total_time_label = ctk.CTkLabel(dashboard_frame, text="0s", font=(messages.FONT_FAMILY, messages.FONT_SIZE_MAIN, "bold"), text_color="#aaaaaa", width=80, anchor="w")
total_time_label.pack(side="left", padx=(0, 15))

ctk.CTkLabel(dashboard_frame, text="Total Size:", font=(messages.FONT_FAMILY, messages.FONT_SIZE_MAIN, "bold")).pack(side="left", padx=(0, 5))
total_size_label = ctk.CTkLabel(dashboard_frame, text="0.0 MB", font=(messages.FONT_FAMILY, messages.FONT_SIZE_MAIN, "bold"), text_color="#aaaaaa", width=80, anchor="w")
total_size_label.pack(side="left")

# Video quality selection and fetch buttons
quality_layout = ctk.CTkFrame(toolbar_frame, fg_color="transparent")
quality_layout.pack(side="right")

# Reset sizes when user changes the quality
def on_quality_change(choice):
    for row in video_rows:
        row['bytes_size'] = -1 
        safe_ui_update(row['size_label'], text="N/A", text_color="white")
    update_dynamic_totals()

# Start fetching sizes in the background
def on_fetch_sizes_click():
    threading.Thread(target=fetch_all_sizes_worker, daemon=True).start()

# Stop fetching sizes
def on_stop_fetch_click():
    global is_fetching_sizes
    is_fetching_sizes = False
    update_global_status("Stopping fetch... please wait.", "orange", "")

fetch_action_frame = ctk.CTkFrame(quality_layout, fg_color="transparent")
fetch_action_frame.pack(side="left", padx=(0, 10))

fetch_btn = ctk.CTkButton(fetch_action_frame, text="Fetch Sizes", width=90, fg_color=config.COLOR_CYAN, hover_color=config.COLOR_CYAN_HOVER, command=on_fetch_sizes_click)
fetch_btn.pack(side="left")

stop_fetch_btn = ctk.CTkButton(fetch_action_frame, text="Stop Fetch", width=90, fg_color=config.COLOR_RED, hover_color=config.COLOR_RED_HOVER, command=on_stop_fetch_click)

ctk.CTkLabel(quality_layout, text="Quality:").pack(side="left", padx=(0, 5))
quality_combo = ctk.CTkComboBox(quality_layout, values=["Waiting for link..."], width=130, command=on_quality_change)
quality_combo.set("Select Quality")
quality_combo.pack(side="left")

# ==================== Table Header ====================
# Column titles for the video list
header_frame = ctk.CTkFrame(app, fg_color="#1e1e1e", height=40, corner_radius=5)
header_frame.pack(fill="x", padx=20, pady=(0, 5))

ctk.CTkLabel(header_frame, text="", width=30).pack(side="left", padx=5)
ctk.CTkLabel(header_frame, text="#", width=30, font=(messages.FONT_FAMILY, messages.FONT_SIZE_MAIN, "bold")).pack(side="left", padx=(5, 0))
ctk.CTkLabel(header_frame, text="Video Title", width=250, anchor="w", font=(messages.FONT_FAMILY, messages.FONT_SIZE_MAIN, "bold")).pack(side="left")
ctk.CTkLabel(header_frame, text="Duration", width=70, font=(messages.FONT_FAMILY, messages.FONT_SIZE_MAIN, "bold")).pack(side="left")
ctk.CTkLabel(header_frame, text="Size", width=80, font=(messages.FONT_FAMILY, messages.FONT_SIZE_MAIN, "bold")).pack(side="left")
ctk.CTkLabel(header_frame, text="Status", width=100, font=(messages.FONT_FAMILY, messages.FONT_SIZE_MAIN, "bold")).pack(side="left")
ctk.CTkLabel(header_frame, text="Progress", width=120, font=(messages.FONT_FAMILY, messages.FONT_SIZE_MAIN, "bold")).pack(side="left", padx=(10, 5))
ctk.CTkLabel(header_frame, text="%", width=40, font=(messages.FONT_FAMILY, messages.FONT_SIZE_MAIN, "bold")).pack(side="left")

# ==================== List Area ====================
# The scrolling area where video rows appear
list_frame = ctk.CTkScrollableFrame(app, fg_color="#2b2b2b")
list_frame.pack(fill="both", expand=True, padx=20, pady=(0, 10))

# ==================== Status Bar ====================
# Text at the very bottom showing what the app is doing
status_bar = ctk.CTkFrame(app, height=30, fg_color="#1e1e1e", corner_radius=0)
status_bar.pack(fill="x", side="bottom")

global_status_label = ctk.CTkLabel(status_bar, text="Status: Ready", font=(messages.FONT_FAMILY, messages.FONT_SIZE_MAIN))
global_status_label.pack(side="left", padx=(20, 5))

global_warning_label = ctk.CTkLabel(status_bar, text="", font=(messages.FONT_FAMILY, messages.FONT_SIZE_MAIN, "bold"), text_color=config.COLOR_RED)
global_warning_label.pack(side="left")

# ==================== UI Safety Helpers ====================
# Safe ways to update text and progress bars without crashing the app
def safe_ui_update(widget, **kwargs):
    if widget and widget.winfo_exists():
        widget.configure(**kwargs)

def safe_progress_update(widget, value):
    if widget and widget.winfo_exists():
        widget.set(value)

# ==================== Core Functions & Custom Popups ====================
# Put windows exactly in the middle of the screen
def center_toplevel(top, width, height):
    app.update_idletasks()
    x = app.winfo_x() + (app.winfo_width() // 2) - (width // 2)
    y = app.winfo_y() + (app.winfo_height() // 2) - (height // 2)
    top.geometry(f"{width}x{height}+{x}+{y}")

# Our custom message box builder
def custom_msg_box(title, message, msg_type="error"):
    dialog = ctk.CTkToplevel(app)
    dialog.title(title)
    center_toplevel(dialog, config.POPUP_WIDTH, config.POPUP_HEIGHT)
    dialog.transient(app)
    dialog.grab_set()
    
    def apply_icon():
        try:
            dialog.iconbitmap(config.ICON_FILE)
        except:
            pass
    dialog.after(200, apply_icon)
    
    config.play_sound(msg_type)
    
    color = config.COLOR_RED 
    icon = "🛑"
    if msg_type == "warning":
        color = "#FFCC00" 
        icon = "⚠️"
    elif msg_type == "success":
        color = "#28a745"
        icon = "✅"
    elif msg_type == "info":
        color = config.COLOR_CYAN
        icon = "ℹ️"
        
    lbl_title = ctk.CTkLabel(dialog, text=f"{icon} {title}", font=(messages.FONT_FAMILY, messages.FONT_SIZE_POPUP_TITLE, "bold"), text_color=color)
    lbl_title.pack(pady=(20, 5))
    
    lbl_msg = ctk.CTkLabel(dialog, text=message, font=(messages.FONT_FAMILY, messages.FONT_SIZE_POPUP_BODY), wraplength=400)
    lbl_msg.pack(pady=(0, 20), padx=20)
    
    ctk.CTkButton(dialog, text=messages.BTN_OK, fg_color="#555", hover_color="#333", width=100, command=dialog.destroy).pack(pady=(0, 20))
    app.wait_window(dialog)

# Change raw bytes into readable text like MB or GB
def format_size(bytes_size):
    if bytes_size <= 0: return "0.0 MB"
    mb = bytes_size / (1024 * 1024)
    if mb >= 1000:
        gb = mb / 1024
        return f"{gb:.2f} GB"
    return f"{mb:.1f} MB"

# Change the text at the bottom bar
def update_global_status(msg, color="white", warning_msg=""):
    global_status_label.configure(text=f"Status: {msg}", text_color=color)
    global_warning_label.configure(text=warning_msg)

# Calculate the total time and size of selected videos
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

# Check or uncheck all boxes
def toggle_all(state):
    for row_data in video_rows:
        if state: row_data["checkbox"].select()
        else: row_data["checkbox"].deselect()
    update_dynamic_totals()

# Delete selected videos from the list
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

# Change seconds to mm:ss format
def format_duration(seconds):
    if not seconds: return "00:00"
    m, s = divmod(int(seconds), 60)
    h, m = divmod(m, 60)
    if h > 0: return f"{h}:{m:02d}:{s:02d}"
    return f"{m:02d}:{s:02d}"

# Remove all videos from the list
def clear_list():
    global video_rows
    for widget in list_frame.winfo_children():
        widget.destroy()
    video_rows.clear()
    update_dynamic_totals()

# Draw a single video row on the screen
def add_video_row(index, title, duration, vid_url, status="Ready", status_color="#28a745"):
    row = ctk.CTkFrame(list_frame, fg_color="#333333", height=50)
    row.pack(side="top", fill="x", pady=2, anchor="n") 
    
    cb = ctk.CTkCheckBox(row, text="", width=30, command=update_dynamic_totals)
    cb.select()
    cb.pack(side="left", padx=5)

    ctk.CTkLabel(row, text=str(index), width=30).pack(side="left", padx=(5, 0))
    
    title_entry = ctk.CTkEntry(row, width=250, fg_color="transparent", border_width=0, text_color="white", font=(messages.FONT_FAMILY, messages.FONT_SIZE_MAIN))
    title_entry.insert(0, title)
    title_entry.configure(state="readonly")
    title_entry.pack(side="left")

    ctk.CTkLabel(row, text=duration, width=70).pack(side="left")
    
    size_lbl = ctk.CTkLabel(row, text="N/A", width=80)
    size_lbl.pack(side="left")
    
    status_lbl = ctk.CTkLabel(row, text=status, text_color=status_color, width=100)
    status_lbl.pack(side="left")
    
    prog_bar = ctk.CTkProgressBar(row, width=120, progress_color=config.COLOR_MAGENTA)
    prog_bar.set(0)
    prog_bar.pack(side="left", padx=(10, 5))
    
    percent_lbl = ctk.CTkLabel(row, text="0%", width=40, font=(messages.FONT_FAMILY, messages.FONT_SIZE_MAIN))
    percent_lbl.pack(side="left")

    # Save video data in our dictionary, including a hidden pocket for errors
    row_data = {
        "frame": row, "checkbox": cb, "title": title, 
        "duration": duration, "progress": prog_bar, 
        "size_label": size_lbl, "status_label": status_lbl,
        "percent_label": percent_lbl,
        "url": vid_url,
        "bytes_size": -1,
        "dl_state": "ready",
        "error_msg": "" # Hidden pocket for errors
    }
    video_rows.append(row_data)

    # Show error details when user clicks on a failed status
    def on_status_click(event, r=row_data):
        if r['dl_state'] == 'failed' and r['error_msg']:
            custom_msg_box(messages.TITLE_ERROR_DETAILS, r['error_msg'], "error")

    status_lbl.bind("<Button-1>", on_status_click)

# ==================== Size Calculation Engine ====================
# Generate the right format string for yt-dlp based on user choice
def get_ydl_format_string(quality):
    if "Audio Only" in quality: return 'bestaudio/best'
    if "Medium" in quality or "720" in quality: return 'bestvideo[height<=720]+bestaudio/best'
    if "Low" in quality or "480" in quality: return 'bestvideo[height<=480]+bestaudio/best'
    height = ''.join(filter(str.isdigit, quality))
    if height: return f'bestvideo[height<={height}]+bestaudio/best'
    return 'bestvideo+bestaudio/best'

# Get the size of one video from YouTube
def fetch_size_for_single_video(row_data, quality):
    global is_fetching_sizes, consecutive_errors
    
    if not is_fetching_sizes: return 
    if not row_data['frame'].winfo_exists(): return
    if row_data['bytes_size'] != -1: return 

    app.after(0, lambda: safe_ui_update(row_data['size_label'], text="...", text_color=config.COLOR_CYAN))

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
                app.after(0, lambda: safe_ui_update(row_data['size_label'], text="Blocked", text_color=config.COLOR_RED))
                with error_lock:
                    consecutive_errors += 1
                    if consecutive_errors >= config.MAX_CONSECUTIVE_ERRORS:
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
        app.after(0, lambda: safe_ui_update(row_data['size_label'], text="Error", text_color=config.COLOR_RED))
        with error_lock:
            consecutive_errors += 1
            if consecutive_errors >= config.MAX_CONSECUTIVE_ERRORS:
                is_fetching_sizes = False 
    
    app.after(0, update_dynamic_totals)

# Manage multiple threads to fetch sizes fast
def fetch_all_sizes_worker():
    global is_fetching_sizes, consecutive_errors
    
    quality = quality_combo.get()
    if quality in ["Select Quality", "Waiting for link...", "Loading..."]:
        app.after(0, lambda: custom_msg_box(messages.TITLE_WARNING, messages.MSG_QUALITY_MISSING, "warning"))
        return
        
    selected_rows = [r for r in video_rows if r["checkbox"].get() == 1]
    if not selected_rows:
        app.after(0, lambda: custom_msg_box(messages.TITLE_WARNING, messages.MSG_NO_VIDEO_FETCH, "warning"))
        return

    consecutive_errors = 0
    is_fetching_sizes = True
    app.after(0, lambda: update_global_status(f"Fetching sizes for {quality}...", config.COLOR_CYAN, ""))
    
    global fetch_btn, stop_fetch_btn
    app.after(0, lambda: fetch_btn.pack_forget() if 'fetch_btn' in globals() else None)
    app.after(0, lambda: stop_fetch_btn.pack(side="left") if 'stop_fetch_btn' in globals() else None)

    with concurrent.futures.ThreadPoolExecutor(max_workers=config.MAX_THREADS) as executor:
        futures = [executor.submit(fetch_size_for_single_video, row, quality) for row in selected_rows]
        concurrent.futures.wait(futures)

    app.after(0, lambda: stop_fetch_btn.pack_forget() if 'stop_fetch_btn' in globals() else None)
    app.after(0, lambda: fetch_btn.pack(side="left") if 'fetch_btn' in globals() else None)
    
    if consecutive_errors >= config.MAX_CONSECUTIVE_ERRORS:
        app.after(0, lambda: update_global_status("Fetching stopped automatically: YouTube blocked the connection.", config.COLOR_RED, ""))
        app.after(0, lambda: custom_msg_box(messages.TITLE_ERROR, messages.MSG_BLOCKED, "error"))
    elif is_fetching_sizes:
        blocked_count = sum(1 for r in selected_rows if r['bytes_size'] == 0)
        if blocked_count > 0:
            app.after(0, lambda: update_global_status("Sizes fetched.", "#28a745", f"({blocked_count} video(s) might be blocked or failed)"))
        else:
            app.after(0, lambda: update_global_status("All sizes fetched successfully.", "#28a745", ""))
    else:
        app.after(0, lambda: update_global_status("Fetching stopped by user.", "orange", ""))
        
    is_fetching_sizes = False

# Draw videos on screen in groups so the app doesn't freeze
def render_chunk(entries_data, current_idx, qualities, chunk_size=config.RENDER_CHUNK_SIZE):
    end_idx = min(current_idx + chunk_size, len(entries_data))
    
    for i in range(current_idx, end_idx):
        data = entries_data[i]
        add_video_row(data['idx'], data['title'], data['dur'], data['url'])
        
    app.after(0, lambda: update_global_status(f"Rendering videos... ({end_idx}/{len(entries_data)})", config.COLOR_CYAN, ""))

    if end_idx < len(entries_data):
        app.after(10, lambda: render_chunk(entries_data, end_idx, qualities, chunk_size))
    else:
        quality_combo.configure(values=qualities)
        if qualities: quality_combo.set(qualities[0])
        app.after(0, update_dynamic_totals) 
        app.after(0, lambda: update_global_status("Data fetched successfully. Ready to use.", "#28a745", ""))

# Search YouTube link and get videos
def fetch_video_data():
    url = url_entry.get()
    if not url:
        app.after(0, lambda: custom_msg_box(messages.TITLE_ERROR, messages.MSG_URL_MISSING, "error"))
        return

    app.after(0, clear_list)
    app.after(0, lambda: update_global_status("Connecting to YouTube... Please wait.", config.COLOR_CYAN, ""))
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
        app.after(0, lambda: update_global_status("Search Failed.", config.COLOR_RED, ""))
        app.after(0, lambda e=e: custom_msg_box(messages.TITLE_ERROR, messages.MSG_CONN_ERROR, "error"))

# Start searching when button is clicked
def on_search_click():
    threading.Thread(target=fetch_video_data, daemon=True).start()

ctk.CTkButton(url_input_layout, text="🔍", width=40, fg_color=config.COLOR_MAGENTA, hover_color=config.COLOR_MAGENTA_HOVER, command=on_search_click).pack(side="left")

# Check if a video is already on the computer
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

# The main function to download files
def _download_process(rows_to_download, quality, save_path):
    global is_downloading
    format_str = get_ydl_format_string(quality)
    postprocessors = []
    if "Audio Only" in quality:
        postprocessors = [{'key': 'FFmpegExtractAudio', 'preferredcodec': 'mp3', 'preferredquality': config.AUDIO_BITRATE}]

    for row_data in rows_to_download:
        if not is_downloading: break 
        if not row_data['frame'].winfo_exists(): continue 
        
        row_data['dl_state'] = 'preparing'
        app.after(0, lambda r=row_data: safe_ui_update(r['status_label'], text="Preparing...", text_color=config.COLOR_MAGENTA))
        
        # Look for messages saying file already exists and print logs if enabled
        class DownloadLogger:
            def debug(self, msg):
                if config.SHOW_TERMINAL_LOGS: print(msg)
                if "has already been downloaded" in msg or "already exists" in msg:
                    row_data['dl_state'] = 'already_exists'
                    app.after(0, lambda r=row_data: safe_ui_update(r['status_label'], text="Already Exists", text_color="#28a745"))
                    app.after(0, lambda r=row_data: safe_progress_update(r['progress'], 1.0))
                    app.after(0, lambda r=row_data: safe_ui_update(r['percent_label'], text="100%", text_color="#28a745"))
            def warning(self, msg): 
                if config.SHOW_TERMINAL_LOGS: print(msg)
            def error(self, msg): 
                if config.SHOW_TERMINAL_LOGS: print(msg)

        # Update progress bar during download
        def progress_hook(d, r=row_data):
            global is_downloading
            if not is_downloading:
                raise ValueError("DOWNLOAD_CANCELLED")
                
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
                        app.after(0, lambda: safe_ui_update(r['status_label'], text="Downloading...", text_color=config.COLOR_MAGENTA))
            
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
                
        # Catch the error, save it in the hidden pocket, and change cursor to hand
        except Exception as e:
            if not is_downloading:
                pass 
            else:
                row_data['dl_state'] = 'failed'
                row_data['error_msg'] = str(e)
                app.after(0, lambda r=row_data: safe_ui_update(r['status_label'], text="Failed", text_color=config.COLOR_RED, cursor="hand2"))

# Start the download background task
def download_worker():
    global is_downloading
    save_path = path_entry.get()
    
    if not save_path or not os.path.isdir(save_path):
        app.after(0, lambda: custom_msg_box(messages.TITLE_ERROR, messages.MSG_INVALID_PATH, "error"))
        return

    selected_rows = [r for r in video_rows if r["checkbox"].get() == 1]
    if not selected_rows:
        app.after(0, lambda: custom_msg_box(messages.TITLE_WARNING, messages.MSG_NO_VIDEO_DL, "warning"))
        return

    quality = quality_combo.get()
    if quality in ["Select Quality", "Waiting for link...", "Loading..."]:
        app.after(0, lambda: custom_msg_box(messages.TITLE_WARNING, messages.MSG_QUALITY_MISSING, "warning"))
        return

    is_downloading = True
    app.after(0, lambda: update_global_status(f"Starting download for {len(selected_rows)} videos...", config.COLOR_MAGENTA, ""))

    _download_process(selected_rows, quality, save_path)

    # Check for errors and show final status without playing sounds
    if is_downloading:
        failed_count = sum(1 for r in selected_rows if r.get('dl_state') == 'failed')
        if failed_count > 0:
            app.after(0, lambda: update_global_status(f"Finished with {failed_count} errors. Click 'Failed' in the list to see why.", "orange", ""))
        else:
            app.after(0, lambda: update_global_status("Downloads finished successfully.", "#28a745", ""))
    else:
        app.after(0, lambda: update_global_status("Downloads canceled by user.", "orange", ""))
        
    is_downloading = False

# Ask user if they want fast or slow conversion
def ask_conversion_speed():
    dialog = ctk.CTkToplevel(app)
    dialog.title(messages.TITLE_SPEED)
    center_toplevel(dialog, 350, 150)
    dialog.transient(app) 
    dialog.grab_set() 
    
    def apply_icon():
        try:
            dialog.iconbitmap(config.ICON_FILE)
        except:
            pass
    dialog.after(200, apply_icon)
    
    config.play_sound("info")
    result = ["cancel"] 
    def set_res(val):
        result[0] = val
        dialog.destroy()
        
    lbl = ctk.CTkLabel(dialog, text=messages.MSG_SPEED_PROMPT, font=(messages.FONT_FAMILY, messages.FONT_SIZE_LARGE, "bold"))
    lbl.pack(pady=20)
    
    btn_frame = ctk.CTkFrame(dialog, fg_color="transparent")
    btn_frame.pack()
    
    ctk.CTkButton(btn_frame, text=messages.BTN_FAST, fg_color="#28a745", hover_color="#218838", width=90, command=lambda: set_res("fast")).pack(side="left", padx=10)
    ctk.CTkButton(btn_frame, text=messages.BTN_SLOW, fg_color=config.COLOR_RED, hover_color=config.COLOR_RED_HOVER, width=90, command=lambda: set_res("slow")).pack(side="left", padx=10)
    ctk.CTkButton(btn_frame, text=messages.BTN_CANCEL, fg_color="#555", hover_color="#333", width=90, command=lambda: set_res("cancel")).pack(side="left", padx=10)
    
    app.wait_window(dialog)
    return result[0]

# Ask user a Yes or No question
def custom_ask_yes_no(title, message, icon="⚠️"):
    dialog = ctk.CTkToplevel(app)
    dialog.title(title)
    center_toplevel(dialog, config.POPUP_WIDTH, config.POPUP_HEIGHT)
    dialog.transient(app)
    dialog.grab_set()
    
    def apply_icon():
        try:
            dialog.iconbitmap(config.ICON_FILE)
        except:
            pass
    dialog.after(200, apply_icon)
    
    config.play_sound("warning")
    result = [False]
    def set_res(val):
        result[0] = val
        dialog.destroy()
        
    lbl = ctk.CTkLabel(dialog, text=f"{icon} {message}", font=(messages.FONT_FAMILY, messages.FONT_SIZE_LARGE, "bold"), wraplength=400)
    lbl.pack(pady=20, padx=20)
    
    btn_frame = ctk.CTkFrame(dialog, fg_color="transparent")
    btn_frame.pack()
    
    ctk.CTkButton(btn_frame, text=messages.BTN_YES, fg_color="#28a745", hover_color="#218838", width=90, command=lambda: set_res(True)).pack(side="left", padx=10)
    ctk.CTkButton(btn_frame, text=messages.BTN_NO, fg_color=config.COLOR_RED, hover_color=config.COLOR_RED_HOVER, width=90, command=lambda: set_res(False)).pack(side="left", padx=10)
    
    app.wait_window(dialog)
    return result[0]

# The main function to convert files to MP4 using FFmpeg
def convert_worker(speed_choice, selected_rows, save_path, quality, do_download_first):
    global is_converting, current_ffmpeg_process
    
    # Download files first if needed
    if do_download_first:
        global is_downloading
        is_downloading = True
        app.after(0, lambda: update_global_status("Downloading missing files...", config.COLOR_MAGENTA, ""))
        _download_process(selected_rows, quality, save_path)
        is_downloading = False
        
        if not is_converting: 
            app.after(0, lambda: update_global_status("Conversion canceled.", "orange", ""))
            return
            
    # Hide Convert button and show Stop button
    global convert_btn, stop_convert_btn
    app.after(0, lambda: convert_btn.pack_forget() if 'convert_btn' in globals() else None)
    app.after(0, lambda: stop_convert_btn.pack(side="left", padx=10) if 'stop_convert_btn' in globals() else None)
    
    files_to_delete = []
    app.after(0, lambda: update_global_status("Starting conversion...", config.COLOR_CYAN, ""))
    
    for row_data in selected_rows:
        if not is_converting: break 
        if not row_data['frame'].winfo_exists(): continue 
        
        input_file = find_downloaded_file(save_path, row_data['title'])
        if not input_file:
            row_data['dl_state'] = 'failed'
            row_data['error_msg'] = "File not found in the save path."
            app.after(0, lambda r=row_data: safe_ui_update(r['status_label'], text="Failed", text_color=config.COLOR_RED, cursor="hand2"))
            continue
            
        if input_file.endswith(('.mp4')):
            app.after(0, lambda r=row_data: safe_ui_update(r['status_label'], text="Already MP4", text_color="#28a745"))
            app.after(0, lambda r=row_data: safe_progress_update(r['progress'], 1.0))
            app.after(0, lambda r=row_data: safe_ui_update(r['percent_label'], text="100%", text_color="#28a745"))
            continue
            
        if input_file.endswith(('.mp3', '.m4a', '.wav')):
            app.after(0, lambda r=row_data: safe_ui_update(r['status_label'], text="Audio File", text_color="#28a745"))
            app.after(0, lambda r=row_data: safe_progress_update(r['progress'], 1.0))
            app.after(0, lambda r=row_data: safe_ui_update(r['percent_label'], text="100%", text_color="#28a745"))
            continue
            
        output_file = os.path.splitext(input_file)[0] + '.mp4'
        
        app.after(0, lambda r=row_data: safe_ui_update(r['status_label'], text="Converting...", text_color=config.COLOR_CYAN))
        app.after(0, lambda r=row_data: safe_ui_update(r['percent_label'], text="---", text_color=config.COLOR_CYAN))
        app.after(0, lambda r=row_data: r['progress'].configure(mode="indeterminate", progress_color=config.COLOR_CYAN))
        app.after(0, lambda r=row_data: r['progress'].start())
        
        update_status_msg = "Remuxing" if speed_choice == "fast" else "Re-encoding"
        app.after(0, lambda: update_global_status(f"Converting ({update_status_msg})...", config.COLOR_CYAN, ""))
        
        # Build FFmpeg command
        cmd = [imageio_ffmpeg.get_ffmpeg_exe(), '-y', '-i', input_file]
        if speed_choice == "fast":
            cmd.extend(['-c', 'copy'])
        else:
            cmd.extend(['-c:v', 'libx264', '-preset', 'fast', '-c:a', 'aac'])
        cmd.append(output_file)
        
        # Run FFmpeg
        try:
            current_ffmpeg_process = subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            current_ffmpeg_process.wait() 
            
            if not is_converting: 
                raise Exception("KILLED_BY_USER")
                
            if current_ffmpeg_process.returncode != 0:
                raise Exception("FFMPEG_ERROR: Something went wrong during conversion.")
            
            app.after(0, lambda r=row_data: r['progress'].stop())
            app.after(0, lambda r=row_data: r['progress'].configure(mode="determinate", progress_color=config.COLOR_MAGENTA))
            app.after(0, lambda r=row_data: safe_progress_update(r['progress'], 1.0))
            app.after(0, lambda r=row_data: safe_ui_update(r['percent_label'], text="100%", text_color="#28a745"))
            app.after(0, lambda r=row_data: safe_ui_update(r['status_label'], text="Converted", text_color="#28a745"))
            
            files_to_delete.append(input_file)
        except Exception as e:
            app.after(0, lambda r=row_data: r['progress'].stop())
            app.after(0, lambda r=row_data: r['progress'].configure(mode="determinate", progress_color=config.COLOR_MAGENTA))
            if not is_converting:
                app.after(0, lambda r=row_data: safe_ui_update(r['status_label'], text="Canceled", text_color=config.COLOR_RED))
                app.after(0, lambda r=row_data: safe_progress_update(r['progress'], 0))
                app.after(0, lambda r=row_data: safe_ui_update(r['percent_label'], text="0%", text_color=config.COLOR_RED))
            else:
                row_data['dl_state'] = 'failed'
                row_data['error_msg'] = str(e)
                app.after(0, lambda r=row_data: safe_ui_update(r['status_label'], text="Failed", text_color=config.COLOR_RED, cursor="hand2"))
        finally:
            current_ffmpeg_process = None
            
    # Show Convert button again
    app.after(0, lambda: stop_convert_btn.pack_forget() if 'stop_convert_btn' in globals() else None)
    app.after(0, lambda: convert_btn.pack(side="left", padx=10) if 'convert_btn' in globals() else None)
    
    # Check for errors and show final status without playing sounds
    if is_converting:
        failed_count = sum(1 for r in selected_rows if r.get('dl_state') == 'failed')
        if failed_count > 0:
            app.after(0, lambda: update_global_status(f"Finished with {failed_count} errors. Click 'Failed' in the list to see why.", "orange", ""))
        else:
            app.after(0, lambda: update_global_status("All conversions completed successfully.", "#28a745", ""))
            
        if files_to_delete:
            def ask_cleanup():
                if custom_ask_yes_no(messages.TITLE_CONFIRM, messages.MSG_CLEANUP):
                    for f in files_to_delete:
                        try: os.remove(f)
                        except: pass
                    update_global_status("Conversion complete. Old files deleted.", "#28a745", "")
            app.after(0, ask_cleanup)
    else:
        app.after(0, lambda: update_global_status("Conversion stopped by user.", "orange", ""))

# ==================== Bottom Actions ====================
# The main big buttons at the bottom of the app

bottom_frame = ctk.CTkFrame(app, fg_color="transparent")
bottom_frame.pack(pady=10, side="bottom") 

center_actions_frame = ctk.CTkFrame(bottom_frame, fg_color="transparent")
center_actions_frame.pack()

# Start download
def on_download_click():
    threading.Thread(target=download_worker, daemon=True).start()

# Cancel download
def on_cancel_download_click():
    global is_downloading
    if is_downloading:
        is_downloading = False
        update_global_status("Canceling download... please wait.", "orange", "")
        for r in video_rows:
            if r.get('dl_state') in ['preparing', 'downloading']:
                r['dl_state'] = 'canceled'
                safe_ui_update(r['status_label'], text="Canceled", text_color=config.COLOR_RED)
                safe_progress_update(r['progress'], 0)
                safe_ui_update(r['percent_label'], text="0%", text_color=config.COLOR_RED)

# Start conversion
def on_convert_click():
    global is_converting
    save_path = path_entry.get()
    if not save_path or not os.path.isdir(save_path):
        custom_msg_box(messages.TITLE_ERROR, messages.MSG_INVALID_PATH, "error")
        return

    selected_rows = [r for r in video_rows if r["checkbox"].get() == 1]
    if not selected_rows:
        custom_msg_box(messages.TITLE_WARNING, messages.MSG_NO_VIDEO_CONV, "warning")
        return
        
    quality = quality_combo.get()
    if quality in ["Select Quality", "Waiting for link...", "Loading..."]:
        custom_msg_box(messages.TITLE_WARNING, messages.MSG_QUALITY_MISSING, "warning")
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
        dl_choice = custom_ask_yes_no(messages.TITLE_WARNING, messages.MSG_DL_REQUIRED, icon="⚠️")
        if not dl_choice:
            update_global_status("Conversion canceled by user.", "orange", "")
            return
        do_download_first = True
        
    is_converting = True
    threading.Thread(target=convert_worker, args=(speed_choice, selected_rows, save_path, quality, do_download_first), daemon=True).start()

# Stop conversion
def on_stop_convert_click():
    global is_converting, current_ffmpeg_process
    is_converting = False
    if current_ffmpeg_process:
        try: current_ffmpeg_process.terminate()
        except: pass
    update_global_status("Stopping conversion... please wait.", "orange", "")

# Draw the bottom buttons
ctk.CTkButton(center_actions_frame, text="Download Selected", width=150, height=40, font=(messages.FONT_FAMILY, messages.FONT_SIZE_LARGE, "bold"), fg_color=config.COLOR_MAGENTA, hover_color=config.COLOR_MAGENTA_HOVER, command=on_download_click).pack(side="left", padx=10)
ctk.CTkButton(center_actions_frame, text="Cancel Download", width=150, height=40, font=(messages.FONT_FAMILY, messages.FONT_SIZE_LARGE, "bold"), fg_color=config.COLOR_RED, hover_color=config.COLOR_RED_HOVER, command=on_cancel_download_click).pack(side="left", padx=10)

convert_action_frame = ctk.CTkFrame(center_actions_frame, fg_color="transparent")
convert_action_frame.pack(side="left")

convert_btn = ctk.CTkButton(convert_action_frame, text="Convert to MP4", width=150, height=40, font=(messages.FONT_FAMILY, messages.FONT_SIZE_LARGE, "bold"), fg_color=config.COLOR_CYAN, hover_color=config.COLOR_CYAN_HOVER, command=on_convert_click)
convert_btn.pack(side="left", padx=10)

stop_convert_btn = ctk.CTkButton(convert_action_frame, text="Stop Convert", width=150, height=40, font=(messages.FONT_FAMILY, messages.FONT_SIZE_LARGE, "bold"), fg_color=config.COLOR_RED, hover_color=config.COLOR_RED_HOVER, command=on_stop_convert_click)

# ==================== V2 Features: Contact, Onboarding, Exit ====================

# 1. Contact Us Button & Popup
def show_contact_popup():
    dialog = ctk.CTkToplevel(app)
    dialog.title("Contact Us")
    center_toplevel(dialog, 400, 250)
    dialog.transient(app)
    dialog.grab_set()
    
    lbl = ctk.CTkLabel(dialog, text=messages.MSG_CONTACT_WHERE, font=(messages.FONT_FAMILY, messages.FONT_SIZE_POPUP_TITLE, "bold"))
    lbl.pack(pady=(20, 15))
    
    btn_frame = ctk.CTkFrame(dialog, fg_color="transparent")
    btn_frame.pack()
    
    # Create contact buttons that open browser links
    ctk.CTkButton(btn_frame, text="LinkedIn", fg_color="#0077b5", hover_color="#005582", width=120, command=lambda: webbrowser.open(messages.URL_LINKEDIN)).grid(row=0, column=0, padx=10, pady=10)
    ctk.CTkButton(btn_frame, text="WhatsApp", fg_color="#25D366", hover_color="#1DA851", width=120, command=lambda: webbrowser.open(messages.URL_WHATSAPP)).grid(row=0, column=1, padx=10, pady=10)
    ctk.CTkButton(btn_frame, text="GitHub", fg_color="#333", hover_color="#111", width=120, command=lambda: webbrowser.open(messages.URL_GITHUB)).grid(row=1, column=0, padx=10, pady=10)
    ctk.CTkButton(btn_frame, text="Email", fg_color=config.COLOR_CYAN, hover_color=config.COLOR_CYAN_HOVER, width=120, command=lambda: webbrowser.open(messages.URL_EMAIL)).grid(row=1, column=1, padx=10, pady=10)

# Create the button at the bottom right corner
contact_btn = ctk.CTkButton(app, text=messages.BTN_CONTACT_US, fg_color=config.COLOR_MAGENTA, hover_color=config.COLOR_MAGENTA_HOVER, command=show_contact_popup, corner_radius=20)
contact_btn.place(relx=0.98, rely=0.98, anchor="se")

# Animate the button slightly to catch attention (Pulse Effect)
def pulse_contact_button():
    contact_btn.configure(fg_color=config.COLOR_CYAN) # Change to Cyan
    app.after(400, lambda: contact_btn.configure(fg_color=config.COLOR_MAGENTA)) # Back to Magenta quickly
    app.after(config.CONTACT_PULSE_INTERVAL, pulse_contact_button) # Repeat based on config

app.after(config.CONTACT_PULSE_INTERVAL, pulse_contact_button)

# 2. Smart Exit Confirmation
def custom_exit_dialog(title, message, green_text, red_text):
    dialog = ctk.CTkToplevel(app)
    dialog.title(title)
    center_toplevel(dialog, 450, 200)
    dialog.transient(app)
    dialog.grab_set()
    
    config.play_sound("warning")
    result = ["cancel"]
    def set_res(val):
        result[0] = val
        dialog.destroy()
        
    lbl = ctk.CTkLabel(dialog, text=message, font=(messages.FONT_FAMILY, messages.FONT_SIZE_LARGE, "bold"), wraplength=400)
    lbl.pack(pady=30, padx=20)
    
    btn_frame = ctk.CTkFrame(dialog, fg_color="transparent")
    btn_frame.pack()
    
    ctk.CTkButton(btn_frame, text=green_text, fg_color="#28a745", hover_color="#218838", command=lambda: set_res("stay")).pack(side="left", padx=10)
    ctk.CTkButton(btn_frame, text=red_text, fg_color=config.COLOR_RED, hover_color=config.COLOR_RED_HOVER, command=lambda: set_res("leave")).pack(side="left", padx=10)
    
    app.wait_window(dialog)
    return result[0]

def on_closing():
    # First friendly prompt
    choice = custom_exit_dialog(messages.TITLE_EXIT, messages.MSG_EXIT_ASK, messages.BTN_STAY, messages.BTN_LEAVE)
    
    if choice == "leave":
        # Check if app is busy doing work
        if is_downloading or is_converting or is_fetching_sizes:
            warn_choice = custom_exit_dialog(messages.TITLE_EXIT_WARN, messages.MSG_EXIT_WARN, messages.BTN_WAIT, messages.BTN_FORCE_QUIT)
            if warn_choice == "leave": # User clicked BTN_FORCE_QUIT (the red button)
                app.destroy()
        else:
            app.destroy()

# Tell the app to run on_closing() when the X button is clicked
app.protocol("WM_DELETE_WINDOW", on_closing)

# 3. Welcome Onboarding Popup
def show_welcome_onboarding():
    data_file = "user_data.json"
    
    # Stop if we already know the user
    if os.path.exists(data_file):
        return

    dialog = ctk.CTkToplevel(app)
    dialog.title(messages.TITLE_WELCOME)
    center_toplevel(dialog, 400, 200)
    dialog.transient(app)
    dialog.grab_set()
    
    # Disable the standard close window 'X' button so they MUST enter a name
    dialog.protocol("WM_DELETE_WINDOW", lambda: None)
    
    lbl = ctk.CTkLabel(dialog, text=messages.MSG_WELCOME_ASK, font=(messages.FONT_FAMILY, messages.FONT_SIZE_LARGE, "bold"))
    lbl.pack(pady=(30, 10))
    
    name_entry = ctk.CTkEntry(dialog, placeholder_text=messages.PLACEHOLDER_NAME, width=200, justify="center")
    name_entry.pack(pady=10)
    
    def save_name():
        name = name_entry.get().strip()
        if name:
            with open(data_file, "w", encoding="utf-8") as f:
                json.dump({"name": name}, f)
            dialog.destroy()
            
            # Show the second friendly greeting popup
            greet_msg = messages.MSG_WELCOME_GREET.replace("{name}", name)
            custom_msg_box(messages.TITLE_WELCOME, greet_msg, "success")
            
    ctk.CTkButton(dialog, text=messages.BTN_CONFIRM_NAME, fg_color=config.COLOR_MAGENTA, hover_color=config.COLOR_MAGENTA_HOVER, command=save_name).pack(pady=10)

# Run the onboarding check a split second after the app opens
app.after(500, show_welcome_onboarding)

# Keep the window running
app.mainloop()