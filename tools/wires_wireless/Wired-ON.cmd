@echo off
setlocal EnableExtensions

set "WIRED_IF=Ethernet"

net session >nul 2>&1
if not "%errorlevel%"=="0" (
  echo Requesting Administrator privileges...
  mshta "vbscript:CreateObject(""Shell.Application"").ShellExecute(""%~f0"","","",""runas"",1)(close)"
  exit /b
)

echo.
echo Enabling wired interface: "%WIRED_IF%"
netsh interface set interface name="%WIRED_IF%" admin=enabled

echo.
netsh interface show interface | findstr /I /C:"%WIRED_IF%"
echo.
if not defined AUDION_NO_PAUSE pause
