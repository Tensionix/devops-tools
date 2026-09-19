#Requires -Version 5.1
<#
.SYNOPSIS
    Что запускается само: показать, завести, убрать пересечения.

.DESCRIPTION
    В Windows программу можно поднять при старте четырьмя разными способами, и
    каждый живёт своей жизнью: задача планировщика, ярлык в автозагрузке, ключ
    реестра `Run`, ключ `RunOnce`. Заводят их в разное время и разными руками, а
    потом одна и та же программа стартует дважды и мешает сама себе.

    Мастер собирает все четыре места в один список, заводит новое и - прежде
    чем завести - показывает, что уже запускает ту же программу, и предлагает
    убрать лишнее.

    Про задержку. Сразу после загрузки половина вещей не работает: сеть ещё не
    поднялась, службы не готовы, профиль не развёрнут. У задачи планировщика
    задержка своя, штатная; у ярлыка автозагрузки её нет вовсе - тогда мастер
    кладёт рядом обёртку, которая ждёт и лишь потом запускает.

    Про раздачу Wi-Fi. Она не поднимается «при загрузке» ни при каких
    настройках: `NetworkOperatorTetheringManager` требует контекста вошедшего
    пользователя. Мастер это знает и уводит такую задачу на вход в систему.

.PARAMETER Action
    list - показать (по умолчанию), add - завести, remove - убрать.

.PARAMETER Path
    Что запускать. Не указан - спросим.

.PARAMETER Arguments
    Аргументы запускаемой программы.

.PARAMETER When
    logon - при входе пользователя (по умолчанию), boot - при загрузке машины.

.PARAMETER DelayMinutes
    Задержка после события, в минутах. Ноль - без задержки.

.PARAMETER How
    task - задача планировщика (по умолчанию), startup - ярлык в автозагрузке.

.PARAMETER Name
    Имя записи. Не указано - возьмём по имени программы.

.PARAMETER NoPause
    Враппер держит паузу сам.

.EXAMPLE
    .\Audion-Startup-Kit.ps1
    Показать всё, что стартует само.

.EXAMPLE
    .\Audion-Startup-Kit.ps1 -Action add -Path "C:\Tools\hotspot.ps1" -When logon -DelayMinutes 2
    Завести запуск через две минуты после входа в систему.
#>
[CmdletBinding()]
param(
    [ValidateSet('list', 'add', 'remove')][string]$Action = 'list',
    [string]$Path = '',
    [string]$Arguments = '',
    [ValidateSet('logon', 'boot')][string]$When = 'logon',
    [int]$DelayMinutes = 0,
    [ValidateSet('task', 'startup')][string]$How = 'task',
    [string]$Name = '',
    [switch]$NoPause
)

$ErrorActionPreference = 'Stop'
try { [Console]::OutputEncoding = [System.Text.UTF8Encoding]::new($false) } catch { }

$StartupUser = [Environment]::GetFolderPath('Startup')
$StartupAll = [Environment]::GetFolderPath('CommonStartup')
$RunKeys = @(
    @{ Path = 'HKCU:\Software\Microsoft\Windows\CurrentVersion\Run';     Where = 'реестр Run (этот пользователь)' }
    @{ Path = 'HKLM:\Software\Microsoft\Windows\CurrentVersion\Run';     Where = 'реестр Run (все)' }
    @{ Path = 'HKCU:\Software\Microsoft\Windows\CurrentVersion\RunOnce'; Where = 'реестр RunOnce (этот пользователь)' }
    @{ Path = 'HKLM:\Software\Microsoft\Windows\CurrentVersion\RunOnce'; Where = 'реестр RunOnce (все)' }
)

function Write-Line { param([string]$Text, [string]$Colour = 'Gray') Write-Host ('  ' + $Text) -ForegroundColor $Colour }

function Test-Elevated {
    $id = [Security.Principal.WindowsIdentity]::GetCurrent()
    return ([Security.Principal.WindowsPrincipal]$id).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
}

# --- Что уже стартует --------------------------------------------------------
function Get-StartupEntries {
    <#
        Все четыре места одним списком. Задачи берём только те, у которых есть
        триггер входа или загрузки: ночное расписание к автозапуску отношения
        не имеет.
    #>
    $rows = @()

    foreach ($task in @(Get-ScheduledTask -ErrorAction SilentlyContinue)) {
        $triggers = @($task.Triggers | Where-Object {
            $_.CimClass.CimClassName -in @('MSFT_TaskLogonTrigger', 'MSFT_TaskBootTrigger')
        })
        if (-not $triggers.Count) { continue }

        $action = @($task.Actions | Where-Object { $_.Execute })[0]
        if (-not $action) { continue }

        $delay = ''
        foreach ($trigger in $triggers) {
            if ($trigger.Delay) { $delay = [string]$trigger.Delay }
        }

        $rows += [pscustomobject]@{
            Where    = 'планировщик'
            Name     = $task.TaskName
            Command  = ('{0} {1}' -f $action.Execute, $action.Arguments).Trim()
            When     = $(if (@($triggers | Where-Object { $_.CimClass.CimClassName -eq 'MSFT_TaskBootTrigger' }).Count) { 'загрузка' } else { 'вход' })
            Delay    = $delay
            Handle   = $task.TaskPath + $task.TaskName
        }
    }

    foreach ($folder in @(@{ P = $StartupUser; W = 'автозагрузка (этот пользователь)' },
                          @{ P = $StartupAll;  W = 'автозагрузка (все)' })) {
        if (-not (Test-Path -LiteralPath $folder.P)) { continue }
        foreach ($file in @(Get-ChildItem -LiteralPath $folder.P -File -ErrorAction SilentlyContinue)) {
            $target = $file.FullName
            if ($file.Extension -eq '.lnk') {
                try {
                    $shell = New-Object -ComObject WScript.Shell
                    $link = $shell.CreateShortcut($file.FullName)
                    $target = ('{0} {1}' -f $link.TargetPath, $link.Arguments).Trim()
                } catch { }
            }
            # Наша обёртка прячет программу за cmd.exe: разворачиваем, иначе
            # пересечение с ней не найдётся, а проверка после заведения не
            # узнает собственную запись.
            $delay = ''
            if ($target -match '(?i)cmd\.exe /c "(.+Audion\\Startup\\.+\.cmd)"') {
                $helper = $Matches[1]
                if (Test-Path -LiteralPath $helper) {
                    $body = Get-Content -LiteralPath $helper -Raw
                    if ($body -match '(?im)^timeout /t (\d+)') { $delay = ('{0} мин' -f ([int]$Matches[1] / 60)) }
                    if ($body -match '(?im)^start "" (.+)$') { $target = $Matches[1].Trim() }
                }
            }

            $rows += [pscustomobject]@{
                Where   = $folder.W
                Name    = $file.Name
                Command = $target
                When    = 'вход'
                Delay   = $delay
                Handle  = $file.FullName
            }
        }
    }

    foreach ($key in $RunKeys) {
        if (-not (Test-Path -LiteralPath $key.Path)) { continue }
        $item = Get-Item -LiteralPath $key.Path
        foreach ($value in @($item.GetValueNames())) {
            $rows += [pscustomobject]@{
                Where   = $key.Where
                Name    = $value
                Command = [string]$item.GetValue($value)
                When    = 'вход'
                Delay   = ''
                Handle  = $key.Path + '|' + $value
            }
        }
    }

    return $rows
}

function Show-Entries {
    param([object[]]$Rows)

    if (-not $Rows.Count) { Write-Line 'ничего не стартует само' ; return }

    $n = 0
    foreach ($row in $Rows) {
        $n++
        $tail = ''
        if ($row.Delay) { $tail = '  задержка ' + $row.Delay }
        Write-Host ('  {0,3}. {1,-32} {2,-10}{3}' -f $n, $row.Name, $row.When, $tail) -ForegroundColor White
        Write-Host ('       {0}' -f $row.Where) -ForegroundColor DarkGray
        Write-Host ('       {0}' -f $row.Command) -ForegroundColor Gray
    }
}

# --- Пересечения -------------------------------------------------------------
function Find-Overlaps {
    <#
        Что уже запускает ту же программу. Сравниваем по имени файла, а не по
        всей строке: один и тот же exe заводят то с полным путём, то через
        обёртку, то с аргументами - строки разные, программа одна.
    #>
    param([object[]]$Rows, [string]$Target)

    $leaf = [System.IO.Path]::GetFileName($Target)
    if (-not $leaf) { return @() }
    return @($Rows | Where-Object { $_.Command -and $_.Command -match [regex]::Escape($leaf) })
}

# --- Заведение ---------------------------------------------------------------
function Add-Startup {
    param([string]$Target, [string]$Args, [string]$Moment, [int]$Delay, [string]$Way, [string]$Title)

    if ($Way -eq 'task') {
        $execute = $Target
        $argument = $Args
        # Сценарий сам по себе не запускается: планировщик умеет только
        # программы, поэтому .ps1 и .cmd заворачиваем в их движок.
        switch ([System.IO.Path]::GetExtension($Target).ToLower()) {
            '.ps1' {
                $execute = 'powershell.exe'
                $argument = ('-NoProfile -ExecutionPolicy Bypass -WindowStyle Hidden -File "{0}" {1}' -f $Target, $Args).Trim()
            }
            '.cmd' { $execute = 'cmd.exe'; $argument = ('/c "{0}" {1}' -f $Target, $Args).Trim() }
            '.bat' { $execute = 'cmd.exe'; $argument = ('/c "{0}" {1}' -f $Target, $Args).Trim() }
        }

        # Пустой -Argument планировщик не принимает: у программы без
        # аргументов его просто не должно быть в вызове.
        $action = $(if ($argument) {
            New-ScheduledTaskAction -Execute $execute -Argument $argument
        } else {
            New-ScheduledTaskAction -Execute $execute
        })
        $trigger = $(if ($Moment -eq 'boot') { New-ScheduledTaskTrigger -AtStartup }
                     else { New-ScheduledTaskTrigger -AtLogOn -User ('{0}\{1}' -f $env:USERDOMAIN, $env:USERNAME) })
        if ($Delay -gt 0) { $trigger.Delay = ('PT{0}M' -f $Delay) }

        $settings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries `
            -ExecutionTimeLimit ([TimeSpan]::Zero) -StartWhenAvailable

        $user = $(if ($Moment -eq 'boot') { 'SYSTEM' } else { '{0}\{1}' -f $env:USERDOMAIN, $env:USERNAME })
        $level = $(if ($Moment -eq 'boot') { 'Highest' } else { 'Limited' })

        Register-ScheduledTask -TaskName $Title -Action $action -Trigger $trigger -Settings $settings `
            -User $user -RunLevel $level -Force | Out-Null
        return @{ Kind = 'task'; Handle = $Title }
    }

    # Ярлык в автозагрузке. Своей задержки у него нет: если она нужна, рядом
    # ложится обёртка, которая ждёт и лишь потом запускает.
    $shell = New-Object -ComObject WScript.Shell
    $linkPath = Join-Path $StartupUser ($Title + '.lnk')

    if ($Delay -gt 0) {
        $helperDir = Join-Path $env:LOCALAPPDATA 'Audion\Startup'
        New-Item -ItemType Directory -Path $helperDir -Force | Out-Null
        $helper = Join-Path $helperDir ($Title + '.cmd')
        $lines = @(
            '@echo off',
            'rem Written by Audion Startup Kit. A shortcut has no delay of its own,',
            'rem so the wait lives here.',
            ('timeout /t {0} /nobreak >nul' -f ($Delay * 60)),
            ('start "" "{0}" {1}' -f $Target, $Args).Trim()
        )
        [System.IO.File]::WriteAllLines($helper, $lines, [System.Text.UTF8Encoding]::new($false))
        $link = $shell.CreateShortcut($linkPath)
        $link.TargetPath = 'cmd.exe'
        $link.Arguments = ('/c "{0}"' -f $helper)
        $link.WindowStyle = 7
    } else {
        $link = $shell.CreateShortcut($linkPath)
        $link.TargetPath = $Target
        if ($Args) { $link.Arguments = $Args }
    }
    $link.WorkingDirectory = [System.IO.Path]::GetDirectoryName($Target)
    $link.Save()
    return @{ Kind = 'startup'; Handle = $linkPath }
}

function Remove-Entry {
    param([object]$Row)

    switch -Wildcard ($Row.Where) {
        'планировщик' { Unregister-ScheduledTask -TaskName $Row.Name -Confirm:$false; return $true }
        'автозагрузка*' { Remove-Item -LiteralPath $Row.Handle -Force; return $true }
        'реестр*' {
            $parts = $Row.Handle -split '\|', 2
            Remove-ItemProperty -LiteralPath $parts[0] -Name $parts[1] -Force
            return $true
        }
    }
    return $false
}

# ============================================================================
Write-Host ''
Write-Host '=== ЧТО ЗАПУСКАЕТСЯ САМО ===' -ForegroundColor Cyan
Write-Host ''

$entries = @(Get-StartupEntries)
Show-Entries -Rows $entries
Write-Host ''

if ($Action -eq 'list') {
    Write-Line ('записей: {0}' -f $entries.Count)
    Write-Line 'завести новую: -Action add, убрать: -Action remove' DarkGray
    Write-Host ''
    exit 0
}

# --- Убрать ------------------------------------------------------------------
if ($Action -eq 'remove') {
    if (-not $entries.Count) { Write-Host ''; exit 0 }
    $answer = Read-Host '  Номер записи, которую убрать (пусто - выйти)'
    if (-not ($answer -match '^\d+$')) { Write-Line 'ничего не тронуто'; Write-Host ''; exit 0 }
    $at = [int]$answer
    if ($at -lt 1 -or $at -gt $entries.Count) { Write-Line 'нет такого номера' Yellow; Write-Host ''; exit 1 }

    $row = $entries[$at - 1]
    Write-Line ('убираю: {0} ({1})' -f $row.Name, $row.Where) Yellow
    if (($row.Where -like '*все*' -or $row.Where -like '*HKLM*') -and -not (Test-Elevated)) {
        Write-Line 'эта запись общая для всех - нужны права администратора' Yellow
        Write-Host ''
        exit 1
    }
    if (Remove-Entry -Row $row) { Write-Line 'убрано' Green } else { Write-Line 'не вышло' Red }
    Write-Host ''
    exit 0
}

# --- Завести -----------------------------------------------------------------
if (-not $Path) {
    $Path = (Read-Host '  Что запускать (полный путь)').Trim('"').Trim()
}
if (-not $Path -or -not (Test-Path -LiteralPath $Path)) {
    Write-Line ('нет такого файла: {0}' -f $Path) Yellow
    Write-Host ''
    exit 1
}
$Path = (Resolve-Path -LiteralPath $Path).Path

if (-not $Name) { $Name = 'Audion ' + [System.IO.Path]::GetFileNameWithoutExtension($Path) }

# Пересечения - до того, как заводить.
$overlaps = @(Find-Overlaps -Rows $entries -Target $Path)
if ($overlaps.Count) {
    Write-Host ''
    Write-Line 'эту программу уже что-то запускает:' Yellow
    foreach ($row in $overlaps) {
        Write-Host ('       {0}  ({1})' -f $row.Name, $row.Where) -ForegroundColor Yellow
    }
    $answer = Read-Host '  Убрать найденное, чтобы не запускалось дважды? (да/нет)'
    if ($answer -match '^(?i)д|y') {
        foreach ($row in $overlaps) {
            try {
                if (Remove-Entry -Row $row) { Write-Line ('убрано: {0}' -f $row.Name) Green }
            } catch {
                Write-Line ('не вышло убрать {0}: {1}' -f $row.Name, $_.Exception.Message) Yellow
            }
        }
    }
}

# Момент и задержка.
if (-not $PSBoundParameters.ContainsKey('When')) {
    $answer = Read-Host '  Когда запускать: 1 - при входе в систему, 2 - при загрузке машины'
    $When = $(if ($answer -eq '2') { 'boot' } else { 'logon' })
}
if (-not $PSBoundParameters.ContainsKey('DelayMinutes')) {
    $answer = Read-Host '  Задержка в минутах после события (0 - сразу)'
    if ($answer -match '^\d+$') { $DelayMinutes = [int]$answer }
}

# Раздача Wi-Fi при загрузке не поднимется ни при каких настройках: интерфейсу
# нужен контекст вошедшего пользователя, а до входа радиомодулем некому владеть.
if ($When -eq 'boot' -and ($Path -match '(?i)hotspot|tether')) {
    Write-Host ''
    Write-Line 'раздача Wi-Fi при загрузке машины не поднимается:' Yellow
    Write-Line 'ей нужен контекст вошедшего пользователя, а до входа его нет' Gray
    Write-Line 'перевожу на вход в систему' Gray
    $When = 'logon'
}

if ($When -eq 'boot' -and -not (Test-Elevated)) {
    Write-Host ''
    Write-Line 'запуск при загрузке заводится от имени системы - нужны права администратора' Yellow
    Write-Host ''
    exit 1
}

Write-Host ''
Write-Line ('завожу: {0}' -f $Name) Cyan
Write-Line ('  что   : {0} {1}' -f $Path, $Arguments)
Write-Line ('  когда : {0}' -f $(if ($When -eq 'boot') { 'при загрузке машины' } else { 'при входе в систему' }))
Write-Line ('  пауза : {0}' -f $(if ($DelayMinutes -gt 0) { ('{0} мин' -f $DelayMinutes) } else { 'без задержки' }))
Write-Line ('  как   : {0}' -f $(if ($How -eq 'task') { 'задача планировщика' } else { 'ярлык в автозагрузке' }))

$made = Add-Startup -Target $Path -Args $Arguments -Moment $When -Delay $DelayMinutes -Way $How -Title $Name

# Проверяем делом: запись обязана найтись в общем списке, а не «наверное есть».
Write-Host ''
$again = @(Get-StartupEntries | Where-Object {
    $_.Name -eq $Name -or $_.Name -eq ($Name + '.lnk')
})
if ($again.Count) {
    Write-Line 'заведено и видно в списке:' Green
    foreach ($row in $again) {
        Write-Host ('       {0}  ({1}{2})' -f $row.Name, $row.Where, $(if ($row.Delay) { ', задержка ' + $row.Delay } else { '' })) -ForegroundColor Green
    }
} else {
    Write-Line 'запись не нашлась в списке - что-то пошло не так' Red
    Write-Host ''
    exit 1
}

Write-Host ''
exit 0
