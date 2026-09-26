# Wires & Wireless / Провод и Wi-Fi

## RU

В паке один сценарий — `Audion-Hotspot.ps1`: раздача Wi-Fi (мобильный хот-спот Windows).
Показать, включить, выключить — тот же переключатель, что в параметрах Windows.
Имя сети и пароль задаются в параметрах Windows, сценарий их не трогает.

    powershell -NoProfile -File Audion-Hotspot.ps1 -Action status|on|off [-NoPause]

Нужен Windows PowerShell 5.1: менеджер раздачи — тип WinRT.

Подключение к сетям Wi-Fi, режим автоподключения профиля, экспорт и импорт профилей и
переключение провод / Wi-Fi делает само окно DevOps Tools (раздел сети), своим кодом.
Две постоянные сети — кнопки WI-FI MAIN / SECOND: имя и пароль вводятся в окне,
пароль хранится под DPAPI Windows в data\wifi\slots.json.

## EN

The pack holds one script, `Audion-Hotspot.ps1`: Windows mobile hotspot — status, on, off,
the same switch as in Windows Settings. Network name and password stay in Windows Settings.

    powershell -NoProfile -File Audion-Hotspot.ps1 -Action status|on|off [-NoPause]

Needs Windows PowerShell 5.1: the tethering manager is a WinRT type.

Connecting to Wi-Fi networks, profile auto-connect mode, profile export/import and the
wired / Wi-Fi switch live in the DevOps Tools window itself (network section).
Two standing networks are the WI-FI MAIN / SECOND buttons: SSID and password typed in the
window, the password kept under Windows DPAPI in data\wifi\slots.json.
