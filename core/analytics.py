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
    """Return the empty starting data."""
    return {
        # Version of the data structure. If changed, app will reset file safely.
        "_schema_version": 1, 
        "app_lifecycle": {
            "total_launches": 0,
            "first_app_launch_date": "",  # <- New: Records the exact date/time of first launch
            "total_uptime_minutes": 0,
            "hardware_shortcuts_used": 0,
            "context_menu_used": 0,
            "support_interactions": {
                "main_contact_btn_clicks": 0,
                "whatsapp_clicks": 0,
                "linkedin_clicks": 0,
                "github_clicks": 0,
                "email_clicks": 0
            }
        },
        "search_behavior": {
            "total_links_searched": 0,
            "single_video_links": 0,
            "playlist_links": 0,
            "invalid_links_entered": 0,
            "fetch_sizes_clicks": 0,
            "videos_fetched_successfully": 0
        },
        "download_metrics": {
            "total_videos_downloaded": 0,
            "single_videos_downloaded": 0,
            "playlists_downloaded": 0,
            "total_playlist_videos_downloaded": 0,
            "downloads_completed": 0,
            "downloads_failed": 0,
            "downloads_canceled_by_user": 0,
            "total_downloaded_mb": 0.0,
            "total_download_time_seconds": 0.0,
            "highest_speed_mbps": 0.0,
            "lowest_speed_mbps": 0.0,
            "internet_speed_profile": {
                "last_tested_speed_mbps": 0.0,
                "highest_tested_speed_mbps": 0.0,
                "lowest_tested_speed_mbps": 0.0,
                "last_speedtest_timestamp": 0.0
            },
            "quality_preferences": {
                "single_videos_exact_resolutions": {
                    "exact_144p": 0, "exact_240p": 0, "exact_360p": 0, 
                    "exact_480p": 0, "exact_720p": 0, "exact_1080p": 0, 
                    "exact_1440p": 0, "exact_4K": 0, "exact_8K": 0, 
                    "exact_16K_plus": 0, "single_Audio_Only": 0
                },
                "playlist_presets": {
                    "playlist_Best_Quality": 0, "playlist_Medium": 0, 
                    "playlist_Low": 0, "playlist_Audio_Only": 0
                }
            }
        },
        "conversion_metrics": {
            "conversions_completed": 0,
            "conversions_failed": 0,
            "conversions_canceled": 0,
            "skipped_already_mp4": 0,
            "speed_mode_ultrafast": 0,
            "speed_mode_medium": 0,
            "total_converted_mb": 0.0,
            "total_conversion_time_seconds": 0.0
        },
        "resilience": {
            "youtube_blocks_encountered": 0,
            "network_retries_triggered": 0,
            "data_limit_warnings_shown": 0,
            # How many times the app fixed a broken or deleted part of the file
            "schema_repairs_count": 0
        },
        "system": {
            "os_version": "Unknown",
            "cpu_cores": 0,
            "cpu_name": "Unknown",
            "ram_gb": "Unknown",
            "gpu_name": "Unknown",
            "last_hardware_scan_timestamp": 0.0  # <- New: For 6-months caching logic
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
        
        os.replace(tmp_path, file_path) # Switch files safely
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
                bak_data["resilience"]["schema_repairs_count"] += 1
                _analytics_cache = bak_data
                needs_immediate_save = True
            else:
                _analytics_cache = json_data
                
        elif bak_data and not json_data:
            logging.warning("JSON file missing! Restoring from BAK.")
            bak_data["resilience"]["schema_repairs_count"] += 1
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
        
    with _analytics_lock: # Lock wraps BOTH load and save cleanly
        try:
            data = load_analytics()
            current_high = data["download_metrics"]["highest_speed_mbps"]
            current_low = data["download_metrics"]["lowest_speed_mbps"]
            
            if speed_mbps > current_high:
                data["download_metrics"]["highest_speed_mbps"] = round(speed_mbps, 2)
                
            if current_low == 0.0 or speed_mbps < current_low:
                data["download_metrics"]["lowest_speed_mbps"] = round(speed_mbps, 2)
                
            save_analytics(data)

        except Exception as e:
            logging.error(f"Error saving speed stat: {str(e)}")

def record_speedtest_result(speed_mbps):
    """
    Save the independent network speed test result safely.
    Updates the speed profile using precise Mbps format.
    """
    if speed_mbps <= 0:
        return

    with _analytics_lock:
        try:
            data = load_analytics()
            
            # Defensive check: Initialize sub-dictionary if missing in old files
            if "internet_speed_profile" not in data["download_metrics"]:
                data["download_metrics"]["internet_speed_profile"] = {
                    "last_tested_speed_mbps": 0.0,
                    "highest_tested_speed_mbps": 0.0,
                    "lowest_tested_speed_mbps": 0.0,
                    "last_speedtest_timestamp": 0.0
                }

            profile = data["download_metrics"]["internet_speed_profile"]
            
            # Save current test data
            profile["last_tested_speed_mbps"] = round(speed_mbps, 2)
            profile["last_speedtest_timestamp"] = time.time()
            
            # Check and update historical high/low limits
            if speed_mbps > profile["highest_tested_speed_mbps"]:
                profile["highest_tested_speed_mbps"] = round(speed_mbps, 2)
                
            if profile["lowest_tested_speed_mbps"] == 0.0 or speed_mbps < profile["lowest_tested_speed_mbps"]:
                profile["lowest_tested_speed_mbps"] = round(speed_mbps, 2)
                
            save_analytics(data)

        except Exception as e:
            logging.error(f"Error saving speed stat: {str(e)}")

def record_system_info():
    """Smart async hardware scan with caching & lifecycle recording."""
    import datetime
    import config

    with _analytics_lock:
        data = load_analytics()
        
        # 1. Record First Launch Date (Only if empty)
        if "first_app_launch_date" not in data["app_lifecycle"] or not data["app_lifecycle"]["first_app_launch_date"]:
            now_str = datetime.datetime.now().strftime("%Y-%m-%d %I:%M:%S %p")
            data["app_lifecycle"]["first_app_launch_date"] = now_str
            save_analytics(data)
            
        # 2. Check Cache Gate (Failsafe for missing keys in old files)
        sys_data = data.get("system", {})
        last_scan_time = sys_data.get("last_hardware_scan_timestamp", 0.0)
        cpu = sys_data.get("cpu_name", "Unknown")
        
        days_passed = (time.time() - last_scan_time) / 86400.0
        
        # 3. Fast Exit: If we have the data and it's fresh (under 6 months), do NOT block or scan!
        if cpu != "Unknown" and days_passed < config.SYSTEM_INFO_CACHE_DAYS:
            return

    # 4. Background Execution: Only runs if data is missing or expired (6 months passed)
    def background_scanner():
        time.sleep(5)
        try:
            # Gather data
            os_ver = f"{platform.system()} {platform.release()}"
            cores = os.cpu_count() or 0
            cpu_name = _get_cpu_name()
            ram = _get_ram_gb()
            gpu = _get_gpu_name()
            
            # Save data safely
            with _analytics_lock:
                fresh_data = load_analytics()
                
                # Defensive check in case schema is corrupted
                if "system" not in fresh_data:
                    fresh_data["system"] = {}
                    
                fresh_data["system"]["os_version"] = os_ver
                fresh_data["system"]["cpu_cores"] = cores
                fresh_data["system"]["cpu_name"] = cpu_name
                fresh_data["system"]["ram_gb"] = ram
                fresh_data["system"]["gpu_name"] = gpu
                fresh_data["system"]["last_hardware_scan_timestamp"] = time.time()
                
                save_analytics(fresh_data)
        except Exception as e:
            # Save critical errors quietly
            logging.error(f"Background Hardware Scan Failed: {str(e)}")

    # Launch without blocking the UI
    scanner_thread = threading.Thread(target=background_scanner, daemon=True)
    scanner_thread.start()

def record_uptime(start_time_seconds):
    """Calculate total minutes the app was used and save it."""
    uptime_minutes = (time.time() - start_time_seconds) / 60.0
    with _analytics_lock:
        try:
            data = load_analytics()
            data["app_lifecycle"]["total_uptime_minutes"] += round(uptime_minutes, 2)
            save_analytics(data)
        except Exception as e:
            # Save error quietly but document it
            logging.error(f"Failed to record uptime during shutdown: {str(e)}")