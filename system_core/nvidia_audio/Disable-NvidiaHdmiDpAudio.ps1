$ErrorActionPreference = 'Stop'
Import-Module (Join-Path $PSScriptRoot 'NvidiaHdmiDpAudio.psm1') -Force
Assert-AudionAdmin
Write-Host 'Disabling NVIDIA HDMI/DP audio devices...'
Disable-AudionNvidiaAudioDevices
Write-Host 'Done.'
