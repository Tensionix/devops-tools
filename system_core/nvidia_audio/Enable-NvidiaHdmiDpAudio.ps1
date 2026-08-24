$ErrorActionPreference = 'Stop'
Import-Module (Join-Path $PSScriptRoot 'NvidiaHdmiDpAudio.psm1') -Force
Assert-AudionAdmin
Write-Host 'Enabling NVIDIA HDMI/DP audio devices...'
Enable-AudionNvidiaAudioDevices
Write-Host 'Done.'
