import customtkinter as ctk
import yt_dlp
import threading

# --- Window Setup ---
ctk.set_appearance_mode("Dark")
app = ctk.CTk()
app.geometry("950x700")
app.title("ElmarakbyTube Downloader")

video_rows = []

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
ctk.CTkButton(path_input_layout, text="Browse", width=80, fg_color="#840284", hover_color="#6b016b").pack(side="left")

url_frame = ctk.CTkFrame(top_frame, fg_color="transparent")
url_frame.pack(side="left", fill="x", expand=True)
ctk.CTkLabel(url_frame, text="Video or Playlist URL:", font=("Arial", 12, "bold")).pack(anchor="w")

url_input_layout = ctk.CTkFrame(url_frame, fg_color="transparent")
url_input_layout.pack(fill="x")
url_entry = ctk.CTkEntry(url_input_layout, placeholder_text="Paste your YouTube link here...")
url_entry.pack(side="left", fill="x", expand=True, padx=(0, 5))

# --- Hardware shortcuts fix ---
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

calc_frame = ctk.CTkFrame(toolbar_frame, fg_color="transparent")
calc_frame.pack(side="left", padx=20)
ctk.CTkButton(calc_frame, text="Calc Time", width=80, fg_color="#FF6600", hover_color="#cc5200", command=lambda: calculate_total_time()).pack(side="left", padx=(0, 5))
total_time_label = ctk.CTkLabel(calc_frame, text="0h 0m 0s", font=("Arial", 12, "bold"), text_color="#aaaaaa")
total_time_label.pack(side="left")

quality_layout = ctk.CTkFrame(toolbar_frame, fg_color="transparent")
quality_layout.pack(side="right")
ctk.CTkLabel(quality_layout, text="Quality:").pack(side="left", padx=(0, 10))
quality_combo = ctk.CTkComboBox(quality_layout, values=["Waiting for link..."], width=150)
quality_combo.set("Select Quality")
quality_combo.pack(side="left")

# ==================== Table Header ====================
header_frame = ctk.CTkFrame(app, fg_color="#1e1e1e", height=40, corner_radius=5)
header_frame.pack(fill="x", padx=20, pady=(0, 5))

ctk.CTkLabel(header_frame, text="", width=30).pack(side="left", padx=5)
ctk.CTkLabel(header_frame, text="#", width=30, font=("Arial", 12, "bold")).pack(side="left", padx=(5, 0))
ctk.CTkLabel(header_frame, text="Video Title", width=270, anchor="w", font=("Arial", 12, "bold")).pack(side="left")
ctk.CTkLabel(header_frame, text="Duration", width=80, font=("Arial", 12, "bold")).pack(side="left")
ctk.CTkLabel(header_frame, text="Size", width=80, font=("Arial", 12, "bold")).pack(side="left")
ctk.CTkLabel(header_frame, text="Status", width=100, font=("Arial", 12, "bold")).pack(side="left")
ctk.CTkLabel(header_frame, text="Progress", width=150, font=("Arial", 12, "bold")).pack(side="left", padx=10)

# ==================== List Area ====================
list_frame = ctk.CTkScrollableFrame(app, fg_color="#2b2b2b")
list_frame.pack(fill="both", expand=True, padx=20, pady=(0, 10))

# ==================== Status Bar ====================
status_bar = ctk.CTkFrame(app, height=30, fg_color="#1e1e1e", corner_radius=0)
status_bar.pack(fill="x", side="bottom")

global_status_label = ctk.CTkLabel(status_bar, text="Status: Ready", font=("Arial", 12))
global_status_label.pack(side="left", padx=20)

# ==================== Bottom Section ====================
bottom_frame = ctk.CTkFrame(app, fg_color="transparent")
bottom_frame.pack(pady=10, side="bottom")

ctk.CTkButton(bottom_frame, text="Download Selected", width=150, height=40, font=("Arial", 14, "bold"), fg_color="#840284", hover_color="#6b016b").pack(side="left", padx=10)
ctk.CTkButton(bottom_frame, text="Cancel Download", width=150, height=40, font=("Arial", 14, "bold"), fg_color="#FF6600", hover_color="#cc5200").pack(side="left", padx=10)

# ==================== Functions ====================

def update_global_status(msg, color="white"):
    global_status_label.configure(text=f"Status: {msg}", text_color=color)

def toggle_all(state):
    for row_data in video_rows:
        if state: row_data["checkbox"].select()
        else: row_data["checkbox"].deselect()

def remove_selected():
    global video_rows
    for row_data in reversed(video_rows):
        if row_data["checkbox"].get() == 1:
            row_data["frame"].destroy()
            video_rows.remove(row_data)
            
    total_time_label.configure(text="0h 0m 0s", text_color="#aaaaaa")
    try: app.after(10, lambda: list_frame._parent_canvas.yview_moveto(0.0))
    except: pass

def calculate_total_time():
    """Calculate the total time ONLY for the selected (checked) videos"""
    total_seconds = 0
    for row_data in video_rows:
        # Check if the checkbox is selected before adding its time
        if row_data["checkbox"].get() == 1:
            dur_str = row_data["duration"]
            if dur_str == "--:--" or dur_str == "N/A": continue
            parts = dur_str.split(":")
            
            if len(parts) == 2:
                total_seconds += int(parts[0]) * 60 + int(parts[1])
            elif len(parts) == 3:
                total_seconds += int(parts[0]) * 3600 + int(parts[1]) * 60 + int(parts[2])
    
    h, r = divmod(total_seconds, 3600)
    m, s = divmod(r, 60)
    
    time_text = ""
    if h > 0: time_text += f"{int(h)}h "
    if m > 0 or h > 0: time_text += f"{int(m)}m "
    time_text += f"{int(s)}s"
    
    if total_seconds == 0: time_text = "0h 0m 0s"
    total_time_label.configure(text=time_text, text_color="#FF6600")

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
    total_time_label.configure(text="0h 0m 0s", text_color="#aaaaaa")

def add_video_row(index, title, duration, status="Ready", status_color="#28a745"):
    row = ctk.CTkFrame(list_frame, fg_color="#333333", height=50)
    row.pack(side="top", fill="x", pady=2, anchor="n") 
    
    cb = ctk.CTkCheckBox(row, text="", width=30)
    cb.select()
    cb.pack(side="left", padx=5)

    ctk.CTkLabel(row, text=str(index), width=30).pack(side="left", padx=(5, 0))
    
    title_entry = ctk.CTkEntry(row, width=270, fg_color="transparent", border_width=0, text_color="white", font=("Arial", 12))
    title_entry.insert(0, title)
    title_entry.configure(state="readonly")
    title_entry.pack(side="left")

    ctk.CTkLabel(row, text=duration, width=80).pack(side="left")
    ctk.CTkLabel(row, text="N/A", width=80).pack(side="left")
    ctk.CTkLabel(row, text=status, text_color=status_color, width=100).pack(side="left")
    
    prog_bar = ctk.CTkProgressBar(row, width=150, progress_color="#FF6600")
    prog_bar.set(0)
    prog_bar.pack(side="left", padx=10)

    video_rows.append({
        "frame": row, "checkbox": cb, "title": title, 
        "duration": duration, "progress": prog_bar, 
        "status_label": row.winfo_children()[-2]
    })

def render_chunk(entries_data, current_idx, qualities, chunk_size=15):
    end_idx = min(current_idx + chunk_size, len(entries_data))
    
    for i in range(current_idx, end_idx):
        data = entries_data[i]
        add_video_row(data['idx'], data['title'], data['dur'])
        
    update_global_status(f"Rendering videos... ({end_idx}/{len(entries_data)})", "#FF6600")

    if end_idx < len(entries_data):
        app.after(10, lambda: render_chunk(entries_data, end_idx, qualities, chunk_size))
    else:
        quality_combo.configure(values=qualities)
        if qualities: quality_combo.set(qualities[0])
        update_global_status("Data fetched successfully. Ready to download.", "#28a745")

def fetch_video_data():
    url = url_entry.get()
    if not url:
        app.after(0, lambda: update_global_status("Error: Please enter a valid YouTube URL!", "red"))
        return

    app.after(0, clear_list)
    app.after(0, lambda: update_global_status("Connecting to YouTube... Please wait.", "#FF6600"))
    app.after(0, lambda: quality_combo.set("Loading..."))

    is_single_video = ("watch?v=" in url) or ("youtu.be/" in url)
    
    ydl_opts = {
        'quiet': True, 
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
                    entries_data.append({'idx': idx, 'title': title, 'dur': dur})
                    
                qualities = ["Best Quality", "Medium", "Low", "Audio Only (MP3)"]
            
            else:
                title = info.get('title', 'Unknown Title')
                dur = format_duration(info.get('duration', 0))
                entries_data.append({'idx': 1, 'title': title, 'dur': dur})
                
                formats = info.get('formats', [])
                q_set = set()
                for f in formats:
                    h = f.get('height')
                    if h and h > 0:
                        q_set.add(f"{h}p")
                
                qualities = sorted(list(q_set), key=lambda x: int(x.replace('p', '')), reverse=True)
                if not qualities: 
                    qualities = ["Best Quality"]
                qualities.append("Audio Only (MP3)")
            
            app.after(0, lambda: render_chunk(entries_data, 0, qualities))

    except Exception as e:
        app.after(0, lambda e=e: update_global_status(f"Error: {str(e)[:80]}...", "red"))

def on_search_click():
    threading.Thread(target=fetch_video_data, daemon=True).start()

ctk.CTkButton(url_input_layout, text="🔍", width=40, fg_color="#840284", hover_color="#6b016b", command=on_search_click).pack(side="left")

app.mainloop()