# Repairs a driver-rank downgrade for a device selected by Hardware ID.
# It generalizes the Intel Iris Xe OEM rank repair script while keeping the Intel defaults.

[CmdletBinding()]
param(
    [string[]]$HardwareId,
    [string]$HardwareIdList,
    [string]$DeviceInstanceId,
    [string]$BadVersion = '32.0.101.7026',
    [string]$TargetVersion = '32.0.101.7085',
    [string]$TargetInfPath,
    [string]$TargetInfNamePattern = '*.inf',
    [string]$DriverClass = 'Display',
    [switch]$SkipCurrentVersionCheck,
    [switch]$AllowVersionOnlyTargetInfFallback,
    [switch]$KeepGlobalWindowsUpdateDriverBlock,
    [switch]$NoPolicyBlock,
    [switch]$Status
)

$ErrorActionPreference = 'Stop'
try { $PSNativeCommandUseErrorActionPreference = $false } catch { }
try {
    $utf8NoBom = New-Object System.Text.UTF8Encoding($false)
    [Console]::OutputEncoding = $utf8NoBom
    $OutputEncoding = $utf8NoBom
} catch { }

$restrictionsKey = 'HKLM:\SOFTWARE\Policies\Microsoft\Windows\DeviceInstall\Restrictions'
$denyListKey = Join-Path $restrictionsKey 'DenyDeviceIDs'
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

function Write-TextFileUtf8 {
    param(
        [Parameter(Mandatory=$true)][string]$Path,
        [AllowNull()][string]$Text
    )
    if ($null -eq $Text) { $Text = '' }
    $utf8NoBom = [System.Text.UTF8Encoding]::new($false)
    [System.IO.File]::WriteAllText($Path, $Text, $utf8NoBom)
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
        Write-Host "WARNING: Backup export failed for $RegPath. reg.exe exit code: $exitCode" -ForegroundColor Yellow
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

function New-DirIfMissing {
    param([Parameter(Mandatory=$true)][string]$Path)
    if (-not (Test-Path -LiteralPath $Path)) {
        New-Item -ItemType Directory -Path $Path -Force | Out-Null
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
    return @($ids)
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
        foreach ($candidate in $hids) {
            $matched = $false
            foreach ($target in $TargetHardwareIds) {
                if (Test-HardwareIdMatch -Candidate $candidate -Target ([string]$target)) {
                    $matched = $true
                    break
                }
            }
            if ($matched) {
                $matches += [pscustomobject]@{
                    FriendlyName = $device.FriendlyName
                    Class = $device.Class
                    Status = $device.Status
                    InstanceId = $instanceId
                    HardwareIds = @($hids)
                }
                break
            }
        }
    }
    return @($matches)
}

function Resolve-TargetDeviceInstanceId {
    param([AllowNull()][AllowEmptyCollection()][object[]]$TargetHardwareIds)

    if ($DeviceInstanceId -and $DeviceInstanceId.Trim().Length -gt 0) {
        return $DeviceInstanceId.Trim()
    }

    $matches = @(Find-MatchingPnpDevices -TargetHardwareIds $TargetHardwareIds)
    if ($matches.Count -eq 0) {
        throw 'No present device matched the supplied Hardware IDs. Supply -DeviceInstanceId if the device is hidden/offline.'
    }
    if ($matches.Count -gt 1) {
        Write-Host 'Multiple present devices matched the supplied Hardware IDs:' -ForegroundColor Yellow
        $matches | Select-Object FriendlyName, Class, Status, InstanceId | Format-Table -AutoSize | Out-Host
        throw 'Multiple devices matched. Re-run with -DeviceInstanceId.'
    }
    return [string]$matches[0].InstanceId
}

function Get-SignedDriverForDevice {
    param([Parameter(Mandatory=$true)][string]$InstanceId)
    return Get-CimInstance Win32_PnPSignedDriver |
        Where-Object { [string]$_.DeviceID -ieq $InstanceId } |
        Select-Object -First 1
}

function Get-FirstDevicePropertyString {
    param(
        [Parameter(Mandatory=$true)][string]$InstanceId,
        [Parameter(Mandatory=$true)][string]$KeyName
    )

    $values = @(Get-DevicePropertyData -InstanceId $InstanceId -KeyName $KeyName)
    if ($values.Count -eq 0 -or $null -eq $values[0]) { return $null }
    return [string]$values[0]
}

function Get-ObjectPropertyValue {
    param(
        [AllowNull()][object]$Object,
        [Parameter(Mandatory=$true)][string]$Name
    )
    if ($null -eq $Object) { return $null }
    $property = $Object.PSObject.Properties[$Name]
    if ($null -eq $property) { return $null }
    return $property.Value
}

function Format-ClassGuidForRegPath {
    param([AllowNull()][string]$ClassGuid)
    if ([string]::IsNullOrWhiteSpace($ClassGuid)) { return $null }
    $clean = $ClassGuid.Trim()
    if ($clean.StartsWith('{') -and $clean.EndsWith('}')) { return $clean }
    return "{$clean}"
}

function Convert-PnpPropertyDataForJson {
    param([AllowNull()][object]$Data)
    if ($null -eq $Data) { return $null }
    if ($Data -is [array]) {
        return @($Data | ForEach-Object { if ($null -eq $_) { $null } else { [string]$_ } })
    }
    return [string]$Data
}

function New-DeviceRepairPreflightBackup {
    param(
        [Parameter(Mandatory=$true)][string]$Root,
        [Parameter(Mandatory=$true)][string]$InstanceId,
        [AllowNull()][AllowEmptyCollection()][object[]]$TargetHardwareIds,
        [AllowNull()][object]$SignedDriver,
        [AllowNull()][string]$BeforeReport,
        [AllowNull()][string]$ClassDriversText,
        [AllowNull()][string]$DriverClassName,
        [AllowNull()][string]$CurrentVersion,
        [AllowNull()][string]$ExpectedBadVersion,
        [AllowNull()][string]$ExpectedTargetVersion
    )

    $preflightDir = Join-Path $Root 'preflight_backup'
    New-DirIfMissing $preflightDir

    Write-Section 'Preflight backup bundle'
    Write-Host "preflightDir=$preflightDir"

    Export-RegKeyIfExists 'HKLM\SOFTWARE\Policies\Microsoft\Windows\DeviceInstall\Restrictions' (Join-Path $preflightDir 'policy_DeviceInstall_Restrictions_before.reg')
    Export-RegKeyIfExists 'HKLM\SOFTWARE\Policies\Microsoft\Windows\WindowsUpdate' (Join-Path $preflightDir 'policy_WindowsUpdate_before.reg')
    Export-RegKeyIfExists "HKLM\SYSTEM\CurrentControlSet\Enum\$InstanceId" (Join-Path $preflightDir 'device_enum_before.reg')

    $classGuid = Get-FirstDevicePropertyString -InstanceId $InstanceId -KeyName 'DEVPKEY_Device_ClassGuid'
    if (-not $classGuid) { $classGuid = [string](Get-ObjectPropertyValue -Object $SignedDriver -Name 'ClassGuid') }
    $classGuidForReg = Format-ClassGuidForRegPath -ClassGuid $classGuid
    if ($classGuidForReg) {
        Export-RegKeyIfExists "HKLM\SYSTEM\CurrentControlSet\Control\Class\$classGuidForReg" (Join-Path $preflightDir 'class_before.reg')
    }

    $driverKey = Get-FirstDevicePropertyString -InstanceId $InstanceId -KeyName 'DEVPKEY_Device_Driver'
    if ($driverKey) {
        Export-RegKeyIfExists "HKLM\SYSTEM\CurrentControlSet\Control\Class\$driverKey" (Join-Path $preflightDir 'driver_instance_before.reg')
    }

    $serviceName = Get-FirstDevicePropertyString -InstanceId $InstanceId -KeyName 'DEVPKEY_Device_Service'
    if ($serviceName) {
        Export-RegKeyIfExists "HKLM\SYSTEM\CurrentControlSet\Services\$serviceName" (Join-Path $preflightDir 'service_before.reg')
    }

    Write-TextFileUtf8 -Path (Join-Path $preflightDir 'before_device_drivers.txt') -Text $BeforeReport
    Write-TextFileUtf8 -Path (Join-Path $preflightDir 'before_class_drivers.txt') -Text $ClassDriversText

    $pnpDevice = $null
    try {
        $pnpDevice = Get-PnpDevice -InstanceId $InstanceId -ErrorAction Stop
    } catch { }

    $pnpProperties = @()
    try {
        foreach ($property in @(Get-PnpDeviceProperty -InstanceId $InstanceId -ErrorAction Stop)) {
            $pnpProperties += [pscustomobject]@{
                KeyName = [string]$property.KeyName
                Type = [string]$property.Type
                Data = Convert-PnpPropertyDataForJson -Data $property.Data
            }
        }
    } catch {
        $pnpProperties += [pscustomobject]@{
            KeyName = 'ERROR'
            Type = 'Exception'
            Data = $_.Exception.Message
        }
    }

    $snapshot = [pscustomobject]@{
        CreatedAt = (Get-Date).ToString('yyyy-MM-dd HH:mm:ss')
        BackupKind = 'HWID rank repair preflight'
        DeviceInstanceId = $InstanceId
        TargetHardwareIds = @($TargetHardwareIds)
        DriverClass = $DriverClassName
        CurrentVersion = $CurrentVersion
        BadDriverVersion = $ExpectedBadVersion
        TargetDriverVersion = $ExpectedTargetVersion
        AllowVersionOnlyTargetInfFallback = [bool]$AllowVersionOnlyTargetInfFallback
        TargetInfPath = $TargetInfPath
        TargetInfNamePattern = $TargetInfNamePattern
        ClassGuid = $classGuidForReg
        DriverKey = $driverKey
        Service = $serviceName
        PnpDevice = if ($pnpDevice) {
            [pscustomobject]@{
                FriendlyName = [string](Get-ObjectPropertyValue -Object $pnpDevice -Name 'FriendlyName')
                Class = [string](Get-ObjectPropertyValue -Object $pnpDevice -Name 'Class')
                Status = [string](Get-ObjectPropertyValue -Object $pnpDevice -Name 'Status')
                InstanceId = [string](Get-ObjectPropertyValue -Object $pnpDevice -Name 'InstanceId')
                Problem = Get-ObjectPropertyValue -Object $pnpDevice -Name 'Problem'
                Present = Get-ObjectPropertyValue -Object $pnpDevice -Name 'Present'
            }
        } else { $null }
        SignedDriver = if ($SignedDriver) {
            $SignedDriver | Select-Object DeviceName, Manufacturer, DriverProviderName, DriverVersion, DriverDate, InfName, IsSigned, Signer, DeviceID, ClassGuid
        } else { $null }
        PnpProperties = @($pnpProperties)
    }

    $snapshot | ConvertTo-Json -Depth 8 | Set-Content -LiteralPath (Join-Path $preflightDir 'device_snapshot.json') -Encoding UTF8
    Write-Host 'Preflight JSON/REG backup saved.' -ForegroundColor Green
    return $preflightDir
}

function Write-RestoreNotes {
    param(
        [Parameter(Mandatory=$true)][string]$Path,
        [Parameter(Mandatory=$true)][string]$InstanceId,
        [Parameter(Mandatory=$true)][string]$PreflightDir,
        [Parameter(Mandatory=$true)][string]$DriverBackupDir,
        [AllowNull()][string]$OldPrimaryInf,
        [AllowNull()][string]$OldCompanionInf,
        [AllowNull()][string]$TargetInf
    )

    $lines = [System.Collections.Generic.List[string]]::new()
    $lines.Add('Audion HWID Rank Repair - manual restore notes')
    $lines.Add('')
    $lines.Add('Review these files before importing registry data. Registry import is contextual and should be used only when repair left the device in a bad state.')
    $lines.Add('')
    $lines.Add("DeviceInstanceId: $InstanceId")
    $lines.Add("OldPrimaryInf:    $OldPrimaryInf")
    $lines.Add("OldCompanionInf:  $OldCompanionInf")
    $lines.Add("TargetInf:        $TargetInf")
    $lines.Add('')
    $lines.Add('Preflight backup files:')
    foreach ($fileName in @(
        'policy_DeviceInstall_Restrictions_before.reg',
        'policy_WindowsUpdate_before.reg',
        'device_enum_before.reg',
        'class_before.reg',
        'driver_instance_before.reg',
        'service_before.reg',
        'device_snapshot.json',
        'before_device_drivers.txt',
        'before_class_drivers.txt'
    )) {
        $candidate = Join-Path $PreflightDir $fileName
        if (Test-Path -LiteralPath $candidate) {
            $lines.Add("  $candidate")
        }
    }
    $lines.Add('')
    $lines.Add('Possible manual restore commands, if needed:')
    foreach ($fileName in @(
        'policy_DeviceInstall_Restrictions_before.reg',
        'policy_WindowsUpdate_before.reg',
        'device_enum_before.reg',
        'class_before.reg',
        'driver_instance_before.reg',
        'service_before.reg'
    )) {
        $candidate = Join-Path $PreflightDir $fileName
        if (Test-Path -LiteralPath $candidate) {
            $lines.Add("reg import `"$candidate`"")
        }
    }
    $lines.Add("pnputil /add-driver `"$DriverBackupDir\*.inf`" /subdirs /install")
    $lines.Add('pnputil /scan-devices')
    $lines.Add("pnputil /restart-device `"$InstanceId`"")

    Write-TextFileUtf8 -Path $Path -Text ($lines -join [Environment]::NewLine)
    Write-Host "Restore notes: $Path"
}

function Get-CurrentDriverReport {
    param([Parameter(Mandatory=$true)][string]$InstanceId)
    return Invoke-NativeText -FilePath 'pnputil.exe' -Arguments @('/enum-devices', '/instanceid', $InstanceId, '/drivers')
}

function Invoke-LoggedNative {
    param(
        [Parameter(Mandatory=$true)][string]$Label,
        [Parameter(Mandatory=$true)][string]$FilePath,
        [Parameter(Mandatory=$true)][string[]]$Arguments,
        [int[]]$SuccessExitCodes = @(0),
        [switch]$AllowFailure
    )

    Write-Section $Label
    Write-Host ("> {0} {1}" -f $FilePath, ($Arguments -join ' '))
    $text = Invoke-NativeText -FilePath $FilePath -Arguments $Arguments -SuccessExitCodes $SuccessExitCodes -AllowFailure:$AllowFailure
    if (-not [string]::IsNullOrWhiteSpace($text)) {
        Write-Utf8ConsoleText $text.TrimEnd()
    }
    $code = $script:LastNativeExitCode
    Write-Host "exit=$code"
}

function Find-FirstInfNearVersion {
    param(
        [Parameter(Mandatory=$true)][string]$Text,
        [Parameter(Mandatory=$true)][string]$Version,
        [string]$ExcludeInf
    )
    $blocks = [regex]::Split($Text, '(\r?\n){2,}')
    foreach ($block in $blocks) {
        if ($block -notmatch [regex]::Escape($Version)) { continue }
        $matches = [regex]::Matches($block, 'oem\d+\.inf', [System.Text.RegularExpressions.RegexOptions]::IgnoreCase)
        foreach ($match in $matches) {
            $value = $match.Value.ToLowerInvariant()
            if ($ExcludeInf -and $value -eq $ExcludeInf.ToLowerInvariant()) { continue }
            return $value
        }
    }
    return $null
}

function Get-HardwareIdSearchVariants {
    param([AllowNull()][AllowEmptyCollection()][object[]]$TargetHardwareIds)

    $variants = @()
    foreach ($id in $TargetHardwareIds) {
        $value = ([string]$id).Trim()
        if (-not $value) { continue }
        $variants += $value
        if ($value -match '^(.*)&REV_[0-9A-Fa-f]+$') { $variants += $Matches[1] }
        if ($value -match '^(PCI\\VEN_[0-9A-Fa-f]{4}&DEV_[0-9A-Fa-f]{4})') { $variants += $Matches[1] }
        if ($value -match '^(USB\\VID_[0-9A-Fa-f]{4}&PID_[0-9A-Fa-f]{4})') { $variants += $Matches[1] }
        if ($value -match '^(HDAUDIO\\FUNC_[^&]+&VEN_[^&]+&DEV_[^&]+)') { $variants += $Matches[1] }
    }
    return @($variants | Where-Object { $_ -and $_.Trim().Length -gt 0 } | Select-Object -Unique)
}

function Find-TargetInf {
    param(
        [AllowNull()][AllowEmptyCollection()][object[]]$TargetHardwareIds,
        [Parameter(Mandatory=$true)][string]$Version
    )

    if ($TargetInfPath -and $TargetInfPath.Trim().Length -gt 0) {
        $resolved = (Resolve-Path -LiteralPath $TargetInfPath -ErrorAction Stop).Path
        if (-not (Test-Path -LiteralPath $resolved -PathType Leaf)) {
            throw "Target INF path is not a file: $resolved"
        }
        return $resolved
    }

    $repo = Join-Path $env:SystemRoot 'System32\DriverStore\FileRepository'
    if (-not (Test-Path -LiteralPath $repo)) {
        throw "DriverStore FileRepository was not found: $repo"
    }

    $pattern = if ($TargetInfNamePattern -and $TargetInfNamePattern.Trim().Length -gt 0) { $TargetInfNamePattern.Trim() } else { '*.inf' }
    $idVariants = @(Get-HardwareIdSearchVariants -TargetHardwareIds $TargetHardwareIds)
    $versionPattern = 'DriverVer=.*' + [regex]::Escape($Version)
    $matched = @()
    $versionOnly = @()

    Write-Host "Searching DriverStore for INF pattern '$pattern', target version '$Version'..."
    $dirs = @(Get-ChildItem -LiteralPath $repo -Directory -ErrorAction Stop)
    foreach ($dir in $dirs) {
        $infs = @(Get-ChildItem -LiteralPath $dir.FullName -Filter $pattern -File -ErrorAction SilentlyContinue)
        foreach ($inf in $infs) {
            $hasVersion = Select-String -LiteralPath $inf.FullName -Pattern $versionPattern -List -ErrorAction SilentlyContinue
            if (-not $hasVersion) { continue }

            $hasHardwareId = $false
            foreach ($variant in $idVariants) {
                if (Select-String -LiteralPath $inf.FullName -SimpleMatch $variant -Quiet -ErrorAction SilentlyContinue) {
                    $hasHardwareId = $true
                    break
                }
            }

            $item = [pscustomobject]@{
                Path = $inf.FullName
                LastWriteTime = $inf.LastWriteTime
            }
            if ($hasHardwareId) {
                $matched += $item
            } else {
                $versionOnly += $item
            }
        }
    }

    $best = @($matched | Sort-Object LastWriteTime -Descending | Select-Object -First 1)
    if ($best.Count -gt 0) { return $best[0].Path }

    $fallback = @($versionOnly | Sort-Object LastWriteTime -Descending | Select-Object -First 1)
    if ($fallback.Count -gt 0) {
        if (-not $AllowVersionOnlyTargetInfFallback) {
            throw "Found target version $Version in DriverStore, but none of those INF files matched the supplied HWID. Supply -TargetInfPath or re-run with -AllowVersionOnlyTargetInfFallback after manual verification."
        }
        Write-Host 'WARNING: Found target version but did not find the supplied HWID inside the INF. Using newest version-only match.' -ForegroundColor Yellow
        Write-Host 'If this is not intended, re-run with -TargetInfPath or a narrower -TargetInfNamePattern.'
        return $fallback[0].Path
    }

    throw "Could not find target driver INF for version $Version. Install/extract the target package first, or supply -TargetInfPath."
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

function Write-NumberedStringSubkey {
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

function Set-PerHardwareIdBlock {
    param([AllowNull()][AllowEmptyCollection()][object[]]$TargetHardwareIds)

    if ($NoPolicyBlock) {
        Write-Host 'Policy block skipped because -NoPolicyBlock was supplied.'
        return
    }

    Write-Section 'Apply per-Hardware-ID driver block'
    New-Item -Path $restrictionsKey -Force | Out-Null
    New-ItemProperty -LiteralPath $restrictionsKey -Name DenyDeviceIDs -PropertyType DWord -Value 1 -Force | Out-Null
    New-ItemProperty -LiteralPath $restrictionsKey -Name DenyDeviceIDsRetroactive -PropertyType DWord -Value 0 -Force | Out-Null

    $existing = @(Get-StringValuesFromSubkey -Path $denyListKey)
    $merged = @($existing + $TargetHardwareIds | Where-Object { $_ -and $_.Trim().Length -gt 0 } | Select-Object -Unique)
    Write-NumberedStringSubkey -Path $denyListKey -Values $merged

    if (-not $KeepGlobalWindowsUpdateDriverBlock) {
        if (Test-Path -LiteralPath $windowsUpdateKey) {
            Remove-ItemProperty -LiteralPath $windowsUpdateKey -Name ExcludeWUDriversInQualityUpdate -ErrorAction SilentlyContinue
        }
        Write-Host 'Global ExcludeWUDriversInQualityUpdate removed or was absent.'
    }
}

$ScriptRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$ProjectRoot = (Resolve-Path -LiteralPath (Join-Path $ScriptRoot '..\..')).Path
$timestamp = Get-Date -Format 'yyyyMMdd_HHmmss'
$logDir = Join-Path $ProjectRoot "backup\driver_guard\rank_repair\RankRepair_$timestamp"
$backupDir = Join-Path $logDir 'driver_backup'
$logFile = Join-Path $logDir 'repair.log'
New-DirIfMissing $backupDir

$transcriptStarted = $false

try {
    Start-Transcript -LiteralPath $logFile -Force | Out-Null
    $transcriptStarted = $true

    $targetHardwareIds = @(Get-TargetHardwareIds)
    if ($targetHardwareIds.Count -eq 0) {
        throw 'No Hardware IDs were supplied.'
    }

    $effectiveDeviceInstanceId = Resolve-TargetDeviceInstanceId -TargetHardwareIds $targetHardwareIds
    $signedDriver = Get-SignedDriverForDevice -InstanceId $effectiveDeviceInstanceId
    $currentVersion = if ($signedDriver) { [string]$signedDriver.DriverVersion } else { $null }

    Write-Section 'Target device'
    Write-Host "DeviceInstanceId=$effectiveDeviceInstanceId"
    Write-Host "CurrentVersion=$currentVersion"
    if ($signedDriver) {
        $signedDriver | Select-Object DeviceName, Manufacturer, DriverProviderName, DriverVersion, InfName, DeviceID | Format-List | Out-Host
    }

    $beforeReport = Get-CurrentDriverReport -InstanceId $effectiveDeviceInstanceId
    $beforeReport | Set-Content -LiteralPath (Join-Path $logDir 'before_device_drivers.txt') -Encoding UTF8
    $classDriversText = $null
    if ($DriverClass -and $DriverClass.Trim().Length -gt 0) {
        $classDriversText = Invoke-NativeText -FilePath 'pnputil.exe' -Arguments @('/enum-drivers', '/class', $DriverClass)
        $classDriversText | Set-Content -LiteralPath (Join-Path $logDir "before_$DriverClass`_drivers.txt") -Encoding UTF8
    } else {
        $classDriversText = Invoke-NativeText -FilePath 'pnputil.exe' -Arguments @('/enum-drivers')
        $classDriversText | Set-Content -LiteralPath (Join-Path $logDir 'before_all_drivers.txt') -Encoding UTF8
    }
    Get-CimInstance Win32_PnPSignedDriver |
        Where-Object { [string]$_.DeviceID -ieq $effectiveDeviceInstanceId } |
        Format-List |
        Out-String |
        Set-Content -LiteralPath (Join-Path $logDir 'before_signed_driver.txt') -Encoding UTF8

    $preflightDir = New-DeviceRepairPreflightBackup `
        -Root $logDir `
        -InstanceId $effectiveDeviceInstanceId `
        -TargetHardwareIds $targetHardwareIds `
        -SignedDriver $signedDriver `
        -BeforeReport $beforeReport `
        -ClassDriversText $classDriversText `
        -DriverClassName $DriverClass `
        -CurrentVersion $currentVersion `
        -ExpectedBadVersion $BadVersion `
        -ExpectedTargetVersion $TargetVersion

    if ($Status) {
        Write-Section 'PnP driver report'
        Write-Utf8ConsoleText $beforeReport
        Write-Host "logDir=$logDir"
        exit 0
    }

    Assert-Administrator

    if ($currentVersion -eq $TargetVersion) {
        Write-Host 'Target driver is already active. Applying per-Hardware-ID block only.'
        Set-PerHardwareIdBlock -TargetHardwareIds $targetHardwareIds
        Invoke-LoggedNative -Label 'Refresh policy' -FilePath 'gpupdate.exe' -Arguments @('/target:computer', '/force') -AllowFailure
        Write-Host "logDir=$logDir"
        exit 0
    }

    if (-not $SkipCurrentVersionCheck) {
        if (-not $currentVersion) {
            throw 'Current driver version could not be resolved. Re-run with -SkipCurrentVersionCheck if you want to continue.'
        }
        if ($currentVersion -ne $BadVersion) {
            throw "Current driver is '$currentVersion', expected bad version '$BadVersion' or target '$TargetVersion'. Aborting."
        }
    }

    $oldPrimaryInf = Find-FirstInfNearVersion -Text $beforeReport -Version $BadVersion
    if (-not $oldPrimaryInf) {
        throw "Could not find installed old INF for $BadVersion in device report."
    }
    $oldCompanionInf = Find-FirstInfNearVersion -Text $beforeReport -Version $BadVersion -ExcludeInf $oldPrimaryInf
    $targetInf = Find-TargetInf -TargetHardwareIds $targetHardwareIds -Version $TargetVersion

    Write-Host "oldPrimaryInf=$oldPrimaryInf"
    Write-Host "oldCompanionInf=$oldCompanionInf"
    Write-Host "targetInf=$targetInf"
    Write-RestoreNotes `
        -Path (Join-Path $logDir 'RESTORE_NOTES.txt') `
        -InstanceId $effectiveDeviceInstanceId `
        -PreflightDir $preflightDir `
        -DriverBackupDir $backupDir `
        -OldPrimaryInf $oldPrimaryInf `
        -OldCompanionInf $oldCompanionInf `
        -TargetInf $targetInf

    Invoke-LoggedNative -Label "Export old primary driver $oldPrimaryInf" -FilePath 'pnputil.exe' -Arguments @('/export-driver', $oldPrimaryInf, $backupDir)
    if ($oldCompanionInf) {
        Invoke-LoggedNative -Label "Export old companion driver $oldCompanionInf" -FilePath 'pnputil.exe' -Arguments @('/export-driver', $oldCompanionInf, $backupDir) -AllowFailure
    }

    if ($oldCompanionInf) {
        Invoke-LoggedNative -Label "Remove old companion driver $oldCompanionInf" -FilePath 'pnputil.exe' -Arguments @('/delete-driver', $oldCompanionInf, '/uninstall', '/force') -AllowFailure
    }
    Invoke-LoggedNative -Label "Remove old primary driver $oldPrimaryInf" -FilePath 'pnputil.exe' -Arguments @('/delete-driver', $oldPrimaryInf, '/uninstall', '/force')
    Invoke-LoggedNative -Label "Apply target driver $TargetVersion" -FilePath 'pnputil.exe' -Arguments @('/add-driver', $targetInf, '/install') -SuccessExitCodes @(0, 259)
    Invoke-LoggedNative -Label 'Scan devices' -FilePath 'pnputil.exe' -Arguments @('/scan-devices') -AllowFailure
    Invoke-LoggedNative -Label 'Restart target device' -FilePath 'pnputil.exe' -Arguments @('/restart-device', $effectiveDeviceInstanceId) -AllowFailure

    Start-Sleep -Seconds 5
    Set-PerHardwareIdBlock -TargetHardwareIds $targetHardwareIds
    Invoke-LoggedNative -Label 'Refresh policy' -FilePath 'gpupdate.exe' -Arguments @('/target:computer', '/force') -AllowFailure

    $afterReport = Get-CurrentDriverReport -InstanceId $effectiveDeviceInstanceId
    $afterReport | Set-Content -LiteralPath (Join-Path $logDir 'after_device_drivers.txt') -Encoding UTF8
    Get-CimInstance Win32_PnPSignedDriver |
        Where-Object { [string]$_.DeviceID -ieq $effectiveDeviceInstanceId } |
        Format-List |
        Out-String |
        Set-Content -LiteralPath (Join-Path $logDir 'after_signed_driver.txt') -Encoding UTF8

    Write-Section 'After'
    Write-Utf8ConsoleText $afterReport
    Write-Host "logDir=$logDir"
    exit 0
} catch {
    Write-Host ''
    Write-Host "ERROR: $($_.Exception.Message)" -ForegroundColor Red
    Write-Host "logDir=$logDir"
    exit 1
} finally {
    if ($transcriptStarted) {
        Stop-Transcript | Out-Null
    }
}
