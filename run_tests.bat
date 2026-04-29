@echo off
REM ── Fix Console Encoding for Box Characters ──────────────────────────────
chcp 65001 >nul

REM ═══════════════════════════════════════════════════════════════════════════
REM  ElmarakbyTube Downloader — Master Test Runner
REM  Run this from the PROJECT ROOT (the folder containing main.py)
REM ═══════════════════════════════════════════════════════════════════════════

REM ── Activate Virtual Environment automatically ───────────────────────────
if exist "venv\Scripts\activate.bat" (
    call venv\Scripts\activate.bat
)

echo.
echo ╔══════════════════════════════════════════════════════╗
echo ║     ElmarakbyTube — Baseline Test Suite Runner       ║
echo ╚══════════════════════════════════════════════════════╝
echo.

REM ── Verify Python is on PATH ─────────────────────────────────────────────
python --version >nul 2>&1
IF ERRORLEVEL 1 (
    echo [ERROR] Python not found in PATH. Install Python and retry.
    pause & exit /b 1
)

REM ── Auto-install test dependencies if pytest is missing ───────────────────
python -m pytest --version >nul 2>&1
IF ERRORLEVEL 1 (
    echo [INFO] pytest not found. Installing test dependencies...
    pip install -r requirements_test.txt
    IF ERRORLEVEL 1 (
        echo [ERROR] Failed to install dependencies.
        pause & exit /b 1
    )
)

REM ── Ensure reports directory exists ──────────────────────────────────────
if not exist "tests\reports" mkdir tests\reports

echo ┌─────────────────────────────────────────────────────────┐
echo │  Choose a test mode:                                    │
echo │                                                         │
echo │  1 = Full suite  (all test folders)                     │
REM Run all unit tests including logic, state, and assets
echo │  2 = Unit tests (Logic + Assets + State)               │
echo │  3 = State / threading tests only                       │
echo │  4 = UI state tests only                                │
echo │  5 = Benchmarks only  → outputs JSON + CSV             │
echo │  6 = Coverage report  → opens HTML in browser          │
echo │  7 = FULL + Coverage  (Recommended before Refactor)    │
└─────────────────────────────────────────────────────────┘
echo.
set /p CHOICE="Enter number (1-7): "

if "%CHOICE%"=="1" goto full_suite
if "%CHOICE%"=="2" goto logic_only
if "%CHOICE%"=="3" goto state_only
if "%CHOICE%"=="4" goto ui_only
if "%CHOICE%"=="5" goto benchmarks_only
if "%CHOICE%"=="6" goto coverage_only
if "%CHOICE%"=="7" goto full_with_coverage
goto invalid

:full_suite
echo.
echo [RUN] Full test suite (logic + state + ui + benchmarks)...
python -m pytest tests\ -v --tb=short -s
goto done

:logic_only
echo.
echo [RUN] Running all unit tests (Logic, State, and Assets)...
python -m pytest tests/unit/ -v --tb=short
goto done

:state_only
echo.
echo [RUN] Threading and state tests...
python -m pytest tests/unit/test_state.py -v --tb=short
goto done

:ui_only
echo.
echo [RUN] UI state tests...
python -m pytest tests/ui/test_ui.py -v --tb=short
goto done

:benchmarks_only
echo.
echo [RUN] Performance benchmarks...
python -m pytest tests/performance/test_benchmark.py -v -s --tb=short --benchmark-json=tests/reports/baseline_metrics.json
echo.
echo [DONE] Baseline data saved to:
echo        tests\reports\baseline_metrics.json
goto done

:coverage_only
echo.
echo [RUN] Generating coverage report...
python -m pytest tests/ ^
    --cov=main ^
    --cov=config ^
    --cov=messages ^
    --cov-report=html:tests/reports/coverage_html ^
    --cov-report=term-missing
echo.
echo [DONE] Coverage HTML: tests\reports\coverage_html\index.html
start tests\reports\coverage_html\index.html
goto done

:full_with_coverage
echo.
echo [RUN] Full suite + coverage + performance report...
python -m pytest tests/ ^
    -v ^
    --tb=short ^
    -s ^
    --cov=main ^
    --cov=config ^
    --cov=messages ^
    --cov-report=html:tests/reports/coverage_html ^
    --cov-report=term-missing ^
    --benchmark-json=tests/reports/baseline_metrics.json
echo.
echo [DONE] All outputs saved:
echo   Coverage HTML  : tests\reports\coverage_html\index.html
echo   Benchmark JSON : tests\reports\baseline_metrics.json
start tests\reports\coverage_html\index.html
goto done

:invalid
echo [ERROR] Invalid choice. Re-run the script and enter 1-7.
goto done

:done
echo.
echo ═══════════════════════════════════════════════════════
echo  Done.
echo ═══════════════════════════════════════════════════════
pause