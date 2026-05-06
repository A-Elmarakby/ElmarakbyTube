"""
File: main.py
What it does: The main brain of the app. Connects logic (core) with UI (layout).
"""

import customtkinter as ctk
import yt_dlp
import threading
import os
import glob
import concurrent.futures

import config
import messages
from core.fetcher import get_video_info
from core.downloader import download_single_video, get_ydl_format_string
from core.converter import convert_single_file
from core.utils import format_size
from yt_dlp.utils import sanitize_filename

import ui.state as state
from ui.popups import custom_msg_box, custom_ask_yes_no, ask_conversion_speed, show_contact_popup, v2_exit_dialog, show_welcome_onboarding
import ui.layout as layout

# Keep UI functions available in main namespace to prevent breaking existing tests
from ui.layout import (
    safe_ui_update, safe_progress_update, update_global_status, 
    update_dynamic_totals, toggle_all, remove_selected, clear_list, add_video_row
)


# --- Window Setup ---
ctk.set_appearance_mode("Dark")
app = ctk.CTk()
app.geometry("1000x700")
app.title(config.APP_TITLE)

try:
    app.iconbitmap(default=config.ICON_FILE)
except:
    pass

# --- Custom Logger ---
class SilentLogger:
    def debug(self, msg): 
        if config.SHOW_TERMINAL_LOGS: print(msg)
    def warning(self, msg): 
        if config.SHOW_TERMINAL_LOGS: print(msg)
    def error(self, msg): 
        if config.SHOW_TERMINAL_LOGS: print(msg)

def global_hardware_shortcuts(event):
    has_ctrl = (event.state & 4) != 0
    has_shift = (event.state & 1) != 0

    if has_ctrl:
        keysym = event.keysym.lower()
        if event.keycode == 65 and keysym != 'a': 
            try:
                event.widget.select_range(0, 'end')
                event.widget.icursor('end')
            except: pass
            return "break"
        elif event.keycode == 67 and keysym != 'c': 
            try: event.widget.event_generate("<<Copy>>")
            except: pass
            return "break"
        elif event.keycode == 86 and keysym != 'v': 
            try: event.widget.event_generate("<<Paste>>")
            except: pass
            return "break"
        elif event.keycode == 88 and keysym != 'x': 
            try: event.widget.event_generate("<<Cut>>")
            except: pass
            return "break"
        elif event.keycode == 90 and keysym != 'z': 
            try:
                if has_shift: event.widget.event_generate("<<Redo>>") 
                else: event.widget.event_generate("<<Undo>>") 
            except: pass
            return "break"

def fetch_size_for_single_video(row_data, quality):
    if not state.fetch_event.is_set(): return 
    if not row_data['frame'].winfo_exists(): return
    if row_data['bytes_size'] != -1: return 

    app.after(0, lambda: layout.safe_ui_update(row_data['size_label'], text="...", text_color=config.COLOR_CYAN))

    ydl_opts = {
        'quiet': True, 
        'no_warnings': True, 
        'noplaylist': True, 
        'ignoreerrors': True,
        'logger': SilentLogger(),
        'format': get_ydl_format_string(quality),
        'socket_timeout': config.SOCKET_TIMEOUT,
        'retries': config.FETCH_RETRIES
    }
    
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(row_data['url'], download=False)
            
            if not state.fetch_event.is_set(): 
                app.after(0, lambda: layout.safe_ui_update(row_data['size_label'], text="N/A", text_color="white"))
                return
                
            if not info:
                row_data['bytes_size'] = 0
                app.after(0, lambda: layout.safe_ui_update(row_data['size_label'], text="Blocked", text_color=config.COLOR_RED))
                with state.error_lock:
                    state.consecutive_errors += 1
                    if state.consecutive_errors >= config.MAX_CONSECUTIVE_ERRORS:
                        state.fetch_event.clear()
                return

            file_size = info.get('filesize') or info.get('filesize_approx')
            if not file_size and 'requested_formats' in info:
                file_size = sum([f.get('filesize') or f.get('filesize_approx') or 0 for f in info['requested_formats']])
            
            if file_size and file_size > 0:
                row_data['bytes_size'] = file_size
                size_str = format_size(file_size)
                app.after(0, lambda: layout.safe_ui_update(row_data['size_label'], text=size_str, text_color="white"))
                with state.error_lock:
                    state.consecutive_errors = 0
            else:
                row_data['bytes_size'] = 0
                app.after(0, lambda: layout.safe_ui_update(row_data['size_label'], text="Unknown", text_color="#aaaaaa"))
                
    except Exception:
        row_data['bytes_size'] = 0
        app.after(0, lambda: layout.safe_ui_update(row_data['size_label'], text="Error", text_color=config.COLOR_RED))
        with state.error_lock:
            state.consecutive_errors += 1
            if state.consecutive_errors >= config.MAX_CONSECUTIVE_ERRORS:
                state.fetch_event.clear()
    
    app.after(0, layout.update_dynamic_totals)

def fetch_all_sizes_worker():
    if state.quality_combo is None: return
    quality = state.quality_combo.get()
    
    if quality in ["Select Quality", "Waiting for link...", "Loading..."]:
        app.after(0, lambda: custom_msg_box(messages.TITLE_WARNING, messages.MSG_QUALITY_MISSING, "warning"))
        return
        
    with state.ui_list_lock:
        selected_rows = [r for r in state.video_rows if r["checkbox"].get() == 1]
    if not selected_rows:
        app.after(0, lambda: custom_msg_box(messages.TITLE_WARNING, messages.MSG_NO_VIDEO_FETCH, "warning"))
        return

    if not state.operation_lock.acquire(blocking=False):
        app.after(0, lambda: custom_msg_box(messages.TITLE_WARNING, messages.MSG_OPERATION_RUNNING, "warning"))
        return

    try:
        state.fetch_event.set()
        state.consecutive_errors = 0
        app.after(0, lambda: layout.update_global_status(f"Fetching sizes for {quality}...", config.COLOR_CYAN, ""))
        
        if state.fetch_btn and state.stop_fetch_btn:
            app.after(0, lambda: state.fetch_btn.pack_forget())
            app.after(0, lambda: state.stop_fetch_btn.pack(side="left"))

        with concurrent.futures.ThreadPoolExecutor(max_workers=config.MAX_THREADS) as executor:
            futures = [executor.submit(fetch_size_for_single_video, row, quality) for row in selected_rows]
            batches = (len(selected_rows) + config.MAX_THREADS - 1) // config.MAX_THREADS
            done, not_done = concurrent.futures.wait(futures, timeout=config.SOCKET_TIMEOUT * batches)
            
            if not_done:
                state.fetch_event.clear()
        
        if state.consecutive_errors >= config.MAX_CONSECUTIVE_ERRORS:
            app.after(0, lambda: layout.update_global_status("Fetching stopped automatically: YouTube blocked the connection.", config.COLOR_RED, ""))
            app.after(0, lambda: custom_msg_box(messages.TITLE_ERROR, messages.MSG_BLOCKED, "error", custom_height=230))
        elif state.fetch_event.is_set():
            blocked_count = sum(1 for r in selected_rows if r['bytes_size'] == 0)
            if blocked_count > 0:
                app.after(0, lambda: layout.update_global_status("Sizes fetched.", "#28a745", f"({blocked_count} video(s) might be blocked or failed)"))
            else:
                app.after(0, lambda: layout.update_global_status("All sizes fetched successfully.", "#28a745", ""))
        else:
            app.after(0, lambda: layout.update_global_status("Fetching stopped by user.", "orange", ""))
            
    finally:
        state.fetch_event.clear()
        state.operation_lock.release()
        
        if state.fetch_btn and state.stop_fetch_btn:
            app.after(0, lambda: state.stop_fetch_btn.pack_forget())
            app.after(0, lambda: state.fetch_btn.pack(side="left"))

def on_fetch_sizes_click():
    threading.Thread(target=fetch_all_sizes_worker, daemon=True).start()

def on_stop_fetch_click():
    state.fetch_event.clear()
    layout.update_global_status("Stopping fetch... please wait.", "orange", "")

def render_chunk(entries_data, current_idx, qualities, chunk_size=config.RENDER_CHUNK_SIZE):
    end_idx = min(current_idx + chunk_size, len(entries_data))
    
    for i in range(current_idx, end_idx):
        data = entries_data[i]
        layout.add_video_row(data['idx'], data['title'], data['dur'], data['url'])
        
    app.after(0, lambda: layout.update_global_status(f"Rendering videos... ({end_idx}/{len(entries_data)})", config.COLOR_CYAN, ""))

    if end_idx < len(entries_data):
        app.after(10, lambda: render_chunk(entries_data, end_idx, qualities, chunk_size))
    else:
        if state.quality_combo:
            state.quality_combo.configure(values=qualities)
            if qualities: state.quality_combo.set(qualities[0])
        app.after(0, layout.update_dynamic_totals) 
        app.after(0, lambda: layout.update_global_status("Data fetched successfully. Ready to use.", "#28a745", ""))

def fetch_video_data():
    if state.url_entry is None: return
    url = state.url_entry.get()
    
    if not url:
        app.after(0, lambda: custom_msg_box(messages.TITLE_ERROR, messages.MSG_URL_MISSING, "error"))
        return

    app.after(0, layout.clear_list)
    app.after(0, lambda: layout.update_global_status(messages.STATUS_CONNECTING, config.COLOR_CYAN, ""))
    if state.quality_combo:
        app.after(0, lambda: state.quality_combo.set(messages.STATUS_LOADING))

    try:
        entries_data, qualities = get_video_info(url)
        app.after(0, lambda: render_chunk(entries_data, 0, qualities))
    except Exception as e:
        app.after(0, lambda: layout.update_global_status(messages.STATUS_SEARCH_FAILED, config.COLOR_RED, ""))
        app.after(0, lambda e=e: custom_msg_box(messages.TITLE_ERROR, messages.MSG_CONN_ERROR, "error"))

def on_search_click():
    threading.Thread(target=fetch_video_data, daemon=True).start()

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
    for row_data in rows_to_download:
        if not state.download_event.is_set(): break 
        if not row_data['frame'].winfo_exists(): continue 
        
        row_data['dl_state'] = 'preparing'
        app.after(0, lambda r=row_data: layout.safe_ui_update(r['status_label'], text="Preparing...", text_color=config.COLOR_MAGENTA))

        def handle_progress(status, percent, total_bytes, r=row_data):
            if not r['frame'].winfo_exists(): return 
            
            if status == 'downloading':
                app.after(0, lambda p=percent: layout.safe_progress_update(r['progress'], p))
                app.after(0, lambda p=percent: layout.safe_ui_update(r['percent_label'], text=f"{int(p*100)}%"))
                if r['bytes_size'] == -1 and total_bytes > 0:
                    size_str = format_size(total_bytes)
                    app.after(0, lambda: layout.safe_ui_update(r['size_label'], text=size_str))
                if r.get('dl_state') not in ['canceled', 'already_exists']:
                    r['dl_state'] = 'downloading'
                    app.after(0, lambda: layout.safe_ui_update(r['status_label'], text="Downloading...", text_color=config.COLOR_MAGENTA))
            
            elif status == 'finished':
                if r.get('dl_state') != 'already_exists':
                    r['dl_state'] = 'processing'
                    app.after(0, lambda: layout.safe_progress_update(r['progress'], 1.0))
                    app.after(0, lambda: layout.safe_ui_update(r['percent_label'], text="100%", text_color="#28a745"))
                    app.after(0, lambda: layout.safe_ui_update(r['status_label'], text="Processing...", text_color="#FFCC00"))
                    
            elif status == 'already_exists':
                r['dl_state'] = 'already_exists'
                app.after(0, lambda: layout.safe_ui_update(r['status_label'], text="Already Exists", text_color="#28a745"))
                app.after(0, lambda: layout.safe_progress_update(r['progress'], 1.0))
                app.after(0, lambda: layout.safe_ui_update(r['percent_label'], text="100%", text_color="#28a745"))

        def check_cancelled():
            return not state.download_event.is_set()

        try:
            download_single_video(
                row_data['url'], row_data['title'], save_path, quality, handle_progress, check_cancelled
            )
            if state.download_event.is_set() and row_data.get('dl_state') not in ['canceled', 'already_exists', 'failed']:
                row_data['dl_state'] = 'completed'
                app.after(0, lambda r=row_data: layout.safe_ui_update(r['status_label'], text="Completed", text_color="#28a745"))
                app.after(0, lambda r=row_data: layout.safe_progress_update(r['progress'], 1.0))
                app.after(0, lambda r=row_data: layout.safe_ui_update(r['percent_label'], text="100%", text_color="#28a745"))
        except Exception as e:
            if state.download_event.is_set():
                row_data['dl_state'] = 'failed'
                row_data['error_msg'] = str(e)
                app.after(0, lambda r=row_data: layout.safe_ui_update(r['status_label'], text="Failed", text_color=config.COLOR_RED, cursor="hand2"))

def download_worker():
    if state.path_entry is None or state.quality_combo is None: return
    
    save_path = state.path_entry.get()
    if not save_path or not os.path.isdir(save_path):
        app.after(0, lambda: custom_msg_box(messages.TITLE_ERROR, messages.MSG_INVALID_PATH, "error"))
        return

    with state.ui_list_lock:
        selected_rows = [r for r in state.video_rows if r["checkbox"].get() == 1]
    if not selected_rows:
        app.after(0, lambda: custom_msg_box(messages.TITLE_WARNING, messages.MSG_NO_VIDEO_DL, "warning"))
        return

    quality = state.quality_combo.get()
    if quality in ["Select Quality", "Waiting for link...", "Loading..."]:
        app.after(0, lambda: custom_msg_box(messages.TITLE_WARNING, messages.MSG_QUALITY_MISSING, "warning"))
        return

    if not state.operation_lock.acquire(blocking=False):
        app.after(0, lambda: custom_msg_box(messages.TITLE_WARNING, messages.MSG_OPERATION_RUNNING, "warning"))
        return

    try:
        state.download_event.set()
        
        if state.download_btn:
            app.after(0, lambda: state.download_btn.configure(text="Cancel Download", fg_color=config.COLOR_RED, hover_color=config.COLOR_RED_HOVER, command=on_cancel_download_click))

        app.after(0, lambda: layout.update_global_status(f"Starting download for {len(selected_rows)} videos...", config.COLOR_MAGENTA, ""))

        _download_process(selected_rows, quality, save_path)

        if state.download_event.is_set():
            failed_count = sum(1 for r in selected_rows if r.get('dl_state') == 'failed')
            if failed_count > 0:
                app.after(0, lambda: layout.update_global_status(f"Finished with {failed_count} errors. Click 'Failed' in the list to see why.", "orange", ""))
            else:
                app.after(0, lambda: layout.update_global_status("Downloads finished successfully.", "#28a745", ""))
                app.after(0, lambda: config.play_sound("success"))
        else:
            app.after(0, lambda: layout.update_global_status("Downloads canceled by user.", "orange", ""))
            
    finally:
        state.download_event.clear()
        state.operation_lock.release()
        
        if state.download_btn:
            app.after(0, lambda: state.download_btn.configure(text="Download Selected", state="normal", fg_color=config.COLOR_MAGENTA, hover_color=config.COLOR_MAGENTA_HOVER, command=on_download_click))

def on_download_click():
    threading.Thread(target=download_worker, daemon=True).start()

def on_cancel_download_click():
    if not state.download_event.is_set():
        return

    state.download_event.clear()
    state.convert_event.clear()
    
    if state.download_btn:
        state.download_btn.configure(text="Canceling...", state="disabled", fg_color="orange", hover_color="orange")
        
    layout.update_global_status("Canceling download... please wait.", "orange", "")
    
    for r in state.video_rows:
        if r.get('dl_state') in ['preparing', 'downloading']:
            r['dl_state'] = 'canceled'
            layout.safe_ui_update(r['status_label'], text="Canceled", text_color=config.COLOR_RED)
            layout.safe_progress_update(r['progress'], 0)
            layout.safe_ui_update(r['percent_label'], text="0%", text_color=config.COLOR_RED)

def convert_worker(speed_choice, selected_rows, save_path, quality, do_download_first):
    if not state.operation_lock.acquire(blocking=False):
        app.after(0, lambda: custom_msg_box(messages.TITLE_WARNING, messages.MSG_OPERATION_RUNNING, "warning"))
        return
        
    try:
        state.convert_event.set()
        
        if state.convert_btn:
            app.after(0, lambda: state.convert_btn.configure(text="Stop Convert", fg_color=config.COLOR_RED, hover_color=config.COLOR_RED_HOVER, command=on_stop_convert_click))

        if do_download_first:
            state.download_event.set()
            
            if state.download_btn:
                app.after(0, lambda: state.download_btn.configure(text="Cancel Download", fg_color=config.COLOR_RED, hover_color=config.COLOR_RED_HOVER, command=on_cancel_download_click))

            try:
                app.after(0, lambda: layout.update_global_status("Downloading missing files...", config.COLOR_MAGENTA, ""))
                _download_process(selected_rows, quality, save_path)
            finally:
                state.download_event.clear()
                if state.download_btn:
                    app.after(0, lambda: state.download_btn.configure(text="Download Selected", state="normal", fg_color=config.COLOR_MAGENTA, hover_color=config.COLOR_MAGENTA_HOVER, command=on_download_click))
            
            if not state.convert_event.is_set(): 
                app.after(0, lambda: layout.update_global_status("Conversion canceled.", "orange", ""))
                return
                
        files_to_delete = []
        app.after(0, lambda: layout.update_global_status("Starting conversion...", config.COLOR_CYAN, ""))
        
        for row_data in selected_rows:
            if not state.convert_event.is_set(): break 
            if not row_data['frame'].winfo_exists(): continue 
            
            input_file = find_downloaded_file(save_path, row_data['title'])
            if not input_file:
                row_data['dl_state'] = 'failed'
                row_data['error_msg'] = "File not found in the save path."
                app.after(0, lambda r=row_data: layout.safe_ui_update(r['status_label'], text="Failed", text_color=config.COLOR_RED, cursor="hand2"))
                continue
            
            app.after(0, lambda r=row_data: layout.safe_ui_update(r['status_label'], text="Converting...", text_color=config.COLOR_CYAN))
            app.after(0, lambda r=row_data: layout.safe_ui_update(r['percent_label'], text="---", text_color=config.COLOR_CYAN))
            app.after(0, lambda r=row_data: r['progress'].configure(mode="indeterminate", progress_color=config.COLOR_CYAN))
            app.after(0, lambda r=row_data: r['progress'].start())

            def converter_callback(status, r=row_data):
                if not r['frame'].winfo_exists(): return
                
                if status == 'already_mp4':
                    app.after(0, lambda: r['progress'].stop())
                    app.after(0, lambda: layout.safe_ui_update(r['status_label'], text=messages.STATUS_ALREADY_MP4, text_color="#28a745"))
                    app.after(0, lambda: r['progress'].configure(mode="determinate", progress_color=config.COLOR_MAGENTA))
                    app.after(0, lambda: layout.safe_progress_update(r['progress'], 1.0))
                    app.after(0, lambda: layout.safe_ui_update(r['percent_label'], text="100%", text_color="#28a745"))
                elif status == 'audio_file':
                    app.after(0, lambda: r['progress'].stop())
                    app.after(0, lambda: layout.safe_ui_update(r['status_label'], text=messages.STATUS_AUDIO_FILE, text_color="#28a745"))
                    app.after(0, lambda: r['progress'].configure(mode="determinate", progress_color=config.COLOR_MAGENTA))
                    app.after(0, lambda: layout.safe_progress_update(r['progress'], 1.0))
                    app.after(0, lambda: layout.safe_ui_update(r['percent_label'], text="100%", text_color="#28a745"))
                elif status == 'started_remux':
                    app.after(0, lambda: layout.update_global_status(messages.STATUS_CONVERTING_REMUX, config.COLOR_CYAN, ""))
                elif status == 'started_reencode':
                    app.after(0, lambda: layout.update_global_status(messages.STATUS_CONVERTING_RECODE, config.COLOR_CYAN, ""))
                elif status == 'finished':
                    app.after(0, lambda: r['progress'].stop())
                    app.after(0, lambda: r['progress'].configure(mode="determinate", progress_color=config.COLOR_MAGENTA))
                    app.after(0, lambda: layout.safe_progress_update(r['progress'], 1.0))
                    app.after(0, lambda: layout.safe_ui_update(r['percent_label'], text="100%", text_color="#28a745"))
                    app.after(0, lambda: layout.safe_ui_update(r['status_label'], text="Converted", text_color="#28a745"))

            def check_cancelled():
                return not state.convert_event.is_set()

            try:
                converted_file = convert_single_file(input_file, speed_choice, converter_callback, check_cancelled)
                if converted_file:
                    files_to_delete.append(converted_file)
                    
            except InterruptedError:
                app.after(0, lambda r=row_data: r['progress'].stop())
                app.after(0, lambda r=row_data: r['progress'].configure(mode="determinate", progress_color=config.COLOR_MAGENTA))
                app.after(0, lambda r=row_data: layout.safe_ui_update(r['status_label'], text="Canceled", text_color=config.COLOR_RED))
                app.after(0, lambda r=row_data: layout.safe_progress_update(r['progress'], 0))
                app.after(0, lambda r=row_data: layout.safe_ui_update(r['percent_label'], text="0%", text_color=config.COLOR_RED))
                break
                
            except Exception as e:
                app.after(0, lambda r=row_data: r['progress'].stop())
                app.after(0, lambda r=row_data: r['progress'].configure(mode="determinate", progress_color=config.COLOR_MAGENTA))
                row_data['dl_state'] = 'failed'
                row_data['error_msg'] = str(e)
                app.after(0, lambda r=row_data: layout.safe_ui_update(r['status_label'], text="Failed", text_color=config.COLOR_RED, cursor="hand2"))
                
        if state.convert_event.is_set():
            failed_count = sum(1 for r in selected_rows if r.get('dl_state') == 'failed')
            if failed_count > 0:
                app.after(0, lambda: layout.update_global_status(f"Finished with {failed_count} errors. Click 'Failed' in the list to see why.", "orange", ""))
            else:
                app.after(0, lambda: layout.update_global_status("All conversions completed successfully.", "#28a745", ""))
                app.after(0, lambda: config.play_sound("success"))
                
            if files_to_delete:
                def ask_cleanup():
                    if custom_ask_yes_no(messages.TITLE_CONFIRM, messages.MSG_CLEANUP):
                        for f in files_to_delete:
                            try: os.remove(f)
                            except: pass
                        layout.update_global_status("Conversion complete. Old files deleted.", "#28a745", "")
                app.after(0, ask_cleanup)
        else:
            app.after(0, lambda: layout.update_global_status("Conversion stopped by user.", "orange", ""))

    finally:
        state.convert_event.clear()
        state.operation_lock.release() 
        
        if state.convert_btn:
            app.after(0, lambda: state.convert_btn.configure(text="Convert to MP4", state="normal", fg_color=config.COLOR_CYAN, hover_color=config.COLOR_CYAN_HOVER, command=on_convert_click))

def on_convert_click():
    if state.path_entry is None or state.quality_combo is None: return
    if state.fetch_event.is_set() or state.download_event.is_set() or state.convert_event.is_set():
        custom_msg_box(messages.TITLE_WARNING, messages.MSG_OPERATION_RUNNING, "warning")
        return
        
    save_path = state.path_entry.get()
    if not save_path or not os.path.isdir(save_path):
        custom_msg_box(messages.TITLE_ERROR, messages.MSG_INVALID_PATH, "error")
        return

    with state.ui_list_lock:
        selected_rows = [r for r in state.video_rows if r["checkbox"].get() == 1]
    if not selected_rows:
        custom_msg_box(messages.TITLE_WARNING, messages.MSG_NO_VIDEO_CONV, "warning")
        return

    quality = state.quality_combo.get()
    if quality in ["Select Quality", "Waiting for link...", "Loading..."]:
        custom_msg_box(messages.TITLE_WARNING, messages.MSG_QUALITY_MISSING, "warning")
        return

    speed_choice = ask_conversion_speed(app)
    if speed_choice == "cancel":
        layout.update_global_status("Conversion canceled by user.", "orange", "")
        return
    
    needs_download = False
    for r in selected_rows:
        if not find_downloaded_file(save_path, r['title']):
            needs_download = True
            break
            
    do_download_first = False
    if needs_download:
        dl_choice = custom_ask_yes_no(messages.TITLE_WARNING, messages.MSG_DL_REQUIRED, icon="⚠️ ")
        if not dl_choice:
            layout.update_global_status("Conversion canceled by user.", "orange", "")
            return
        do_download_first = True
        
    threading.Thread(target=convert_worker, args=(speed_choice, selected_rows, save_path, quality, do_download_first), daemon=True).start()

_stop_convert_dialog_open = False 
def on_stop_convert_click():
    global _stop_convert_dialog_open 
    
    if _stop_convert_dialog_open:
        return 
        
    if state.download_event.is_set():
        _stop_convert_dialog_open = True
        if state.convert_btn:
            state.convert_btn.configure(state="disabled") 
            
        try:
            choice = custom_ask_yes_no(messages.TITLE_CONFIRM, messages.MSG_KEEP_DL_CANCEL_CONV, icon="⚠️")
        finally:
            _stop_convert_dialog_open = False
            if state.convert_btn:
                state.convert_btn.configure(state="normal") 
                
        if choice:
            state.convert_event.clear() 
            if state.convert_btn: 
                state.convert_btn.configure(text="Convert to MP4", fg_color=config.COLOR_CYAN, hover_color=config.COLOR_CYAN_HOVER, command=on_convert_click)
            layout.update_global_status("Conversion canceled. Download will continue.", "orange", "")
        return

    state.convert_event.clear() 
    state.download_event.clear() 
    
    if state.convert_btn:
        state.convert_btn.configure(text="Stopping...", state="disabled", fg_color="orange", hover_color="orange")
        
    try:
        proc = state.current_ffmpeg_process
        if proc is not None:
            proc.terminate()
    except Exception:
        pass
    layout.update_global_status("Stopping conversion... please wait.", "orange", "")


def _force_kill_all_background_processes():
    state.download_event.clear()
    state.convert_event.clear()
    state.fetch_event.clear()

    proc = state.current_ffmpeg_process
    if proc is not None:
        try:
            proc.terminate() 
            proc.wait(timeout=1) 
        except:
            try:
                if proc: proc.kill()
            except:
                pass

def on_closing():
    choice = v2_exit_dialog(messages.TITLE_EXIT, messages.MSG_EXIT_ASK, messages.BTN_STAY, messages.BTN_LEAVE, app)
    if choice == "leave":
        if state.download_event.is_set() or state.convert_event.is_set() or state.fetch_event.is_set():
            warn_choice = v2_exit_dialog(messages.TITLE_EXIT_WARN, messages.MSG_EXIT_WARN, messages.BTN_WAIT, messages.BTN_FORCE_QUIT, app)
            if warn_choice == "leave":
                _force_kill_all_background_processes() 
                app.destroy()
        else:
            _force_kill_all_background_processes() 
            app.destroy()

app.protocol("WM_DELETE_WINDOW", on_closing)

app.after(500, lambda: show_welcome_onboarding(app))

# --- Build UI via layout.py ---
callbacks_dict = {
    'global_hardware_shortcuts': global_hardware_shortcuts,
    'on_search_click': on_search_click,
    'on_fetch_sizes_click': on_fetch_sizes_click,
    'on_stop_fetch_click': on_stop_fetch_click,
    'on_download_click': on_download_click,
    'on_convert_click': on_convert_click,
    'on_cancel_download_click': on_cancel_download_click,
    'on_stop_convert_click': on_stop_convert_click,
    'show_contact_popup': lambda: show_contact_popup(app)
}

layout.build_app_ui(app, callbacks_dict)

if __name__ == "__main__":
    app.mainloop()
#delete me