"""
File: network_tester.py
What it does: Runs a silent internet speed test in the background.
Uses centralized variables from config.py and records speed results.
"""

import time
import threading
import urllib.request
import logging
import config
from core.analytics import load_analytics, record_speedtest_result

def run_background_speedtest(app=None):
    """
    Runs a silent network speed test in the background.
    Checks internet speed once every 24 hours using a 10MB fixed file size.
    Fully isolated using try-except blocks to guarantee zero application lag.
    """
    try:
        # 1. Check the 24-hour cache safety gate first using central config constant
        data = load_analytics()
        current_time = time.time()

        # Read the SAME path that record_speedtest_result() writes to (schema v2).
        # The old path "download_metrics.internet_speed_profile" no longer exists, so
        # the gate never engaged and a fresh speed test ran on every single launch.
        last_run = data.get("4_network_profile", {}).get("speed_test", {}).get("last_tested_timestamp", 0.0)

        # Use centralized interval constant (86400 seconds)
        if (current_time - last_run) < config.NET_TEST_INTERVAL_SECONDS:
            return # Skip testing to protect user internet package data limit

        # 2. Prepare the high-speed chunk download using config values
        test_url = config.NET_SPEED_TEST_URL
        file_size_bytes = config.NET_TEST_FILE_SIZE_BYTES
        
        # Act like a real web browser using the central configuration User-Agent spoof
        headers = {'User-Agent': config.NET_USER_AGENT_SPOOF}
        req = urllib.request.Request(test_url, headers=headers)
        
        start_time = time.time()
        
        # Fetch the chunk with a strict configuration safety timeout
        with urllib.request.urlopen(req, timeout=config.NET_TEST_TIMEOUT_SECONDS) as response:
            response.read() # Download the data completely into volatile memory
            
        time_taken = time.time() - start_time
        
        # 3. Calculate exact network speed in Mbps safely
        if time_taken > 0:
            speed_mbps = (file_size_bytes * 8.0) / (time_taken * 1024.0 * 1024.0)
            record_speedtest_result(speed_mbps)
            
    except Exception as e:
        # Log the error silently into ElmarakbyTube_Errors.log without freezing the UI
        logging.error(f"Background Speedtest Failed: {str(e)}") # Die 100% silently with zero UI interference or warnings for safe background testing

def start_network_speed_assessment(app):
    """
    Launch the network testing daemon in a separate track.
    We add a 2-second sleep delay to let the UI finish rendering first.
    """
    def delay_wrapper():
        time.sleep(2.0) # Grace period to ensure main thread window is 100% active
        run_background_speedtest(app)
        
    threading.Thread(target=delay_wrapper, daemon=True).start()