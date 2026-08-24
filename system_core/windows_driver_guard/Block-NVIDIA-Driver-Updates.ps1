# Blocks future driver installs/updates for the currently installed NVIDIA PCI devices.
# It writes Group Policy-compatible Device Installation Restrictions for NVIDIA Hardware IDs.
# Run as Administrator.
# Default is NOT retroactive, so an already working NVIDIA driver should not be removed.

param(
    [switch]$IncludeCompatibleIds,
    [switch]$Retroactive
)

$ErrorActionPreference = 'Stop'
# PowerShell 7.x can promote native command failures to errors. Keep reg.exe/gpupdate.exe under explicit exit-code control.
$PSNativeCommandUseErrorActionPreference = $false

function Assert-Administrator {
    $identity = [Security.Principal.WindowsIdentity]::GetCurrent()
    $principal = New-Object Security.Principal.WindowsPrincipal($identity)
    if (-not $principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) {
        Write-Host 'ERROR: Run this script as Administrator.' -ForegroundColor Red
        exit 1
    }
}

function New-DirIfMissing {
    param([Parameter(Mandatory=$true)][string]$Path)
    if (-not (Test-Path -LiteralPath $Path)) {
        New-Item -ItemType Directory -Path $Path -Force | Out-Null
    }
}

function Convert-RegExePathToProviderPath {
    param([Parameter(Mandatory=$true)][string]$RegPath)

    $clean = $RegPath.Trim().TrimEnd('\')
    $upper = $clean.ToUpperInvariant()

    if ($upper -eq 'HKLM') { return 'Registry::HKEY_LOCAL_MACHINE' }
    if ($upper.StartsWith('HKLM\')) { return "Registry::HKEY_LOCAL_MACHINE\$($clean.Substring(5))" }

    if ($upper -eq 'HKCU') { return 'Registry::HKEY_CURRENT_USER' }
    if ($upper.StartsWith('HKCU\')) { return "Registry::HKEY_CURRENT_USER\$($clean.Substring(5))" }

    if ($upper -eq 'HKCR') { return 'Registry::HKEY_CLASSES_ROOT' }
    if ($upper.StartsWith('HKCR\')) { return "Registry::HKEY_CLASSES_ROOT\$($clean.Substring(5))" }

    if ($upper -eq 'HKU') { return 'Registry::HKEY_USERS' }
    if ($upper.StartsWith('HKU\')) { return "Registry::HKEY_USERS\$($clean.Substring(4))" }

    if ($upper -eq 'HKCC') { return 'Registry::HKEY_CURRENT_CONFIG' }
    if ($upper.StartsWith('HKCC\')) { return "Registry::HKEY_CURRENT_CONFIG\$($clean.Substring(5))" }

    throw "Unsupported registry path: $RegPath"
}

function Export-RegKeyIfExists {
    param(
        [Parameter(Mandatory=$true)][string]$RegPath,
        [Parameter(Mandatory=$true)][string]$BackupFile
    )

    $providerPath = Convert-RegExePathToProviderPath -RegPath $RegPath
    if (-not (Test-Path -LiteralPath $providerPath)) {
        Write-Host "Backup skipped, key does not exist: $RegPath" -ForegroundColor Yellow
        return
    }

    $oldErrorActionPreference = $ErrorActionPreference
    $ErrorActionPreference = 'Continue'
    try {
        & reg.exe export $RegPath $BackupFile /y *> $null
        $exitCode = $LASTEXITCODE
    } finally {
        $ErrorActionPreference = $oldErrorActionPreference
    }

    if ($exitCode -eq 0 -and (Test-Path -LiteralPath $BackupFile)) {
        Write-Host "Backup: $BackupFile"
    } else {
        Write-Host "WARNING: Backup export failed for $RegPath. reg.exe exit code: $($exitCode)" -ForegroundColor Yellow
    }
}

function Get-DevicePropertyData {
    param(
        [Parameter(Mandatory=$true)][string]$InstanceId,
        [Parameter(Mandatory=$true)][string]$KeyName
    )
    $prop = Get-PnpDeviceProperty -InstanceId $InstanceId -KeyName $KeyName -ErrorAction SilentlyContinue
    if ($null -eq $prop) { return @() }
    if ($null -eq $prop.Data) { return @() }
    if ($prop.Data -is [array]) { return @($prop.Data) }
    return @($prop.Data)
}

function Get-StringValuesFromSubkey {
    param([Parameter(Mandatory=$true)][string]$Path)
    if (-not (Test-Path -LiteralPath $Path)) { return @() }
    $item = Get-ItemProperty -LiteralPath $Path
    $values = @()
    foreach ($p in $item.PSObject.Properties) {
        if ($p.Name -like 'PS*') { continue }
        if ($null -eq $p.Value) { continue }
        if ($p.Value -is [string]) { $values += [string]$p.Value }
    }
    return @($values | Where-Object { $_ -and $_.Trim().Length -gt 0 })
}

function Write-NumberedStringSubkey {
    param(
        [string]$Path,
        [AllowNull()][AllowEmptyCollection()][object[]]$Values
    )
    if ([string]::IsNullOrWhiteSpace($Path)) { return }
    if ($null -eq $Values) { $Values = @() }
    $clean = @($Values | ForEach-Object { [string]$_ } | Where-Object { $_ -and $_.Trim().Length -gt 0 } | Select-Object -Unique)
    if (Test-Path -LiteralPath $Path) {
        Remove-Item -LiteralPath $Path -Recurse -Force
    }
    if ($clean.Count -eq 0) { return }
    New-Item -Path $Path -Force | Out-Null
    $i = 1
    foreach ($value in $clean) {
        New-ItemProperty -Path $Path -Name ([string]$i) -PropertyType String -Value $value -Force | Out-Null
        $i++
    }
}

function Merge-NvidiaList {
    param(
        [AllowNull()][AllowEmptyCollection()][object[]]$Existing,
        [AllowNull()][AllowEmptyCollection()][object[]]$NewValues
    )
    if ($null -eq $Existing) { $Existing = @() }
    if ($null -eq $NewValues) { $NewValues = @() }
    $kept = @($Existing | ForEach-Object { [string]$_ } | Where-Object { $_ -notlike 'PCI\VEN_10DE*' })
    $merged = @($kept + @($NewValues | ForEach-Object { [string]$_ })) | Where-Object { $_ -and $_.Trim().Length -gt 0 } | Select-Object -Unique
    return @($merged)
}

Assert-Administrator

$ScriptRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$ProjectRoot = (Resolve-Path -LiteralPath (Join-Path $ScriptRoot '..\..')).Path
$BackupDir = Join-Path $ProjectRoot 'backup\driver_guard\policy'
$StateDir = Join-Path $ProjectRoot 'data\driver_guard'
New-DirIfMissing $BackupDir
New-DirIfMissing $StateDir
$Stamp = Get-Date -Format 'yyyyMMdd_HHmmss'

Export-RegKeyIfExists 'HKLM\SOFTWARE\Policies\Microsoft\Windows\DeviceInstall\Restrictions' (Join-Path $BackupDir "DeviceInstall_Restrictions_before_nvidia_block_$Stamp.reg")

Write-Host 'Detecting present NVIDIA PCI devices...'
$devices = @(Get-PnpDevice -PresentOnly -ErrorAction Stop | Where-Object {
    ($_.InstanceId -like 'PCI\VEN_10DE*') -or ($_.FriendlyName -match 'NVIDIA|GeForce|RTX|GTX|Quadro|Tesla')
})

if ($devices.Count -eq 0) {
    Write-Host 'ERROR: No present NVIDIA PCI devices were detected.' -ForegroundColor Red
    Write-Host 'Check Device Manager, install the desired NVIDIA Studio driver first, then run this script again.'
    exit 2
}

$hardwareIds = @()
$compatibleIds = @()
$instanceIds = @()
$deviceReport = @()

foreach ($device in $devices) {
    $instanceId = [string]$device.InstanceId
    if ($instanceId -like 'PCI\VEN_10DE*') {
        $instanceIds += $instanceId
    }

    $hids = @(Get-DevicePropertyData -InstanceId $instanceId -KeyName 'DEVPKEY_Device_HardwareIds' | ForEach-Object { [string]$_ } | Where-Object { $_ -like 'PCI\VEN_10DE*' })
    $cids = @(Get-DevicePropertyData -InstanceId $instanceId -KeyName 'DEVPKEY_Device_CompatibleIds' | ForEach-Object { [string]$_ } | Where-Object { $_ -like 'PCI\VEN_10DE*' })

    $hardwareIds += $hids
    if ($IncludeCompatibleIds) { $compatibleIds += $cids }

    $deviceReport += [pscustomobject]@{
        FriendlyName = $device.FriendlyName
        Class = $device.Class
        Status = $device.Status
        InstanceId = $instanceId
        HardwareIds = @($hids)
        CompatibleIds = @($cids)
    }
}

$idsToDeny = @($hardwareIds)
if ($IncludeCompatibleIds) { $idsToDeny += $compatibleIds }
$idsToDeny = @($idsToDeny | Where-Object { $_ -and $_.Trim().Length -gt 0 } | Select-Object -Unique)
$instanceIds = @($instanceIds | Where-Object { $_ -and $_.Trim().Length -gt 0 } | Select-Object -Unique)

if ($idsToDeny.Count -eq 0) {
    Write-Host 'ERROR: NVIDIA devices were found, but no NVIDIA Hardware IDs were readable.' -ForegroundColor Red
    exit 3
}

$base = 'HKLM:\SOFTWARE\Policies\Microsoft\Windows\DeviceInstall\Restrictions'
New-Item -Path $base -Force | Out-Null

$denyDeviceIdsKey = Join-Path $base 'DenyDeviceIDs'
$denyInstanceIdsKey = Join-Path $base 'DenyInstanceIDs'

$existingDeviceIds = @(Get-StringValuesFromSubkey -Path $denyDeviceIdsKey)
$existingInstanceIds = @(Get-StringValuesFromSubkey -Path $denyInstanceIdsKey)

$mergedDeviceIds = @(Merge-NvidiaList -Existing $existingDeviceIds -NewValues $idsToDeny)
$mergedInstanceIds = @(Merge-NvidiaList -Existing $existingInstanceIds -NewValues $instanceIds)

New-ItemProperty -Path $base -Name 'DenyDeviceIDs' -PropertyType DWord -Value 1 -Force | Out-Null
New-ItemProperty -Path $base -Name 'DenyDeviceIDsRetroactive' -PropertyType DWord -Value ([int][bool]$Retroactive) -Force | Out-Null
Write-NumberedStringSubkey -Path $denyDeviceIdsKey -Values $mergedDeviceIds

if ($mergedInstanceIds.Count -gt 0) {
    New-ItemProperty -Path $base -Name 'DenyInstanceIDs' -PropertyType DWord -Value 1 -Force | Out-Null
    New-ItemProperty -Path $base -Name 'DenyInstanceIDsRetroactive' -PropertyType DWord -Value ([int][bool]$Retroactive) -Force | Out-Null
    Write-NumberedStringSubkey -Path $denyInstanceIdsKey -Values $mergedInstanceIds
}

$state = [pscustomobject]@{
    CreatedAt = (Get-Date).ToString('yyyy-MM-dd HH:mm:ss')
    Retroactive = [bool]$Retroactive
    IncludeCompatibleIds = [bool]$IncludeCompatibleIds
    Devices = $deviceReport
    DeniedDeviceIds = $idsToDeny
    DeniedInstanceIds = $instanceIds
}
$statePath = Join-Path $StateDir 'NVIDIA_DeviceInstall_Block_State.json'
$state | ConvertTo-Json -Depth 8 | Set-Content -LiteralPath $statePath -Encoding UTF8

Write-Host ''
Write-Host 'NVIDIA devices found:'
$devices | Select-Object FriendlyName, Class, Status, InstanceId | Format-Table -AutoSize | Out-Host

Write-Host 'Denied Hardware IDs:'
$idsToDeny | ForEach-Object { Write-Host "  $_" }

if ($instanceIds.Count -gt 0) {
    Write-Host 'Denied Instance IDs:'
    $instanceIds | ForEach-Object { Write-Host "  $_" }
}

Write-Host ''
Write-Host "State saved: $statePath"
Write-Host 'Refreshing computer policy...'
& gpupdate.exe /target:computer /force | Out-Host

Write-Host ''
Write-Host 'DONE: future NVIDIA driver installs/updates are blocked by Device Installation Restrictions.' -ForegroundColor Green
Write-Host 'Recommended workflow: unblock NVIDIA before a deliberate NVCleanstall/manual NVIDIA driver reinstall, then block again.'
if (-not $Retroactive) {
    Write-Host 'Retroactive mode was OFF. This is safer for an already working GPU driver.'
}
