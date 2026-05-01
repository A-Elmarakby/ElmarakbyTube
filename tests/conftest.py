"""
conftest.py — Hybrid Session-Level GUI Mock & State Reset
==========================================================
This file creates fake versions of GUI modules for testing.
It prevents the app from opening windows during tests.
"""

import sys
import threading
import os
import pytest
from unittest.mock import MagicMock
import ui.state as state

# ─────────────────────────────────────────────────────────────────────────────
# 1. BUILD A STATEFUL MOCK WIDGET
# ─────────────────────────────────────────────────────────────────────────────
class MockWidget(MagicMock):
    """A fake widget that saves its state (like text and colors)."""
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._state: dict = {}
        self._value = kwargs.get("default_value", 0)
        self._checked = True

    def configure(self, **kwargs):
        """Save configuration changes so we can check them in tests."""
        self._state.update(kwargs)

    def cget(self, key):
        """Get a saved configuration value."""
        return self._state.get(key, "")

    def winfo_exists(self): 
        """Always return True to simulate a live widget."""
        return True

    def get(self):
        """Get value for Entry or Checkbox."""
        if "checkbox" in str(getattr(self, "_mock_name", "") or "").lower():
            return 1 if self._checked else 0
        return self._value

    def set(self, value): 
        self._value = value

    def select(self): 
        self._checked = True

    def deselect(self): 
        self._checked = False

    def pack(self, **kwargs): pass
    def pack_forget(self): pass
    def grid(self, **kwargs): pass
    def place(self, **kwargs): pass

    # THE CRITICAL FIX: Run UI updates immediately, but skip animations.
    def after(self, ms, func=None, *args):
        if func is None:
            return
        
        # Get the name of the function to be executed
        func_name = getattr(func, "__name__", "").lower()
        
        # Skip animation functions to prevent infinite loops and crashes
        if "animate" in func_name or "contact" in func_name:
            return
            
        # Run normal UI updates (like labels) immediately for the test
        try:
            func(*args)
        except Exception:
            pass

    def bind(self, *args, **kwargs): pass
    def bind_all(self, *args, **kwargs): pass
    def protocol(self, *args, **kwargs): pass
    def destroy(self): pass
    def update_idletasks(self): pass
    def winfo_children(self): return []
    def start(self): pass
    def stop(self): pass
    def grab_set(self): pass
    def transient(self, *a): pass
    def wait_window(self, *a): pass
    def geometry(self, *a): pass
    def title(self, *a): pass
    def iconbitmap(self, *a, **kw): pass

# ─────────────────────────────────────────────────────────────────────────────
# 2. INJECT MOCKS INTO sys.modules BEFORE IMPORT
# ─────────────────────────────────────────────────────────────────────────────
def _build_ctk_mock():
    """Create a fake CustomTkinter module."""
    ctk = MagicMock(name="customtkinter")
    mock_app = MockWidget(name="CTkApp")
    ctk.CTk = MagicMock(return_value=mock_app)
    for widget_name in ["CTkFrame", "CTkLabel", "CTkButton", "CTkEntry", "CTkCheckBox", "CTkComboBox", "CTkScrollableFrame", "CTkProgressBar", "CTkToplevel", "CTkImage"]:
        setattr(ctk, widget_name, MagicMock(side_effect=lambda *a, name=widget_name, **kw: MockWidget(name=name)))
    return ctk

def _build_ytdlp_mock():
    """Create a fake yt-dlp module."""
    ytdlp = MagicMock(name="yt_dlp")
    mock_ydl_instance = MagicMock()
    mock_ydl_instance.__enter__ = MagicMock(return_value=mock_ydl_instance)
    ytdlp.YoutubeDL = MagicMock(return_value=mock_ydl_instance)
    # Mock the utils submodule
    ytdlp.utils = MagicMock(name="yt_dlp.utils")
    ytdlp.utils.sanitize_filename = MagicMock(side_effect=lambda x: x)
    return ytdlp, mock_ydl_instance

# Inject all fake modules into Python memory
sys.modules["customtkinter"] = _build_ctk_mock()
sys.modules["tkinter"] = MagicMock(name="tkinter")
sys.modules["tkinter.filedialog"] = MagicMock()
sys.modules["tkinter.dialog"] = MagicMock()
_mock_ytdlp, _mock_ydl_instance = _build_ytdlp_mock()
sys.modules["yt_dlp"] = _mock_ytdlp
sys.modules["yt_dlp.utils"] = _mock_ytdlp.utils
sys.modules["PIL"] = MagicMock(name="PIL")
sys.modules["imageio_ffmpeg"] = MagicMock(name="imageio_ffmpeg")

# Add project folder to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

# ─────────────────────────────────────────────────────────────────────────────
# 3. FIXTURES & STATE RESET
# ─────────────────────────────────────────────────────────────────────────────
@pytest.fixture(scope="session")
def main_module():
    """Import the main.py file once for all tests."""
    import main as m
    yield m

@pytest.fixture(autouse=True)
def reset_app_state(main_module):
    """Clean up memory before every single test."""
    # 1. Clear the video list
    state.video_rows.clear()
    
    # 2. Reset error counter
    state.consecutive_errors = 0
    
    # 3. Release locks if they are stuck
    if hasattr(state, 'operation_lock') and state.operation_lock.locked():
        state.operation_lock.release()
    if hasattr(state, 'ui_list_lock') and state.ui_list_lock.locked():
        state.ui_list_lock.release()
    if hasattr(state, 'error_lock') and state.error_lock.locked():
        state.error_lock.release()
        
    # 4. Clear all events (signals)
    if hasattr(state, 'fetch_event'): state.fetch_event.clear()
    if hasattr(state, 'download_event'): state.download_event.clear()
    if hasattr(state, 'convert_event'): state.convert_event.clear()
    
    # 5. Reset FFmpeg process
    state.current_ffmpeg_process = None
    
    yield

@pytest.fixture
def fresh_events():
    """Provide clean threading events for testing logic."""
    return {
        "operation_lock": threading.Lock(),
        "fetch_event": threading.Event(),
        "download_event": threading.Event(),
        "convert_event": threading.Event(),
    }

@pytest.fixture
def mock_video_row():
    """Provide a fake video row data structure."""
    checkbox = MockWidget(name="checkbox")
    checkbox._checked = True
    return {
        "frame": MockWidget(name="frame"),
        "checkbox": checkbox,
        "title": "Test Video",
        "duration": "03:45",
        "progress": MockWidget(name="progress"),
        "size_label": MockWidget(name="size_label"),
        "status_label": MockWidget(name="status_label"),
        "percent_label": MockWidget(name="percent_label"),
        "url": "https://www.youtube.com/watch?v=TEST",
        "bytes_size": -1,
        "dl_state": "ready",
        "error_msg": "",
    }

@pytest.fixture
def mock_ydl_instance():
    """Expose the shared yt-dlp mock to tests."""
    return _mock_ydl_instance