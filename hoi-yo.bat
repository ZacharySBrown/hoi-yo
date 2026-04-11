@echo off
title HOI-YO - AI War Room
echo.
echo   _           _
echo  ^| ^|__   ___ (_)      _   _  ___
echo  ^| '_ \ / _ \^| ^|_____^| ^| ^| ^|/ _ \
echo  ^| ^| ^| ^| (_) ^| ^|_____^| ^|_^| ^| (_) ^|
echo  ^|_^| ^|_^|\___/^|_^|      \__,_^|\___/
echo.
echo   Starting AI War Room...
echo.

cd /d "%~dp0"

REM Check for Python
python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python 3.11+ is required but not found.
    echo Install Python from https://python.org and try again.
    pause
    exit /b 1
)

REM Create venv if needed
if not exist .venv (
    echo First-time setup: creating Python environment...
    python -m venv .venv
    echo Installing dependencies...
    .venv\Scripts\pip install -e . -q
    echo Setup complete!
    echo.
)

REM Activate and run
echo Opening HOI-YO in your browser...
echo Press Ctrl+C to stop.
echo.
.venv\Scripts\python -m src.cli dashboard
