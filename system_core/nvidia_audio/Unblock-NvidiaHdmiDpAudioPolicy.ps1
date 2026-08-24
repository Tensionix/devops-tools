$ErrorActionPreference = 'Stop'
Import-Module (Join-Path $PSScriptRoot 'NvidiaHdmiDpAudio.psm1') -Force
Assert-AudionAdmin

Write-Host 'Creating backup of current DeviceInstall policy...'
Backup-AudionDeviceInstallPolicy

$statePath = Get-AudionBlockedIdsStatePath
$ids = @()

if (Test-Path $statePath) {
    $ids += Get-Content -Path $statePath -ErrorAction SilentlyContinue
}

$ids += Get-AudionNvidiaAudioHardwareIds
$ids = @($ids | Where-Object { -not [string]::IsNullOrWhiteSpace($_) } | Sort-Object -Unique)

if ($ids.Count -eq 0) {
    Write-Host 'No known NVIDIA HDAUDIO Hardware IDs were found in state or current devices.'
    Write-Host 'Nothing to remove automatically.'
} else {
    Write-Host ''
    Write-Host 'Hardware IDs to unblock:'
    foreach ($id in $ids) {
        Write-Host "  $id"
    }

    Write-Host ''
    Write-Host 'Removing Windows Device Installation policy block entries...'
    Remove-AudionDenyDeviceIds -HardwareIds $ids
}

Write-Host ''
Invoke-AudionPnpRescan

Write-Host ''
Write-Host 'Trying to enable matching devices...'
Enable-AudionNvidiaAudioDevices

Write-Host ''
Write-Host 'Unblock operation completed.'
