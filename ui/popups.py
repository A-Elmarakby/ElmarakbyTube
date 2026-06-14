"""
File: popups.py
What it does: Contains all the popup windows (alerts, questions).
Why we need it: To keep the main screen code clean and separated from these small dialogs.
"""

import customtkinter as ctk
import os
import sys
import json
import logging
import webbrowser
import re
from PIL import Image

import config
import messages
from core.utils import apply_bidi, load_user_data, update_user_data
from core.analytics import increment_stat # Added to save clicks

# ==========================================
# UI Helpers & Smart Icon Loader
# ==========================================
def add_focus_visuals(*buttons):
    """
    Changes the button color to its hover state when focused via Tab key.
    This creates a clear visual cue for keyboard navigation.
    """
    for btn in buttons:
        orig_color = btn.cget("fg_color")
        hover_color = btn.cget("hover_color")
        
        # When Tab focuses the button, make it look hovered
        btn.bind("<FocusIn>", lambda e, b=btn, hc=hover_color: b.configure(fg_color=hc))
        # When Tab leaves the button, revert to normal
        btn.bind("<FocusOut>", lambda e, b=btn, oc=orig_color: b.configure(fg_color=oc))


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
    # Sanitize message: Remove terminal ANSI color codes before displaying in UI
    if isinstance(message, str):
        message = re.sub(r'\x1b\[[0-9;]*m', '', message)

    if parent_window is None:
        import __main__
        if hasattr(__main__, 'app'):
            parent_window = __main__.app

    dialog = ctk.CTkToplevel(parent_window)
    dialog.title(apply_bidi(title)) 
    
    # Set icon IMMEDIATELY before centering or grabbing focus
    add_dialog_icon(dialog)
    
    # Dynamic height so a long message is never clipped and the OK button (pinned
    # to the bottom below) always stays visible. Capped at ~85% of the screen.
    if custom_height:
        height = custom_height
    else:
        _text = str(message)
        _lines = sum(max(1, (len(line) // 38) + 1) for line in _text.split('\n'))
        try:
            _max_h = min(560, int(dialog.winfo_screenheight() * 0.85))
        except Exception:
            _max_h = 560
        height = max(config.POPUP_HEIGHT, min(180 + _lines * 28, _max_h))
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
    
    # Pin the OK button to the bottom FIRST so a long message can never push it off-screen.
    btn_ok = ctk.CTkButton(dialog, text=apply_bidi(messages.BTN_OK), fg_color="#555", hover_color="#333", width=100, command=dialog.destroy)
    btn_ok.pack(side="bottom", pady=(10, 20))

    lbl_msg = ctk.CTkLabel(dialog, text=apply_bidi(message), font=(messages.FONT_FAMILY, messages.FONT_SIZE_POPUP_BODY), wraplength=400, justify="center")
    lbl_msg.pack(side="top", expand=True, pady=(0, 10), padx=20)
    
    # Enter maps to the button's command, Escape maps explicitly to destroy
    dialog.bind("<Return>", lambda event: btn_ok.invoke())
    dialog.bind("<KP_Enter>", lambda event: btn_ok.invoke())
    dialog.bind("<Escape>", lambda event: dialog.destroy())
    
    btn_ok.focus()
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

    btn_no = ctk.CTkButton(btn_frame, text=apply_bidi(messages.BTN_NO), font=big_btn_font, fg_color=config.COLOR_RED, hover_color=config.COLOR_RED_HOVER, width=110, height=30, command=lambda: set_res(False))
    btn_no.pack(side="left", padx=10)
    
    btn_yes = ctk.CTkButton(btn_frame, text=apply_bidi(messages.BTN_YES), font=big_btn_font, fg_color="#28a745", hover_color="#218838", width=110, height=30, command=lambda: set_res(True))
    btn_yes.pack(side="left", padx=10)
    
    # Escape always cancels (Safe exit)
    dialog.bind("<Escape>", lambda event: set_res(False))
    
    # Disable Tab key navigation completely to prevent accidental selections
    dialog.bind("<Tab>", lambda event: "break")
    
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
    
    # --- SMART DYNAMIC HEIGHT CALCULATION ---
    # Count lines based on new lines (\n) or total text length
    new_lines = message.count('\n')
    wrapped_lines = len(message) // 40  # assume each line is about 40 characters
    estimated_lines = max(new_lines, wrapped_lines) + 1
    
    # Base height is 130, and add 25 for each extra line, minimum 160 for short text
    dynamic_height = max(160, 130 + (estimated_lines * 25))
    
    center_toplevel(alert_dlg, 400, dynamic_height, parent_window)
    alert_dlg.transient(parent_window)
    alert_dlg.grab_set()
    
    config.play_sound("warning")
    btn_font = (messages.FONT_FAMILY, messages.FONT_SIZE_MAIN, "bold")
    
    lbl = ctk.CTkLabel(alert_dlg, text=apply_bidi(message), font=btn_font, wraplength=350)
    lbl.pack(pady=(30, 20))
    
    # Use Arabic OK button from messages
    try:
        ok_text = apply_bidi(messages.BTN_OK)
    except Exception:
        ok_text = "OK"
        
    btn_ok = ctk.CTkButton(alert_dlg, text=ok_text, font=btn_font, fg_color="#555", hover_color="#333", width=80, command=alert_dlg.destroy)
    btn_ok.pack()
    
    # Enter maps to the button's command, Escape maps explicitly to destroy
    alert_dlg.bind("<Return>", lambda event: btn_ok.invoke())
    alert_dlg.bind("<KP_Enter>", lambda event: btn_ok.invoke())
    alert_dlg.bind("<Escape>", lambda event: alert_dlg.destroy())
    
    btn_ok.focus()
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

    btn_slow = ctk.CTkButton(btn_frame, **slow_btn_kwargs)
    btn_slow.pack(side="left", padx=15)
    
    btn_fast = ctk.CTkButton(btn_frame, **fast_btn_kwargs)
    btn_fast.pack(side="left", padx=15)
    
    # Escape always cancels (Safe exit)
    dialog.bind("<Escape>", lambda event: set_res("cancel"))
    
    # Disable Tab key navigation completely to prevent accidental selections
    dialog.bind("<Tab>", lambda event: "break")
    
    dialog.wait_window()
    return result[0]

def show_contact_popup(parent_window=None):
    import urllib.parse
    import logging
    import tkinter as tk
    from PIL import Image
    
    if parent_window is None:
        import __main__
        if hasattr(__main__, 'app'):
            parent_window = __main__.app

    # Record contact click
    try:
        from core.analytics import increment_stat
        increment_stat("1_app_lifecycle", "main_contact_btn_clicks", sub_category="support_interactions")
    except Exception:
        pass

    dialog = ctk.CTkToplevel(parent_window)
    dialog.title("Contact Us")
    
    add_dialog_icon(dialog)
    
    # Start with 4 buttons size
    center_toplevel(dialog, 420, 200, parent_window)
    dialog.transient(parent_window)
    dialog.grab_set()
    
    dialog._email_expanded = False
    dialog._reset_timer = None # Timer to reset button colors
    dialog._gmail_tracked = False # Count "Open in Gmail" once per popup open (reopen = new count)
    
    lbl = ctk.CTkLabel(dialog, text=apply_bidi(messages.MSG_CONTACT_WHERE), font=(messages.FONT_FAMILY, messages.FONT_SIZE_POPUP_TITLE, "bold"))
    lbl.pack(pady=(20, 15))
    
    btn_frame = ctk.CTkFrame(dialog, fg_color="transparent")
    btn_frame.pack()
    btn_font = (messages.FONT_FAMILY, messages.FONT_SIZE_MAIN, "bold")
    
    email_expansion_frame = ctk.CTkFrame(dialog, fg_color="transparent")
    email_address = messages.URL_EMAIL.replace("mailto:", "")
    
    def open_social_and_track(platform_name, url):
        try:
            from core.analytics import increment_stat
            key_name = f"{platform_name}_clicks"
            increment_stat("1_app_lifecycle", key_name, sub_category="support_interactions")
            webbrowser.open(url)
        except Exception as e:
            logging.critical(f"Critical error opening link for {platform_name}: {str(e)}", exc_info=True)

    # --- The main engine to change both buttons together ---
    def show_copied_state():
        if dialog._reset_timer is not None:
            dialog.after_cancel(dialog._reset_timer)
            
        try:
            copied_img = ctk.CTkImage(
                light_image=Image.open(config.COPIED_ICON_PATH), 
                dark_image=Image.open(config.COPIED_ICON_PATH), 
                size=config.COPIED_ICON_SIZE
            )
            # Use image on the right, text on the left
            copied_kwargs = {
                "image": copied_img, 
                "compound": "right", 
                "text": apply_bidi(f"{messages.BTN_COPIED}" )
            }
        except Exception as e:
            logging.error(f"Missing Copied icon '{config.COPIED_ICON_PATH}': {str(e)}")
            # Use image=None to center text, and put emoji on the right
            copied_kwargs = {
                "image": None, 
                "text": apply_bidi(f"{messages.BTN_COPIED} {config.COPIED_FALLBACK_EMOJI}")
            }

        # Update Main Email Button
        if email_btn.winfo_exists():
            email_btn.configure(fg_color=config.COLOR_GREEN, hover_color=config.COLOR_GREEN_HOVER, **copied_kwargs)
        
        # Update Bottom Copy Button
        if hasattr(dialog, 'copy_btn') and dialog.copy_btn.winfo_exists():
            dialog.copy_btn.configure(fg_color=config.COLOR_GREEN, hover_color=config.COLOR_GREEN_HOVER, **copied_kwargs)
            
        def revert_state():
            # Use image=None to clean the button and fix the text in the center
            if email_btn.winfo_exists():
                email_btn.configure(text="Email", image=None, fg_color=config.SOCIAL_EMAIL_COLOR, hover_color=config.SOCIAL_EMAIL_HOVER)
            if hasattr(dialog, 'copy_btn') and dialog.copy_btn.winfo_exists():
                dialog.copy_btn.configure(text=apply_bidi(messages.BTN_COPY), image=None, fg_color=config.COPY_BTN_COLOR, hover_color=config.COPY_BTN_HOVER)
                
        # Wait and then return to normal
        dialog._reset_timer = dialog.after(config.EMAIL_COPY_DURATION_MS, revert_state)
    # ----------------------------------------------

    # Smart copy function
    email_tracked_flag = [False]
    def trigger_copy(event=None):
        if event:
            try:
                selected_text = dialog.email_entry.selection_get()
                # If user selected a small part, copy it silently
                if selected_text and selected_text != email_address:
                    dialog.clipboard_clear()
                    dialog.clipboard_append(selected_text)
                    return "break"
            except Exception:
                pass # Did not select anything
                
        # Full copy
        dialog.clipboard_clear()
        dialog.clipboard_append(email_address)
        config.play_sound("success")
        show_copied_state()
        
        try:
            if not email_tracked_flag[0]:
                from core.analytics import increment_stat
                increment_stat("1_app_lifecycle", "email_clicks", sub_category="support_interactions")
                email_tracked_flag[0] = True
        except: pass
        
        return "break"

    def handle_email_click():
        try:
            trigger_copy()
            
            # Show the bottom frame only once
            if not dialog._email_expanded:
                dialog._email_expanded = True
                
                # Make window height 310 to remove empty space
                current_geom = dialog.geometry()
                try:
                    x_y = current_geom.split('+')[1:]
                    dialog.geometry(f"420x270+{x_y[0]}+{x_y[1]}")
                except:
                    dialog.geometry("420x270")
                    
                email_expansion_frame.pack(fill="x", padx=25, pady=(15, 0))
                
                row1 = ctk.CTkFrame(email_expansion_frame, fg_color="transparent")
                row1.pack(fill="x", pady=(0, 10))
                
                dialog.email_entry = ctk.CTkEntry(row1, font=(messages.FONT_FAMILY, messages.FONT_SIZE_MAIN), text_color="#aaaaaa", justify="center")
                dialog.email_entry.pack(side="left", fill="x", expand=True, padx=(0, 10))
                dialog.email_entry.insert(0, email_address)
                dialog.email_entry.configure(state="readonly")
                
                def select_all(event=None):
                    dialog.email_entry.select_range(0, 'end')
                    return "break"
                    
                def show_mini_menu(event):
                    dialog.email_entry.focus()
                    menu = tk.Menu(dialog, tearoff=0, font=(messages.FONT_FAMILY, 10), bg=config.MENU_BG_COLOR, fg=config.MENU_TEXT_COLOR, activebackground=config.MENU_HOVER_COLOR, activeforeground="white", relief="flat", bd=1)
                    menu.add_command(label="Copy", command=trigger_copy)
                    menu.add_command(label="Cut", command=trigger_copy)
                    menu.add_command(label="Select All", command=select_all)
                    menu.tk_popup(event.x_root, event.y_root)

                dialog.email_entry.bind("<Button-3>", show_mini_menu)
                dialog.email_entry.bind("<Control-c>", trigger_copy)
                dialog.email_entry.bind("<Control-x>", trigger_copy) 
                dialog.email_entry.bind("<Control-a>", select_all)
                
                dialog.copy_btn = ctk.CTkButton(row1, text=apply_bidi(messages.BTN_COPY), font=btn_font, width=70, fg_color=config.COPY_BTN_COLOR, hover_color=config.COPY_BTN_HOVER, command=trigger_copy)
                dialog.copy_btn.pack(side="right")
                
                # Gmail button with safe URL
                subject = urllib.parse.quote(messages.MSG_GMAIL_SUBJECT)
                body = urllib.parse.quote(messages.MSG_GMAIL_BODY)
                gmail_url = f"https://mail.google.com/mail/?view=cm&fs=1&to={email_address}&su={subject}&body={body}"
                
                # Count "Open in Gmail" once per popup open; reopening the popup counts again.
                # Always opens Gmail on every click, but only records the intent once.
                def handle_gmail_click(u=gmail_url):
                    try:
                        if not getattr(dialog, '_gmail_tracked', False):
                            increment_stat("1_app_lifecycle", "open_in_gmail_clicks", sub_category="support_interactions")
                            dialog._gmail_tracked = True
                        webbrowser.open(u)
                    except Exception as e:
                        logging.critical(f"Critical error opening Gmail: {str(e)}", exc_info=True)

                # Make button, put image on the left side
                gmail_btn = ctk.CTkButton(email_expansion_frame, height=35, text="", font=btn_font, text_color="white", fg_color=config.SOCIAL_GMAIL_COLOR, hover_color=config.SOCIAL_GMAIL_HOVER, compound="left", command=handle_gmail_click)
                gmail_btn.pack(fill="x", pady=(0, 5))
                
                try:
                    gmail_img = ctk.CTkImage(
                        light_image=Image.open(config.GMAIL_ICON_PATH), 
                        dark_image=Image.open(config.GMAIL_ICON_PATH), 
                        size=config.GMAIL_ICON_SIZE
                    )
                    gmail_btn.configure(image=gmail_img, text=apply_bidi(f"  {messages.BTN_OPEN_GMAIL}"))
                except Exception as img_err:
                    logging.error(f"Missing Gmail icon '{config.GMAIL_ICON_PATH}': {str(img_err)}")
                    # Use image=None and emoji on the left
                    gmail_btn.configure(image=None, text=apply_bidi(f"{config.GMAIL_FALLBACK_EMOJI} {messages.BTN_OPEN_GMAIL}"))
                    
                show_copied_state()

        except Exception as e:
            logging.critical(f"Critical error in email popup: {str(e)}", exc_info=True)

    # Basic social buttons
    ctk.CTkButton(btn_frame, text="LinkedIn", font=btn_font, fg_color=config.SOCIAL_LINKEDIN_COLOR, hover=True, hover_color=config.SOCIAL_LINKEDIN_HOVER, width=config.SOCIAL_BTN_WIDTH, command=lambda: open_social_and_track("linkedin", messages.URL_LINKEDIN)).grid(row=0, column=0, padx=10, pady=10)
    ctk.CTkButton(btn_frame, text="WhatsApp", font=btn_font, fg_color=config.SOCIAL_WHATSAPP_COLOR, hover=True, hover_color=config.SOCIAL_WHATSAPP_HOVER, width=config.SOCIAL_BTN_WIDTH, command=lambda: open_social_and_track("whatsapp", messages.URL_WHATSAPP)).grid(row=0, column=1, padx=10, pady=10)
    ctk.CTkButton(btn_frame, text="GitHub", font=btn_font, fg_color=config.SOCIAL_GITHUB_COLOR, hover=True, hover_color=config.SOCIAL_GITHUB_HOVER, width=config.SOCIAL_BTN_WIDTH, command=lambda: open_social_and_track("github", messages.URL_GITHUB)).grid(row=1, column=0, padx=10, pady=10)
    
    email_btn = ctk.CTkButton(btn_frame, text="Email", font=btn_font, fg_color=config.SOCIAL_EMAIL_COLOR, hover=True, hover_color=config.SOCIAL_EMAIL_HOVER, width=config.SOCIAL_BTN_WIDTH, command=handle_email_click)
    email_btn.grid(row=1, column=1, padx=10, pady=10)    
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
    
    btn_leave = ctk.CTkButton(btn_frame, text=apply_bidi(red_text), font=big_btn_font, fg_color=config.EXIT_LEAVE_COLOR, hover_color=config.EXIT_LEAVE_HOVER, width=110, height=30, command=lambda: set_res("leave"))
    btn_leave.pack(side="left", padx=10)
    
    btn_stay = ctk.CTkButton(btn_frame, text=apply_bidi(green_text), font=big_btn_font, fg_color=config.EXIT_STAY_COLOR, hover_color=config.EXIT_STAY_HOVER, width=110, height=30, command=lambda: set_res("stay"))
    btn_stay.pack(side="left", padx=10)
    
    # Escape always stays safely in the app (Safe exit)
    dialog.bind("<Escape>", lambda event: set_res("stay"))
    
    # Disable Tab key navigation completely to prevent accidental selections
    dialog.bind("<Tab>", lambda event: "break")
    
    dialog.wait_window()
    return result[0]

def is_valid_name(name):
    # Remove extra spaces and make letters small for checking
    clean_name = re.sub(r"\s+", " ", name.strip().lower())
    
    if not clean_name: return False, messages.MSG_NAME_REQUIRED

    # Safe regex pattern to catch refusal words without blocking real names
    reject_pattern = (
        r"^(لا+|لأ+|لاء+|no+|n+|nn+|nah|nope|cancel|skip( it)?|gh+|hg|la+)$|"
        r"^(مش|يا عم|يعم|لا يا عم)(\s|$)|"
        r"^(مش |يا عم |يعم |لا يا عم )(عايز|عاوز|لا|هقول|قايل|مهتم|فارق|مهم|دعوه|فكك|طنش|سر|مجهول|ماشي).*|"
        r"^(فكك|طنش|سر|مجهول|ولا حاجة|اي حاجة|ولا يهمك|براحتي|ماشي)$"
    )
    
    # Return custom rejected message if it matches the pattern
    if re.match(reject_pattern, clean_name):
        return False, messages.MSG_NAME_REJECTED

    if len(clean_name) < config.NAME_MIN_LENGTH or len(clean_name) > config.NAME_MAX_LENGTH: return False, messages.MSG_INVALID_NAME
    if not config.NAME_ALLOW_NUMBERS and any(char.isdigit() for char in clean_name): return False, messages.MSG_INVALID_NAME
    if not config.NAME_ALLOW_SYMBOLS:
        if not clean_name.replace(" ", "").isalpha(): return False, messages.MSG_INVALID_NAME
    if config.NAME_MAX_REPEATS > 0:
        for i in range(len(clean_name) - config.NAME_MAX_REPEATS):
            chunk = clean_name[i : i + config.NAME_MAX_REPEATS + 1]
            if len(set(chunk)) == 1 and chunk[0] != " ": return False, messages.MSG_INVALID_NAME
            
    return True, ""

def show_welcome_onboarding(parent_window=None):
    if parent_window is None:
        import __main__
        if hasattr(__main__, 'app'):
            parent_window = __main__.app

    # Check if the user already provided their name
    if "name" in load_user_data():
        return

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
            # Safely save the name without overwriting other future settings
            update_user_data("name", name)
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
            btn_welcome = ctk.CTkButton(greet_dialog, text=apply_bidi(messages.WELCOME_BTN), font=btn_font, fg_color=config.WELCOME_BTN_COLOR, hover=True, hover_color=config.WELCOME_BTN_HOVER, width=config.WELCOME_BTN_WIDTH, command=greet_dialog.destroy)
            btn_welcome.pack()
            
            greet_dialog.bind("<Return>", lambda event: greet_dialog.destroy())
            greet_dialog.bind("<KP_Enter>", lambda event: greet_dialog.destroy())
            greet_dialog.bind("<Escape>", lambda event: greet_dialog.destroy())
            
            btn_welcome.focus()
        else:
            custom_alert_dialog(messages.TITLE_ALERT, error_msg, parent_window)
            
    btn_confirm = ctk.CTkButton(dialog, text=apply_bidi(messages.BTN_CONFIRM_NAME), font=btn_font, fg_color=config.COLOR_MAGENTA, hover_color=config.COLOR_MAGENTA_HOVER, command=save_name)
    btn_confirm.pack(pady=10)

    # Keyboard shortcuts to save the name instantly
    dialog.bind("<Return>", lambda event: save_name())
    dialog.bind("<KP_Enter>", lambda event: save_name())
    
    # Make typing start immediately when window opens
    name_entry.focus()


def show_1gb_warning_dialog(parent_window=None):
    if parent_window is None:
        import __main__
        if hasattr(__main__, 'app'):
            parent_window = __main__.app

    dialog = ctk.CTkToplevel(parent_window)
    dialog.title(apply_bidi(messages.TITLE_1GB_WARNING))
    
    add_dialog_icon(dialog)
    
    center_toplevel(dialog, 400, 220, parent_window)
    dialog.transient(parent_window)
    dialog.grab_set()
    
    # Play the dedicated data warning audio type configured in config
    config.play_sound("data_warning")
    
    # Show the funny message
    lbl = ctk.CTkLabel(dialog, text=apply_bidi(messages.MSG_1GB_WARNING), font=(messages.FONT_FAMILY, messages.FONT_SIZE_LARGE, "bold"), wraplength=350, justify="center")
    lbl.pack(pady=(20, 15))
    
    # Checkbox for opt-out preference
    chk = ctk.CTkCheckBox(dialog, text=apply_bidi(messages.CHK_DONT_SHOW), font=(messages.FONT_FAMILY, messages.FONT_SIZE_MAIN), checkbox_height=20, checkbox_width=20)
    chk.pack(pady=(0, 15))
    
    def on_continue():
        # Save choice to hard drive if user checked the box (1 means checked)
        if chk.get() == 1:
            update_user_data("hide_1gb_warning", True)
        dialog.destroy()

    btn_font = (messages.FONT_FAMILY, messages.FONT_SIZE_MAIN, "bold")
    btn_continue = ctk.CTkButton(dialog, text=apply_bidi(messages.BTN_CONTINUE), font=btn_font, fg_color="#28a745", hover_color="#218838", width=120, command=on_continue)
    btn_continue.pack()
    
    # Enter triggers the main button's command, Escape closes without saving
    dialog.bind("<Return>", lambda event: btn_continue.invoke())
    dialog.bind("<KP_Enter>", lambda event: btn_continue.invoke())
    dialog.bind("<Escape>", lambda event: dialog.destroy())
    
    btn_continue.focus()
    dialog.wait_window()
