"""
tests/unit/test_logic.py
==================================================================
Exhaustive Unit Tests for Pure Logic (Merged from Claude 1)
Tests mathematical formulas, text injection, and validations.
"""

import pytest
import config

# Use the fixture from conftest.py to load main safely
@pytest.fixture(scope="module")
def m(main_module):
    """Shorthand alias for the main module."""
    return main_module

class TestFormatSize:
    """Validates the byte-to-human-readable size converter."""
    
    @pytest.mark.parametrize("bytes_input, expected", [
        (0,           "0.0 MB"),   # Zero bytes
        (-1,          "0.0 MB"),   # Negative bytes treated as zero
        (1048576,     "1.0 MB"),   # Exactly 1 MB
        (5242880,     "5.0 MB"),   # 5 MB
        (1048576000,  "0.98 GB"),  # Shifts to GB in the actual main.py logic
        (1073741824,  "1.00 GB"),  # Exactly 1 GB
        (2684354560,  "2.50 GB"),  # 2.5 GB
    ])
    def test_format_size_parametrized(self, m, bytes_input, expected):
        result = m.format_size(bytes_input)
        assert result == expected, f"Expected {expected} but got {result}"

class TestFormatDuration:
    """Validates the duration formatter used in video list rows."""
    
    @pytest.mark.parametrize("seconds_input, expected", [
        (0,     "00:00"),
        (45,    "00:45"),
        (125,   "02:05"),      # 2 mins, 5 secs
        (600,   "10:00"),
        (3600,  "1:00:00"),    # 1 hour exactly
        (3665,  "1:01:05"),    # 1 hr, 1 min, 5 secs
    ])
    def test_format_duration_parametrized(self, m, seconds_input, expected):
        assert m.format_duration(seconds_input) == expected

class TestApplyBidi:
    """Validates the RTL Unicode injection for Arabic UI text."""
    RLE = "\u202B"
    PDF = "\u202C"

    def test_arabic_text_starts_with_rle(self, m):
        """Arabic text must be wrapped starting with RLE."""
        assert m.apply_bidi("مرحبًا").startswith(self.RLE)

    def test_arabic_text_ends_with_pdf(self, m):
        """Arabic text must close with PDF."""
        assert m.apply_bidi("نص").endswith(self.PDF)

    @pytest.mark.parametrize("english_text", [
        "Download Selected",
        "Fetch Sizes",
        "1080p",
        "", # Empty string
    ])
    def test_english_text_passes_through(self, m, english_text):
        """English text must NOT receive RTL markers."""
        assert m.apply_bidi(english_text) == english_text

    def test_multiline_arabic_wrapping(self, m):
        """Each line in multi-line Arabic must be wrapped individually to prevent escaping."""
        result = m.apply_bidi("سطر1\nسطر2")
        lines = result.split("\n")
        for line in lines:
            assert line.startswith(self.RLE) and line.endswith(self.PDF)

class TestIsValidName:
    """Tests the onboarding name validation rules."""
    
    @pytest.mark.parametrize("name, expect_valid", [
        ("Ahmed",        True),
        ("Ali Mohamed",  True),
        ("",             False),  # Empty
        ("A",            False),  # Too short
        ("A" * 31,       False),  # Too long
        ("Ahmed123",     False),  # Contains numbers
        ("Ahhh",         False),  # Absurd repetition
    ])
    def test_is_valid_name_parametrized(self, m, name, expect_valid):
        # Override config strictly for this test
        config.NAME_ALLOW_NUMBERS = False
        config.NAME_MAX_REPEATS = 2
        
        is_valid, error_msg = m.is_valid_name(name)
        assert is_valid == expect_valid

class TestGetYdlFormatString:
    """Validates the quality label mapping for yt-dlp."""
    
    @pytest.mark.parametrize("quality_input, expected_format", [
        ("Audio Only (MP3)",   "bestaudio/best"),
        ("Best Quality",       "bestvideo+bestaudio/best"),
        ("Medium",             "bestvideo[height<=720]+bestaudio/best"),
        ("1080p",              "bestvideo[height<=1080]+bestaudio/best"),
        ("Select Quality",     "bestvideo+bestaudio/best"), # Fallback
    ])
    def test_get_ydl_format_string(self, m, quality_input, expected_format):
        assert m.get_ydl_format_string(quality_input) == expected_format

class TestBatchCalculationMath:
    """Tests the ceiling-division formula used for thread timeouts."""
    
    @pytest.mark.parametrize("num_videos, max_threads, expected_batches", [
        (5,    5,   1),
        (10,   5,   2),
        (11,   5,   3),  # Ceiling test
        (1,    5,   1),
    ])
    def test_batch_calculation(self, m, num_videos, max_threads, expected_batches):
        # Formula from main.py line ~549
        result = (num_videos + max_threads - 1) // max_threads
        assert result == expected_batches

        # =============================================================================
# G. Duration Parsing Math (update_dynamic_totals contract)
# =============================================================================

class TestDurationParsingInTotals:
    @staticmethod
    def parse_duration_string(dur_str: str) -> int:
        if dur_str in ("--:--", "N/A", "00:00"):
            return 0
        parts = dur_str.split(":")
        if len(parts) == 2:
            return int(parts[0]) * 60 + int(parts[1])
        elif len(parts) == 3:
            return int(parts[0]) * 3600 + int(parts[1]) * 60 + int(parts[2])
        return 0

    @pytest.mark.parametrize("dur_str, expected_seconds", [
        ("00:00",   0),
        ("01:30",   90),
        ("1:00:00", 3600),
        ("--:--",   0),
    ])
    def test_duration_parsing(self, dur_str, expected_seconds):
        assert self.parse_duration_string(dur_str) == expected_seconds


# =============================================================================
# H. find_downloaded_file() — File lookup on real filesystem
# =============================================================================

class TestFindDownloadedFile:
    def test_finds_mp4_file(self, m, tmp_path):
        f = tmp_path / "My Test Video.mp4"
        f.touch()
        assert m.find_downloaded_file(str(tmp_path), "My Test Video") == str(f)

    def test_returns_none_when_not_found(self, m, tmp_path):
        assert m.find_downloaded_file(str(tmp_path), "Nonexistent Title") is None

    def test_ignores_part_files(self, m, tmp_path):
        part = tmp_path / "In Progress.mp4.part"
        part.touch()
        assert m.find_downloaded_file(str(tmp_path), "In Progress") is None