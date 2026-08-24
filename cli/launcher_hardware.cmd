@echo off
chcp 65001 >nul
setlocal EnableExtensions EnableDelayedExpansion

title Audion DevOps Tools - Hardware / Driver Guard

for %%I in ("%~dp0..") do set "BASE_DIR=%%~fI"
if "%BASE_DIR:~-1%"=="\" set "BASE_DIR=%BASE_DIR:~0,-1%"
cd /d "%BASE_DIR%"

set "CORE_DIR=%BASE_DIR%\system_core"
set "PS_ENGINE="
set "PS_SCRIPT="
set "PS_EXTRA="

if /I "%~1"=="--elevated-action" (
  call :RUN_ACTION "%~2"
  if not defined AUDION_NO_PAUSE pause
  exit /b %ERRORLEVEL%
)

:MAIN
cls
echo ======================================================================
echo   AUDION DEVOPS TOOLS - HARDWARE / DRIVER GUARD
echo ======================================================================
echo Root: %BASE_DIR%
echo.
echo [1] Check driver protection status
echo [2] Block Windows Update driver delivery
echo [3] Unblock Windows Update driver delivery
echo [4] Export installed third-party drivers
echo [5] Restore newest exported driver backup
echo [6] Block NVIDIA driver installs
echo [7] Unblock NVIDIA driver installs
echo [8] Check custom HWID restrictions
echo [9] Block custom HWID driver installs
echo [A] Unblock custom HWID driver installs
echo [B] Repair driver rank by HWID
echo [C] NVIDIA HDMI/DP audio status
echo [D] Disable NVIDIA HDMI/DP audio devices
echo [E] Enable NVIDIA HDMI/DP audio devices
echo [F] Policy-block NVIDIA HDMI/DP audio
echo [G] Unblock NVIDIA HDMI/DP audio policy
echo [H] Open driver backups
echo [I] Open NVIDIA audio output
echo [J] Windows driver/firmware audit
echo [0] Exit
echo.
choice /C 123456789ABCDEFGHIJ0 /N /M "Select: "
if errorlevel 20 exit /b 0
if errorlevel 19 goto DRIVER_FIRMWARE_AUDIT
if errorlevel 18 goto OPEN_NVIDIA_OUTPUT
if errorlevel 17 goto OPEN_DRIVER_BACKUPS
if errorlevel 16 goto NVIDIA_AUDIO_UNBLOCK_POLICY
if errorlevel 15 goto NVIDIA_AUDIO_BLOCK_POLICY
if errorlevel 14 goto NVIDIA_AUDIO_ENABLE
if errorlevel 13 goto NVIDIA_AUDIO_DISABLE
if errorlevel 12 goto NVIDIA_AUDIO_STATUS
if errorlevel 11 goto HWID_RANK_REPAIR
if errorlevel 10 goto HWID_UNBLOCK
if errorlevel 9 goto HWID_BLOCK
if errorlevel 8 goto HWID_STATUS
if errorlevel 7 goto NVIDIA_UNBLOCK
if errorlevel 6 goto NVIDIA_BLOCK
if errorlevel 5 goto DRIVER_RESTORE_NEWEST
if errorlevel 4 goto DRIVER_EXPORT
if errorlevel 3 goto DRIVER_UNBLOCK_ALL
if errorlevel 2 goto DRIVER_BLOCK_ALL
if errorlevel 1 goto DRIVER_STATUS
goto MAIN

:DRIVER_STATUS
call :SET_SCRIPT "windows_driver_guard\Show-Driver-Block-Status.ps1"
call :RUN_PS1
if not defined AUDION_NO_PAUSE pause
goto MAIN

:DRIVER_BLOCK_ALL
call :RUN_ADMIN_ACTION block_all
goto MAIN

:DRIVER_UNBLOCK_ALL
call :RUN_ADMIN_ACTION unblock_all
goto MAIN

:DRIVER_EXPORT
call :RUN_ADMIN_ACTION export_drivers
goto MAIN

:DRIVER_RESTORE_NEWEST
call :RUN_ADMIN_ACTION restore_drivers
goto MAIN

:NVIDIA_BLOCK
call :RUN_ADMIN_ACTION block_nvidia
goto MAIN

:NVIDIA_UNBLOCK
call :RUN_ADMIN_ACTION unblock_nvidia
goto MAIN

:HWID_STATUS
call :SET_SCRIPT "windows_driver_guard\Set-HardwareId-DriverInstallRestriction.ps1"
call :PROMPT_HWIDS_OPTIONAL
if defined HWID_LIST (
  set "PS_EXTRA=-Status -HardwareIdList ^"!HWID_LIST!^""
) else (
  set "PS_EXTRA=-Status"
)
call :RUN_PS1
if not defined AUDION_NO_PAUSE pause
goto MAIN

:HWID_BLOCK
call :RUN_ADMIN_ACTION block_hwid
goto MAIN

:HWID_UNBLOCK
call :RUN_ADMIN_ACTION unblock_hwid
goto MAIN

:HWID_RANK_REPAIR
call :RUN_ADMIN_ACTION repair_rank_hwid
goto MAIN

:NVIDIA_AUDIO_STATUS
call :SET_SCRIPT "nvidia_audio\Status-NvidiaHdmiDpAudio.ps1"
call :RUN_PS1
if not defined AUDION_NO_PAUSE pause
goto MAIN

:NVIDIA_AUDIO_DISABLE
call :RUN_ADMIN_ACTION nvidia_audio_disable
goto MAIN

:NVIDIA_AUDIO_ENABLE
call :RUN_ADMIN_ACTION nvidia_audio_enable
goto MAIN

:NVIDIA_AUDIO_BLOCK_POLICY
call :RUN_ADMIN_ACTION nvidia_audio_block
goto MAIN

:NVIDIA_AUDIO_UNBLOCK_POLICY
call :RUN_ADMIN_ACTION nvidia_audio_unblock
goto MAIN

:OPEN_DRIVER_BACKUPS
if not exist "%BASE_DIR%\backup\driver_guard" mkdir "%BASE_DIR%\backup\driver_guard" >nul 2>nul
start "" explorer "%BASE_DIR%\backup\driver_guard"
goto MAIN

:OPEN_NVIDIA_OUTPUT
if not exist "%BASE_DIR%\output\nvidia_audio" mkdir "%BASE_DIR%\output\nvidia_audio" >nul 2>nul
start "" explorer "%BASE_DIR%\output\nvidia_audio"
goto MAIN

:DRIVER_FIRMWARE_AUDIT
set "PS_SCRIPT=%CORE_DIR%\diagnostics\Invoke-WindowsDriverFirmwareAudit.ps1"
if not exist "%BASE_DIR%\logs" mkdir "%BASE_DIR%\logs" >nul 2>nul
call :RESOLVE_PWSH
echo PowerShell: %PS_ENGINE%
echo Script: %PS_SCRIPT%
echo Output: %BASE_DIR%\logs
echo.
"%PS_ENGINE%" -NoLogo -NoProfile -ExecutionPolicy Bypass -File "%PS_SCRIPT%" -OutputDir "%BASE_DIR%\logs" -Json -Csv -OpenReport
set "RC=%ERRORLEVEL%"
echo.
echo Exit code: %RC%
if not defined AUDION_NO_PAUSE pause
goto MAIN

:RUN_ADMIN_ACTION
set "ACTION=%~1"
net session >nul 2>nul
if "%ERRORLEVEL%"=="0" (
  call :RUN_ACTION "%ACTION%"
  if not defined AUDION_NO_PAUSE pause
  exit /b %ERRORLEVEL%
)
echo Requesting Administrator rights for: %ACTION%
powershell.exe -NoLogo -NoProfile -ExecutionPolicy Bypass -Command "Start-Process -FilePath '%~f0' -ArgumentList '--elevated-action','%ACTION%' -WorkingDirectory '%BASE_DIR%' -Verb RunAs"
exit /b 0

:RUN_ACTION
set "ACTION=%~1"
set "PS_EXTRA="
if /I "%ACTION%"=="block_all" call :SET_SCRIPT "windows_driver_guard\Block-All-WU-Driver-Updates.ps1" & goto ACTION_RUN
if /I "%ACTION%"=="unblock_all" call :SET_SCRIPT "windows_driver_guard\Unblock-All-WU-Driver-Updates.ps1" & goto ACTION_RUN
if /I "%ACTION%"=="export_drivers" call :SET_SCRIPT "windows_driver_guard\Export-Installed-Drivers.ps1" & goto ACTION_RUN
if /I "%ACTION%"=="restore_drivers" call :SET_SCRIPT "windows_driver_guard\Restore-Exported-Drivers.ps1" & set "PS_EXTRA=-NoPrompt" & goto ACTION_RUN
if /I "%ACTION%"=="block_nvidia" call :SET_SCRIPT "windows_driver_guard\Block-NVIDIA-Driver-Updates.ps1" & goto ACTION_RUN
if /I "%ACTION%"=="unblock_nvidia" call :SET_SCRIPT "windows_driver_guard\Unblock-NVIDIA-Driver-Updates.ps1" & goto ACTION_RUN
if /I "%ACTION%"=="block_hwid" goto ACTION_BLOCK_HWID
if /I "%ACTION%"=="unblock_hwid" goto ACTION_UNBLOCK_HWID
if /I "%ACTION%"=="repair_rank_hwid" goto ACTION_REPAIR_RANK_HWID
if /I "%ACTION%"=="nvidia_audio_disable" call :SET_SCRIPT "nvidia_audio\Disable-NvidiaHdmiDpAudio.ps1" & goto ACTION_RUN
if /I "%ACTION%"=="nvidia_audio_enable" call :SET_SCRIPT "nvidia_audio\Enable-NvidiaHdmiDpAudio.ps1" & goto ACTION_RUN
if /I "%ACTION%"=="nvidia_audio_block" call :SET_SCRIPT "nvidia_audio\Block-NvidiaHdmiDpAudioPolicy.ps1" & goto ACTION_RUN
if /I "%ACTION%"=="nvidia_audio_unblock" call :SET_SCRIPT "nvidia_audio\Unblock-NvidiaHdmiDpAudioPolicy.ps1" & goto ACTION_RUN
echo [ERROR] Unknown action: %ACTION%
exit /b 2

:ACTION_BLOCK_HWID
call :SET_SCRIPT "windows_driver_guard\Set-HardwareId-DriverInstallRestriction.ps1"
call :PROMPT_HWIDS_REQUIRED
if errorlevel 1 exit /b 1
set "PS_EXTRA=-HardwareIdList ^"!HWID_LIST!^""
goto ACTION_RUN

:ACTION_UNBLOCK_HWID
call :SET_SCRIPT "windows_driver_guard\Set-HardwareId-DriverInstallRestriction.ps1"
call :PROMPT_HWIDS_REQUIRED
if errorlevel 1 exit /b 1
set "PS_EXTRA=-Unblock -HardwareIdList ^"!HWID_LIST!^""
goto ACTION_RUN

:ACTION_REPAIR_RANK_HWID
call :SET_SCRIPT "windows_driver_guard\Repair-DriverRank-ByHardwareId.ps1"
call :PROMPT_DRIVER_RANK_REPAIR_ARGS
if errorlevel 1 exit /b 1
goto ACTION_RUN

:ACTION_RUN
call :RUN_PS1
exit /b %ERRORLEVEL%

:SET_SCRIPT
set "PS_SCRIPT=%CORE_DIR%\%~1"
exit /b 0

:PROMPT_HWIDS_REQUIRED
set "HWID_LIST="
echo.
echo Enter Hardware ID(s). Separate multiple IDs with comma or semicolon.
echo Example: PCI\VEN_8086^&DEV_46A8^&SUBSYS_22E717AA
echo Press Enter to use built-in cache: Intel Iris Xe / VEN_8086 DEV_46A8
set /p "HWID_LIST=HWID: "
if not defined HWID_LIST (
  set "HWID_LIST=PCI\VEN_8086&DEV_46A8&SUBSYS_22E717AA"
)
exit /b 0

:PROMPT_HWIDS_OPTIONAL
set "HWID_LIST="
echo.
echo Enter Hardware ID(s), or press Enter to use the built-in cache.
echo Example: PCI\VEN_8086^&DEV_46A8^&SUBSYS_22E717AA
echo Press Enter to use built-in cache: Intel Iris Xe / VEN_8086 DEV_46A8
set /p "HWID_LIST=HWID: "
if not defined HWID_LIST (
  set "HWID_LIST=PCI\VEN_8086&DEV_46A8&SUBSYS_22E717AA"
)
exit /b 0

:PROMPT_DRIVER_RANK_REPAIR_ARGS
call :PROMPT_HWIDS_REQUIRED
if errorlevel 1 exit /b 1
set "BAD_VERSION=32.0.101.7026"
set "TARGET_VERSION=32.0.101.7085"
set "INF_PATTERN=*.inf"
set "DEVICE_INSTANCE_ID="
set "TARGET_INF_PATH="
echo.
echo Driver rank repair options. Press Enter to keep defaults.
set /p "BAD_VERSION_INPUT=Bad driver version [%BAD_VERSION%]: "
if defined BAD_VERSION_INPUT set "BAD_VERSION=%BAD_VERSION_INPUT%"
set /p "TARGET_VERSION_INPUT=Target driver version [%TARGET_VERSION%]: "
if defined TARGET_VERSION_INPUT set "TARGET_VERSION=%TARGET_VERSION_INPUT%"
set /p "INF_PATTERN_INPUT=Target INF pattern [%INF_PATTERN%]: "
if defined INF_PATTERN_INPUT set "INF_PATTERN=%INF_PATTERN_INPUT%"
set /p "DEVICE_INSTANCE_ID=Device Instance ID override [optional]: "
set /p "TARGET_INF_PATH=Exact Target INF path [optional]: "
set "PS_EXTRA=-HardwareIdList ^"!HWID_LIST!^" -BadVersion ^"!BAD_VERSION!^" -TargetVersion ^"!TARGET_VERSION!^" -TargetInfNamePattern ^"!INF_PATTERN!^""
if defined DEVICE_INSTANCE_ID set "PS_EXTRA=!PS_EXTRA! -DeviceInstanceId ^"!DEVICE_INSTANCE_ID!^""
if defined TARGET_INF_PATH set "PS_EXTRA=!PS_EXTRA! -TargetInfPath ^"!TARGET_INF_PATH!^""
exit /b 0

:RUN_PS1
if not exist "%PS_SCRIPT%" (
  echo [ERROR] PowerShell script not found:
  echo   %PS_SCRIPT%
  exit /b 2
)
call :RESOLVE_PWSH
echo PowerShell: %PS_ENGINE%
echo Script: %PS_SCRIPT%
if defined PS_EXTRA echo Args: %PS_EXTRA%
echo.
"%PS_ENGINE%" -NoLogo -NoProfile -ExecutionPolicy Bypass -File "%PS_SCRIPT%" %PS_EXTRA%
set "RC=%ERRORLEVEL%"
echo.
echo Exit code: %RC%
exit /b %RC%

:RESOLVE_PWSH
if exist "%CORE_DIR%\powershell\pwsh.exe" set "PS_ENGINE=%CORE_DIR%\powershell\pwsh.exe" & exit /b 0
where pwsh.exe >nul 2>nul
if not errorlevel 1 set "PS_ENGINE=pwsh.exe" & exit /b 0
where powershell.exe >nul 2>nul
if not errorlevel 1 set "PS_ENGINE=powershell.exe" & exit /b 0
set "PS_ENGINE=%SystemRoot%\System32\WindowsPowerShell\v1.0\powershell.exe"
exit /b 0
