# Adds/removes Device Installation Restrictions for explicit Hardware IDs.
# This is the generic version of the earlier Intel Iris Xe per-HWID guard.

[CmdletBinding()]
param(
    [string[]]$HardwareId,
    [string]$HardwareIdList,
    [string]$DeviceInstanceId,
    [switch]$Unblock,
    [switch]$Status,
    [switch]$Retroactive,
    [switch]$KeepGlobalWindowsUpdateDriverBlock,
    [switch]$NoGpUpdate
)

$ErrorActionPreference = 'Stop'
try { $PSNativeCommandUseErrorActionPreference = $false } catch { }
try {
    $utf8NoBom = New-Object System.Text.UTF8Encoding($false)
    [Console]::OutputEncoding = $utf8NoBom
    $OutputEncoding = $utf8NoBom
} catch { }

$restrictionsKey = 'HKLM:\SOFTWARE\Policies\Microsoft\Windows\DeviceInstall\Restrictions'
$denyDeviceIdsKey = Join-Path $restrictionsKey 'DenyDeviceIDs'
$windowsUpdateKey = 'HKLM:\SOFTWARE\Policies\Microsoft\Windows\WindowsUpdate'
$builtInHardwareIdCacheName = 'Intel Iris Xe / VEN_8086 DEV_46A8'
$builtInRecommendedHardwareIds = @(
    'PCI\VEN_8086&DEV_46A8&SUBSYS_22E717AA'
)
$builtInCleanupAliasHardwareIds = @(
    'PCI\VEN_8086&DEV_46A8&SUBSYS_22E717AA&REV_0C'
)

function Test-Admin {
    $identity = [Security.Principal.WindowsIdentity]::GetCurrent()
    $principal = New-Object Security.Principal.WindowsPrincipal($identity)
    return $principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
}

function Assert-Administrator {
    if (-not (Test-Admin)) {
        Write-Host 'ERROR: Run this script as Administrator.' -ForegroundColor Red
        exit 1
    }
}

function Write-Section {
    param([string]$Title)
    Write-Host ''
    Write-Host "=== $Title ===" -ForegroundColor Cyan
}

function Write-Utf8ConsoleText {
    param([AllowNull()][string]$Text)
    if ([string]::IsNullOrEmpty($Text)) { return }
    try {
        $payload = $Text + [Environment]::NewLine
        $bytes = [System.Text.Encoding]::UTF8.GetBytes($payload)
        $stream = [Console]::OpenStandardOutput()
        $stream.Write($bytes, 0, $bytes.Length)
        $stream.Flush()
    } catch {
        Write-Host $Text
    }
}

function Get-WindowsAnsiEncoding {
    try {
        [System.Text.Encoding]::RegisterProvider([System.Text.CodePagesEncodingProvider]::Instance)
    } catch { }
    try {
        return [System.Text.Encoding]::GetEncoding([System.Globalization.CultureInfo]::CurrentCulture.TextInfo.ANSICodePage)
    } catch {
        return [Console]::OutputEncoding
    }
}

function Test-TextHasCharRange {
    param(
        [AllowNull()][string]$Text,
        [Parameter(Mandatory=$true)][int]$Start,
        [Parameter(Mandatory=$true)][int]$End
    )
    if ([string]::IsNullOrEmpty($Text)) { return $false }
    foreach ($char in $Text.ToCharArray()) {
        $code = [int][char]$char
        if ($code -ge $Start -and $code -le $End) { return $true }
    }
    return $false
}

function Repair-Cp1251MojibakeText {
    param([AllowNull()][string]$Text)
    if ([string]::IsNullOrEmpty($Text)) { return $Text }
    if (Test-TextHasCharRange -Text $Text -Start 0x0400 -End 0x04FF) { return $Text }
    if (-not (Test-TextHasCharRange -Text $Text -Start 0x00C0 -End 0x00FF)) { return $Text }
    try {
        $latin1 = [System.Text.Encoding]::GetEncoding(28591)
        $cp1251 = [System.Text.Encoding]::GetEncoding(1251)
        return $cp1251.GetString($latin1.GetBytes($Text))
    } catch {
        return $Text
    }
}

function ConvertTo-WindowsCommandLineArgument {
    param([AllowNull()][string]$Argument)

    if ($null -eq $Argument) { return '""' }
    if ($Argument.Length -eq 0) { return '""' }
    if ($Argument -notmatch '[\s"]') { return $Argument }

    $result = [System.Text.StringBuilder]::new()
    [void]$result.Append('"')
    $backslashes = 0
    foreach ($char in $Argument.ToCharArray()) {
        if ($char -eq '\') {
            $backslashes += 1
            continue
        }
        if ($char -eq '"') {
            [void]$result.Append('\' * ($backslashes * 2 + 1))
            [void]$result.Append('"')
            $backslashes = 0
            continue
        }
        if ($backslashes -gt 0) {
            [void]$result.Append('\' * $backslashes)
            $backslashes = 0
        }
        [void]$result.Append($char)
    }
    if ($backslashes -gt 0) {
        [void]$result.Append('\' * ($backslashes * 2))
    }
    [void]$result.Append('"')
    return $result.ToString()
}

function Join-WindowsCommandLineArguments {
    param([AllowNull()][AllowEmptyCollection()][string[]]$Arguments)

    $items = @()
    foreach ($argument in @($Arguments)) {
        if ($null -eq $argument) { continue }
        $items += ConvertTo-WindowsCommandLineArgument -Argument ([string]$argument)
    }
    return ($items -join ' ')
}

function Invoke-NativeText {
    param(
        [Parameter(Mandatory=$true)][string]$FilePath,
        [AllowNull()][AllowEmptyCollection()][string[]]$Arguments,
        [int[]]$SuccessExitCodes = @(0),
        [switch]$AllowFailure
    )

    $psi = [System.Diagnostics.ProcessStartInfo]::new()
    $psi.FileName = $FilePath
    $psi.Arguments = Join-WindowsCommandLineArguments -Arguments $Arguments
    $psi.UseShellExecute = $false
    $psi.RedirectStandardOutput = $true
    $psi.RedirectStandardError = $true
    $psi.CreateNoWindow = $true
    $encoding = Get-WindowsAnsiEncoding
    try { $psi.StandardOutputEncoding = $encoding } catch { }
    try { $psi.StandardErrorEncoding = $encoding } catch { }

    $proc = [System.Diagnostics.Process]::new()
    $proc.StartInfo = $psi
    [void]$proc.Start()
    $stdout = $proc.StandardOutput.ReadToEnd()
    $stderr = $proc.StandardError.ReadToEnd()
    $proc.WaitForExit()
    $script:LastNativeExitCode = $proc.ExitCode

    $text = $stdout
    if (-not [string]::IsNullOrWhiteSpace($stderr)) {
        $text = $stdout.TrimEnd() + "`r`n" + $stderr
    }
    $text = Repair-Cp1251MojibakeText -Text $text

    if ($SuccessExitCodes -notcontains $proc.ExitCode -and -not $AllowFailure) {
        throw "$FilePath failed with exit code $($proc.ExitCode). $($text.Trim())"
    }
    return $text
}

function Write-NativeText {
    param(
        [Parameter(Mandatory=$true)][string]$FilePath,
        [AllowNull()][AllowEmptyCollection()][string[]]$Arguments,
        [int[]]$SuccessExitCodes = @(0),
        [switch]$AllowFailure
    )

    $text = Invoke-NativeText -FilePath $FilePath -Arguments $Arguments -SuccessExitCodes $SuccessExitCodes -AllowFailure:$AllowFailure
    if (-not [string]::IsNullOrWhiteSpace($text)) {
        Write-Utf8ConsoleText $text.TrimEnd()
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

function New-DirIfMissing {
    param([Parameter(Mandatory=$true)][string]$Path)
    if (-not (Test-Path -LiteralPath $Path)) {
        New-Item -ItemType Directory -Path $Path -Force | Out-Null
    }
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
        Write-Host "WARNING: Backup export failed for $RegPath. reg.exe exit code: $exitCode" -ForegroundColor Yellow
    }
}

function Split-IdText {
    param([AllowNull()][AllowEmptyCollection()][object[]]$Items)

    $result = @()
    if ($null -eq $Items) { return @() }
    foreach ($item in $Items) {
        if ($null -eq $item) { continue }
        $parts = [regex]::Split([string]$item, '[\r\n,;]+')
        foreach ($part in $parts) {
            $value = ([string]$part).Trim().Trim('"').Trim("'")
            if (-not $value) { continue }
            $result += $value
        }
    }
    return @($result | Select-Object -Unique)
}

function Get-TargetHardwareIds {
    $items = @()
    if ($HardwareId) { $items += $HardwareId }
    if ($HardwareIdList) { $items += $HardwareIdList }
    $ids = @(Split-IdText -Items $items)

    if ($ids.Count -eq 0) {
        Write-Host "Using built-in HWID cache: $builtInHardwareIdCacheName" -ForegroundColor Yellow
        Write-Host 'Recommended lock ID is used; REV alias is matched by prefix during status/unblock.'
        $ids = @($builtInRecommendedHardwareIds)
    }

    foreach ($id in $ids) {
        if ($id -match '^[^\\]+\\[^\\]+\\') {
            Write-Host "WARNING: '$id' looks like a Device Instance ID. DenyDeviceIDs expects a Hardware ID." -ForegroundColor Yellow
        }
    }

    return @($ids)
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
        [Parameter(Mandatory=$true)][string]$Path,
        [AllowNull()][AllowEmptyCollection()][object[]]$Values
    )

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

function Remove-PolicyValueIfExists {
    param(
        [Parameter(Mandatory=$true)][string]$Path,
        [Parameter(Mandatory=$true)][string]$Name
    )
    if (-not (Test-Path -LiteralPath $Path)) { return }
    $prop = Get-ItemProperty -LiteralPath $Path -Name $Name -ErrorAction SilentlyContinue
    if ($null -ne $prop) {
        Remove-ItemProperty -LiteralPath $Path -Name $Name -Force
    }
}

function Remove-GlobalWindowsUpdateDriverBlock {
    if (Test-Path -LiteralPath $windowsUpdateKey) {
        Remove-ItemProperty -LiteralPath $windowsUpdateKey -Name ExcludeWUDriversInQualityUpdate -ErrorAction SilentlyContinue
    }
    Write-Host 'Global ExcludeWUDriversInQualityUpdate removed or was absent.'
}

function Test-HardwareIdMatch {
    param(
        [Parameter(Mandatory=$true)][string]$Candidate,
        [Parameter(Mandatory=$true)][string]$Target
    )

    $candidateText = $Candidate.Trim()
    $targetText = $Target.Trim()
    if (-not $candidateText -or -not $targetText) { return $false }

    if ($candidateText.Equals($targetText, [StringComparison]::OrdinalIgnoreCase)) { return $true }
    if ($candidateText.StartsWith($targetText + '&', [StringComparison]::OrdinalIgnoreCase)) { return $true }
    if ($candidateText.StartsWith($targetText + '\', [StringComparison]::OrdinalIgnoreCase)) { return $true }
    return $false
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

function Find-MatchingPnpDevices {
    param([AllowNull()][AllowEmptyCollection()][object[]]$TargetHardwareIds)

    if ($null -eq $TargetHardwareIds -or $TargetHardwareIds.Count -eq 0) { return @() }
    try {
        $devices = @(Get-PnpDevice -PresentOnly -ErrorAction Stop)
    } catch {
        Write-Host "Could not query present PnP devices: $($_.Exception.Message)" -ForegroundColor Yellow
        return @()
    }

    $prefixes = @($TargetHardwareIds | ForEach-Object { ([string]$_).Trim() } | Where-Object { $_ -and $_.Contains('\') } | Select-Object -Unique)
    if ($prefixes.Count -gt 0) {
        $devices = @($devices | Where-Object {
            $instanceId = [string]$_.InstanceId
            $matchedPrefix = $false
            foreach ($prefix in $prefixes) {
                if ($instanceId.StartsWith($prefix, [StringComparison]::OrdinalIgnoreCase)) {
                    $matchedPrefix = $true
                    break
                }
            }
            $matchedPrefix
        })
    }

    $matches = @()
    foreach ($device in $devices) {
        $instanceId = [string]$device.InstanceId
        $hids = @(Get-DevicePropertyData -InstanceId $instanceId -KeyName 'DEVPKEY_Device_HardwareIds' | ForEach-Object { [string]$_ })
        $matchedIds = @()
        foreach ($candidate in $hids) {
            foreach ($target in $TargetHardwareIds) {
                if (Test-HardwareIdMatch -Candidate $candidate -Target ([string]$target)) {
                    $matchedIds += $candidate
                    break
                }
            }
        }
        if ($matchedIds.Count -gt 0) {
            $matches += [pscustomobject]@{
                FriendlyName = $device.FriendlyName
                Class = $device.Class
                Status = $device.Status
                InstanceId = $instanceId
                MatchingHardwareIds = @($matchedIds | Select-Object -Unique)
            }
        }
    }
    return @($matches)
}

function Show-Status {
    param(
        [AllowNull()][AllowEmptyCollection()][object[]]$TargetHardwareIds,
        [string]$InstanceId
    )

    $deviceList = @(Get-StringValuesFromSubkey -Path $denyDeviceIdsKey)
    $matchingPolicyIds = @()
    if ($TargetHardwareIds -and $TargetHardwareIds.Count -gt 0) {
        foreach ($existing in $deviceList) {
            foreach ($target in $TargetHardwareIds) {
                if (Test-HardwareIdMatch -Candidate ([string]$existing) -Target ([string]$target)) {
                    $matchingPolicyIds += $existing
                    break
                }
            }
        }
    }

    Write-Section 'Device Installation Restrictions'
    Write-Host "DenyDeviceIDs: $(Get-RegValueSafe -Path $restrictionsKey -Name 'DenyDeviceIDs')"
    Write-Host "DenyDeviceIDsRetroactive: $(Get-RegValueSafe -Path $restrictionsKey -Name 'DenyDeviceIDsRetroactive')"
    Write-Host "Total denied Hardware IDs: $($deviceList.Count)"
    if ($TargetHardwareIds -and $TargetHardwareIds.Count -gt 0) {
        Write-Host "Matching target Hardware IDs in policy: $($matchingPolicyIds.Count)"
        $matchingPolicyIds | ForEach-Object { Write-Host "  $_" }
    } elseif ($deviceList.Count -gt 0) {
        Write-Host 'Denied Hardware IDs:'
        $deviceList | ForEach-Object { Write-Host "  $_" }
    }

    Write-Section 'Windows Update driver policy'
    Write-Host "ExcludeWUDriversInQualityUpdate: $(Get-RegValueSafe -Path $windowsUpdateKey -Name 'ExcludeWUDriversInQualityUpdate')"

    $matches = @(Find-MatchingPnpDevices -TargetHardwareIds $TargetHardwareIds)
    if ($TargetHardwareIds -and $TargetHardwareIds.Count -gt 0) {
        Write-Section 'Present matching PnP devices'
        if ($matches.Count -eq 0) {
            Write-Host 'No present devices matched the supplied Hardware IDs.'
        } else {
            $matches | Select-Object FriendlyName, Class, Status, InstanceId | Format-Table -AutoSize | Out-Host
        }
    }

    $instanceIds = @()
    if ($InstanceId) { $instanceIds += $InstanceId }
    foreach ($match in $matches) { $instanceIds += $match.InstanceId }
    $instanceIds = @($instanceIds | Where-Object { $_ -and $_.Trim().Length -gt 0 } | Select-Object -Unique)

    foreach ($id in $instanceIds) {
        Write-Section "PnP driver rank: $id"
        Write-NativeText -FilePath 'pnputil.exe' -Arguments @('/enum-devices', '/instanceid', $id, '/drivers') -AllowFailure
    }
}

$targetHardwareIds = @(Get-TargetHardwareIds)

if (-not $Status -and $targetHardwareIds.Count -eq 0) {
    Write-Host 'ERROR: No Hardware IDs were supplied.' -ForegroundColor Red
    exit 2
}

if ($Status) {
    Show-Status -TargetHardwareIds $targetHardwareIds -InstanceId $DeviceInstanceId
    exit 0
}

Assert-Administrator

$ScriptRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$ProjectRoot = (Resolve-Path -LiteralPath (Join-Path $ScriptRoot '..\..')).Path
$BackupDir = Join-Path $ProjectRoot 'backup\driver_guard\policy'
$StateDir = Join-Path $ProjectRoot 'data\driver_guard'
New-DirIfMissing $BackupDir
New-DirIfMissing $StateDir
$Stamp = Get-Date -Format 'yyyyMMdd_HHmmss'

Export-RegKeyIfExists 'HKLM\SOFTWARE\Policies\Microsoft\Windows\DeviceInstall\Restrictions' (Join-Path $BackupDir "DeviceInstall_Restrictions_before_hwid_$Stamp.reg")
Export-RegKeyIfExists 'HKLM\SOFTWARE\Policies\Microsoft\Windows\WindowsUpdate' (Join-Path $BackupDir "WindowsUpdate_policy_before_hwid_$Stamp.reg")

$existingDeviceIds = @(Get-StringValuesFromSubkey -Path $denyDeviceIdsKey)

if ($Unblock) {
    Write-Section 'Remove per-Hardware-ID driver block'
    $keptDeviceIds = @()
    foreach ($existing in $existingDeviceIds) {
        $remove = $false
        foreach ($target in $targetHardwareIds) {
            if (Test-HardwareIdMatch -Candidate ([string]$existing) -Target ([string]$target)) {
                $remove = $true
                break
            }
        }
        if (-not $remove) { $keptDeviceIds += $existing }
    }

    Write-NumberedStringSubkeyOrRemove -Path $denyDeviceIdsKey -Values $keptDeviceIds
    if ($keptDeviceIds.Count -eq 0) {
        Remove-PolicyValueIfExists -Path $restrictionsKey -Name 'DenyDeviceIDs'
        Remove-PolicyValueIfExists -Path $restrictionsKey -Name 'DenyDeviceIDsRetroactive'
    }

    Write-Host "Removed matching Hardware IDs: $($existingDeviceIds.Count - $keptDeviceIds.Count)"
} else {
    Write-Section 'Apply per-Hardware-ID driver block'
    $mergedDeviceIds = @($existingDeviceIds + $targetHardwareIds | Where-Object { $_ -and $_.Trim().Length -gt 0 } | Select-Object -Unique)

    New-Item -Path $restrictionsKey -Force | Out-Null
    New-ItemProperty -Path $restrictionsKey -Name 'DenyDeviceIDs' -PropertyType DWord -Value 1 -Force | Out-Null
    New-ItemProperty -Path $restrictionsKey -Name 'DenyDeviceIDsRetroactive' -PropertyType DWord -Value ([int][bool]$Retroactive) -Force | Out-Null
    Write-NumberedStringSubkeyOrRemove -Path $denyDeviceIdsKey -Values $mergedDeviceIds

    Write-Host 'Blocked Hardware IDs:'
    $targetHardwareIds | ForEach-Object { Write-Host "  $_" }
    Write-Host "Retroactive=$([bool]$Retroactive)"
}

if (-not $KeepGlobalWindowsUpdateDriverBlock) {
    Write-Section 'Remove global Windows Update driver block'
    Remove-GlobalWindowsUpdateDriverBlock
}

$state = [pscustomobject]@{
    CreatedAt = (Get-Date).ToString('yyyy-MM-dd HH:mm:ss')
    Action = if ($Unblock) { 'unblock' } else { 'block' }
    Retroactive = [bool]$Retroactive
    HardwareIds = @($targetHardwareIds)
    KeepGlobalWindowsUpdateDriverBlock = [bool]$KeepGlobalWindowsUpdateDriverBlock
}
$statePath = Join-Path $StateDir 'HWID_DeviceInstall_Block_State.json'
$state | ConvertTo-Json -Depth 6 | Set-Content -LiteralPath $statePath -Encoding UTF8
Write-Host "State saved: $statePath"

if (-not $NoGpUpdate) {
    Write-Section 'Refresh policy'
    Write-NativeText -FilePath 'gpupdate.exe' -Arguments @('/target:computer', '/force') -AllowFailure
}

Show-Status -TargetHardwareIds $targetHardwareIds -InstanceId $DeviceInstanceId
