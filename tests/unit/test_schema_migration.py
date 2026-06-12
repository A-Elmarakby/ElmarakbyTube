"""
test_schema_migration.py — Enterprise-grade tests for the analytics schema
migration engine (migrate vs. reset on _schema_version change).
==========================================================================

Covers three layers:
  1. _is_type_compatible  — the defensive type guard for leaf values
  2. _migrate_schema      — the recursive deep-merge engine
  3. load_analytics()     — the real end-to-end flow with the config switch,
                            disk persistence, and the migration counters.

Design notes:
  - Every test points the analytics file paths at a pytest tmp dir so the real
    user's analytics.json is never touched.
  - The in-memory cache (_analytics_cache) is reset before each test so each
    case reads from "disk" (the tmp files) like a fresh app launch.
"""

import os
import json
import copy
import threading
import pytest

import config
import core.analytics as a


# ─────────────────────────────────────────────────────────────────────────────
# Helpers / fixtures
# ─────────────────────────────────────────────────────────────────────────────
@pytest.fixture
def iso(tmp_path, monkeypatch):
    """Isolate analytics to a temp dir and reset the RAM cache.

    Returns a small helper namespace with the two file paths, a writer that
    drops the same payload into both files, and a reader for the on-disk JSON.
    """
    jpath = str(tmp_path / "analytics.json")
    bpath = str(tmp_path / ".sys_ax_backup.dat")

    monkeypatch.setattr(a, "get_analytics_file_path", lambda: jpath)
    monkeypatch.setattr(a, "get_backup_file_path", lambda: bpath)

    # Fresh launch: nothing cached in RAM.
    a._analytics_cache = None

    class _Iso:
        json_path = jpath
        bak_path = bpath

        @staticmethod
        def write_both(payload):
            for p in (jpath, bpath):
                with open(p, "w", encoding="utf-8") as f:
                    json.dump(payload, f)

        @staticmethod
        def read_disk_json():
            with open(jpath, "r", encoding="utf-8") as f:
                return json.load(f)

        @staticmethod
        def reset_cache():
            a._analytics_cache = None

    yield _Iso()
    a._analytics_cache = None


def make_old_file(version=2):
    """A realistic 'previous version' file: the current schema shape but with
    an older version number, the migration counters removed (they didn't exist
    in v2), some accumulated counters, and one obsolete key."""
    old = a.get_default_schema()
    old["_schema_version"] = version
    # v2 did not have the migration counters yet.
    old["0_data_integrity"].pop("schema_migrations_count", None)
    old["0_data_integrity"].pop("last_migration_timestamp", None)
    # The user has real history we must not lose.
    old["1_app_lifecycle"]["total_launches"] = 137
    old["2_search_behavior"]["total_links_searched"] = 88
    # A field that no longer exists in the new schema.
    old["2_search_behavior"]["obsolete_legacy_counter"] = 999
    return old


CUR_VERSION = a.get_default_schema()["_schema_version"]


# ─────────────────────────────────────────────────────────────────────────────
# 1. _is_type_compatible — the leaf type guard
# ─────────────────────────────────────────────────────────────────────────────
class TestTypeCompatible:
    def test_int_to_int(self):
        assert a._is_type_compatible(5, 0) is True

    def test_int_to_float_is_numeric_compatible(self):
        assert a._is_type_compatible(5, 0.0) is True
        assert a._is_type_compatible(5.0, 0) is True

    def test_string_into_counter_rejected(self):
        assert a._is_type_compatible("999", 0) is False

    def test_bool_not_accepted_as_counter(self):
        # bool is a subclass of int; must be rejected for numeric fields.
        assert a._is_type_compatible(True, 0) is False

    def test_bool_field_keeps_bool(self):
        assert a._is_type_compatible(False, True) is True

    def test_int_not_accepted_into_bool_field(self):
        assert a._is_type_compatible(1, True) is False

    def test_string_to_string(self):
        assert a._is_type_compatible("hello", "Unknown") is True

    def test_int_into_string_field_rejected(self):
        assert a._is_type_compatible(5, "Unknown") is False

    def test_dict_into_dict(self):
        assert a._is_type_compatible({}, {}) is True

    def test_scalar_into_dict_rejected(self):
        assert a._is_type_compatible(5, {}) is False

    def test_none_default_accepts_anything(self):
        assert a._is_type_compatible("whatever", None) is True
        assert a._is_type_compatible(123, None) is True


# ─────────────────────────────────────────────────────────────────────────────
# 2. _migrate_schema — recursive deep merge
# ─────────────────────────────────────────────────────────────────────────────
class TestMigrateSchema:
    def test_new_key_gets_default(self):
        default = {"a": 1, "b": 2}
        saved = {"a": 50}
        out = a._migrate_schema(saved, default)
        assert out == {"a": 50, "b": 2}

    def test_obsolete_key_dropped(self):
        default = {"a": 1}
        saved = {"a": 50, "ghost": 999}
        out = a._migrate_schema(saved, default)
        assert "ghost" not in out
        assert out == {"a": 50}

    def test_existing_compatible_value_kept(self):
        default = {"count": 0}
        saved = {"count": 42}
        assert a._migrate_schema(saved, default)["count"] == 42

    def test_nested_dict_recursion(self):
        default = {"lvl1": {"keep": 0, "added": 7}}
        saved = {"lvl1": {"keep": 99}}
        out = a._migrate_schema(saved, default)
        assert out == {"lvl1": {"keep": 99, "added": 7}}

    def test_three_levels_deep(self):
        default = {"a": {"b": {"c": 0, "d": 1}}}
        saved = {"a": {"b": {"c": 555}}}
        out = a._migrate_schema(saved, default)
        assert out["a"]["b"]["c"] == 555
        assert out["a"]["b"]["d"] == 1

    def test_type_mismatch_falls_back_to_default(self):
        default = {"count": 0}
        saved = {"count": "corrupted"}
        assert a._migrate_schema(saved, default)["count"] == 0

    def test_scalar_where_dict_expected_uses_default(self):
        default = {"section": {"x": 0}}
        saved = {"section": 12345}  # user/file corruption
        out = a._migrate_schema(saved, default)
        assert out["section"] == {"x": 0}

    def test_dict_where_scalar_expected_uses_default(self):
        default = {"count": 0}
        saved = {"count": {"unexpected": "dict"}}
        assert a._migrate_schema(saved, default)["count"] == 0

    def test_saved_not_a_dict_returns_default_copy(self):
        default = {"a": 1}
        assert a._migrate_schema(None, default) == {"a": 1}
        assert a._migrate_schema("garbage", default) == {"a": 1}
        assert a._migrate_schema([1, 2, 3], default) == {"a": 1}

    def test_empty_saved_yields_full_defaults(self):
        default = {"a": 1, "b": {"c": 2}}
        assert a._migrate_schema({}, default) == {"a": 1, "b": {"c": 2}}

    def test_result_is_independent_copy(self):
        default = {"nested": {"v": 0}}
        saved = {}
        out = a._migrate_schema(saved, default)
        out["nested"]["v"] = 12345
        # Mutating the migrated result must not corrupt the default template.
        assert default["nested"]["v"] == 0

    def test_real_schema_round_trip_preserves_and_extends(self):
        default = a.get_default_schema()
        old = make_old_file(version=2)
        out = a._migrate_schema(old, default)
        # Preserved
        assert out["1_app_lifecycle"]["total_launches"] == 137
        assert out["2_search_behavior"]["total_links_searched"] == 88
        # New fields present at defaults
        assert out["0_data_integrity"]["schema_migrations_count"] == 0
        assert out["0_data_integrity"]["last_migration_timestamp"] == 0.0
        # Obsolete field dropped
        assert "obsolete_legacy_counter" not in out["2_search_behavior"]
        # Structure complete (same top-level keys as the template)
        assert set(out.keys()) == set(default.keys())


# ─────────────────────────────────────────────────────────────────────────────
# 3. load_analytics() — end-to-end with the config switch + disk persistence
# ─────────────────────────────────────────────────────────────────────────────
class TestLoadMigrateMode:
    def test_migrate_keeps_data_and_bumps_version(self, iso, monkeypatch):
        monkeypatch.setattr(config, "ANALYTICS_SCHEMA_CHANGE_MODE", "migrate")
        iso.write_both(make_old_file(version=2))

        data = a.load_analytics()

        assert data["_schema_version"] == CUR_VERSION          # never the OLD version
        assert data["1_app_lifecycle"]["total_launches"] == 137  # data preserved
        assert data["2_search_behavior"]["total_links_searched"] == 88
        assert "obsolete_legacy_counter" not in data["2_search_behavior"]
        assert data["0_data_integrity"]["schema_migrations_count"] == 1
        assert data["0_data_integrity"]["last_migration_timestamp"] > 0

    def test_migration_persisted_to_disk(self, iso, monkeypatch):
        monkeypatch.setattr(config, "ANALYTICS_SCHEMA_CHANGE_MODE", "migrate")
        iso.write_both(make_old_file(version=2))

        a.load_analytics()  # triggers migrate + save

        on_disk = iso.read_disk_json()
        assert on_disk["_schema_version"] == CUR_VERSION
        assert on_disk["1_app_lifecycle"]["total_launches"] == 137
        assert on_disk["0_data_integrity"]["schema_migrations_count"] == 1

    def test_new_field_present_after_migrate(self, iso, monkeypatch):
        monkeypatch.setattr(config, "ANALYTICS_SCHEMA_CHANGE_MODE", "migrate")
        old = make_old_file(version=2)
        # remove a key that exists in the new schema entirely
        old["1_app_lifecycle"].pop("total_uptime_minutes", None)
        iso.write_both(old)

        data = a.load_analytics()
        assert "total_uptime_minutes" in data["1_app_lifecycle"]
        assert data["1_app_lifecycle"]["total_uptime_minutes"] == 0.0

    def test_tampered_type_repaired_then_increment_works(self, iso, monkeypatch):
        monkeypatch.setattr(config, "ANALYTICS_SCHEMA_CHANGE_MODE", "migrate")
        old = make_old_file(version=2)
        old["1_app_lifecycle"]["total_launches"] = "HACKED"  # wrong type
        iso.write_both(old)

        data = a.load_analytics()
        # defensive: reset to numeric default
        assert data["1_app_lifecycle"]["total_launches"] == 0
        # and the counter is usable again
        a.increment_stat("1_app_lifecycle", "total_launches", amount=3)
        assert a.load_analytics()["1_app_lifecycle"]["total_launches"] == 3

    def test_migration_count_accumulates(self, iso, monkeypatch):
        monkeypatch.setattr(config, "ANALYTICS_SCHEMA_CHANGE_MODE", "migrate")
        old = make_old_file(version=2)
        # pretend this user already migrated 5 times before
        old["0_data_integrity"]["schema_migrations_count"] = 5
        iso.write_both(old)

        data = a.load_analytics()
        assert data["0_data_integrity"]["schema_migrations_count"] == 6

    def test_unknown_mode_defaults_to_migrate(self, iso, monkeypatch):
        monkeypatch.setattr(config, "ANALYTICS_SCHEMA_CHANGE_MODE", "banana")
        iso.write_both(make_old_file(version=2))

        data = a.load_analytics()
        assert data["1_app_lifecycle"]["total_launches"] == 137  # preserved
        assert data["_schema_version"] == CUR_VERSION

    def test_mode_is_case_and_space_insensitive(self, iso, monkeypatch):
        monkeypatch.setattr(config, "ANALYTICS_SCHEMA_CHANGE_MODE", "  RESET  ")
        iso.write_both(make_old_file(version=2))

        data = a.load_analytics()
        # treated as reset -> wiped
        assert data["1_app_lifecycle"]["total_launches"] == 0


class TestLoadResetMode:
    def test_reset_wipes_everything(self, iso, monkeypatch):
        monkeypatch.setattr(config, "ANALYTICS_SCHEMA_CHANGE_MODE", "reset")
        iso.write_both(make_old_file(version=2))

        data = a.load_analytics()
        assert data["_schema_version"] == CUR_VERSION
        assert data["1_app_lifecycle"]["total_launches"] == 0     # wiped
        assert data["2_search_behavior"]["total_links_searched"] == 0
        assert data["0_data_integrity"]["schema_migrations_count"] == 0  # not a migration

    def test_reset_persisted_to_disk(self, iso, monkeypatch):
        monkeypatch.setattr(config, "ANALYTICS_SCHEMA_CHANGE_MODE", "reset")
        iso.write_both(make_old_file(version=2))

        a.load_analytics()
        on_disk = iso.read_disk_json()
        assert on_disk["_schema_version"] == CUR_VERSION
        assert on_disk["1_app_lifecycle"]["total_launches"] == 0


class TestNoVersionChange:
    def test_same_version_loads_as_is_no_migration(self, iso, monkeypatch):
        monkeypatch.setattr(config, "ANALYTICS_SCHEMA_CHANGE_MODE", "migrate")
        current = a.get_default_schema()
        current["1_app_lifecycle"]["total_launches"] = 70
        iso.write_both(current)

        data = a.load_analytics()
        assert data["1_app_lifecycle"]["total_launches"] == 70
        # No migration happened -> counter stays 0
        assert data["0_data_integrity"]["schema_migrations_count"] == 0

    def test_brand_new_user_gets_fresh_defaults(self, iso, monkeypatch):
        monkeypatch.setattr(config, "ANALYTICS_SCHEMA_CHANGE_MODE", "migrate")
        # No files written at all.
        data = a.load_analytics()
        assert data["_schema_version"] == CUR_VERSION
        assert data["1_app_lifecycle"]["total_launches"] == 0
        assert data["0_data_integrity"]["schema_migrations_count"] == 0


# ─────────────────────────────────────────────────────────────────────────────
# 4. Stress / concurrency — file must survive parallel writers post-migration
# ─────────────────────────────────────────────────────────────────────────────
class TestConcurrencyAfterMigration:
    def test_parallel_increments_are_consistent(self, iso, monkeypatch):
        monkeypatch.setattr(config, "ANALYTICS_SCHEMA_CHANGE_MODE", "migrate")
        iso.write_both(make_old_file(version=2))
        a.load_analytics()  # migrate first

        N_THREADS = 10
        PER_THREAD = 50

        def worker():
            for _ in range(PER_THREAD):
                a.increment_stat("1_app_lifecycle", "total_launches")

        threads = [threading.Thread(target=worker) for _ in range(N_THREADS)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        final = a.load_analytics()["1_app_lifecycle"]["total_launches"]
        # started at 137 (preserved), plus all increments, none lost
        assert final == 137 + (N_THREADS * PER_THREAD)
