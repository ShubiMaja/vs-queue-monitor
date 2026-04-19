@echo off
REM Short launcher name for Windows Run (Win+R) and PATH — same behavior as Run VS Queue Monitor.bat
cd /d "%~dp0"
if exist ".venv\Scripts\python.exe" (
  "%~dp0.venv\Scripts\python.exe" "%~dp0monitor.py" %*
  exit /b %ERRORLEVEL%
)
where py >nul 2>&1 && (
  py -3 "%~dp0monitor.py" %*
  exit /b %ERRORLEVEL%
)
where python >nul 2>&1 && (
  python "%~dp0monitor.py" %*
  exit /b %ERRORLEVEL%
)
echo.
echo Python is not installed or not on your PATH.
echo Install Python 3.10+ from https://www.python.org/downloads/windows/
echo Guide: https://docs.python.org/3/using/windows.html
echo During setup, enable "Add python.exe to PATH", then run this again.
echo.
start "" "https://www.python.org/downloads/windows/"
pause
exit /b 1
