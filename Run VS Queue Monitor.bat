@echo off
REM Double-click this file to start the app (uses .venv if present).
cd /d "%~dp0"
if exist ".venv\Scripts\python.exe" (
  "%~dp0.venv\Scripts\python.exe" "%~dp0monitor.py" %*
  exit /b %ERRORLEVEL%
)
where py >nul 2>&1 && (
  py -3 "%~dp0monitor.py" %*
  exit /b %ERRORLEVEL%
)
python "%~dp0monitor.py" %*
exit /b %ERRORLEVEL%
