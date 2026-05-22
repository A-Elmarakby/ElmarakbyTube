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
            "gpu_name": "Unknown"
        }
    }

# ==========================================
# 5. HARDWARE READERS (CROSS-PLATFORM)
# ==========================================
# These functions ask the computer (Windows, Mac, or Linux) for hardware info.
# We use 'try' and 'except' so the app never crashes if it cannot find the info.

def _get_cpu_name():
    """Try to get the processor name safely and clean empty lines."""
    try:
        os_name = platform.system()
        if os_name == "Windows":
            # Ask Windows for CPU name
            output = subprocess.check_output("wmic cpu get name", shell=True, text=True)
            # Remove empty lines and the word 'Name'
            lines = [l.strip() for l in output.split('\n') if l.strip() and l.strip().lower() != 'name']
            if lines: return lines[0] # Return the first real text
        elif os_name == "Darwin": 
            # Ask Mac for CPU name
            output = subprocess.check_output("sysctl -n machdep.cpu.brand_string", shell=True, text=True)
            if output.strip(): return output.strip()
        elif os_name == "Linux":
            # Look inside the Linux cpu info file
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
            # Ask Windows for RAM bytes
            output = subprocess.check_output("wmic computersystem get totalphysicalmemory", shell=True, text=True)
            # Remove empty lines and the header
            lines = [l.strip() for l in output.split('\n') if l.strip() and l.strip().lower() != 'totalphysicalmemory']
            if lines:
                # Convert bytes to GB
                gb = int(lines[0]) / (1024 * 1024 * 1024)
                return f"{round(gb)} GB"
        elif os_name == "Darwin":
            # Ask Mac for RAM
            output = subprocess.check_output("sysctl -n hw.memsize", shell=True, text=True)
            if output.strip():
                gb = int(output.strip()) / (1024 * 1024 * 1024)
                return f"{round(gb)} GB"
        elif os_name == "Linux":
            # Look inside Linux memory file
            with open("/proc/meminfo", "r") as f:
                for line in f:
                    if "MemTotal" in line:
                        kb = int(line.split()[1])
                        gb = kb / (1024 * 1024) # KB to GB
                        return f"{round(gb)} GB"
    except Exception:
        pass
    return "Unknown"

def _get_gpu_name():
    """Try to get Graphic Card name. (Can find multiple GPUs)"""
    try:
        os_name = platform.system()
        if os_name == "Windows":
            # Ask Windows for GPU
            output = subprocess.check_output("wmic path win32_VideoController get name", shell=True, text=True)
            # Remove empty lines and header
            lines = [l.strip() for l in output.split('\n') if l.strip() and l.strip().lower() != 'name']
            # If the user has 2 GPUs (like Intel + Nvidia), join them together
            if lines: return " + ".join(lines)
        elif os_name == "Linux":
            # Ask Linux for GPU
            output = subprocess.check_output("lspci | grep -i vga", shell=True, text=True)
            if output.strip(): return output.split(":")[2].strip()
        # Mac GPU is a bit hard without heavy commands, we skip it safely
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
        if not os.path.exists(file_path):
            # Create a new file and put the empty blueprint in it
            with open(file_path, "w", encoding="utf-8") as f:
                json.dump(get_default_schema(), f, indent=4)
        else:
            # If file exists, check if it is broken. If broken, make it new.
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    json.load(f)
            except Exception:
                with open(file_path, "w", encoding="utf-8") as f:
                    json.dump(get_default_schema(), f, indent=4)

def load_analytics():
    """Read data from the file and return it."""
    try:
        with open(get_analytics_file_path(), "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return get_default_schema()

def save_analytics(data):
    """Write the updated data back into the file."""
    try:
        with open(get_analytics_file_path(), "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4)
    except Exception:
        pass

# ==========================================
# 7. UPDATE FUNCTIONS
# ==========================================
# These functions are called by the app to change the numbers in the file.

def increment_stat(category, key, amount=1, sub_category=None):
    """Add a number (like +1) to a specific counter in the file."""
    with _analytics_lock:
        data = load_analytics()
        
        # Go to the right place and add the number safely
        if category in data:
            if sub_category and sub_category in data[category]:
                if key in data[category][sub_category]:
                    data[category][sub_category][key] += amount
            elif key in data[category]:
                data[category][key] += amount
                
        save_analytics(data)

def update_speed_stat(speed_mbps):
    """Check and update the highest and lowest internet speed."""
    if speed_mbps <= 0:
        return
        
    with _analytics_lock:
        data = load_analytics()
        
        current_high = data["download_metrics"]["highest_speed_mbps"]
        current_low = data["download_metrics"]["lowest_speed_mbps"]
        
        # If the new speed is higher, save it
        if speed_mbps > current_high:
            data["download_metrics"]["highest_speed_mbps"] = round(speed_mbps, 2)
            
        # If it is the first time (0.0) or the new speed is lower, save it
        if current_low == 0.0 or speed_mbps < current_low:
            data["download_metrics"]["lowest_speed_mbps"] = round(speed_mbps, 2)
            
        save_analytics(data)

def record_system_info():
    """Save computer OS, CPU, RAM, and GPU info safely."""
    with _analytics_lock:
        data = load_analytics()
        
        # Save normal OS info
        data["system"]["os_version"] = f"{platform.system()} {platform.release()}"
        data["system"]["cpu_cores"] = os.cpu_count() or 0
        
        # Call our cross-platform hardware readers
        data["system"]["cpu_name"] = _get_cpu_name()
        data["system"]["ram_gb"] = _get_ram_gb()
        data["system"]["gpu_name"] = _get_gpu_name()
        
        save_analytics(data)

def record_uptime(start_time_seconds):
    """Calculate total minutes the app was used and save it."""
    import time
    # Get total minutes: (Current time - Start time) / 60
    uptime_minutes = (time.time() - start_time_seconds) / 60.0
    with _analytics_lock:
        data = load_analytics()
        # Add the new minutes to the existing total
        data["app_lifecycle"]["total_uptime_minutes"] += round(uptime_minutes, 2)
        save_analytics(data)