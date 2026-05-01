"""
tests/integration/test_downloads.py
===========================================================
Integration tests for the download and fetch logic.
Uses mocks to prevent real network calls to YouTube.
"""

import pytest
import ui.state as state

@pytest.fixture(scope="module")
def m(main_module):
    """Alias for the main module fixture."""
    return main_module

def test_fetch_size_success(m, mock_ydl_instance, mock_video_row):
    """
    Test fetching the size of a single video using a mock yt-dlp.
    Matches the 'mock_ydl_instance' fixture in conftest.py.
    """
    # 1. Setup mock to return 10 MB
    mock_ydl_instance.extract_info.return_value = {'filesize': 10485760}
    
    # 2. Set the fetch event to True via the module fixture (Thread-safe)
    state.fetch_event.set()
    
    # 3. Call the worker function
    m.fetch_size_for_single_video(mock_video_row, "Best Quality")
    
    # 4. Assert size was saved and UI label updated
    assert mock_video_row['bytes_size'] == 10485760
    assert mock_video_row['size_label']._state.get("text") == "10.0 MB"

def test_fetch_size_blocked_by_youtube(m, mock_ydl_instance, mock_video_row):
    """Test how the app handles a blocked connection or missing info."""
    # 1. Simulate YouTube blocking (returns None)
    mock_ydl_instance.extract_info.return_value = None
    
    state.fetch_event.set()
    
    m.fetch_size_for_single_video(mock_video_row, "Best Quality")
    
    # 2. Assert logic handles it as 0 bytes and marks as Blocked
    assert mock_video_row['bytes_size'] == 0
    assert mock_video_row['size_label']._state.get("text") == "Blocked"

def test_cancel_download_logic(m, mock_video_row):
    """Test that clicking cancel stops the download events."""
    # Access events directly from the module fixture to ensure we are testing the live state
    state.download_event.set()
    state.convert_event.set()
    mock_video_row['dl_state'] = 'downloading'
    
    # Simulate clicking Cancel
    m.on_cancel_download_click()
    
    # Verify events are cleared (OFF)
    assert not state.download_event.is_set()
    assert not state.convert_event.is_set()