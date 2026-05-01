#######################__1__############################
# Safe ways to update text and progress bars without crashing the app
def apply_bidi(text):
    """Force Right-to-Left layout for normal text, labels, and buttons using Unicode."""
    text = str(text)
    if any('\u0600' <= c <= '\u06FF' for c in text):
        # Split by newlines to handle multi-line popups safely
        lines = text.split('\n')
        # Wrap EACH line strictly: [RLE][RLM] text [RLM][PDF]
        # This absolutely prevents punctuation (!, .) and English words from escaping to the wrong side.
        return '\n'.join(['\u202B\u200F' + line + '\u200F\u202C' for line in lines])
    return text



#######################__2__############################
# Change raw bytes into readable text like MB or GB
def format_size(bytes_size):
    if bytes_size <= 0: return "0.0 MB"
    mb = bytes_size / (1024 * 1024)
    if mb >= 1000:
        gb = mb / 1024
        return f"{gb:.2f} GB"
    return f"{mb:.1f} MB"



#######################__3__############################
# Change seconds to mm:ss format
def format_duration(seconds):
    if not seconds: return "00:00"
    m, s = divmod(int(seconds), 60)
    h, m = divmod(m, 60)
    if h > 0: return f"{h}:{m:02d}:{s:02d}"
    return f"{m:02d}:{s:02d}"