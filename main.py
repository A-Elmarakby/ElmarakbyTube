import customtkinter as ctk

# --- Window Setup ---
ctk.set_appearance_mode("Dark")
app = ctk.CTk()
app.geometry("950x650") # Slightly wider to fit the table nicely
app.title("ElmarakbyTube Downloader")

# ==================== Top Section (Save Path & URL) ====================
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

# 2. Playlist/Video URL Input
url_frame = ctk.CTkFrame(top_frame, fg_color="transparent")
url_frame.pack(side="left", fill="x", expand=True)
ctk.CTkLabel(url_frame, text="Video or Playlist URL:", font=("Arial", 12, "bold")).pack(anchor="w")

url_input_layout = ctk.CTkFrame(url_frame, fg_color="transparent")
url_input_layout.pack(fill="x")
ctk.CTkEntry(url_input_layout, placeholder_text="Paste your YouTube link here...").pack(side="left", fill="x", expand=True, padx=(0, 5))
# Brand Purple Color for Search Button
ctk.CTkButton(url_input_layout, text="🔍", width=40, fg_color="#840284", hover_color="#6b016b").pack(side="left")

# ==================== Toolbar Section ====================
toolbar_frame = ctk.CTkFrame(app, fg_color="transparent")
toolbar_frame.pack(fill="x", padx=20, pady=(0, 10))

ctk.CTkButton(toolbar_frame, text="Select All", width=100, fg_color="#333", hover_color="#444").pack(side="left", padx=(0, 5))
ctk.CTkButton(toolbar_frame, text="Deselect All", width=100, fg_color="#333", hover_color="#444").pack(side="left")

# Quality Dropdown with Label
quality_layout = ctk.CTkFrame(toolbar_frame, fg_color="transparent")
quality_layout.pack(side="right")
ctk.CTkLabel(quality_layout, text="Quality:").pack(side="left", padx=(0, 10))

quality_options = ["Loading available qualities..."] # Will be dynamic later
quality_combo = ctk.CTkComboBox(quality_layout, values=quality_options, width=150)
quality_combo.set("Select Quality")
quality_combo.pack(side="left")

# ==================== Table Header Row ====================
# A dark frame to act as the header background
header_frame = ctk.CTkFrame(app, fg_color="#1e1e1e", height=40, corner_radius=5)
header_frame.pack(fill="x", padx=20, pady=(0, 5))

# Aligning widths to match the data rows below
ctk.CTkLabel(header_frame, text="", width=30).pack(side="left", padx=5) # Empty space for checkbox
ctk.CTkLabel(header_frame, text="Video Title", width=300, anchor="w", font=("Arial", 12, "bold")).pack(side="left")
ctk.CTkLabel(header_frame, text="Duration", width=80, font=("Arial", 12, "bold")).pack(side="left")
ctk.CTkLabel(header_frame, text="Size", width=80, font=("Arial", 12, "bold")).pack(side="left")
ctk.CTkLabel(header_frame, text="Status", width=100, font=("Arial", 12, "bold")).pack(side="left")
ctk.CTkLabel(header_frame, text="Progress", width=150, font=("Arial", 12, "bold")).pack(side="left", padx=10)

# ==================== List Area (Scrollable Data Grid) ====================
list_frame = ctk.CTkScrollableFrame(app, fg_color="#2b2b2b")
list_frame.pack(fill="both", expand=True, padx=20, pady=(0, 20))

# --- Dummy Row 1 ---
row_1 = ctk.CTkFrame(list_frame, fg_color="#333333", height=50)
row_1.pack(fill="x", pady=2)
ctk.CTkCheckBox(row_1, text="", width=30).pack(side="left", padx=5)
ctk.CTkLabel(row_1, text="1. Python Programming for Beginners", width=300, anchor="w").pack(side="left")
ctk.CTkLabel(row_1, text="15:20", width=80).pack(side="left")
ctk.CTkLabel(row_1, text="150 MB", width=80).pack(side="left")
ctk.CTkLabel(row_1, text="Completed", text_color="#28a745", width=100).pack(side="left") # Green text
ctk.CTkProgressBar(row_1, width=150, progress_color="#28a745").pack(side="left", padx=10)

# --- Dummy Row 2 ---
row_2 = ctk.CTkFrame(list_frame, fg_color="#333333", height=50)
row_2.pack(fill="x", pady=2)
ctk.CTkCheckBox(row_2, text="", width=30).pack(side="left", padx=5)
ctk.CTkLabel(row_2, text="2. Advanced UI Design Tutorial", width=300, anchor="w").pack(side="left")
ctk.CTkLabel(row_2, text="22:10", width=80).pack(side="left")
ctk.CTkLabel(row_2, text="220 MB", width=80).pack(side="left")
ctk.CTkLabel(row_2, text="Downloading", text_color="#FF6600", width=100).pack(side="left") # Brand Orange text
# Setting progress bar to 60%
prog_bar_2 = ctk.CTkProgressBar(row_2, width=150, progress_color="#FF6600")
prog_bar_2.pack(side="left", padx=10)
prog_bar_2.set(0.6) 

# ==================== Bottom Section (Download/Cancel Buttons) ====================
bottom_frame = ctk.CTkFrame(app, fg_color="transparent")
bottom_frame.pack(pady=10)

# Download Button (Brand Purple)
ctk.CTkButton(bottom_frame, text="Download Selected", width=150, height=40, font=("Arial", 14, "bold"), fg_color="#840284", hover_color="#6b016b").pack(side="left", padx=10)

# Cancel Button (Brand Orange)
ctk.CTkButton(bottom_frame, text="Cancel Download", width=150, height=40, font=("Arial", 14, "bold"), fg_color="#FF6600", hover_color="#cc5200").pack(side="left", padx=10)

# --- Run App ---
app.mainloop()
