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

# ==================== System Sounds ====================
def play_sound(sound_type="info"):
    """Plays Windows system sounds based on event type"""
    if sound_type == "error":
        winsound.MessageBeep(winsound.MB_ICONHAND)
    elif sound_type == "warning":
        winsound.MessageBeep(winsound.MB_ICONEXCLAMATION)
    else:
        winsound.MessageBeep(winsound.MB_ICONASTERISK)