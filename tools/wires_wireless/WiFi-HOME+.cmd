@echo off
setlocal

set "TARGET=BASE_Master"
set "OTHER=BASE_Master_TTK_Wi-Fi"

echo.
echo === Switching Wi-Fi to: "%TARGET%" ===
echo.

netsh wlan connect name="%TARGET%"
netsh wlan set profileparameter name="%TARGET%" connectionmode=auto
netsh wlan set profileparameter name="%OTHER%"  connectionmode=manual

timeout /t 2 /nobreak >nul

echo.
echo --- Current Wi-Fi SSID ---
netsh wlan show interfaces | findstr /R /C:"^[ ]*SSID[ ]*:"

echo.
echo --- IP configuration (Wi-Fi) ---
ipconfig | findstr /I /C:"adapter Wi-Fi" /C:"adapter WLAN" /C:"adapter Беспровод" /C:"IPv4" /C:"Default Gateway" /C:"DNS Servers"

echo.
if not defined AUDION_NO_PAUSE pause
