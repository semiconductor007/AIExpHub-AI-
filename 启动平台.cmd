@echo off
chcp 65001 >nul
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\manage-local.ps1" -Action start
set "AIEXPHUB_EXIT=%ERRORLEVEL%"
if not "%AIEXPHUB_EXIT%"=="0" pause
exit /b %AIEXPHUB_EXIT%
