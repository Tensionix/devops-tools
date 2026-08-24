# Generates fallback .reg files for manual Administrator import.
# The NVIDIA .reg files are built from the currently present NVIDIA PCI devices and current DeviceInstall policy lists.
# This script does not change the registry.

$ErrorActionPreference = 'Continue'
try { $PSNativeCommandUseErrorActionPreference = $false } catch { }

function Escape-RegString {
    param([AllowNull()][string]$Value)
    if ($null -eq $Value) { return '' }
    return ($Value -replace '\\', '\\' -replace '"', '\"')
}

function Convert-ToRegDword {
    param([int]$Value)
    return ('dword:{0:x8}' -f $Value)
}

function Write-RegFileUnicode {
    param(
        [string]$Path,
        [AllowNull()][AllowEmptyCollection()][object[]]$Lines
    )
    if ([string]::IsNullOrWhiteSpace($Path)) {
        throw 'Write-RegFileUnicode: Path is empty.'
    }
    if ($null -eq $Lines) { $Lines = @() }
    $safeLines = @($Lines | ForEach-Object {
        if ($null -eq $_) { '' } else { [string]$_ }
    })
    $text = ($safeLines -join "`r`n") + "`r`n"
    Set-Content -LiteralPath $Path -Value $text -Encoding Unicode
}

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
    try {
        $item = Get-ItemProperty -LiteralPath $Path -ErrorAction Stop
        $values = @()
        foreach ($p in $item.PSObject.Properties) {
            if ($p.Name -like 'PS*') { continue }
            if ($null -eq $p.Value) { continue }
            if ($p.Value -is [string]) { $values += [string]$p.Value }
        }
        return @($values | Where-Object { $_ -and $_.Trim().Length -gt 0 })
    } catch {
        return @()
    }
}

function Get-DevicePropertyData {
    param(
        [Parameter(Mandatory=$true)][string]$InstanceId,
        [Parameter(Mandatory=$true)][string]$KeyName
    )
    try {
        $prop = Get-PnpDeviceProperty -InstanceId $InstanceId -KeyName $KeyName -ErrorAction SilentlyContinue
        if ($null -eq $prop) { return @() }
        if ($null -eq $prop.Data) { return @() }
        if ($prop.Data -is [array]) { return @($prop.Data) }
        return @($prop.Data)
    } catch {
        return @()
    }
}

function Add-RegStringListSubkey {
    param(
        [System.Collections.Generic.List[string]]$Lines,
        [string]$KeyPath,
        [AllowNull()][AllowEmptyCollection()][object[]]$Values
    )
    if ($null -eq $Lines) { return }
    if ([string]::IsNullOrWhiteSpace($KeyPath)) { return }
    if ($null -eq $Values) { $Values = @() }
    $clean = @($Values | ForEach-Object { [string]$_ } | Where-Object { $_ -and $_.Trim().Length -gt 0 } | Select-Object -Unique)
    if ($clean.Count -eq 0) { return }
    $Lines.Add('')
    $Lines.Add("[$KeyPath]")
    $i = 1
    foreach ($value in $clean) {
        $Lines.Add(('"{0}"="{1}"' -f $i, (Escape-RegString $value)))
        $i++
    }
}

function Add-RegDeleteAndOptionalStringListSubkey {
    param(
        [System.Collections.Generic.List[string]]$Lines,
        [string]$KeyPath,
        [AllowNull()][AllowEmptyCollection()][object[]]$Values
    )
    if ($null -eq $Lines) { return }
    if ([string]::IsNullOrWhiteSpace($KeyPath)) { return }
    if ($null -eq $Values) { $Values = @() }
    $Lines.Add('')
    $Lines.Add("[-$KeyPath]")
    Add-RegStringListSubkey -Lines $Lines -KeyPath $KeyPath -Values $Values
}

function Get-NvidiaSnapshot {
    $devices = @()
    try {
        $devices = @(Get-PnpDevice -PresentOnly -ErrorAction Stop | Where-Object {
            ($_.InstanceId -like 'PCI\VEN_10DE*') -or ($_.FriendlyName -match 'NVIDIA|GeForce|RTX|GTX|Quadro|Tesla')
        })
    } catch {
        $devices = @()
    }

    $hardwareIds = @()
    $instanceIds = @()

    foreach ($device in $devices) {
        $instanceId = [string]$device.InstanceId
        if ($instanceId -like 'PCI\VEN_10DE*') {
            $instanceIds += $instanceId
        }

        $hids = @(Get-DevicePropertyData -InstanceId $instanceId -KeyName 'DEVPKEY_Device_HardwareIds' | ForEach-Object { [string]$_ } | Where-Object { $_ -like 'PCI\VEN_10DE*' })
        $hardwareIds += $hids
    }

    [pscustomobject]@{
        Devices = @($devices)
        HardwareIds = @($hardwareIds | Where-Object { $_ -and $_.Trim().Length -gt 0 } | Select-Object -Unique)
        InstanceIds = @($instanceIds | Where-Object { $_ -and $_.Trim().Length -gt 0 } | Select-Object -Unique)
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
    return @($kept + @($NewValues | ForEach-Object { [string]$_ }) | Where-Object { $_ -and $_.Trim().Length -gt 0 } | Select-Object -Unique)
}

function New-BlockAllRegLines {
    return @(
        'Windows Registry Editor Version 5.00',
        '',
        '; Audion Windows Driver Update Blocker fallback.',
        '; Import as Administrator, then run: gpupdate /target:computer /force',
        '',
        '[HKEY_LOCAL_MACHINE\SOFTWARE\Policies\Microsoft\Windows\WindowsUpdate]',
        '"ExcludeWUDriversInQualityUpdate"=dword:00000001',
        '',
        '[HKEY_LOCAL_MACHINE\SOFTWARE\Policies\Microsoft\Windows\DriverSearching]',
        '"DriverUpdateWizardWuSearchEnabled"=dword:00000000',
        '',
        '[HKEY_LOCAL_MACHINE\SOFTWARE\Microsoft\Windows\CurrentVersion\DriverSearching]',
        '"SearchOrderConfig"=dword:00000000',
        '',
        '[HKEY_LOCAL_MACHINE\SOFTWARE\Policies\Microsoft\Windows\Device Metadata]',
        '"PreventDeviceMetadataFromNetwork"=dword:00000001'
    )
}

function New-UnblockAllRegLines {
    return @(
        'Windows Registry Editor Version 5.00',
        '',
        '; Audion Windows Driver Update Blocker fallback.',
        '; Import as Administrator, then run: gpupdate /target:computer /force',
        '',
        '[HKEY_LOCAL_MACHINE\SOFTWARE\Policies\Microsoft\Windows\WindowsUpdate]',
        '"ExcludeWUDriversInQualityUpdate"=-',
        '',
        '[HKEY_LOCAL_MACHINE\SOFTWARE\Policies\Microsoft\Windows\DriverSearching]',
        '"DriverUpdateWizardWuSearchEnabled"=-',
        '',
        '[HKEY_LOCAL_MACHINE\SOFTWARE\Policies\Microsoft\Windows\Device Metadata]',
        '"PreventDeviceMetadataFromNetwork"=-',
        '',
        '[HKEY_LOCAL_MACHINE\SOFTWARE\Microsoft\Windows\CurrentVersion\DriverSearching]',
        '"SearchOrderConfig"=dword:00000001'
    )
}

function New-BlockNvidiaRegLines {
    param(
        [AllowNull()][AllowEmptyCollection()][object[]]$ExistingDeviceIds,
        [AllowNull()][AllowEmptyCollection()][object[]]$ExistingInstanceIds,
        [AllowNull()][AllowEmptyCollection()][object[]]$NewNvidiaDeviceIds,
        [AllowNull()][AllowEmptyCollection()][object[]]$NewNvidiaInstanceIds,
        [int]$Retroactive = 0
    )

    if ($null -eq $ExistingDeviceIds) { $ExistingDeviceIds = @() }
    if ($null -eq $ExistingInstanceIds) { $ExistingInstanceIds = @() }
    if ($null -eq $NewNvidiaDeviceIds) { $NewNvidiaDeviceIds = @() }
    if ($null -eq $NewNvidiaInstanceIds) { $NewNvidiaInstanceIds = @() }
    $ExistingDeviceIds = @($ExistingDeviceIds | ForEach-Object { [string]$_ } | Where-Object { $_ -and $_.Trim().Length -gt 0 })
    $ExistingInstanceIds = @($ExistingInstanceIds | ForEach-Object { [string]$_ } | Where-Object { $_ -and $_.Trim().Length -gt 0 })
    $NewNvidiaDeviceIds = @($NewNvidiaDeviceIds | ForEach-Object { [string]$_ } | Where-Object { $_ -and $_.Trim().Length -gt 0 })
    $NewNvidiaInstanceIds = @($NewNvidiaInstanceIds | ForEach-Object { [string]$_ } | Where-Object { $_ -and $_.Trim().Length -gt 0 })

    $lines = [System.Collections.Generic.List[string]]::new()
    $lines.Add('Windows Registry Editor Version 5.00')
    $lines.Add('')
    $lines.Add('; Audion Windows Driver Update Blocker fallback.')
    if ($Retroactive -eq 1) {
        $lines.Add('; DANGEROUS: retroactive mode can affect already installed matching NVIDIA devices.')
    }
    $lines.Add('; Import as Administrator, then run: gpupdate /target:computer /force')

    if ($NewNvidiaDeviceIds.Count -eq 0) {
        $lines.Add('')
        $lines.Add('; No NVIDIA Hardware IDs were detected when this file was generated.')
        $lines.Add('; Run the Status or Generate REG Fallbacks action on the target Windows machine first.')
        return $lines.ToArray()
    }

    $base = 'HKEY_LOCAL_MACHINE\SOFTWARE\Policies\Microsoft\Windows\DeviceInstall\Restrictions'
    $devKey = "$base\DenyDeviceIDs"
    $instKey = "$base\DenyInstanceIDs"

    $mergedDeviceIds = @(Merge-NvidiaList -Existing $ExistingDeviceIds -NewValues $NewNvidiaDeviceIds)
    $mergedInstanceIds = @(Merge-NvidiaList -Existing $ExistingInstanceIds -NewValues $NewNvidiaInstanceIds)

    $lines.Add('')
    $lines.Add("[$base]")
    $lines.Add('"DenyDeviceIDs"=dword:00000001')
    $lines.Add(('"DenyDeviceIDsRetroactive"={0}' -f (Convert-ToRegDword $Retroactive)))
    if ($mergedInstanceIds.Count -gt 0) {
        $lines.Add('"DenyInstanceIDs"=dword:00000001')
        $lines.Add(('"DenyInstanceIDsRetroactive"={0}' -f (Convert-ToRegDword $Retroactive)))
    }

    Add-RegDeleteAndOptionalStringListSubkey -Lines $lines -KeyPath $devKey -Values $mergedDeviceIds
    if ($mergedInstanceIds.Count -gt 0) {
        Add-RegDeleteAndOptionalStringListSubkey -Lines $lines -KeyPath $instKey -Values $mergedInstanceIds
    }

    return $lines.ToArray()
}

function New-UnblockNvidiaRegLines {
    param(
        [AllowNull()][AllowEmptyCollection()][object[]]$ExistingDeviceIds,
        [AllowNull()][AllowEmptyCollection()][object[]]$ExistingInstanceIds,
        [AllowNull()][object]$ExistingDenyDeviceIds,
        [AllowNull()][object]$ExistingDenyDeviceIdsRetroactive,
        [AllowNull()][object]$ExistingDenyInstanceIds,
        [AllowNull()][object]$ExistingDenyInstanceIdsRetroactive
    )

    if ($null -eq $ExistingDeviceIds) { $ExistingDeviceIds = @() }
    if ($null -eq $ExistingInstanceIds) { $ExistingInstanceIds = @() }
    $ExistingDeviceIds = @($ExistingDeviceIds | ForEach-Object { [string]$_ } | Where-Object { $_ -and $_.Trim().Length -gt 0 })
    $ExistingInstanceIds = @($ExistingInstanceIds | ForEach-Object { [string]$_ } | Where-Object { $_ -and $_.Trim().Length -gt 0 })

    $lines = [System.Collections.Generic.List[string]]::new()
    $lines.Add('Windows Registry Editor Version 5.00')
    $lines.Add('')
    $lines.Add('; Audion Windows Driver Update Blocker fallback.')
    $lines.Add('; Removes NVIDIA-specific PCI\\VEN_10DE entries from Device Installation Restrictions.')
    $lines.Add('; Import as Administrator, then run: gpupdate /target:computer /force')

    $base = 'HKEY_LOCAL_MACHINE\SOFTWARE\Policies\Microsoft\Windows\DeviceInstall\Restrictions'
    $devKey = "$base\DenyDeviceIDs"
    $instKey = "$base\DenyInstanceIDs"

    $keptDeviceIds = @($ExistingDeviceIds | Where-Object { $_ -notlike 'PCI\VEN_10DE*' })
    $keptInstanceIds = @($ExistingInstanceIds | Where-Object { $_ -notlike 'PCI\VEN_10DE*' })

    Add-RegDeleteAndOptionalStringListSubkey -Lines $lines -KeyPath $devKey -Values $keptDeviceIds
    Add-RegDeleteAndOptionalStringListSubkey -Lines $lines -KeyPath $instKey -Values $keptInstanceIds

    $lines.Add('')
    $lines.Add("[$base]")

    if ($keptDeviceIds.Count -gt 0) {
        $d = 1
        if ($null -ne $ExistingDenyDeviceIds) { $d = [int]$ExistingDenyDeviceIds }
        $r = 0
        if ($null -ne $ExistingDenyDeviceIdsRetroactive) { $r = [int]$ExistingDenyDeviceIdsRetroactive }
        $lines.Add(('"DenyDeviceIDs"={0}' -f (Convert-ToRegDword $d)))
        $lines.Add(('"DenyDeviceIDsRetroactive"={0}' -f (Convert-ToRegDword $r)))
    } else {
        $lines.Add('"DenyDeviceIDs"=-')
        $lines.Add('"DenyDeviceIDsRetroactive"=-')
    }

    if ($keptInstanceIds.Count -gt 0) {
        $d = 1
        if ($null -ne $ExistingDenyInstanceIds) { $d = [int]$ExistingDenyInstanceIds }
        $r = 0
        if ($null -ne $ExistingDenyInstanceIdsRetroactive) { $r = [int]$ExistingDenyInstanceIdsRetroactive }
        $lines.Add(('"DenyInstanceIDs"={0}' -f (Convert-ToRegDword $d)))
        $lines.Add(('"DenyInstanceIDsRetroactive"={0}' -f (Convert-ToRegDword $r)))
    } else {
        $lines.Add('"DenyInstanceIDs"=-')
        $lines.Add('"DenyInstanceIDsRetroactive"=-')
    }

    return $lines.ToArray()
}

$ScriptRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
if (-not $ScriptRoot) { $ScriptRoot = (Get-Location).Path }
$ProjectRoot = (Resolve-Path -LiteralPath (Join-Path $ScriptRoot '..\..')).Path

$RegFallbackDir = Join-Path $ProjectRoot 'output\driver_guard\reg_fallback'
New-Item -ItemType Directory -Force -Path $RegFallbackDir | Out-Null

$basePs = 'HKLM:\SOFTWARE\Policies\Microsoft\Windows\DeviceInstall\Restrictions'
$deviceKeyPs = Join-Path $basePs 'DenyDeviceIDs'
$instanceKeyPs = Join-Path $basePs 'DenyInstanceIDs'

$existingDeviceIds = @(Get-StringValuesFromSubkey -Path $deviceKeyPs)
$existingInstanceIds = @(Get-StringValuesFromSubkey -Path $instanceKeyPs)
$denyDeviceIds = Get-RegValueSafe -Path $basePs -Name 'DenyDeviceIDs'
$denyDeviceIdsRetro = Get-RegValueSafe -Path $basePs -Name 'DenyDeviceIDsRetroactive'
$denyInstanceIds = Get-RegValueSafe -Path $basePs -Name 'DenyInstanceIDs'
$denyInstanceIdsRetro = Get-RegValueSafe -Path $basePs -Name 'DenyInstanceIDsRetroactive'

$nvidia = Get-NvidiaSnapshot

Write-RegFileUnicode -Path (Join-Path $RegFallbackDir 'Run_Block_All.reg') -Lines (New-BlockAllRegLines)
Write-RegFileUnicode -Path (Join-Path $RegFallbackDir 'Run_Unblock_All.reg') -Lines (New-UnblockAllRegLines)
Write-RegFileUnicode -Path (Join-Path $RegFallbackDir 'Run_Block_NVIDIA.reg') -Lines (New-BlockNvidiaRegLines -ExistingDeviceIds $existingDeviceIds -ExistingInstanceIds $existingInstanceIds -NewNvidiaDeviceIds $nvidia.HardwareIds -NewNvidiaInstanceIds $nvidia.InstanceIds -Retroactive 0)
Write-RegFileUnicode -Path (Join-Path $RegFallbackDir 'Run_Block_NVIDIA_Retroactive_DANGEROUS.reg') -Lines (New-BlockNvidiaRegLines -ExistingDeviceIds $existingDeviceIds -ExistingInstanceIds $existingInstanceIds -NewNvidiaDeviceIds $nvidia.HardwareIds -NewNvidiaInstanceIds $nvidia.InstanceIds -Retroactive 1)
Write-RegFileUnicode -Path (Join-Path $RegFallbackDir 'Run_Unblock_NVIDIA.reg') -Lines (New-UnblockNvidiaRegLines -ExistingDeviceIds $existingDeviceIds -ExistingInstanceIds $existingInstanceIds -ExistingDenyDeviceIds $denyDeviceIds -ExistingDenyDeviceIdsRetroactive $denyDeviceIdsRetro -ExistingDenyInstanceIds $denyInstanceIds -ExistingDenyInstanceIdsRetroactive $denyInstanceIdsRetro)

Write-Host ''
Write-Host 'Fallback REG files written:' -ForegroundColor Cyan
Write-Host "  $(Join-Path $RegFallbackDir 'Run_Block_All.reg')"
Write-Host "  $(Join-Path $RegFallbackDir 'Run_Block_NVIDIA.reg')"
Write-Host "  $(Join-Path $RegFallbackDir 'Run_Block_NVIDIA_Retroactive_DANGEROUS.reg')"
Write-Host "  $(Join-Path $RegFallbackDir 'Run_Unblock_All.reg')"
Write-Host "  $(Join-Path $RegFallbackDir 'Run_Unblock_NVIDIA.reg')"
Write-Host ''
Write-Host "Detected NVIDIA Hardware IDs: $($nvidia.HardwareIds.Count)"
Write-Host "Detected NVIDIA Instance IDs: $($nvidia.InstanceIds.Count)"
if ($nvidia.HardwareIds.Count -eq 0) {
    Write-Host 'WARNING: NVIDIA block REG files are no-op until NVIDIA Hardware IDs are detected.' -ForegroundColor Yellow
}
