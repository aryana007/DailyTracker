@echo off
:: ========================================================
:: Daily Routine & Food Log - One-Click Launcher
:: ========================================================
setlocal
cd /d "%~dp0"

:: 1. Try direct pythonw from user's installed Python 3.14
if exist "%LOCALAPPDATA%\Python\pythoncore-3.14-64\pythonw.exe" (
    start "" "%LOCALAPPDATA%\Python\pythoncore-3.14-64\pythonw.exe" "daily_tracker.py"
    exit /b 0
)

:: 2. Try pythonw in PATH (silent GUI execution)
where pythonw >nul 2>&1
if %errorlevel% equ 0 (
    start "" pythonw "daily_tracker.py"
    exit /b 0
)

:: 3. Try standard python in PATH
where python >nul 2>&1
if %errorlevel% equ 0 (
    start "" python "daily_tracker.py"
    exit /b 0
)

:: 4. Try Windows Python Launcher (py.exe)
where py >nul 2>&1
if %errorlevel% equ 0 (
    start "" py -3 "daily_tracker.py"
    exit /b 0
)

echo.
echo [ERROR] Python was not found on your system!
echo Please make sure Python is installed.
echo.
pause
