# Audion DevOps Tools - Windows Driver and Firmware Audit
# Safe read-only diagnostic script.
# Default output language is English to avoid console encoding issues.

[CmdletBinding()]
param(
    [string]$OutputDir = "",
    [switch]$OpenReport,
    [switch]$Json,
    [switch]$Csv
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Continue"

function Get-SafeTimestamp {
    return (Get-Date -Format "yyyyMMdd_HHmmss")
}

function Resolve-OutputDir {
    param([string]$RequestedOutputDir)

    if (-not [string]::IsNullOrWhiteSpace($RequestedOutputDir)) {
        $dir = $RequestedOutputDir
    }
    else {
        $scriptRoot = Split-Path -Parent $PSCommandPath
        $projectRoot = Resolve-Path (Join-Path $scriptRoot "..\..") -ErrorAction SilentlyContinue
        if ($projectRoot) {
            $dir = Join-Path $projectRoot.Path "logs"
        }
        else {
            $dir = Join-Path $env:USERPROFILE "Desktop"
        }
    }

    New-Item -Path $dir -ItemType Directory -Force | Out-Null
    return (Resolve-Path $dir).Path
}

function Write-Section {
    param(
        [System.Text.StringBuilder]$Builder,
        [string]$Title
    )
    [void]$Builder.AppendLine("")
    [void]$Builder.AppendLine(("=" * 90))
    [void]$Builder.AppendLine($Title)
    [void]$Builder.AppendLine(("=" * 90))
}

function Add-TextBlock {
    param(
        [System.Text.StringBuilder]$Builder,
        [string]$Text
    )
    if ([string]::IsNullOrWhiteSpace($Text)) {
        [void]$Builder.AppendLine("(no output)")
    }
    else {
        [void]$Builder.AppendLine($Text.TrimEnd())
    }
}

function Format-Objects {
    param(
        [object[]]$InputObjects,
        [int]$Width = 260
    )

    if (-not $InputObjects -or $InputObjects.Count -eq 0) {
        return "(no rows)"
    }

    return ($InputObjects | Format-Table -Auto | Out-String -Width $Width)
}

function Get-ProblemDevices {
    try {
        return @(Get-PnpDevice -PresentOnly | Where-Object Status -ne "OK" | Sort-Object Class,FriendlyName |
            Select-Object Class,FriendlyName,Status,InstanceId)
    }
    catch {
        return @([pscustomobject]@{
            Class = "ERROR"
            FriendlyName = "Get-PnpDevice failed"
            Status = $_.Exception.Message
            InstanceId = ""
        })
    }
}

function Get-BiosSummary {
    try {
        return @(Get-CimInstance Win32_BIOS |
            Select-Object SMBIOSBIOSVersion,ReleaseDate,Manufacturer,EmbeddedControllerMajorVersion,EmbeddedControllerMinorVersion)
    }
    catch {
        return @([pscustomobject]@{
            SMBIOSBIOSVersion = "ERROR"
            ReleaseDate = ""
            Manufacturer = $_.Exception.Message
            EmbeddedControllerMajorVersion = ""
            EmbeddedControllerMinorVersion = ""
        })
    }
}

function Get-BiosRegistrySummary {
    try {
        return @(Get-ItemProperty 'HKLM:\HARDWARE\DESCRIPTION\System\BIOS' |
            Select-Object BIOSVersion,BIOSReleaseDate,SystemSKU,SystemProductName)
    }
    catch {
        return @([pscustomobject]@{
            BIOSVersion = "ERROR"
            BIOSReleaseDate = ""
            SystemSKU = ""
            SystemProductName = $_.Exception.Message
        })
    }
}

function Get-FirmwareSummary {
    try {
        return @(Get-PnpDevice -PresentOnly -Class Firmware |
            Sort-Object FriendlyName |
            Select-Object FriendlyName,Status,InstanceId)
    }
    catch {
        return @([pscustomobject]@{
            FriendlyName = "ERROR"
            Status = $_.Exception.Message
            InstanceId = ""
        })
    }
}

function Get-FirmwareDetails {
    $rows = New-Object System.Collections.Generic.List[object]
    try {
        $firmwareDevices = @(Get-PnpDevice -PresentOnly -Class Firmware | Sort-Object FriendlyName)
        foreach ($dev in $firmwareDevices) {
            $props = @(Get-PnpDeviceProperty -InstanceId $dev.InstanceId -ErrorAction SilentlyContinue)

            $getProp = {
                param([string]$Name)
                $p = $props | Where-Object KeyName -eq $Name | Select-Object -First 1
                if ($p) { return $p.Data }
                return $null
            }

            $rows.Add([pscustomobject]@{
                FriendlyName = $dev.FriendlyName
                Status = $dev.Status
                FirmwareDate = & $getProp "DEVPKEY_Device_FirmwareDate"
                FirmwareVersion = & $getProp "DEVPKEY_Device_FirmwareVersion"
                DriverVersion = & $getProp "DEVPKEY_Device_DriverVersion"
                DriverDate = & $getProp "DEVPKEY_Device_DriverDate"
                DriverProvider = & $getProp "DEVPKEY_Device_DriverProvider"
                DriverInfPath = & $getProp "DEVPKEY_Device_DriverInfPath"
                FirmwareResourceVersion = & $getProp "DEVPKEY_FirmwareResource_Version"
                LowestSupportedVersion = & $getProp "DEVPKEY_FirmwareResource_LowestSupportedVersion"
                InstanceId = $dev.InstanceId
            })
        }
    }
    catch {
        $rows.Add([pscustomobject]@{
            FriendlyName = "ERROR"
            Status = $_.Exception.Message
            FirmwareDate = ""
            FirmwareVersion = ""
            DriverVersion = ""
            DriverDate = ""
            DriverProvider = ""
            DriverInfPath = ""
            FirmwareResourceVersion = ""
            LowestSupportedVersion = ""
            InstanceId = ""
        })
    }
    return @($rows)
}

function Get-KeyDriverSummary {
    $pattern = 'Realtek|Smart Sound|SST|Thunderbolt|USB4|Management Engine|MEI|CSME|Serial IO|Dynamic Tuning|GNA|Lenovo|ThinkPad|Power|Hotkey|Fn|Fingerprint|Camera|IR|MIPI|HID|ELAN|Monitor'
    try {
        return @(Get-CimInstance Win32_PnPSignedDriver |
            Where-Object {
                $_.DeviceName -and (
                    $_.DeviceName -match $pattern -or
                    $_.DriverProviderName -match 'Lenovo|Intel|Realtek|ELAN|Synaptics|Goodix'
                )
            } |
            Sort-Object DeviceClass,DeviceName |
            Select-Object DeviceClass,DeviceName,DriverProviderName,DriverVersion,DriverDate,InfName)
    }
    catch {
        return @([pscustomobject]@{
            DeviceClass = "ERROR"
            DeviceName = "Get-CimInstance Win32_PnPSignedDriver failed"
            DriverProviderName = $_.Exception.Message
            DriverVersion = ""
            DriverDate = ""
            InfName = ""
        })
    }
}

function Get-ThinkPadHealthVerdict {
    param(
        [object[]]$ProblemDevices,
        [object[]]$FirmwareDetails,
        [object[]]$KeyDrivers
    )

    $warnings = New-Object System.Collections.Generic.List[string]

    if ($ProblemDevices -and $ProblemDevices.Count -gt 0) {
        $warnings.Add("Problem devices are present. Review the Problem Devices section.")
    }

    $firmwareProblems = @($FirmwareDetails | Where-Object { $_.Status -and $_.Status -ne "OK" })
    if ($firmwareProblems.Count -gt 0) {
        $warnings.Add("One or more firmware resources are not OK.")
    }

    if ($warnings.Count -eq 0) {
        return "GREEN: No present devices with non-OK status. Key Windows platform driver and firmware resources look healthy. Do not keep reinstalling drivers if functional tests pass."
    }

    return ("CHECK: " + ($warnings -join " | "))
}

$outDir = Resolve-OutputDir -RequestedOutputDir $OutputDir
$timestamp = Get-SafeTimestamp
$txtPath = Join-Path $outDir "Windows_Driver_Firmware_Audit_$timestamp.txt"
$jsonPath = Join-Path $outDir "Windows_Driver_Firmware_Audit_$timestamp.json"
$csvPath = Join-Path $outDir "Windows_Driver_Firmware_Audit_KeyDrivers_$timestamp.csv"

$problemDevices = Get-ProblemDevices
$bios = Get-BiosSummary
$biosReg = Get-BiosRegistrySummary
$firmwareSummary = Get-FirmwareSummary
$firmwareDetails = Get-FirmwareDetails
$keyDrivers = Get-KeyDriverSummary
$verdict = Get-ThinkPadHealthVerdict -ProblemDevices $problemDevices -FirmwareDetails $firmwareDetails -KeyDrivers $keyDrivers

$sb = New-Object System.Text.StringBuilder
[void]$sb.AppendLine("Audion DevOps Tools - Windows Driver and Firmware Audit")
[void]$sb.AppendLine("Generated: $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')")
[void]$sb.AppendLine("Computer: $env:COMPUTERNAME")
[void]$sb.AppendLine("User: $env:USERNAME")
[void]$sb.AppendLine("PowerShell: $($PSVersionTable.PSVersion)")
[void]$sb.AppendLine("")

Write-Section -Builder $sb -Title "VERDICT"
Add-TextBlock -Builder $sb -Text $verdict

Write-Section -Builder $sb -Title "PROBLEM DEVICES"
Add-TextBlock -Builder $sb -Text (Format-Objects -InputObjects $problemDevices)

Write-Section -Builder $sb -Title "BIOS AND EMBEDDED CONTROLLER"
Add-TextBlock -Builder $sb -Text (Format-Objects -InputObjects $bios)

Write-Section -Builder $sb -Title "BIOS REGISTRY SUMMARY"
Add-TextBlock -Builder $sb -Text (Format-Objects -InputObjects $biosReg)

Write-Section -Builder $sb -Title "FIRMWARE SUMMARY"
Add-TextBlock -Builder $sb -Text (Format-Objects -InputObjects $firmwareSummary)

Write-Section -Builder $sb -Title "FIRMWARE DETAILS"
Add-TextBlock -Builder $sb -Text (Format-Objects -InputObjects $firmwareDetails)

Write-Section -Builder $sb -Title "KEY DRIVER SUMMARY"
Add-TextBlock -Builder $sb -Text (Format-Objects -InputObjects $keyDrivers)

Set-Content -Path $txtPath -Value $sb.ToString() -Encoding UTF8

if ($Json) {
    [pscustomobject]@{
        Generated = Get-Date
        Computer = $env:COMPUTERNAME
        User = $env:USERNAME
        PowerShell = $PSVersionTable.PSVersion.ToString()
        Verdict = $verdict
        ProblemDevices = $problemDevices
        Bios = $bios
        BiosRegistry = $biosReg
        FirmwareSummary = $firmwareSummary
        FirmwareDetails = $firmwareDetails
        KeyDrivers = $keyDrivers
    } | ConvertTo-Json -Depth 8 | Set-Content -Path $jsonPath -Encoding UTF8
}

if ($Csv) {
    $keyDrivers | Export-Csv -Path $csvPath -Encoding UTF8 -NoTypeInformation
}

Write-Host "Report written:" $txtPath
if ($Json) { Write-Host "JSON written:" $jsonPath }
if ($Csv) { Write-Host "CSV written:" $csvPath }

if ($OpenReport) {
    Start-Process notepad.exe $txtPath
}
