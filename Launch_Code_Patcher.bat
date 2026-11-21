@echo off
:: ========================================================
:: Python Code Patcher - One-Click Launcher
:: ========================================================
setlocal
cd /d "%~dp0"

if exist "%LOCALAPPDATA%\Python\pythoncore-3.14-64\pythonw.exe" (
    start "" "%LOCALAPPDATA%\Python\pythoncore-3.14-64\pythonw.exe" "code_patcher.py"
    exit /b 0
)

where pythonw >nul 2>&1
if %errorlevel% equ 0 (
    start "" pythonw "code_patcher.py"
    exit /b 0
)

start "" python "code_patcher.py"
