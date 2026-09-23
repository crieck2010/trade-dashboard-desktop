@echo off
REM One-command Windows build for TradeDashboardDesktop.
REM Run this on your Windows PC (native .exe requires a Windows build host).
REM Produces dist\TradeDashboardDesktop.exe, then build the installer with Inno Setup.

setlocal
cd /d "%~dp0"

python --version >nul 2>&1
if errorlevel 1 (
    echo Python 3.10+ is required: https://www.python.org/downloads/
    exit /b 1
)

echo Installing build tooling...
python -m pip install --upgrade pip pyinstaller

echo Building single-file executable...
python build.py
if errorlevel 1 (
    echo Build failed.
    exit /b 1
)

echo.
echo Done: dist\TradeDashboardDesktop.exe
echo Next: open installer.iss in Inno Setup and compile the installer.
endlocal
