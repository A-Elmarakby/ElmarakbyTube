#######################__1__############################
# Safe ways to update text and progress bars without crashing the app
def apply_bidi(text):
    """Force Right-to-Left layout for normal text, labels, and buttons using Unicode."""
    text = str(text)
    if any('\u0600' <= c <= '\u06FF' for c in text):
        # Split by newlines to handle multi-line popups safely
        lines = text.split('\n')
        # Wrap EACH line strictly: [RLE][RLM] text [RLM][PDF]
        # This absolutely prevents punctuation (!, .) and English words from escaping to the wrong side.
        return '\n'.join(['\u202B\u200F' + line + '\u200F\u202C' for line in lines])
    return text



#######################__2__############################
# Change raw bytes into readable text like MB or GB
def format_size(bytes_size):
    if bytes_size <= 0: return "0.0 MB"
    mb = bytes_size / (1024 * 1024)
    if mb >= 1000:
        gb = mb / 1024
        return f"{gb:.2f} GB"
    return f"{mb:.1f} MB"



#######################__3__############################
# Change seconds to mm:ss format
def format_duration(seconds):
    if not seconds: return "00:00"
    m, s = divmod(int(seconds), 60)
    h, m = divmod(m, 60)
    if h > 0: return f"{h}:{m:02d}:{s:02d}"
    return f"{m:02d}:{s:02d}"

    #######################__4__############################
# User Data Management (Centralized state persistence)
import os
import json
import config

def get_user_data_path():
    """Calculate and ensure the dynamic path for saving user data."""
    if config.USER_DATA_SAVE_DIR.strip():
        base_dir = config.USER_DATA_SAVE_DIR
    else:
        appdata = os.getenv('APPDATA')
        if appdata: 
            base_dir = os.path.join(appdata, "ElmarakbyTube")
        else:
            # Fallback for missing APPDATA or Mac/Linux systems
            base_dir = os.path.join(os.path.expanduser("~"), ".ElmarakbyTube")
            
    # Ensure the directory exists before returning the file path (Creates it if missing)
    os.makedirs(base_dir, exist_ok=True)
    
    return os.path.join(base_dir, config.USER_DATA_FILE_NAME)

def load_user_data():
    """Safely load user data, returning an empty dictionary if file is missing or corrupted."""
    data_file = get_user_data_path()
    if not os.path.exists(data_file):
        return {}
    
    try:
        with open(data_file, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        # If file is corrupted (e.g., empty or invalid JSON), return empty dict safely
        return {}

def update_user_data(key, value):
    """Safely update a single key in the user data without erasing other data."""
    data = load_user_data()
    data[key] = value
    
    data_file = get_user_data_path()
    with open(data_file, "w", encoding="utf-8") as f:
        # Save with indent for readability and ensure_ascii=False for Arabic support
        json.dump(data, f, ensure_ascii=False, indent=4)