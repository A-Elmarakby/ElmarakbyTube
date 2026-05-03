"""
File: state.py
What it does: Stores shared variables, signals, and UI references.
Why we need it: Acts as a single source of truth to avoid circular imports.
"""

import threading

# --- Shared Data ---
video_rows = []           # List of all video row dictionaries
consecutive_errors = 0    # Counts consecutive YouTube fetch errors

# --- Threading Locks & Events ---
operation_lock = threading.Lock()   # Prevents overlapping operations
fetch_event = threading.Event()     # Signal: fetch is running
download_event = threading.Event()  # Signal: download is running
convert_event = threading.Event()   # Signal: conversion is running

# --- Process Handle ---
current_ffmpeg_process = None  # Reference to the live FFmpeg subprocess

# --- UI Widget References ---
# Set by layout.py after the widgets are created

# Main buttons
download_btn = None   
convert_btn = None
fetch_btn = None
stop_fetch_btn = None

# Input fields and options
path_entry = None
url_entry = None
quality_combo = None

# List and total info
list_frame = None
total_time_label = None
total_size_label = None

# Bottom text labels
global_status_label = None
global_warning_label = None

ui_list_lock = threading.Lock()   # Protects the video UI list
error_lock = threading.Lock()     # Protects the error counter