"""
File: downloader.py
What it does: This file has the logic to download videos from YouTube.
Why we need it: We want to separate the download work from the screen buttons and colors.
"""

import os
import yt_dlp
import imageio_ffmpeg
import config
import logging

def get_ydl_format_string(quality: str) -> str:
    """
    Change the quality string from the UI into a format that yt-dlp understands.
    """
    # 0. Safety check: stop if the user did not choose a quality.
    if quality == "Select Quality" or not quality.strip():
        raise ValueError("You must select a video quality first.")
    
    # 1. Check for Audio Only. This works for single videos and playlists.
    if "Audio Only" in quality:
        return 'bestaudio/best'

    # 2. Check for Playlist constants (Exact match is safer here).
    if quality == config.QUALITY_BEST:
        return 'bestvideo+bestaudio/best'

    if quality == config.QUALITY_MEDIUM:
        return 'bestvideo[height<=720]+bestaudio/best'

    if quality == config.QUALITY_LOW:
        return 'bestvideo[height<=480]+bestaudio/best'

    # 3. Extract numbers from the clean string.
    # Example: we take "1080" from "1080p".
    height_str = ''.join(filter(str.isdigit, quality))
    if height_str:
        return f'bestvideo[height<={height_str}]+bestaudio/best'

    # 4. Fallback if something goes wrong.
    return 'bestvideo+bestaudio/best'

def _record_network_retry(msg):
    """Count each automatic yt-dlp retry attempt for resilience analytics.
    yt-dlp may send 'Retrying (1/3)...' to either the debug or warning channel
    depending on the version, so we check both. Each message hits only one
    channel, so there is no double-count."""
    if "retrying" in msg.lower():
        try:
            from core.analytics import increment_stat
            increment_stat("6_resilience_and_errors", "network_retries")
        except Exception:
            pass

# Unambiguous YouTube-block signatures only (rate-limit / bot challenge).
# We deliberately exclude vague messages like "video unavailable" so we do
# not mis-attribute a deleted/private video as a block.
_YT_BLOCK_MARKERS = (
    "sign in to confirm you're not a bot",
    "sign in to confirm youre not a bot",
    "http error 429",
    "too many requests",
)

def _record_youtube_block(msg):
    """Count YouTube blocks that happen during the DOWNLOAD phase.
    The fetch (size) phase is counted separately in main.py when fetching
    auto-stops after MAX_CONSECUTIVE_ERRORS, so there is no double-count:
    these are two different phases of the app."""
    low = msg.lower()
    if any(marker in low for marker in _YT_BLOCK_MARKERS):
        try:
            from core.analytics import increment_stat
            increment_stat("6_resilience_and_errors", "youtube_blocks")
        except Exception:
            pass

class DownloadLogger:
    # A simple tool to check if the file is already downloaded
    def __init__(self, callback):
        self.callback = callback

    def debug(self, msg):
        if config.SHOW_TERMINAL_LOGS: print(msg)

        # Catch yt-dlp retries and network drops (they are sent as debug messages)
        msg_lower = msg.lower()
        if "retrying" in msg_lower or "giving up" in msg_lower:
            logging.warning(f"[yt-dlp Network Drop] {msg}")
        _record_network_retry(msg)

        # If yt-dlp says it is already downloaded, tell the main file using the walkie-talkie
        if "has already been downloaded" in msg or "already exists" in msg:
            self.callback('already_exists', 1.0, 0)

    def warning(self, msg):
        logging.warning(f"[yt-dlp] {msg}") # Save to file
        _record_network_retry(msg)
        if config.SHOW_TERMINAL_LOGS: print(msg)
        
    def error(self, msg):
        logging.error(f"[yt-dlp] {msg}") # Save to file
        _record_youtube_block(msg)
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

    # Clean quality string (e.g., "Audio Only (MP3)" -> "Audio_Only_MP3")
    clean_quality = quality.replace(" ", "_").replace("(", "").replace(")", "")
    
    # Get short app name ("ElmarakbyTube Downloader" -> "ElmarakbyTube")
    app_name = config.APP_TITLE.split()[0]
    
    # Build safe output name. We cut the title length to prevent Windows crashes.
    dynamic_outtmpl = os.path.join(save_path, f'%(title).{config.MAX_VIDEO_TITLE_LENGTH}s [{app_name}-{clean_quality}].%(ext)s')

    ydl_opts = {
        'outtmpl': dynamic_outtmpl,
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