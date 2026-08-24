@echo off
setlocal EnableExtensions

for %%I in ("%~dp0..") do set "KIT=%%~fI"

set "PWSH="
if exist "S:\Audion\Tools\PowerShell\pwsh.exe" (
  set "PWSH=S:\Audion\Tools\PowerShell\pwsh.exe"
) else if exist "E:\Audion\Tools\PowerShell\pwsh.exe" (
  set "PWSH=E:\Audion\Tools\PowerShell\pwsh.exe"
) else (
  where pwsh.exe >nul 2>&1
  if "%ERRORLEVEL%"=="0" set "PWSH=pwsh.exe"
)

if "%PWSH%"=="" (
  echo [WARN] pwsh.exe not found in:
  echo        S:\Audion\Tools\PowerShell\pwsh.exe
  echo        E:\Audion\Tools\PowerShell\pwsh.exe
  echo        PATH
  echo.
  set /p "PWSH=Enter full path to pwsh.exe: "
)

if "%PWSH%"=="" (
  echo [ERROR] pwsh.exe path is empty. Exiting.
  if not defined AUDION_NO_PAUSE pause
  exit /b 1
)

if not exist "%PWSH%" (
  echo [ERROR] pwsh.exe not found: %PWSH%
  if not defined AUDION_NO_PAUSE pause
  exit /b 1
)

set "DEFAULT_ROOTDIR="
rem The program's own folders, not personal drives: results go to output,
rem material to restore comes from input.
for %%I in ("%KIT%\..\..") do set "APPROOT=%%~fI"
if exist "%APPROOT%\output\" (
  set "DEFAULT_ROOTDIR=%APPROOT%\output\ssh_keykit"
) else if exist "%APPROOT%\" (
  set "DEFAULT_ROOTDIR=%APPROOT%\output\ssh_keykit"
)

:menu
cls
echo ==========================================
echo   OpenSSH KeyKit (Windows) - Menu
echo ==========================================
echo.
echo   pwsh:    %PWSH%
echo   Machine: %COMPUTERNAME%
echo   User:    %USERNAME%
echo.
if not "%DEFAULT_ROOTDIR%"=="" (
  echo   RootDir:  %DEFAULT_ROOTDIR%
) else (
  echo   RootDir:  (not detected)
)
echo.
echo   1) Export CLIENT keys (no admin)
echo   2) Export CLIENT + SERVER host keys (admin)
echo   3) Import CLIENT keys (no admin)         [this PC/user]
echo   4) Import CLIENT + SERVER host keys (admin) [this PC/user]
echo.
echo   Q) Quit
echo.
set /p "CHOICE=Select: "

if /I "%CHOICE%"=="Q" goto :eof
if "%CHOICE%"=="1" goto export_client
if "%CHOICE%"=="2" goto export_all_admin
if "%CHOICE%"=="3" goto import_client
if "%CHOICE%"=="4" goto import_all_admin
if "%CHOICE%"=="5" goto check_links

echo.
echo [ERROR] Unknown selection.
if not defined AUDION_NO_PAUSE pause
goto menu

:ask_root
set "ROOTDIR="

if not "%DEFAULT_ROOTDIR%"=="" (
  echo.
  echo [INFO] Default RootDir: %DEFAULT_ROOTDIR%
  set /p "ROOTDIR=Press Enter to use it, or type another path: "
  if "%ROOTDIR%"=="" set "ROOTDIR=%DEFAULT_ROOTDIR%"
) else (
  echo.
  set /p "ROOTDIR=Enter RootDir: "
)

if "%ROOTDIR%"=="" (
  echo [ERROR] RootDir is empty.
  if not defined AUDION_NO_PAUSE pause
  goto menu
)

if not exist "%ROOTDIR%" mkdir "%ROOTDIR%" >nul 2>nul
goto :eof

:require_admin
net session >nul 2>&1
if not "%ERRORLEVEL%"=="0" (
  echo.
  echo [ERROR] This action requires Administrator privileges.
  echo [HINT] Right-click keykit.cmd -> Run as Administrator
  if not defined AUDION_NO_PAUSE pause
  goto menu
)
goto :eof

:export_client
call :ask_root
echo.
echo [INFO] Exporting CLIENT keys...
"%PWSH%" -NoProfile -ExecutionPolicy Bypass -File "%KIT%\Export-OpenSSHKeys.ps1" -RootDir "%ROOTDIR%" -IncludeServerKeys:$false
echo.
echo [INFO] Done.
if not defined AUDION_NO_PAUSE pause
goto menu

:export_all_admin
call :require_admin
call :ask_root
echo.
echo [INFO] Exporting CLIENT + SERVER host keys...
"%PWSH%" -NoProfile -ExecutionPolicy Bypass -File "%KIT%\Export-OpenSSHKeys.ps1" -RootDir "%ROOTDIR%" -IncludeServerKeys:$true
echo.
echo [INFO] Done.
if not defined AUDION_NO_PAUSE pause
goto menu

:import_client
call :ask_root
echo.
echo [INFO] Importing CLIENT keys (latest snapshot) for: %COMPUTERNAME%\%USERNAME%
"%PWSH%" -NoProfile -ExecutionPolicy Bypass -File "%KIT%\Import-OpenSSHKeys.ps1" -RootDir "%ROOTDIR%" -ImportServerKeys:$false
echo.
echo [INFO] Done.
if not defined AUDION_NO_PAUSE pause
goto menu

:import_all_admin
call :require_admin
call :ask_root
echo.
echo [INFO] Importing CLIENT + SERVER host keys (latest snapshots) for: %COMPUTERNAME%\%USERNAME%
"%PWSH%" -NoProfile -ExecutionPolicy Bypass -File "%KIT%\Import-OpenSSHKeys.ps1" -RootDir "%ROOTDIR%" -ImportServerKeys:$true
echo.
echo [INFO] Done.
if not defined AUDION_NO_PAUSE pause
goto menu

:check_links
echo.
echo [INFO] Checking configured access paths...
"%PWSH%" -NoProfile -ExecutionPolicy Bypass -File "%KIT%\Test-SSHAccessLinks.ps1"
echo.
echo [INFO] Done.
if not defined AUDION_NO_PAUSE pause
goto menu
