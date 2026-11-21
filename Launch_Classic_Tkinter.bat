@echo off
setlocal
cd /d "%~dp0"
if exist "%LOCALAPPDATA%\Python\pythoncore-3.14-64\pythonw.exe" (
    start "" "%LOCALAPPDATA%\Python\pythoncore-3.14-64\pythonw.exe" "daily_tracker_classic.py"
    exit /b 0
)
start "" pythonw "daily_tracker_classic.py"
