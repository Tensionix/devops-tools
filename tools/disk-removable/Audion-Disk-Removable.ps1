#Requires -Version 5.1
<#
.SYNOPSIS
    Обнулить диск и разметить заново: один раздел на весь объём.

.DESCRIPTION
    Для флешек и внешних дисков, у которых разметка испорчена: разделы нулевого
    размера, «не распределена» во весь диск, следы прежней установки Windows.
    Управление дисками такое чинит через несколько окон, здесь это один шаг.

    Диск называется дважды: сперва номером, потом объёмом. Номер меняется от
    подключения к подключению, а объём - примета самого носителя, и совпасть
    случайно им трудно. Не сошлось - выходим, ничего не тронув.

    Данные на выбранном диске исчезают целиком. Это и есть назначение.

.PARAMETER Disk
    Номер диска. Не указан - спросим, показав список.

.PARAMETER SizeGb
    Объём выбранного диска в гигабайтах, для сверки. Не указан - спросим.

.PARAMETER FileSystem
    exFAT (по умолчанию), NTFS или FAT32.

.PARAMETER Label
    Метка тома. По умолчанию AUDION.

.PARAMETER Style
    Разметка: MBR (по умолчанию) или GPT. MBR читается везде, включая старые
    магнитолы и телевизоры; GPT нужен дискам больше двух терабайт.

.EXAMPLE
    .\Prepare-Removable.ps1
    Спросит всё по порядку.

.EXAMPLE
    .\Prepare-Removable.ps1 -Disk 2 -SizeGb 28.48 -Label ARCHIVE
    То же без вопросов - когда номер и объём уже известны.
#>
[CmdletBinding()]
param(
    [int]$Disk = -1,
    [double]$SizeGb = 0,
    [ValidateSet('exFAT', 'NTFS', 'FAT32')][string]$FileSystem = 'exFAT',
    [string]$Label = 'AUDION',
    [ValidateSet('MBR', 'GPT')][string]$Style = 'MBR',
    # Враппер держит паузу сам; ключ принимается, чтобы вызов из него не падал.
    [switch]$NoPause
)

$ErrorActionPreference = 'Stop'
try { [Console]::OutputEncoding = [System.Text.UTF8Encoding]::new($false) } catch { }

function Write-Line { param([string]$Text, [string]$Colour = 'Gray') Write-Host ('  ' + $Text) -ForegroundColor $Colour }

Write-Host ''
Write-Host '=== РАЗМЕТИТЬ НОСИТЕЛЬ ЗАНОВО ===' -ForegroundColor Cyan
Write-Host ''

# --- Права ------------------------------------------------------------------
$identity = [Security.Principal.WindowsIdentity]::GetCurrent()
if (-not ([Security.Principal.WindowsPrincipal]$identity).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) {
    Write-Line 'нужны права администратора - запустите prepare-removable.cmd' Yellow
    Write-Host ''
    exit 1
}

# --- Список -----------------------------------------------------------------
$all = @(Get-Disk | Sort-Object Number)
Write-Host '  ДИСКИ' -ForegroundColor Cyan
Write-Host ''
foreach ($one in $all) {
    $letters = @(Get-Partition -DiskNumber $one.Number -ErrorAction SilentlyContinue |
        Where-Object { $_.DriveLetter } | ForEach-Object { [string]$_.DriveLetter + ':' })
    $mark = ''
    if ($one.IsBoot -or $one.IsSystem) { $mark = '  <- СИСТЕМНЫЙ' }

    $colour = $(if ($mark) { 'Red' } elseif ($one.BusType -eq 'USB') { 'Green' } else { 'Gray' })
    Write-Host ('   {0}  {1,-28} {2,-6} {3,8:N2} ГБ  {4,-4} {5}{6}' -f
        $one.Number, $one.FriendlyName, $one.BusType, ($one.Size / 1GB),
        $one.PartitionStyle, ($letters -join ' '), $mark) -ForegroundColor $colour
}
Write-Host ''

# --- Какой ------------------------------------------------------------------
if ($Disk -lt 0) {
    $answer = Read-Host '  Номер диска, который обнулить'
    if (-not ($answer -match '^\d+$')) { Write-Line 'это не номер - выхожу' Yellow; exit 1 }
    $Disk = [int]$answer
}

$target = $all | Where-Object { $_.Number -eq $Disk }
if (-not $target) { Write-Line ('диска {0} нет' -f $Disk) Red; exit 1 }

$actual = [math]::Round($target.Size / 1GB, 2)
Write-Host ''
Write-Line ('выбран диск {0}: {1}, {2}, {3:N2} ГБ' -f $target.Number, $target.FriendlyName, $target.BusType, $actual) Cyan
$onIt = @(Get-Partition -DiskNumber $Disk -ErrorAction SilentlyContinue | Where-Object { $_.DriveLetter } |
    ForEach-Object { [string]$_.DriveLetter + ':' })
if ($onIt.Count) { Write-Line ('на нём тома: ' + ($onIt -join ' ')) Yellow }
if ($target.IsBoot -or $target.IsSystem) { Write-Line 'ЭТО СИСТЕМНЫЙ ДИСК' Red }

# --- Сверка объёмом ---------------------------------------------------------
# Номер диска меняется от подключения к подключению; объём - примета самого
# носителя. Совпасть случайно им трудно, и это единственная преграда перед тем,
# как данные исчезнут.
if ($SizeGb -le 0) {
    $answer = Read-Host ('  Объём этого диска в ГБ, как подтверждение (например {0:N2})' -f $actual)
    $answer = ([string]$answer).Replace(',', '.')
    if (-not ($answer -match '^\d+(\.\d+)?$')) { Write-Line 'это не число - выхожу' Yellow; exit 1 }
    $SizeGb = [double]$answer
}

if ([math]::Abs($SizeGb - $actual) -gt 0.5) {
    Write-Host ''
    Write-Line ('не сходится: сказано {0:N2} ГБ, у диска {1:N2} ГБ' -f $SizeGb, $actual) Red
    Write-Line 'ничего не тронуто' Yellow
    Write-Host ''
    exit 1
}

# --- Работа -----------------------------------------------------------------
Write-Host ''
Write-Line ('обнуляю диск {0} и делаю один раздел {1}, метка {2}, разметка {3}' -f $Disk, $FileSystem, $Label, $Style) Yellow
Write-Host ''

Clear-Disk -Number $Disk -RemoveData -RemoveOEM -Confirm:$false
Initialize-Disk -Number $Disk -PartitionStyle $Style -ErrorAction SilentlyContinue
$part = New-Partition -DiskNumber $Disk -UseMaximumSize -AssignDriveLetter
Start-Sleep -Seconds 2
$volume = Format-Volume -Partition $part -FileSystem $FileSystem -NewFileSystemLabel $Label -Confirm:$false

Write-Host ''
Write-Line ('готово: {0}: {1}, {2}, свободно {3:N2} ГБ' -f
    $volume.DriveLetter, $volume.FileSystemLabel, $volume.FileSystem, ($volume.SizeRemaining / 1GB)) Green
Write-Host ''
exit 0
