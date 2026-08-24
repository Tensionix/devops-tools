@echo off
chcp 65001 >nul
setlocal EnableExtensions EnableDelayedExpansion

title Audion DevOps Tools - NVIDIA Driver Install Lock

set "SCRIPT_NAME=%~nx0"
set "ORIGINAL_ARGS=%*"
for %%I in ("%~dp0..") do set "BASE_DIR=%%~fI"
if "%BASE_DIR:~-1%"=="\" set "BASE_DIR=%BASE_DIR:~0,-1%"
cd /d "%BASE_DIR%"

set "CORE_DIR=%BASE_DIR%\system_core"
set "PS_SCRIPT=%CORE_DIR%\windows_driver_guard\Block-NVIDIA-Driver-Updates.ps1"
set "PS_ENGINE="
set "PS_EXTRA="
set "NO_PAUSE="

:ARGS
if "%~1"=="" goto ARGS_DONE
if /I "%~1"=="--no-pause" set "NO_PAUSE=1" & shift & goto ARGS
if /I "%~1"=="/nopause" set "NO_PAUSE=1" & shift & goto ARGS
if /I "%~1"=="--include-compatible" set "PS_EXTRA=!PS_EXTRA! -IncludeCompatibleIds" & shift & goto ARGS
if /I "%~1"=="--retroactive" set "PS_EXTRA=!PS_EXTRA! -Retroactive" & shift & goto ARGS
if /I "%~1"=="--help" goto HELP
if /I "%~1"=="/?" goto HELP
echo [ERROR] Unknown argument: %~1
set "EXIT_CODE=2"
goto FINISH

:ARGS_DONE
if not exist "%PS_SCRIPT%" (
  echo [ERROR] Script not found:
  echo %PS_SCRIPT%
  set "EXIT_CODE=2"
  goto FINISH
)

call :SELECT_POWERSHELL

net session >nul 2>&1
if errorlevel 1 (
  echo Requesting Administrator rights...
  set "AUDION_ELEVATE_TARGET=%~f0"
  set "AUDION_ELEVATE_ARGS=%ORIGINAL_ARGS%"
  set "AUDION_ELEVATE_CWD=%BASE_DIR%"
  powershell.exe -NoLogo -NoProfile -ExecutionPolicy Bypass -Command "try { $p = Start-Process -FilePath $env:AUDION_ELEVATE_TARGET -ArgumentList $env:AUDION_ELEVATE_ARGS -WorkingDirectory $env:AUDION_ELEVATE_CWD -Verb RunAs -Wait -PassThru -ErrorAction Stop; exit $p.ExitCode } catch { Write-Host $_.Exception.Message; exit 1223 }"
  set "EXIT_CODE=%ERRORLEVEL%"
  goto FINISH
)

echo ======================================================================
echo   NVIDIA DRIVER INSTALL LOCK
echo ======================================================================
echo Root:        %BASE_DIR%
echo PowerShell:  %PS_ENGINE%
echo Script:      %PS_SCRIPT%
echo Extra:       !PS_EXTRA!
echo.

"%PS_ENGINE%" -NoLogo -NoProfile -ExecutionPolicy Bypass -File "%PS_SCRIPT%" !PS_EXTRA!
set "EXIT_CODE=%ERRORLEVEL%"
goto FINISH

:HELP
echo Usage:
echo   %SCRIPT_NAME% [--no-pause] [--include-compatible] [--retroactive]
echo.
echo Default mode blocks present NVIDIA PCI Hardware IDs without retroactive removal.
echo Use --retroactive only when you intentionally want Windows to apply the block to already installed matching devices.
set "EXIT_CODE=0"
goto FINISH

:FINISH
echo.
echo Exit code: %EXIT_CODE%
if not defined NO_PAUSE (
  echo Press any key to close.
  if not defined AUDION_NO_PAUSE pause >nul
)
exit /b %EXIT_CODE%

:SELECT_POWERSHELL
if exist "%CORE_DIR%\powershell\pwsh.exe" set "PS_ENGINE=%CORE_DIR%\powershell\pwsh.exe" & exit /b 0
where pwsh.exe >nul 2>nul
if not errorlevel 1 set "PS_ENGINE=pwsh.exe" & exit /b 0
where powershell.exe >nul 2>nul
if not errorlevel 1 set "PS_ENGINE=powershell.exe" & exit /b 0
set "PS_ENGINE=%SystemRoot%\System32\WindowsPowerShell\v1.0\powershell.exe"
exit /b 0
