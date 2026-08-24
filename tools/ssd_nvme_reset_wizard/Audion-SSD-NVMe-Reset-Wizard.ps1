#Requires -RunAsAdministrator

[CmdletBinding()]
param(
    [switch]$NoPause,
    [switch]$AllowSystemDisk
)

$ErrorActionPreference = 'Stop'
Set-StrictMode -Version 2

try {
    if ($PSVersionTable.PSEdition -eq 'Core') {
        Import-Module Storage -UseWindowsPowerShell -ErrorAction Stop
    } else {
        Import-Module Storage -ErrorAction Stop
    }
} catch {
    Write-Host '[ERROR] Failed to import the Storage module.' -ForegroundColor Red
    Write-Host $_.Exception.Message -ForegroundColor Red
    exit 1
}

$ScriptRootPath = if ($PSScriptRoot) { $PSScriptRoot } else { Split-Path -Parent $MyInvocation.MyCommand.Path }
$LogsPath = Join-Path $ScriptRootPath 'logs'
if (-not (Test-Path -LiteralPath $LogsPath)) {
    New-Item -Path $LogsPath -ItemType Directory -Force | Out-Null
}
$LogFile = Join-Path $LogsPath ('ssd_reset_' + (Get-Date -Format 'yyyyMMdd_HHmmss') + '.log')

function Write-Log {
    param([string]$Line)

    Add-Content -Path $LogFile -Value $Line
}

function Write-Info {
    param([string]$Message)
    $line = '[INFO] ' + $Message
    Write-Host $line
    Write-Log $line
}

function Write-WarnMsg {
    param([string]$Message)
    $line = '[WARN] ' + $Message
    Write-Host $line -ForegroundColor Yellow
    Write-Log $line
}

function Write-Ok {
    param([string]$Message)
    $line = '[OK] ' + $Message
    Write-Host $line -ForegroundColor Green
    Write-Log $line
}

function Fail {
    param([string]$Message)
    $line = '[ERROR] ' + $Message
    Write-Host $line -ForegroundColor Red
    Write-Log $line
    Pause-IfNeeded
    exit 1
}

function Pause-IfNeeded {
    if (-not $NoPause) {
        Write-Host ''
        [void](Read-Host 'Press Enter to continue')
    }
}

function Format-Bytes {
    param([UInt64]$Bytes)

    if ($Bytes -ge 1TB) { return '{0:N2} TB' -f ($Bytes / 1TB) }
    if ($Bytes -ge 1GB) { return '{0:N2} GB' -f ($Bytes / 1GB) }
    if ($Bytes -ge 1MB) { return '{0:N2} MB' -f ($Bytes / 1MB) }
    if ($Bytes -ge 1KB) { return '{0:N2} KB' -f ($Bytes / 1KB) }
    return "$Bytes B"
}

function Get-SystemDiskNumbers {
    $numbers = @()

    try {
        $systemDriveLetter = $env:SystemDrive.TrimEnd(':')
        $osPartition = Get-Partition -DriveLetter $systemDriveLetter -ErrorAction Stop
        if ($osPartition) {
            $numbers += [int]$osPartition.DiskNumber
        }
    } catch {
    }

    try {
        $bootSystemDisks = Get-Disk | Where-Object { $_.IsBoot -or $_.IsSystem }
        foreach ($disk in $bootSystemDisks) {
            $numbers += [int]$disk.Number
        }
    } catch {
    }

    $numbers | Sort-Object -Unique
}

function Show-DiskList {
    Write-Host ''
    Write-Info 'Available disks:'

    $rows = Get-Disk | Sort-Object Number | ForEach-Object {
        [pscustomobject]@{
            Number         = $_.Number
            FriendlyName   = $_.FriendlyName
            BusType        = [string]$_.BusType
            Size           = Format-Bytes -Bytes ([UInt64]$_.Size)
            PartitionStyle = [string]$_.PartitionStyle
            Health         = [string]$_.HealthStatus
            IsSystem       = [bool]$_.IsSystem
            IsBoot         = [bool]$_.IsBoot
            IsOffline      = [bool]$_.IsOffline
            IsReadOnly     = [bool]$_.IsReadOnly
        }
    }

    $rows | Format-Table -AutoSize | Out-Host
}

function Show-DiskDetails {
    param([int]$DiskNumber)

    $disk = Get-Disk -Number $DiskNumber -ErrorAction Stop

    Write-Host ''
    Write-Info ('Selected disk: ' + $DiskNumber)
    Write-Host ('  FriendlyName   : ' + $disk.FriendlyName)
    Write-Host ('  BusType        : ' + [string]$disk.BusType)
    Write-Host ('  Size           : ' + (Format-Bytes -Bytes ([UInt64]$disk.Size)))
    Write-Host ('  PartitionStyle : ' + [string]$disk.PartitionStyle)
    Write-Host ('  HealthStatus   : ' + [string]$disk.HealthStatus)
    Write-Host ('  IsSystem       : ' + [string][bool]$disk.IsSystem)
    Write-Host ('  IsBoot         : ' + [string][bool]$disk.IsBoot)
    Write-Host ('  IsOffline      : ' + [string][bool]$disk.IsOffline)
    Write-Host ('  IsReadOnly     : ' + [string][bool]$disk.IsReadOnly)

    $partitions = @(Get-Partition -DiskNumber $DiskNumber -ErrorAction SilentlyContinue | Sort-Object Offset)
    Write-Host ''
    if ($partitions.Count -eq 0) {
        Write-Host '  No partitions found.'
        return
    }

    $rows = foreach ($p in $partitions) {
        $vol = $null
        try {
            $vol = Get-Volume -Partition $p -ErrorAction SilentlyContinue
        } catch {
        }

        $access = ''
        if ($p.DriveLetter) {
            $access = $p.DriveLetter + ':'
        } elseif ($vol -and $vol.Path) {
            $access = $vol.Path
        }

        $label = ''
        if ($vol -and $vol.FileSystemLabel) {
            $label = $vol.FileSystemLabel
        }

        [pscustomobject]@{
            Partition   = $p.PartitionNumber
            Access      = $access
            Size        = Format-Bytes -Bytes ([UInt64]$p.Size)
            Type        = [string]$p.Type
            GptType     = [string]$p.GptType
            Label       = $label
            Offset      = Format-Bytes -Bytes ([UInt64]$p.Offset)
        }
    }

    Write-Info 'Partitions on selected disk:'
    $rows | Format-Table -AutoSize | Out-Host
}

function Ensure-DiskOnlineWritable {
    param([int]$DiskNumber)

    $disk = Get-Disk -Number $DiskNumber -ErrorAction Stop

    if ($disk.IsOffline) {
        Write-WarnMsg 'Disk is offline. Bringing it online.'
        Set-Disk -Number $DiskNumber -IsOffline $false -ErrorAction Stop
    }

    if ($disk.IsReadOnly) {
        Write-WarnMsg 'Disk is read-only. Clearing the read-only flag.'
        Set-Disk -Number $DiskNumber -IsReadOnly $false -ErrorAction Stop
    }
}

function Invoke-DiskPart {
    param(
        [string[]]$Lines,
        [string]$Description
    )

    $tmp = Join-Path $env:TEMP ('diskpart_' + [guid]::NewGuid().ToString('N') + '.txt')
    try {
        $normalizedLines = New-Object 'System.Collections.Generic.List[string]'
        foreach ($item in @($Lines)) {
            if ($null -eq $item) {
                continue
            }

            $line = ([string]$item).Trim()
            if ($line -ne '') {
                [void]$normalizedLines.Add($line)
            }
        }

        if ($normalizedLines.Count -eq 0) {
            Fail 'DiskPart command list is empty.'
        }

        $encoding = New-Object System.Text.ASCIIEncoding
        [System.IO.File]::WriteAllLines($tmp, $normalizedLines, $encoding)

        Write-Info $Description
        Write-Info ('DiskPart script lines: ' + $normalizedLines.Count)
        Write-Info ('DiskPart script: ' + ($normalizedLines -join ' ; '))
        Write-Log '----- DiskPart Begin -----'
        $lineNumber = 0
        foreach ($line in $normalizedLines) {
            $lineNumber++
            Write-Log ('[' + $lineNumber + '] ' + $line)
        }
        Write-Log '----- DiskPart Script File Dump -----'
        foreach ($dumpLine in (Get-Content -LiteralPath $tmp -Encoding Ascii)) {
            Write-Log ('> ' + $dumpLine)
        }

        $output = & diskpart.exe /s $tmp 2>&1
        $exitCode = $LASTEXITCODE

        foreach ($line in $output) {
            Write-Host $line
            Write-Log ([string]$line)
        }
        Write-Log '----- DiskPart End -----'

        if ($exitCode -ne 0) {
            Fail ('DiskPart failed with exit code ' + $exitCode + '.')
        }

        return $true
    } finally {
        Remove-Item -LiteralPath $tmp -Force -ErrorAction SilentlyContinue
    }
}


function New-DiskPartCommandArray {
    param([Parameter(ValueFromRemainingArguments = $true)][string[]]$Items)

    $result = New-Object 'System.Collections.Generic.List[string]'
    foreach ($item in $Items) {
        if ($null -eq $item) {
            continue
        }

        $line = ([string]$item).Trim()
        if ($line -ne '') {
            [void]$result.Add($line)
        }
    }

    return ,$result.ToArray()
}

function Confirm-Text {
    param(
        [string]$Prompt,
        [string]$ExactText
    )

    Write-Host ''
    Write-Host $Prompt -ForegroundColor Yellow
    Write-Host ('Required confirmation text: ' + $ExactText) -ForegroundColor Yellow
    $answer = Read-Host 'Enter confirmation text'
    if ($answer -cne $ExactText) {
        Write-WarnMsg 'Confirmation text did not match. Operation cancelled.'
        return $false
    }
    return $true
}

function Read-DiskNumber {
    while ($true) {
        $raw = Read-Host 'Enter disk number'
        $number = 0
        if ([int]::TryParse($raw, [ref]$number)) {
            try {
                $null = Get-Disk -Number $number -ErrorAction Stop
                return $number
            } catch {
            }
        }
        Write-WarnMsg 'Invalid disk number.'
    }
}

function Read-MenuChoice {
    param([string[]]$Allowed)

    while ($true) {
        $raw = Read-Host 'Select action'
        if ($Allowed -contains $raw) {
            return $raw
        }
        Write-WarnMsg ('Allowed choices: ' + ($Allowed -join ', '))
    }
}

function Read-PartitionNumber {
    param([int]$DiskNumber)

    $partitions = @(Get-Partition -DiskNumber $DiskNumber -ErrorAction SilentlyContinue | Sort-Object Offset)
    if ($partitions.Count -eq 0) {
        Write-WarnMsg 'No partitions exist on the selected disk.'
        return $null
    }

    while ($true) {
        $raw = Read-Host 'Enter partition number'
        $number = 0
        if ([int]::TryParse($raw, [ref]$number)) {
            $match = $partitions | Where-Object { $_.PartitionNumber -eq $number }
            if ($match) {
                return $number
            }
        }
        Write-WarnMsg 'Invalid partition number.'
    }
}

function Reset-DiskFast {
    param([int]$DiskNumber)

    Ensure-DiskOnlineWritable -DiskNumber $DiskNumber
    if (-not (Confirm-Text -Prompt 'Fast reset removes the partition table only. Data may still be recoverable.' -ExactText ('CLEAN DISK ' + $DiskNumber))) {
        return $false
    }

    $diskPartLines = New-DiskPartCommandArray ('select disk ' + $DiskNumber) 'clean'
    Invoke-DiskPart -Lines $diskPartLines -Description ('Running fast reset on disk ' + $DiskNumber + '.') | Out-Null
    Write-Ok 'Fast reset finished.'
    return $true
}

function Reset-DiskFullZeroFill {
    param([int]$DiskNumber)

    Ensure-DiskOnlineWritable -DiskNumber $DiskNumber
    Write-WarnMsg 'Full zero-fill wipe is slow and adds unnecessary wear on SSD and NVMe media.'
    Write-WarnMsg 'For the closest SSD factory-state workflow, prefer vendor Secure Erase, Sanitize, or NVMe Format where available.'
    if (-not (Confirm-Text -Prompt 'Continue with full zero-fill wipe only if you really need it.' -ExactText ('CLEAN ALL DISK ' + $DiskNumber))) {
        return $false
    }

    $diskPartLines = New-DiskPartCommandArray ('select disk ' + $DiskNumber) 'clean all'
    Invoke-DiskPart -Lines $diskPartLines -Description ('Running full zero-fill wipe on disk ' + $DiskNumber + '.') | Out-Null
    Write-Ok 'Full zero-fill wipe finished.'
    return $true
}

function Delete-PartitionOverride {
    param(
        [int]$DiskNumber,
        [int]$PartitionNumber
    )

    Ensure-DiskOnlineWritable -DiskNumber $DiskNumber
    if (-not (Confirm-Text -Prompt 'This permanently deletes the selected partition.' -ExactText ('DELETE PARTITION ' + $PartitionNumber + ' ON DISK ' + $DiskNumber))) {
        return $false
    }

    $diskPartLines = New-DiskPartCommandArray ('select disk ' + $DiskNumber) ('select partition ' + $PartitionNumber) 'delete partition override'
    Invoke-DiskPart -Lines $diskPartLines -Description ('Deleting partition ' + $PartitionNumber + ' on disk ' + $DiskNumber + '.') | Out-Null
    Write-Ok 'Selected partition was removed.'
    return $true
}

function Initialize-And-BuildVolume {
    param(
        [int]$DiskNumber,
        [string]$Label = 'DATA'
    )

    Ensure-DiskOnlineWritable -DiskNumber $DiskNumber
    $disk = Get-Disk -Number $DiskNumber -ErrorAction Stop

    if ($disk.PartitionStyle -eq 'RAW') {
        Initialize-Disk -Number $DiskNumber -PartitionStyle GPT -ErrorAction Stop | Out-Null
    } else {
        $diskPartLines = New-DiskPartCommandArray ('select disk ' + $DiskNumber) 'convert gpt'
        Invoke-DiskPart -Lines $diskPartLines -Description ('Ensuring GPT partition style on disk ' + $DiskNumber + '.')
    }

    $partition = New-Partition -DiskNumber $DiskNumber -UseMaximumSize -AssignDriveLetter -ErrorAction Stop
    $volume = Format-Volume -Partition $partition -FileSystem NTFS -NewFileSystemLabel $Label -Confirm:$false -Force -ErrorAction Stop
    Write-Ok ('Created NTFS volume ' + $volume.DriveLetter + ': with label "' + $Label + '".')
}

function Prompt-VolumeLabel {
    $label = Read-Host 'Enter volume label or press Enter for DATA'
    if ([string]::IsNullOrWhiteSpace($label)) {
        return 'DATA'
    }
    return $label.Trim()
}

Write-Log ('Log created at ' + (Get-Date).ToString('yyyy-MM-dd HH:mm:ss'))

Write-Host '======================================================================' -ForegroundColor Cyan
Write-Host '  AUDION SSD / NVME RESET WIZARD v4' -ForegroundColor Cyan
Write-Host '======================================================================' -ForegroundColor Cyan
Write-Host ''
Write-Host 'Native Windows disk reset and reprovision helper.' -ForegroundColor Gray
Write-Host 'This tool can delete partitions, reset a disk, and rebuild it as GPT + NTFS.' -ForegroundColor Gray
Write-Host ''
Write-Host 'Reality check for SSD and NVMe media:' -ForegroundColor Yellow
Write-Host '  - Fast reset uses DiskPart CLEAN and removes the partition table only.' -ForegroundColor Yellow
Write-Host '  - Full wipe uses DiskPart CLEAN ALL and writes zeros across the device.' -ForegroundColor Yellow
Write-Host '  - Neither mode guarantees the same result as vendor Secure Erase or NVMe Sanitize.' -ForegroundColor Yellow
Write-Host ''

try {
    Show-DiskList

    $systemDiskNumbers = @(Get-SystemDiskNumbers)
    if (-not $AllowSystemDisk -and $systemDiskNumbers.Count -gt 0) {
        Write-WarnMsg ('System-protected disk numbers: ' + ($systemDiskNumbers -join ', '))
    }

    $diskNumber = Read-DiskNumber
    $disk = Get-Disk -Number $diskNumber -ErrorAction Stop

    if ((-not $AllowSystemDisk) -and ($systemDiskNumbers -contains $diskNumber)) {
        Fail 'Selected disk appears to be a system or boot disk. This tool blocks destructive actions on it by default.'
    }

    Show-DiskDetails -DiskNumber $diskNumber

    Write-Host ''
    Write-Host 'Actions:' -ForegroundColor Cyan
    Write-Host '  1 - Preview selected disk again'
    Write-Host '  2 - Delete one partition on selected disk'
    Write-Host '  3 - Fast reset disk: DiskPart CLEAN'
    Write-Host '  4 - Full zero-fill wipe: DiskPart CLEAN ALL'
    Write-Host '  5 - Fast reset + rebuild as GPT + one NTFS volume'
    Write-Host '  6 - Full zero-fill wipe + rebuild as GPT + one NTFS volume'
    Write-Host '  7 - Exit'
    Write-Host ''

    $choice = Read-MenuChoice -Allowed @('1', '2', '3', '4', '5', '6', '7')

    switch ($choice) {
        '1' {
            Show-DiskDetails -DiskNumber $diskNumber
            Write-Ok 'Preview completed.'
        }
        '2' {
            $partitionNumber = Read-PartitionNumber -DiskNumber $diskNumber
            if ($null -ne $partitionNumber) {
                Delete-PartitionOverride -DiskNumber $diskNumber -PartitionNumber $partitionNumber
            }
        }
        '3' {
            Reset-DiskFast -DiskNumber $diskNumber
        }
        '4' {
            Reset-DiskFullZeroFill -DiskNumber $diskNumber
        }
        '5' {
            $label = Prompt-VolumeLabel
            if (Reset-DiskFast -DiskNumber $diskNumber) {
                Show-DiskDetails -DiskNumber $diskNumber
                if (-not (Confirm-Text -Prompt 'Ready to initialize GPT and create one NTFS volume.' -ExactText ('REBUILD DISK ' + $diskNumber))) {
                    Write-WarnMsg 'Rebuild stage cancelled.'
                } else {
                    Initialize-And-BuildVolume -DiskNumber $diskNumber -Label $label
                }
            } else {
                Write-WarnMsg 'Fast reset stage cancelled.'
            }
        }
        '6' {
            $label = Prompt-VolumeLabel
            if (Reset-DiskFullZeroFill -DiskNumber $diskNumber) {
                Show-DiskDetails -DiskNumber $diskNumber
                if (-not (Confirm-Text -Prompt 'Ready to initialize GPT and create one NTFS volume.' -ExactText ('REBUILD DISK ' + $diskNumber))) {
                    Write-WarnMsg 'Rebuild stage cancelled.'
                } else {
                    Initialize-And-BuildVolume -DiskNumber $diskNumber -Label $label
                }
            } else {
                Write-WarnMsg 'Full zero-fill wipe stage cancelled.'
            }
        }
        '7' {
            Write-WarnMsg 'No changes were made.'
        }
    }

    Write-Host ''
    Write-Info 'Final disk state:'
    Show-DiskDetails -DiskNumber $diskNumber
    Write-Info ('Log file: ' + $LogFile)
} catch {
    Fail $_.Exception.Message
}

Pause-IfNeeded
