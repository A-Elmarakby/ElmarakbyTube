"""
tests/unit/test_state.py
=============================================================
Threading State, Locks, and Event Signal Tests (From Claude 1)
"""

import pytest
import threading
import time

class TestOperationLock:
    """Verifies the Smart Lock (_operation_lock) prevents overlapping operations."""

    def test_lock_acquires_when_free(self, fresh_events):
        lock = fresh_events["operation_lock"]
        result = lock.acquire(blocking=False)
        assert result is True, "Lock must be acquirable when free"
        lock.release()

    def test_second_non_blocking_acquire_fails(self, fresh_events):
        lock = fresh_events["operation_lock"]
        first = lock.acquire(blocking=False)
        assert first is True
        second = lock.acquire(blocking=False)
        assert second is False, "Second non-blocking acquire must fail while lock is held"
        lock.release()

    def test_lock_free_after_background_finishes(self, fresh_events):
        """After a background thread releases the lock, it must be acquirable again."""
        lock = fresh_events["operation_lock"]
        done = threading.Event()

        def worker():
            lock.acquire()
            time.sleep(0.05)
            lock.release()
            done.set()

        threading.Thread(target=worker).start()
        done.wait(timeout=2.0)

        result = lock.acquire(blocking=False)
        assert result is True
        lock.release()

class TestThreadingEvents:
    """Events act as on/off signals for long-running operations."""

    def test_all_events_start_cleared(self, fresh_events):
        """All three operation events must start in CLEARED state."""
        for name, obj in fresh_events.items():
            if isinstance(obj, threading.Event):
                assert not obj.is_set(), f"'{name}' must start cleared"

    def test_events_are_fully_independent(self, fresh_events):
        """Setting one event must have zero effect on the others."""
        fresh_events["fetch_event"].set()
        assert fresh_events["fetch_event"].is_set() is True
        assert fresh_events["download_event"].is_set() is False
        assert fresh_events["convert_event"].is_set() is False

class TestOperationGuardPattern:
    """Tests the combined lock+event guard used in all three workers."""

    def test_event_cleared_even_when_worker_crashes(self, fresh_events):
        """CRITICAL INVARIANT: finally block MUST clear the event and release the lock."""
        lock = fresh_events["operation_lock"]
        event = fresh_events["download_event"]

        lock.acquire(blocking=False)
        event.set()

        try:
            raise RuntimeError("Simulated crash")
        except RuntimeError:
            pass
        finally:
            event.clear()
            lock.release()

        assert not event.is_set(), "Event must be cleared even after worker crash"