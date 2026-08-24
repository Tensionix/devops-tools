# Shows the current Windows Update driver and NVIDIA Device Installation Restriction status.
# Run as Administrator for complete visibility.

$ErrorActionPreference = 'Continue'

function Get-RegValueSafe {
    param(
        [Parameter(Mandatory=$true)][string]$Path,
        [Parameter(Mandatory=$true)][string]$Name
    )
    try {
        $item = Get-ItemProperty -LiteralPath $Path -Name $Name -ErrorAction Stop
        return $item.$Name
    } catch {
        return $null
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

$wu = Get-RegValueSafe -Path 'HKLM:\SOFTWARE\Policies\Microsoft\Windows\WindowsUpdate' -Name 'ExcludeWUDriversInQualityUpdate'
$wizard = Get-RegValueSafe -Path 'HKLM:\SOFTWARE\Policies\Microsoft\Windows\DriverSearching' -Name 'DriverUpdateWizardWuSearchEnabled'
$legacy = Get-RegValueSafe -Path 'HKLM:\SOFTWARE\Microsoft\Windows\CurrentVersion\DriverSearching' -Name 'SearchOrderConfig'
$metadata = Get-RegValueSafe -Path 'HKLM:\SOFTWARE\Policies\Microsoft\Windows\Device Metadata' -Name 'PreventDeviceMetadataFromNetwork'

$base = 'HKLM:\SOFTWARE\Policies\Microsoft\Windows\DeviceInstall\Restrictions'
$denyDeviceIds = Get-RegValueSafe -Path $base -Name 'DenyDeviceIDs'
$denyDeviceIdsRetro = Get-RegValueSafe -Path $base -Name 'DenyDeviceIDsRetroactive'
$denyInstanceIds = Get-RegValueSafe -Path $base -Name 'DenyInstanceIDs'
$denyInstanceIdsRetro = Get-RegValueSafe -Path $base -Name 'DenyInstanceIDsRetroactive'

$deviceList = @(Get-StringValuesFromSubkey -Path (Join-Path $base 'DenyDeviceIDs'))
$instanceList = @(Get-StringValuesFromSubkey -Path (Join-Path $base 'DenyInstanceIDs'))
$nvidiaDeviceList = @($deviceList | Where-Object { $_ -like 'PCI\VEN_10DE*' })
$nvidiaInstanceList = @($instanceList | Where-Object { $_ -like 'PCI\VEN_10DE*' })

Write-Host ''
Write-Host '=== Windows Update driver policy ===' -ForegroundColor Cyan
Write-Host "ExcludeWUDriversInQualityUpdate: $wu"
Write-Host "DriverUpdateWizardWuSearchEnabled: $wizard"
Write-Host "SearchOrderConfig: $legacy"
Write-Host "PreventDeviceMetadataFromNetwork: $metadata"

Write-Host ''
Write-Host '=== Device Installation Restrictions ===' -ForegroundColor Cyan
Write-Host "DenyDeviceIDs: $denyDeviceIds"
Write-Host "DenyDeviceIDsRetroactive: $denyDeviceIdsRetro"
Write-Host "DenyInstanceIDs: $denyInstanceIds"
Write-Host "DenyInstanceIDsRetroactive: $denyInstanceIdsRetro"
Write-Host "Total denied Hardware IDs: $($deviceList.Count)"
Write-Host "Total denied Instance IDs: $($instanceList.Count)"
Write-Host "NVIDIA denied Hardware IDs: $($nvidiaDeviceList.Count)"
Write-Host "NVIDIA denied Instance IDs: $($nvidiaInstanceList.Count)"

if ($nvidiaDeviceList.Count -gt 0) {
    Write-Host ''
    Write-Host 'NVIDIA denied Hardware IDs:' -ForegroundColor Cyan
    $nvidiaDeviceList | ForEach-Object { Write-Host "  $_" }
}

if ($nvidiaInstanceList.Count -gt 0) {
    Write-Host ''
    Write-Host 'NVIDIA denied Instance IDs:' -ForegroundColor Cyan
    $nvidiaInstanceList | ForEach-Object { Write-Host "  $_" }
}

Write-Host ''
Write-Host '=== Present NVIDIA PCI devices ===' -ForegroundColor Cyan
try {
    $devices = @(Get-PnpDevice -PresentOnly | Where-Object { $_.InstanceId -like 'PCI\VEN_10DE*' -or $_.FriendlyName -match 'NVIDIA|GeForce|RTX|GTX|Quadro|Tesla' })
    if ($devices.Count -eq 0) {
        Write-Host 'No present NVIDIA PCI devices detected.'
    } else {
        $devices | Select-Object FriendlyName, Class, Status, InstanceId | Format-Table -AutoSize | Out-Host
    }
} catch {
    Write-Host "Could not query PnP devices: $($_.Exception.Message)" -ForegroundColor Yellow
}
Write-Host ''
Write-Host '=== Fallback REG files ===' -ForegroundColor Cyan
try {
    $generator = Join-Path (Split-Path -Parent $MyInvocation.MyCommand.Path) 'Generate-Reg-Fallback-Files.ps1'
    if (Test-Path -LiteralPath $generator) {
        & $generator | Out-Host
    } else {
        Write-Host 'Fallback generator not found.' -ForegroundColor Yellow
    }
} catch {
    Write-Host "Could not generate fallback REG files: $($_.Exception.Message)" -ForegroundColor Yellow
}
