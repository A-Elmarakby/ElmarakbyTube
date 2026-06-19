"""
test_analytics.py — Exhaustive forensic test suite for core/analytics.py
=========================================================================
بناءً على تقرير المرحلة 1 (التدقيق الجنائي) ومصفوفة الاختبارات المتفق عليها.

Design rules (enforced):
  1. Scope = core/analytics.py ONLY (no main.py logic).            النطاق: محرك التحليلات فقط
  2. Real disk I/O via tmp_path; NO mocking of file writes.        قرص حقيقي بدون محاكاة للكتابة
  3. autouse fixture redirects BOTH path functions AND resets the  إعادة ضبط الكاش قبل وبعد كل اختبار
     module-global cache before AND after every test (Phase 1 D8).
  4. Discovered bugs are written as the DESIRED behavior and       الباجات تُكتب كسلوك مطلوب + xfail
     marked @pytest.mark.xfail(strict=False) so CI stays green.

Colour key:  GREEN = must pass (correct behaviour)
             YELLOW (xfail) = documents a Phase-1 bug; will fix later.
"""

import os
import json
import copy
import time
import datetime
import threading

import pytest

import config
import core.analytics as analytics


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────
def read_disk(path):
    """Read a JSON file straight from disk (proves real persistence, not cache)."""
    with open(str(path), "r", encoding="utf-8") as f:
        return json.load(f)


def _assert_same_structure(expected, actual, path=""):
    """Recursively assert `actual` contains every key of `expected` (same shape)."""
    assert isinstance(actual, dict), f"{path or '<root>'} is not a dict"
    for key, val in expected.items():
        assert key in actual, f"Missing schema key: {path}/{key}"
        if isinstance(val, dict):
            _assert_same_structure(val, actual[key], f"{path}/{key}")


# ─────────────────────────────────────────────────────────────────────────────
# CRITICAL INFRASTRUCTURE FIXTURE  (Phase 1 finding D8)
# يعيد توجيه مساري الملفات إلى مجلد مؤقت + يصفّر الكاش العالمي قبل وبعد كل اختبار
# ─────────────────────────────────────────────────────────────────────────────
@pytest.fixture(autouse=True)
def setup_analytics(tmp_path, monkeypatch):
    """
    Real I/O isolation. Without the cache reset, analytics._analytics_cache
    leaks RAM state across tests and every disk assertion becomes meaningless.
    """
    json_path = tmp_path / "analytics.json"
    bak_path = tmp_path / ".sys_ax_backup.dat"

    monkeypatch.setattr(analytics, "get_analytics_file_path", lambda: str(json_path))
    monkeypatch.setattr(analytics, "get_backup_file_path", lambda: str(bak_path))

    # CRITICAL: wipe the in-memory cache so the test reads OUR tmp files.
    analytics._analytics_cache = None
    yield {"json": json_path, "bak": bak_path, "dir": tmp_path}
    # CRITICAL: wipe again so the next test never inherits our RAM state.
    analytics._analytics_cache = None


# ═════════════════════════════════════════════════════════════════════════════
# 1. BOOTSTRAP & SCHEMA INTEGRITY  (GREEN)
# ═════════════════════════════════════════════════════════════════════════════
class TestBootstrapAndSchema:
    def test_fresh_schema_version_is_3(self):
        """A1: catches docstring/version drift — the live schema must be v3."""
        assert analytics.get_default_schema()["_schema_version"] == 3

    def test_init_creates_both_files(self, setup_analytics):
        """init_analytics must materialise BOTH the JSON and the backup on disk."""
        assert not setup_analytics["json"].exists()
        assert not setup_analytics["bak"].exists()
        analytics.init_analytics()
        assert setup_analytics["json"].exists()
        assert setup_analytics["bak"].exists()

    def test_schema_has_every_key(self, setup_analytics):
        """100% structural coverage: every default key must survive init→load."""
        analytics.init_analytics()
        data = analytics.load_analytics()
        _assert_same_structure(analytics.get_default_schema(), data)

    def test_brand_new_user_gets_defaults(self, setup_analytics):
        """No files at all → clean defaults, no crash."""
        data = analytics.load_analytics()
        assert data["_schema_version"] == 3
        assert data["1_app_lifecycle"]["total_launches"] == 0


# ═════════════════════════════════════════════════════════════════════════════
# 2. EXHAUSTIVE KEY COVERAGE — FLAT COUNTERS  (GREEN)
# كل عدّاد مسطّح في المخطط يتم اختباره فعلياً
# ═════════════════════════════════════════════════════════════════════════════
FLAT_KEYS = [
    ("1_app_lifecycle", "total_launches"),
    ("2_search_behavior", "total_links_searched"),
    ("2_search_behavior", "single_video_links"),
    ("2_search_behavior", "playlist_links"),
    ("2_search_behavior", "invalid_links_entered"),
    ("2_search_behavior", "fetch_sizes_clicks"),
    ("2_search_behavior", "videos_fetched_successfully"),
    ("5_conversion_stats", "attempted"),
    ("5_conversion_stats", "completed"),
    ("5_conversion_stats", "failed"),
    ("5_conversion_stats", "canceled"),
    ("5_conversion_stats", "skipped"),
    ("5_conversion_stats", "speed_mode_fast"),
    ("5_conversion_stats", "speed_mode_slow"),
    ("6_resilience_and_errors", "youtube_blocks"),
    ("6_resilience_and_errors", "network_retries"),
    ("6_resilience_and_errors", "data_limit_warnings_shown"),
    ("6_resilience_and_errors", "fetch_failures"),
]


@pytest.mark.parametrize("category,key", FLAT_KEYS)
def test_flat_key_increments_exactly(setup_analytics, category, key):
    """1 + 4 = 5, persisted to disk, no off-by-one and no cross-talk."""
    analytics.init_analytics()
    analytics.increment_stat(category, key)            # +1
    analytics.increment_stat(category, key, amount=4)  # +4
    assert analytics.load_analytics()[category][key] == 5
    assert read_disk(setup_analytics["json"])[category][key] == 5


# ═════════════════════════════════════════════════════════════════════════════
# 3. EXHAUSTIVE KEY COVERAGE — 2-LEVEL (sub_category)  (GREEN)
# ═════════════════════════════════════════════════════════════════════════════
SUB_KEYS = [
    ("1_app_lifecycle", "ui_interactions", "hardware_shortcuts_used"),
    ("1_app_lifecycle", "ui_interactions", "context_menu_used"),
    ("1_app_lifecycle", "support_interactions", "main_contact_btn_clicks"),
    ("1_app_lifecycle", "support_interactions", "whatsapp_clicks"),
    ("1_app_lifecycle", "support_interactions", "linkedin_clicks"),
    ("1_app_lifecycle", "support_interactions", "github_clicks"),
    ("1_app_lifecycle", "support_interactions", "email_clicks"),
    ("1_app_lifecycle", "support_interactions", "open_in_gmail_clicks"),
    ("3_download_stats", "single_videos", "attempted"),
    ("3_download_stats", "single_videos", "completed"),
    ("3_download_stats", "single_videos", "failed"),
    ("3_download_stats", "single_videos", "canceled"),
    ("3_download_stats", "single_videos", "already_exists"),
    ("3_download_stats", "playlists", "attempted"),
    ("3_download_stats", "playlists", "completed"),
    ("3_download_stats", "playlists", "failed"),
    ("3_download_stats", "playlists", "canceled"),
    ("3_download_stats", "playlists", "total_videos_downloaded"),
    ("3_download_stats", "playlists", "total_videos_already_exists"),
    ("3_download_stats", "playlists", "total_videos_failed"),
    ("3_download_stats", "volume", "single_videos_downloaded_mb"),
    ("3_download_stats", "volume", "single_videos_download_time_seconds"),
    ("3_download_stats", "volume", "playlists_downloaded_mb"),
    ("3_download_stats", "volume", "playlists_download_time_seconds"),
    ("3_download_stats", "volume", "total_downloaded_mb"),
    ("3_download_stats", "volume", "total_download_time_seconds"),
    ("5_conversion_stats", "volume", "total_converted_mb"),
    ("5_conversion_stats", "volume", "total_conversion_time_seconds"),
]


@pytest.mark.parametrize("category,sub,key", SUB_KEYS)
def test_sub_key_increments_exactly(setup_analytics, category, sub, key):
    """Two-level keys (clicks, download stats, volume) increment precisely."""
    analytics.init_analytics()
    analytics.increment_stat(category, key, sub_category=sub)            # +1
    analytics.increment_stat(category, key, amount=4, sub_category=sub)  # +4
    assert analytics.load_analytics()[category][sub][key] == 5
    assert read_disk(setup_analytics["json"])[category][sub][key] == 5


# ═════════════════════════════════════════════════════════════════════════════
# 4. EXHAUSTIVE KEY COVERAGE — 3-LEVEL (quality_preferences)  (GREEN)
# ═════════════════════════════════════════════════════════════════════════════
DEEP_KEYS = (
    [("single_videos_exact_resolutions", k) for k in
        ["exact_144p", "exact_240p", "exact_360p", "exact_480p", "exact_720p",
         "exact_1080p", "exact_1440p", "exact_4k", "exact_8k", "exact_16k_plus",
         "audio_only"]]
    + [("playlist_presets", k) for k in
        ["best_quality", "medium", "low", "audio_only"]]
)


@pytest.mark.parametrize("sub,key", DEEP_KEYS)
def test_quality_preference_increments_exactly(setup_analytics, sub, key):
    """Deep 3-level quality counters under quality_preferences increment precisely."""
    analytics.init_analytics()
    analytics.increment_stat("3_download_stats", key, sub_category=sub)
    analytics.increment_stat("3_download_stats", key, amount=2, sub_category=sub)
    val = analytics.load_analytics()["3_download_stats"]["quality_preferences"][sub][key]
    assert val == 3


# ═════════════════════════════════════════════════════════════════════════════
# 5. increment_stat BEHAVIOUR & GUARDS
# ═════════════════════════════════════════════════════════════════════════════
class TestIncrementBehaviour:
    def test_unknown_category_is_silent_noop(self, setup_analytics):
        """Typos must not crash and must not auto-create keys."""
        analytics.init_analytics()
        analytics.increment_stat("NONEXISTENT_CATEGORY", "whatever")
        analytics.increment_stat("6_resilience_and_errors", "ghost_key_xyz")
        data = analytics.load_analytics()
        assert "NONEXISTENT_CATEGORY" not in data
        assert "ghost_key_xyz" not in data["6_resilience_and_errors"]
        assert data["6_resilience_and_errors"]["youtube_blocks"] == 0

    def test_float_amount_accumulates(self, setup_analytics):
        """Float amounts accumulate (volume/time fields are floats)."""
        analytics.init_analytics()
        analytics.increment_stat("3_download_stats", "total_downloaded_mb",
                                 amount=2.5, sub_category="volume")
        analytics.increment_stat("3_download_stats", "total_downloaded_mb",
                                 amount=2.5, sub_category="volume")
        v = analytics.load_analytics()["3_download_stats"]["volume"]["total_downloaded_mb"]
        assert v == pytest.approx(5.0)

    def test_amount_zero_changes_nothing(self, setup_analytics):
        analytics.init_analytics()
        analytics.increment_stat("6_resilience_and_errors", "youtube_blocks", amount=0)
        assert analytics.load_analytics()["6_resilience_and_errors"]["youtube_blocks"] == 0

    @pytest.mark.xfail(strict=False,
                       reason="Phase 1 Bug B5: increment_stat does not guard negative amount → counter can go negative")
    def test_negative_amount_should_not_go_negative(self, setup_analytics):
        """DESIRED: a counter must never be driven below zero."""
        analytics.init_analytics()
        analytics.increment_stat("6_resilience_and_errors", "youtube_blocks", amount=-5)
        val = analytics.load_analytics()["6_resilience_and_errors"]["youtube_blocks"]
        assert val >= 0


# ═════════════════════════════════════════════════════════════════════════════
# 6. NETWORK PROFILE — speeds & speed test  (GREEN + 2 xfail)
# ═════════════════════════════════════════════════════════════════════════════
class TestNetworkProfile:
    def test_download_speed_high_low_tracking(self, setup_analytics):
        analytics.init_analytics()
        analytics.update_speed_stat(50.0)
        s = analytics.load_analytics()["4_network_profile"]["download_speeds"]
        assert s["highest_mbps"] == 50.0 and s["lowest_mbps"] == 50.0

        analytics.update_speed_stat(100.0)   # new high
        s = analytics.load_analytics()["4_network_profile"]["download_speeds"]
        assert s["highest_mbps"] == 100.0 and s["lowest_mbps"] == 50.0

        analytics.update_speed_stat(10.0)    # new low
        s = analytics.load_analytics()["4_network_profile"]["download_speeds"]
        assert s["highest_mbps"] == 100.0 and s["lowest_mbps"] == 10.0

    def test_speed_ignores_zero_and_negative(self, setup_analytics):
        analytics.init_analytics()
        analytics.update_speed_stat(0)
        analytics.update_speed_stat(-12.5)
        s = analytics.load_analytics()["4_network_profile"]["download_speeds"]
        assert s["highest_mbps"] == 0.0 and s["lowest_mbps"] == 0.0

    def test_speedtest_result_tracking(self, setup_analytics):
        """Mirrors the user's real values (25.9 / 27.09)."""
        analytics.init_analytics()
        analytics.record_speedtest_result(25.9)
        st = analytics.load_analytics()["4_network_profile"]["speed_test"]
        assert st["last_result_mbps"] == 25.9
        assert st["highest_mbps"] == 25.9
        assert st["lowest_mbps"] == 25.9
        assert st["last_tested_timestamp"] > 0

        analytics.record_speedtest_result(27.09)  # new high
        st = analytics.load_analytics()["4_network_profile"]["speed_test"]
        assert st["last_result_mbps"] == 27.09
        assert st["highest_mbps"] == 27.09
        assert st["lowest_mbps"] == 25.9

        analytics.record_speedtest_result(10.0)   # new low
        st = analytics.load_analytics()["4_network_profile"]["speed_test"]
        assert st["last_result_mbps"] == 10.0
        assert st["highest_mbps"] == 27.09
        assert st["lowest_mbps"] == 10.0

    @pytest.mark.xfail(strict=False,
                       reason="Phase 1 Bug B2: update_speed_stat has no upper sanity bound → impossible speeds stored")
    def test_giant_speed_should_be_rejected(self, setup_analytics):
        """DESIRED: 1e9 Mbps is physically impossible and must be rejected/clamped."""
        analytics.init_analytics()
        analytics.update_speed_stat(1e9)
        s = analytics.load_analytics()["4_network_profile"]["download_speeds"]
        assert s["highest_mbps"] < 100000

    @pytest.mark.xfail(strict=False,
                       reason="Phase 1 Bug B3: sub-0.005 Mbps rounds to 0.0 and is swallowed by the 'unset' sentinel")
    def test_tiny_real_speed_should_register(self, setup_analytics):
        """DESIRED: a genuine slow speed (0.004) should still register as > 0."""
        analytics.init_analytics()
        analytics.update_speed_stat(0.004)
        s = analytics.load_analytics()["4_network_profile"]["download_speeds"]
        assert s["highest_mbps"] > 0.0


# ═════════════════════════════════════════════════════════════════════════════
# 7. LIFECYCLE — launches, unique days, uptime  (GREEN + 1 xfail)
# ═════════════════════════════════════════════════════════════════════════════
class TestLifecycle:
    def test_app_launch_and_unique_days(self, setup_analytics, monkeypatch):
        """total_launches, first-launch stamps, and the unique-day counter."""
        analytics.init_analytics()
        base = datetime.datetime(2023, 6, 15, 12, 0, 0).timestamp()  # safe noon anchor
        holder = {"t": base}
        monkeypatch.setattr(analytics.time, "time", lambda: holder["t"])

        analytics.record_app_launch()                         # launch #1
        d = analytics.load_analytics()["1_app_lifecycle"]
        assert d["total_launches"] == 1
        assert d["unique_days_active"] == 1
        assert d["first_app_launch_timestamp"] == base
        assert d["first_app_launch_date_str"] != "Unknown"

        holder["t"] = base + 60                               # same calendar day
        analytics.record_app_launch()                         # launch #2
        d = analytics.load_analytics()["1_app_lifecycle"]
        assert d["total_launches"] == 2
        assert d["unique_days_active"] == 1                   # still same day

        holder["t"] = base + 2 * 86400                        # +2 days
        analytics.record_app_launch()                         # launch #3
        d = analytics.load_analytics()["1_app_lifecycle"]
        assert d["total_launches"] == 3
        assert d["unique_days_active"] == 2                   # new day counted

    def test_uptime_positive_session(self, setup_analytics, monkeypatch):
        analytics.init_analytics()
        fixed_now = 5000.0
        monkeypatch.setattr(analytics.time, "time", lambda: fixed_now)
        analytics.record_uptime(fixed_now - 120)              # a 120-second session
        d = analytics.load_analytics()["1_app_lifecycle"]
        assert d["total_uptime_minutes"] == 2.0

    @pytest.mark.xfail(strict=False,
                       reason="Phase 1 Bug B1: record_uptime uses wall-clock → backward clock jump subtracts/goes negative")
    def test_uptime_backward_clock_should_not_go_negative(self, setup_analytics, monkeypatch):
        """DESIRED: a backward clock jump must never make uptime negative."""
        analytics.init_analytics()
        monkeypatch.setattr(analytics.time, "time", lambda: 1000.0)  # 'now' BEFORE start
        analytics.record_uptime(2000.0)                              # start was later
        d = analytics.load_analytics()["1_app_lifecycle"]
        assert d["total_uptime_minutes"] >= 0.0


# ═════════════════════════════════════════════════════════════════════════════
# 8. SYSTEM HARDWARE — async scan + cache gate  (GREEN)
# ═════════════════════════════════════════════════════════════════════════════
class TestSystemHardware:
    def test_scan_runs_when_data_is_stale(self, setup_analytics, monkeypatch):
        """Fresh defaults (cpu=Unknown) must trigger a background scan that fills hardware."""
        analytics.init_analytics()
        monkeypatch.setattr(analytics.time, "sleep", lambda *_: None)     # skip the 5s wait
        monkeypatch.setattr(analytics, "_get_cpu_name", lambda: "TEST-CPU")
        monkeypatch.setattr(analytics, "_get_ram_gb", lambda: "16 GB")
        monkeypatch.setattr(analytics, "_get_gpu_name", lambda: "TEST-GPU")

        analytics.record_system_info()

        # busy-wait for the daemon thread (no time.sleep — it's patched to no-op)
        deadline = time.monotonic() + 5.0
        while time.monotonic() < deadline:
            if analytics.load_analytics()["7_system_hardware"]["cpu_name"] == "TEST-CPU":
                break
        hw = analytics.load_analytics()["7_system_hardware"]
        assert hw["cpu_name"] == "TEST-CPU"
        assert hw["ram_gb"] == "16 GB"
        assert hw["gpu_name"] == "TEST-GPU"
        assert hw["cpu_cores"] == (os.cpu_count() or 0)
        assert hw["last_scan_timestamp"] > 0

    def test_scan_is_skipped_when_fresh(self, setup_analytics, monkeypatch):
        """Cache gate: recent scan + known CPU → do NOT re-scan."""
        data = analytics.get_default_schema()
        data["7_system_hardware"]["cpu_name"] = "CACHED-CPU"
        data["7_system_hardware"]["last_scan_timestamp"] = time.time()  # fresh
        analytics.save_analytics(data)

        monkeypatch.setattr(analytics.time, "sleep", lambda *_: None)
        monkeypatch.setattr(analytics, "_get_cpu_name", lambda: "SHOULD-NOT-APPEAR")
        analytics.record_system_info()

        # brief window; value must stay the cached one
        end = time.monotonic() + 0.5
        while time.monotonic() < end:
            pass
        assert analytics.load_analytics()["7_system_hardware"]["cpu_name"] == "CACHED-CPU"


# ═════════════════════════════════════════════════════════════════════════════
# 9. JSON INTEGRITY & RECOVERY  (GREEN + xfail for the C1 crash)
# ═════════════════════════════════════════════════════════════════════════════
class TestIntegrityAndRecovery:
    def test_zero_byte_file_recovers(self, setup_analytics):
        """0-byte JSON, no backup → clean defaults, no crash."""
        setup_analytics["json"].write_text("", encoding="utf-8")
        analytics._analytics_cache = None
        data = analytics.load_analytics()
        assert data["_schema_version"] == 3

    def test_syntax_error_recovers(self, setup_analytics):
        """Corrupted (invalid) JSON, no backup → defaults, no crash."""
        setup_analytics["json"].write_text("{ this is : not json ", encoding="utf-8")
        analytics._analytics_cache = None
        data = analytics.load_analytics()
        assert data["_schema_version"] == 3

    def test_empty_containers_treated_as_missing(self, setup_analytics):
        """Falsy valid JSON ({} / []) is treated as 'missing' → defaults."""
        setup_analytics["json"].write_text("{}", encoding="utf-8")
        setup_analytics["bak"].write_text("[]", encoding="utf-8")
        analytics._analytics_cache = None
        data = analytics.load_analytics()
        assert data["_schema_version"] == 3

    def test_corrupt_json_restores_from_valid_backup(self, setup_analytics):
        """Corrupt JSON but valid BAK → restore BAK + bump schema_repairs_count."""
        setup_analytics["json"].write_text("{bad", encoding="utf-8")
        bak = analytics.get_default_schema()
        bak["2_search_behavior"]["total_links_searched"] = 33
        setup_analytics["bak"].write_text(json.dumps(bak), encoding="utf-8")
        analytics._analytics_cache = None

        data = analytics.load_analytics()
        assert data["2_search_behavior"]["total_links_searched"] == 33
        assert data["0_data_integrity"]["schema_repairs_count"] == 1

    @pytest.mark.xfail(strict=False,
                       reason="Phase 1 Bug C1: valid-JSON-but-not-a-dict ([..]/42/'x') crashes load_analytics → app refuses to start")
    def test_nondict_json_list_should_not_crash(self, setup_analytics):
        """DESIRED: a JSON array payload must fall back to defaults, not crash."""
        setup_analytics["json"].write_text("[1, 2, 3]", encoding="utf-8")
        analytics._analytics_cache = None
        analytics.init_analytics()  # currently raises AttributeError
        data = analytics.load_analytics()
        assert isinstance(data, dict) and data["_schema_version"] == 3

    @pytest.mark.xfail(strict=False,
                       reason="Phase 1 Bug C1: truthy non-dict in the BACKUP crashes the version check")
    def test_nondict_backup_number_should_not_crash(self, setup_analytics):
        """DESIRED: a corrupt backup containing `42` must not crash recovery."""
        setup_analytics["bak"].write_text("42", encoding="utf-8")
        analytics._analytics_cache = None
        data = analytics.load_analytics()
        assert isinstance(data, dict) and data["_schema_version"] == 3

    @pytest.mark.xfail(strict=False,
                       reason="Phase 1 Bug C2: schema_version as string '3' != int 3 → endless re-migration")
    def test_string_schema_version_should_not_remigrate(self, setup_analytics):
        """DESIRED: '3' (string) should be treated as version 3 (no migration)."""
        d = analytics.get_default_schema()
        d["_schema_version"] = "3"                      # tampered type
        payload = json.dumps(d)
        setup_analytics["json"].write_text(payload, encoding="utf-8")
        setup_analytics["bak"].write_text(payload, encoding="utf-8")
        analytics._analytics_cache = None
        data = analytics.load_analytics()
        assert data["0_data_integrity"]["schema_migrations_count"] == 0


# ═════════════════════════════════════════════════════════════════════════════
# 10. STRICT REPLICA ENGINE  (GREEN)
# محرك النسخة المطابقة: من يكسب عند الاختلاف؟
# ═════════════════════════════════════════════════════════════════════════════
class TestReplicaEngine:
    def test_backup_wins_on_mismatch(self, setup_analytics):
        """JSON ≠ BAK (both valid v3) → BAK is source of truth + repair counted."""
        base = analytics.get_default_schema()
        jv = copy.deepcopy(base); jv["6_resilience_and_errors"]["youtube_blocks"] = 11
        bv = copy.deepcopy(base); bv["6_resilience_and_errors"]["youtube_blocks"] = 99
        setup_analytics["json"].write_text(json.dumps(jv), encoding="utf-8")
        setup_analytics["bak"].write_text(json.dumps(bv), encoding="utf-8")
        analytics._analytics_cache = None

        data = analytics.load_analytics()
        assert data["6_resilience_and_errors"]["youtube_blocks"] == 99
        assert data["0_data_integrity"]["schema_repairs_count"] == 1

    def test_restore_when_json_missing(self, setup_analytics):
        """JSON gone, BAK present → restore from BAK + repair counted + JSON rebuilt."""
        bv = analytics.get_default_schema()
        bv["6_resilience_and_errors"]["fetch_failures"] = 7
        setup_analytics["bak"].write_text(json.dumps(bv), encoding="utf-8")
        analytics._analytics_cache = None

        data = analytics.load_analytics()
        assert data["6_resilience_and_errors"]["fetch_failures"] == 7
        assert data["0_data_integrity"]["schema_repairs_count"] == 1
        assert setup_analytics["json"].exists()

    def test_rebuild_backup_when_missing(self, setup_analytics):
        """BAK gone, JSON present → keep JSON, rebuild BAK, NO repair count bump."""
        jv = analytics.get_default_schema()
        jv["6_resilience_and_errors"]["fetch_failures"] = 5
        setup_analytics["json"].write_text(json.dumps(jv), encoding="utf-8")
        analytics._analytics_cache = None

        data = analytics.load_analytics()
        assert data["6_resilience_and_errors"]["fetch_failures"] == 5
        assert setup_analytics["bak"].exists()
        assert data["0_data_integrity"]["schema_repairs_count"] == 0


# ═════════════════════════════════════════════════════════════════════════════
# 11. ATOMIC WRITE & FAILOVER (real disk, simulated faults)  (GREEN)
# ═════════════════════════════════════════════════════════════════════════════
class TestAtomicWriteAndFailover:
    def test_no_temp_files_remain_after_save(self, setup_analytics):
        """A clean save must leave NO .tmp_* artifacts behind."""
        analytics.init_analytics()
        analytics.increment_stat("6_resilience_and_errors", "youtube_blocks")
        leftover = [p.name for p in setup_analytics["dir"].iterdir()
                    if p.name.startswith(".tmp_")]
        assert leftover == []

    def test_crash_between_bak_and_json_self_heals(self, setup_analytics, monkeypatch):
        """
        Simulate a crash AFTER the backup is written but BEFORE the JSON write.
        Next load must detect the mismatch and recover the newer BAK value.
        """
        analytics.init_analytics()  # baseline: youtube_blocks = 0 in both files
        original = analytics._atomic_write
        flag = {"fail_json": True}

        def patched(path, content):
            if flag["fail_json"] and str(path) == str(setup_analytics["json"]):
                raise OSError("simulated power loss during JSON write")
            return original(path, content)

        monkeypatch.setattr(analytics, "_atomic_write", patched)
        analytics.increment_stat("6_resilience_and_errors", "youtube_blocks", amount=5)

        flag["fail_json"] = False          # 'reboot' — writes work again
        analytics._analytics_cache = None  # cold start after crash
        data = analytics.load_analytics()

        assert data["6_resilience_and_errors"]["youtube_blocks"] == 5   # recovered from BAK
        assert data["0_data_integrity"]["schema_repairs_count"] == 1

    def test_permission_denied_never_crashes(self, setup_analytics, monkeypatch):
        """
        os.replace always denied (antivirus lock). increment_stat must swallow it,
        not crash, leave the file unchanged, and leave NO temp files behind.
        """
        analytics.init_analytics()
        before = read_disk(setup_analytics["json"])
        monkeypatch.setattr(analytics.time, "sleep", lambda *_: None)  # skip retry delay

        def deny(*_a, **_k):
            raise PermissionError("file locked by antivirus")
        monkeypatch.setattr(analytics.os, "replace", deny)

        analytics.increment_stat("6_resilience_and_errors", "youtube_blocks", amount=3)  # must not raise

        assert read_disk(setup_analytics["json"]) == before
        leftover = [p.name for p in setup_analytics["dir"].iterdir()
                    if p.name.startswith(".tmp_")]
        assert leftover == []


# ═════════════════════════════════════════════════════════════════════════════
# 12. CONCURRENCY — RLock under heavy load  (GREEN)
# اختبار الضغط: 20 خيط × 500 عملية = 10000، إثبات عدم فقدان أي تحديث
# ═════════════════════════════════════════════════════════════════════════════
class TestConcurrency:
    def test_rlock_reentrancy_no_deadlock(self, setup_analytics):
        """
        increment_stat holds the lock then calls load+save which re-acquire it.
        With a plain Lock() this deadlocks instantly. Proves RLock re-entrancy.
        """
        analytics.init_analytics()
        done = threading.Event()

        def run():
            analytics.increment_stat("6_resilience_and_errors", "youtube_blocks")
            done.set()

        t = threading.Thread(target=run)
        t.start()
        t.join(timeout=5)
        assert done.is_set(), "DEADLOCK: increment_stat never returned (RLock broken?)"

    def test_stress_20_threads_no_lost_updates(self, setup_analytics):
        """20 threads × 500 increments on ONE key → exactly 10000, on disk too."""
        analytics.init_analytics()
        n_threads, per_thread = 20, 500

        def worker():
            for _ in range(per_thread):
                analytics.increment_stat("6_resilience_and_errors", "network_retries")

        threads = [threading.Thread(target=worker) for _ in range(n_threads)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        expected = n_threads * per_thread  # 10000
        assert analytics.load_analytics()["6_resilience_and_errors"]["network_retries"] == expected
        assert read_disk(setup_analytics["json"])["6_resilience_and_errors"]["network_retries"] == expected

    def test_stress_mixed_keys_stay_independent(self, setup_analytics):
        """Many threads on DIFFERENT keys → each exact, no cross-contamination."""
        analytics.init_analytics()
        targets = [
            ("6_resilience_and_errors", "youtube_blocks"),
            ("2_search_behavior", "total_links_searched"),
            ("5_conversion_stats", "attempted"),
        ]
        n_threads, per_thread = 12, 300

        def worker(cat, key):
            for _ in range(per_thread):
                analytics.increment_stat(cat, key)

        threads = []
        for cat, key in targets:
            for _ in range(n_threads):
                threads.append(threading.Thread(target=worker, args=(cat, key)))
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        data = analytics.load_analytics()
        for cat, key in targets:
            assert data[cat][key] == n_threads * per_thread  # 3600 each

    def test_file_always_valid_json_under_concurrent_mixed_ops(self, setup_analytics):
        """Concurrent increments + speed updates + launches → file never corrupts."""
        analytics.init_analytics()

        def inc():
            for _ in range(200):
                analytics.increment_stat("6_resilience_and_errors", "fetch_failures")

        def spd():
            for i in range(200):
                analytics.update_speed_stat(float(i % 90) + 1.0)

        def launch():
            for _ in range(50):
                analytics.record_app_launch()

        threads = ([threading.Thread(target=inc) for _ in range(6)]
                   + [threading.Thread(target=spd) for _ in range(6)]
                   + [threading.Thread(target=launch) for _ in range(3)])
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        # The on-disk file must still be parseable valid JSON (never half-written).
        disk = read_disk(setup_analytics["json"])
        assert disk["6_resilience_and_errors"]["fetch_failures"] == 6 * 200
        assert disk["1_app_lifecycle"]["total_launches"] == 3 * 50


# ═════════════════════════════════════════════════════════════════════════════
# 13. BOUNDARIES & UNICODE  (GREEN)
# ═════════════════════════════════════════════════════════════════════════════
class TestBoundaries:
    def test_volume_extreme_values(self, setup_analytics):
        """0, 1 byte (1e-9 MB), and a huge value must store without crashing."""
        analytics.init_analytics()
        analytics.increment_stat("3_download_stats", "total_downloaded_mb",
                                 amount=0.0, sub_category="volume")
        analytics.increment_stat("3_download_stats", "total_downloaded_mb",
                                 amount=1e-9, sub_category="volume")
        analytics.increment_stat("3_download_stats", "total_downloaded_mb",
                                 amount=1e12, sub_category="volume")
        v = analytics.load_analytics()["3_download_stats"]["volume"]["total_downloaded_mb"]
        assert v == pytest.approx(1e12, rel=1e-6)

    def test_unicode_arabic_value_roundtrips(self, setup_analytics):
        """Arabic + emoji in a string field must survive save→disk→load intact."""
        data = analytics.get_default_schema()
        data["7_system_hardware"]["cpu_name"] = "معالج عربي 🚀 Intel®"
        analytics.save_analytics(data)
        analytics._analytics_cache = None
        loaded = analytics.load_analytics()
        assert loaded["7_system_hardware"]["cpu_name"] == "معالج عربي 🚀 Intel®"
