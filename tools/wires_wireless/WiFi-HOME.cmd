@echo off
setlocal

set "TARGET=BASE_Master"
set "OTHER=BASE_Master_TTK_Wi-Fi"

echo Connecting to "%TARGET%"...
netsh wlan connect name="%TARGET%"

netsh wlan set profileparameter name="%TARGET%" connectionmode=auto
netsh wlan set profileparameter name="%OTHER%"  connectionmode=manual

echo Done.
if not defined AUDION_NO_PAUSE pause
