"""
File: popups.py
What it does: Contains all the popup windows (alerts, questions).
Why we need it: To keep the main screen code clean and separated from these small dialogs.
"""

import customtkinter as ctk
import config
import messages
from core.utils import apply_bidi

def center_toplevel(top, width, height, parent_window=None):
    # Center a popup window relative to the screen or parent window
    if parent_window:
        parent_window.update_idletasks()
        x = parent_window.winfo_x() + (parent_window.winfo_width() // 2) - (width // 2)
        y = parent_window.winfo_y() + (parent_window.winfo_height() // 2) - (height // 2)
    else:
        top.update_idletasks()
        screen_width = top.winfo_screenwidth()
        screen_height = top.winfo_screenheight()
        x = (screen_width // 2) - (width // 2)
        y = (screen_height // 2) - (height // 2)
    top.geometry(f"{width}x{height}+{x}+{y}")

def custom_msg_box(title, message, msg_type="error", parent_window=None):
    # If no parent is provided, try to find the main app window automatically
    if parent_window is None:
        import __main__
        if hasattr(__main__, 'app'):
            parent_window = __main__.app

    # Our custom message box builder
    dialog = ctk.CTkToplevel(parent_window)
    dialog.title(apply_bidi(title)) 
    
    center_toplevel(dialog, config.POPUP_WIDTH, config.POPUP_HEIGHT, parent_window)
    dialog.transient(parent_window)
    dialog.grab_set()
    
    def apply_icon():
        try: dialog.iconbitmap(config.ICON_FILE)
        except: pass
    dialog.after(200, apply_icon)
    
    config.play_sound(msg_type)
    
    color = config.COLOR_RED 
    icon = " 🛑 "
    if msg_type == "warning":
        color = "#FFCC00" 
        icon = "⚠️ "
    elif msg_type == "success":
        color = "#28a745"
        icon = "✅"
    elif msg_type == "info":
        color = config.COLOR_CYAN
        icon = "ℹ️"
        
    # Architectural Solution: Frame Separation to perfectly align Emojis and Punctuation
    title_frame = ctk.CTkFrame(dialog, fg_color="transparent")
    title_frame.pack(pady=(20, 5))
    
    is_arabic = any('\u0600' <= c <= '\u06FF' for c in str(title))
    if is_arabic:
        ctk.CTkLabel(title_frame, text=f"{icon} ", font=(messages.FONT_FAMILY, messages.FONT_SIZE_POPUP_TITLE, "bold"), text_color=color).pack(side="right")
        ctk.CTkLabel(title_frame, text=apply_bidi(title), font=(messages.FONT_FAMILY, messages.FONT_SIZE_POPUP_TITLE, "bold"), text_color=color).pack(side="right")
    else:
        ctk.CTkLabel(title_frame, text=f"{icon} ", font=(messages.FONT_FAMILY, messages.FONT_SIZE_POPUP_TITLE, "bold"), text_color=color).pack(side="left")
        ctk.CTkLabel(title_frame, text=title, font=(messages.FONT_FAMILY, messages.FONT_SIZE_POPUP_TITLE, "bold"), text_color=color).pack(side="left")
    
    lbl_msg = ctk.CTkLabel(dialog, text=apply_bidi(message), font=(messages.FONT_FAMILY, messages.FONT_SIZE_POPUP_BODY), wraplength=400, justify="center")
    lbl_msg.pack(pady=(0, 20), padx=20)
    
    ctk.CTkButton(dialog, text=apply_bidi(messages.BTN_OK), fg_color="#555", hover_color="#333", width=100, command=dialog.destroy).pack(pady=(0, 20))
    dialog.wait_window()

def custom_ask_yes_no(title, message, icon="⚠️", parent_window=None):
    # If no parent is provided, try to find the main app window automatically
    if parent_window is None:
        import __main__
        if hasattr(__main__, 'app'):
            parent_window = __main__.app

    # Ask user a Yes or No question
    dialog = ctk.CTkToplevel(parent_window)
    dialog.title(apply_bidi(title))
    center_toplevel(dialog, config.POPUP_WIDTH, config.POPUP_HEIGHT, parent_window)
    dialog.transient(parent_window)
    dialog.grab_set()
    
    def apply_icon():
        try: dialog.iconbitmap(config.ICON_FILE)
        except: pass
    dialog.after(200, apply_icon)

    config.play_sound("warning")
    result = [False]
    def set_res(val):
        result[0] = val
        dialog.destroy()
        
    # --- Architectural Solution: Header Frame (Icon + Title) ---
    title_frame = ctk.CTkFrame(dialog, fg_color="transparent")
    title_frame.pack(pady=(20, 5))
    
    warning_color = "#FFCC00" 
    is_arabic_title = any('\u0600' <= c <= '\u06FF' for c in str(title))
    
    if is_arabic_title:
        ctk.CTkLabel(title_frame, text=f"{icon} ", font=(messages.FONT_FAMILY, messages.FONT_SIZE_POPUP_TITLE, "bold"), text_color=warning_color).pack(side="right")
        ctk.CTkLabel(title_frame, text=apply_bidi(title), font=(messages.FONT_FAMILY, messages.FONT_SIZE_POPUP_TITLE, "bold"), text_color=warning_color).pack(side="right")
    else:
        ctk.CTkLabel(title_frame, text=f"{icon} ", font=(messages.FONT_FAMILY, messages.FONT_SIZE_POPUP_TITLE, "bold"), text_color=warning_color).pack(side="left")
        ctk.CTkLabel(title_frame, text=title, font=(messages.FONT_FAMILY, messages.FONT_SIZE_POPUP_TITLE, "bold"), text_color=warning_color).pack(side="left")

    # --- Clean, Centered Body Message ---
    lbl_msg = ctk.CTkLabel(dialog, text=apply_bidi(message), font=(messages.FONT_FAMILY, messages.FONT_SIZE_LARGE, "bold"), wraplength=380, justify="center")
    lbl_msg.pack(pady=(5, 20), padx=20)
    
    btn_frame = ctk.CTkFrame(dialog, fg_color="transparent")
    btn_frame.pack()
    
    big_btn_font = (messages.FONT_FAMILY, messages.FONT_SIZE_MAIN + 2, "bold")

    ctk.CTkButton(btn_frame, text=apply_bidi(messages.BTN_YES), font=big_btn_font, fg_color="#28a745", hover_color="#218838", width=110, height=30, command=lambda: set_res(True)).pack(side="left", padx=10)
    ctk.CTkButton(btn_frame, text=apply_bidi(messages.BTN_NO), font=big_btn_font, fg_color=config.COLOR_RED, hover_color=config.COLOR_RED_HOVER, width=110, height=30, command=lambda: set_res(False)).pack(side="left", padx=10)
    
    dialog.wait_window()
    return result[0]