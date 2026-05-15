# Import the youtube download tool
import yt_dlp
# Import our tools and settings
from core.utils import format_duration
import config
import messages

# ==========================================
# RESOLUTION WHITELIST & SNAPPING LOGIC
# ==========================================

# We only accept these standard resolutions. Includes 8K (4320) and 16K (8640).
STANDARD_RESOLUTIONS = [8640, 4320, 2160, 1440, 1080, 720, 480, 360, 240, 144]



def _get_short_side(fmt: dict) -> int | None:
    """
    Get the short side of the video format safely.
    """
    w = fmt.get('width')
    h = fmt.get('height')

    if not w or not h:
        return None

    try:
        # Force numbers to be integers to prevent crashes from text or decimals.
        return min(int(w), int(h))
    except (ValueError, TypeError):
        return None

def _snap_to_standard(short_side: int) -> int | None:
    """
    Check if the short_side is close to a standard resolution.
    """
    for std in STANDARD_RESOLUTIONS:
        # Prevent dividing by zero if config is wrong.
        if std <= 0:
            continue
            
        if abs(short_side - std) / std <= config.SNAP_THRESHOLD:
            return std

    return None

def _extract_qualities(formats: list) -> list[str]:
    """
    Get a clean and sorted list of qualities.
    We use a set to automatically remove duplicates.
    """
    accepted_resolutions = set()

    for fmt in formats:
        short_side = _get_short_side(fmt)

        # Ignore formats with no size.
        if short_side is None:
            continue

        # Ignore useless qualities smaller than 144p.
        if short_side < 144:
            continue

        # Try to fix the raw resolution to a standard one.
        standard = _snap_to_standard(short_side)

        if standard is not None:
            accepted_resolutions.add(standard)

    # Sort the numbers from high to low.
    sorted_resolutions = sorted(list(accepted_resolutions), reverse=True)
    
    # Return strings with 'p' (Example: ["1080p", "720p"]).
    return [f"{res}p" for res in sorted_resolutions]

# ==========================================
# MAIN FETCH FUNCTION
# ==========================================

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
                # Format the duration
                dur = format_duration(entry.get('duration', 0))
                # Get video URL; reconstruct from id if the direct url is missing
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

            # For playlists, we use fixed quality names because checking each video is too slow.
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

            # Run our new extraction tool on the raw formats.
            raw_formats = info.get('formats', [])
            qualities = _extract_qualities(raw_formats)

            # Fallback if yt-dlp gives no usable video sizes.
            if not qualities:
                qualities = [config.QUALITY_BEST]

            # Always add Audio option at the end.
            qualities.append(config.QUALITY_AUDIO)

        # 6. Add "Select Quality" at the top, then return.
        qualities.insert(0, "Select Quality")
        return entries_data, qualities