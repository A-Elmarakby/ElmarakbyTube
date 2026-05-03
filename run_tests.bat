@echo off
REM --- Fix Console Encoding ---
chcp 65001 >nul

REM ===========================================================================
REM  ElmarakbyTube Downloader - Master Test Runner
REM  Run this file from the PROJECT ROOT (the folder containing main.py)
REM ===========================================================================

REM --- Activate Virtual Environment automatically ---
if exist "venv\Scripts\activate.bat" (
    call venv\Scripts\activate.bat
)

echo.
echo ======================================================
echo       ElmarakbyTube - Master Test Suite Runner        
echo ======================================================
echo.

REM --- Verify Python is on PATH ---
python --version >nul 2>&1
IF ERRORLEVEL 1 (
    echo [ERROR] Python not found in PATH. Install Python and retry.
    pause & exit /b 1
)

REM --- Auto-install test dependencies if pytest is missing ---
python -m pytest --version >nul 2>&1
IF ERRORLEVEL 1 (
    echo [INFO] pytest not found. Installing test dependencies...
    pip install -r requirements_test.txt
    IF ERRORLEVEL 1 (
        echo [ERROR] Failed to install dependencies.
        pause & exit /b 1
    )
)

REM --- Ensure reports directory exists ---
if not exist "tests\reports" mkdir tests\reports

REM --- Generate Dynamic Filename (Timestamp + Auto-Version) ---
for /f "tokens=2 delims==" %%I in ('wmic os get localdatetime /value') do set dt=%%I
set YYYY=%dt:~0,4%
set MM=%dt:~4,2%
set DD=%dt:~6,2%
set HH=%dt:~8,2%
set MIN=%dt:~10,2%
set TIMESTAMP=%YYYY%-%MM%-%DD%_%HH%-%MIN%

set /a VERSION=1
for /f %%A in ('dir /b /a-d "tests\reports\baseline_metrics_*.json" 2^>nul ^| find /c /v ""') do set /a VERSION=%%A + 1
set REPORT_FILE=baseline_metrics_%TIMESTAMP%_v%VERSION%.json

REM --- Detect whether pytest-benchmark is installed ---
set HAS_BENCHMARK=0
python -c "import pytest_benchmark" >nul 2>&1
IF NOT ERRORLEVEL 1 set HAS_BENCHMARK=1

echo +----------------------------------------------------------+
echo ^|  Choose a test mode:                                     ^|
echo ^|                                                          ^|
echo ^|  1 = Full suite        (all test folders)                ^|
echo ^|  2 = Unit tests        (Logic + Assets + State +        ^|
echo ^|                         Layout + Popups)                 ^|
echo ^|  3 = State / threading tests only                        ^|
echo ^|  4 = UI state tests only  (test_ui.py)                   ^|
echo ^|  5 = Benchmarks only      - outputs JSON report          ^|
echo ^|  6 = Coverage report      - opens HTML in browser        ^|
echo ^|  7 = FULL + Coverage      (recommended before refactor)  ^|
echo ^|  8 = Layout + Popup unit tests  (isolated, verbose)      ^|
echo +----------------------------------------------------------+
echo.
set /p CHOICE="Enter number (1-8): "

if "%CHOICE%"=="1" goto full_suite
if "%CHOICE%"=="2" goto unit_all
if "%CHOICE%"=="3" goto state_only
if "%CHOICE%"=="4" goto ui_only
if "%CHOICE%"=="5" goto benchmarks_only
if "%CHOICE%"=="6" goto coverage_only
if "%CHOICE%"=="7" goto full_with_coverage
if "%CHOICE%"=="8" goto layout_popup_only
goto invalid

REM -------------------------------------------------------------------------
:full_suite
echo.
echo [RUN] Full suite (all test folders) ...
IF "%HAS_BENCHMARK%"=="1" (
    python -m pytest tests\ -v --tb=short -s --benchmark-json=tests/reports/%REPORT_FILE%
) ELSE (
    python -m pytest tests\ -v --tb=short -s -p no:benchmark
)
goto done

REM -------------------------------------------------------------------------
:unit_all
echo.
echo [RUN] All unit tests (Logic + Assets + State + Layout + Popups) ...
python -m pytest tests/unit/ -v --tb=short -p no:benchmark
goto done

REM -------------------------------------------------------------------------
:state_only
echo.
echo [RUN] Threading and state tests ...
python -m pytest tests/unit/test_state.py -v --tb=short -p no:benchmark
goto done

REM -------------------------------------------------------------------------
:ui_only
echo.
echo [RUN] UI state tests (test_ui.py) ...
python -m pytest tests/ui/test_ui.py -v --tb=short -p no:benchmark
goto done

REM -------------------------------------------------------------------------
:benchmarks_only
echo.
IF "%HAS_BENCHMARK%"=="0" (
    echo [WARNING] pytest-benchmark is not installed.
    echo           Run:  pip install pytest-benchmark
    echo           Then re-run this script and choose option 5 again.
    goto done
)
echo [RUN] Performance benchmarks ...
python -m pytest tests/performance/test_benchmark.py -v -s --tb=short --benchmark-json=tests/reports/%REPORT_FILE%
echo.
echo [DONE] Benchmark JSON saved to:
echo        tests\reports\%REPORT_FILE%
goto done

REM -------------------------------------------------------------------------
:coverage_only
echo.
echo [RUN] Generating full coverage report (all tests) ...
python -m pytest tests/ -p no:benchmark --tb=short
echo.
echo [DONE] Coverage HTML: tests\reports\coverage_html\index.html
start tests\reports\coverage_html\index.html
goto done

REM -------------------------------------------------------------------------
:full_with_coverage
echo.
echo [RUN] Full suite + coverage + benchmark baseline ...
IF "%HAS_BENCHMARK%"=="1" (
    python -m pytest tests/ -v --tb=short -s --benchmark-json=tests/reports/%REPORT_FILE%
) ELSE (
    echo [INFO] pytest-benchmark not installed - skipping benchmark JSON.
    python -m pytest tests/ -v --tb=short -s -p no:benchmark
)
echo.
echo [DONE] All outputs saved:
echo   Coverage HTML  : tests\reports\coverage_html\index.html
IF "%HAS_BENCHMARK%"=="1" (
    echo   Benchmark JSON : tests\reports\%REPORT_FILE%
)
start tests\reports\coverage_html\index.html
goto done

REM -------------------------------------------------------------------------
:layout_popup_only
echo.
echo [RUN] Layout + Popup unit tests (isolated, verbose, stdout visible) ...
python -m pytest tests/unit/test_layout.py tests/unit/test_popups.py -v -s --tb=long -p no:benchmark
echo.
echo [TIP] To see only failures, re-run with:
echo       python -m pytest tests/unit/test_layout.py tests/unit/test_popups.py -v --tb=short
goto done

REM -------------------------------------------------------------------------
:invalid
echo.
echo [ERROR] Invalid choice. Re-run the script and enter a number from 1 to 8.
goto done

REM -------------------------------------------------------------------------
:done
echo.
echo ==========================================================
echo  Done.
echo ==========================================================
pause