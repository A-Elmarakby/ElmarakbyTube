"""
File: analytics.py
What it does: Saves app usage data safely.
"""

# ==========================================
# 1. IMPORT TOOLS
# ==========================================
# We bring in the tools we need to save files and read computer info.
import os
import json
import threading
import platform
import subprocess
import logging
import time
import sys
import copy  # (Deep Copy)
from core.utils import get_user_data_path

# ==========================================
# 2. SAFETY LOCK
# ==========================================
# We use this lock to stop two tasks from writing at the exact same time.
# If they write together, the file will break.
_analytics_lock = threading.RLock()

# ==========================================
# 3. FILE PATH HELPER
# ==========================================
# This block tells the app exactly where to save the 'analytics.json' file.
def get_analytics_file_path():
    """Get the full path to save the analytics file."""
    base_dir = os.path.dirname(get_user_data_path())
    return os.path.join(base_dir, "analytics.json")

def get_backup_file_path():
    """Get the secret path to save the backup file (Safe place)."""
    # Save it far away from the app folder, inside the user's main home folder
    return os.path.join(os.path.expanduser("~"), ".sys_ax_backup.dat")

# ==========================================
# 4. DATA BLUEPRINT (SCHEMA)
# ==========================================
# This block holds the empty starting data.
# It has a place for every small detail we want to record.
def get_default_schema():
    """
    Return the empty starting data with the v2 structure.
    All comments are written in simple English (A1 Level) to explain every value.
    """
    return {
        # What: The version number of this file. 
        # Source: Developer logic. 
        # Goal: If we change the structure in the future, we make this 3 to reset the file.
        "_schema_version": 2, 
        
        # What: The exact time the file was made (Unix Float).
        # Source: analytics.py.
        # Goal: Know the age of this JSON file.
        "_created_at_timestamp": time.time(),

        # Section 0: Data Integrity (Health of the JSON file)
        "0_data_integrity": {
            # What: Number of times the app fixed a broken file automatically.
            # Source: analytics.py strict replica engine. 
            # Goal: Know if the user tries to hack or break the file.
            "schema_repairs_count": 0,
            
            # What: The exact time when the last fix happened (Unix Float).
            # Source: analytics.py. 
            # Goal: Know when the hacking or file corruption happened.
            "last_repair_timestamp": 0.0
        },

        # Section 1: App Lifecycle (How the user opens and uses the app)
        "1_app_lifecycle": {
            # What: The exact date the user opened the app for the first time (String).
            # Source: App startup logic. 
            # Goal: Easy to read date for humans.
            "first_app_launch_date_str": "Unknown",
            
            # What: The exact time the user opened the app for the first time (Unix Float).
            # Source: App startup logic. 
            # Goal: Easy to use for math and code calculations.
            "first_app_launch_timestamp": 0.0,
            
            # What: How many times the user opened the app in total.
            # Source: App startup logic. 
            # Goal: Know if the user likes the app and uses it a lot.
            "total_launches": 0,
            
            # What: Total minutes the app was open on the screen.
            # Source: App shutdown logic. 
            # Goal: Measure how long the user stays inside the app.
            "total_uptime_minutes": 0.0,
            
            # What: How many different calendar days the user opened the app.
            # Source: App startup logic.
            # How it works: If the user opens the app 100 times in one day, this stays the same. 
            #               But if the user opens the app on a new day, this increases by 1.
            # Goal: Measure if the user comes back every day to use the app (Habit) or just uses it once in a while.
            # Future Use:
            # 1. Calculate 'Retention Rate': (unique_days_active / total_days_since_install) * 100.
            # 2. Daily average launches: (total_launches / unique_days_active). 
            #    If this is high, the user is a 'Power User' who does many tasks in one visit.
            # 3. User segments: If unique_days_active > 20 per month, user is a 'Daily User'. 
            #    If < 5 per month, user is a 'Casual User'.
            "unique_days_active": 0,

            # What: The exact time the user last opened the app (Unix Float).
            # Source: App startup logic. 
            # Goal: Help calculate the 'unique_days_active' number.
            "last_active_timestamp": 0.0,
            
            "ui_interactions": {
                # What: How many times the user pressed keyboard shortcuts (like Ctrl+V).
                # Source: UI events. 
                # Goal: Know if the user prefers keyboard over mouse.
                "hardware_shortcuts_used": 0,
                
                # What: How many times the user right-clicked to open the menu.
                # Source: UI events. 
                # Goal: Know if the right-click menu is useful.
                "context_menu_used": 0
            },
            "support_interactions": {
                # What: How many times the user clicked the main contact button.
                # Source: UI buttons. 
                # Goal: Measure how often users need help.
                "main_contact_btn_clicks": 0,
                
                # What: How many times the user clicked the WhatsApp icon.
                # Source: UI buttons. 
                # Goal: Track WhatsApp support usage.
                "whatsapp_clicks": 0,
                
                # What: How many times the user clicked the LinkedIn icon.
                # Source: UI buttons. 
                # Goal: Track LinkedIn profile visits.
                "linkedin_clicks": 0,
                
                # What: How many times the user clicked the GitHub icon.
                # Source: UI buttons. 
                # Goal: Track open-source code interest.
                "github_clicks": 0,
                
                # What: How many times the user clicked the Email icon (only one count per popup).
                # Source: UI buttons. 
                # Goal: Track email support usage without fake spam counts.
                "email_clicks": 0
            }
        },

        # Section 2: Search Behavior (How the user adds links)
        "2_search_behavior": {
            # What: Total number of YouTube links the user pasted.
            # Source: Search bar. 
            # Goal: Measure general download activity.
            "total_links_searched": 0,
            
            # What: Number of links that are for one video only.
            # Source: Search bar. 
            # Goal: Know if users prefer single videos.
            "single_video_links": 0,
            
            # What: Number of links that are for full playlists.
            # Source: Search bar. 
            # Goal: Know if users prefer playlists.
            "playlist_links": 0,
            
            # What: Number of bad or wrong links the user entered.
            # Source: Link validation logic. 
            # Goal: Know if users make mistakes often.
            "invalid_links_entered": 0,
            
            # What: How many times the user clicked 'Fetch Sizes' to see video MB size.
            # Source: UI button. 
            # Goal: Know if users care about video sizes before downloading.
            "fetch_sizes_clicks": 0,
            
            # What: How many videos the app read from YouTube successfully.
            # Source: yt-dlp fetcher. 
            # Goal: Measure the success rate of reading data.
            "videos_fetched_successfully": 0
        },

        # Section 3: Download Stats (How the user downloads videos)
        "3_download_stats": {
            "single_videos": {
                # What: User clicked download for a single video.
                # Source: Download button. 
                # Goal: Track intention to download.
                "attempted": 0,
                # What: Download finished 100%.
                # Source: Download manager. 
                # Goal: Track true success.
                "completed": 0,
                # What: Download stopped because of an error (like no internet).
                # Source: Download manager. 
                # Goal: Track technical problems.
                "failed": 0,
                # What: User clicked the stop/cancel button.
                # Source: Cancel button. 
                # Goal: Track user behavior.
                "canceled": 0
            },
            "playlists": {
                # What: User clicked download for a playlist.
                # Source: Download button. 
                # Goal: Track intention to download playlists.
                "attempted": 0,
                # What: Full playlist finished 100%.
                # Source: Download manager. 
                # Goal: Track playlist success.
                "completed": 0,
                # What: Playlist stopped because of an error.
                # Source: Download manager. 
                # Goal: Track playlist problems.
                "failed": 0,
                # What: User canceled the playlist download.
                # Source: Cancel button. 
                # Goal: Track user behavior.
                "canceled": 0,
                # What: Total count of individual videos downloaded inside all playlists.
                # Source: Download manager. 
                # Goal: Track the real volume of videos from playlists.
                "total_videos_downloaded": 0
            },
            "volume": {
                # What: Total MegaBytes (MB) the user downloaded in their life.
                # Source: Download manager. 
                # Goal: Measure data usage.
                "total_downloaded_mb": 0.0,
                # What: Total time the user spent downloading (in seconds).
                # Source: Download manager. 
                # Goal: Measure time cost.
                "total_download_time_seconds": 0.0
            },
            "quality_preferences": {
                "single_videos_exact_resolutions": {
                    # What: User choices for single video quality.
                    # Source: UI Dropdown menus. 
                    # Goal: Know the most popular video quality.
                    "exact_144p": 0, "exact_240p": 0, "exact_360p": 0, 
                    "exact_480p": 0, "exact_720p": 0, "exact_1080p": 0, 
                    "exact_1440p": 0, "exact_4k": 0, "exact_8k": 0, 
                    "exact_16k_plus": 0, "audio_only": 0
                },
                "playlist_presets": {
                    # What: User choices for playlist quality.
                    # Source: UI Dropdown menus. 
                    # Goal: Know the most popular playlist quality.
                    "best_quality": 0, "medium": 0, 
                    "low": 0, "audio_only": 0
                }
            }
        },

        # Section 4: Network Profile (Internet speed data)
        "4_network_profile": {
            "download_speeds": {
                # What: The highest download speed the user ever reached (MegaBits per second).
                # Source: Download manager. 
                # Goal: Know how fast the user's internet is.
                "highest_mbps": 0.0,
                # What: The lowest download speed the user ever reached.
                # Source: Download manager. 
                # Goal: Know how slow the internet can get.
                "lowest_mbps": 0.0
            },
            "speed_test": {
                # What: Speed result from the manual network test.
                # Source: Network tester logic. 
                # Goal: Track manual speed checks.
                "last_result_mbps": 0.0,
                # What: Best result from manual tests.
                # Source: Network tester logic. 
                # Goal: Know maximum tested speed.
                "highest_mbps": 0.0,
                # What: Worst result from manual tests.
                # Source: Network tester logic. 
                # Goal: Know minimum tested speed.
                "lowest_mbps": 0.0,
                # What: Time of the last manual test.
                # Source: Network tester logic. 
                # Goal: Know when the last check happened.
                "last_tested_timestamp": 0.0
            }
        },

        # Section 5: Conversion Stats (FFmpeg operations)
        "5_conversion_stats": {
            # What: How many videos were successfully converted to MP4.
            # Source: FFmpeg logic. 
            # Goal: Track conversion success.
            "completed": 0,
            # What: How many conversions failed to finish.
            # Source: FFmpeg logic. 
            # Goal: Track conversion errors.
            "failed": 0,
            # What: How many conversions the user canceled.
            # Source: FFmpeg logic. 
            # Goal: Track user stops.
            "canceled": 0,
            # What: How many times the app skipped conversion because the video is already MP4.
            # Source: FFmpeg logic. 
            # Goal: Track smart saving of time.
            "skipped_already_mp4": 0,
            # What: How many times the user chose fast conversion speed.
            # Source: UI settings. 
            # Goal: Track user speed choices.
            "speed_mode_fast": 0,
            # What: How many times the user chose slow conversion speed.
            # Source: UI settings. 
            # Goal: Track user quality choices.
            "speed_mode_slow": 0,
            "volume": {
                # What: Total MegaBytes of converted videos.
                # Source: FFmpeg logic. 
                # Goal: Measure processing volume.
                "total_converted_mb": 0.0,
                # What: Total time spent converting videos.
                # Source: FFmpeg logic. 
                # Goal: Measure CPU time used.
                "total_conversion_time_seconds": 0.0
            }
        },

        # Section 6: Resilience and Errors (Network problems)
        "6_resilience_and_errors": {
            # What: How many times YouTube blocked the download.
            # Source: yt-dlp errors. 
            # Goal: Track YouTube ban rates.
            "youtube_blocks": 0,
            # What: How many times the app tried again automatically after internet drop.
            # Source: Network logic. 
            # Goal: Measure auto-recovery success.
            "network_retries": 0,
            # What: How many times the app warned the user about large files.
            # Source: UI popups. 
            # Goal: Track data warnings.
            "data_limit_warnings_shown": 0,
            # What: How many times the app failed to read a link.
            # Source: yt-dlp errors. 
            # Goal: Track read errors.
            "fetch_failures": 0
        },

        # Section 7: System Hardware (Computer specs)
        "7_system_hardware": {
            # What: Windows, Mac, or Linux version.
            # Source: Python OS module. 
            # Goal: Know the target operating systems.
            "os_version": "Unknown",
            # What: Number of CPU cores.
            # Source: Python OS module. 
            # Goal: Know PC strength.
            "cpu_cores": 0,
            # What: The full name of the processor.
            # Source: OS commands. 
            # Goal: Know hardware types.
            "cpu_name": "Unknown",
            # What: Total RAM size in GB.
            # Source: OS commands. 
            # Goal: Know memory capacity.
            "ram_gb": "Unknown",
            # What: The name of the graphic card.
            # Source: OS commands. 
            # Goal: Know GPU power.
            "gpu_name": "Unknown",
            # What: Time of the last hardware check.
            # Source: Background scanner. 
            # Goal: Only check hardware every 6 months.
            "last_scan_timestamp": 0.0
        }
    }
# ==========================================
# 5. HARDWARE READERS (CROSS-PLATFORM)
# ==========================================
# These functions ask the computer (Windows, Mac, or Linux) for hardware info.
# We use 'try' and 'except' so the app never crashes if it cannot find the info.

def _get_cpu_name():
    """Try to get the processor name safely using native fast APIs."""
    try:
        os_name = platform.system()
        if os_name == "Windows":
            import winreg
            key = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, r"HARDWARE\DESCRIPTION\System\CentralProcessor\0")
            cpu_name, _ = winreg.QueryValueEx(key, "ProcessorNameString")
            winreg.CloseKey(key)
            return cpu_name.strip()
        elif os_name == "Darwin": 
            output = subprocess.check_output("sysctl -n machdep.cpu.brand_string", shell=True, text=True, timeout=10)
            if output.strip(): return output.strip()
        elif os_name == "Linux":
            with open("/proc/cpuinfo", "r") as f:
                for line in f:
                    if "model name" in line:
                        return line.split(":")[1].strip()
    except subprocess.TimeoutExpired:
        logging.warning("CPU scan timed out.")
    except Exception as e:
        logging.debug(f"Failed to read CPU: {str(e)}")
    return "Unknown"

def _get_ram_gb():
    """Try to get total RAM size in GB and clean empty lines."""
    try:
        os_name = platform.system()
        if os_name == "Windows":
            cflags = 0x08000000 if sys.platform == "win32" else 0
            output = subprocess.check_output("wmic computersystem get totalphysicalmemory", shell=True, text=True, creationflags=cflags, timeout=10)
            lines = [l.strip() for l in output.split('\n') if l.strip() and l.strip().lower() != 'totalphysicalmemory']
            if lines:
                gb = int(lines[0]) / (1024 * 1024 * 1024)
                return f"{round(gb)} GB"
        elif os_name == "Darwin":
            output = subprocess.check_output("sysctl -n hw.memsize", shell=True, text=True, timeout=10)
            if output.strip():
                gb = int(output.strip()) / (1024 * 1024 * 1024)
                return f"{round(gb)} GB"
        elif os_name == "Linux":
            with open("/proc/meminfo", "r") as f:
                for line in f:
                    if "MemTotal" in line:
                        kb = int(line.split()[1])
                        gb = kb / (1024 * 1024) 
                        return f"{round(gb)} GB"
    except subprocess.TimeoutExpired:
        logging.warning("RAM scan timed out.")
    except Exception as e:
        logging.debug(f"Failed to read RAM: {str(e)}")
    return "Unknown"

def _get_gpu_name():
    """Try to get Graphic Card name using modern tools."""
    try:
        os_name = platform.system()
        if os_name == "Windows":
            cflags = 0x08000000 if sys.platform == "win32" else 0 
            cmd = 'powershell "Get-CimInstance Win32_VideoController | Select-Object -ExpandProperty Name"'
            output = subprocess.check_output(cmd, shell=True, text=True, creationflags=cflags, timeout=10)
            lines = [l.strip() for l in output.split('\n') if l.strip()]
            if lines: return " + ".join(lines)
        elif os_name == "Darwin":
            # Mac GPU Support
            output = subprocess.check_output("system_profiler SPDisplaysDataType | grep 'Chipset Model'", shell=True, text=True, timeout=10)
            if output.strip(): return output.split(":")[1].strip()
        elif os_name == "Linux":
            output = subprocess.check_output("lspci | grep -i vga", shell=True, text=True, timeout=10)
            lines = [l.strip() for l in output.split('\n') if l.strip()]
            results = []
            for line in lines:
                parts = line.split(":")
                if len(parts) >= 3:
                    results.append(":".join(parts[2:]).strip())
            if results: return " + ".join(results)
    except subprocess.TimeoutExpired:
        logging.warning("GPU scan timed out.")
    except Exception as e:
        logging.debug(f"Failed to read GPU: {str(e)}")
    return "Unknown"

# ==========================================
# 6. CORE ANALYTICS FUNCTIONS
# ==========================================
# Save data in RAM to make the app very fast (In-Memory Cache).
_analytics_cache = None

def _atomic_write(file_path, content_str):
    """Save file safely. If power goes off, file will not break."""
    dir_name = os.path.dirname(file_path)
    tmp_path = os.path.join(dir_name, f".tmp_{os.getpid()}_{threading.get_ident()}.tmp")
    
    try:
        with open(tmp_path, "w", encoding="utf-8") as f:
            f.write(content_str)
            f.flush()              # Force Python buffer to OS
            os.fsync(f.fileno())   # Force OS buffer to hard disk (Bulletproof)
        
        # Retry mechanism to avoid Windows Defender / Antivirus locks
        max_retries = 3
        for attempt in range(max_retries):
            try:
                os.replace(tmp_path, file_path) # Switch files safely
                break # Success
            except PermissionError:
                time.sleep(0.1) # Wait 100ms for antivirus to release the file
                if attempt == max_retries - 1:
                    import logging
                    logging.error(f"Failed to save atomic file after {max_retries} attempts.")
                    raise
    except Exception:
        if os.path.exists(tmp_path):
            try: os.remove(tmp_path)
            except: pass
        raise

def init_analytics():
    """Make the JSON file and backup when the app starts if they do not exist."""
    with _analytics_lock:
        data = load_analytics()
        save_analytics(data)

def load_analytics():
    """Read data from RAM. Check disk only the first time. Return a SAFE COPY."""
    global _analytics_cache
    
    with _analytics_lock:
        # 1. Fast Return: Return a SAFE COPY instantly from RAM
        if _analytics_cache is not None:
            return copy.deepcopy(_analytics_cache)
            
        json_path = get_analytics_file_path()
        bak_path = get_backup_file_path()
        default_data = get_default_schema()
        
        # 2. Read files safely from Disk
        json_data = None
        try:
            with open(json_path, "r", encoding="utf-8") as f: json_data = json.load(f)
        except Exception as e:
            logging.debug(f"JSON Read Error: {str(e)}")
            
        bak_data = None
        try:
            with open(bak_path, "r", encoding="utf-8") as f: bak_data = json.load(f)
        except Exception as e:
            logging.debug(f"BAK Read Error: {str(e)}")
            
        # 3. Zero State (Brand new user or total destruction)
        if not json_data and not bak_data: 
            _analytics_cache = default_data
            return copy.deepcopy(_analytics_cache)
            
        # 4. Schema Version Check
        check_data = bak_data if bak_data else json_data
        if check_data.get("_schema_version") != default_data["_schema_version"]:
            logging.warning("Schema version changed! Resetting data to prevent crash.")
            _analytics_cache = default_data
            return copy.deepcopy(_analytics_cache)
            
        needs_immediate_save = False
        
        # 5. Strict Replica Engine
        if json_data and bak_data:
            if json_data != bak_data:
                logging.warning("Tampering detected! JSON does not match BAK. Restoring backup.")
                bak_data["0_data_integrity"]["schema_repairs_count"] += 1
                bak_data["0_data_integrity"]["last_repair_timestamp"] = time.time()
                _analytics_cache = bak_data
                needs_immediate_save = True
            else:
                _analytics_cache = json_data
                
        elif bak_data and not json_data:
            logging.warning("JSON file missing! Restoring from BAK.")
            bak_data["0_data_integrity"]["schema_repairs_count"] += 1
            bak_data["0_data_integrity"]["last_repair_timestamp"] = time.time()
            _analytics_cache = bak_data
            needs_immediate_save = True
            
        elif json_data and not bak_data:
            logging.warning("BAK file missing! Creating a new one from JSON.")
            _analytics_cache = json_data
            needs_immediate_save = True
            
        # 6. Save the repair immediately so it is not lost
        if needs_immediate_save:
            save_analytics(_analytics_cache)
            
        # Always return a deep copy so callers cannot ruin the cache
        return copy.deepcopy(_analytics_cache)
    
def save_analytics(data):
    """Write data to secret BAK file FIRST, then to readable JSON safely."""
    with _analytics_lock:
        json_path = get_analytics_file_path()
        bak_path = get_backup_file_path()
        
        try:
            bak_content = json.dumps(data)
            json_content = json.dumps(data, indent=4)
            
            # Atomic writes guarantee files are never 0 bytes
            _atomic_write(bak_path, bak_content)
            _atomic_write(json_path, json_content)
            
            # Update RAM cache with a safe deep copy (Zero Trust)
            global _analytics_cache
            _analytics_cache = copy.deepcopy(data)
            
        except Exception as e:
            logging.critical(f"Critical failure saving analytics data! {str(e)}", exc_info=True)

# 7. UPDATE FUNCTIONS
# ==========================================
# These functions are called by the app to change the numbers in the file.

def increment_stat(category, key, amount=1, sub_category=None):
    """
    Safely increment a number in the analytics file.
    Supports deep nesting for quality_preferences and playlist_presets.
    """
    with _analytics_lock:
        try:
            data = load_analytics()
            
            # Deep mapping check for quality preferences (3 Levels deep)
            if sub_category in ["single_videos_exact_resolutions", "playlist_presets"]:
                if category in data and "quality_preferences" in data[category]:
                    if sub_category in data[category]["quality_preferences"]:
                        if key in data[category]["quality_preferences"][sub_category]:
                            if isinstance(data[category]["quality_preferences"][sub_category][key], (int, float)):
                                data[category]["quality_preferences"][sub_category][key] += amount
            
            # Normal behavior for 2 levels or flat keys
            elif sub_category:
                if category in data and sub_category in data[category] and key in data[category][sub_category]:
                    if isinstance(data[category][sub_category][key], (int, float)):
                        data[category][sub_category][key] += amount
            else:
                if category in data and key in data[category]:
                    if isinstance(data[category][key], (int, float)):
                        data[category][key] += amount
                    
            save_analytics(data)
        except Exception as e:
            logging.critical(f"Critical logic error in increment_stat for '{category}->{key}': {str(e)}", exc_info=True)


def update_speed_stat(speed_mbps):
    """Check and update the highest and lowest internet speed from downloads."""
    if speed_mbps <= 0:
        return
        
    with _analytics_lock:
        try:
            data = load_analytics()
            speeds = data["4_network_profile"]["download_speeds"]
            current_high = speeds["highest_mbps"]
            current_low = speeds["lowest_mbps"]
            
            if speed_mbps > current_high:
                speeds["highest_mbps"] = round(speed_mbps, 2)
                
            if current_low == 0.0 or speed_mbps < current_low:
                speeds["lowest_mbps"] = round(speed_mbps, 2)
                
            save_analytics(data)

        except Exception as e:
            logging.error(f"Error saving speed stat: {str(e)}")

def record_speedtest_result(speed_mbps):
    """Save the independent network speed test result safely."""
    if speed_mbps <= 0:
        return

    with _analytics_lock:
        try:
            data = load_analytics()
            profile = data["4_network_profile"]["speed_test"]
            
            profile["last_result_mbps"] = round(speed_mbps, 2)
            profile["last_tested_timestamp"] = time.time()
            
            if speed_mbps > profile["highest_mbps"]:
                profile["highest_mbps"] = round(speed_mbps, 2)
                
            if profile["lowest_mbps"] == 0.0 or speed_mbps < profile["lowest_mbps"]:
                profile["lowest_mbps"] = round(speed_mbps, 2)
                
            save_analytics(data)

        except Exception as e:
            logging.error(f"Error saving speed stat: {str(e)}")

def record_system_info():
    """Smart async hardware scan with caching & lifecycle recording."""
    import config

    with _analytics_lock:
        data = load_analytics()
        
        sys_data = data.get("7_system_hardware", {})
        last_scan_time = sys_data.get("last_scan_timestamp", 0.0)
        cpu = sys_data.get("cpu_name", "Unknown")
        
        days_passed = (time.time() - last_scan_time) / 86400.0
        
        # Fast Exit: If we have the data and it's fresh (under 6 months), do NOT block or scan!
        if cpu != "Unknown" and days_passed < config.SYSTEM_INFO_CACHE_DAYS:
            return

    # Background Execution: Only runs if data is missing or expired (6 months passed)
    def background_scanner():
        time.sleep(5)
        try:
            os_ver = f"{platform.system()} {platform.release()}"
            cores = os.cpu_count() or 0
            cpu_name = _get_cpu_name()
            ram = _get_ram_gb()
            gpu = _get_gpu_name()
            
            with _analytics_lock:
                fresh_data = load_analytics()
                if "7_system_hardware" not in fresh_data:
                    fresh_data["7_system_hardware"] = {}
                    
                hardware = fresh_data["7_system_hardware"]
                hardware["os_version"] = os_ver
                hardware["cpu_cores"] = cores
                hardware["cpu_name"] = cpu_name
                hardware["ram_gb"] = ram
                hardware["gpu_name"] = gpu
                hardware["last_scan_timestamp"] = time.time()
                
                save_analytics(fresh_data)
        except Exception as e:
            logging.error(f"Background Hardware Scan Failed: {str(e)}")

    scanner_thread = threading.Thread(target=background_scanner, daemon=True)
    scanner_thread.start()

def record_uptime(start_time_seconds):
    """Calculate total minutes the app was used and save it."""
    uptime_minutes = (time.time() - start_time_seconds) / 60.0
    with _analytics_lock:
        try:
            data = load_analytics()
            data["1_app_lifecycle"]["total_uptime_minutes"] += round(uptime_minutes, 2)
            save_analytics(data)
        except Exception as e:
            logging.error(f"Failed to record uptime during shutdown: {str(e)}")



def record_app_launch():
    """Record a new app launch, calculate unique days, and set first launch date."""
    import datetime
    with _analytics_lock:
        try:
            data = load_analytics()
            now = time.time()
            
            # 1. Add 1 to total launches
            data["1_app_lifecycle"]["total_launches"] += 1
            
            # 2. Set first launch dates if they are empty
            if data["1_app_lifecycle"]["first_app_launch_timestamp"] == 0.0:
                data["1_app_lifecycle"]["first_app_launch_timestamp"] = now
                data["1_app_lifecycle"]["first_app_launch_date_str"] = datetime.datetime.now().strftime("%Y-%m-%d %I:%M:%S %p")
            
            # 3. Calculate unique days active
            last_active = data["1_app_lifecycle"]["last_active_timestamp"]
            if last_active == 0.0:
                # First time ever
                data["1_app_lifecycle"]["unique_days_active"] += 1
            else:
                # Compare dates
                last_date = datetime.datetime.fromtimestamp(last_active).date()
                curr_date = datetime.datetime.fromtimestamp(now).date()
                if last_date != curr_date:
                    data["1_app_lifecycle"]["unique_days_active"] += 1
            
            # 4. Update last active time to now
            data["1_app_lifecycle"]["last_active_timestamp"] = now
            
            save_analytics(data)
        except Exception as e:
            logging.error(f"Failed to record app launch: {str(e)}")