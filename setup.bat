@echo off
setlocal

echo.
echo  =====================================================
echo   Disney World Dining Reservation Monitor — Setup
echo  =====================================================
echo.

:: ── 1. Check Python ──────────────────────────────────────────────────────────
where python >nul 2>&1
if errorlevel 1 (
    echo  ERROR: Python is not installed or not on PATH.
    echo  Download it from https://www.python.org/downloads/
    echo  Make sure to check "Add Python to PATH" during install.
    pause
    exit /b 1
)

for /f "tokens=2 delims= " %%v in ('python --version 2^>^&1') do set PYVER=%%v
echo  Python found: %PYVER%

:: ── 2. Create virtual environment ────────────────────────────────────────────
if not exist ".venv" (
    echo.
    echo  Creating virtual environment...
    python -m venv .venv
    if errorlevel 1 (
        echo  ERROR: Failed to create virtual environment.
        pause
        exit /b 1
    )
    echo  Virtual environment created.
) else (
    echo  Virtual environment already exists, skipping creation.
)

:: ── 3. Install dependencies ───────────────────────────────────────────────────
echo.
echo  Installing Python dependencies...
call .venv\Scripts\pip install --upgrade pip --quiet
call .venv\Scripts\pip install -r requirements.txt
if errorlevel 1 (
    echo  ERROR: pip install failed.
    pause
    exit /b 1
)
echo  Dependencies installed.

:: ── 4. Install Playwright browser ────────────────────────────────────────────
echo.
echo  Installing Playwright browser (this may take a minute)...
call .venv\Scripts\python -m playwright install chromium
if errorlevel 1 (
    echo  ERROR: Playwright browser install failed.
    pause
    exit /b 1
)
echo  Playwright browser installed.

:: ── 5. Copy .env if not present ───────────────────────────────────────────────
if not exist ".env" (
    echo.
    echo  Copying .env.example to .env ...
    copy .env.example .env >nul
    echo  Created .env  ^<^<^< EDIT THIS FILE with your Disney credentials ^>^>^>
) else (
    echo.
    echo  .env already exists, skipping copy.
)

:: ── 6. Done ───────────────────────────────────────────────────────────────────
echo.
echo  =====================================================
echo   Setup complete!
echo  =====================================================
echo.
echo  Next steps:
echo    1. Edit .env and fill in your MyDisney credentials
echo    2. Run the agent:
echo.
echo       .venv\Scripts\python main.py
echo.
echo  Or for a one-time check:
echo.
echo       .venv\Scripts\python main.py --check-once --restaurant "be our guest" --date 2026-06-15 --party 2
echo.
pause
endlocal
