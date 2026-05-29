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
from core.utils import get_user_data_path

# ==========================================
# 2. SAFETY LOCK
# ==========================================
# We use this lock to stop two tasks from writing at the exact same time.
# If they write together, the file will break.
_analytics_lock = threading.Lock()

# ==========================================
# 3. FILE PATH HELPER
# ==========================================
# This block tells the app exactly where to save the 'analytics.json' file.
def get_analytics_file_path():
    """Get the full path to save the analytics file."""
    base_dir = os.path.dirname(get_user_data_path())
    return os.path.join(base_dir, "analytics.json")

# ==========================================
# 4. DATA BLUEPRINT (SCHEMA)
# ==========================================
# This block holds the empty starting data.
# It has a place for every small detail we want to record.
def get_default_schema():
    """Return the empty starting data."""
    return {
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
            "data_limit_warnings_shown": 0
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
            # Lightning fast Registry read (Zero subprocess blocking)
            import winreg
            key = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, r"HARDWARE\DESCRIPTION\System\CentralProcessor\0")
            cpu_name, _ = winreg.QueryValueEx(key, "ProcessorNameString")
            winreg.CloseKey(key)
            return cpu_name.strip()
        elif os_name == "Darwin": 
            output = subprocess.check_output("sysctl -n machdep.cpu.brand_string", shell=True, text=True)
            if output.strip(): return output.strip()
        elif os_name == "Linux":
            with open("/proc/cpuinfo", "r") as f:
                for line in f:
                    if "model name" in line:
                        return line.split(":")[1].strip()
    except Exception:
        pass
    return "Unknown"

def _get_ram_gb():
    """Try to get total RAM size in GB and clean empty lines."""
    try:
        os_name = platform.system()
        if os_name == "Windows":
            cflags = 0x08000000 if sys.platform == "win32" else 0 # Hide console
            output = subprocess.check_output("wmic computersystem get totalphysicalmemory", shell=True, text=True, creationflags=cflags)
            lines = [l.strip() for l in output.split('\n') if l.strip() and l.strip().lower() != 'totalphysicalmemory']
            if lines:
                gb = int(lines[0]) / (1024 * 1024 * 1024)
                return f"{round(gb)} GB"
        elif os_name == "Darwin":
            output = subprocess.check_output("sysctl -n hw.memsize", shell=True, text=True)
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
    except Exception:
        pass
    return "Unknown"

def _get_gpu_name():
    """Try to get Graphic Card name using modern tools."""
    try:
        os_name = platform.system()
        if os_name == "Windows":
            cflags = 0x08000000 if sys.platform == "win32" else 0 # Hide console window
            # Use modern PowerShell instead of deprecated wmic
            cmd = 'powershell "Get-CimInstance Win32_VideoController | Select-Object -ExpandProperty Name"'
            output = subprocess.check_output(cmd, shell=True, text=True, creationflags=cflags)
            lines = [l.strip() for l in output.split('\n') if l.strip()]
            if lines: return " + ".join(lines)
        elif os_name == "Linux":
            output = subprocess.check_output("lspci | grep -i vga", shell=True, text=True)
            if output.strip(): return output.split(":")[2].strip()
    except Exception:
        pass
    return "Unknown"

# ==========================================
# 6. CORE ANALYTICS FUNCTIONS
# ==========================================
# These are the main functions to start the file, read it, and write to it.

def init_analytics():
    """Make the JSON file when the app starts if it does not exist."""
    file_path = get_analytics_file_path()
    with _analytics_lock:
        try:
            if not os.path.exists(file_path):
                # Create a new file and put the empty blueprint in it
                with open(file_path, "w", encoding="utf-8") as f:
                    json.dump(get_default_schema(), f, indent=4)
            else:
                # If file exists, check if it is broken (JSONDecodeError)
                try:
                    with open(file_path, "r", encoding="utf-8") as f:
                        json.load(f)
                except json.JSONDecodeError:
                    logging.warning("Analytics file corrupted. Recreating a fresh blueprint.")
                    with open(file_path, "w", encoding="utf-8") as f:
                        json.dump(get_default_schema(), f, indent=4)
        except Exception as e:
            # CRITICAL ERROR: Hard drive issue, permission denied, etc.
            logging.critical(f"Critical error initializing analytics file: {str(e)}", exc_info=True)

def load_analytics():
    """Read data from the file and return it safely."""
    file_path = get_analytics_file_path()
    
    # Normal behavior: File hasn't been created yet
    if not os.path.exists(file_path):
        return get_default_schema()
        
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except json.JSONDecodeError:
        return get_default_schema()
    except Exception as e:
        # CRITICAL ERROR: Read failure due to OS level blocks
        logging.critical(f"Critical OS error reading analytics file: {str(e)}", exc_info=True)
        return get_default_schema()

def save_analytics(data):
    """Write the updated data back into the file."""
    try:
        with open(get_analytics_file_path(), "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4)
    except Exception as e:
        # CRITICAL ERROR: Disk full (No space left), write protected, etc.
        logging.critical(f"Critical failure saving analytics data! Data lost: {str(e)}", exc_info=True)

# ==========================================
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
                            data[category]["quality_preferences"][sub_category][key] += amount
            
            # Normal behavior for 2 levels or flat keys
            elif sub_category:
                if category in data and sub_category in data[category] and key in data[category][sub_category]:
                    data[category][sub_category][key] += amount
            else:
                if category in data and key in data[category]:
                    data[category][key] += amount
                    
            save_analytics(data)
        except Exception as e:
            logging.critical(f"Critical logic error in increment_stat for '{category}->{key}': {str(e)}", exc_info=True)

def update_speed_stat(speed_mbps):
    """Check and update the highest and lowest internet speed from downloads."""
    if speed_mbps <= 0:
        return
        
    with _analytics_lock:
        data = load_analytics()
        try:
            current_high = data["download_metrics"]["highest_speed_mbps"]
            current_low = data["download_metrics"]["lowest_speed_mbps"]
            
            if speed_mbps > current_high:
                data["download_metrics"]["highest_speed_mbps"] = round(speed_mbps, 2)
                
            if current_low == 0.0 or speed_mbps < current_low:
                data["download_metrics"]["lowest_speed_mbps"] = round(speed_mbps, 2)
                
            save_analytics(data)
        except Exception:
            pass

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
        except Exception:
            pass

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
    # Get total minutes: (Current time - Start time) / 60
    uptime_minutes = (time.time() - start_time_seconds) / 60.0
    def record_uptime(start_time_seconds):
        """Calculate total minutes the app was used and save it."""
        uptime_minutes = (time.time() - start_time_seconds) / 60.0
        with _analytics_lock:
            try:
                data = load_analytics()
                data["app_lifecycle"]["total_uptime_minutes"] += round(uptime_minutes, 2)
                save_analytics(data)
            except Exception:
                pass # Ignore errors during app shutdown to ensure a clean exit