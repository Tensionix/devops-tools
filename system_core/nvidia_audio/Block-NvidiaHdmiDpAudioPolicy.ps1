$ErrorActionPreference = 'Stop'
Import-Module (Join-Path $PSScriptRoot 'NvidiaHdmiDpAudio.psm1') -Force
Assert-AudionAdmin

Write-Host 'Creating backup of current DeviceInstall policy...'
Backup-AudionDeviceInstallPolicy

Write-Host ''
Write-Host 'Collecting NVIDIA HDAUDIO Hardware IDs...'
$ids = Get-AudionNvidiaAudioHardwareIds

if ($ids.Count -eq 0) {
    Write-Host 'ERROR: No NVIDIA HDAUDIO Hardware IDs were found.' -ForegroundColor Red
    Write-Host 'Run Export NVIDIA audio IDs and inspect output\nvidia_audio\nvidia_hdmi_dp_audio_device_ids.txt.'
    exit 1
}

Write-Host ''
Write-Host 'Hardware IDs to block:'
foreach ($id in $ids) {
    Write-Host "  $id"
}

Write-Host ''
Write-Host 'Applying Windows Device Installation policy block...'
Set-AudionDenyDeviceIds -HardwareIds $ids

Write-Host ''
Write-Host 'Disabling currently installed matching devices...'
Disable-AudionNvidiaAudioDevices

Write-Host ''
Invoke-AudionPnpRescan

Write-Host ''
Write-Host 'Policy block is active. Reboot is recommended after driver changes.'
