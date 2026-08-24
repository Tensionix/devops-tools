$ErrorActionPreference = 'Stop'
Import-Module (Join-Path $PSScriptRoot 'NvidiaHdmiDpAudio.psm1') -Force
Export-AudionNvidiaAudioDeviceIds
