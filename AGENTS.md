# ElmarakbyTube — Developer Reference

## Project Summary

Desktop app for downloading YouTube videos and playlists (MP4 / MP3 conversion). Built for Windows with Python 3.14+, CustomTkinter GUI, yt-dlp, and FFmpeg. Target audience: Arabic-speaking end users.

**Current Branch:** `feature/logging-and-stats`  
**Status:** Under development — no real users yet, no migration code needed.

---

## File Map

```
main.py                — App entry point, UI↔core bridge, all threading, Analytics V3 Final Judge
config.py              — All constants (colors, paths, thread counts, quality presets, network)
messages.py            — All Arabic UI strings (never hardcode strings elsewhere)

core/
  analytics.py         — Analytics engine: JSON persistence, atomic writes, RLock thread safety
  downloader.py        — yt-dlp wrapper with progress callbacks
  fetcher.py           — YouTube metadata extraction, quality/size detection
  converter.py         — FFmpeg wrapper (fast = copy stream, slow = re-encode)
  network_tester.py    — Background 24h speed test against Cloudflare
  utils.py             — Logging setup, file helpers, apply_bidi() for Arabic text RTL

ui/
  layout.py            — Main window construction, video row management, toolbar
  popups.py            — All dialog windows (errors, welcome, contact, 1GB warning, etc.)
  state.py             — Shared mutable state container (widget refs, locks, events, flags)
```

---

## Architecture

### Threading Model

- **Main thread** — Tkinter event loop only; all UI writes must go through `app.after(0, lambda: ...)`
- **fetch_video_data** — Runs in a daemon thread; calls `app.after()` to push results to UI
- **fetch_all_sizes_worker** — Pool of `MAX_THREADS` (5) threads fetch video sizes concurrently
- **download_worker** (Session Manager) — Outer thread; owns the Final Judge logic
- **_download_process** (Content Worker) — Inner thread; calls yt-dlp, reports progress via callbacks

### Analytics V3 — "Final Judge" Pattern

The single most important architectural rule: **never count the same event in both the Content Worker and the Session Manager.**

```
Session Manager (download_worker)
  │  sets _session_crashed = True  (crash protection)
  │
  ├─► spawns Content Worker (_download_process)
  │     │  downloads files, calls callbacks
  │     └─► signals completion event
  │
  └─► Final Judge evaluates outcome AFTER Content Worker exits:
        - Check yt-dlp outcome + file presence
        - Increment exactly ONE of: completed / failed / canceled / already_exists
        - Set _session_crashed = False on clean exit
```

**Crash protection:** `_session_crashed = True` is set before any download work begins. It is set `False` only when the session completes cleanly. If the process dies, the flag stays `True` and the next launch records the crash.

### State and Locks

- `state.operation_lock` — `threading.Lock()` (plain, NOT re-entrant), prevents overlapping fetch/download/convert operations. Analytics thread-safety is a *separate* lock: `_analytics_lock = threading.RLock()` inside `core/analytics.py`, acquired for every `increment_stat` / `save_analytics`.
- `state.fetch_event` — `threading.Event()`, set to signal fetch cancellation
- `state.video_rows` — list of dicts, one per video row widget
- `state.active_download_category` — NOT declared in `state.py`; set dynamically on the `state` module before download so Force-Quit crash recovery knows what was running (read with a `getattr(state, 'active_download_category', 'single_videos')` fallback)

---

## Analytics Engine (`core/analytics.py`)

### Storage

| File | Path | Purpose |
|------|------|---------|
| `analytics.json` | `%AppData%\ElmarakbyTube\analytics.json` | Human-readable, indented |
| `.sys_ax_backup.dat` | `~\.sys_ax_backup.dat` | Compact backup |

Writes use temp file + `os.replace()` (atomic, crash-safe). In-memory cache uses `copy.deepcopy()`.

### Schema Sections

```
1_integrity_and_system    — schema_version, crash_count, last_launch
2_search_behavior         — links entered, single vs playlist, invalid links, fetch_failures
3_download_stats          — single_videos / playlists (attempted, completed, failed, canceled,
                             already_exists, speed, volume, quality breakdown)
4_network_stats           — speed test results
5_conversion_stats        — attempted, completed, failed, canceled, skipped,
                             speed_mode_fast/slow, volume (total_converted_mb, total_conversion_time_seconds)
6_resilience_and_errors   — youtube_blocks, fetch_failures, data_limit_warnings_shown
7_hardware_and_system     — CPU, RAM, GPU, OS (cached 180 days)
```

### Schema Equation

```
attempted = completed + failed + canceled + already_exists   (downloads)
attempted = completed + failed + canceled                    (conversions)
```

### Key Rule: `increment_stat` silent failure

If a key does not exist in the schema, `increment_stat()` silently does nothing — no error, no log. **Always verify the key exists in `get_default_schema()` before adding a new call site.**

To add a sub-category value (e.g. volume stats):
```python
increment_stat("5_conversion_stats", "total_converted_mb",
               amount=size_mb, sub_category="volume")
```

---

## Quality Lock Pattern

`_current_session_quality_counted` prevents counting the same quality selection twice in one session. It is reset by `reset_quality_flag()` (defined in `main.py`, passed into `layout.py` via `callbacks_dict`). The flag resets when the user changes quality in the dropdown — `on_quality_change()` in `layout.py` must call `callbacks['reset_quality_flag']()`.

---

## Config Constants (key ones)

| Constant | Default | Purpose |
|----------|---------|---------|
| `MAX_THREADS` | 5 | Concurrent size-fetch threads |
| `MAX_CONSECUTIVE_ERRORS` | 10 | Auto-stop fetch after N YouTube errors in a row |
| `FETCH_RETRIES` | 3 | Retry count for metadata fetch |
| `DOWNLOAD_RETRIES` | 5 | Retry count for mid-download drops |
| `SNAP_THRESHOLD` | 0.10 | ±10% quality snapping tolerance |
| `DATA_WARNING_LIMIT_THRESHOLD_GB` | 1.0 | Trigger 1GB popup |
| `NET_TEST_INTERVAL_SECONDS` | 86400 | Re-run speed test every 24h |
| `SYSTEM_INFO_CACHE_DAYS` | 180 | Hardware scan cache (~6 months) |

---

## Playlist Speed / Time Tracking (Intentional Design Decision)

Single-video downloads track `time_taken`, `avg_speed_mbps`, and contribute to `single_videos_downloaded_mb` / `single_videos_download_time_seconds`. **Playlist sessions do NOT feed the speed calculation.** Speed data (`download_speeds`) is sourced only from single-video downloads + the Cloudflare speed test.

**However**, playlist downloads DO track per-video volume time in `playlists_download_time_seconds`. This is safe because `video_start_time` resets per video in the loop — inter-video gaps are NOT included. Only yt-dlp init overhead per video is included (same overhead that exists in single-video tracking).

`playlists_download_time_seconds` is for data-volume reference only. Never use it to derive speed.

The volume section in `3_download_stats`:
```
single_videos_downloaded_mb / single_videos_download_time_seconds × 8  →  Mbps (matches download_speeds)
playlists_downloaded_mb / playlists_download_time_seconds              →  NOT a valid speed metric
```

---

## Development Setup

```powershell
python -m venv venv
venv\Scripts\Activate.ps1
pip install customtkinter yt-dlp Pillow
# Install FFmpeg and add to PATH
python main.py
```

## Testing

```powershell
.\run_tests.bat          # Full suite
pytest tests/ -v         # Direct
pytest tests/unit/ -v    # Unit only
```

---

## Common Pitfalls

1. **Double-counting** — Never increment a stat in both Content Worker and Session Manager.
2. **Schema key missing** — `increment_stat()` silently no-ops on unknown keys; verify schema first.
3. **UI from background thread** — Always use `app.after(0, lambda: ...)` for any widget update.
4. **Quality lock not reset** — After quality dropdown change, call `reset_quality_flag()` or the next session won't count quality stats.
5. **Analytics file stale after schema change** — If `get_default_schema()` adds new keys, delete `analytics.json` and `.sys_ax_backup.dat` so the new schema is written from scratch (acceptable since there are no real users yet).
6. **Playlist is_playlist detection** — Derive from `len(state.video_rows) > 1`, not from UI combo state.
