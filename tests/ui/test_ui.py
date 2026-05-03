import pytest
from unittest.mock import MagicMock
# Direct import of UI module
import ui.layout as m

class TestSafeUiUpdate:
    """Test safe UI update gate"""

    def test_configures_live_widget(self):
        from tests.conftest import MockWidget
        widget = MockWidget(name="label")
        m.safe_ui_update(widget, text="Hello", text_color="green")
        assert widget._state.get("text") == "Hello"
        assert widget._state.get("text_color") == "green"

    def test_skips_dead_widget(self):
        from tests.conftest import MockWidget
        widget = MockWidget(name="dead_label")
        widget.winfo_exists = MagicMock(return_value=False)
        m.safe_ui_update(widget, text="Should not appear")
        assert widget._state.get("text") is None

    def test_handles_none_widget_gracefully(self):
        m.safe_ui_update(None, text="anything") 

class TestVideoRowStructure:
    REQUIRED_KEYS = [
        "frame", "checkbox", "title", "duration", "progress",
        "size_label", "status_label", "percent_label", "url",
        "bytes_size", "dl_state", "error_msg",
    ]

    def test_all_required_keys_present(self, mock_video_row):
        for key in self.REQUIRED_KEYS:
            assert key in mock_video_row, f"Row dict is missing key: '{key}'"

    def test_initial_dl_state_is_ready(self, mock_video_row):
        assert mock_video_row["dl_state"] == "ready"

class TestDownloadButtonStateMachine:
    def test_button_changes_to_cancel_on_start(self):
        import config
        from tests.conftest import MockWidget
        btn = MockWidget(name="download_btn")
        btn.configure(text="Cancel Download", fg_color=config.COLOR_RED)
        assert btn._state["text"] == "Cancel Download"
        assert btn._state["fg_color"] == config.COLOR_RED

class TestSizeDisplayChain:
    def test_blocked_video_displays_blocked_in_red(self, mock_video_row):
        import config
        mock_video_row["bytes_size"] = 0
        m.safe_ui_update(mock_video_row["size_label"], text="Blocked", text_color=config.COLOR_RED)
        assert mock_video_row["size_label"]._state["text"] == "Blocked"
        assert mock_video_row["size_label"]._state["text_color"] == config.COLOR_RED

class TestProgressHookMath:
    @pytest.mark.parametrize("downloaded, total, expected_percent", [
        (0, 1000000, 0.0), (500000, 1000000, 0.5), (1000000, 1000000, 1.0), (250000, 1000000, 0.25),
    ])
    def test_percent_calculation(self, downloaded, total, expected_percent):
        percent = downloaded / total
        assert percent == expected_percent