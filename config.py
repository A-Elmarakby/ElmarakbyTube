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
COLOR_GREEN = "#398F3E"
COLOR_GREEN_HOVER = "#183B19"

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

# Show errors in the black terminal screen for debugging (True = Yes, False = No)
SHOW_TERMINAL_LOGS = True

# ==================== Contact Button Settings ====================
# Time in milliseconds between each pulse animation for the Contact button (10000 = 10 seconds)
CONTACT_PULSE_INTERVAL = 10000


# ==================== V2 UI & Validation Settings ====================

# --- Contact Us Button Configuration ---
CONTACT_BTN_WIDTH = 90
CONTACT_BTN_HEIGHT = 28
CONTACT_CORNER_RADIUS = 14

# Icon settings
CONTACT_ICON_PATH = "chat_icon.png" # Path to your colored PNG file
CONTACT_ICON_SIZE = (22, 22)        # Width and Height of the icon

# Pulse animation timing (in milliseconds)
CONTACT_DURATION_COLOR_1 = 1000  
CONTACT_DURATION_COLOR_2 = 2000  

# Background colors
CONTACT_COLOR_1 = COLOR_MAGENTA
CONTACT_HOVER_1 = COLOR_CYAN_HOVER
CONTACT_COLOR_2 = "#96034C"
CONTACT_HOVER_2 = COLOR_CYAN_HOVER



# --- Social Media Buttons (Contact Popup) ---
SOCIAL_BTN_WIDTH = 120
SOCIAL_LINKEDIN_COLOR = "#0077b5"
SOCIAL_LINKEDIN_HOVER = "#005582"

SOCIAL_WHATSAPP_COLOR = COLOR_MAGENTA
SOCIAL_WHATSAPP_HOVER = COLOR_MAGENTA_HOVER

SOCIAL_GITHUB_COLOR = COLOR_MAGENTA
SOCIAL_GITHUB_HOVER = COLOR_MAGENTA_HOVER

SOCIAL_EMAIL_COLOR = COLOR_CYAN
SOCIAL_EMAIL_HOVER = COLOR_CYAN_HOVER

# --- Exit Confirmation Buttons ---
EXIT_STAY_COLOR = COLOR_GREEN
EXIT_STAY_HOVER = COLOR_GREEN_HOVER

EXIT_LEAVE_COLOR = COLOR_RED
EXIT_LEAVE_HOVER = COLOR_RED_HOVER

# --- Name Validation Rules (Welcome Popup) ---
# 1. Allow Numbers? (True = Yes, False = No)
NAME_ALLOW_NUMBERS = False
# 2. Allow Symbols? (e.g., @, #, $, _) (True = Yes, False = No)
NAME_ALLOW_SYMBOLS = False
# 3. Minimum length of the name
NAME_MIN_LENGTH = 2
# 4. Maximum length of the name
NAME_MAX_LENGTH = 30
# 5. Maximum times a single letter can be repeated (e.g., 2 means 'aa' is ok, 'aaa' is rejected)
NAME_MAX_REPEATS = 2


# --- Welcome Dialog OK Button ---
WELCOME_BTN_WIDTH = 100
WELCOME_BTN_COLOR = COLOR_CYAN
WELCOME_BTN_HOVER = COLOR_CYAN_HOVER