@echo off
chcp 65001 >nul
setlocal EnableExtensions EnableDelayedExpansion

title Audion DevOps Tools - Build Portable Env PS

set "PS_EXE="
set "PS1_FILE=%~dpn0.ps1"
set "ASSUME_YES=0"
set "NO_PAUSE=0"
set "PS_ARGS="

:parse_args
if "%~1"=="" goto args_done
if /I "%~1"=="/Y" set "ASSUME_YES=1" & shift & goto parse_args
if /I "%~1"=="--yes" set "ASSUME_YES=1" & shift & goto parse_args
if /I "%~1"=="-Yes" set "ASSUME_YES=1" & shift & goto parse_args
if /I "%~1"=="/NOPAUSE" set "NO_PAUSE=1" & shift & goto parse_args
if /I "%~1"=="--no-pause" set "NO_PAUSE=1" & shift & goto parse_args
if /I "%~1"=="-NoPause" set "NO_PAUSE=1" & shift & goto parse_args
if /I "%~1"=="/?" goto usage
if /I "%~1"=="-h" goto usage
if /I "%~1"=="--help" goto usage
echo [ERROR] Unknown argument: %~1
echo.
goto usage

:args_done
if /I "%AUDION_UNATTENDED%"=="1" set "ASSUME_YES=1"
if /I "%AUDION_NO_PAUSE%"=="1" set "NO_PAUSE=1"
if "%ASSUME_YES%"=="1" set "PS_ARGS=-Yes"

if exist "%~dp0..\system_core\powershell\pwsh.exe" set "PS_EXE=%~dp0..\system_core\powershell\pwsh.exe"
if not defined PS_EXE where pwsh.exe >nul 2>nul && set "PS_EXE=pwsh.exe"
if not defined PS_EXE where powershell.exe >nul 2>nul && set "PS_EXE=powershell.exe"

if not defined PS_EXE (
    echo [ERROR] PowerShell was not found.
    echo [INFO] Expected portable path:
    echo %~dp0..\system_core\powershell\pwsh.exe
    if not defined AUDION_NO_PAUSE pause
    exit /b 1
)

"%PS_EXE%" -NoLogo -NoProfile -ExecutionPolicy Bypass -File "%PS1_FILE%" %PS_ARGS%
set "RC=%errorlevel%"

echo.
if "%RC%"=="0" (
    echo [OK] Build_Portable_Env.ps1 finished successfully.
) else (
    echo [ERROR] Build_Portable_Env.ps1 finished with exit code %RC%.
)

if not "%NO_PAUSE%"=="1" pause
exit /b %RC%

:usage
echo Usage:
echo   Build_Portable_Env.cmd [/Y] [/NOPAUSE]
echo.
echo Options:
echo   /Y              Rebuild generated runtime/wheelhouse without asking.
echo   /NOPAUSE        Do not wait for a key at the end.
echo.
if not "%NO_PAUSE%"=="1" pause
exit /b 0
