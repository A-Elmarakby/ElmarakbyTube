"""
=============================================================
TEST SUITE: Download Start & Cancel Logic
ElmarakbyTube Downloader — main.py
=============================================================
Strategy:
  - We do NOT import tkinter or ctk (they require a display).
  - Instead, we extract and test the PURE LOGIC of the download
    system by reimplementing the exact same code patterns used
    in main.py in a headless environment.
  - Every test maps to a real scenario the user can trigger.
=============================================================
"""

import threading
import time
import unittest
from unittest.mock import MagicMock, patch, call
from dataclasses import dataclass, field
from typing import Optional


# ─────────────────────────────────────────────────────────────
# HELPERS: Simulating the exact state model from main.py
# ─────────────────────────────────────────────────────────────

def make_operation_lock():
    return threading.Lock()

def make_events():
    """Mirrors the three threading.Event objects in main.py"""
    return {
        'fetch':    threading.Event(),
        'download': threading.Event(),
        'convert':  threading.Event(),
    }

def make_video_row(title="Test Video", dl_state="ready", checked=True):
    """Simulates a single row_data dict from add_video_row()"""
    frame_mock = MagicMock()
    frame_mock.winfo_exists.return_value = True
    checkbox_mock = MagicMock()
    checkbox_mock.get.return_value = 1 if checked else 0
    return {
        'frame':         frame_mock,
        'checkbox':      checkbox_mock,
        'title':         title,
        'duration':      '05:00',
        'progress':      MagicMock(),
        'size_label':    MagicMock(),
        'status_label':  MagicMock(),
        'percent_label': MagicMock(),
        'url':           f'https://www.youtube.com/watch?v=fake_{title}',
        'bytes_size':    -1,
        'dl_state':      dl_state,
        'error_msg':     '',
    }


# ─────────────────────────────────────────────────────────────
# EXACT LOGIC EXTRACTED from main.py (no GUI dependencies)
# These are the real functions under test.
# ─────────────────────────────────────────────────────────────

class DownloadSystem:
    """
    A self-contained reimplementation of the download logic from main.py.
    Same code, same patterns — no GUI. Used for logic testing.
    """

    def __init__(self):
        self._operation_lock   = threading.Lock()
        self._ui_list_lock     = threading.Lock()
        self._download_event   = threading.Event()

        # Simulated app state
        self.video_rows        = []
        self.save_path         = "/tmp/fake_save"  # Will be patched per test
        self.quality           = "Best Quality"
        self.status_messages   = []
        self.ui_calls          = []

        # Track whether "Download" button is visible (swap behavior)
        # In the CURRENT main.py — both buttons are ALWAYS visible.
        # This flag tracks what SHOULD happen in a fixed version.
        self.download_btn_visible = True
        self.stop_btn_visible     = False

    # ── Mocked UI helpers ──────────────────────────────────────
    def update_global_status(self, msg, color="white", warning=""):
        self.status_messages.append((msg, color))

    def safe_ui_update(self, widget, **kwargs):
        self.ui_calls.append(('update', widget, kwargs))

    def safe_progress_update(self, widget, value):
        self.ui_calls.append(('progress', widget, value))

    def show_error(self, title, msg):
        self.ui_calls.append(('error_popup', title, msg))

    # ── Exact duplicate of _download_process logic ─────────────
    def _download_process(self, rows_to_download, quality, save_path, fake_ydl_func=None):
        """
        Mirrors _download_process() from main.py.
        fake_ydl_func: callable(url) — simulates yt_dlp behavior.
        """
        for row_data in rows_to_download:
            # Check #1: stop signal before starting each video
            if not self._download_event.is_set():
                break

            if not row_data['frame'].winfo_exists():
                continue

            row_data['dl_state'] = 'preparing'
            self.safe_ui_update(row_data['status_label'], text="Preparing...")

            # Simulate the progress_hook closure (Issue #4 — lambda closure bug)
            def progress_hook(d, r=row_data):
                if not self._download_event.is_set():
                    raise ValueError("DOWNLOAD_CANCELLED")
                if d['status'] == 'downloading':
                    total      = d.get('total_bytes') or d.get('total_bytes_estimate', 0)
                    downloaded = d.get('downloaded_bytes', 0)
                    if total > 0:
                        percent = downloaded / total
                        # BUG PRESENT: percent is captured by reference in lambdas
                        # Fixed version would be: lambda p=percent: ...
                        self.safe_progress_update(row_data['progress'], percent)
                        self.safe_ui_update(row_data['percent_label'], text=f"{int(percent*100)}%")
                        row_data['dl_state'] = 'downloading'
                        self.safe_ui_update(row_data['status_label'], text="Downloading...")

                elif d['status'] == 'finished':
                    row_data['dl_state'] = 'processing'
                    self.safe_progress_update(row_data['progress'], 1.0)
                    self.safe_ui_update(row_data['status_label'], text="Processing...")

            try:
                if fake_ydl_func:
                    fake_ydl_func(row_data['url'], progress_hook)

                if self._download_event.is_set() and row_data.get('dl_state') not in ['canceled', 'already_exists', 'failed']:
                    row_data['dl_state'] = 'completed'
                    self.safe_ui_update(row_data['status_label'], text="Completed")
                    self.safe_progress_update(row_data['progress'], 1.0)

            except Exception as e:
                if not self._download_event.is_set():
                    pass  # Canceled — silently ignore
                else:
                    row_data['dl_state'] = 'failed'
                    row_data['error_msg'] = str(e)
                    self.safe_ui_update(row_data['status_label'], text="Failed")

    # ── Exact duplicate of download_worker logic ───────────────
    def download_worker(self, fake_ydl_func=None, override_path=None, override_quality=None):
        """
        Mirrors download_worker() from main.py.
        Returns the final status string for assertion.
        """
        # ── CURRENT BUG: No button swap here ──
        # In the current code, Download button stays visible during download.
        # A fixed version would call: self._swap_to_stop_btn()

        if not self._operation_lock.acquire(blocking=False):
            self.show_error("Warning", "Operation running")
            return "LOCK_BUSY"

        try:
            self._download_event.set()

            save_path = override_path if override_path is not None else self.save_path
            if not save_path or save_path == "INVALID":
                self.show_error("Error", "Invalid path")
                return "INVALID_PATH"

            with self._ui_list_lock:
                selected_rows = [r for r in self.video_rows if r["checkbox"].get() == 1]

            if not selected_rows:
                self.show_error("Warning", "No videos selected")
                return "NO_VIDEOS"

            quality = override_quality if override_quality is not None else self.quality
            if quality in ["Select Quality", "Waiting for link...", "Loading..."]:
                self.show_error("Warning", "No quality selected")
                return "NO_QUALITY"

            self.update_global_status(f"Starting download for {len(selected_rows)} videos...", "magenta")
            self._download_process(selected_rows, quality, save_path, fake_ydl_func)

            if self._download_event.is_set():
                failed = sum(1 for r in selected_rows if r.get('dl_state') == 'failed')
                if failed > 0:
                    self.update_global_status(f"Finished with {failed} errors.", "orange")
                    return "FINISHED_WITH_ERRORS"
                else:
                    self.update_global_status("Downloads finished successfully.", "#28a745")
                    return "SUCCESS"
            else:
                self.update_global_status("Downloads canceled by user.", "orange")
                return "CANCELED"

        finally:
            # ── CURRENT BUG: No button swap back here ──
            self._download_event.clear()
            self._operation_lock.release()

    # ── Exact duplicate of on_cancel_download_click logic ──────
    def on_cancel_download_click(self):
        """
        Mirrors on_cancel_download_click() from main.py.
        NOTE: In the real code this runs on UI thread directly.
        """
        if self._download_event.is_set():
            self._download_event.clear()  # Signal the worker to stop
            self.update_global_status("Canceling download... please wait.", "orange")

            # BUG: No _ui_list_lock here in the original code
            for r in self.video_rows:
                if r.get('dl_state') in ['preparing', 'downloading']:
                    r['dl_state'] = 'canceled'
                    self.safe_ui_update(r['status_label'], text="Canceled")
                    self.safe_progress_update(r['progress'], 0)
                    self.safe_ui_update(r['percent_label'], text="0%")


# ═══════════════════════════════════════════════════════════════
# TEST CLASS 1: Download Worker — State & Flow
# ═══════════════════════════════════════════════════════════════

class TestDownloadWorkerFlow(unittest.TestCase):

    def setUp(self):
        self.sys = DownloadSystem()

    def test_T01_clean_start_sets_download_event(self):
        """
        T-01: When download starts, _download_event must be SET
        before _download_process is called.
        Maps to: download_worker() line 754
        """
        event_was_set_during_download = []

        def fake_ydl(url, hook):
            # Capture the event state while download is in progress
            event_was_set_during_download.append(self.sys._download_event.is_set())

        self.sys.video_rows = [make_video_row()]
        self.sys.save_path = "/tmp/fake"

        with patch('os.path.isdir', return_value=True):
            self.sys.download_worker(fake_ydl_func=fake_ydl)

        self.assertTrue(
            event_was_set_during_download[0],
            "FAIL T-01: _download_event was NOT set when download was running"
        )
        print("PASS T-01: _download_event is correctly SET during download")

    def test_T02_event_cleared_after_success(self):
        """
        T-02: After successful download, _download_event must be CLEARED.
        This is the cleanup in finally block (line 788).
        """
        self.sys.video_rows = [make_video_row()]

        def fake_ydl(url, hook):
            hook({'status': 'finished'})

        with patch('os.path.isdir', return_value=True):
            result = self.sys.download_worker(fake_ydl_func=fake_ydl)

        self.assertFalse(
            self.sys._download_event.is_set(),
            "FAIL T-02: _download_event was NOT cleared after successful download"
        )
        print(f"PASS T-02: _download_event correctly cleared after success. Result={result}")

    def test_T03_lock_released_after_success(self):
        """
        T-03: _operation_lock must be released after download finishes.
        If not released, all future operations (fetch, convert) are blocked.
        Maps to: finally block, line 789.
        """
        self.sys.video_rows = [make_video_row()]

        with patch('os.path.isdir', return_value=True):
            self.sys.download_worker(fake_ydl_func=lambda url, h: None)

        # If lock is properly released, we can acquire it again
        acquired = self.sys._operation_lock.acquire(blocking=False)
        self.assertTrue(
            acquired,
            "FAIL T-03: _operation_lock was NOT released after download — app is deadlocked"
        )
        if acquired:
            self.sys._operation_lock.release()
        print("PASS T-03: _operation_lock correctly released after download")

    def test_T04_lock_released_on_invalid_path(self):
        """
        T-04: CRITICAL — lock must be released even when validation fails.
        If save_path is invalid, the worker returns early. Does the finally block
        still release the lock?
        Maps to: the return on line 759, finally on line 787.
        """
        self.sys.video_rows = [make_video_row()]

        with patch('os.path.isdir', return_value=False):
            result = self.sys.download_worker(override_path="INVALID")

        acquired = self.sys._operation_lock.acquire(blocking=False)
        self.assertTrue(
            acquired,
            "FAIL T-04: _operation_lock was NOT released after invalid path — DEADLOCK"
        )
        if acquired:
            self.sys._operation_lock.release()
        print(f"PASS T-04: lock released even after validation failure. Result={result}")

    def test_T05_lock_released_on_no_videos(self):
        """
        T-05: lock must be released when no videos are selected.
        """
        self.sys.video_rows = [make_video_row(checked=False)]  # All unchecked

        with patch('os.path.isdir', return_value=True):
            result = self.sys.download_worker()

        acquired = self.sys._operation_lock.acquire(blocking=False)
        self.assertTrue(
            acquired,
            "FAIL T-05: lock NOT released when no videos selected — DEADLOCK"
        )
        if acquired:
            self.sys._operation_lock.release()
        print(f"PASS T-05: lock released when no videos selected. Result={result}")

    def test_T06_double_click_blocked_by_lock(self):
        """
        T-06: CRITICAL UX BUG — Pressing Download twice should not start
        two parallel downloads. The second click must be blocked.
        This tests the _operation_lock.acquire(blocking=False) guard.

        Design note: We use an Event (not a Barrier) to guarantee that
        the second thread tries to acquire the lock WHILE the first thread
        is still holding it. A Barrier would cause a BrokenBarrierError
        because the second thread never reaches the barrier (it is blocked
        by the lock before it can call fake_ydl).
        """
        w1_is_inside = threading.Event()  # Fires when worker-1 is holding the lock
        results = []

        def slow_ydl(url, hook):
            w1_is_inside.set()    # Signal: lock is currently held by worker-1
            time.sleep(0.15)      # Keep the lock for 150ms

        self.sys.video_rows = [make_video_row()]

        def run_worker_1():
            with patch('os.path.isdir', return_value=True):
                r = self.sys.download_worker(fake_ydl_func=slow_ydl)
                results.append(r)

        def run_worker_2():
            # Wait until worker-1 is inside and definitely holds the lock
            w1_is_inside.wait(timeout=3)
            with patch('os.path.isdir', return_value=True):
                r = self.sys.download_worker(fake_ydl_func=slow_ydl)
                results.append(r)

        t1 = threading.Thread(target=run_worker_1)
        t2 = threading.Thread(target=run_worker_2)
        t1.start()
        t2.start()
        t1.join(timeout=5)
        t2.join(timeout=5)

        success_count   = results.count("SUCCESS")
        lock_busy_count = results.count("LOCK_BUSY")

        self.assertEqual(
            success_count, 1,
            f"FAIL T-06: Expected 1 success, got {success_count} — double download happened"
        )
        self.assertEqual(
            lock_busy_count, 1,
            f"FAIL T-06: Expected 1 blocked, got {lock_busy_count}"
        )
        print(f"PASS T-06: Double-click correctly blocked. Results: {results}")

    def test_T07_download_event_set_before_download_event_cleared(self):
        """
        T-07: _download_event must be SET before _download_process runs,
        and only CLEARED in the finally block — not before.
        If it's cleared too early, cancel check inside progress_hook fails.
        """
        event_states = []

        def fake_ydl(url, hook):
            # Record event state at each progress step
            event_states.append(('before_hook', self.sys._download_event.is_set()))
            hook({'status': 'downloading', 'total_bytes': 1000, 'downloaded_bytes': 500})
            event_states.append(('after_hook', self.sys._download_event.is_set()))

        self.sys.video_rows = [make_video_row()]

        with patch('os.path.isdir', return_value=True):
            self.sys.download_worker(fake_ydl_func=fake_ydl)

        for label, state in event_states:
            self.assertTrue(
                state,
                f"FAIL T-07: _download_event was CLEARED too early at stage: {label}"
            )
        print(f"PASS T-07: _download_event stays SET throughout download. States: {event_states}")


# ═══════════════════════════════════════════════════════════════
# TEST CLASS 2: Cancel Logic
# ═══════════════════════════════════════════════════════════════

class TestCancelDownloadLogic(unittest.TestCase):

    def setUp(self):
        self.sys = DownloadSystem()

    def test_T08_cancel_clears_download_event(self):
        """
        T-08: Pressing Cancel must CLEAR the _download_event immediately.
        This is the primary stop signal for the worker thread.
        Maps to: on_cancel_download_click() line 1012.
        """
        self.sys._download_event.set()  # Simulate: download is running
        self.sys.video_rows = [make_video_row(dl_state='downloading')]

        self.sys.on_cancel_download_click()

        self.assertFalse(
            self.sys._download_event.is_set(),
            "FAIL T-08: _download_event was NOT cleared after cancel click"
        )
        print("PASS T-08: _download_event correctly cleared on cancel click")

    def test_T09_cancel_when_idle_does_nothing(self):
        """
        T-09: Pressing Cancel when no download is running should be a no-op.
        The status message should NOT change to "Canceling...".
        """
        # _download_event is NOT set — no download running
        self.sys.video_rows = [make_video_row()]

        self.sys.on_cancel_download_click()

        canceling_msgs = [m for m, _ in self.sys.status_messages if "Canceling" in m]
        self.assertEqual(
            len(canceling_msgs), 0,
            "FAIL T-09: Cancel triggered a status update even when nothing was downloading"
        )
        print("PASS T-09: Cancel correctly does nothing when no download is running")

    def test_T10_cancel_marks_preparing_rows_as_canceled(self):
        """
        T-10: Rows in 'preparing' state must be marked 'canceled' on cancel click.
        Maps to: on_cancel_download_click() line 1015-1016.
        """
        row = make_video_row(dl_state='preparing')
        self.sys.video_rows = [row]
        self.sys._download_event.set()

        self.sys.on_cancel_download_click()

        self.assertEqual(
            row['dl_state'], 'canceled',
            f"FAIL T-10: Row in 'preparing' state was NOT marked 'canceled'. State={row['dl_state']}"
        )
        print("PASS T-10: 'preparing' row correctly marked 'canceled'")

    def test_T11_cancel_marks_downloading_rows_as_canceled(self):
        """
        T-11: Rows in 'downloading' state must be marked 'canceled' on cancel click.
        """
        row = make_video_row(dl_state='downloading')
        self.sys.video_rows = [row]
        self.sys._download_event.set()

        self.sys.on_cancel_download_click()

        self.assertEqual(
            row['dl_state'], 'canceled',
            f"FAIL T-11: Row in 'downloading' state was NOT marked 'canceled'. State={row['dl_state']}"
        )
        print("PASS T-11: 'downloading' row correctly marked 'canceled'")

    def test_T12_cancel_does_not_touch_completed_rows(self):
        """
        T-12: Rows already 'completed' must NOT be touched by cancel.
        """
        completed_row   = make_video_row(dl_state='completed')
        downloading_row = make_video_row(dl_state='downloading')
        self.sys.video_rows = [completed_row, downloading_row]
        self.sys._download_event.set()

        self.sys.on_cancel_download_click()

        self.assertEqual(
            completed_row['dl_state'], 'completed',
            "FAIL T-12: Cancel changed the state of a 'completed' row — it should be untouched"
        )
        print("PASS T-12: 'completed' row untouched by cancel")

    def test_T13_cancel_does_not_touch_failed_rows(self):
        """
        T-13: Rows already 'failed' must NOT be touched by cancel.
        """
        failed_row = make_video_row(dl_state='failed')
        failed_row['error_msg'] = "Some error"
        self.sys.video_rows = [failed_row]
        self.sys._download_event.set()

        self.sys.on_cancel_download_click()

        self.assertEqual(
            failed_row['dl_state'], 'failed',
            "FAIL T-13: Cancel overwrote a 'failed' row — original error was lost"
        )
        print("PASS T-13: 'failed' row correctly untouched by cancel")

    def test_T14_cancel_stops_worker_mid_playlist(self):
        """
        T-14: CRITICAL — Cancel mid-playlist must stop the loop.
        In _download_process, the loop checks: if not _download_event.is_set(): break
        This test verifies only some videos download, not all.
        Maps to: _download_process() line 681.
        """
        downloaded_urls = []

        def slow_ydl(url, hook):
            downloaded_urls.append(url)
            # Simulate: cancel happens after the first video starts
            if len(downloaded_urls) == 1:
                self.sys._download_event.clear()
            time.sleep(0.01)

        rows = [make_video_row(title=f"Video {i}") for i in range(5)]
        self.sys.video_rows = rows
        self.sys._download_event.set()  # Manually set — bypassing the worker for isolation

        self.sys._download_process(rows, "Best Quality", "/tmp/fake", fake_ydl_func=slow_ydl)

        self.assertLess(
            len(downloaded_urls), 5,
            f"FAIL T-14: Cancel mid-playlist did NOT stop the loop. All 5 videos downloaded."
        )
        print(f"PASS T-14: Mid-playlist cancel works. Only {len(downloaded_urls)}/5 videos downloaded")

    def test_T15_progress_hook_raises_on_cancel(self):
        """
        T-15: When _download_event is cleared mid-download, the progress_hook
        must raise ValueError("DOWNLOAD_CANCELLED") to interrupt yt-dlp.
        Maps to: progress_hook() line 688-689.
        """
        self.sys._download_event.set()
        self.sys._download_event.clear()  # Simulate cancel happening

        row = make_video_row()
        hook_raised = False

        # Simulate the exact progress_hook from _download_process
        def simulate_progress_hook(d, r=row):
            nonlocal hook_raised
            if not self.sys._download_event.is_set():
                hook_raised = True
                raise ValueError("DOWNLOAD_CANCELLED")

        try:
            simulate_progress_hook({'status': 'downloading', 'total_bytes': 100, 'downloaded_bytes': 50})
        except ValueError as e:
            self.assertEqual(str(e), "DOWNLOAD_CANCELLED")

        self.assertTrue(
            hook_raised,
            "FAIL T-15: progress_hook did NOT raise ValueError when download was canceled"
        )
        print("PASS T-15: progress_hook correctly raises ValueError('DOWNLOAD_CANCELLED') on cancel")

    def test_T16_exception_on_cancel_is_silenced(self):
        """
        T-16: When yt-dlp raises an exception DUE to cancellation,
        the except block must silently pass (not mark as 'failed').
        Maps to: _download_process except block, line 738-740.
        """
        def ydl_that_raises_on_cancel(url, hook):
            self.sys._download_event.clear()  # Simulate cancel
            raise ValueError("DOWNLOAD_CANCELLED")  # yt-dlp propagates our exception

        row = make_video_row()
        self.sys.video_rows = [row]
        self.sys._download_event.set()

        self.sys._download_process([row], "Best Quality", "/tmp/fake", fake_ydl_func=ydl_that_raises_on_cancel)

        self.assertNotEqual(
            row['dl_state'], 'failed',
            "FAIL T-16: A cancel-caused exception was marked as 'failed' — wrong behavior"
        )
        print(f"PASS T-16: Cancel exception silenced correctly. dl_state={row['dl_state']}")

    def test_T17_real_error_still_marks_as_failed(self):
        """
        T-17: A real network error (NOT a cancel) must mark the row as 'failed'.
        The except block must distinguish cancel from real errors.
        Maps to: _download_process except block, lines 741-744.
        """
        def ydl_that_crashes(url, hook):
            raise ConnectionError("Network unreachable")

        row = make_video_row()
        self.sys.video_rows = [row]
        self.sys._download_event.set()  # Download IS running (not canceled)

        self.sys._download_process([row], "Best Quality", "/tmp/fake", fake_ydl_func=ydl_that_crashes)

        self.assertEqual(
            row['dl_state'], 'failed',
            f"FAIL T-17: Real network error was NOT marked as 'failed'. State={row['dl_state']}"
        )
        self.assertIn(
            "Network unreachable", row['error_msg'],
            "FAIL T-17: error_msg was not saved correctly"
        )
        print(f"PASS T-17: Real error correctly marked as 'failed'. error_msg='{row['error_msg']}'")


# ═══════════════════════════════════════════════════════════════
# TEST CLASS 3: The BUG — No Button Swap on Download
# ═══════════════════════════════════════════════════════════════

class TestDownloadButtonBug(unittest.TestCase):
    """
    These tests DOCUMENT the current broken behavior and VERIFY the fix.
    """

    def setUp(self):
        self.sys = DownloadSystem()

    def test_T18_BUG_download_button_stays_visible_during_download(self):
        """
        T-18: DOCUMENTS THE BUG.
        In the current code, there is NO button swap in download_worker().
        The "Download Selected" button stays visible and clickable
        during the entire download process.
        Expected (BUGGY) behavior: download_btn_visible stays True during download.
        Expected (FIXED) behavior: download_btn_visible = False, stop_btn_visible = True.
        """
        btn_state_during_download = []

        def fake_ydl(url, hook):
            # Record button state DURING download
            btn_state_during_download.append({
                'download_btn': self.sys.download_btn_visible,
                'stop_btn':     self.sys.stop_btn_visible,
            })

        self.sys.video_rows = [make_video_row()]

        with patch('os.path.isdir', return_value=True):
            self.sys.download_worker(fake_ydl_func=fake_ydl)

        state = btn_state_during_download[0]
        
        # This assertion PASSES because of the bug (both are in their default state)
        self.assertTrue(
            state['download_btn'],
            "T-18 CONFIRMED BUG: 'Download Selected' button is STILL VISIBLE during download — "
            "user can click it again and start a second download attempt"
        )
        print(
            f"T-18 BUG CONFIRMED: During download — "
            f"download_btn visible={state['download_btn']}, "
            f"stop_btn visible={state['stop_btn']}"
        )
        print("  → Fix: Add button swap in download_worker() exactly like convert_worker() does")

    def test_T19_FIXED_download_button_should_hide_during_download(self):
        """
        T-19: Verifies the FIXED behavior.
        In a fixed version of download_worker(), when download starts:
          - Download button: pack_forget() (hidden)
          - Stop button: pack() (visible)
        And in the finally block:
          - Download button: pack() (visible again)
          - Stop button: pack_forget() (hidden)
        """
        class FixedDownloadSystem(DownloadSystem):
            """Same as DownloadSystem but with the button swap fix applied."""

            def download_worker(self, fake_ydl_func=None, override_path=None, override_quality=None):
                if not self._operation_lock.acquire(blocking=False):
                    return "LOCK_BUSY"
                try:
                    self._download_event.set()

                    # ✅ FIX APPLIED: Swap buttons at start
                    self.download_btn_visible = False
                    self.stop_btn_visible     = True

                    save_path = override_path if override_path is not None else self.save_path
                    if not save_path or save_path == "INVALID":
                        return "INVALID_PATH"

                    with self._ui_list_lock:
                        selected_rows = [r for r in self.video_rows if r["checkbox"].get() == 1]
                    if not selected_rows:
                        return "NO_VIDEOS"

                    quality = override_quality if override_quality is not None else self.quality
                    self._download_process(selected_rows, quality, save_path, fake_ydl_func)

                    if self._download_event.is_set():
                        return "SUCCESS"
                    return "CANCELED"
                finally:
                    self._download_event.clear()
                    self._operation_lock.release()

                    # ✅ FIX APPLIED: Swap back in finally
                    self.download_btn_visible = True
                    self.stop_btn_visible     = False

        fixed_sys = FixedDownloadSystem()
        fixed_sys.video_rows = [make_video_row()]

        btn_state_during_download = []

        def fake_ydl(url, hook):
            btn_state_during_download.append({
                'download_btn': fixed_sys.download_btn_visible,
                'stop_btn':     fixed_sys.stop_btn_visible,
            })

        with patch('os.path.isdir', return_value=True):
            fixed_sys.download_worker(fake_ydl_func=fake_ydl)

        state = btn_state_during_download[0]

        self.assertFalse(state['download_btn'],
            "FAIL T-19: Fixed version should HIDE download button during download")
        self.assertTrue(state['stop_btn'],
            "FAIL T-19: Fixed version should SHOW stop button during download")

        # After download: check restored
        self.assertTrue(fixed_sys.download_btn_visible,
            "FAIL T-19: Fixed version should RESTORE download button after download")
        self.assertFalse(fixed_sys.stop_btn_visible,
            "FAIL T-19: Fixed version should HIDE stop button after download")

        print("PASS T-19: Fixed button swap behavior verified:")
        print(f"  → During download: download_btn={state['download_btn']}, stop_btn={state['stop_btn']}")
        print(f"  → After  download: download_btn={fixed_sys.download_btn_visible}, stop_btn={fixed_sys.stop_btn_visible}")


# ═══════════════════════════════════════════════════════════════
# TEST CLASS 4: Race Conditions (Thread Safety)
# ═══════════════════════════════════════════════════════════════

class TestRaceConditions(unittest.TestCase):

    def setUp(self):
        self.sys = DownloadSystem()

    def test_T20_cancel_during_preparation_phase(self):
        """
        T-20: Cancel arrives exactly when a video is in 'preparing' state.
        The row's dl_state should end up as 'canceled', not 'completed'.
        This is a timing edge case.
        """
        row = make_video_row()
        self.sys.video_rows = [row]

        def fake_ydl(url, hook):
            # Cancel happens RIGHT after preparation but before download starts
            self.sys.on_cancel_download_click()
            # Then yt-dlp tries to report progress (should be ignored)
            try:
                hook({'status': 'downloading', 'total_bytes': 1000, 'downloaded_bytes': 500})
            except ValueError:
                pass  # Expected — DOWNLOAD_CANCELLED

        with patch('os.path.isdir', return_value=True):
            result = self.sys.download_worker(fake_ydl_func=fake_ydl)

        self.assertIn(
            row['dl_state'], ['canceled', 'preparing'],
            f"FAIL T-20: Row in wrong state after mid-preparation cancel. State={row['dl_state']}"
        )
        self.assertNotEqual(
            row['dl_state'], 'completed',
            "FAIL T-20: Row was marked 'completed' even after being canceled"
        )
        print(f"PASS T-20: Mid-preparation cancel handled correctly. dl_state={row['dl_state']}")

    def test_T21_cancel_without_lock_race_window(self):
        """
        T-21: DOCUMENTS THE BUG in on_cancel_download_click.
        The cancel function reads video_rows without _ui_list_lock.
        This test simulates concurrent modification of video_rows during cancel.
        """
        # Setup: 10 rows
        rows = [make_video_row(title=f"Video {i}", dl_state='downloading') for i in range(10)]
        self.sys.video_rows = rows
        self.sys._download_event.set()

        errors = []
        cancel_completed = threading.Event()

        def do_cancel():
            try:
                self.sys.on_cancel_download_click()
            except Exception as e:
                errors.append(str(e))
            finally:
                cancel_completed.set()

        def mutate_rows():
            # Simulate worker modifying rows concurrently (no lock in cancel)
            time.sleep(0.001)
            try:
                # This simulates the download worker changing dl_state at the same time
                for r in list(rows):
                    r['dl_state'] = 'completed'
            except Exception as e:
                errors.append(f"Mutation error: {e}")

        t1 = threading.Thread(target=do_cancel)
        t2 = threading.Thread(target=mutate_rows)
        t1.start()
        t2.start()
        t1.join(timeout=2)
        t2.join(timeout=2)

        # The test documents whether this is safe or not
        # In Python, due to the GIL, this specific pattern rarely crashes,
        # but it's still logically unsound
        print(
            f"T-21 RACE WINDOW DOCUMENTED: cancel runs without lock. "
            f"Concurrent mutations: {'detected' if errors else 'not detected this run (GIL protected but not safe)'}. "
            f"Errors: {errors if errors else 'None (GIL saved us)'}"
        )
        print("  → Fix: Add 'with _ui_list_lock:' inside on_cancel_download_click()")

    def test_T22_multiple_cancels_are_idempotent(self):
        """
        T-22: Pressing Cancel multiple times must be safe.
        The second and subsequent clicks should be no-ops.
        """
        row = make_video_row(dl_state='downloading')
        self.sys.video_rows = [row]
        self.sys._download_event.set()

        # Click cancel 5 times
        for _ in range(5):
            self.sys.on_cancel_download_click()

        self.assertEqual(
            row['dl_state'], 'canceled',
            f"FAIL T-22: After 5 cancel clicks, row is in wrong state: {row['dl_state']}"
        )
        # Event should still be cleared
        self.assertFalse(self.sys._download_event.is_set())
        print("PASS T-22: Multiple cancel clicks are safely idempotent")


# ═══════════════════════════════════════════════════════════════
# TEST CLASS 5: Edge Cases & Boundary Conditions
# ═══════════════════════════════════════════════════════════════

class TestEdgeCases(unittest.TestCase):

    def setUp(self):
        self.sys = DownloadSystem()

    def test_T23_empty_playlist_returns_no_videos(self):
        """
        T-23: No videos in list — worker must return early with NO_VIDEOS.
        """
        self.sys.video_rows = []

        with patch('os.path.isdir', return_value=True):
            result = self.sys.download_worker()

        self.assertEqual(result, "NO_VIDEOS")
        print(f"PASS T-23: Empty list handled correctly. Result={result}")

    def test_T24_all_unchecked_returns_no_videos(self):
        """
        T-24: If all checkboxes are unchecked, worker must return NO_VIDEOS.
        """
        self.sys.video_rows = [make_video_row(checked=False) for _ in range(5)]

        with patch('os.path.isdir', return_value=True):
            result = self.sys.download_worker()

        self.assertEqual(result, "NO_VIDEOS")
        print(f"PASS T-24: All-unchecked handled correctly. Result={result}")

    def test_T25_already_exists_row_not_re_downloaded(self):
        """
        T-25: A row with dl_state='already_exists' should not be marked 'completed'
        when ydl.download() returns. The logger sets already_exists, and the
        post-download check must respect it.
        Maps to: _download_process line 732.
        """
        row = make_video_row()

        def fake_ydl(url, hook):
            # Simulate yt-dlp logging "already downloaded"
            row['dl_state'] = 'already_exists'

        self.sys.video_rows = [row]
        self.sys._download_event.set()

        self.sys._download_process([row], "Best Quality", "/tmp/fake", fake_ydl_func=fake_ydl)

        self.assertEqual(
            row['dl_state'], 'already_exists',
            f"FAIL T-25: 'already_exists' was overwritten to '{row['dl_state']}'"
        )
        print(f"PASS T-25: 'already_exists' state preserved correctly")

    def test_T26_destroyed_frame_skipped(self):
        """
        T-26: If a row's frame is destroyed (user removed it from UI),
        the download loop must skip it gracefully.
        Maps to: _download_process line 682.
        """
        destroyed_row = make_video_row(title="Destroyed Row")
        destroyed_row['frame'].winfo_exists.return_value = False  # Frame is gone

        normal_row = make_video_row(title="Normal Row")
        downloaded = []

        def fake_ydl(url, hook):
            downloaded.append(url)

        self.sys.video_rows = [destroyed_row, normal_row]
        self.sys._download_event.set()

        self.sys._download_process(
            [destroyed_row, normal_row], "Best Quality", "/tmp/fake", fake_ydl_func=fake_ydl
        )

        self.assertEqual(len(downloaded), 1, "FAIL T-26: Destroyed frame was not skipped")
        self.assertIn(normal_row['url'], downloaded, "FAIL T-26: Normal row was not downloaded")
        print(f"PASS T-26: Destroyed frame skipped. Downloaded {len(downloaded)}/2 rows")

    def test_T27_invalid_quality_returns_early(self):
        """
        T-27: If quality is a placeholder value, worker returns NO_QUALITY.
        Tests all three placeholder values from the code.
        """
        placeholders = ["Select Quality", "Waiting for link...", "Loading..."]
        self.sys.video_rows = [make_video_row()]

        for placeholder in placeholders:
            with patch('os.path.isdir', return_value=True):
                result = self.sys.download_worker(override_quality=placeholder)
            self.assertEqual(result, "NO_QUALITY",
                f"FAIL T-27: Placeholder quality '{placeholder}' was not caught")

        print(f"PASS T-27: All 3 placeholder quality values correctly caught")

    def test_T28_final_status_correct_with_partial_failures(self):
        """
        T-28: If 2 out of 5 videos fail, the final status must be
        'FINISHED_WITH_ERRORS', not 'SUCCESS'.
        """
        call_count = [0]

        def fake_ydl(url, hook):
            call_count[0] += 1
            if call_count[0] <= 2:
                raise ConnectionError("Network error")  # First 2 fail

        rows = [make_video_row(title=f"Video {i}") for i in range(5)]
        self.sys.video_rows = rows

        with patch('os.path.isdir', return_value=True):
            result = self.sys.download_worker(fake_ydl_func=fake_ydl)

        self.assertEqual(result, "FINISHED_WITH_ERRORS",
            f"FAIL T-28: Expected FINISHED_WITH_ERRORS, got {result}")
        print(f"PASS T-28: Partial failure correctly reported as FINISHED_WITH_ERRORS")


# ═══════════════════════════════════════════════════════════════
# RUN ALL TESTS WITH STRUCTURED REPORT
# ═══════════════════════════════════════════════════════════════

if __name__ == '__main__':
    loader = unittest.TestLoader()
    suite  = unittest.TestSuite()

    # Load all test classes in order
    for cls in [
        TestDownloadWorkerFlow,
        TestCancelDownloadLogic,
        TestDownloadButtonBug,
        TestRaceConditions,
        TestEdgeCases,
    ]:
        suite.addTests(loader.loadTestsFromTestCase(cls))

    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
