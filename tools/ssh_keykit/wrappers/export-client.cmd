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
  echo [ERROR] pwsh.exe not found. Use keykit.cmd or set PATH.
  if not defined AUDION_NO_PAUSE pause
  exit /b 1
)

rem Results land in the program's own output folder, the same door every
rem other pack uses. Personal drives have no place in a released tool.
for %%I in ("%KIT%\..\..") do set "APPROOT=%%~fI"
set "ROOTDIR=%APPROOT%\output\ssh_keykit"

if not "%~1"=="" set "ROOTDIR=%~1"

if "%ROOTDIR%"=="" (
  echo [ERROR] RootDir is empty.
  if not defined AUDION_NO_PAUSE pause
  exit /b 1
)

if not exist "%ROOTDIR%" mkdir "%ROOTDIR%" >nul 2>nul

"%PWSH%" -NoProfile -ExecutionPolicy Bypass -File "%KIT%\Export-OpenSSHKeys.ps1" -RootDir "%ROOTDIR%" -IncludeServerKeys:$false

echo.
echo [INFO] Done.
if not defined AUDION_NO_PAUSE pause
