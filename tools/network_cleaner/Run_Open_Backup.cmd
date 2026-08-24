@echo off
setlocal EnableExtensions
cd /d "%~dp0"
set "BACKUP=%~dp0backup"
if not exist "%BACKUP%" mkdir "%BACKUP%"
start "" explorer.exe "%BACKUP%"
exit /b 0
