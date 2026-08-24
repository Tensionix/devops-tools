@echo off
setlocal EnableExtensions EnableDelayedExpansion

REM === CONFIG (edit if you rename SSIDs or subnets) ===
set "HOME_SSID=BASE_Master"
set "TTK_SSID=BASE_Master_TTK_Wi-Fi"

set "HOME_NET_PREFIX=192.168.1."
set "TTK_NET_PREFIX=192.168.2."
REM === /CONFIG ===

echo.
echo === Wi-Fi STATUS ===
echo.

REM --- Get current SSID (works fine on RU/EN Windows) ---
set "SSID="
for /f "tokens=1,* delims=:" %%A in ('netsh wlan show interfaces ^| findstr /R /C:"^[ ]*SSID[ ]*:"') do (
  set "SSID=%%B"
)
if defined SSID (
  for /f "tokens=* delims= " %%S in ("!SSID!") do set "SSID=%%S"
) else (
  set "SSID=(unknown)"
)

echo SSID: !SSID!

REM --- Decide segment by SSID ---
set "SEGMENT=UNKNOWN"
if /I "!SSID!"=="%HOME_SSID%" set "SEGMENT=HOME"
if /I "!SSID!"=="%TTK_SSID%"  set "SEGMENT=TTK"

echo Segment (by SSID): !SEGMENT!

echo.
echo --- Current Wi-Fi SSID (raw) ---
netsh wlan show interfaces | findstr /R /C:"^[ ]*SSID[ ]*:"

echo.
echo --- IP configuration (Wi-Fi related lines) ---
ipconfig | findstr /I /C:"adapter Wi-Fi" /C:"adapter WLAN" /C:"adapter Беспровод" /C:"IPv4" /C:"Default Gateway" /C:"DNS Servers"

REM --- Optional: try to detect by subnet prefix (best-effort) ---
set "SUBNET_HINT=UNKNOWN"
ipconfig | findstr /I /C:"%HOME_NET_PREFIX%" >nul && set "SUBNET_HINT=HOME"
ipconfig | findstr /I /C:"%TTK_NET_PREFIX%"  >nul && set "SUBNET_HINT=TTK"
echo.
echo Segment (by subnet hint): !SUBNET_HINT!

echo.
if not defined AUDION_NO_PAUSE pause
