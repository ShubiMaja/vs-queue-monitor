@echo off
REM One-line Windows bootstrap: clone (if needed), venv, pip, run monitor.py.
REM Requires Python 3.10+ on PATH as "py" or "python". See README (Win+R flow).
REM Prefer Downloads when it already exists (do not create it); else user profile.
setlocal
cd /d "%USERPROFILE%\Downloads" 2>nul
if errorlevel 1 cd /d "%USERPROFILE%"
if not defined VS_QUEUE_MONITOR_BOOTSTRAP_URL (
  set "VS_QUEUE_MONITOR_BOOTSTRAP_URL=https://raw.githubusercontent.com/ShubiMaja/vs-queue-monitor/main/bootstrap.py"
)

where py >nul 2>&1 && (
  curl -fsSL "%VS_QUEUE_MONITOR_BOOTSTRAP_URL%" | py -3 -
  exit /b %ERRORLEVEL%
)
where python >nul 2>&1 && (
  curl -fsSL "%VS_QUEUE_MONITOR_BOOTSTRAP_URL%" | python -
  exit /b %ERRORLEVEL%
)

echo.
echo Python is not installed or not on your PATH.
echo.
echo Install Python 3.10 or newer for Windows, then run this file again.
echo   https://www.python.org/downloads/windows/
echo.
echo During setup, enable "Add python.exe to PATH" (or add Python manually later).
echo Full guide: https://docs.python.org/3/using/windows.html
echo.
start "" "https://www.python.org/downloads/windows/"
pause
exit /b 1
