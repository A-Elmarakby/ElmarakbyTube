"""
tests/unit/test_popups.py
═══════════════════════════════════════════════════════════════════════════════
Unit tests for ui/popups.py

STRATEGY
────────
Testing blocking Tkinter popups (which use `wait_window()`) is notoriously
difficult. Instead of using flaky background threads, we use a robust
synchronous mocking strategy:
1. We mock CTkToplevel, CTkButton, CTkLabel, etc.
2. We intercept the creation of CTkButton to capture its `command`.
3. We override `wait_window` to instantly trigger the button command we 
   want to test, simulating an instantaneous user click.
"""

import pytest
from unittest.mock import patch, MagicMock, mock_open
import os

import config
import messages
import ui.popups as popups
from core.utils import apply_bidi

# ─────────────────────────────────────────────────────────────────────────────
# Fixture — UIMocker (Intercepts buttons and simulates clicks)
# ─────────────────────────────────────────────────────────────────────────────
@pytest.fixture
def mock_ui():
    """
    Mocks CustomTkinter components. Intercepts CTkButton to store its callback
    so we can simulate clicks dynamically.
    """
    class UIMocker:
        def __init__(self):
            self.commands = {}
            self.dialog_mock = MagicMock()
            self.mock_entry = None
            
        def fake_button(self, master=None, **kwargs):
            # Save the command using the button's text as the key
            text = kwargs.get('text', '')
            self.commands[text] = kwargs.get('command')
            return MagicMock()

        def click(self, text_key):
            """Simulates a click on a button containing the text_key."""
            bidi_text = apply_bidi(text_key)
            for key, cmd in self.commands.items():
                # Check both normal and bidi versions, allowing for emojis/spaces
                if bidi_text in key or text_key in key:
                    if cmd:
                        cmd()
                    return
            raise ValueError(f"Button '{text_key}' not found. Available: {list(self.commands.keys())}")

    mocker = UIMocker()
    
    # Patch all the CTk UI elements used in popups.py
    with patch('ui.popups.ctk.CTkToplevel', return_value=mocker.dialog_mock), \
         patch('ui.popups.ctk.CTkButton', side_effect=mocker.fake_button), \
         patch('ui.popups.ctk.CTkLabel'), \
         patch('ui.popups.ctk.CTkImage'), \
         patch('ui.popups.config.play_sound'), \
         patch('ui.popups.ctk.CTkEntry') as mock_entry:
        
        mocker.mock_entry = mock_entry
        yield mocker


# ═════════════════════════════════════════════════════════════════════════════
# 1. Core Logic & Icons
# ═════════════════════════════════════════════════════════════════════════════
class TestAddDialogIcon:
    def test_add_dialog_icon_applies_all_stages(self):
        dialog = MagicMock()
        popups.add_dialog_icon(dialog)
        
        # Stage 1: Immediate call
        dialog.wm_iconbitmap.assert_called_with(config.ICON_FILE)
        # Stage 2: 200ms delay call
        dialog.after.assert_called()
        # Stage 3: GC Protection
        assert getattr(dialog, "_icon_path_ref", None) == config.ICON_FILE

class TestIsValidName:
    def test_empty_name(self):
        valid, msg = popups.is_valid_name("   ")
        assert not valid
        assert msg == messages.MSG_NAME_REQUIRED

    def test_too_short(self):
        valid, msg = popups.is_valid_name("A")
        assert not valid
        assert msg == messages.MSG_INVALID_NAME

    def test_too_long(self):
        valid, msg = popups.is_valid_name("A" * 31)
        assert not valid
        assert msg == messages.MSG_INVALID_NAME

    def test_contains_numbers(self):
        config.NAME_ALLOW_NUMBERS = False
        valid, msg = popups.is_valid_name("Ahmed123")
        assert not valid
        assert msg == messages.MSG_INVALID_NAME
        
    def test_valid_name(self):
        valid, msg = popups.is_valid_name("Ahmed")
        assert valid
        assert msg == ""


# ═════════════════════════════════════════════════════════════════════════════
# 2. General Message Boxes
# ═════════════════════════════════════════════════════════════════════════════
class TestMessageBoxes:
    def test_custom_msg_box_destroys_on_ok(self, mock_ui):
        # When wait_window is called, simulate clicking OK
        mock_ui.dialog_mock.wait_window.side_effect = lambda: mock_ui.click(messages.BTN_OK)
        
        popups.custom_msg_box("Title", "Error Msg", "error")
        mock_ui.dialog_mock.destroy.assert_called()

    def test_custom_alert_dialog_destroys_on_ok(self, mock_ui):
        mock_ui.dialog_mock.wait_window.side_effect = lambda: mock_ui.click("OK")
        popups.custom_alert_dialog("Title", "Msg")
        mock_ui.dialog_mock.destroy.assert_called()


# ═════════════════════════════════════════════════════════════════════════════
# 3. Interactive Popups (Yes/No, Speed, Exit)
# ═════════════════════════════════════════════════════════════════════════════
class TestCustomAskYesNo:
    def test_returns_true_on_yes(self, mock_ui):
        mock_ui.dialog_mock.wait_window.side_effect = lambda: mock_ui.click(messages.BTN_YES)
        assert popups.custom_ask_yes_no("Title", "Message") is True

    def test_returns_false_on_no(self, mock_ui):
        mock_ui.dialog_mock.wait_window.side_effect = lambda: mock_ui.click(messages.BTN_NO)
        assert popups.custom_ask_yes_no("Title", "Message") is False

class TestAskConversionSpeed:
    def test_fast_speed(self, mock_ui):
        mock_ui.dialog_mock.wait_window.side_effect = lambda: mock_ui.click(messages.BTN_FAST)
        assert popups.ask_conversion_speed() == "fast"

    def test_slow_speed(self, mock_ui):
        mock_ui.dialog_mock.wait_window.side_effect = lambda: mock_ui.click(messages.BTN_SLOW)
        assert popups.ask_conversion_speed() == "slow"

    def test_cancel_default(self, mock_ui):
        # If wait_window finishes without clicking (e.g. user clicked X on window)
        # It should return the default "cancel"
        assert popups.ask_conversion_speed() == "cancel"

class TestV2ExitDialog:
    def test_stay(self, mock_ui):
        mock_ui.dialog_mock.wait_window.side_effect = lambda: mock_ui.click(messages.BTN_STAY)
        assert popups.v2_exit_dialog("Title", "Msg", messages.BTN_STAY, messages.BTN_LEAVE) == "stay"

    def test_leave(self, mock_ui):
        mock_ui.dialog_mock.wait_window.side_effect = lambda: mock_ui.click(messages.BTN_LEAVE)
        assert popups.v2_exit_dialog("Title", "Msg", messages.BTN_STAY, messages.BTN_LEAVE) == "leave"


# ═════════════════════════════════════════════════════════════════════════════
# 4. Standalone Feature Popups (Contact, Welcome)
# ═════════════════════════════════════════════════════════════════════════════
class TestShowContactPopup:
    @patch('ui.popups.webbrowser.open')
    def test_links_open_correctly(self, mock_webbrowser, mock_ui):
        # Contact popup does not block with wait_window, it just opens.
        popups.show_contact_popup()
        
        mock_ui.click("LinkedIn")
        mock_webbrowser.assert_called_with(messages.URL_LINKEDIN)

        mock_ui.click("WhatsApp")
        mock_webbrowser.assert_called_with(messages.URL_WHATSAPP)

class TestWelcomeOnboarding:
    @patch('os.path.exists', return_value=True)
    def test_skips_if_user_data_exists(self, mock_exists, mock_ui):
        popups.show_welcome_onboarding()
        # TopLevel should not be titled/created if file exists
        mock_ui.dialog_mock.title.assert_not_called()

    @patch('os.path.exists', return_value=False)
    @patch('os.makedirs')
    @patch('ui.popups.json.dump') # we added check for json
    @patch('builtins.open', new_callable=mock_open)
    def test_valid_name_saves_data_and_greets(self, mock_file, mock_json_dump, mock_makedirs, mock_exists, mock_ui):
        # put valid name in input
        entry_instance = MagicMock()
        entry_instance.get.return_value = "Abdelrahman"
        mock_ui.mock_entry.return_value = entry_instance

        popups.show_welcome_onboarding()
        mock_ui.click(messages.BTN_CONFIRM_NAME)

        # file should be saved
        mock_file.assert_called_once()
        # check json.dump got correct data
        mock_json_dump.assert_called_once_with({"name": "Abdelrahman"}, mock_file())

    @patch('os.path.exists', return_value=False)
    @patch('os.makedirs')
    @patch('ui.popups.custom_alert_dialog')
    def test_invalid_name_shows_alert(self, mock_alert, mock_makedirs, mock_exists, mock_ui):
        # Inject invalid name into the mocked CTkEntry
        entry_instance = MagicMock()
        entry_instance.get.return_value = "123" # Numbers not allowed
        mock_ui.mock_entry.return_value = entry_instance

        popups.show_welcome_onboarding()
        mock_ui.click(messages.BTN_CONFIRM_NAME)

        # Alert should be triggered
        mock_alert.assert_called_once()
        args = mock_alert.call_args[0]
        assert args[0] == messages.TITLE_ALERT
        assert messages.MSG_INVALID_NAME in args[1]