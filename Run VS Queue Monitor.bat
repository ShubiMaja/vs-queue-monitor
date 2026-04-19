@echo off
REM Delegates to vs-queue-monitor.cmd. See README.
call "%~dp0vs-queue-monitor.cmd" %*
exit /b %ERRORLEVEL%
