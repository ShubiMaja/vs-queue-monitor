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
set "VSQM_BOOTSTRAP_FILE=%TEMP%\vs-queue-monitor-bootstrap.py"
set "VSQM_PYTHON="
set "VSQM_EXIT=0"

where py >nul 2>&1 && set "VSQM_PYTHON=py -3"
if not defined VSQM_PYTHON (
  where python >nul 2>&1 && set "VSQM_PYTHON=python"
)

if not defined VSQM_PYTHON goto :no_python

echo.
echo Downloading VS Queue Monitor bootstrap...
curl -fsSL "%VS_QUEUE_MONITOR_BOOTSTRAP_URL%" -o "%VSQM_BOOTSTRAP_FILE%"
if errorlevel 1 (
  echo.
  echo Bootstrap download failed.
  echo URL: %VS_QUEUE_MONITOR_BOOTSTRAP_URL%
  set "VSQM_EXIT=1"
  goto :finish
)

echo Running bootstrap...
call %VSQM_PYTHON% "%VSQM_BOOTSTRAP_FILE%"
set "VSQM_EXIT=%ERRORLEVEL%"
if exist "%VSQM_BOOTSTRAP_FILE%" del /q "%VSQM_BOOTSTRAP_FILE%" >nul 2>&1
goto :finish

:no_python
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
set "VSQM_EXIT=1"

:finish
echo.
if "%VSQM_EXIT%"=="0" (
  echo VS Queue Monitor finished with exit code 0.
) else (
  echo VS Queue Monitor ended with exit code %VSQM_EXIT%.
)
echo Press any key to close this window.
pause >nul
exit /b %VSQM_EXIT%
