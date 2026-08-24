@echo off
rem Verify that every path named in ssh and rclone configuration still exists.
rem Nothing is copied or changed here: the check only reads and reports.
rem Comments are ASCII on purpose - cmd reads .cmd files in the OEM codepage.
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

"%PWSH%" -NoProfile -ExecutionPolicy Bypass -File "%KIT%\Test-SSHAccessLinks.ps1"
set "RC=%ERRORLEVEL%"

echo.
if "%RC%"=="0" (
  echo [INFO] All configured paths exist.
) else (
  echo [WARN] Some configured paths are missing - see the list above.
)
if not defined AUDION_NO_PAUSE pause
exit /b %RC%
