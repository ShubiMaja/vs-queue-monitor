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
python "%~dp0monitor.py" %*
exit /b %ERRORLEVEL%
