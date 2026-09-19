#Requires -Version 5.1
<#
.SYNOPSIS
    Раздача Wi-Fi: показать, включить, выключить.

.DESCRIPTION
    Тот же переключатель, что в параметрах Windows, только из консоли и без
    мыши. Управляет им `NetworkOperatorTetheringManager` - тот же интерфейс,
    которым пользуется сама система.

    Имя сети и пароль здесь не задаются: их владелец ставит в параметрах
    Windows, и лезть туда незачем. Этот сценарий только поднимает и опускает
    раздачу.

    Почему её нельзя завести «при загрузке машины». Интерфейсу нужен контекст
    вошедшего пользователя: у него есть доступ к профилю подключения и к
    радиомодулю в пользовательской сессии. До входа радиомодулем некому владеть,
    и вызов из задачи под SYSTEM молча ничего не делает - без ошибки, просто
    впустую. Поэтому автозапуск такой раздачи ставят на вход в систему:

        tools\startup_kit\Run-Audion-Startup-Kit.cmd -Action add ^
            -Path "<этот сценарий>" -Arguments "-Action on" -When logon -DelayMinutes 1

    Задержка нужна: сразу после входа адаптер ещё поднимается.

.PARAMETER Action
    status - показать (по умолчанию), on - включить, off - выключить.

.PARAMETER NoPause
    Враппер держит паузу сам.

.EXAMPLE
    .\Audion-Hotspot.ps1
    Показать состояние раздачи.

.EXAMPLE
    .\Audion-Hotspot.ps1 -Action on
    Включить раздачу.
#>
[CmdletBinding()]
param(
    [ValidateSet('status', 'on', 'off')][string]$Action = 'status',
    [switch]$NoPause
)

$ErrorActionPreference = 'Stop'
try { [Console]::OutputEncoding = [System.Text.UTF8Encoding]::new($false) } catch { }

function Write-Line { param([string]$Text, [string]$Colour = 'Gray') Write-Host ('  ' + $Text) -ForegroundColor $Colour }

function Wait-Async {
    <#
        Ожидание WinRT-операции без await: у IAsyncOperation есть Status, и
        этого хватает. Значения: 0 - идёт, 1 - готово, 2 - отменено, 3 - ошибка.
    #>
    param($Operation, [int]$Seconds = 20)

    $waited = 0
    while ([int]$Operation.Status -eq 0 -and $waited -lt ($Seconds * 5)) {
        Start-Sleep -Milliseconds 200
        $waited++
    }
    return [int]$Operation.Status
}

Write-Host ''
Write-Host '=== РАЗДАЧА WI-FI ===' -ForegroundColor Cyan
Write-Host ''

# Типы WinRT грузятся так: обычный Add-Type их не видит.
try {
    $null = [Windows.Networking.Connectivity.NetworkInformation, Windows.Networking, ContentType = WindowsRuntime]
    $null = [Windows.Networking.NetworkOperators.NetworkOperatorTetheringManager, Windows.Networking, ContentType = WindowsRuntime]
} catch {
    Write-Line 'системный интерфейс раздачи недоступен на этой машине' Red
    Write-Host ''
    exit 1
}

$profile = [Windows.Networking.Connectivity.NetworkInformation]::GetInternetConnectionProfile()
if (-not $profile) {
    Write-Line 'интернета нет - раздавать нечего' Yellow
    Write-Line 'раздача берёт то подключение, через которое машина сама выходит в сеть' Gray
    Write-Host ''
    exit 1
}

Write-Line ('источник интернета: {0}' -f $profile.ProfileName)

try {
    $manager = [Windows.Networking.NetworkOperators.NetworkOperatorTetheringManager]::CreateFromConnectionProfile($profile)
} catch {
    Write-Line ('этим подключением раздавать нельзя: {0}' -f $_.Exception.Message) Yellow
    Write-Host ''
    exit 1
}

$state = [string]$manager.TetheringOperationalState
Write-Line ('состояние: {0}' -f $(switch ($state) {
    'On'  { 'раздача идёт' }
    'Off' { 'выключена' }
    default { $state }
}))

# Имя сети показываем, пароль - нет: он секрет и меняется в параметрах Windows.
try {
    $config = $manager.GetCurrentAccessPointConfiguration()
    if ($config) { Write-Line ('имя сети: {0}' -f $config.Ssid) }
} catch { }

if ($state -eq 'On') {
    Write-Line ('подключено устройств: {0} из {1}' -f $manager.ClientCount, $manager.MaxClientCount)
}

if ($Action -eq 'status') {
    Write-Host ''
    Write-Line 'включить: -Action on, выключить: -Action off' DarkGray
    Write-Host ''
    exit 0
}

# --- Включить или выключить --------------------------------------------------
if ($Action -eq 'on' -and $state -eq 'On') {
    Write-Host ''
    Write-Line 'раздача уже идёт' Green
    Write-Host ''
    exit 0
}
if ($Action -eq 'off' -and $state -eq 'Off') {
    Write-Host ''
    Write-Line 'раздача и так выключена' Green
    Write-Host ''
    exit 0
}

Write-Host ''
Write-Line $(if ($Action -eq 'on') { 'включаю' } else { 'выключаю' }) Yellow

$operation = $(if ($Action -eq 'on') { $manager.StartTetheringAsync() } else { $manager.StopTetheringAsync() })
$status = Wait-Async -Operation $operation

if ($status -ne 1) {
    Write-Line ('не вышло: операция завершилась со статусом {0}' -f $status) Red
    Write-Host ''
    exit 1
}

# Проверяем делом: состояние обязано смениться, а не «наверное сменилось».
Start-Sleep -Seconds 1
$now = [string]$manager.TetheringOperationalState
$want = $(if ($Action -eq 'on') { 'On' } else { 'Off' })

if ($now -eq $want) {
    Write-Line ('готово: {0}' -f $(if ($now -eq 'On') { 'раздача идёт' } else { 'раздача выключена' })) Green
} else {
    Write-Line ('состояние осталось прежним: {0}' -f $now) Red
    Write-Host ''
    exit 1
}

Write-Host ''
exit 0
