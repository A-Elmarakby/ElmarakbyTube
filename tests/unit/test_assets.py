import os
import pytest
import config

def test_required_assets_exist():
    """
    Check if all image files defined in config.py actually exist 
    in the assets folder.
    """
    # List of all asset paths from config.py
    asset_paths = [
        config.ICON_FILE,
        config.SEARCH_ICON_PATH,
        config.CONTACT_ICON_PATH,
        config.SPEED_FAST_ICON_PATH,
        config.SPEED_SLOW_ICON_PATH
    ]
    
    for path in asset_paths:
        # Check if the file exists on the disk
        assert os.path.exists(path), f"Asset missing: {path}"

def test_assets_folder_exists():
    """
    Ensure the 'assets' directory itself exists.
    """
    assert os.path.isdir("assets"), "The 'assets' folder was not found!"