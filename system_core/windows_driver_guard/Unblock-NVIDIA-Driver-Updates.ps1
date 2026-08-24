# Removes NVIDIA-specific Device Installation Restrictions created by Block-NVIDIA-Driver-Updates.ps1.
# It preserves non-NVIDIA restrictions in the same policy lists.
# Run as Administrator.

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

function Write-NumberedStringSubkeyOrRemove {
    param(
        [string]$Path,
        [AllowNull()][AllowEmptyCollection()][object[]]$Values
    )
    if ([string]::IsNullOrWhiteSpace($Path)) { return }
    if ($null -eq $Values) { $Values = @() }
    $clean = @($Values | ForEach-Object { [string]$_ } | Where-Object { $_ -and $_.Trim().Length -gt 0 } | Select-Object -Unique)
    if ($clean.Count -eq 0) {
        if (Test-Path -LiteralPath $Path) { Remove-Item -LiteralPath $Path -Recurse -Force }
        return
    }

    if (Test-Path -LiteralPath $Path) { Remove-Item -LiteralPath $Path -Recurse -Force }
    New-Item -Path $Path -Force | Out-Null
    $i = 1
    foreach ($value in $clean) {
        New-ItemProperty -Path $Path -Name ([string]$i) -PropertyType String -Value $value -Force | Out-Null
        $i++
    }
}

function Remove-ValueIfExists {
    param(
        [Parameter(Mandatory=$true)][string]$Path,
        [Parameter(Mandatory=$true)][string]$Name
    )
    if (Test-Path -LiteralPath $Path) {
        $prop = Get-ItemProperty -LiteralPath $Path -Name $Name -ErrorAction SilentlyContinue
        if ($null -ne $prop) { Remove-ItemProperty -LiteralPath $Path -Name $Name -Force }
    }
}

Assert-Administrator

$ScriptRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$ProjectRoot = (Resolve-Path -LiteralPath (Join-Path $ScriptRoot '..\..')).Path
$BackupDir = Join-Path $ProjectRoot 'backup\driver_guard\policy'
New-DirIfMissing $BackupDir
$Stamp = Get-Date -Format 'yyyyMMdd_HHmmss'

Export-RegKeyIfExists 'HKLM\SOFTWARE\Policies\Microsoft\Windows\DeviceInstall\Restrictions' (Join-Path $BackupDir "DeviceInstall_Restrictions_before_nvidia_unblock_$Stamp.reg")

$base = 'HKLM:\SOFTWARE\Policies\Microsoft\Windows\DeviceInstall\Restrictions'
$denyDeviceIdsKey = Join-Path $base 'DenyDeviceIDs'
$denyInstanceIdsKey = Join-Path $base 'DenyInstanceIDs'

if (-not (Test-Path -LiteralPath $base)) {
    Write-Host 'Device Installation Restrictions key is absent. Nothing to remove.' -ForegroundColor Yellow
    exit 0
}

$existingDeviceIds = @(Get-StringValuesFromSubkey -Path $denyDeviceIdsKey)
$existingInstanceIds = @(Get-StringValuesFromSubkey -Path $denyInstanceIdsKey)

$keptDeviceIds = @($existingDeviceIds | Where-Object { $_ -notlike 'PCI\VEN_10DE*' })
$keptInstanceIds = @($existingInstanceIds | Where-Object { $_ -notlike 'PCI\VEN_10DE*' })

Write-NumberedStringSubkeyOrRemove -Path $denyDeviceIdsKey -Values $keptDeviceIds
Write-NumberedStringSubkeyOrRemove -Path $denyInstanceIdsKey -Values $keptInstanceIds

if ($keptDeviceIds.Count -eq 0) {
    Remove-ValueIfExists -Path $base -Name 'DenyDeviceIDs'
    Remove-ValueIfExists -Path $base -Name 'DenyDeviceIDsRetroactive'
}
if ($keptInstanceIds.Count -eq 0) {
    Remove-ValueIfExists -Path $base -Name 'DenyInstanceIDs'
    Remove-ValueIfExists -Path $base -Name 'DenyInstanceIDsRetroactive'
}

Write-Host ''
Write-Host "Removed NVIDIA Hardware IDs: $($existingDeviceIds.Count - $keptDeviceIds.Count)"
Write-Host "Removed NVIDIA Instance IDs: $($existingInstanceIds.Count - $keptInstanceIds.Count)"

Write-Host ''
Write-Host 'Refreshing computer policy...'
& gpupdate.exe /target:computer /force | Out-Host

Write-Host ''
Write-Host 'DONE: NVIDIA-specific Device Installation Restrictions were removed.' -ForegroundColor Green
Write-Host 'Recommended next step: reboot before a deliberate NVIDIA driver reinstall.'
