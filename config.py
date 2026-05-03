import os
import sys

# ==========================================
# 1. GENERAL APP SETTINGS
# ==========================================
# The name of the app.
APP_TITLE = "ElmarakbyTube Downloader"

# The path to the app icon (logo).
ICON_FILE = "assets/icon.ico"

# Default popup window size (width, height).
POPUP_WIDTH = 450
POPUP_HEIGHT = 200

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
SOCKET_TIMEOUT = 30

# Number of times to retry fetching video sizes if a network error occurs
FETCH_RETRIES = 3

# Number of times to retry a download if the connection drops mid-way
DOWNLOAD_RETRIES = 10

# ==========================================
# 4. DATA STORAGE (Saving user data)
# ==========================================
# The name of the file where user data (like name) is saved
USER_DATA_FILE_NAME = "user_data.json"

# The folder path to save the data file. 
# Leave it empty "" to save it safely inside Windows AppData.
USER_DATA_SAVE_DIR = ""

# ==========================================
# 5. SYSTEM SOUNDS (Beeps and alerts)
# ==========================================
# Play a sound when a task finishes successfully? (True = Yes, False = No)
PLAY_SUCCESS_SOUND = True

# Type of sound to play on success ("success", "info", "warning", "error")
SUCCESS_SOUND_TYPE = "success"

# Source of the success sound ("windows" or "custom")
SUCCESS_SOUND_SOURCE = "windows"

# If source is "custom", type the path to your .wav file (e.g., "sounds/success.wav")
CUSTOM_SUCCESS_SOUND_PATH = "success.wav"

def play_sound(sound_type="info"):
    """Plays system or custom sounds based on event type safely cross-platform"""
    
    if sys.platform != "win32":
        return # Skip sound on Mac/Linux to prevent crashes

    import winsound # Import here safely
    if sound_type == "success":
        if not PLAY_SUCCESS_SOUND:
            return 
        if SUCCESS_SOUND_SOURCE == "custom" and os.path.exists(CUSTOM_SUCCESS_SOUND_PATH):
            winsound.PlaySound(CUSTOM_SUCCESS_SOUND_PATH, winsound.SND_FILENAME | winsound.SND_ASYNC)
        else:
            winsound.MessageBeep(winsound.MB_ICONASTERISK)
    elif sound_type == "error":
        winsound.MessageBeep(winsound.MB_ICONHAND)
    elif sound_type == "warning":
        winsound.MessageBeep(winsound.MB_ICONEXCLAMATION)
    else:
        winsound.MessageBeep(winsound.MB_ICONASTERISK)


# ==========================================
# 6. ICONS & IMAGES (Paths to pictures)
# ==========================================
# Search button icon.
SEARCH_ICON_PATH = "assets/search_icon.png" 
SEARCH_ICON_SIZE = (15, 15)

# Speed setting icons.
SPEED_FAST_ICON_PATH = "assets/fast_icon.png"
SPEED_SLOW_ICON_PATH = "assets/slow_icon.png"
SPEED_ICON_SIZE = (22, 22)

# If image fails, use these emojis.
SPEED_FAST_FALLBACK_EMOJI = "🚀"
SPEED_SLOW_FALLBACK_EMOJI = "🐢"

# Contact button icon.
CONTACT_ICON_PATH = "assets/chat_icon.png" 
CONTACT_ICON_SIZE = (22, 22)        

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