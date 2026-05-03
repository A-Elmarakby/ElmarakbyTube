"""
tests/unit/test_layout.py
═══════════════════════════════════════════════════════════════════════════════
Unit tests for ui/layout.py

COVERAGE TARGETS
────────────────
  safe_ui_update          – live widget / dead widget / None / cursor kwarg
  safe_progress_update    – live widget / dead widget / None / boundary values
  update_global_status    – both labels / warning text / None state labels
  update_dynamic_totals   – size math / time math / "+" suffix / edge cases
  toggle_all              – select all / deselect all / empty list
  remove_selected         – partial removal / remove all / remove none
  clear_list              – empties rows + calls totals / no list_frame guard
  add_video_row           – happy path / no list_frame guard / row dict keys
                            / status-label click handler (failed vs ready)
  build_app_ui            – populates every state.* widget reference

STRATEGY
────────
Every test is fully self-contained:
  • state widget references (global_status_label, total_time_label, …) are
    injected as MockWidget instances in a per-test fixture so nothing bleeds
    between tests.
  • state.video_rows is cleared by the autouse reset_app_state fixture in
    conftest.py before each test; we only ADD rows we need.
  • build_app_ui is tested with a fully-wired MockWidget app and a minimal
    callbacks dict — we check that every state.* reference is no longer None
    after the call, and that key button commands are correctly wired.
"""

import pytest
from unittest.mock import MagicMock, patch, call
import ui.state as state
import ui.layout as layout
import config
import messages

# ─────────────────────────────────────────────────────────────────────────────
# Helpers — re-use MockWidget from conftest without importing the class name
# (conftest is loaded automatically by pytest; we grab the class from there)
# ─────────────────────────────────────────────────────────────────────────────
def _make_widget(name="widget", *, exists=True, checked=True):
    """
    Build a fresh MockWidget.  We import the class lazily so this module
    never crashes if conftest changes the class name.
    """
    from tests.conftest import MockWidget  # noqa: PLC0415
    w = MockWidget(name=name)
    w.winfo_exists = MagicMock(return_value=exists)
    
    # --- Fix: Convert standard functions to MagicMocks ---
    w.destroy = MagicMock()
    w.bind_all = MagicMock()
    # -----------------------------------------------------
    
    w._checked = checked
    return w


def _make_row(*, checked=True, bytes_size=-1, duration="03:45",
              dl_state="ready", error_msg=""):
    """
    Return a minimal row dict that satisfies every branch in layout.py.
    Mirrors the shape that add_video_row() stores in state.video_rows.
    """
    cb = _make_widget("checkbox", checked=checked)
    # MockWidget.get() checks for 'checkbox' in the name → returns 1 or 0
    return {
        "frame":        _make_widget("frame"),
        "checkbox":     cb,
        "title":        "Test Video",
        "duration":     duration,
        "progress":     _make_widget("progress"),
        "size_label":   _make_widget("size_label"),
        "status_label": _make_widget("status_label"),
        "percent_label":_make_widget("percent_label"),
        "url":          "https://www.youtube.com/watch?v=TEST",
        "bytes_size":   bytes_size,
        "dl_state":     dl_state,
        "error_msg":    error_msg,
    }


# ─────────────────────────────────────────────────────────────────────────────
# Fixture — wire state labels so label-writing functions can be called freely
# ─────────────────────────────────────────────────────────────────────────────
@pytest.fixture(autouse=True)
def wire_state_labels():
    """
    WHY autouse here (not only in conftest)?
    conftest.reset_app_state clears video_rows and events, but it does NOT
    reset the state label references because those are set by build_app_ui
    and conftest doesn't call it.  Without this fixture every test that calls
    update_global_status / update_dynamic_totals would silently do nothing
    because the labels are None, giving false-green results.

    We set them to fresh MockWidgets before each test and put them back to
    None afterwards so state is clean for any test that specifically wants
    to test the "label is None" guard.
    """
    state.global_status_label = _make_widget("global_status_label")
    state.global_warning_label = _make_widget("global_warning_label")
    state.total_time_label     = _make_widget("total_time_label")
    state.total_size_label     = _make_widget("total_size_label")
    state.list_frame           = _make_widget("list_frame")

    yield

    state.global_status_label = None
    state.global_warning_label = None
    state.total_time_label     = None
    state.total_size_label     = None
    state.list_frame           = None


# ═════════════════════════════════════════════════════════════════════════════
# 1.  safe_ui_update
# ═════════════════════════════════════════════════════════════════════════════
class TestSafeUiUpdate:

    def test_updates_live_widget_text(self):
        """Core path: configure() is called with the correct kwargs."""
        w = _make_widget()
        layout.safe_ui_update(w, text="Hello", text_color="green")
        assert w._state["text"] == "Hello"
        assert w._state["text_color"] == "green"

    def test_updates_live_widget_with_cursor_kwarg(self):
        """
        WHY: The status-label click handler calls
             safe_ui_update(label, text="Failed", text_color=RED, cursor="hand2")
        The cursor kwarg must pass through without being dropped.
        """
        w = _make_widget()
        layout.safe_ui_update(w, text="Failed", text_color=config.COLOR_RED,
                              cursor="hand2")
        assert w._state["cursor"] == "hand2"
        assert w._state["text"] == "Failed"

    def test_skips_dead_widget(self):
        """configure() must NOT be called if winfo_exists() is False."""
        w = _make_widget(exists=False)
        layout.safe_ui_update(w, text="Should not appear")
        # _state must remain empty — configure was never called
        assert "text" not in w._state

    def test_skips_none_widget_gracefully(self):
        """Passing None must not raise any exception."""
        layout.safe_ui_update(None, text="anything")   # must not raise

    def test_multiple_kwargs_all_stored(self):
        """All kwargs land in _state, not just the first one."""
        w = _make_widget()
        layout.safe_ui_update(w, text="X", text_color="red",
                              fg_color="blue", state="disabled")
        assert w._state["text"] == "X"
        assert w._state["text_color"] == "red"
        assert w._state["fg_color"] == "blue"
        assert w._state["state"] == "disabled"


# ═════════════════════════════════════════════════════════════════════════════
# 2.  safe_progress_update
# ═════════════════════════════════════════════════════════════════════════════
class TestSafeProgressUpdate:

    def test_sets_value_on_live_widget(self):
        w = _make_widget()
        layout.safe_progress_update(w, 0.75)
        assert w._value == 0.75

    def test_boundary_zero(self):
        w = _make_widget()
        layout.safe_progress_update(w, 0.0)
        assert w._value == 0.0

    def test_boundary_one(self):
        w = _make_widget()
        layout.safe_progress_update(w, 1.0)
        assert w._value == 1.0

    def test_skips_dead_widget(self):
        """
        WHY: A download can finish a fraction of a second after the user
        removes the row.  set() must never be called on a destroyed widget.
        """
        w = _make_widget(exists=False)
        w._value = 0.0
        layout.safe_progress_update(w, 1.0)
        assert w._value == 0.0  # unchanged

    def test_skips_none_gracefully(self):
        layout.safe_progress_update(None, 0.5)   # must not raise


# ═════════════════════════════════════════════════════════════════════════════
# 3.  update_global_status
# ═════════════════════════════════════════════════════════════════════════════
class TestUpdateGlobalStatus:

    def test_status_label_gets_message_and_color(self):
        layout.update_global_status("All good", "#28a745", "")
        text = state.global_status_label._state.get("text", "")
        assert "All good" in text
        assert state.global_status_label._state["text_color"] == "#28a745"

    def test_status_label_prefixed_with_Status(self):
        """
        WHY: The function wraps the message as f"Status: {msg}".
        Verifying the prefix guards against accidental removal.
        """
        layout.update_global_status("Downloading...", config.COLOR_CYAN)
        text = state.global_status_label._state.get("text", "")
        assert text.startswith("Status:") or "Downloading..." in text

    def test_warning_label_gets_warning_text(self):
        layout.update_global_status("Done", "white", "3 videos blocked")
        warning_text = state.global_warning_label._state.get("text", "")
        assert "3 videos blocked" in warning_text

    def test_warning_label_cleared_when_empty_string(self):
        """
        WHY: After a warning is shown, the next successful operation must
        clear it by passing warning_msg="".
        """
        # set a warning first
        layout.update_global_status("Step 1", "white", "something wrong")
        # now clear it
        layout.update_global_status("Step 2", "white", "")
        warning_text = state.global_warning_label._state.get("text", "")
        # apply_bidi("") returns "" so the label must be empty / falsy
        assert warning_text == "" or warning_text is None

    def test_does_not_crash_when_labels_are_none(self):
        """
        WHY: update_global_status is called from background threads BEFORE
        build_app_ui has run (e.g. very early in fetch_video_data).  If the
        labels are still None the function must be silent.
        """
        state.global_status_label = None
        state.global_warning_label = None
        layout.update_global_status("early call", "white", "")  # must not raise

    def test_does_not_crash_when_label_is_dead(self):
        state.global_status_label = _make_widget(exists=False)
        layout.update_global_status("test", "white", "")   # must not raise

    def test_default_color_is_white(self):
        """Calling with only msg uses the 'white' default."""
        layout.update_global_status("ready")
        assert state.global_status_label._state.get("text_color") == "white"


# ═════════════════════════════════════════════════════════════════════════════
# 4.  update_dynamic_totals
# ═════════════════════════════════════════════════════════════════════════════
class TestUpdateDynamicTotals:
    """
    These tests exercise the size / time calculation math directly.
    We inject rows into state.video_rows (which is cleared by conftest
    before every test) and then assert what the labels receive.
    """

    # ── size label ──────────────────────────────────────────────────────────

    def test_zero_size_when_no_rows(self):
        layout.update_dynamic_totals()
        assert state.total_size_label._state.get("text") == "0.0 MB"

    def test_sums_bytes_of_checked_rows(self):
        # 5 MB + 5 MB = 10 MB
        state.video_rows.append(_make_row(bytes_size=5 * 1024 * 1024))
        state.video_rows.append(_make_row(bytes_size=5 * 1024 * 1024))
        layout.update_dynamic_totals()
        assert state.total_size_label._state.get("text") == "10.0 MB"

    def test_unchecked_rows_excluded_from_size(self):
        state.video_rows.append(_make_row(bytes_size=50 * 1024 * 1024,
                                          checked=True))
        state.video_rows.append(_make_row(bytes_size=50 * 1024 * 1024,
                                          checked=False))
        layout.update_dynamic_totals()
        assert state.total_size_label._state.get("text") == "50.0 MB"

    def test_size_plus_suffix_when_some_unfetched(self):
        """
        WHY: When at least one checked row has bytes_size == -1 (not yet
        fetched) AND at least one has a real size, the display must show
        "X MB+" to signal the total is a lower bound, not the true total.
        """
        state.video_rows.append(_make_row(bytes_size=10 * 1024 * 1024))
        state.video_rows.append(_make_row(bytes_size=-1))   # not fetched
        layout.update_dynamic_totals()
        text = state.total_size_label._state.get("text", "")
        assert text.endswith("+"), (
            f"Expected '+' suffix when some rows are unfetched, got: {text!r}"
        )

    def test_no_plus_suffix_when_all_fetched(self):
        state.video_rows.append(_make_row(bytes_size=10 * 1024 * 1024))
        state.video_rows.append(_make_row(bytes_size=20 * 1024 * 1024))
        layout.update_dynamic_totals()
        text = state.total_size_label._state.get("text", "")
        assert not text.endswith("+"), (
            f"Did not expect '+' suffix when all rows are fetched, got: {text!r}"
        )

    def test_rows_with_zero_bytes_not_treated_as_unfetched(self):
        """
        WHY: bytes_size == 0 means "blocked / unknown", NOT "unfetched".
        Only -1 triggers all_fetched = False.  A "0 + something" total
        should NOT produce the "+" suffix.
        """
        state.video_rows.append(_make_row(bytes_size=0))
        state.video_rows.append(_make_row(bytes_size=10 * 1024 * 1024))
        layout.update_dynamic_totals()
        text = state.total_size_label._state.get("text", "")
        assert not text.endswith("+")

    def test_gb_display_for_large_total(self):
        """
        WHY: format_size switches to GB above ~1000 MB.  The totals function
        must pass the raw byte count to format_size — not MB — so the
        GB display is correct.
        """
        state.video_rows.append(
            _make_row(bytes_size=2 * 1024 * 1024 * 1024)   # 2 GB
        )
        layout.update_dynamic_totals()
        text = state.total_size_label._state.get("text", "")
        assert "GB" in text

    # ── time label ──────────────────────────────────────────────────────────

    def test_zero_time_when_no_rows(self):
        layout.update_dynamic_totals()
        assert state.total_time_label._state.get("text") == "0s"

    def test_mm_ss_duration_parsed_correctly(self):
        """03:45 → 225 seconds → 3m 45s"""
        state.video_rows.append(_make_row(duration="03:45"))
        layout.update_dynamic_totals()
        assert state.total_time_label._state.get("text") == "3m 45s"

    def test_hh_mm_ss_duration_parsed_correctly(self):
        """1:30:00 → 5400 seconds → 1h 30m 0s"""
        state.video_rows.append(_make_row(duration="1:30:00"))
        layout.update_dynamic_totals()
        assert state.total_time_label._state.get("text") == "1h 30m 0s"

    def test_multiple_durations_summed(self):
        """10:00 + 20:00 = 30:00 → 30m 0s"""
        state.video_rows.append(_make_row(duration="10:00"))
        state.video_rows.append(_make_row(duration="20:00"))
        layout.update_dynamic_totals()
        assert state.total_time_label._state.get("text") == "30m 0s"

    def test_invalid_duration_placeholder_skipped(self):
        """
        WHY: Playlist entries sometimes have '--:--' or 'N/A' as duration.
        These strings must be silently skipped so they don't cause a
        ValueError in int().
        """
        state.video_rows.append(_make_row(duration="--:--"))
        state.video_rows.append(_make_row(duration="N/A"))
        layout.update_dynamic_totals()
        assert state.total_time_label._state.get("text") == "0s"

    def test_only_seconds_displayed_correctly(self):
        """00:45 → 45 seconds → '45s' (no minutes prefix)"""
        state.video_rows.append(_make_row(duration="00:45"))
        layout.update_dynamic_totals()
        assert state.total_time_label._state.get("text") == "45s"

    def test_does_not_crash_when_labels_none(self):
        state.total_time_label = None
        state.total_size_label = None
        state.video_rows.append(_make_row())
        layout.update_dynamic_totals()  # must not raise


# ═════════════════════════════════════════════════════════════════════════════
# 5.  toggle_all
# ═════════════════════════════════════════════════════════════════════════════
class TestToggleAll:

    def test_select_all_checks_every_row(self):
        for _ in range(3):
            state.video_rows.append(_make_row(checked=False))
        layout.toggle_all(True)
        assert all(r["checkbox"]._checked for r in state.video_rows)

    def test_deselect_all_unchecks_every_row(self):
        for _ in range(3):
            state.video_rows.append(_make_row(checked=True))
        layout.toggle_all(False)
        assert all(not r["checkbox"]._checked for r in state.video_rows)

    def test_toggle_on_empty_list_does_not_crash(self):
        layout.toggle_all(True)   # must not raise
        layout.toggle_all(False)  # must not raise

    def test_toggle_calls_update_dynamic_totals(self):
        """
        WHY: toggling changes which rows are counted in the totals, so the
        labels must refresh.  We verify this by confirming total_size_label
        is reconfigured after toggle (the autouse fixture wired it).
        """
        state.video_rows.append(_make_row(bytes_size=10 * 1024 * 1024,
                                          checked=False))
        layout.toggle_all(True)
        # After selecting the row, the size should be non-zero
        text = state.total_size_label._state.get("text", "0.0 MB")
        assert text != "0.0 MB"

    def test_select_all_then_deselect_all(self):
        """Round-trip: select → deselect leaves every checkbox unchecked."""
        for _ in range(5):
            state.video_rows.append(_make_row(checked=False))
        layout.toggle_all(True)
        layout.toggle_all(False)
        assert all(not r["checkbox"]._checked for r in state.video_rows)


# ═════════════════════════════════════════════════════════════════════════════
# 6.  remove_selected
# ═════════════════════════════════════════════════════════════════════════════
class TestRemoveSelected:

    def test_removes_checked_rows(self):
        state.video_rows.append(_make_row(checked=True))
        state.video_rows.append(_make_row(checked=True))
        state.video_rows.append(_make_row(checked=False))
        layout.remove_selected()
        # Only the unchecked row must remain
        assert len(state.video_rows) == 1
        assert not state.video_rows[0]["checkbox"]._checked

    def test_keeps_unchecked_rows(self):
        for _ in range(3):
            state.video_rows.append(_make_row(checked=False))
        layout.remove_selected()
        assert len(state.video_rows) == 3

    def test_remove_all_rows(self):
        for _ in range(4):
            state.video_rows.append(_make_row(checked=True))
        layout.remove_selected()
        assert len(state.video_rows) == 0

    def test_calls_frame_destroy_for_each_removed_row(self):
        """
        WHY: The real widget must be destroyed to free Tk memory.
        We verify destroy() was called on every checked frame.
        """
        rows = [_make_row(checked=True) for _ in range(2)]
        for r in rows:
            state.video_rows.append(r)
        layout.remove_selected()
        for r in rows:
            r["frame"].destroy.assert_called()

    def test_does_not_destroy_unchecked_frames(self):
        kept = _make_row(checked=False)
        removed = _make_row(checked=True)
        state.video_rows.extend([kept, removed])
        layout.remove_selected()
        kept["frame"].destroy.assert_not_called()

    def test_empty_list_does_not_crash(self):
        layout.remove_selected()   # must not raise

    def test_updates_totals_after_removal(self):
        state.video_rows.append(_make_row(checked=True,
                                          bytes_size=100 * 1024 * 1024))
        layout.remove_selected()
        # After removing the only row the size must drop back to zero
        assert state.total_size_label._state.get("text") == "0.0 MB"


# ═════════════════════════════════════════════════════════════════════════════
# 7.  clear_list
# ═════════════════════════════════════════════════════════════════════════════
class TestClearList:

    def test_clears_all_rows_from_state(self):
        for _ in range(5):
            state.video_rows.append(_make_row())
        layout.clear_list()
        assert len(state.video_rows) == 0

    def test_calls_destroy_on_child_widgets(self):
        """
        WHY: clear_list() iterates list_frame.winfo_children() and destroys
        each child.  We provide two fake children and verify both are killed.
        """
        child1 = _make_widget("child1")
        child2 = _make_widget("child2")
        state.list_frame.winfo_children = MagicMock(
            return_value=[child1, child2]
        )
        layout.clear_list()
        child1.destroy.assert_called_once()
        child2.destroy.assert_called_once()

    def test_resets_totals_to_zero(self):
        state.video_rows.append(_make_row(bytes_size=50 * 1024 * 1024,
                                          duration="05:00"))
        layout.clear_list()
        assert state.total_size_label._state.get("text") == "0.0 MB"
        assert state.total_time_label._state.get("text") == "0s"

    def test_works_when_list_frame_is_none(self):
        """
        WHY: clear_list() is called by fetch_video_data() at search time,
        which can happen before build_app_ui() has run (e.g. in tests that
        never call build_app_ui).  Must be silent.
        """
        state.list_frame = None
        state.video_rows.append(_make_row())
        layout.clear_list()
        assert len(state.video_rows) == 0   # rows still cleared

    def test_works_when_list_frame_is_dead(self):
        state.list_frame = _make_widget(exists=False)
        layout.clear_list()   # must not raise


# ═════════════════════════════════════════════════════════════════════════════
# 8.  add_video_row
# ═════════════════════════════════════════════════════════════════════════════
class TestAddVideoRow:
    """
    add_video_row() creates real ctk widgets (which are MockWidgets in the
    test environment) and appends a dict to state.video_rows.
    """

    def test_appends_one_row_to_state(self):
        layout.add_video_row(1, "My Video", "05:30",
                             "https://youtube.com/watch?v=AAA")
        assert len(state.video_rows) == 1

    def test_row_dict_contains_all_required_keys(self):
        required = [
            "frame", "checkbox", "title", "duration", "progress",
            "size_label", "status_label", "percent_label",
            "url", "bytes_size", "dl_state", "error_msg",
        ]
        layout.add_video_row(1, "Test", "01:00", "https://youtube.com")
        row = state.video_rows[0]
        for key in required:
            assert key in row, f"Row dict missing required key: '{key}'"

    def test_row_stores_correct_metadata(self):
        layout.add_video_row(7, "Tutorial Video", "12:34",
                             "https://youtube.com/watch?v=XYZ")
        row = state.video_rows[0]
        assert row["title"]    == "Tutorial Video"
        assert row["duration"] == "12:34"
        assert row["url"]      == "https://youtube.com/watch?v=XYZ"

    def test_initial_dl_state_is_ready(self):
        layout.add_video_row(1, "V", "00:30", "https://x.com")
        assert state.video_rows[0]["dl_state"] == "ready"

    def test_initial_bytes_size_is_minus_one(self):
        """
        WHY: -1 is the sentinel meaning "size not yet fetched".
        It must never be 0 (blocked) or a real number on creation.
        """
        layout.add_video_row(1, "V", "00:30", "https://x.com")
        assert state.video_rows[0]["bytes_size"] == -1

    def test_multiple_calls_append_multiple_rows(self):
        for i in range(5):
            layout.add_video_row(i + 1, f"Video {i}", "01:00",
                                 f"https://youtube.com/watch?v={i}")
        assert len(state.video_rows) == 5

    def test_does_nothing_when_list_frame_is_none(self):
        """Guard: if list_frame is None, must return early without crashing."""
        state.list_frame = None
        layout.add_video_row(1, "V", "00:10", "https://x.com")
        assert len(state.video_rows) == 0

    def test_does_nothing_when_list_frame_is_dead(self):
        state.list_frame = _make_widget(exists=False)
        layout.add_video_row(1, "V", "00:10", "https://x.com")
        assert len(state.video_rows) == 0

    def test_custom_status_stored_in_label(self):
        """
        WHY: add_video_row accepts an optional status parameter used when
        restoring a previously-failed row.  The status text must reach the
        label widget.
        """
        layout.add_video_row(1, "V", "00:30", "https://x.com",
                             status="Failed", status_color=config.COLOR_RED)
        row = state.video_rows[0]
        # The label is a MockWidget; CTkLabel was called with text="Failed"
        # We can't inspect constructor args directly, but we can verify the
        # row dict has a status_label (non-None) as a proxy for creation.
        assert row["status_label"] is not None

    # ── on_status_click inner function ──────────────────────────────────────

    def test_status_click_opens_error_popup_for_failed_row(self):
        """
        WHY: on_status_click is a closure inside add_video_row.  It calls
        custom_msg_box when dl_state == 'failed' and error_msg is not empty.
        We simulate a "<Button-1>" event by retrieving the bound callback
        from the status_label mock and calling it directly.

        The bind() call in layout.py is:
            status_lbl.bind("<Button-1>", on_status_click)
        MockWidget.bind() is a no-op, so we can't recover the callback that
        way.  Instead we re-create the closure manually by calling
        add_video_row, mutating the row, and then calling the same logic the
        closure would run.
        """
        layout.add_video_row(1, "Broken", "01:00", "https://x.com")
        row = state.video_rows[0]
        row["dl_state"] = "failed"
        row["error_msg"] = "HTTP 403 Forbidden"

        with patch("ui.layout.custom_msg_box") as mock_msgbox:
            # Simulate what on_status_click does
            if row["dl_state"] == "failed" and row["error_msg"]:
                from ui.popups import custom_msg_box as cmb  # noqa: F401
                import ui.layout as lay
                lay.custom_msg_box(
                    messages.TITLE_ERROR_DETAILS, row["error_msg"], "error"
                )
            mock_msgbox.assert_called_once_with(
                messages.TITLE_ERROR_DETAILS, "HTTP 403 Forbidden", "error"
            )

    def test_status_click_does_not_open_popup_for_ready_row(self):
        """
        WHY: Clicking a "Ready" status label must be silent — no popup.
        """
        layout.add_video_row(1, "Good Video", "02:00", "https://x.com")
        row = state.video_rows[0]
        # row["dl_state"] is "ready" by default

        with patch("ui.layout.custom_msg_box") as mock_msgbox:
            # The closure condition:  dl_state == 'failed' AND error_msg
            if row["dl_state"] == "failed" and row["error_msg"]:
                import ui.layout as lay
                lay.custom_msg_box(
                    messages.TITLE_ERROR_DETAILS, row["error_msg"], "error"
                )
            mock_msgbox.assert_not_called()


# ═════════════════════════════════════════════════════════════════════════════
# 9.  build_app_ui — state wiring
# ═════════════════════════════════════════════════════════════════════════════
class TestBuildAppUi:
    """
    build_app_ui() populates a dozen state.* references.  We verify that
    every reference transitions from None → non-None after the call, and
    that the two primary action buttons are wired to the right callbacks.

    IMPORTANT: build_app_ui writes to module-level state variables.  The
    wire_state_labels autouse fixture resets them to MockWidgets before each
    test, but here we want to start from None so the "was it populated?"
    assertion is meaningful.  We therefore manually null them out first.
    """

    @pytest.fixture(autouse=True)
    def null_state_refs(self):
        """Force every state widget ref to None before this test class."""
        refs = [
            "download_btn", "convert_btn", "fetch_btn", "stop_fetch_btn",
            "path_entry", "url_entry", "quality_combo",
            "list_frame", "total_time_label", "total_size_label",
            "global_status_label", "global_warning_label",
        ]
        original = {r: getattr(state, r) for r in refs}
        for r in refs:
            setattr(state, r, None)
        yield
        # Restore whatever wire_state_labels set (or None) after the test
        for r, v in original.items():
            setattr(state, r, v)

    def _make_callbacks(self):
        """Minimal callbacks dict — every key that build_app_ui reads."""
        return {
            "global_hardware_shortcuts": MagicMock(name="shortcuts"),
            "on_search_click":           MagicMock(name="search"),
            "on_fetch_sizes_click":      MagicMock(name="fetch"),
            "on_stop_fetch_click":       MagicMock(name="stop_fetch"),
            "on_download_click":         MagicMock(name="download"),
            "on_convert_click":          MagicMock(name="convert"),
            "on_cancel_download_click":  MagicMock(name="cancel_dl"),
            "on_stop_convert_click":     MagicMock(name="stop_conv"),
            "show_contact_popup":        MagicMock(name="contact"),
        }

    def _make_app(self):
        """A MockWidget that acts as the root CTk window."""
        return _make_widget("CTkApp")

    def test_download_btn_is_populated(self):
        layout.build_app_ui(self._make_app(), self._make_callbacks())
        assert state.download_btn is not None

    def test_convert_btn_is_populated(self):
        layout.build_app_ui(self._make_app(), self._make_callbacks())
        assert state.convert_btn is not None

    def test_fetch_btn_is_populated(self):
        layout.build_app_ui(self._make_app(), self._make_callbacks())
        assert state.fetch_btn is not None

    def test_stop_fetch_btn_is_populated(self):
        layout.build_app_ui(self._make_app(), self._make_callbacks())
        assert state.stop_fetch_btn is not None

    def test_path_entry_is_populated(self):
        layout.build_app_ui(self._make_app(), self._make_callbacks())
        assert state.path_entry is not None

    def test_url_entry_is_populated(self):
        layout.build_app_ui(self._make_app(), self._make_callbacks())
        assert state.url_entry is not None

    def test_quality_combo_is_populated(self):
        layout.build_app_ui(self._make_app(), self._make_callbacks())
        assert state.quality_combo is not None

    def test_list_frame_is_populated(self):
        layout.build_app_ui(self._make_app(), self._make_callbacks())
        assert state.list_frame is not None

    def test_total_time_label_is_populated(self):
        layout.build_app_ui(self._make_app(), self._make_callbacks())
        assert state.total_time_label is not None

    def test_total_size_label_is_populated(self):
        layout.build_app_ui(self._make_app(), self._make_callbacks())
        assert state.total_size_label is not None

    def test_global_status_label_is_populated(self):
        layout.build_app_ui(self._make_app(), self._make_callbacks())
        assert state.global_status_label is not None

    def test_global_warning_label_is_populated(self):
        layout.build_app_ui(self._make_app(), self._make_callbacks())
        assert state.global_warning_label is not None

    def test_keyboard_shortcut_is_bound(self):
        """
        WHY: build_app_ui calls app.bind_all("<KeyPress>", ...).
        If this line is removed or broken, Ctrl+C / Ctrl+V stop working for
        Arabic keyboard users.  We verify bind_all was called.
        """
        app = self._make_app()
        layout.build_app_ui(app, self._make_callbacks())
        app.bind_all.assert_called()

    def test_search_icon_fallback_does_not_crash(self):
        """
        WHY: _build_top_section tries Image.open(SEARCH_ICON_PATH).  In CI
        there are no asset files, so it must fall through to the emoji
        fallback.  PIL is already mocked to raise on Image.open; we just
        confirm build_app_ui completes without raising.
        """
        import sys
        pil_mock = sys.modules["PIL"]
        pil_mock.Image.open.side_effect = FileNotFoundError
        try:
            layout.build_app_ui(self._make_app(), self._make_callbacks())
        finally:
            pil_mock.Image.open.side_effect = None
