@echo off
setlocal

echo.
echo === Wi-Fi STATUS ===
echo.

echo --- Current Wi-Fi SSID ---
netsh wlan show interfaces | findstr /R /C:"^[ ]*SSID[ ]*:"

echo.
echo --- IP configuration (Wi-Fi) ---
ipconfig | findstr /I /C:"adapter Wi-Fi" /C:"adapter WLAN" /C:"adapter Беспровод" /C:"IPv4" /C:"Default Gateway" /C:"DNS Servers"

echo.
if not defined AUDION_NO_PAUSE pause
