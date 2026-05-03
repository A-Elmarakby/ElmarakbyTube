"""
File: popups.py
What it does: Contains all the popup windows (alerts, questions).
Why we need it: To keep the main screen code clean and separated from these small dialogs.
"""

import customtkinter as ctk
import os
import sys
import json
import webbrowser
from PIL import Image

import config
import messages
from core.utils import apply_bidi

# ==========================================
# UI Helpers & Smart Icon Loader
# ==========================================

def add_dialog_icon(dialog):
    """
    Final strong fix:
    1. Run now (no flicker).
    2. Run again after 200ms (fix Windows redraw).
    3. Keep memory (do not lose icon).
    """
    def apply():
        try: 
            # wm_iconbitmap is stronger on Windows
            dialog.wm_iconbitmap(config.ICON_FILE)
        except Exception: 
            pass

    # Step 1: run now (window opens with icon)
    apply()

    # Step 2: run after 200 ms (fix Windows update)
    dialog.after(200, apply)

    # Step 3: keep memory (Python does not remove path)
    dialog._icon_path_ref = config.ICON_FILE

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

# ==========================================
# Core Message Boxes
# ==========================================

def custom_msg_box(title, message, msg_type="error", parent_window=None, custom_height=None):
    if parent_window is None:
        import __main__
        if hasattr(__main__, 'app'):
            parent_window = __main__.app

    dialog = ctk.CTkToplevel(parent_window)
    dialog.title(apply_bidi(title)) 
    
    # Set icon IMMEDIATELY before centering or grabbing focus
    add_dialog_icon(dialog)
    
    height = custom_height if custom_height else config.POPUP_HEIGHT
    center_toplevel(dialog, config.POPUP_WIDTH, height, parent_window)
    dialog.transient(parent_window)
    dialog.grab_set()
    
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
    if parent_window is None:
        import __main__
        if hasattr(__main__, 'app'):
            parent_window = __main__.app

    dialog = ctk.CTkToplevel(parent_window)
    dialog.title(apply_bidi(title))
    
    add_dialog_icon(dialog)
    
    center_toplevel(dialog, config.POPUP_WIDTH, config.POPUP_HEIGHT, parent_window)
    dialog.transient(parent_window)
    dialog.grab_set()

    config.play_sound("warning")
    result = [False]
    def set_res(val):
        result[0] = val
        dialog.destroy()
        
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

    lbl_msg = ctk.CTkLabel(dialog, text=apply_bidi(message), font=(messages.FONT_FAMILY, messages.FONT_SIZE_LARGE, "bold"), wraplength=380, justify="center")
    lbl_msg.pack(pady=(5, 20), padx=20)
    
    btn_frame = ctk.CTkFrame(dialog, fg_color="transparent")
    btn_frame.pack()
    
    big_btn_font = (messages.FONT_FAMILY, messages.FONT_SIZE_MAIN + 2, "bold")

    ctk.CTkButton(btn_frame, text=apply_bidi(messages.BTN_YES), font=big_btn_font, fg_color="#28a745", hover_color="#218838", width=110, height=30, command=lambda: set_res(True)).pack(side="left", padx=10)
    ctk.CTkButton(btn_frame, text=apply_bidi(messages.BTN_NO), font=big_btn_font, fg_color=config.COLOR_RED, hover_color=config.COLOR_RED_HOVER, width=110, height=30, command=lambda: set_res(False)).pack(side="left", padx=10)
    
    dialog.wait_window()
    return result[0]

def custom_alert_dialog(title, message, parent_window=None):
    if parent_window is None:
        import __main__
        if hasattr(__main__, 'app'):
            parent_window = __main__.app

    alert_dlg = ctk.CTkToplevel(parent_window)
    alert_dlg.title(apply_bidi(title))
    
    add_dialog_icon(alert_dlg)
    
    center_toplevel(alert_dlg, 400, 160, parent_window)
    alert_dlg.transient(parent_window)
    alert_dlg.grab_set()
    
    config.play_sound("warning")
    btn_font = (messages.FONT_FAMILY, messages.FONT_SIZE_MAIN, "bold")
    
    lbl = ctk.CTkLabel(alert_dlg, text=apply_bidi(message), font=btn_font, wraplength=350)
    lbl.pack(pady=(30, 20))
    ctk.CTkButton(alert_dlg, text="OK", font=btn_font, fg_color="#555", hover_color="#333", width=80, command=alert_dlg.destroy).pack()
    alert_dlg.wait_window()


# ==========================================
# Feature Dialogs (Speed, Contact, Exit, Welcome)
# ==========================================

def ask_conversion_speed(parent_window=None):
    if parent_window is None:
        import __main__
        if hasattr(__main__, 'app'):
            parent_window = __main__.app

    dialog = ctk.CTkToplevel(parent_window)
    dialog.title(apply_bidi(messages.TITLE_SPEED))
    
    add_dialog_icon(dialog)
    
    center_toplevel(dialog, 450, 160, parent_window)
    dialog.transient(parent_window) 
    dialog.grab_set() 
    
    config.play_sound("info")
    result = ["cancel"] 
    def set_res(val):
        result[0] = val
        dialog.destroy()
        
    lbl = ctk.CTkLabel(dialog, text=apply_bidi(messages.MSG_SPEED_PROMPT), font=(messages.FONT_FAMILY, messages.FONT_SIZE_LARGE, "bold"))
    lbl.pack(pady=20)
    
    btn_frame = ctk.CTkFrame(dialog, fg_color="transparent")
    btn_frame.pack()
    
    big_btn_font = (messages.FONT_FAMILY, messages.FONT_SIZE_MAIN + 2, "bold")

    fast_btn_kwargs = {
        "font": big_btn_font, "fg_color": "#28a745", "hover_color": "#218838",
        "width": 120, "height": 35, "command": lambda: set_res("fast")
    }
    
    slow_btn_kwargs = {
        "font": big_btn_font, "fg_color": config.COLOR_RED, "hover_color": config.COLOR_RED_HOVER,
        "width": 120, "height": 35, "command": lambda: set_res("slow")
    }
    
    # Garbage Collection Protection: Save images as attributes of the dialog
    dialog._images = []
    
    try:
        fast_img = ctk.CTkImage(light_image=Image.open(config.SPEED_FAST_ICON_PATH), dark_image=Image.open(config.SPEED_FAST_ICON_PATH), size=config.SPEED_ICON_SIZE)
        dialog._images.append(fast_img) # Protect from GC
        fast_btn_kwargs["image"] = fast_img
        fast_btn_kwargs["text"] = apply_bidi(f"  {messages.BTN_FAST}")
    except Exception:
        fast_btn_kwargs["text"] = apply_bidi(f"{messages.BTN_FAST} {config.SPEED_FAST_FALLBACK_EMOJI}")
        
    try:
        slow_img = ctk.CTkImage(light_image=Image.open(config.SPEED_SLOW_ICON_PATH), dark_image=Image.open(config.SPEED_SLOW_ICON_PATH), size=config.SPEED_ICON_SIZE)
        dialog._images.append(slow_img) # Protect from GC
        slow_btn_kwargs["image"] = slow_img
        slow_btn_kwargs["text"] = apply_bidi(f"  {messages.BTN_SLOW}")
    except Exception:
        slow_btn_kwargs["text"] = apply_bidi(f"{messages.BTN_SLOW} {config.SPEED_SLOW_FALLBACK_EMOJI}")

    ctk.CTkButton(btn_frame, **fast_btn_kwargs).pack(side="left", padx=15)
    ctk.CTkButton(btn_frame, **slow_btn_kwargs).pack(side="left", padx=15)
    
    dialog.wait_window()
    return result[0]

def show_contact_popup(parent_window=None):
    if parent_window is None:
        import __main__
        if hasattr(__main__, 'app'):
            parent_window = __main__.app

    dialog = ctk.CTkToplevel(parent_window)
    dialog.title("Contact Us")
    
    add_dialog_icon(dialog)
    
    center_toplevel(dialog, 400, 250, parent_window)
    dialog.transient(parent_window)
    dialog.grab_set()
    
    lbl = ctk.CTkLabel(dialog, text=apply_bidi(messages.MSG_CONTACT_WHERE), font=(messages.FONT_FAMILY, messages.FONT_SIZE_POPUP_TITLE, "bold"))
    lbl.pack(pady=(20, 15))
    
    btn_frame = ctk.CTkFrame(dialog, fg_color="transparent")
    btn_frame.pack()
    btn_font = (messages.FONT_FAMILY, messages.FONT_SIZE_MAIN, "bold")
    
    ctk.CTkButton(btn_frame, text="LinkedIn", font=btn_font, fg_color=config.SOCIAL_LINKEDIN_COLOR, hover=True, hover_color=config.SOCIAL_LINKEDIN_HOVER, width=config.SOCIAL_BTN_WIDTH, command=lambda: webbrowser.open(messages.URL_LINKEDIN)).grid(row=0, column=0, padx=10, pady=10)
    ctk.CTkButton(btn_frame, text="WhatsApp", font=btn_font, fg_color=config.SOCIAL_WHATSAPP_COLOR, hover=True, hover_color=config.SOCIAL_WHATSAPP_HOVER, width=config.SOCIAL_BTN_WIDTH, command=lambda: webbrowser.open(messages.URL_WHATSAPP)).grid(row=0, column=1, padx=10, pady=10)
    ctk.CTkButton(btn_frame, text="GitHub", font=btn_font, fg_color=config.SOCIAL_GITHUB_COLOR, hover=True, hover_color=config.SOCIAL_GITHUB_HOVER, width=config.SOCIAL_BTN_WIDTH, command=lambda: webbrowser.open(messages.URL_GITHUB)).grid(row=1, column=0, padx=10, pady=10)
    ctk.CTkButton(btn_frame, text="Email", font=btn_font, fg_color=config.SOCIAL_EMAIL_COLOR, hover=True, hover_color=config.SOCIAL_EMAIL_HOVER, width=config.SOCIAL_BTN_WIDTH, command=lambda: webbrowser.open(messages.URL_EMAIL)).grid(row=1, column=1, padx=10, pady=10)

def v2_exit_dialog(title, message, green_text, red_text, parent_window=None):
    if parent_window is None:
        import __main__
        if hasattr(__main__, 'app'):
            parent_window = __main__.app

    dialog = ctk.CTkToplevel(parent_window)
    dialog.title(apply_bidi(title)) 
    
    add_dialog_icon(dialog)
    
    center_toplevel(dialog, 450, 200, parent_window)
    dialog.transient(parent_window)
    dialog.grab_set()
    
    config.play_sound("warning")
    result = ["cancel"]
    def set_res(val):
        result[0] = val
        dialog.destroy()
        
    lbl = ctk.CTkLabel(dialog, text=apply_bidi(message), font=(messages.FONT_FAMILY, messages.FONT_SIZE_LARGE, "bold"), wraplength=400, justify="center")
    lbl.pack(pady=30, padx=20)
    
    btn_frame = ctk.CTkFrame(dialog, fg_color="transparent")
    btn_frame.pack()
    big_btn_font = (messages.FONT_FAMILY, messages.FONT_SIZE_MAIN, "bold")
    
    ctk.CTkButton(btn_frame, text=apply_bidi(green_text), font=big_btn_font, fg_color=config.EXIT_STAY_COLOR, hover_color=config.EXIT_STAY_HOVER, width=110, height=30, command=lambda: set_res("stay")).pack(side="left", padx=10)
    ctk.CTkButton(btn_frame, text=apply_bidi(red_text), font=big_btn_font, fg_color=config.EXIT_LEAVE_COLOR, hover_color=config.EXIT_LEAVE_HOVER, width=110, height=30, command=lambda: set_res("leave")).pack(side="left", padx=10)
    dialog.wait_window()
    return result[0]

def is_valid_name(name):
    name = name.strip()
    if not name: return False, messages.MSG_NAME_REQUIRED
    if len(name) < config.NAME_MIN_LENGTH or len(name) > config.NAME_MAX_LENGTH: return False, messages.MSG_INVALID_NAME
    if not config.NAME_ALLOW_NUMBERS and any(char.isdigit() for char in name): return False, messages.MSG_INVALID_NAME
    if not config.NAME_ALLOW_SYMBOLS:
        if not name.replace(" ", "").isalpha(): return False, messages.MSG_INVALID_NAME
    if config.NAME_MAX_REPEATS > 0:
        for i in range(len(name) - config.NAME_MAX_REPEATS):
            chunk = name[i : i + config.NAME_MAX_REPEATS + 1]
            if len(set(chunk)) == 1 and chunk[0] != " ": return False, messages.MSG_INVALID_NAME
    return True, ""

def show_welcome_onboarding(parent_window=None):
    if parent_window is None:
        import __main__
        if hasattr(__main__, 'app'):
            parent_window = __main__.app

    if config.USER_DATA_SAVE_DIR.strip():
        base_dir = config.USER_DATA_SAVE_DIR
    else:
        appdata = os.getenv('APPDATA')
        if appdata: base_dir = os.path.join(appdata, "ElmarakbyTube")
        else:
            if getattr(sys, 'frozen', False): base_dir = os.path.dirname(sys.executable)
            else: base_dir = os.path.dirname(os.path.abspath(__file__))
            
    os.makedirs(base_dir, exist_ok=True)
    data_file = os.path.join(base_dir, config.USER_DATA_FILE_NAME)
    
    if os.path.exists(data_file): return

    dialog = ctk.CTkToplevel(parent_window)
    dialog.title(messages.TITLE_WELCOME)
    
    add_dialog_icon(dialog)
    
    center_toplevel(dialog, 450, 220, parent_window)
    dialog.transient(parent_window)
    dialog.grab_set()
    
    btn_font = (messages.FONT_FAMILY, messages.FONT_SIZE_MAIN, "bold")
    
    def on_welcome_close():
        custom_alert_dialog(messages.TITLE_ALERT, messages.MSG_NAME_REQUIRED, parent_window)

    dialog.protocol("WM_DELETE_WINDOW", on_welcome_close)
    
    lbl = ctk.CTkLabel(dialog, text=apply_bidi(messages.MSG_WELCOME_ASK), font=(messages.FONT_FAMILY, messages.FONT_SIZE_LARGE, "bold"))
    lbl.pack(pady=(20, 10))
    
    name_entry = ctk.CTkEntry(
        dialog, placeholder_text=apply_bidi(messages.PLACEHOLDER_NAME), 
        placeholder_text_color="#999999", width=280, height=40, font=btn_font, justify="center"
    )
    name_entry.pack(pady=10)
    
    def save_name():
        name = name_entry.get().strip()
        is_valid, error_msg = is_valid_name(name)
        if is_valid:
            with open(data_file, "w", encoding="utf-8") as f:
                json.dump({"name": name}, f)
            dialog.destroy()
            
            first_name = name.split()[0]
            greet_msg = messages.MSG_WELCOME_GREET.replace("{name}", first_name)
            
            greet_dialog = ctk.CTkToplevel(parent_window)
            greet_dialog.title(messages.TITLE_WELCOME)
            
            add_dialog_icon(greet_dialog)
            
            center_toplevel(greet_dialog, 500, 200, parent_window)
            greet_dialog.transient(parent_window) 
            greet_dialog.grab_set()     
            
            config.play_sound("success")
            ctk.CTkLabel(greet_dialog, text=apply_bidi(greet_msg), font=(messages.FONT_FAMILY, messages.FONT_SIZE_POPUP_BODY, "bold")).pack(pady=40, padx=20)
            ctk.CTkButton(greet_dialog, text=apply_bidi(messages.WELCOME_BTN), font=btn_font, fg_color=config.WELCOME_BTN_COLOR, hover=True, hover_color=config.WELCOME_BTN_HOVER, width=config.WELCOME_BTN_WIDTH, command=greet_dialog.destroy).pack()
        else:
            custom_alert_dialog(messages.TITLE_ALERT, error_msg, parent_window)
            
    ctk.CTkButton(dialog, text=apply_bidi(messages.BTN_CONFIRM_NAME), font=btn_font, fg_color=config.COLOR_MAGENTA, hover_color=config.COLOR_MAGENTA_HOVER, command=save_name).pack(pady=10)