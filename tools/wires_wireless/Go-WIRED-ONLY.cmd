@echo off
setlocal

call "%~dp0Wired-ON.cmd"

netsh wlan disconnect

echo.
echo Wi-Fi disconnected.
echo.
if not defined AUDION_NO_PAUSE pause
