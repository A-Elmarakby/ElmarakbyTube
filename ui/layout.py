"""
File: layout.py
What it does: Draws all the UI (buttons, frames, text) and updates the screen.
Why we need it: To separate the UI drawing from the main logic.
"""

import customtkinter as ctk
from tkinter import filedialog
from PIL import Image

import config
import messages
from core.utils import apply_bidi, format_size
import ui.state as state
from ui.popups import custom_msg_box


# ==========================================
# 1. UI Helper Functions
# ==========================================

def safe_ui_update(widget, **kwargs):
    # Update widget safely without crashing
    if widget and widget.winfo_exists():
        widget.configure(**kwargs)

def safe_progress_update(widget, value):
    # Update progress bar safely
    if widget and widget.winfo_exists():
        widget.set(value)

def update_global_status(msg, color="white", warning_msg=""):
    # Change the text at the bottom bar
    if state.global_status_label and state.global_status_label.winfo_exists():
        state.global_status_label.configure(text=apply_bidi(f"Status: {msg}"), text_color=color)
    if state.global_warning_label and state.global_warning_label.winfo_exists():
        state.global_warning_label.configure(text=apply_bidi(warning_msg))

def update_dynamic_totals():
    # Calculate the total time and size of selected videos
    total_bytes = 0
    total_seconds = 0
    all_fetched = True 

    for row in state.video_rows:
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
    if state.total_time_label and state.total_time_label.winfo_exists():
        state.total_time_label.configure(text=time_text)

    size_text = format_size(total_bytes)
    if not all_fetched and total_bytes > 0:
        size_text += "+"
    if state.total_size_label and state.total_size_label.winfo_exists():
        state.total_size_label.configure(text=size_text)

def toggle_all(is_checked):
    # Check or uncheck all boxes
    for row_data in state.video_rows:
        if is_checked: 
            row_data["checkbox"].select()
        else: 
            row_data["checkbox"].deselect()
    update_dynamic_totals()

def remove_selected():
    # Delete selected videos from the list
    with state.ui_list_lock:
        for row_data in reversed(state.video_rows):
             if row_data["checkbox"].get() == 1:
                row_data["frame"].destroy()
                state.video_rows.remove(row_data)
    update_dynamic_totals()
    
    if state.list_frame and state.list_frame.winfo_exists():
        try: state.list_frame.winfo_toplevel().after(10, lambda: state.list_frame._parent_canvas.yview_moveto(0.0))
        except: pass

def clear_list():
    # Remove all videos from the list
    if state.list_frame and state.list_frame.winfo_exists():
        for widget in state.list_frame.winfo_children():
            widget.destroy()
    state.video_rows.clear()
    update_dynamic_totals()
    
    if state.list_frame and state.list_frame.winfo_exists():
        try: state.list_frame.winfo_toplevel().after(10, lambda: state.list_frame._parent_canvas.yview_moveto(0.0))
        except: pass

def add_video_row(index, title, duration, vid_url, status="Ready", status_color="#28a745"):
    # Draw a single video row on the screen
    if not state.list_frame or not state.list_frame.winfo_exists():
        return
        
    row = ctk.CTkFrame(state.list_frame, fg_color="#333333", height=50)
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

    row_data = {
        "frame": row, "checkbox": cb, "title": title, 
        "duration": duration, "progress": prog_bar, 
        "size_label": size_lbl, "status_label": status_lbl,
        "percent_label": percent_lbl,
        "url": vid_url,
        "bytes_size": -1,
        "dl_state": "ready",
        "error_msg": ""
    }
    state.video_rows.append(row_data)

    def on_status_click(event, r=row_data):
        if r['dl_state'] == 'failed' and r['error_msg']:
            custom_msg_box(messages.TITLE_ERROR_DETAILS, r['error_msg'], "error")

    status_lbl.bind("<Button-1>", on_status_click)


# ==========================================
# 2. Builder Functions
# ==========================================

def _build_top_section(parent, callbacks):
    # Top section for Path and URL
    top_frame = ctk.CTkFrame(parent, fg_color="transparent")
    top_frame.pack(fill="x", padx=20, pady=20)

    # Save Path Input
    save_path_frame = ctk.CTkFrame(top_frame, fg_color="transparent")
    save_path_frame.pack(side="left", fill="x", expand=True, padx=(0, 10))
    ctk.CTkLabel(save_path_frame, text="Save Path:", font=(messages.FONT_FAMILY, messages.FONT_SIZE_MAIN, "bold")).pack(anchor="w")

    path_input_layout = ctk.CTkFrame(save_path_frame, fg_color="transparent")
    path_input_layout.pack(fill="x")
    state.path_entry = ctk.CTkEntry(path_input_layout, placeholder_text="/Downloads/Playlists...")
    state.path_entry.pack(side="left", fill="x", expand=True, padx=(0, 5))

    def browse_save_path():
        folder_path = filedialog.askdirectory(title="Select Save Folder")
        if folder_path:
            state.path_entry.delete(0, 'end')
            state.path_entry.insert(0, folder_path)

    ctk.CTkButton(path_input_layout, text="Browse", width=80, fg_color=config.COLOR_MAGENTA, hover_color=config.COLOR_MAGENTA_HOVER, command=browse_save_path).pack(side="left")

    # YouTube URL Input
    url_frame = ctk.CTkFrame(top_frame, fg_color="transparent")
    url_frame.pack(side="left", fill="x", expand=True)
    ctk.CTkLabel(url_frame, text="Video or Playlist URL:", font=(messages.FONT_FAMILY, messages.FONT_SIZE_MAIN, "bold")).pack(anchor="w")

    url_input_layout = ctk.CTkFrame(url_frame, fg_color="transparent")
    url_input_layout.pack(fill="x")
    state.url_entry = ctk.CTkEntry(url_input_layout, placeholder_text="Paste your YouTube link here...")
    state.url_entry.pack(side="left", fill="x", expand=True, padx=(0, 5))

    # Search Button
    try:
        search_icon = ctk.CTkImage(light_image=Image.open(config.SEARCH_ICON_PATH), dark_image=Image.open(config.SEARCH_ICON_PATH), size=config.SEARCH_ICON_SIZE)
        ctk.CTkButton(url_input_layout, text="", image=search_icon, width=40, fg_color=config.COLOR_MAGENTA, hover_color=config.COLOR_MAGENTA_HOVER, command=callbacks['on_search_click']).pack(side="left")
    except Exception:
        ctk.CTkButton(url_input_layout, text="🔍", width=40, fg_color=config.COLOR_MAGENTA, hover_color=config.COLOR_MAGENTA_HOVER, command=callbacks['on_search_click']).pack(side="left")

def _build_toolbar_section(parent, callbacks):
    # Middle section for buttons and totals
    toolbar_frame = ctk.CTkFrame(parent, fg_color="transparent")
    toolbar_frame.pack(fill="x", padx=20, pady=(0, 10))

    ctk.CTkButton(toolbar_frame, text="Select All", width=90, fg_color="#333", hover_color="#444", command=lambda: toggle_all(True)).pack(side="left", padx=(0, 5))
    ctk.CTkButton(toolbar_frame, text="Deselect All", width=90, fg_color="#333", hover_color="#444", command=lambda: toggle_all(False)).pack(side="left", padx=(0, 5))
    ctk.CTkButton(toolbar_frame, text="Remove Selected", width=110, fg_color=config.COLOR_RED, hover_color=config.COLOR_RED_HOVER, command=remove_selected).pack(side="left")

    # Dashboard 
    dashboard_frame = ctk.CTkFrame(toolbar_frame, fg_color="transparent")
    dashboard_frame.pack(side="left", padx=20)

    ctk.CTkLabel(dashboard_frame, text="Total Time:", font=(messages.FONT_FAMILY, messages.FONT_SIZE_MAIN, "bold")).pack(side="left", padx=(0, 5))
    state.total_time_label = ctk.CTkLabel(dashboard_frame, text="0s", font=(messages.FONT_FAMILY, messages.FONT_SIZE_MAIN, "bold"), text_color="#aaaaaa", width=80, anchor="w")
    state.total_time_label.pack(side="left", padx=(0, 15))

    ctk.CTkLabel(dashboard_frame, text="Total Size:", font=(messages.FONT_FAMILY, messages.FONT_SIZE_MAIN, "bold")).pack(side="left", padx=(0, 5))
    state.total_size_label = ctk.CTkLabel(dashboard_frame, text="0.0 MB", font=(messages.FONT_FAMILY, messages.FONT_SIZE_MAIN, "bold"), text_color="#aaaaaa", width=80, anchor="w")
    state.total_size_label.pack(side="left")

    quality_layout = ctk.CTkFrame(toolbar_frame, fg_color="transparent")
    quality_layout.pack(side="right")

    def on_quality_change(choice):
        for row in state.video_rows:
            row['bytes_size'] = -1 
            safe_ui_update(row['size_label'], text="N/A", text_color="white")
        update_dynamic_totals()

    fetch_action_frame = ctk.CTkFrame(quality_layout, fg_color="transparent")
    fetch_action_frame.pack(side="left", padx=(0, 10))

    state.fetch_btn = ctk.CTkButton(fetch_action_frame, text="Fetch Sizes", width=90, fg_color=config.COLOR_CYAN, hover_color=config.COLOR_CYAN_HOVER, command=callbacks['on_fetch_sizes_click'])
    state.fetch_btn.pack(side="left")

    state.stop_fetch_btn = ctk.CTkButton(fetch_action_frame, text="Stop Fetch", width=90, fg_color=config.COLOR_RED, hover_color=config.COLOR_RED_HOVER, command=callbacks['on_stop_fetch_click'])

    ctk.CTkLabel(quality_layout, text="Quality:").pack(side="left", padx=(0, 5))
    state.quality_combo = ctk.CTkComboBox(quality_layout, values=["Waiting for link..."], width=130, command=on_quality_change)
    state.quality_combo.set("Select Quality")
    state.quality_combo.pack(side="left")

def _build_list_area(parent):
    # Header and Video List
    header_frame = ctk.CTkFrame(parent, fg_color="#1e1e1e", height=40, corner_radius=5)
    header_frame.pack(fill="x", padx=20, pady=(0, 5))

    ctk.CTkLabel(header_frame, text="", width=30).pack(side="left", padx=5)
    ctk.CTkLabel(header_frame, text="#", width=30, font=(messages.FONT_FAMILY, messages.FONT_SIZE_MAIN, "bold")).pack(side="left", padx=(5, 0))
    ctk.CTkLabel(header_frame, text="Video Title", width=250, anchor="w", font=(messages.FONT_FAMILY, messages.FONT_SIZE_MAIN, "bold")).pack(side="left")
    ctk.CTkLabel(header_frame, text="Duration", width=70, font=(messages.FONT_FAMILY, messages.FONT_SIZE_MAIN, "bold")).pack(side="left")
    ctk.CTkLabel(header_frame, text="Size", width=80, font=(messages.FONT_FAMILY, messages.FONT_SIZE_MAIN, "bold")).pack(side="left")
    ctk.CTkLabel(header_frame, text="Status", width=100, font=(messages.FONT_FAMILY, messages.FONT_SIZE_MAIN, "bold")).pack(side="left")
    ctk.CTkLabel(header_frame, text="Progress", width=120, font=(messages.FONT_FAMILY, messages.FONT_SIZE_MAIN, "bold")).pack(side="left", padx=(10, 5))
    ctk.CTkLabel(header_frame, text="%", width=40, font=(messages.FONT_FAMILY, messages.FONT_SIZE_MAIN, "bold")).pack(side="left")

    state.list_frame = ctk.CTkScrollableFrame(parent, fg_color="#2b2b2b")
    state.list_frame.pack(fill="both", expand=True, padx=20, pady=(0, 10))

def _build_status_bar(parent, callbacks):
    # Status bar at the very bottom
    status_bar = ctk.CTkFrame(parent, height=30, fg_color="#1e1e1e", corner_radius=0)
    status_bar.pack(fill="x", side="bottom")

    state.global_status_label = ctk.CTkLabel(status_bar, text="Status: Ready", font=(messages.FONT_FAMILY, messages.FONT_SIZE_MAIN))
    state.global_status_label.pack(side="left", padx=(20, 5))

    state.global_warning_label = ctk.CTkLabel(status_bar, text="", font=(messages.FONT_FAMILY, messages.FONT_SIZE_MAIN, "bold"), text_color=config.COLOR_RED)
    state.global_warning_label.pack(side="left")

    # Contact Button
    try:
        contact_icon = ctk.CTkImage(light_image=Image.open(config.CONTACT_ICON_PATH), dark_image=Image.open(config.CONTACT_ICON_PATH), size=config.CONTACT_ICON_SIZE)
    except Exception:
        contact_icon = None

    contact_btn = ctk.CTkButton(status_bar, text=apply_bidi(messages.BTN_CONTACT_US), font=("Segoe UI", 12, "bold"), fg_color=config.CONTACT_COLOR_1, hover_color=config.CONTACT_HOVER_1, width=config.CONTACT_BTN_WIDTH, height=config.CONTACT_BTN_HEIGHT, corner_radius=config.CONTACT_CORNER_RADIUS, command=callbacks['show_contact_popup'])
    contact_btn.pack(side="right", padx=(5, 25), pady=2) 

    if contact_icon:
        icon_label = ctk.CTkLabel(status_bar, text="", image=contact_icon)
        icon_label.pack(side="right", padx=(10, 0), pady=2)

    def animate_contact_btn(current_state=1):
        if current_state == 1:
            contact_btn.configure(fg_color=config.CONTACT_COLOR_1, hover_color=config.CONTACT_HOVER_1)
            status_bar.after(config.CONTACT_DURATION_COLOR_1, animate_contact_btn, 2)
        else:
            contact_btn.configure(fg_color=config.CONTACT_COLOR_2, hover_color=config.CONTACT_HOVER_2)
            status_bar.after(config.CONTACT_DURATION_COLOR_2, animate_contact_btn, 1)

    animate_contact_btn(1)

def _build_bottom_actions(parent, callbacks):
    # Main action buttons above status bar
    bottom_frame = ctk.CTkFrame(parent, fg_color="transparent")
    bottom_frame.pack(pady=10, side="bottom") 

    center_actions_frame = ctk.CTkFrame(bottom_frame, fg_color="transparent")
    center_actions_frame.pack()

    state.download_btn = ctk.CTkButton(center_actions_frame, text="Download Selected", width=150, height=40, font=(messages.FONT_FAMILY, messages.FONT_SIZE_LARGE, "bold"), fg_color=config.COLOR_MAGENTA, hover_color=config.COLOR_MAGENTA_HOVER, command=callbacks['on_download_click'])
    state.download_btn.pack(side="left", padx=10)

    state.convert_btn = ctk.CTkButton(center_actions_frame, text="Convert to MP4", width=150, height=40, font=(messages.FONT_FAMILY, messages.FONT_SIZE_LARGE, "bold"), fg_color=config.COLOR_CYAN, hover_color=config.COLOR_CYAN_HOVER, command=callbacks['on_convert_click'])
    state.convert_btn.pack(side="left", padx=10)

# ==========================================
# 3. Main Builder Entry
# ==========================================

def build_app_ui(app, callbacks):
    # Build everything in the correct order
    app.bind_all("<KeyPress>", callbacks['global_hardware_shortcuts'])
    
    _build_top_section(app, callbacks)
    _build_toolbar_section(app, callbacks)
    _build_list_area(app)
    
    # Pack status bar first to keep it at the very bottom
    _build_status_bar(app, callbacks)
    _build_bottom_actions(app, callbacks)