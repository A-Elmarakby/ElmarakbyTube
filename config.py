import winsound

# ==================== App Settings ====================
APP_TITLE = "ElmarakbyTube Downloader"
ICON_FILE = "icon.ico"

# ==================== Popup Dimensions ====================
POPUP_WIDTH = 450
POPUP_HEIGHT = 200

# ==================== Brand Colors ====================
COLOR_CYAN = "#007BA7"        
COLOR_CYAN_HOVER = "#005F83"
COLOR_MAGENTA = "#B20059"     
COLOR_MAGENTA_HOVER = "#8C0046"
COLOR_RED = "#D32F2F"         
COLOR_RED_HOVER = "#9A0007"

# ==================== Performance & Engine Settings ====================

# Maximum number of videos to fetch size for at the same time (Higher = faster, but uses more CPU/Network)
MAX_THREADS = 5

# Stop fetching sizes if this number of errors happens in a row (Prevents YouTube from blocking your IP)
MAX_CONSECUTIVE_ERRORS = 10

# Number of videos to draw on the screen at once (Prevents the app from freezing when loading large playlists)
RENDER_CHUNK_SIZE = 15

# Default audio quality for MP3 downloads (Options: "128", "192", "320")
AUDIO_BITRATE = "192"

# ==================== System Sounds ====================
def play_sound(sound_type="info"):
    """Plays Windows system sounds based on event type"""
    if sound_type == "error":
        winsound.MessageBeep(winsound.MB_ICONHAND)
    elif sound_type == "warning":
        winsound.MessageBeep(winsound.MB_ICONEXCLAMATION)
    else:
        winsound.MessageBeep(winsound.MB_ICONASTERISK)