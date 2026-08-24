# Audion NVIDIA HDMI/DP Audio Control module
# Purpose: disable or policy-block NVIDIA HDMI/DisplayPort audio devices without touching normal audio interfaces.
# All user-visible strings are English to avoid console encoding issues.

$script:RestrictionsPath = 'HKLM:\SOFTWARE\Policies\Microsoft\Windows\DeviceInstall\Restrictions'
$script:DenyDeviceIdsPath = Join-Path $script:RestrictionsPath 'DenyDeviceIDs'

function Get-AudionRoot {
    return (Resolve-Path (Join-Path $PSScriptRoot '..\..')).Path
}

function Get-AudionBackupDir {
    $dir = Join-Path (Get-AudionRoot) 'backup\nvidia_audio'
    if (-not (Test-Path $dir)) {
        New-Item -ItemType Directory -Path $dir -Force | Out-Null
    }
    return $dir
}

function Get-AudionOutputDir {
    $dir = Join-Path (Get-AudionRoot) 'output\nvidia_audio'
    if (-not (Test-Path $dir)) {
        New-Item -ItemType Directory -Path $dir -Force | Out-Null
    }
    return $dir
}

function Get-AudionStateDir {
    $dir = Join-Path (Get-AudionRoot) 'data\nvidia_audio'
    if (-not (Test-Path $dir)) {
        New-Item -ItemType Directory -Path $dir -Force | Out-Null
    }
    return $dir
}

function Get-AudionBlockedIdsStatePath {
    return (Join-Path (Get-AudionStateDir) 'nvidia_audio_blocked_hardware_ids.txt')
}

function Test-AudionAdmin {
    $identity = [Security.Principal.WindowsIdentity]::GetCurrent()
    $principal = New-Object Security.Principal.WindowsPrincipal($identity)
    return $principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
}

function Assert-AudionAdmin {
    if (-not (Test-AudionAdmin)) {
        Write-Host 'ERROR: Administrator privileges are required.' -ForegroundColor Red
        Write-Host 'Run the CMD wrapper as Administrator, or allow the UAC prompt.'
        exit 740
    }
}

function Test-AudionPnpModule {
    $cmd = Get-Command Get-PnpDevice -ErrorAction SilentlyContinue
    if (-not $cmd) {
        Write-Host 'ERROR: Get-PnpDevice is not available on this system.' -ForegroundColor Red
        Write-Host 'This kit requires the Windows PnpDevice PowerShell module.'
        exit 2
    }
}

function Get-AudionNvidiaAudioDevices {
    Test-AudionPnpModule

    $devices = Get-PnpDevice -ErrorAction Stop | Where-Object {
        $name = [string]$_.FriendlyName
        $id = [string]$_.InstanceId
        $class = [string]$_.Class

        $classOk = $class -in @('MEDIA', 'AudioEndpoint')
        $notVirtual = $name -notmatch '(?i)\bVirtual\b'
        $nameOk = $name -match '(?i)NVIDIA High Definition Audio|NVIDIA Output|\(NVIDIA High Definition Audio\)|HDMI.*NVIDIA|DisplayPort.*NVIDIA'
        $idOk = $id -match '(?i)^HDAUDIO\\FUNC_01&VEN_10DE'

        return ($classOk -and $notVirtual -and ($nameOk -or $idOk))
    }

    return @($devices | Sort-Object Class, FriendlyName, InstanceId -Unique)
}

function Get-AudionDeviceHardwareIds {
    param(
        [Parameter(Mandatory = $true)]
        [string]$InstanceId
    )

    try {
        $prop = Get-PnpDeviceProperty -InstanceId $InstanceId -KeyName 'DEVPKEY_Device_HardwareIds' -ErrorAction Stop
        if ($null -eq $prop.Data) {
            return @()
        }

        if ($prop.Data -is [array]) {
            return @($prop.Data)
        }

        return @([string]$prop.Data)
    } catch {
        return @()
    }
}

function Get-AudionDeviceCompatibleIds {
    param(
        [Parameter(Mandatory = $true)]
        [string]$InstanceId
    )

    try {
        $prop = Get-PnpDeviceProperty -InstanceId $InstanceId -KeyName 'DEVPKEY_Device_CompatibleIds' -ErrorAction Stop
        if ($null -eq $prop.Data) {
            return @()
        }

        if ($prop.Data -is [array]) {
            return @($prop.Data)
        }

        return @([string]$prop.Data)
    } catch {
        return @()
    }
}

function Get-AudionNvidiaAudioHardwareIds {
    $devices = Get-AudionNvidiaAudioDevices
    $allIds = New-Object System.Collections.Generic.List[string]

    foreach ($device in $devices) {
        $ids = Get-AudionDeviceHardwareIds -InstanceId $device.InstanceId
        foreach ($id in $ids) {
            if ([string]::IsNullOrWhiteSpace($id)) {
                continue
            }

            # The safe target is NVIDIA HDAUDIO codec, not the display adapter and not generic PCI functions.
            if ($id -match '(?i)^HDAUDIO\\FUNC_01&VEN_10DE') {
                $allIds.Add($id)
            }
        }
    }

    if ($allIds.Count -eq 0) {
        foreach ($device in $devices) {
            $ids = Get-AudionDeviceHardwareIds -InstanceId $device.InstanceId
            foreach ($id in $ids) {
                if ([string]::IsNullOrWhiteSpace($id)) {
                    continue
                }

                if ($id -match '(?i)VEN_10DE' -and $id -match '(?i)HDAUDIO') {
                    $allIds.Add($id)
                }
            }
        }
    }

    return @($allIds | Sort-Object -Unique)
}

function Backup-AudionDeviceInstallPolicy {
    Assert-AudionAdmin

    $backupDir = Get-AudionBackupDir
    $stamp = Get-Date -Format 'yyyyMMdd_HHmmss'
    $regBackup = Join-Path $backupDir "device_install_policy_before_change_$stamp.reg"
    $notePath = Join-Path $backupDir "device_install_policy_backup_note_$stamp.txt"

    $regKey = 'HKLM\SOFTWARE\Policies\Microsoft\Windows\DeviceInstall'
    & reg.exe export $regKey $regBackup /y | Out-Null

    if ($LASTEXITCODE -eq 0) {
        "Last registry policy backup: $regBackup" | Set-Content -Path $notePath -Encoding UTF8
        Write-Host "Policy backup saved: $regBackup"
    } else {
        "No existing DeviceInstall policy key was exported. This is normal on a clean system." | Set-Content -Path $notePath -Encoding UTF8
        Write-Host 'No existing DeviceInstall policy key was exported. This is normal on a clean system.'
    }
}

function Get-AudionDenyDeviceIdEntries {
    if (-not (Test-Path $script:DenyDeviceIdsPath)) {
        return @()
    }

    $props = Get-ItemProperty -Path $script:DenyDeviceIdsPath
    $entries = foreach ($prop in $props.PSObject.Properties) {
        if ($prop.Name -match '^PS') {
            continue
        }

        if ([string]::IsNullOrWhiteSpace([string]$prop.Value)) {
            continue
        }

        [PSCustomObject]@{
            Name = [string]$prop.Name
            Value = [string]$prop.Value
        }
    }

    return @($entries)
}

function Set-AudionDenyDeviceIds {
    param(
        [Parameter(Mandatory = $true)]
        [string[]]$HardwareIds
    )

    Assert-AudionAdmin

    $idsToAdd = @($HardwareIds | Where-Object { -not [string]::IsNullOrWhiteSpace($_) } | Sort-Object -Unique)
    if ($idsToAdd.Count -eq 0) {
        Write-Host 'No Hardware IDs to add.'
        return
    }

    if (-not (Test-Path $script:RestrictionsPath)) {
        New-Item -Path $script:RestrictionsPath -Force | Out-Null
    }

    if (-not (Test-Path $script:DenyDeviceIdsPath)) {
        New-Item -Path $script:DenyDeviceIdsPath -Force | Out-Null
    }

    New-ItemProperty -Path $script:RestrictionsPath -Name 'DenyDeviceIDs' -Value 1 -PropertyType DWord -Force | Out-Null
    New-ItemProperty -Path $script:RestrictionsPath -Name 'DenyDeviceIDsRetroactive' -Value 1 -PropertyType DWord -Force | Out-Null

    $existingEntries = Get-AudionDenyDeviceIdEntries
    $existingValues = @($existingEntries | ForEach-Object { $_.Value })

    $usedNumbers = @($existingEntries | ForEach-Object {
        $n = 0
        if ([int]::TryParse($_.Name, [ref]$n)) {
            $n
        }
    })

    $next = 1

    foreach ($id in $idsToAdd) {
        if ($existingValues -contains $id) {
            Write-Host "Already blocked: $id"
            continue
        }

        while ($usedNumbers -contains $next) {
            $next++
        }

        New-ItemProperty -Path $script:DenyDeviceIdsPath -Name ([string]$next) -Value $id -PropertyType String -Force | Out-Null
        Write-Host "Added policy block: $id"
        $usedNumbers += $next
        $next++
    }

    $statePath = Get-AudionBlockedIdsStatePath
    $mergedState = @()
    if (Test-Path $statePath) {
        $mergedState += Get-Content -Path $statePath -ErrorAction SilentlyContinue
    }
    $mergedState += $idsToAdd
    @($mergedState | Where-Object { -not [string]::IsNullOrWhiteSpace($_) } | Sort-Object -Unique) | Set-Content -Path $statePath -Encoding UTF8
}

function Remove-AudionDenyDeviceIds {
    param(
        [Parameter(Mandatory = $true)]
        [string[]]$HardwareIds
    )

    Assert-AudionAdmin

    $idsToRemove = @($HardwareIds | Where-Object { -not [string]::IsNullOrWhiteSpace($_) } | Sort-Object -Unique)
    if ($idsToRemove.Count -eq 0) {
        Write-Host 'No Hardware IDs to remove.'
        return
    }

    if (-not (Test-Path $script:DenyDeviceIdsPath)) {
        Write-Host 'No DenyDeviceIDs policy list exists.'
        return
    }

    $entries = Get-AudionDenyDeviceIdEntries
    $remaining = New-Object System.Collections.Generic.List[string]
    $removed = New-Object System.Collections.Generic.List[string]

    foreach ($entry in $entries) {
        if ($idsToRemove -contains $entry.Value) {
            $removed.Add($entry.Value)
        } else {
            $remaining.Add($entry.Value)
        }
    }

    if ($removed.Count -eq 0) {
        Write-Host 'No matching policy entries were found.'
    } else {
        foreach ($id in ($removed | Sort-Object -Unique)) {
            Write-Host "Removed policy block: $id"
        }
    }

    Remove-Item -Path $script:DenyDeviceIdsPath -Recurse -Force -ErrorAction SilentlyContinue

    if ($remaining.Count -gt 0) {
        New-Item -Path $script:DenyDeviceIdsPath -Force | Out-Null
        $i = 1
        foreach ($id in ($remaining | Sort-Object -Unique)) {
            New-ItemProperty -Path $script:DenyDeviceIdsPath -Name ([string]$i) -Value $id -PropertyType String -Force | Out-Null
            $i++
        }

        New-ItemProperty -Path $script:RestrictionsPath -Name 'DenyDeviceIDs' -Value 1 -PropertyType DWord -Force | Out-Null
        New-ItemProperty -Path $script:RestrictionsPath -Name 'DenyDeviceIDsRetroactive' -Value 1 -PropertyType DWord -Force | Out-Null
        Write-Host 'Other device-install policy entries remain enabled.'
    } else {
        Remove-ItemProperty -Path $script:RestrictionsPath -Name 'DenyDeviceIDs' -ErrorAction SilentlyContinue
        Remove-ItemProperty -Path $script:RestrictionsPath -Name 'DenyDeviceIDsRetroactive' -ErrorAction SilentlyContinue
        Write-Host 'DenyDeviceIDs policy list is now empty.'
    }

    $statePath = Get-AudionBlockedIdsStatePath
    if (Test-Path $statePath) {
        Remove-Item -Path $statePath -Force -ErrorAction SilentlyContinue
    }
}

function Disable-AudionNvidiaAudioDevices {
    Assert-AudionAdmin

    $devices = Get-AudionNvidiaAudioDevices
    if ($devices.Count -eq 0) {
        Write-Host 'No matching NVIDIA HDMI/DP audio devices were found.'
        return
    }

    foreach ($device in $devices) {
        $label = "$($device.FriendlyName) [$($device.InstanceId)]"

        if ($device.Status -eq 'Disabled') {
            Write-Host "Already disabled: $label"
            continue
        }

        try {
            Disable-PnpDevice -InstanceId $device.InstanceId -Confirm:$false -ErrorAction Stop
            Write-Host "Disabled: $label"
        } catch {
            Write-Host "FAILED to disable: $label" -ForegroundColor Yellow
            Write-Host $_.Exception.Message -ForegroundColor Yellow
        }
    }
}

function Enable-AudionNvidiaAudioDevices {
    Assert-AudionAdmin

    $devices = Get-AudionNvidiaAudioDevices
    if ($devices.Count -eq 0) {
        Write-Host 'No matching NVIDIA HDMI/DP audio devices were found.'
        return
    }

    foreach ($device in $devices) {
        $label = "$($device.FriendlyName) [$($device.InstanceId)]"

        if ($device.Status -eq 'OK') {
            Write-Host "Already enabled: $label"
            continue
        }

        try {
            Enable-PnpDevice -InstanceId $device.InstanceId -Confirm:$false -ErrorAction Stop
            Write-Host "Enabled: $label"
        } catch {
            Write-Host "FAILED to enable: $label" -ForegroundColor Yellow
            Write-Host $_.Exception.Message -ForegroundColor Yellow
            Write-Host 'If the policy block is still enabled, run Unblock-NvidiaHdmiDpAudioPolicy.ps1 first (GUI: Hardware > NVIDIA HDMI/DP audio > Unblock policy).' -ForegroundColor Yellow
        }
    }
}

function Invoke-AudionPnpRescan {
    $pnputil = Join-Path $env:SystemRoot 'System32\pnputil.exe'
    if (Test-Path $pnputil) {
        Write-Host 'Running PnP rescan...'
        & $pnputil /scan-devices | Out-Host
    }
}

function Show-AudionNvidiaAudioStatus {
    Test-AudionPnpModule

    Write-Host ''
    Write-Host '=== NVIDIA HDMI/DP Audio Devices ==='

    $devices = Get-AudionNvidiaAudioDevices

    if ($devices.Count -eq 0) {
        Write-Host 'No matching NVIDIA HDMI/DP audio devices were detected.'
    } else {
        $devices | Select-Object Status, Class, FriendlyName, InstanceId | Format-Table -AutoSize | Out-Host

        Write-Host ''
        Write-Host '=== Hardware IDs selected for policy block ==='
        $ids = Get-AudionNvidiaAudioHardwareIds
        if ($ids.Count -eq 0) {
            Write-Host 'No NVIDIA HDAUDIO Hardware IDs were found.'
        } else {
            foreach ($id in $ids) {
                Write-Host $id
            }
        }
    }

    Write-Host ''
    Write-Host '=== Device-install policy state ==='

    if (-not (Test-Path $script:RestrictionsPath)) {
        Write-Host 'No DeviceInstall Restrictions policy key exists.'
        return
    }

    $denyEnabled = (Get-ItemProperty -Path $script:RestrictionsPath -Name 'DenyDeviceIDs' -ErrorAction SilentlyContinue).DenyDeviceIDs
    $retroactive = (Get-ItemProperty -Path $script:RestrictionsPath -Name 'DenyDeviceIDsRetroactive' -ErrorAction SilentlyContinue).DenyDeviceIDsRetroactive

    Write-Host "DenyDeviceIDs: $denyEnabled"
    Write-Host "DenyDeviceIDsRetroactive: $retroactive"

    $entries = Get-AudionDenyDeviceIdEntries
    if ($entries.Count -eq 0) {
        Write-Host 'No DenyDeviceIDs entries found.'
    } else {
        $entries | Sort-Object Name | Format-Table Name, Value -AutoSize | Out-Host
    }
}

function Export-AudionNvidiaAudioDeviceIds {
    Test-AudionPnpModule

    $outputDir = Get-AudionOutputDir
    $path = Join-Path $outputDir 'nvidia_hdmi_dp_audio_device_ids.txt'
    $lines = New-Object System.Collections.Generic.List[string]

    $lines.Add('Audion NVIDIA HDMI/DP Audio Device ID Export')
    $lines.Add(('Generated: ' + (Get-Date -Format 'yyyy-MM-dd HH:mm:ss')))
    $lines.Add('')

    $devices = Get-AudionNvidiaAudioDevices

    if ($devices.Count -eq 0) {
        $lines.Add('No matching NVIDIA HDMI/DP audio devices were detected.')
    } else {
        foreach ($device in $devices) {
            $lines.Add('DEVICE')
            $lines.Add(('  Status:       ' + $device.Status))
            $lines.Add(('  Class:        ' + $device.Class))
            $lines.Add(('  FriendlyName: ' + $device.FriendlyName))
            $lines.Add(('  InstanceId:   ' + $device.InstanceId))
            $lines.Add('  HardwareIds:')
            $hardwareIds = Get-AudionDeviceHardwareIds -InstanceId $device.InstanceId
            if ($hardwareIds.Count -eq 0) {
                $lines.Add('    <none>')
            } else {
                foreach ($id in $hardwareIds) {
                    $lines.Add(('    ' + $id))
                }
            }

            $lines.Add('  CompatibleIds:')
            $compatibleIds = Get-AudionDeviceCompatibleIds -InstanceId $device.InstanceId
            if ($compatibleIds.Count -eq 0) {
                $lines.Add('    <none>')
            } else {
                foreach ($id in $compatibleIds) {
                    $lines.Add(('    ' + $id))
                }
            }

            $lines.Add('')
        }
    }

    $lines.Add('Policy block candidates:')
    $policyIds = Get-AudionNvidiaAudioHardwareIds
    if ($policyIds.Count -eq 0) {
        $lines.Add('  <none>')
    } else {
        foreach ($id in $policyIds) {
            $lines.Add(('  ' + $id))
        }
    }

    $lines | Set-Content -Path $path -Encoding UTF8
    Write-Host "Export saved: $path"
}

Export-ModuleMember -Function *-Audion*
