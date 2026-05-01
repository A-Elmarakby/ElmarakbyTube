"""
File: converter.py
What it does: This file handles converting video/audio files to MP4 using FFmpeg.
Why we need it: To separate the hard processing logic from the UI buttons and colors.
"""

import os
import subprocess
import imageio_ffmpeg
import config

def convert_single_file(input_file, speed_choice, progress_callback, is_cancelled):
    """
    Convert a single downloaded file to MP4 safely.
    input_file: The path to the file on the computer.
    speed_choice: "fast" (copy) or "slow" (re-encode).
    progress_callback: A Walkie-Talkie to tell the UI the status.
    is_cancelled: A Walkie-Talkie to check if the user clicked stop.
    Returns: output_file_path (str) if successful, None if skipped/failed.
    """
    
    # 1. Validation Checks
    if not input_file or not os.path.exists(input_file):
        raise FileNotFoundError(f"File not found: {input_file}")

    # 2. Check if the file is already an MP4 or just an Audio file
    if input_file.endswith('.mp4'):
        progress_callback('already_mp4')
        return None
        
    if input_file.endswith(('.mp3', '.m4a', '.wav')):
        progress_callback('audio_file')
        return None

    # 3. Prepare the new MP4 filename
    output_file = os.path.splitext(input_file)[0] + '.mp4'

    # 4. Build the FFmpeg command based on user speed choice
    cmd = [imageio_ffmpeg.get_ffmpeg_exe(), '-y', '-i', input_file]
    
    if speed_choice == "fast":
        # Remux: Super fast, just change the container to mp4
        cmd.extend(['-c', 'copy'])
        progress_callback('started_remux')
    else:
        # Re-encode: Slow but more compatible
        cmd.extend(['-c:v', 'libx264', '-preset', 'fast', '-c:a', 'aac'])
        progress_callback('started_reencode')

    cmd.append(output_file)

    # 5. Start the heavy FFmpeg process
    process = None
    try:
        # Run FFmpeg silently in the background
        process = subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        
        # We need a small loop here to keep checking if the user clicked "Stop Convert"
        while process.poll() is None:
            # Check the walkie-talkie every 0.1 seconds
            if is_cancelled():
                process.terminate()
                raise InterruptedError("CONVERSION_CANCELLED_BY_USER")
            # Briefly sleep so we don't freeze the CPU
            import time
            time.sleep(0.1)
            
        # 6. Check if FFmpeg finished successfully (Code 0 means success)
        if process.returncode != 0 and not is_cancelled():
            raise RuntimeError("FFMPEG_ERROR: Something went wrong during conversion.")
            
        # Tell UI we are done
        progress_callback('finished')
        return input_file # We return the old file path so the UI can ask to delete it
        
    except Exception as e:
        # Make sure process is killed if an error happens
        if process:
            try: process.terminate()
            except: pass
        raise e