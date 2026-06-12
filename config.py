import os
import sys
import logging # Added to record missing files

# Get the full path of the folder containing config.py
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# Build the main assets folder path dynamically
ASSETS_DIR = os.path.join(BASE_DIR, "assets")

# ==========================================
# 1. GENERAL APP SETTINGS
# ==========================================
# The name of the app.
APP_TITLE = "ElmarakbyTube Downloader"

# The path to the app icon (logo).
ICON_FILE = os.path.join(ASSETS_DIR, "icon.ico")

# Default popup window size (width, height).
POPUP_WIDTH = 450
POPUP_HEIGHT = 200

# ==========================================
# WINDOWS LONG PATH FIX (260 CHARACTERS LIMIT)
# ==========================================
# Windows cannot save files if the full folder path + file name is more than 260 letters.
# If a YouTube video has a very long name, the download will fail.
# So, we cut the video name to this safe number of letters.
# This is the maximum number of letters allowed from the video name.
# We cut long names to this size so the download does not fail.
MAX_VIDEO_TITLE_LENGTH = 100

# ==========================================
# 2. COLORS (App look and feel)
# ==========================================
# Main colors.
COLOR_CYAN = "#007BA7"        
COLOR_CYAN_HOVER = "#005F83"
COLOR_MAGENTA = "#B20059"     
COLOR_MAGENTA_HOVER = "#8C0046"

# Alert colors.
COLOR_RED = "#D32F2F"         
COLOR_RED_HOVER = "#9A0007"
COLOR_GREEN = "#398F3E"
COLOR_GREEN_HOVER = "#183B19"

# Right-click menu colors.
# Background color for the menu box.
MENU_BG_COLOR = "#2b2b2b"
# Text color for the menu words.
MENU_TEXT_COLOR = "white"
# Color when you put mouse on a menu word.
MENU_HOVER_COLOR = COLOR_CYAN

# ==========================================
# 3. SETTINGS: PERFORMANCE & ENGINE SETTINGS
# ==========================================
# Max videos to fetch sizes for at the same time (Higher = faster, but heavy on network)
MAX_THREADS = 5

# Stop fetching sizes if this number of errors happens in a row (Anti-ban protection)
MAX_CONSECUTIVE_ERRORS = 10

# Draw videos on screen in groups to prevent app freezing
RENDER_CHUNK_SIZE = 15

# Default audio quality for MP3 conversions ("128", "192", "320")
AUDIO_BITRATE = "192"

# Show yt-dlp logs in the black terminal screen for debugging (True = Yes, False = No)
SHOW_TERMINAL_LOGS = True

# Network wait time (seconds) before giving up on a slow connection
SOCKET_TIMEOUT = 15

# Number of times to retry fetching video sizes if a network error occurs
FETCH_RETRIES = 3

# Number of times to retry a download if the connection drops mid-way
DOWNLOAD_RETRIES = 7

# ==========================================
# 4. DATA STORAGE (Saving user data)
# ==========================================
# The name of the file where user data (like name) is saved
USER_DATA_FILE_NAME = "user_data.json"

# The folder path to save the data file. 
# Leave it empty "" to save it safely inside Windows AppData.
USER_DATA_SAVE_DIR = ""

# Threshold size in gigabytes to trigger the package warning popup in GB
DATA_WARNING_LIMIT_THRESHOLD_GB = 1.0

# ==========================================
# 5. SYSTEM SOUNDS (Beeps and alerts)
# ==========================================
# Play a sound when a task finishes successfully? (True = Yes, False = No)
PLAY_SUCCESS_SOUND = True

# Source of the sounds ("windows" or "custom")
SOUND_SOURCE = "custom"

# Paths to your custom .wav files (used if SOUND_SOURCE is "custom")
CUSTOM_SUCCESS_SOUND_PATH = os.path.join(ASSETS_DIR, "sounds", "Success.wav")
CUSTOM_ERROR_SOUND_PATH = os.path.join(ASSETS_DIR, "sounds", "Error.wav")
CUSTOM_WARNING_SOUND_PATH = os.path.join(ASSETS_DIR, "sounds", "Warning.wav")
CUSTOM_INFO_SOUND_PATH = os.path.join(ASSETS_DIR, "sounds", "Info.wav")
CUSTOM_DATA_LIMIT_WARNING_SOUND_PATH = os.path.join(ASSETS_DIR, "sounds", "DataWarning.wav")
CUSTOM_EXIT_SOUND_PATH = os.path.join(ASSETS_DIR, "sounds", "Exit.wav")

def play_sound(sound_type="info"):
    """Plays system or custom sounds based on event type safely cross-platform"""
    
    if sys.platform != "win32":
        return # Skip sound on Mac/Linux to prevent crashes

    import winsound # Import here safely
    import logging  # Import logging to record missing sounds
    
    # Helper to check file and play, or log warning and play fallback
    def _play(path, fallback_sound, is_async=True):
        if SOUND_SOURCE == "custom" and os.path.exists(path):
            flags = winsound.SND_FILENAME
            if is_async: flags |= winsound.SND_ASYNC
            winsound.PlaySound(path, flags)
        else:
            if SOUND_SOURCE == "custom":
                logging.warning(f"Audio file missing: {path}")
            winsound.MessageBeep(fallback_sound)

    if sound_type == "success":
        if not PLAY_SUCCESS_SOUND: return 
        _play(CUSTOM_SUCCESS_SOUND_PATH, winsound.MB_ICONASTERISK)
            
    elif sound_type == "error":
        _play(CUSTOM_ERROR_SOUND_PATH, winsound.MB_ICONHAND)
            
    elif sound_type == "warning":
        _play(CUSTOM_WARNING_SOUND_PATH, winsound.MB_ICONEXCLAMATION)
            
    elif sound_type == "data_warning":
        _play(CUSTOM_DATA_LIMIT_WARNING_SOUND_PATH, winsound.MB_ICONEXCLAMATION)
            
    elif sound_type == "exit":
        if SOUND_SOURCE == "custom" and os.path.exists(CUSTOM_EXIT_SOUND_PATH):
            winsound.PlaySound(CUSTOM_EXIT_SOUND_PATH, winsound.SND_FILENAME)
        else:
            if SOUND_SOURCE == "custom":
                logging.warning(f"Audio file missing: {CUSTOM_EXIT_SOUND_PATH}")
            # Create a shutdown melody (3 notes going down)
            winsound.Beep(800, 150) # High note
            winsound.Beep(600, 150) # Middle note
            winsound.Beep(400, 250) # Low note
            
    else: # Default is "info"
        _play(CUSTOM_INFO_SOUND_PATH, winsound.MB_ICONASTERISK)

# ==========================================
# 6. ICONS & IMAGES (Paths to pictures)
# ==========================================
# Search button icon.
SEARCH_ICON_PATH = os.path.join(ASSETS_DIR, "search_icon.png")
SEARCH_ICON_SIZE = (15, 15)

# Speed setting icons.
SPEED_FAST_ICON_PATH = os.path.join(ASSETS_DIR, "fast_icon.png")
SPEED_SLOW_ICON_PATH = os.path.join(ASSETS_DIR, "slow_icon.png")
SPEED_ICON_SIZE = (22, 22)

# If image fails, use these emojis.
SPEED_FAST_FALLBACK_EMOJI = "🚀"
SPEED_SLOW_FALLBACK_EMOJI = "🐢"

# Contact button icon.
CONTACT_ICON_PATH = os.path.join(ASSETS_DIR, "chat_icon.png") 
CONTACT_ICON_SIZE = (22, 22)        

GMAIL_ICON_PATH = os.path.join(ASSETS_DIR, "gmail_icon.png")
GMAIL_ICON_SIZE = (22, 22)
GMAIL_FALLBACK_EMOJI = "📧"

COPY_ICON_PATH = os.path.join(ASSETS_DIR, "fast_icon.png") # Optional if you want to add an icon to the copy button

COPIED_ICON_PATH = os.path.join(ASSETS_DIR, "copied_icon.png")
COPIED_ICON_SIZE = (16, 16)
COPIED_FALLBACK_EMOJI = "✔"

# ==========================================
# 7. UI SIZES & RULES (Buttons and text)
# ==========================================
# Contact button settings.
CONTACT_BTN_WIDTH = 90
CONTACT_BTN_HEIGHT = 28
CONTACT_CORNER_RADIUS = 14

# Pulse effect times (in milliseconds).
CONTACT_DURATION_COLOR_1 = 1000  
CONTACT_DURATION_COLOR_2 = 1000  

# Pulse effect colors.
CONTACT_COLOR_1 = COLOR_MAGENTA
CONTACT_HOVER_1 = COLOR_CYAN_HOVER
CONTACT_COLOR_2 = "#96034C"
CONTACT_HOVER_2 = COLOR_CYAN_HOVER

# Welcome dialog OK button.
WELCOME_BTN_WIDTH = 100
WELCOME_BTN_COLOR = COLOR_MAGENTA
WELCOME_BTN_HOVER = COLOR_MAGENTA_HOVER

# Rules for user name.
NAME_ALLOW_NUMBERS = False
NAME_ALLOW_SYMBOLS = False
NAME_MIN_LENGTH = 2
NAME_MAX_LENGTH = 30
NAME_MAX_REPEATS = 2

# Social media buttons sizes and colors.
SOCIAL_BTN_WIDTH = 120
SOCIAL_LINKEDIN_COLOR = "#0077b5"
SOCIAL_LINKEDIN_HOVER = "#005582"
SOCIAL_WHATSAPP_COLOR = COLOR_MAGENTA
SOCIAL_WHATSAPP_HOVER = COLOR_MAGENTA_HOVER
SOCIAL_GITHUB_COLOR = COLOR_MAGENTA
SOCIAL_GITHUB_HOVER = COLOR_MAGENTA_HOVER
SOCIAL_EMAIL_COLOR = COLOR_CYAN
SOCIAL_EMAIL_HOVER = COLOR_CYAN_HOVER

# Gmail direct open button colors
SOCIAL_GMAIL_COLOR =   "#333333" 
SOCIAL_GMAIL_HOVER =   "#444444"

# Copy button colors
COPY_BTN_COLOR = COLOR_MAGENTA  #"#333333" 
COPY_BTN_HOVER = COLOR_MAGENTA_HOVER    #"#444444"

# Time for the button to stay green (in milliseconds)
EMAIL_COPY_DURATION_MS = 2500

# Exit window buttons colors.
EXIT_STAY_COLOR = COLOR_GREEN
EXIT_STAY_HOVER = COLOR_GREEN_HOVER
EXIT_LEAVE_COLOR = COLOR_RED
EXIT_LEAVE_HOVER = COLOR_RED_HOVER

# ==========================================
# 8. VIDEO QUALITIES (Options for user)
# ==========================================
QUALITY_BEST = "Best Quality"
QUALITY_MEDIUM = "Medium"
QUALITY_LOW = "Low"
QUALITY_AUDIO = "Audio Only (MP3)"

# ==========================================
# 9. VIDEO QUALITY ENGINE SETTINGS
# ==========================================

# This number (0.10 = 10%) helps us fix weird YouTube numbers.
# If a video size is 10% close to a standard size (like 720p or 1080p),
# we "snap" it to that standard size.
# If it is more than 10% different, we hide it from the user.
SNAP_THRESHOLD = 0.10

# ==========================================
# 10. LOGGING SETTINGS (Error Tracking)
# ==========================================
# Max size of the log file before creating a new one (1 MB = 1024 * 1024 bytes)
MAX_LOG_SIZE_BYTES = 20*1024 * 1024 
# How many old log files to keep
LOG_BACKUP_COUNT = 5

# =====================================================================
# 11. NETWORK TESTER ENGINE CONFIGURATION (CENTRALIZED)
# =====================================================================
# 1. JUST CHANGE THIS NUMBER: Set the speedtest file size in Megabytes (MB)
NET_TEST_SIZE_MB = 10 #(MB)

# 2. AUTOMATIC CALCULATIONS: The engine will calculate bytes and URL dynamically
NET_TEST_FILE_SIZE_BYTES = NET_TEST_SIZE_MB * 1024 * 1024
NET_SPEED_TEST_URL = f"https://speed.cloudflare.com/__down?bytes={NET_TEST_FILE_SIZE_BYTES}"

# 3. SAFETY AND SECURITY CONSTANTS
NET_TEST_TIMEOUT_SECONDS = 15.0           # Connection timeout limit
NET_TEST_INTERVAL_SECONDS = 86400        # Cache gate split (exactly 24 hours)
NET_USER_AGENT_SPOOF = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'

# ==========================================
# 12. FILE SYSTEM TESTING SETTINGS
# ==========================================
# Name of the hidden temporary file used to check if a folder is protected by Windows/OneDrive
DUMMY_TEST_FILE_NAME = ".ElmarakbyTube_Path_Test.tmp"

# ==========================================
# 13. SYSTEM SCAN & CACHING SETTINGS
# ==========================================
# How many days to wait before scanning the computer hardware again.
# 180 days = ~6 months. This prevents slowing down the app startup.
SYSTEM_INFO_CACHE_DAYS = 180

# ==========================================
# 14. ANALYTICS SCHEMA UPGRADE BEHAVIOR
# ==========================================
# What to do with the analytics file when the schema version changes
# (i.e. when you add/remove/rename fields and bump _schema_version in analytics.py).
#
#   "migrate" → KEEP the user's accumulated numbers. New fields start at their
#               default (0). Removed fields are dropped.
#
#   "reset"   → WIPE everything and start the file fresh from defaults (the old
#               behavior).
# Any unknown value is treated as "migrate" (the safe, non-destructive default).
ANALYTICS_SCHEMA_CHANGE_MODE = "migrate"