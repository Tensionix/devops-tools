@echo off
setlocal EnableExtensions

for %%I in ("%~dp0..") do set "KIT=%%~fI"

net session >nul 2>&1
if not "%ERRORLEVEL%"=="0" (
  echo [ERROR] Run as Administrator.
  if not defined AUDION_NO_PAUSE pause
  exit /b 1
)

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

rem Anything to be restored is taken from the program's input folder.
for %%I in ("%KIT%\..\..") do set "APPROOT=%%~fI"
set "ROOTDIR=%APPROOT%\input"

if not "%~1"=="" set "ROOTDIR=%~1"

if "%ROOTDIR%"=="" (
  echo [ERROR] RootDir is empty.
  if not defined AUDION_NO_PAUSE pause
  exit /b 1
)

"%PWSH%" -NoProfile -ExecutionPolicy Bypass -File "%KIT%\Import-OpenSSHKeys.ps1" -RootDir "%ROOTDIR%" -ImportServerKeys:$true

echo.
echo [INFO] Done.
if not defined AUDION_NO_PAUSE pause
