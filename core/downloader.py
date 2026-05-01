"""
File: downloader.py
What it does: This file has the logic to download videos from YouTube.
Why we need it: We want to separate the download work from the screen buttons and colors.
"""

import os
import yt_dlp
import imageio_ffmpeg
import config

def get_ydl_format_string(quality):
    # Choose the right video format based on what the user selected
    if "Audio Only" in quality: return 'bestaudio/best'
    if "Medium" in quality or "720" in quality: return 'bestvideo[height<=720]+bestaudio/best'
    if "Low" in quality or "480" in quality: return 'bestvideo[height<=480]+bestaudio/best'
    
    # Extract numbers like 1080 from "1080p"
    height = ''.join(filter(str.isdigit, quality))
    if height: return f'bestvideo[height<={height}]+bestaudio/best'
    
    return 'bestvideo+bestaudio/best'

class DownloadLogger:
    # A simple tool to check if the file is already downloaded
    def __init__(self, callback):
        self.callback = callback
        
    def debug(self, msg):
        if config.SHOW_TERMINAL_LOGS: print(msg)
        # If yt-dlp says it is already downloaded, tell the main file using the walkie-talkie
        if "has already been downloaded" in msg or "already exists" in msg:
            self.callback('already_exists', 1.0, 0)
            
    def warning(self, msg): 
        if config.SHOW_TERMINAL_LOGS: print(msg)
        
    def error(self, msg): 
        if config.SHOW_TERMINAL_LOGS: print(msg)

def download_single_video(url, title, save_path, quality, progress_callback, is_cancelled):
    """
    Download one video safely.
    url: Link to the video.
    title: Name of the video.
    save_path: Folder to save the video.
    quality: Video quality (e.g., 1080p).
    progress_callback: A Walkie-Talkie to tell the UI the progress.
    is_cancelled: A Walkie-Talkie to ask the UI if the user clicked stop.
    """
    
    format_str = get_ydl_format_string(quality)
    postprocessors = []
    
    # If user wants MP3, tell yt-dlp to extract audio
    if "Audio Only" in quality:
        postprocessors = [{'key': 'FFmpegExtractAudio', 'preferredcodec': 'mp3', 'preferredquality': config.AUDIO_BITRATE}]

    def yt_dlp_hook(d):
        # Check if user clicked cancel
        if is_cancelled():
            raise ValueError("DOWNLOAD_CANCELLED")
            
        if d['status'] == 'downloading':
            total = d.get('total_bytes') or d.get('total_bytes_estimate', 0)
            downloaded = d.get('downloaded_bytes', 0)
            if total > 0:
                percent = downloaded / total
                # Send the numbers back to the UI
                progress_callback('downloading', percent, total)
                
        elif d['status'] == 'finished':
            # Tell UI we are done
            progress_callback('finished', 1.0, 0)

    ydl_opts = {
        'outtmpl': os.path.join(save_path, '%(title)s.%(ext)s'),
        'format': format_str,
        'progress_hooks': [yt_dlp_hook],
        'noplaylist': True,
        'quiet': True,
        'no_warnings': True,
        'continuedl': True, 
        'logger': DownloadLogger(progress_callback),
        'ffmpeg_location': imageio_ffmpeg.get_ffmpeg_exe(),
        'socket_timeout': config.SOCKET_TIMEOUT,
        'retries': config.DOWNLOAD_RETRIES
    }

    if postprocessors:
        ydl_opts['postprocessors'] = postprocessors

    # Start the download process
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        ydl.download([url])