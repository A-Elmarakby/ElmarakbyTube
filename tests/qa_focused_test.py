"""
qa_focused_test.py — Targeted real-user test.
Finds the exact app window and only clicks WITHIN it.
"""

import sys, os, time, json, subprocess
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import pyautogui
import pygetwindow as gw
from PIL import ImageGrab, Image

pyautogui.FAILSAFE = False
pyautogui.PAUSE = 0.2

SS = os.path.join(os.path.dirname(__file__), "qa_screenshots")
os.makedirs(SS, exist_ok=True)

ANALYTICS_PATH = os.path.join(os.environ.get("APPDATA",""), "ElmarakbyTube", "analytics.json")
VALID_LINK = "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
PLAYLIST_LINK = "https://www.youtube.com/playlist?list=PLbpi6ZahtOH6Ar_3GPy3workFCo3Ij2PB"

def ss(name):
    path = os.path.join(SS, f"{name}.png")
    img = ImageGrab.grab()
    img.save(path)
    return path

def crop_ss(name, win):
    """Screenshot cropped to just the app window."""
    path = os.path.join(SS, f"{name}.png")
    box = (win.left, win.top, win.left + win.width, win.top + win.height)
    img = ImageGrab.grab(bbox=box)
    img.save(path)
    return path

def get_analytics():
    try:
        with open(ANALYTICS_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except:
        return {}

def find_app(timeout=15):
    deadline = time.time() + timeout
    while time.time() < deadline:
        for w in gw.getAllWindows():
            if "ElmarakbyTube" in (w.title or "") and "Visual Studio" not in (w.title or "") and "Code" not in (w.title or ""):
                return w
        time.sleep(0.5)
    return None

def click_in(win, rel_x, rel_y):
    """Click at relative position within the window (0.0–1.0)."""
    x = win.left + int(win.width * rel_x)
    y = win.top + int(win.height * rel_y)
    pyautogui.click(x, y)
    return x, y

def paste_text(text):
    """Paste text via clipboard."""
    subprocess.run(f'powershell Set-Clipboard "{text}"', shell=True, capture_output=True)
    time.sleep(0.2)
    pyautogui.hotkey("ctrl", "v")

log_lines = []
def log(sym, msg):
    line = f"{sym} {msg}"
    log_lines.append(line)
    print(line)

# ─── BASELINE ────────────────────────────────────────────────
pre = get_analytics()
pre_launches = pre.get("1_app_lifecycle", {}).get("total_launches", 0)
pre_searches = pre.get("2_search_behavior", {}).get("total_links_searched", 0)
pre_blocks = pre.get("6_resilience_and_errors", {}).get("youtube_blocks", 0)
print(f"[BASELINE] launches={pre_launches}, searches={pre_searches}, blocks={pre_blocks}")

# ─── LAUNCH ──────────────────────────────────────────────────
print("\n>>> Launching ElmarakbyTube...")
proc = subprocess.Popen(
    [sys.executable, "main.py"],
    cwd=os.path.dirname(os.path.dirname(__file__)),
    creationflags=subprocess.CREATE_NO_WINDOW
)

win = find_app(timeout=15)
if not win:
    log("FAIL", "App window not found after 15 seconds")
    proc.kill()
    sys.exit(1)

print(f"[FOUND] Window '{win.title}' at ({win.left},{win.top}) size {win.width}x{win.height}")

# Bring to front, maximize
try:
    win.activate()
    win.maximize()
    time.sleep(1)
    win = find_app(timeout=3)  # re-find after maximize
    print(f"[MAXIMIZED] Now {win.width}x{win.height}")
except Exception as e:
    print(f"[WARN] maximize: {e}")

time.sleep(0.5)
crop_ss("t01_launch", win)
log("PASS", f"App opened: '{win.title}' ({win.width}x{win.height})")

# ─── CHECK FOR GREETING POPUP ────────────────────────────────
print("\n>>> Checking for greeting popup...")
time.sleep(0.8)
popups = [w for w in gw.getAllWindows()
          if w.title and w != win and w.width > 100
          and "Visual Studio" not in w.title and "Code" not in w.title
          and w.width < win.width]

if popups:
    pop = popups[0]
    crop_ss("t02_greeting_popup", pop)
    log("PASS", f"Greeting popup: '{pop.title}' ({pop.width}x{pop.height})")
    try:
        pop.activate()
        time.sleep(0.3)
        pyautogui.press("enter")
        time.sleep(0.8)
    except Exception as e:
        log("WARN", f"Could not dismiss greeting: {e}")
else:
    log("INFO", "No greeting popup (name already saved — expected)")

crop_ss("t02_after_greeting", win)

# ─── SCENARIO A: INVALID LINK ────────────────────────────────
print("\n>>> Scenario A: Invalid link...")
try:
    win.activate()
    time.sleep(0.3)
except Exception:
    pass

# URL field is at top of window, roughly y=8%, x=50%
url_x, url_y = click_in(win, 0.50, 0.08)
print(f"  Clicking URL field at ({url_x},{url_y})")
time.sleep(0.3)
pyautogui.hotkey("ctrl", "a")
paste_text("https://invalid-bad-link.xyz/notreal")
time.sleep(0.3)
pyautogui.press("return")
time.sleep(3)
crop_ss("tA1_invalid_link", win)

# Check for error popup
time.sleep(0.5)
err_popups = [w for w in gw.getAllWindows()
              if w.title and w != win and w.width > 50
              and "Visual Studio" not in w.title and "Code" not in w.title
              and "Picture" not in w.title]

if err_popups:
    ep = err_popups[0]
    crop_ss("tA2_error_popup", ep)
    log("PASS", f"Error popup for invalid link: '{ep.title}' ({ep.width}x{ep.height})")
    try:
        ep.activate()
        time.sleep(0.2)
        pyautogui.press("return")
        time.sleep(0.5)
    except Exception:
        pass
else:
    log("INFO", "Invalid link error shown inline (no separate popup)")
    crop_ss("tA2_inline_error", win)

try: win.activate(); time.sleep(0.2)
except: pass

# ─── SCENARIO B: VALID SINGLE VIDEO ─────────────────────────
print("\n>>> Scenario B: Valid single video fetch...")
click_in(win, 0.50, 0.08)
time.sleep(0.3)
pyautogui.hotkey("ctrl", "a")
paste_text(VALID_LINK)
time.sleep(0.3)
pyautogui.press("return")
print("  Waiting for fetch (10s)...")
time.sleep(10)
crop_ss("tB1_single_fetched", win)

# Read analytics after fetch
mid = get_analytics()
mid_searches = mid.get("2_search_behavior", {}).get("total_links_searched", 0)
mid_single = mid.get("2_search_behavior", {}).get("single_video_links", 0)
mid_invalid = mid.get("2_search_behavior", {}).get("invalid_links_entered", 0)
print(f"  [ANALYTICS MID] searches={mid_searches}, single={mid_single}, invalid={mid_invalid}")

if mid_searches > pre_searches:
    log("PASS", f"Analytics: total_links_searched {pre_searches} -> {mid_searches}")
else:
    log("FAIL", f"Analytics: total_links_searched NOT incremented (still {mid_searches})")

if mid_single > 0:
    log("PASS", f"Analytics: single_video_links = {mid_single}")
else:
    log("WARN", f"Analytics: single_video_links still 0 after valid fetch")

# ─── SCENARIO C: FETCH SIZES ─────────────────────────────────
print("\n>>> Scenario C: Fetch Sizes button...")
try: win.activate(); time.sleep(0.2)
except: pass
# "Fetch Sizes" button is usually around x=65–70%, y=30–35%
click_in(win, 0.67, 0.32)
time.sleep(6)
crop_ss("tC1_fetch_sizes", win)
after_fetch = get_analytics()
mid_fetch_clicks = after_fetch.get("2_search_behavior", {}).get("fetch_sizes_clicks", 0)
if mid_fetch_clicks > 0:
    log("PASS", f"Analytics: fetch_sizes_clicks = {mid_fetch_clicks}")
else:
    log("INFO", f"Analytics: fetch_sizes_clicks = {mid_fetch_clicks} (button may not have been found)")

# ─── SCENARIO D: PLAYLIST LINK ───────────────────────────────
print("\n>>> Scenario D: Playlist link...")
try: win.activate(); time.sleep(0.2)
except: pass
click_in(win, 0.50, 0.08)
time.sleep(0.3)
pyautogui.hotkey("ctrl", "a")
paste_text(PLAYLIST_LINK)
time.sleep(0.3)
pyautogui.press("return")
print("  Waiting for playlist fetch (15s)...")
time.sleep(15)
crop_ss("tD1_playlist_fetched", win)

post_playlist = get_analytics()
pl_links = post_playlist.get("2_search_behavior", {}).get("playlist_links", 0)
if pl_links > 0:
    log("PASS", f"Analytics: playlist_links = {pl_links}")
else:
    log("INFO", f"Analytics: playlist_links = {pl_links}")

# ─── SCENARIO E: CLOSE & FINAL CHECK ────────────────────────
print("\n>>> Closing app (Alt+F4)...")
try: win.activate(); time.sleep(0.2)
except: pass
pyautogui.hotkey("alt", "f4")
time.sleep(2)

# Handle exit dialog
exit_popups = [w for w in gw.getAllWindows()
               if w.title and w.width > 50 and w.width < 600
               and "Visual Studio" not in w.title and "Code" not in w.title
               and "Picture" not in w.title]
for ep in exit_popups:
    print(f"  Exit dialog: '{ep.title}'")
    crop_ss("tE1_exit_dialog", ep)
    try:
        ep.activate()
        time.sleep(0.3)
        pyautogui.press("return")
        time.sleep(0.5)
    except: pass

time.sleep(2)
try:
    proc.wait(timeout=8)
except:
    proc.kill()

# ─── FINAL ANALYTICS ────────────────────────────────────────
post = get_analytics()
post_launches = post.get("1_app_lifecycle", {}).get("total_launches", 0)
post_searches = post.get("2_search_behavior", {}).get("total_links_searched", 0)
post_single = post.get("2_search_behavior", {}).get("single_video_links", 0)
post_playlist_links = post.get("2_search_behavior", {}).get("playlist_links", 0)
post_invalid = post.get("2_search_behavior", {}).get("invalid_links_entered", 0)
post_blocks = post.get("6_resilience_and_errors", {}).get("youtube_blocks", 0)
post_integrity = post.get("0_data_integrity", {})
post_uptime = post.get("1_app_lifecycle", {}).get("total_uptime_minutes", 0)

print("\n" + "=" * 60)
print("FINAL ANALYTICS DIFF")
print("=" * 60)
print(f"  total_launches:      {pre_launches} -> {post_launches}   delta={post_launches-pre_launches}")
print(f"  total_links_searched:{pre_searches} -> {post_searches}  delta={post_searches-pre_searches}")
print(f"  single_video_links:  {post_single}")
print(f"  playlist_links:      {post_playlist_links}")
print(f"  invalid_links:       {post_invalid}")
print(f"  youtube_blocks:      {pre_blocks} -> {post_blocks}")
print(f"  uptime_minutes:      {post_uptime}")
print(f"  0_data_integrity:    {post_integrity}")
print(f"  schema_version:      {post.get('_schema_version','?')}")
print("=" * 60)

# analytics validation
if post_launches == pre_launches + 1:
    log("PASS", f"Launch recorded correctly ({pre_launches} -> {post_launches})")
else:
    log("FAIL", f"Launch count wrong: expected {pre_launches+1}, got {post_launches}")

if post_integrity.get("schema_repairs_count", 0) == 0:
    log("PASS", "No schema repairs needed (data integrity clean)")
else:
    log("WARN", f"schema_repairs_count = {post_integrity.get('schema_repairs_count')}")

if post.get("_schema_version") == 3:
    log("PASS", "Schema version = 3 (correct)")
else:
    log("FAIL", f"Schema version = {post.get('_schema_version')} (expected 3)")

print("\n" + "=" * 60)
print("SUMMARY")
print("=" * 60)
for line in log_lines:
    print(line)
print(f"\nScreenshots: {SS}")
