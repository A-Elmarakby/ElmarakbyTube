import customtkinter as ctk
import yt_dlp
import threading

# --- Window Setup ---
ctk.set_appearance_mode("Dark")
app = ctk.CTk()
app.geometry("950x650")
app.title("ElmarakbyTube Downloader")

# ==================== Top Section ====================
top_frame = ctk.CTkFrame(app, fg_color="transparent")
top_frame.pack(fill="x", padx=20, pady=20)

# 1. Save Path Input
save_path_frame = ctk.CTkFrame(top_frame, fg_color="transparent")
save_path_frame.pack(side="left", fill="x", expand=True, padx=(0, 10))
ctk.CTkLabel(save_path_frame, text="Save Path:", font=("Arial", 12, "bold")).pack(anchor="w")

path_input_layout = ctk.CTkFrame(save_path_frame, fg_color="transparent")
path_input_layout.pack(fill="x")
ctk.CTkEntry(path_input_layout, placeholder_text="/Downloads/Playlists...").pack(side="left", fill="x", expand=True, padx=(0, 5))
ctk.CTkButton(path_input_layout, text="Browse", width=80, fg_color="#840284", hover_color="#6b016b").pack(side="left")

# 2. URL Input
url_frame = ctk.CTkFrame(top_frame, fg_color="transparent")
url_frame.pack(side="left", fill="x", expand=True)
ctk.CTkLabel(url_frame, text="Video or Playlist URL:", font=("Arial", 12, "bold")).pack(anchor="w")

url_input_layout = ctk.CTkFrame(url_frame, fg_color="transparent")
url_input_layout.pack(fill="x")
url_entry = ctk.CTkEntry(url_input_layout, placeholder_text="Paste your YouTube link here...")
url_entry.pack(side="left", fill="x", expand=True, padx=(0, 5))

# ==================== Toolbar Section ====================
toolbar_frame = ctk.CTkFrame(app, fg_color="transparent")
toolbar_frame.pack(fill="x", padx=20, pady=(0, 10))

ctk.CTkButton(toolbar_frame, text="Select All", width=100, fg_color="#333", hover_color="#444").pack(side="left", padx=(0, 5))
ctk.CTkButton(toolbar_frame, text="Deselect All", width=100, fg_color="#333", hover_color="#444").pack(side="left")

quality_layout = ctk.CTkFrame(toolbar_frame, fg_color="transparent")
quality_layout.pack(side="right")
ctk.CTkLabel(quality_layout, text="Quality:").pack(side="left", padx=(0, 10))

quality_combo = ctk.CTkComboBox(quality_layout, values=["Waiting for link..."], width=150)
quality_combo.set("Select Quality")
quality_combo.pack(side="left")

# ==================== Table Header ====================
header_frame = ctk.CTkFrame(app, fg_color="#1e1e1e", height=40, corner_radius=5)
header_frame.pack(fill="x", padx=20, pady=(0, 5))

# Adding the Index (#) column
ctk.CTkLabel(header_frame, text="#", width=30, font=("Arial", 12, "bold")).pack(side="left", padx=(10, 0))
ctk.CTkLabel(header_frame, text="", width=30).pack(side="left", padx=5) # Checkbox space
ctk.CTkLabel(header_frame, text="Video Title", width=270, anchor="w", font=("Arial", 12, "bold")).pack(side="left")
ctk.CTkLabel(header_frame, text="Duration", width=80, font=("Arial", 12, "bold")).pack(side="left")
ctk.CTkLabel(header_frame, text="Size", width=80, font=("Arial", 12, "bold")).pack(side="left")
ctk.CTkLabel(header_frame, text="Status", width=100, font=("Arial", 12, "bold")).pack(side="left")
ctk.CTkLabel(header_frame, text="Progress", width=150, font=("Arial", 12, "bold")).pack(side="left", padx=10)

# ==================== List Area (Dynamic) ====================
list_frame = ctk.CTkScrollableFrame(app, fg_color="#2b2b2b")
list_frame.pack(fill="both", expand=True, padx=20, pady=(0, 20))

# ==================== Functions ====================

def format_duration(seconds):
    """Convert seconds to MM:SS or HH:MM:SS"""
    if not seconds: return "00:00"
    m, s = divmod(int(seconds), 60)
    h, m = divmod(m, 60)
    if h > 0: return f"{h}:{m:02d}:{s:02d}"
    return f"{m:02d}:{s:02d}"

def clear_list():
    """Remove all rows from the table"""
    for widget in list_frame.winfo_children():
        widget.destroy()

def add_video_row(index, title, duration, status="Ready", status_color="#28a745"):
    """Create a new row in the UI table with an index number"""
    row = ctk.CTkFrame(list_frame, fg_color="#333333", height=50)
    row.pack(fill="x", pady=2)
    
    short_title = title[:40] + "..." if len(title) > 40 else title

    # The Index Number
    ctk.CTkLabel(row, text=str(index), width=30).pack(side="left", padx=(10, 0))
    ctk.CTkCheckBox(row, text="", width=30).pack(side="left", padx=5)
    ctk.CTkLabel(row, text=short_title, width=270, anchor="w").pack(side="left")
    ctk.CTkLabel(row, text=duration, width=80).pack(side="left")
    ctk.CTkLabel(row, text="N/A", width=80).pack(side="left")
    ctk.CTkLabel(row, text=status, text_color=status_color, width=100).pack(side="left")
    
    prog_bar = ctk.CTkProgressBar(row, width=150, progress_color="#FF6600")
    prog_bar.set(0)
    prog_bar.pack(side="left", padx=10)

def update_ui_ready(qualities):
    """Update dropdown menu securely on main thread"""
    quality_combo.configure(values=qualities)
    if qualities:
        quality_combo.set(qualities[0])

def update_ui_error(msg):
    """Show error securely on main thread"""
    clear_list()
    add_video_row("-", msg, "--:--", "Failed", "red")

def fetch_video_data():
    """Background thread to fetch data from YouTube"""
    url = url_entry.get()
    if not url:
        app.after(0, update_ui_error, "Please enter a valid URL!")
        return

    # Update UI to show loading state
    app.after(0, clear_list)
    app.after(0, add_video_row, "-", "Fetching data...", "--:--", "Loading", "#aaaaaa")
    app.after(0, quality_combo.set, "Loading...")

    ydl_opts = {'quiet': True, 'extract_flat': 'in_playlist'}
    
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            
            app.after(0, clear_list) 
            qualities = []

            # Check if it's a playlist
            if 'entries' in info:
                # Loop with index (starting from 1)
                for idx, entry in enumerate(info['entries'], start=1):
                    title = entry.get('title', 'Unknown Title')
                    dur = format_duration(entry.get('duration', 0))
                    app.after(0, add_video_row, idx, title, dur)
                
                # Standard Playlist Qualities
                qualities = ["Best Quality", "1080p (High)", "720p (Medium)", "480p (Low)", "Audio Only (MP3)"]
            
            # Or a single video
            else:
                title = info.get('title', 'Unknown Title')
                dur = format_duration(info.get('duration', 0))
                app.after(0, add_video_row, 1, title, dur)
                
                formats = info.get('formats', [])
                q_set = set()
                for f in formats:
                    if f.get('vcodec') != 'none' and f.get('height'):
                        q_set.add(f"{f.get('height')}p")
                
                qualities = sorted(list(q_set), key=lambda x: int(x.replace('p', '')), reverse=True)
                qualities.append("Audio Only (MP3)")
            
            app.after(0, update_ui_ready, qualities)

    except Exception as e:
        print(f"Error: {e}")
        app.after(0, update_ui_error, "Error fetching data!")

def on_search_click():
    """Start background thread when search button is clicked"""
    threading.Thread(target=fetch_video_data, daemon=True).start()

# Connect search button
ctk.CTkButton(url_input_layout, text="🔍", width=40, fg_color="#840284", hover_color="#6b016b", command=on_search_click).pack(side="left")

# ==================== Bottom Section ====================
bottom_frame = ctk.CTkFrame(app, fg_color="transparent")
bottom_frame.pack(pady=10)

ctk.CTkButton(bottom_frame, text="Download Selected", width=150, height=40, font=("Arial", 14, "bold"), fg_color="#840284", hover_color="#6b016b").pack(side="left", padx=10)
ctk.CTkButton(bottom_frame, text="Cancel Download", width=150, height=40, font=("Arial", 14, "bold"), fg_color="#FF6600", hover_color="#cc5200").pack(side="left", padx=10)

app.mainloop()