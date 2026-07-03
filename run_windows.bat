@echo off
REM -----------------------------------------------------------------------
REM Launcher for Windows — creates venv, installs deps, runs the scraper
REM -----------------------------------------------------------------------
cd /d "%~dp0"

if not exist venv\ (
    echo 🔧 Creating virtual environment ...
    python -m venv venv
)

call venv\Scripts\activate.bat
pip install -q -r requirements.txt

echo.
python main.py
pause
