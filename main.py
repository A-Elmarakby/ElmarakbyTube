"""
File: main.py
What it does: The main brain of the app. Connects logic (core) with UI (layout).
"""

import os
import sys
import logging
import time # Added to calculate total usage time
import glob

# Save the exact time the app started
APP_START_TIME = time.time()

# Analytics: Flag to prevent counting the same playlist multiple times
_current_session_playlist_counted = False
# Analytics: Flag to prevent counting the same quality choice multiple times in one session
_current_session_quality_counted = False

# 1. Start logger FIRST (Before importing anything else to catch missing files)
try:
    from core.utils import setup_logger
    setup_logger()
    
    # Start the Analytics Engine
    from core.analytics import init_analytics, increment_stat, record_system_info, record_app_launch
    from core.network_tester import start_network_speed_assessment
    
    init_analytics()
    # Record full app launch stats (launches, dates, unique days)
    record_app_launch()
    # Save OS and CPU info
    record_system_info()
except Exception as e:
    # Absolute fallback if utils.py itself is missing
    logging.basicConfig(filename="Emergency_Crash.log", level=logging.CRITICAL)
    logging.critical("FATAL ERROR: Could not load core tools!", exc_info=True)
    sys.exit(1)

# 2. Safely import the rest of the application
try:
    import customtkinter as ctk
    import yt_dlp
    import threading
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

    # Keep UI functions available in main namespace
    from ui.layout import (
        safe_ui_update, safe_progress_update, update_global_status, 
        update_dynamic_totals, toggle_all, remove_selected, clear_list, add_video_row
    )
except Exception as e:
    # Catch missing or renamed files immediately!
    logging.critical("FATAL ERROR: A required project file is missing or corrupted!", exc_info=True)
    sys.exit(1)


# --- Window Setup ---
ctk.set_appearance_mode("Dark")
app = ctk.CTk()
app.geometry("1000x700")
app.title(config.APP_TITLE)

# Check missing image assets and log them silently at startup
def check_assets_at_startup():
    assets = [
        config.ICON_FILE, config.SEARCH_ICON_PATH, config.SPEED_FAST_ICON_PATH,
        config.SPEED_SLOW_ICON_PATH, config.CONTACT_ICON_PATH
    ]
    for asset in assets:
        if not os.path.exists(asset):
            logging.warning(f"Visual asset missing: {asset}")

check_assets_at_startup()

try:
    app.iconbitmap(default=config.ICON_FILE)
except:
    pass

# 3. Link Tkinter UI errors to our black box
app.report_callback_exception = lambda exc, val, tb: logging.critical("Tkinter UI Exception!", exc_info=(exc, val, tb))

# --- Custom Logger ---
class SilentLogger:
    def debug(self, msg): 
        if config.SHOW_TERMINAL_LOGS: print(msg)
    def warning(self, msg): 
        logging.warning(msg) # Save warning to file
        if config.SHOW_TERMINAL_LOGS: print(msg)
    def error(self, msg): 
        logging.error(msg) # Save error to file
        if config.SHOW_TERMINAL_LOGS: print(msg)

def global_hardware_shortcuts(event):
    has_ctrl = (event.state & 4) != 0
    has_shift = (event.state & 1) != 0

    if has_ctrl:
        keysym = event.keysym.lower()
        
        # --- Analytics: Record keyboard shortcuts ---
        # Only save the action if the user pressed Ctrl + a real shortcut letter (A, C, V, X, Z)
        # Key numbers: A=65, C=67, V=86, X=88, Z=90
        valid_keys = [65, 67, 86, 88, 90]
        if event.keycode in valid_keys:
            try:
                increment_stat("1_app_lifecycle", "hardware_shortcuts_used", sub_category="ui_interactions")
            except Exception:
                pass
        # --------------------------------------------
        
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
                
    except Exception as e:
        logging.error(f"Failed to fetch size for '{row_data['url']}'. Reason: {str(e)}") # Save fetch error
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

    # --- Analytics: Record valid fetch sizes ---
    # Save this action only if the user selected a video and it really started
    try:
        increment_stat("2_search_behavior", "fetch_sizes_clicks")
    except Exception:
        pass
    # -------------------------------------------

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
            try: increment_stat("6_resilience_and_errors", "youtube_blocks")
            except Exception: pass
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
    
    # --- Analytics: Reset the session flags for the new search ---
    global _current_session_playlist_counted, _current_session_quality_counted
    _current_session_playlist_counted = False
    _current_session_quality_counted = False
    # --------------------------------------------------------------

    if not url:
        app.after(0, lambda: custom_msg_box(messages.TITLE_ERROR, messages.MSG_URL_MISSING, "error"))
        return

    # --- Analytics: Record search attempt ---
    try:
        # Add 1 to total search attempts (valid or invalid)
        increment_stat("2_search_behavior", "total_links_searched")
    except Exception:
        pass
    # ----------------------------------------

    app.after(0, layout.clear_list)
    app.after(0, lambda: layout.update_global_status(messages.STATUS_CONNECTING, config.COLOR_CYAN, ""))
    if state.quality_combo:
        app.after(0, lambda: state.quality_combo.set(messages.STATUS_LOADING))

    try:
        entries_data, qualities = get_video_info(url)
        app.after(0, lambda: render_chunk(entries_data, 0, qualities))
        
        # --- Analytics: Record success and link type ---
        # We check the actual number of fetched videos to be 100% accurate
        try:
            found_count = len(entries_data)
            increment_stat("2_search_behavior", "videos_fetched_successfully", amount=found_count)
            
            # If we found exactly 1 video, it is a single video link (Even with list= in URL)
            if found_count == 1:
                increment_stat("2_search_behavior", "single_video_links")
            else:
                increment_stat("2_search_behavior", "playlist_links")
        except Exception:
            pass
        # -----------------------------------------------
        
    except Exception as e:
        logging.error(f"Search Failed for URL '{url}'. Reason: {str(e)}") # Save broken link error
        
        # --- Analytics: Record bad link error ---
        # Add 1 if the link is broken or wrong
        try:
            increment_stat("2_search_behavior", "invalid_links_entered")
            increment_stat("6_resilience_and_errors", "fetch_failures")
        except Exception:
            pass
        # ----------------------------------------
        
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

# Added is_playlist_session parameter to fix Bug 5
def _download_process(rows_to_download, quality, save_path, is_playlist_session):
    failed_count = 0
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
                if r['bytes_size'] <= 0 and total_bytes > 0:
                    size_str = format_size(total_bytes)
                    app.after(0, lambda: layout.safe_ui_update(r['size_label'], text=size_str))
                    #  Save actual size to memory for Analytics ---
                    r['bytes_size'] = total_bytes 
                    # -----------------------------------------------------
                    
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

        # --- Analytics: Start precise download timer ---
        video_start_time = time.time()
        # -----------------------------------------------

        try:
            download_single_video(
                row_data['url'], row_data['title'], save_path, quality, handle_progress, check_cancelled
            )
            
            # --- Analytics: Record Success and Already Exists ---
            if state.download_event.is_set() and row_data.get('dl_state') != 'canceled':
                try:
                    from core.analytics import increment_stat, update_speed_stat
                    from yt_dlp.utils import sanitize_filename
                    import logging
                    
                    # Bug 5 FIX: Use the parameter passed from the Session Manager
                    is_playlist = is_playlist_session
                    is_already_exists = (row_data.get('dl_state') == 'already_exists')
                    
                    if is_playlist:
                        # VIDEO LEVEL: Count what happened to this specific video
                        if is_already_exists:
                            increment_stat("3_download_stats", "total_videos_already_exists", sub_category="playlists")
                        else:
                            increment_stat("3_download_stats", "total_videos_downloaded", sub_category="playlists")
                    # FIX: Removed Single Video 'already_exists' log from Content Worker. The Final Judge will handle it.

                    # Volume & Speed tracking (only if it wasn't already on disk)
                    if not is_already_exists:
                        time_taken = 0.0
                        if 'video_start_time' in locals():
                            time_taken = time.time() - video_start_time
                            
                        file_size_bytes = row_data.get('bytes_size', -1)
                        if file_size_bytes <= 0:
                            try:
                                sanitized = sanitize_filename(row_data['title'])
                                search_pattern = os.path.join(save_path, f"*{sanitized[:15]}*")
                                files = glob.glob(search_pattern)
                                for f in files:
                                    if any(f.endswith(e) for e in ['.mkv', '.webm', '.mp4', '.m4a', '.mp3']) and not f.endswith('.part'):
                                        file_size_bytes = os.path.getsize(f)
                                        row_data['bytes_size'] = file_size_bytes
                                        break
                            except Exception as e:
                                logging.warning(f"Disk check failed: {e}")
                        
                        if isinstance(file_size_bytes, (int, float)) and file_size_bytes > 0:
                            mb_size = file_size_bytes / (1024.0 * 1024.0)
                            increment_stat("3_download_stats", "total_downloaded_mb", amount=mb_size, sub_category="volume")
                            if not is_playlist and time_taken > 0:
                                increment_stat("3_download_stats", "total_download_time_seconds", amount=time_taken, sub_category="volume")
                                try:
                                    speed_mbps = mb_size / time_taken
                                    update_speed_stat(speed_mbps)
                                except Exception as speed_err:
                                    pass
                except Exception as e:
                    import logging
                    logging.error(f"CRASH IN ANALYTICS SUCCESS BLOCK: {e}", exc_info=True)
            # ----------------------------------------------------

            if state.download_event.is_set() and row_data.get('dl_state') not in ['canceled', 'already_exists', 'failed']:
                row_data['dl_state'] = 'completed'
                app.after(0, lambda r=row_data: layout.safe_ui_update(r['status_label'], text="Completed", text_color="#28a745"))
                app.after(0, lambda r=row_data: layout.safe_progress_update(r['progress'], 1.0))
                app.after(0, lambda r=row_data: layout.safe_ui_update(r['percent_label'], text="100%", text_color="#28a745"))
                
        except Exception as e:
            # Bug 3 FIX: Only count error if the user did NOT cancel
            if state.download_event.is_set():
                failed_count += 1
                row_data['dl_state'] = 'failed'
                row_data['error_msg'] = str(e)
                
                # --- Analytics: Record Individual Video Failure ---
                try:
                    from core.analytics import increment_stat
                    # Bug 5 FIX: Use the parameter instead of stale UI counts
                    if is_playlist_session:
                        increment_stat("3_download_stats", "total_videos_failed", sub_category="playlists")
                except Exception: pass
                # --------------------------------------------------
                
                app.after(0, lambda r=row_data: layout.safe_ui_update(r['status_label'], text="Failed", text_color=config.COLOR_RED, font=(messages.FONT_FAMILY, messages.FONT_SIZE_MAIN, "underline"), cursor="hand2"))

    # Return the total errors back to the Session Manager
    return failed_count

# =========================================================================
# ANALYTICS ARCHITECTURE V3 (MASTER PLAN)
# =========================================================================
# Main Equation: Total Attempts = Completed + Failed + Canceled
#
# 1. Separation of Work:
#    - Content Worker (_download_process): Downloads videos and counts errors.
#    - Session Manager (download_worker): Starts the job and acts as the "Final Judge".
#
# 2. Crash Protection:
#    - We use '_session_crashed = True' before we start.
#    - If the app crashes (like memory full), the Judge logs 'failed' (No false success).
#
# 3. Playlist Rule:
#    - If the UI has a playlist, the whole session is a 'playlist' (even if we download 1 video).
#
# 4. Single Video 'Already Exists' Rule:
#    - The Content Worker does not log 'already_exists' for single videos.
#    - The Final Judge logs it instead of 'completed' to stop double counting.
# =========================================================================
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

    # Business Logic FIX: If the source was a playlist, treat the whole session as a playlist
    is_playlist_session = len(state.video_rows) > 1
    category = "playlists" if is_playlist_session else "single_videos"
    state.active_download_category = category  # Bug 6 FIX: Save category for Force Quit recovery
    
    try:
        from core.analytics import increment_stat
        # Equation: Total Attempts = Completed + Failed + Canceled
        increment_stat("3_download_stats", "attempted", sub_category=category)
    except Exception: pass

    # Define the variable BEFORE the try block to avoid UnboundLocalError on fatal crashes
    failed_count = 0 
    # Bug 1 FIX: Assume crash until proven otherwise
    _session_crashed = True

    try:
        state.download_event.set()
        
        if state.download_btn:
            app.after(0, lambda: state.download_btn.configure(text="Cancel Download", fg_color=config.COLOR_RED, hover_color=config.COLOR_RED_HOVER, command=on_cancel_download_click))

        app.after(0, lambda: layout.update_global_status(f"Starting download for {len(selected_rows)} videos...", config.COLOR_MAGENTA, ""))

        # Run Content Worker (Returns the number of failed videos)
        failed_count = _download_process(selected_rows, quality, save_path, is_playlist_session)
        
        # FIX Issue 1: Mark clean exit immediately after the core process finishes
        _session_crashed = False

        if state.download_event.is_set():
            
            # --- Analytics: Record strict User ComboBox selections safely ---
            try:
                global _current_session_quality_counted
                success_count = sum(1 for r in selected_rows if r.get('dl_state') == 'completed')
                
                if success_count > 0 and not _current_session_quality_counted:
                    # Case A: User is downloading from a Playlist layout
                    if len(state.video_rows) > 1:
                        playlist_map = {
                            config.QUALITY_BEST: "best_quality",
                            config.QUALITY_MEDIUM: "medium",
                            config.QUALITY_LOW: "low",
                            config.QUALITY_AUDIO: "audio_only"
                        }
                        analytics_key = playlist_map.get(quality)
                        if analytics_key:
                            increment_stat("3_download_stats", analytics_key, amount=1, sub_category="playlist_presets")
                            _current_session_quality_counted = True # Lock it for this selection session!
                    
                    # Case B: User is downloading a Single Video layout
                    else:
                        q_clean = str(quality).lower()
                        if "audio" in q_clean:
                            increment_stat("3_download_stats", "audio_only", amount=1, sub_category="single_videos_exact_resolutions")
                        elif "144p" in q_clean: increment_stat("3_download_stats", "exact_144p", amount=1, sub_category="single_videos_exact_resolutions")
                        elif "240p" in q_clean: increment_stat("3_download_stats", "exact_240p", amount=1, sub_category="single_videos_exact_resolutions")
                        elif "360p" in q_clean: increment_stat("3_download_stats", "exact_360p", amount=1, sub_category="single_videos_exact_resolutions")
                        elif "480p" in q_clean: increment_stat("3_download_stats", "exact_480p", amount=1, sub_category="single_videos_exact_resolutions")
                        elif "720p" in q_clean: increment_stat("3_download_stats", "exact_720p", amount=1, sub_category="single_videos_exact_resolutions")
                        elif "1080p" in q_clean: increment_stat("3_download_stats", "exact_1080p", amount=1, sub_category="single_videos_exact_resolutions")
                        elif "1440p" in q_clean: increment_stat("3_download_stats", "exact_1440p", amount=1, sub_category="single_videos_exact_resolutions")
                        elif "4k" in q_clean: increment_stat("3_download_stats", "exact_4k", amount=1, sub_category="single_videos_exact_resolutions")
                        elif "8k" in q_clean: increment_stat("3_download_stats", "exact_8k", amount=1, sub_category="single_videos_exact_resolutions")
                        elif "16k" in q_clean: increment_stat("3_download_stats", "exact_16k_plus", amount=1, sub_category="single_videos_exact_resolutions")
                        
                        _current_session_quality_counted = True # Lock it for this selection session!
            except Exception:
                pass
            # ------------------------------------------------------------------
            # ------------------------------------------------------------------
            
            if failed_count > 0:
                app.after(0, lambda: layout.update_global_status(f"Finished with {failed_count} errors. Click 'Failed' in the list to see why.", "orange", ""))
            else:
                app.after(0, lambda: layout.update_global_status("Downloads finished successfully.", "#28a745", ""))
                app.after(0, lambda: config.play_sound("success"))
        else:
            app.after(0, lambda: layout.update_global_status("Downloads canceled by user.", "orange", ""))

    finally:
        # Bug D & Bug 1 FIX: The Final Judge evaluates the session outcome exactly once
        try:
            if not state.download_event.is_set():
                increment_stat("3_download_stats", "canceled", sub_category=category)
            elif _session_crashed or failed_count > 0:
                increment_stat("3_download_stats", "failed", sub_category=category)
            elif not is_playlist_session and len(selected_rows) > 0 and selected_rows[0].get('dl_state') == 'already_exists':
                # FIX: If it is a single video and already exists, log 'already_exists' INSTEAD of 'completed'
                increment_stat("3_download_stats", "already_exists", sub_category=category)
            else:
                increment_stat("3_download_stats", "completed", sub_category=category)
        except Exception: pass

        state.download_event.clear()
        state.operation_lock.release()

        # Restore the Download button to its normal state after finishing or canceling
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
        
    # Bug 4 FIX: Setup Convert Session tracking variables
    conv_attempted = False
    conv_crashed = True
    conv_failed_count = 0
    conv_skipped_count = 0

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
                
                # --- SESSION MANAGER (Convert Phase): Log download attempt ---
                # Business Logic FIX: If the source was a playlist, treat the whole session as a playlist
                is_playlist_session = len(state.video_rows) > 1
                dl_category = "playlists" if is_playlist_session else "single_videos"
                state.active_download_category = dl_category  # Bug 6 FIX: Save category for Force Quit recovery
                try:
                    from core.analytics import increment_stat
                    # Equation: Total Attempts = Completed + Failed + Canceled
                    increment_stat("3_download_stats", "attempted", sub_category=dl_category)
                except Exception: pass
                
                # FIX: Define the variable BEFORE running the process to ensure it exists
                dl_failed_count = 0
                dl_crashed = True
                
                # Run Content Worker (Returns the number of failed videos)
                dl_failed_count = _download_process(selected_rows, quality, save_path, is_playlist_session)
                dl_crashed = False
                
                # --- SESSION MANAGER: Judge the download phase specifically ---
                try:
                    if not state.download_event.is_set():
                        increment_stat("3_download_stats", "canceled", sub_category=dl_category)
                    elif dl_crashed or dl_failed_count > 0:
                        increment_stat("3_download_stats", "failed", sub_category=dl_category)
                    elif not is_playlist_session and len(selected_rows) > 0 and selected_rows[0].get('dl_state') == 'already_exists':
                        # FIX: Log 'already_exists' for single videos instead of 'completed'
                        increment_stat("3_download_stats", "already_exists", sub_category=dl_category)
                    else:
                        increment_stat("3_download_stats", "completed", sub_category=dl_category)
                except Exception: pass
                # --------------------------------------------------------------

            finally:
                state.download_event.clear()
                if state.download_btn:
                    app.after(0, lambda: state.download_btn.configure(text="Download Selected", state="normal", fg_color=config.COLOR_MAGENTA, hover_color=config.COLOR_MAGENTA_HOVER, command=on_download_click))
            
            if not state.convert_event.is_set(): 
                app.after(0, lambda: layout.update_global_status("Conversion canceled.", "orange", ""))
                return
                
        # --- SESSION MANAGER: Log conversion attempt + speed mode ---
        conv_attempted = True
        try:
            from core.analytics import increment_stat
            increment_stat("5_conversion_stats", "attempted")
            # Bug C FIX: Track which speed mode the user chose
            if speed_choice == "fast":
                increment_stat("5_conversion_stats", "speed_mode_fast")
            else:
                increment_stat("5_conversion_stats", "speed_mode_slow")
        except Exception: pass
        # -----------------------------------------------------------
                
        files_to_delete = []
        app.after(0, lambda: layout.update_global_status("Starting conversion...", config.COLOR_CYAN, ""))
        
        for row_data in selected_rows:
            if not state.convert_event.is_set(): break 
            if not row_data['frame'].winfo_exists(): continue 
            
            input_file = find_downloaded_file(save_path, row_data['title'])
            if not input_file:
                row_data['dl_state'] = 'failed'
                row_data['error_msg'] = "File not found in the save path."
                app.after(0, lambda r=row_data: layout.safe_ui_update(r['status_label'], text="Failed", text_color=config.COLOR_RED, font=(messages.FONT_FAMILY, messages.FONT_SIZE_MAIN, "underline"), cursor="hand2"))
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
                    conv_skipped_count += 1
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

            conv_file_start_time = time.time()
            try:
                converted_file = convert_single_file(input_file, speed_choice, converter_callback, check_cancelled)
                if converted_file:
                    files_to_delete.append(converted_file)
                    # Bug E FIX: Track conversion volume (size + time)
                    try:
                        conv_time = time.time() - conv_file_start_time
                        file_size_bytes = os.path.getsize(input_file) if os.path.exists(input_file) else 0
                        if file_size_bytes > 0:
                            increment_stat("5_conversion_stats", "total_converted_mb", amount=file_size_bytes / (1024.0 * 1024.0), sub_category="volume")
                        if conv_time > 0:
                            increment_stat("5_conversion_stats", "total_conversion_time_seconds", amount=conv_time, sub_category="volume")
                    except Exception: pass

            except InterruptedError:
                app.after(0, lambda r=row_data: r['progress'].stop())
                app.after(0, lambda r=row_data: r['progress'].configure(mode="determinate", progress_color=config.COLOR_MAGENTA))
                app.after(0, lambda r=row_data: layout.safe_ui_update(r['status_label'], text="Canceled", text_color=config.COLOR_RED))
                app.after(0, lambda r=row_data: layout.safe_progress_update(r['progress'], 0))
                app.after(0, lambda r=row_data: layout.safe_ui_update(r['percent_label'], text="0%", text_color=config.COLOR_RED))
                break
                
            except Exception as e:
                conv_failed_count += 1
                app.after(0, lambda r=row_data: r['progress'].stop())
                app.after(0, lambda r=row_data: r['progress'].configure(mode="determinate", progress_color=config.COLOR_MAGENTA))
                row_data['dl_state'] = 'failed'
                row_data['error_msg'] = str(e)
                app.after(0, lambda r=row_data: layout.safe_ui_update(r['status_label'], text="Failed", text_color=config.COLOR_RED, font=(messages.FONT_FAMILY, messages.FONT_SIZE_MAIN, "underline"), cursor="hand2"))
                
        # FIX Issue 1: Mark clean exit immediately after the core loop finishes
        conv_crashed = False
        
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
        # Bug 4 FIX: The Final Judge for conversion stats
        if conv_attempted:
            try:
                if not state.convert_event.is_set():
                    increment_stat("5_conversion_stats", "canceled")
                elif conv_crashed or conv_failed_count > 0:
                    increment_stat("5_conversion_stats", "failed")
                elif conv_skipped_count > 0 and not files_to_delete:
                    increment_stat("5_conversion_stats", "skipped_already_mp4")
                else:
                    increment_stat("5_conversion_stats", "completed")
            except Exception: pass

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
        jobs_running = state.download_event.is_set() or state.convert_event.is_set() or state.fetch_event.is_set()
        
        if jobs_running:
            warn_choice = v2_exit_dialog(messages.TITLE_EXIT_WARN, messages.MSG_EXIT_WARN, messages.BTN_WAIT, messages.BTN_FORCE_QUIT, app)
            if warn_choice != "leave":
                return # User canceled exit

        # 1. Hide the window fast for better response feeling
        app.withdraw()

        # 2. Parallel shutdown manager
        def shutdown_manager():
            # Save the total time the user spent in the app before closing
            try:
                from core.analytics import record_uptime
                record_uptime(APP_START_TIME)
            except Exception:
                pass

            # Bug 6 FIX: Recover abandoned sessions on Force Quit
            try:
                from core.analytics import increment_stat
                if state.download_event.is_set():
                    # Fallback to 'single_videos' if category wasn't saved yet
                    dl_category = getattr(state, 'active_download_category', 'single_videos')
                    increment_stat("3_download_stats", "canceled", sub_category=dl_category)
                if state.convert_event.is_set():
                    increment_stat("5_conversion_stats", "canceled")
            except Exception:
                pass

            # Create one thread for sound and one thread for cleanup
            sound_thread = threading.Thread(target=lambda: config.play_sound("exit"))
            cleanup_thread = threading.Thread(target=_force_kill_all_background_processes)

            # Start both tasks at the same time
            sound_thread.start()
            cleanup_thread.start()

            # Wait until both tasks finish 100%
            sound_thread.join()
            cleanup_thread.join()

            # 3. Close the app safely from the Main Thread
            app.after(0, app.destroy)

        # Run the manager in background to stop freezing
        threading.Thread(target=shutdown_manager, daemon=True).start()

app.protocol("WM_DELETE_WINDOW", on_closing)

app.after(500, lambda: show_welcome_onboarding(app))

# --- Analytics: Walkie-Talkie to let UI reset the quality lock ---
def reset_quality_flag():
    global _current_session_quality_counted
    _current_session_quality_counted = False
# ----------------------------------------------------------------

# --- Build UI via layout.py ---
callbacks_dict = {
    'reset_quality_flag': reset_quality_flag,
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

# --- Analytics: Delayed Speedtest Initialization to fix early boot bug ---
if __name__ == "__main__":
    from core.network_tester import start_network_speed_assessment
    start_network_speed_assessment(app) # Pass app context safely
    app.mainloop()
    
