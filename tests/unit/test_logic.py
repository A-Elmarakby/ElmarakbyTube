import pytest
import config
# Import from new function paths
import core.utils as m
from ui import popups

# Connect name check function because it moved to popups file
m.is_valid_name = popups.is_valid_name

class TestFormatSize:
    @pytest.mark.parametrize("bytes_input, expected", [
        (0,           "0.0 MB"),
        (-1,          "0.0 MB"),
        (1048576,     "1.0 MB"),
        (5242880,     "5.0 MB"),
        (1048576000,  "0.98 GB"),
        (1073741824,  "1.00 GB"),
        (2684354560,  "2.50 GB"),
    ])
    def test_format_size_parametrized(self, bytes_input, expected):
        result = m.format_size(bytes_input)
        assert result == expected

class TestFormatDuration:
    @pytest.mark.parametrize("seconds_input, expected", [
        (0,     "00:00"),
        (45,    "00:45"),
        (125,   "02:05"),
        (600,   "10:00"),
        (3600,  "1:00:00"),
        (3665,  "1:01:05"),
    ])
    def test_format_duration_parametrized(self, seconds_input, expected):
        assert m.format_duration(seconds_input) == expected

class TestApplyBidi:
    RLE = "\u202B"
    PDF = "\u202C"

    def test_arabic_text_starts_with_rle(self):
        assert m.apply_bidi("مرحبًا").startswith(self.RLE)

    def test_arabic_text_ends_with_pdf(self):
        assert m.apply_bidi("نص").endswith(self.PDF)

    @pytest.mark.parametrize("english_text", ["Download Selected", "Fetch Sizes", "1080p", ""])
    def test_english_text_passes_through(self, english_text):
        assert m.apply_bidi(english_text) == english_text

    def test_multiline_arabic_wrapping(self):
        result = m.apply_bidi("سطر1\nسطر2")
        lines = result.split("\n")
        for line in lines:
            assert line.startswith(self.RLE) and line.endswith(self.PDF)

class TestIsValidName:
    @pytest.mark.parametrize("name, expect_valid", [
        ("Ahmed", True), ("Ali Mohamed", True), ("", False), 
        ("A", False), ("A" * 31, False), ("Ahmed123", False), ("Ahhh", False),
    ])
    def test_is_valid_name_parametrized(self, name, expect_valid):
        config.NAME_ALLOW_NUMBERS = False
        config.NAME_MAX_REPEATS = 2
        is_valid, error_msg = m.is_valid_name(name)
        assert is_valid == expect_valid

class TestGetYdlFormatString:
    @pytest.mark.parametrize("quality_input, expected_format", [
        ("Audio Only (MP3)",   "bestaudio/best"),
        ("Best Quality",       "bestvideo+bestaudio/best"),
        ("Medium",             "bestvideo[height<=720]+bestaudio/best"),
        ("1080p",              "bestvideo[height<=1080]+bestaudio/best"),
        ("Select Quality",     "bestvideo+bestaudio/best"),
    ])
    def test_get_ydl_format_string(self, quality_input, expected_format):
        # Import function from new place in downloader core
        from core.downloader import get_ydl_format_string
        assert get_ydl_format_string(quality_input) == expected_format

class TestBatchCalculationMath:
    @pytest.mark.parametrize("num_videos, max_threads, expected_batches", [
        (5, 5, 1), (10, 5, 2), (11, 5, 3), (1, 5, 1),
    ])
    def test_batch_calculation(self, num_videos, max_threads, expected_batches):
        result = (num_videos + max_threads - 1) // max_threads
        assert result == expected_batches

class TestDurationParsingInTotals:
    @staticmethod
    def parse_duration_string(dur_str: str) -> int:
        if dur_str in ("--:--", "N/A", "00:00"): return 0
        parts = dur_str.split(":")
        if len(parts) == 2: return int(parts[0]) * 60 + int(parts[1])
        elif len(parts) == 3: return int(parts[0]) * 3600 + int(parts[1]) * 60 + int(parts[2])
        return 0

    @pytest.mark.parametrize("dur_str, expected_seconds", [
        ("00:00", 0), ("01:30", 90), ("1:00:00", 3600), ("--:--", 0),
    ])
    def test_duration_parsing(self, dur_str, expected_seconds):
        assert self.parse_duration_string(dur_str) == expected_seconds

class TestFindDownloadedFile:
    def test_finds_mp4_file(self, tmp_path):
        # Changed main_3 to main to match your real file name
        from main import find_downloaded_file
        f = tmp_path / "My Test Video.mp4"
        f.touch()
        assert find_downloaded_file(str(tmp_path), "My Test Video") == str(f)

    def test_returns_none_when_not_found(self, tmp_path):
        from main import find_downloaded_file
        assert find_downloaded_file(str(tmp_path), "Nonexistent Title") is None

    def test_ignores_part_files(self, tmp_path):
        from main import find_downloaded_file
        part = tmp_path / "In Progress.mp4.part"
        part.touch()
        assert find_downloaded_file(str(tmp_path), "In Progress") is None