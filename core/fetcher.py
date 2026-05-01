# Import the youtube download tool
import yt_dlp
# Import our tools and settings
from core.utils import format_duration
import config
import messages

def get_video_info(url):
    """
    Get video information from YouTube using a URL.
    Returns: A list of videos (entries_data) and a list of video qualities.
    """
    
    # 1. Check if the link is for a single video or a playlist
    is_single_video = ("watch?v=" in url) or ("youtu.be/" in url)
    
    # 2. Setup yt-dlp settings (quiet mode, do not download)
    ydl_opts = {
        'quiet': True, 
        'no_warnings': True,
        'extract_flat': 'in_playlist',
        'noplaylist': is_single_video
    }
    
    # 3. Connect to YouTube and get the data
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=False)
        
        qualities = []
        entries_data = [] 

        # 4. Handle playlist link
        if 'entries' in info:
            for idx, entry in enumerate(info['entries'], start=1):
                # Get title or use default if missing
                title = entry.get('title', messages.UNKNOWN_TITLE)
                # Format the time
                dur = format_duration(entry.get('duration', 0))
                # Get video URL
                vid_url = entry.get('url')
                if not vid_url: 
                    vid_url = f"https://www.youtube.com/watch?v={entry.get('id')}"
                    
                # Save video data to the list
                entries_data.append({
                    'idx': idx, 
                    'title': title, 
                    'dur': dur, 
                    'url': vid_url
                })
            
            # Default qualities for playlist
            qualities = [config.QUALITY_BEST, config.QUALITY_MEDIUM, config.QUALITY_LOW, config.QUALITY_AUDIO]
        
        # 5. Handle single video link
        else:
            title = info.get('title', messages.UNKNOWN_TITLE)
            dur = format_duration(info.get('duration', 0))
            vid_url = info.get('webpage_url', url)
            
            entries_data.append({
                'idx': 1, 
                'title': title, 
                'dur': dur, 
                'url': vid_url
            })
            
            # Find all available resolutions (like 1080p, 720p)
            formats = info.get('formats', [])
            q_set = set()
            for f in formats:
                h = f.get('height')
                if h and h > 0: 
                    q_set.add(f"{h}p")
            
            # Sort qualities from high to low
            qualities = sorted(list(q_set), key=lambda x: int(x.replace('p', '')), reverse=True)
            if not qualities: 
                qualities = [config.QUALITY_BEST]
            qualities.append(config.QUALITY_AUDIO)
            
        # 6. Return the clean data
        return entries_data, qualities