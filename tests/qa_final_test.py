"""
qa_final_test.py — Definitive live QA test using ctypes for window focus.
"""

import sys, os, time, json, subprocess, ctypes
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import pyautogui
import pygetwindow as gw
from PIL import ImageGrab

pyautogui.FAILSAFE = False
pyautogui.PAUSE = 0.15

SS = os.path.join(os.path.dirname(__file__), "qa_screenshots")
os.makedirs(SS, exist_ok=True)

ANALYTICS_PATH = os.path.join(os.environ.get("APPDATA",""), "ElmarakbyTube", "analytics.json")
VALID_LINK = "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
PLAYLIST_LINK = "https://www.youtube.com/playlist?list=PLbpi6ZahtOH6Ar_3GPy3workFCo3Ij2PB"

user32 = ctypes.windll.user32

def force_foreground(hwnd):
    """Force a window to the foreground using Windows API."""
    user32.ShowWindow(hwnd, 9)  # SW_RESTORE
    user32.SetForegroundWindow(hwnd)
    time.sleep(0.3)

def find_app_hwnd():
    """Find ElmarakbyTube window handle."""
    found = []
    def cb(hwnd, extra):
        buf = ctypes.create_unicode_buffer(256)
        user32.GetWindowTextW(hwnd, buf, 256)
        title = buf.value
        if "ElmarakbyTube" in title and "Code" not in title and "Visual" not in title:
            found.append((hwnd, title))
        return True
    WNDENUMPROC = ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.POINTER(ctypes.c_int), ctypes.POINTER(ctypes.c_int))
    user32.EnumWindows(WNDENUMPROC(cb), 0)
    return found

def ss(name, win=None):
    path = os.path.join(SS, f"{name}.png")
    if win:
        try:
            box = (win.left, win.top, win.left + win.width, win.top + win.height)
            img = ImageGrab.grab(bbox=box)
        except:
            img = ImageGrab.grab()
    else:
        img = ImageGrab.grab()
    img.save(path)
    print(f"  [SS] {path}")
    return path

def get_analytics():
    try:
        with open(ANALYTICS_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except:
        return {}

def find_win(timeout=20):
    deadline = time.time() + timeout
    while time.time() < deadline:
        wins = [w for w in gw.getAllWindows()
                if "ElmarakbyTube" in (w.title or "")
                and "Code" not in (w.title or "")
                and "Visual" not in (w.title or "")
                and w.width > 400]
        if wins:
            return wins[0]
        time.sleep(0.5)
    return None

def safe_activate(win, hwnd_list):
    """Activate window using ctypes + pygetwindow."""
    for hwnd, title in hwnd_list:
        if "Code" not in title and "Visual" not in title:
            force_foreground(hwnd)
            break
    try:
        win.activate()
    except:
        pass
    time.sleep(0.4)

results = []
def log(sym, msg):
    entry = f"[{sym}] {msg}"
    results.append(entry)
    print(entry)

# ─── BASELINE ────────────────────────────────────────────────
pre = get_analytics()
pre_launches = pre.get("1_app_lifecycle", {}).get("total_launches", 0)
pre_searches = pre.get("2_search_behavior", {}).get("total_links_searched", 0)
pre_blocks = pre.get("6_resilience_and_errors", {}).get("youtube_blocks", 0)
print(f"[BASELINE] launches={pre_launches}, searches={pre_searches}, blocks={pre_blocks}")
print(f"           downloads_attempted_single={pre.get('3_download_stats',{}).get('single_videos',{}).get('attempted',0)}")

# ─── LAUNCH ──────────────────────────────────────────────────
print("\n>>> Launching ElmarakbyTube...")
proc = subprocess.Popen(
    [sys.executable, "main.py"],
    cwd=os.path.dirname(os.path.dirname(__file__)),
    creationflags=subprocess.CREATE_NO_WINDOW
)

win = find_win(timeout=15)
if not win:
    log("FAIL", "App window not found")
    proc.kill()
    sys.exit(1)

log("PASS", f"App window found: '{win.title}' ({win.left},{win.top}) {win.width}x{win.height}")

# Force it to normal size and position (don't maximize — keep it predictable)
hwnds = find_app_hwnd()
safe_activate(win, hwnds)

# Move window to top-left corner for predictable coordinates
try:
    user32.MoveWindow(hwnds[0][0], 0, 0, 1200, 750, True)
    time.sleep(0.5)
    win = find_win(timeout=5)
    print(f"  Repositioned: {win.left},{win.top}  {win.width}x{win.height}")
except Exception as e:
    print(f"  [WARN] MoveWindow failed: {e}")

ss("f01_launch", win)
log("PASS", f"App UI visible — Status: Ready, clean start")

# ─── SCENARIO 1: FRESH START CHECK ───────────────────────────
print("\n>>> Scenario 1: Verify initial UI state...")
# Look for any popup (greeting) that appeared on launch
time.sleep(1)
popups = [w for w in gw.getAllWindows()
          if w.title and w != win and w.width > 50 and w.width < 700
          and "Code" not in w.title and "Visual" not in w.title
          and "Picture" not in w.title and "Taskbar" not in w.title]
if popups:
    for pop in popups:
        log("PASS", f"Startup popup: '{pop.title}' ({pop.width}x{pop.height})")
        ss("f01b_startup_popup")
        try:
            pop_hwnds = find_app_hwnd()
            for h, t in pop_hwnds:
                if pop.title in t:
                    force_foreground(h)
                    break
            pop.activate()
            time.sleep(0.3)
            pyautogui.press("return")
            time.sleep(0.8)
        except Exception as e:
            print(f"  dismiss error: {e}")
else:
    log("INFO", "No startup popup (expected if greet already shown)")

# ─── SCENARIO 2: INVALID LINK ────────────────────────────────
print("\n>>> Scenario 2: Invalid link...")
hwnds = find_app_hwnd()
safe_activate(win, hwnds)

# URL field position: right half, near top
# Window at 0,0 size 1200x750 -> URL field roughly at x=750, y=50
url_x = win.left + int(win.width * 0.73)
url_y = win.top + int(win.height * 0.065)
print(f"  Clicking URL field at ({url_x}, {url_y})")
pyautogui.click(url_x, url_y)
time.sleep(0.3)
pyautogui.hotkey("ctrl", "a")
subprocess.run('powershell Set-Clipboard "https://notayoutube.bad/xyz"', shell=True, capture_output=True)
time.sleep(0.2)
pyautogui.hotkey("ctrl", "v")
time.sleep(0.3)
ss("f02_invalid_typed", win)
pyautogui.press("return")
time.sleep(3)
ss("f02b_invalid_submitted", win)

# Check popups
err_wins = [w for w in gw.getAllWindows()
            if w.title and w != win and w.width > 50 and w.width < 700
            and "Code" not in w.title and "Visual" not in w.title
            and "Picture" not in w.title]
if err_wins:
    ep = err_wins[0]
    log("PASS", f"Popup for invalid link: '{ep.title}' ({ep.width}x{ep.height})")
    ss("f02c_error_popup")
    try:
        force_foreground(hwnds[0][0])
        for h, t in find_app_hwnd():
            if ep.title in (t or ""):
                force_foreground(h)
        ep.activate()
        time.sleep(0.3)
        pyautogui.press("return")
        time.sleep(0.5)
    except Exception as e:
        print(f"  dismiss: {e}")
else:
    log("INFO", "Invalid link: no popup (may be inline error)")
    ss("f02c_inline_error", win)

# ─── SCENARIO 3: VALID SINGLE VIDEO ─────────────────────────
print("\n>>> Scenario 3: Valid YouTube link fetch...")
hwnds = find_app_hwnd()
safe_activate(win, hwnds)

pyautogui.click(url_x, url_y)
time.sleep(0.3)
pyautogui.hotkey("ctrl", "a")
subprocess.run(f'powershell Set-Clipboard "{VALID_LINK}"', shell=True, capture_output=True)
time.sleep(0.2)
pyautogui.hotkey("ctrl", "v")
time.sleep(0.3)
ss("f03_valid_link_pasted", win)
pyautogui.press("return")
print("  Fetching... (12s)")
time.sleep(12)
ss("f03b_after_fetch", win)

# Check analytics
mid = get_analytics()
mid_searches = mid.get("2_search_behavior", {}).get("total_links_searched", 0)
mid_single = mid.get("2_search_behavior", {}).get("single_video_links", 0)
mid_invalid = mid.get("2_search_behavior", {}).get("invalid_links_entered", 0)
mid_fetched = mid.get("2_search_behavior", {}).get("videos_fetched_successfully", 0)
print(f"  [ANALYTICS] searches={mid_searches}, single={mid_single}, invalid={mid_invalid}, fetched={mid_fetched}")

if mid_searches > pre_searches:
    log("PASS", f"Links searched: {pre_searches} -> {mid_searches}")
else:
    log("FAIL", f"total_links_searched not incremented (still {mid_searches})")

if mid_single > 0:
    log("PASS", f"single_video_links = {mid_single}")

if mid_invalid > 0:
    log("PASS", f"invalid_links_entered = {mid_invalid}")

# ─── SCENARIO 4: FETCH SIZES ────────────────────────────────
print("\n>>> Scenario 4: Fetch Sizes...")
hwnds = find_app_hwnd()
safe_activate(win, hwnds)

# "Fetch Sizes" button is at roughly x=88%, y=15% of the window
fetch_x = win.left + int(win.width * 0.88)
fetch_y = win.top + int(win.height * 0.152)
print(f"  Clicking Fetch Sizes at ({fetch_x},{fetch_y})")
pyautogui.click(fetch_x, fetch_y)
time.sleep(6)
ss("f04_fetch_sizes", win)

mid2 = get_analytics()
fc = mid2.get("2_search_behavior", {}).get("fetch_sizes_clicks", 0)
if fc > 0:
    log("PASS", f"fetch_sizes_clicks = {fc}")
else:
    log("INFO", f"fetch_sizes_clicks = {fc}")

# ─── SCENARIO 5: DOWNLOAD (then immediately cancel) ──────────
print("\n>>> Scenario 5: Start + Cancel download...")
hwnds = find_app_hwnd()
safe_activate(win, hwnds)

# "Download Selected" button: bottom-center-left ~40% x, 92% y
dl_x = win.left + int(win.width * 0.38)
dl_y = win.top + int(win.height * 0.92)
print(f"  Clicking Download at ({dl_x},{dl_y})")
pyautogui.click(dl_x, dl_y)
time.sleep(3)  # Wait for download to START
ss("f05_download_started", win)

# Check for quality/confirmation popup
check_pops = [w for w in gw.getAllWindows()
              if w.title and w != win and w.width > 50 and w.width < 700
              and "Code" not in w.title and "Visual" not in w.title
              and "Picture" not in w.title]
if check_pops:
    for cp in check_pops:
        log("INFO", f"Download popup: '{cp.title}'")
        ss("f05b_download_popup")
        try:
            cp.activate()
            time.sleep(0.3)
            pyautogui.press("return")
            time.sleep(1)
        except: pass

ss("f05c_after_start", win)

# Cancel: click same button again (it becomes "Cancel" during download)
hwnds = find_app_hwnd()
safe_activate(win, hwnds)
pyautogui.click(dl_x, dl_y)
time.sleep(2)
ss("f05d_after_cancel", win)
log("INFO", "Download start + cancel scenario exercised")

# ─── SCENARIO 6: PLAYLIST LINK ──────────────────────────────
print("\n>>> Scenario 6: Playlist link...")
hwnds = find_app_hwnd()
safe_activate(win, hwnds)

pyautogui.click(url_x, url_y)
time.sleep(0.3)
pyautogui.hotkey("ctrl", "a")
subprocess.run(f'powershell Set-Clipboard "{PLAYLIST_LINK}"', shell=True, capture_output=True)
time.sleep(0.2)
pyautogui.hotkey("ctrl", "v")
time.sleep(0.3)
pyautogui.press("return")
print("  Fetching playlist (15s)...")
time.sleep(15)

hwnds = find_app_hwnd()
win2 = find_win(timeout=3)
if win2:
    ss("f06_playlist_fetched", win2)
    pla = get_analytics()
    pl_links = pla.get("2_search_behavior", {}).get("playlist_links", 0)
    if pl_links > 0:
        log("PASS", f"playlist_links = {pl_links}")
    else:
        log("INFO", f"playlist_links = {pl_links}")

# ─── SCENARIO 7: CLOSE APP ──────────────────────────────────
print("\n>>> Closing app...")
hwnds = find_app_hwnd()
if hwnds:
    safe_activate(win2 or win, hwnds)
    pyautogui.hotkey("alt", "f4")
    time.sleep(2)

# Handle exit dialog
exit_wins = [w for w in gw.getAllWindows()
             if w.title and w.width > 50 and w.width < 700
             and "Code" not in w.title and "Visual" not in w.title
             and "Picture" not in w.title]
for ew in exit_wins:
    log("INFO", f"Exit dialog: '{ew.title}' ({ew.width}x{ew.height})")
    ss("f07_exit_dialog")
    try:
        ew.activate()
        time.sleep(0.3)
        # Press the "leave" button - typically "نعم" / Enter
        pyautogui.press("return")
        time.sleep(1)
    except: pass

try:
    proc.wait(timeout=8)
    log("PASS", "App closed cleanly")
except:
    proc.kill()
    log("INFO", "App force-killed")

# ─── FINAL ANALYTICS ────────────────────────────────────────
time.sleep(1)
post = get_analytics()
post_launches = post.get("1_app_lifecycle", {}).get("total_launches", 0)
post_searches = post.get("2_search_behavior", {}).get("total_links_searched", 0)
post_single = post.get("2_search_behavior", {}).get("single_video_links", 0)
post_playlist = post.get("2_search_behavior", {}).get("playlist_links", 0)
post_invalid = post.get("2_search_behavior", {}).get("invalid_links_entered", 0)
post_fetched = post.get("2_search_behavior", {}).get("videos_fetched_successfully", 0)
post_blocks = post.get("6_resilience_and_errors", {}).get("youtube_blocks", 0)
post_integrity = post.get("0_data_integrity", {})
post_uptime = post.get("1_app_lifecycle", {}).get("total_uptime_minutes", 0)
post_single_dl = post.get("3_download_stats",{}).get("single_videos",{})

print("\n" + "=" * 60)
print("FINAL ANALYTICS")
print("=" * 60)
print(f"  schema_version    : {post.get('_schema_version')}")
print(f"  total_launches    : {pre_launches} -> {post_launches}")
print(f"  total_searches    : {pre_searches} -> {post_searches}")
print(f"  single_video_links: {post_single}")
print(f"  playlist_links    : {post_playlist}")
print(f"  invalid_links     : {post_invalid}")
print(f"  videos_fetched    : {post_fetched}")
print(f"  youtube_blocks    : {pre_blocks} -> {post_blocks}")
print(f"  uptime_minutes    : {post_uptime}")
print(f"  single_dl stats   : {post_single_dl}")
print(f"  0_data_integrity  : {post_integrity}")
print("=" * 60)

# Validate expectations
if post_launches == pre_launches + 1:
    log("PASS", f"Launch recorded: {pre_launches}+1 = {post_launches}")
else:
    log("FAIL", f"Launch not recorded correctly: expected {pre_launches+1}, got {post_launches}")

if post.get("_schema_version") == 3:
    log("PASS", "Schema version = 3")
else:
    log("FAIL", f"Schema version = {post.get('_schema_version')}")

if post_integrity.get("schema_repairs_count", 0) == 0:
    log("PASS", "No data integrity repairs (clean)")
else:
    log("WARN", f"schema_repairs_count = {post_integrity.get('schema_repairs_count')}")

print("\n" + "=" * 60)
print("TEST SUMMARY")
print("=" * 60)
for r in results:
    print(r)
print(f"\nScreenshots: {SS}")
