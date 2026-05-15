"""
File: test_resolution_snapping.py
What it does: Tests the three video quality functions in core/fetcher.py.
How to run: Open your terminal in the project root and type: pytest tests/unit/test_resolution_snapping.py -v
"""

import pytest
import config
# Import the real functions safely
from core.fetcher import _get_short_side, _snap_to_standard, _extract_qualities

# ==========================================
# SETUP: Isolated test configuration
# ==========================================

@pytest.fixture(autouse=True)
def setup_test_threshold(monkeypatch):
    """
    Force SNAP_THRESHOLD to be 0.10 only for tests in this file.
    This protects tests from any future changes in config.py.
    """
    monkeypatch.setattr(config, "SNAP_THRESHOLD", 0.10)
# ==========================================
# TESTS FOR: _get_short_side(fmt)
# What this function does:
#   - Takes one video format dictionary.
#   - Returns the SHORT side (smaller number of width or height).
#   - Returns None if the data is bad or missing.
# ==========================================

class TestGetShortSide:
    """All tests for the _get_short_side function."""

    # --- Normal video formats ---

    def test_normal_horizontal_video(self):
        """A normal wide video. Width is bigger. Short side is the height (1080)."""
        fmt = {'width': 1920, 'height': 1080}
        assert _get_short_side(fmt) == 1080

    def test_normal_vertical_video(self):
        """A vertical video like a Reel or Short. Height is bigger. Short side is the width (1080)."""
        fmt = {'width': 1080, 'height': 1920}
        assert _get_short_side(fmt) == 1080

    def test_square_video(self):
        """Width and height are the same. Short side is just that number."""
        fmt = {'width': 720, 'height': 720}
        assert _get_short_side(fmt) == 720

    # --- String number values from yt-dlp ---

    def test_string_integer_dimensions(self):
        """yt-dlp sometimes sends numbers as text like '1280'. We must handle this."""
        fmt = {'width': '1280', 'height': '720'}
        assert _get_short_side(fmt) == 720

    def test_string_float_exact(self):
        """yt-dlp can send '720.0'. This should work and return 720."""
        fmt = {'width': '1280', 'height': '720.0'}
        assert _get_short_side(fmt) == 720

    def test_string_float_rounds_up(self):
        """
        The key rounding test: '719.9' must round UP to 720, not down to 719.
        If it rounds down, the snap math could push 719 outside the 10% zone
        when it should clearly be 720p.
        """
        fmt = {'width': '1280', 'height': '719.9'}
        assert _get_short_side(fmt) == 720

    def test_string_float_rounds_down(self):
        """'720.4' should round DOWN to 720, not up to 721."""
        fmt = {'width': '1280', 'height': '720.4'}
        assert _get_short_side(fmt) == 720

    # --- Bad or missing data ---

    def test_none_width_and_height(self):
        """Both values are None. We cannot calculate anything. Must return None."""
        fmt = {'width': None, 'height': None}
        assert _get_short_side(fmt) is None

    def test_none_width_only(self):
        """Width is None but height exists. Still bad data. Must return None."""
        fmt = {'width': None, 'height': 1080}
        assert _get_short_side(fmt) is None

    def test_none_height_only(self):
        """Height is None but width exists. Still bad data. Must return None."""
        fmt = {'width': 1920, 'height': None}
        assert _get_short_side(fmt) is None

    def test_missing_height_key(self):
        """The 'height' key does not exist in the dictionary at all. Must return None."""
        fmt = {'width': 854}
        assert _get_short_side(fmt) is None

    def test_missing_width_key(self):
        """The 'width' key does not exist in the dictionary at all. Must return None."""
        fmt = {'height': 480}
        assert _get_short_side(fmt) is None

    def test_empty_dictionary(self):
        """The dictionary has no keys at all. Must return None."""
        fmt = {}
        assert _get_short_side(fmt) is None

    def test_zero_width(self):
        """Width is 0. Zero means no real video. Must return None."""
        fmt = {'width': 0, 'height': 720}
        assert _get_short_side(fmt) is None

    def test_zero_height(self):
        """Height is 0. Same as above. Must return None."""
        fmt = {'width': 1280, 'height': 0}
        assert _get_short_side(fmt) is None

    def test_negative_width(self):
        """Negative numbers make no sense. Must return None directly."""
        fmt = {'width': -1920, 'height': 1080}
        assert _get_short_side(fmt) is None

    def test_negative_height(self):
        """Negative numbers make no sense. Must return None directly."""
        fmt = {'width': 1280, 'height': -1080}
        assert _get_short_side(fmt) is None

    # --- Corrupted text values ---

    def test_corrupted_text_string(self):
        """Value is the word 'unknown'. Cannot convert to a number. Must return None."""
        fmt = {'width': 'unknown', 'height': 1080}
        assert _get_short_side(fmt) is None

    def test_string_with_p_suffix(self):
        """Value is '720p'. The 'p' breaks float(). Must return None."""
        fmt = {'width': 1280, 'height': '720p'}
        assert _get_short_side(fmt) is None

    def test_empty_string_value(self):
        """Value is an empty string ''. This is falsy, so the guard catches it. Must return None."""
        fmt = {'width': '', 'height': 720}
        assert _get_short_side(fmt) is None


# ==========================================
# TESTS FOR: _snap_to_standard(short_side)
# What this function does:
#   - Takes one number (the short side of a video).
#   - Checks if it is close (within 10%) to a standard resolution.
#   - Returns the standard number if yes, or None if no.
# Standard list: [8640, 4320, 2160, 1440, 1080, 720, 480, 360, 240, 144]
# ==========================================

class TestSnapToStandard:
    """All tests for the _snap_to_standard function."""

    # --- Exact matches (0% difference) ---

    def test_exact_match_1080(self):
        """1080 is exactly in the list. Must return 1080."""
        assert _snap_to_standard(1080) == 1080

    def test_exact_match_720(self):
        """720 is exactly in the list. Must return 720."""
        assert _snap_to_standard(720) == 720

    def test_exact_match_144(self):
        """144 is the smallest allowed resolution. Must return 144."""
        assert _snap_to_standard(144) == 144

    def test_exact_match_8640(self):
        """8640 is the largest (16K). Must return 8640."""
        assert _snap_to_standard(8640) == 8640

    def test_exact_match_4320(self):
        """4320 is 8K. Must return 4320."""
        assert _snap_to_standard(4320) == 4320

    # --- Values just inside the 10% boundary (should SNAP) ---

    def test_just_inside_threshold_above_720(self):
        """
        791 vs 720: difference = 71 / 720 = 9.86%. This is less than 10%.
        Must snap to 720.
        """
        assert _snap_to_standard(791) == 720

    def test_just_inside_threshold_below_720(self):
        """
        649 vs 720: difference = 71 / 720 = 9.86%. This is less than 10%.
        Must snap to 720.
        """
        assert _snap_to_standard(649) == 720

    def test_just_inside_threshold_above_1080(self):
        """
        1088 vs 1080: difference = 8 / 1080 = 0.74%. Very small. Must snap to 1080.
        This is a real value that yt-dlp sends sometimes.
        """
        assert _snap_to_standard(1088) == 1080

    def test_just_inside_threshold_above_480(self):
        """
        528 vs 480: difference = 48 / 480 = 10.0%. Exactly at the boundary.
        10% <= 10% is True. Must snap to 480.
        """
        assert _snap_to_standard(528) == 480

    # --- Values just outside the 10% boundary (should NOT snap) ---

    def test_just_outside_threshold_above_720(self):
        """
        793 vs 720: difference = 73 / 720 = 10.14%. This is more than 10%.
        793 vs 1080: difference = 287 / 1080 = 26.6%. Also too far.
        Must return None.
        """
        assert _snap_to_standard(793) is None

    def test_just_outside_threshold_below_720(self):
        """
        647 vs 720: difference = 73 / 720 = 10.14%. More than 10%.
        647 vs 480: difference = 167 / 480 = 34.8%. Also too far.
        Must return None.
        """
        assert _snap_to_standard(647) is None

    def test_weird_resolution_864(self):
        """
        864 is a known weird resolution from yt-dlp.
        864 vs 720: difference = 144 / 720 = 20%. Too far.
        864 vs 1080: difference = 216 / 1080 = 20%. Too far.
        Must return None.
        """
        assert _snap_to_standard(864) is None

    def test_weird_resolution_800(self):
        """
        800 is a weird square video resolution.
        800 vs 720: difference = 80 / 720 = 11.1%. Too far.
        800 vs 1080: difference = 280 / 1080 = 25.9%. Too far.
        Must return None.
        """
        assert _snap_to_standard(800) is None

    # --- Values that are too small ---

    def test_value_below_all_standards(self):
        """
        50 is smaller than the smallest standard (144).
        50 vs 144: difference = 94 / 144 = 65.3%. Way too far.
        Must return None.
        """
        assert _snap_to_standard(50) is None

    # --- First match wins (important for overlapping zones) ---

    def test_returns_first_matching_standard(self):
        """
        The list is checked from high to low [8640, 4320, ...].
        A value should snap to the FIRST standard it matches, which is the highest one.
        This test makes sure the order is correct.
        2100 vs 2160: difference = 60 / 2160 = 2.78%. Snaps to 2160, not 1440.
        """
        assert _snap_to_standard(2100) == 2160


# ==========================================
# TESTS FOR: _extract_qualities(formats)
# What this function does:
#   - Takes the full list of video formats from yt-dlp.
#   - Runs _get_short_side and _snap_to_standard on each one.
#   - Returns a clean, sorted list of strings like ["1080p", "720p"].
# ==========================================

class TestExtractQualities:
    """All tests for the _extract_qualities function."""

    def test_empty_list_returns_empty(self):
        """No formats at all. Result must be an empty list."""
        assert _extract_qualities([]) == []

    def test_all_bad_formats_returns_empty(self):
        """Every format has bad data. None pass. Result must be empty."""
        formats = [
            {'width': None, 'height': None},
            {'width': 0, 'height': 720},
            {'width': 'bad', 'height': 'data'},
        ]
        assert _extract_qualities(formats) == []

    def test_all_too_small_returns_empty(self):
        """Every format is smaller than 144p. All are filtered out. Result is empty."""
        formats = [
            {'width': 100, 'height': 100},
            {'width': 128, 'height': 72},
        ]
        assert _extract_qualities(formats) == []

    def test_single_good_format(self):
        """One good 1080p video. Result must be ['1080p HD']."""
        formats = [{'width': 1920, 'height': 1080}]
        assert _extract_qualities(formats) == ["1080p HD"]

    def test_multiple_good_formats_sorted(self):
        """Three different formats. Result must be sorted with proper badges."""
        formats = [
            {'width': 854, 'height': 480},
            {'width': 1920, 'height': 1080},
            {'width': 1280, 'height': 720},
        ]
        assert _extract_qualities(formats) == ["1080p HD", "720p", "480p"]

    def test_duplicates_are_removed(self):
        """Same resolution appears many times. Result must have 1080p HD only once."""
        formats = [
            {'width': 1920, 'height': 1080},
            {'width': 1920, 'height': 1080},
        ]
        assert _extract_qualities(formats) == ["1080p HD"]

    def test_vertical_videos_read_correctly(self):
        """A vertical Reel (1080x1920) must show as 1080p HD, not 1920p."""
        formats = [{'width': 1080, 'height': 1920}]
        assert _extract_qualities(formats) == ["1080p HD"]

    def test_vertical_and_horizontal_same_resolution_deduped(self):
        """One horizontal and one vertical 1080p must dedup to single 1080p HD."""
        formats = [
            {'width': 1920, 'height': 1080},
            {'width': 1080, 'height': 1920},
        ]
        assert _extract_qualities(formats) == ["1080p HD"]

    def test_near_standard_resolution_snaps_correctly(self):
        """1088 is close to 1080. Must snap and show as '1080p HD'."""
        formats = [{'width': 1920, 'height': 1088}]
        assert _extract_qualities(formats) == ["1080p HD"]

    def test_weird_resolution_is_discarded(self):
        """864p is too far from standard. It must be thrown away."""
        formats = [{'width': 1536, 'height': 864}]
        assert _extract_qualities(formats) == []

    def test_full_mixed_format_list(self):
        """Realistic mix of good, bad, and duplicate formats."""
        formats = [
            {'width': 1920, 'height': 1080},    # 1080p HD
            {'width': 1080, 'height': 1920},    # Duplicate 1080p HD
            {'width': '1280', 'height': '720'}, # 720p
            {'width': 854, 'height': 480},      # 480p
            {'width': 1536, 'height': 864},     # Bad
            {'width': 0, 'height': 720},        # Bad
            {'width': None, 'height': None},    # Bad
        ]
        assert _extract_qualities(formats) == ["1080p HD", "720p", "480p"]

    def test_8k_and_4k_resolutions(self):
        """Ultra high resolutions must get 4K and 8K badges and sort correctly."""
        formats = [
            {'width': 3840, 'height': 2160},  # 4K
            {'width': 7680, 'height': 4320},  # 8K
        ]
        assert _extract_qualities(formats) == ["4320p 8K", "2160p 4K"]

    def test_string_float_719_9_rounds_to_720(self):
        """'719.9' rounds UP to 720 and appears as '720p' (no HD badge)."""
        formats = [{'width': '1280', 'height': '719.9'}]
        assert _extract_qualities(formats) == ["720p"]
