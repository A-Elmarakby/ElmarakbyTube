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

#######################__5__############################
# Advanced Error Logging System
import logging
from logging.handlers import RotatingFileHandler
import sys
import traceback

def setup_logger(app_window=None):
    """Sets up the professional rotating log system to catch silent errors."""
    # 1. Choose where to save the log file (beside user_data.json)
    base_dir = os.path.dirname(get_user_data_path())
    log_file = os.path.join(base_dir, "ElmarakbyTube_Errors.log")

    # 2. Design how the text will look in the file
    # Example: [2026-05-22 14:30:00] [ERROR] [main.py]: Download failed
    log_format = logging.Formatter('[%(asctime)s] [%(levelname)s] [%(filename)s]: %(message)s', datefmt='%Y-%m-%d %H:%M:%S')

    # 3. Setup the file manager (Max 1MB, keep 2 backups)
    file_handler = RotatingFileHandler(log_file, maxBytes=config.MAX_LOG_SIZE_BYTES, backupCount=config.LOG_BACKUP_COUNT, encoding='utf-8')
    file_handler.setFormatter(log_format)

    # 4. Turn on the logger
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO) # Record INFO and above
    
    # Stop adding handlers if called twice
    if not root_logger.handlers:
        root_logger.addHandler(file_handler)

    # 5. Catch silent Python crashes
    def global_exception_handler(exc_type, exc_value, exc_traceback):
        if issubclass(exc_type, KeyboardInterrupt):
            sys.__excepthook__(exc_type, exc_value, exc_traceback)
            return
        logging.critical("Uncaught Python Exception!", exc_info=(exc_type, exc_value, exc_traceback))

    sys.excepthook = global_exception_handler

    # 6. Catch silent UI (Tkinter) crashes
    if app_window:
        def tk_exception_handler(exc, val, tb):
            logging.critical("Tkinter UI Exception!", exc_info=(exc, val, tb))
        app_window.report_callback_exception = tk_exception_handler

    logging.info("--- App Started Successfully ---")


def check_write_permission(directory):
    """
    Tests if the app has permission to write in the selected directory.
    Logs ONLY critical unexpected errors.
    """
    import os
    import logging
    import config
    
    test_file = os.path.join(directory, config.DUMMY_TEST_FILE_NAME)
    try:
        # Try to write
        with open(test_file, 'w') as f:
            f.write("write_test")
        
        # Try to clean up
        try:
            os.remove(test_file)
        except Exception:
            pass 
            
        return True
    
    except (PermissionError, FileNotFoundError):
        # NORMAL BEHAVIOR: Windows Defender or OneDrive blocked it. No need to log this.
        return False
        
    except Exception as e:
        # CRITICAL EDGE CASE: A hardware failure or deep OS error occurred! Log it!
        logging.critical(f"Critical error during path validation for '{directory}': {str(e)}", exc_info=True)
        return False