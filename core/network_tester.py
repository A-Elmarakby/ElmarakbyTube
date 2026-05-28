"""
File: network_tester.py
What it does: Runs a silent internet speed test in the background.
We test network speed once every 24 hours using a 1MB fixed file size to get a clean Mbps number.
"""

import time
import threading
import urllib.request
from core.analytics import load_analytics, record_speedtest_result

def run_background_speedtest(app=None):
    """
    Runs a silent network speed test in the background.
    Checks internet speed once every 24 hours using a 1MB fixed file size.
    Fully isolated using try-except blocks to guarantee zero application lag.
    """
    try:
        # 1. Check the 24-hour cache safety gate first
        data = load_analytics()
        current_time = time.time()
        
        if "download_metrics" in data and "internet_speed_profile" in data["download_metrics"]:
            last_run = data["download_metrics"]["internet_speed_profile"].get("last_speedtest_timestamp", 0.0)
            # 86400 seconds = exactly 24 hours
            if (current_time - last_run) < 86400:
                return # Skip testing to protect user internet package data limit

        # 2. Prepare the high-speed 1MB chunk download configuration
        test_url = "https://speed.cloudflare.com/__down?bytes=10048576"
        file_size_bytes = 10048576 # Exactly 1 Megabyte
        
        # We must act like a real web browser, or Cloudflare will block us (Error 403)
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
        req = urllib.request.Request(test_url, headers=headers)
        
        start_time = time.time()
        
        # Fetch the small chunk with a strict 4-second safety timeout using the fake browser ID
        with urllib.request.urlopen(req, timeout=4.0) as response:
            response.read() # Download the data completely into volatile memory
            
        time_taken = time.time() - start_time
        
        # 3. Calculate exact network speed in Mbps safely
        if time_taken > 0:
            speed_mbps = (file_size_bytes * 8.0) / (time_taken * 1024.0 * 1024.0)
            record_speedtest_result(speed_mbps)
            
    except Exception:
        # If connection fails completely at startup, inform the user safely via UI status bar
        if app:
            try:
                import ui.layout as layout
                import config
                app.after(0, lambda: layout.update_global_status(
                    "Offline Mode: Internet connection down or extremely weak.", 
                    config.COLOR_RED, 
                    "⚠️ Check Connection"
                ))
            except Exception:
                pass

def start_network_speed_assessment(app):
    """
    Launch the network testing daemon in a separate track.
    We add a 2-second sleep delay to let the UI finish rendering first.
    """
    def delay_wrapper():
        time.sleep(2.0) # Grace period to ensure main thread window is 100% active
        run_background_speedtest(app)
        
    threading.Thread(target=delay_wrapper, daemon=True).start()