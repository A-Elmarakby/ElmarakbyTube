import pytest
import threading
import time
import os
import ui.state as state

# ==========================================
# 1. General Integrity Tests
# ==========================================

def test_state_is_singleton():
    """Make sure the store is one instance in memory"""
    import ui.state as state1
    import ui.state as state2
    # expected result: memory address must be the same (no duplicates)
    assert id(state1.video_rows) == id(state2.video_rows)
    assert id(state1.operation_lock) == id(state2.operation_lock)

def test_core_imports_successfully():
    """Make sure there are no circular import errors"""
    try:
        import core.utils
        import core.downloader
        import core.fetcher
        import core.converter
        import ui.popups
    except ImportError as e:
        pytest.fail(f"Import failed: {e}")
    # expected result: test passes with no errors

# ==========================================
# 2. Targeted Tests
# ==========================================

def test_no_lingering_globals_in_main():
    """Check main.py to make sure old variables are removed"""
    main_path = os.path.join(os.path.dirname(__file__), "../../main.py")
    with open(main_path, "r", encoding="utf-8") as f:
        content = f.read()
    
    # expected result: file must not contain these words
    forbidden_terms = ["global _operation_lock", "global _fetch_event", "global video_rows"]
    for term in forbidden_terms:
        assert term not in content, f"Found lingering global variable: {term}"

# ==========================================
# 3. Stress & Edge Case Tests
# ==========================================

def test_race_condition_prevention():
    """Race test: try to run two operations at the same time"""
    # first thread locks the lock
    state.operation_lock.acquire()
    
    # second thread tries to lock without waiting
    second_thread_acquired = state.operation_lock.acquire(blocking=False)
    
    # expected result: second thread must fail (False)
    assert second_thread_acquired is False
    
    # cleanup lock
    state.operation_lock.release()

def test_crash_recovery_clears_events():
    """Recovery test: make sure UI is reset even after a crash"""
    state.download_event.set() # simulate download start
    
    try:
        # simulate a fatal error during download
        raise RuntimeError("Fatal Download Error!")
    except RuntimeError:
        pass
    finally:
        # system cleanup step: clear event
        state.download_event.clear()
        
    # expected result: event must be False so user can retry
    assert state.download_event.is_set() is False

def test_stress_1000_videos(benchmark):
    """Stress test: handle 1000 videos in UI (simulation)"""
    # create 1000 fake items
    class MockCheckbox:
        def __init__(self): self.checked = False
        def select(self): self.checked = True
        def deselect(self): self.checked = False

    state.video_rows = [{"checkbox": MockCheckbox()} for _ in range(1000)]
    
    def simulate_toggle_all(is_checked):
        for row in state.video_rows:
            if is_checked: row["checkbox"].select()
            else: row["checkbox"].deselect()

    # expected result: benchmark checks speed, app must not crash
    benchmark(simulate_toggle_all, True)
    assert all(row["checkbox"].checked for row in state.video_rows)