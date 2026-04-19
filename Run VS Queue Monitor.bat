@echo off
REM Delegates to vsqm.cmd (short name for Win+R / PATH). See README.
call "%~dp0vsqm.cmd" %*
exit /b %ERRORLEVEL%
