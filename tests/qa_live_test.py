"""
qa_live_test.py — Real-user simulation test for ElmarakbyTube.
Launches the actual app, interacts via pyautogui, captures screenshots.
Run from project root: python tests/qa_live_test.py
"""

import sys
import os
import time
import json
import subprocess
import threading

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import pyautogui
import pygetwindow as gw
from PIL import ImageGrab

pyautogui.FAILSAFE = False
pyautogui.PAUSE = 0.3

SCREENSHOTS_DIR = os.path.join(os.path.dirname(__file__), "qa_screenshots")
os.makedirs(SCREENSHOTS_DIR, exist_ok=True)

ANALYTICS_PATH = os.path.join(
    os.environ.get("APPDATA", ""),
    "ElmarakbyTube", "analytics.json"
)

VALID_LINK = "https://www.youtube.com/watch?v=dQw4w9WgXcQ"  # Rick Astley - short & reliable
PLAYLIST_LINK = "https://www.youtube.com/playlist?list=PLbpi6ZahtOH6Ar_3GPy3workFCo3Ij2PB"
INVALID_LINK = "https://www.youtube.com/watch?v=XXXXXXXXXXXX"


def screenshot(name):
    path = os.path.join(SCREENSHOTS_DIR, f"{name}.png")
    img = ImageGrab.grab()
    img.save(path)
    print(f"  📸 Screenshot: {path}")
    return path


def get_analytics():
    try:
        with open(ANALYTICS_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        return {"error": str(e)}


def wait_for_window(title_contains, timeout=20):
    """Wait until a window with the given title appears."""
    deadline = time.time() + timeout
    while time.time() < deadline:
        wins = gw.getWindowsWithTitle(title_contains)
        if wins:
            return wins[0]
        time.sleep(0.5)
    return None


def find_app_window():
    """Find ElmarakbyTube main window."""
    for title in ["ElmarakbyTube", "اليوتيوب", "YouTube"]:
        wins = gw.getWindowsWithTitle(title)
        if wins:
            return wins[0]
    # Try partial match
    all_wins = gw.getAllWindows()
    for w in all_wins:
        if "ElmarakbyTube" in w.title or "يوتيوب" in w.title:
            return w
    return None


def click_center(window, dx=0, dy=0):
    """Click at the center of a window with optional offset."""
    cx = window.left + window.width // 2 + dx
    cy = window.top + window.height // 2 + dy
    pyautogui.click(cx, cy)
    return cx, cy


results = []

def log(icon, msg, detail=""):
    entry = f"{icon} {msg}"
    if detail:
        entry += f"\n     {detail}"
    results.append(entry)
    print(entry)


print("=" * 60)
print("ElmarakbyTube — Live QA Test")
print("=" * 60)

# ─── BASELINE ────────────────────────────────────────────────
pre_analytics = get_analytics()
pre_launches = pre_analytics.get("1_app_lifecycle", {}).get("total_launches", 0)
log("📊", f"Analytics BEFORE test: total_launches={pre_launches}")

# ─── STEP 1: LAUNCH THE APP ──────────────────────────────────
print("\n[1/8] Launching app...")
proc = subprocess.Popen(
    [sys.executable, "main.py"],
    cwd=os.path.dirname(os.path.dirname(__file__)),
    stdout=subprocess.PIPE,
    stderr=subprocess.PIPE,
    creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0
)

time.sleep(4)  # Give CTk time to build the window

win = find_app_window()
if not win:
    # Try harder
    time.sleep(3)
    win = find_app_window()

if win:
    log("✅", f"App launched — window: '{win.title}' ({win.width}×{win.height})")
    try:
        win.activate()
        win.maximize()
    except Exception:
        pass
    time.sleep(0.8)
    screenshot("01_app_launched")
else:
    log("❌", "App window NOT found after 7s")
    proc.terminate()
    print("\n".join(results))
    sys.exit(1)

# ─── STEP 2: HANDLE GREETING DIALOG ─────────────────────────
print("\n[2/8] Checking greeting dialog...")
time.sleep(1)
all_wins = gw.getAllWindows()
popup_found = False
for w in all_wins:
    if w.title and w.title != win.title and any(k in w.title for k in ["مرحب", "أهلاً", "ElmarakbyTube"]):
        log("✅", f"Greeting popup detected: '{w.title}'")
        screenshot("02_greeting_popup")
        # Click OK / confirm
        try:
            w.activate()
            time.sleep(0.3)
            pyautogui.press("enter")
            time.sleep(0.5)
            screenshot("02b_after_greeting_dismiss")
        except Exception:
            pass
        popup_found = True
        break

if not popup_found:
    log("ℹ️", "No greeting dialog — user_data.json already set, skipped as expected")
    screenshot("02_no_greeting")

# ─── STEP 3: INVALID LINK ────────────────────────────────────
print("\n[3/8] Testing invalid link...")
time.sleep(1)
try:
    win.activate()
    time.sleep(0.3)
except Exception:
    pass

# Click the search/link entry area (top-center of the window)
search_x = win.left + win.width // 2
search_y = win.top + 80  # Approximate: near top
pyautogui.click(search_x, search_y)
time.sleep(0.4)
pyautogui.hotkey("ctrl", "a")
pyautogui.typewrite("https://invalid-not-youtube.com/bad", interval=0.02)
time.sleep(0.3)
pyautogui.press("enter")
time.sleep(3)
screenshot("03_invalid_link_entered")

# Check if an error popup appeared
all_wins_after = gw.getAllWindows()
error_popup = None
for w in all_wins_after:
    if w.title and w != win and w.width > 0:
        error_popup = w
        break

if error_popup:
    log("✅", f"Error popup appeared for invalid link: '{error_popup.title}'")
    screenshot("03b_error_popup")
    try:
        error_popup.activate()
        pyautogui.press("enter")
        time.sleep(0.5)
    except Exception:
        pass
else:
    log("ℹ️", "Error shown inline (no separate popup)")

# ─── STEP 4: VALID SINGLE VIDEO LINK ────────────────────────
print("\n[4/8] Pasting valid single video link...")
time.sleep(1)
try:
    win.activate()
    time.sleep(0.3)
except Exception:
    pass

# Clear and paste valid link
search_x = win.left + win.width // 2
search_y = win.top + 80
pyautogui.click(search_x, search_y)
time.sleep(0.4)
pyautogui.hotkey("ctrl", "a")
pyautogui.hotkey("ctrl", "c")  # copy to check
time.sleep(0.2)
pyautogui.hotkey("ctrl", "a")
import subprocess as _sp
_sp.run(f'powershell Set-Clipboard "{VALID_LINK}"', shell=True, capture_output=True)
time.sleep(0.2)
pyautogui.hotkey("ctrl", "v")
time.sleep(0.5)
screenshot("04_valid_link_pasted")
pyautogui.press("enter")
time.sleep(6)  # Wait for fetch
screenshot("04b_after_fetch")

# ─── STEP 5: CHECK VIDEO INFO APPEARED ──────────────────────
print("\n[5/8] Checking video info & Fetch Sizes...")
time.sleep(1)
screenshot("05_video_row_check")

# Try to click "Fetch Sizes" button
# It's typically in the middle area of the window
fetch_btn_y = win.top + int(win.height * 0.35)
fetch_btn_x = win.left + int(win.width * 0.75)
pyautogui.click(fetch_btn_x, fetch_btn_y)
time.sleep(5)
screenshot("05b_after_fetch_sizes")

# ─── STEP 6: TEST PLAYLIST LINK ─────────────────────────────
print("\n[6/8] Testing playlist link...")
try:
    win.activate()
    time.sleep(0.3)
except Exception:
    pass

search_x = win.left + win.width // 2
search_y = win.top + 80
pyautogui.click(search_x, search_y)
time.sleep(0.4)
pyautogui.hotkey("ctrl", "a")
_sp.run(f'powershell Set-Clipboard "{PLAYLIST_LINK}"', shell=True, capture_output=True)
time.sleep(0.2)
pyautogui.hotkey("ctrl", "v")
time.sleep(0.5)
screenshot("06_playlist_link_pasted")
pyautogui.press("enter")
time.sleep(8)  # Playlist takes longer to fetch
screenshot("06b_playlist_fetched")

# ─── STEP 7: CANCEL TEST (single video) ─────────────────────
print("\n[7/8] Testing cancel during download...")
# Go back to single video
try:
    win.activate()
    time.sleep(0.3)
except Exception:
    pass

search_x = win.left + win.width // 2
search_y = win.top + 80
pyautogui.click(search_x, search_y)
time.sleep(0.4)
pyautogui.hotkey("ctrl", "a")
_sp.run(f'powershell Set-Clipboard "{VALID_LINK}"', shell=True, capture_output=True)
time.sleep(0.2)
pyautogui.hotkey("ctrl", "v")
pyautogui.press("enter")
time.sleep(6)

# Find and click Download button (usually center-right area)
dl_btn_x = win.left + int(win.width * 0.85)
dl_btn_y = win.top + int(win.height * 0.4)
pyautogui.click(dl_btn_x, dl_btn_y)
time.sleep(2)
screenshot("07_download_started")

# Click cancel (same button area - it becomes cancel)
pyautogui.click(dl_btn_x, dl_btn_y)
time.sleep(2)
screenshot("07b_download_canceled")
log("✅", "Cancel scenario exercised")

# ─── STEP 8: CLOSE APP & CHECK ANALYTICS ────────────────────
print("\n[8/8] Closing app and checking analytics...")
try:
    win.close()
except Exception:
    try:
        pyautogui.hotkey("alt", "f4")
    except Exception:
        pass
time.sleep(3)

# Handle exit dialog if it appears
all_wins_final = gw.getAllWindows()
for w in all_wins_final:
    if w.title and "ElmarakbyTube" in w.title or (w.width > 0 and w.width < 500):
        try:
            w.activate()
            # Click the "Exit" / "نعم" button
            pyautogui.press("enter")
            time.sleep(1)
        except Exception:
            pass

time.sleep(2)
proc.wait(timeout=5) if proc.poll() is None else None
screenshot("08_app_closed")

# ─── ANALYTICS DIFF ─────────────────────────────────────────
post_analytics = get_analytics()
post_launches = post_analytics.get("1_app_lifecycle", {}).get("total_launches", 0)
post_searches = post_analytics.get("2_search_behavior", {}).get("total_links_searched", 0)
post_invalid = post_analytics.get("2_search_behavior", {}).get("invalid_links_entered", 0)
post_single_links = post_analytics.get("2_search_behavior", {}).get("single_video_links", 0)
post_playlist_links = post_analytics.get("2_search_behavior", {}).get("playlist_links", 0)
post_youtube_blocks = post_analytics.get("6_resilience_and_errors", {}).get("youtube_blocks", 0)
post_fetch_failures = post_analytics.get("6_resilience_and_errors", {}).get("fetch_failures", 0)

pre_youtube_blocks = pre_analytics.get("6_resilience_and_errors", {}).get("youtube_blocks", 0)
pre_fetch_failures = pre_analytics.get("6_resilience_and_errors", {}).get("fetch_failures", 0)
pre_searches = pre_analytics.get("2_search_behavior", {}).get("total_links_searched", 0)
pre_invalid = pre_analytics.get("2_search_behavior", {}).get("invalid_links_entered", 0)

print("\n" + "=" * 60)
print("ANALYTICS DIFF (before → after test):")
print(f"  total_launches:      {pre_launches} → {post_launches}  (+{post_launches - pre_launches})")
print(f"  total_links_searched:{pre_searches} → {post_searches}  (+{post_searches - pre_searches})")
print(f"  invalid_links:       {pre_invalid} → {post_invalid}  (+{post_invalid - pre_invalid})")
print(f"  single_video_links:  {post_single_links}")
print(f"  playlist_links:      {post_playlist_links}")
print(f"  youtube_blocks:      {pre_youtube_blocks} → {post_youtube_blocks}  (+{post_youtube_blocks - pre_youtube_blocks})")
print(f"  fetch_failures:      {pre_fetch_failures} → {post_fetch_failures}  (+{post_fetch_failures - pre_fetch_failures})")
print(f"  schema_version:      {post_analytics.get('_schema_version', '?')}")
print(f"  0_data_integrity:    {post_analytics.get('0_data_integrity', {})}")
print("=" * 60)

print("\n📋 FINDINGS:")
for r in results:
    print(r)

print(f"\n📁 Screenshots saved to: {SCREENSHOTS_DIR}")
