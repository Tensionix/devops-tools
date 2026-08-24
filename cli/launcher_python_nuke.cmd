@echo off
chcp 65001 >nul
setlocal EnableExtensions

title Audion DevOps Tools - Python Nuke

for %%I in ("%~dp0..") do set "BASE_DIR=%%~fI"
if "%BASE_DIR:~-1%"=="\" set "BASE_DIR=%BASE_DIR:~0,-1%"
cd /d "%BASE_DIR%"

set "NUKE_CMD=%BASE_DIR%\tools\python_nuke\Nuke.cmd"
if not exist "%NUKE_CMD%" (
  echo [ERROR] Python Nuke launcher was not found:
  echo   %NUKE_CMD%
  if not defined AUDION_NO_PAUSE pause
  exit /b 1
)

call "%NUKE_CMD%"
exit /b %ERRORLEVEL%
