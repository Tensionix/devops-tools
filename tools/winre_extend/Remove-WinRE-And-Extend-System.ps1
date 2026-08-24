#Requires -RunAsAdministrator

[CmdletBinding(SupportsShouldProcess = $true, ConfirmImpact = 'High')]
param(
    [switch]$SkipBitLockerCheck,
    [switch]$NoPause,
    [switch]$YesIUnderstand
)

$ErrorActionPreference = 'Stop'

function Write-Info {
    param([string]$Message)
    Write-Host "[INFO] $Message"
}

function Write-WarnMsg {
    param([string]$Message)
    Write-Host "[WARN] $Message" -ForegroundColor Yellow
}

function Write-Ok {
    param([string]$Message)
    Write-Host "[OK] $Message" -ForegroundColor Green
}

function Fail {
    param([string]$Message)
    Write-Host "[ERROR] $Message" -ForegroundColor Red
    exit 1
}

function Pause-IfNeeded {
    if (-not $NoPause) {
        Write-Host ''
        Read-Host 'Press Enter to continue'
    }
}

function Get-WinREInfo {
    $reInfo = reagentc /info 2>&1 | Out-String
    if ($LASTEXITCODE -ne 0) {
        Fail 'reagentc /info failed.'
    }

    $diskNumber = $null
    $partitionNumber = $null

    if ($reInfo -match 'harddisk(\d+)\\partition(\d+)') {
        $diskNumber = [int]$Matches[1]
        $partitionNumber = [int]$Matches[2]
    }

    [pscustomobject]@{
        HasLocation      = ($null -ne $diskNumber -and $null -ne $partitionNumber)
        DiskNumber       = $diskNumber
        PartitionNumber  = $partitionNumber
        RawText          = $reInfo
    }
}

function Test-BitLockerSafe {
    param([string]$DriveLetter)

    if ($SkipBitLockerCheck) {
        Write-WarnMsg 'BitLocker check skipped by user request.'
        return
    }

    $cmd = Get-Command Get-BitLockerVolume -ErrorAction SilentlyContinue
    if (-not $cmd) {
        Write-WarnMsg 'Get-BitLockerVolume is not available. Continue only if BitLocker or device encryption is suspended or not used.'
        return
    }

    $blv = Get-BitLockerVolume -MountPoint ($DriveLetter + ':') -ErrorAction Stop
    if (-not $blv) {
        Write-WarnMsg 'Could not read BitLocker status. Continue only if BitLocker or device encryption is suspended or not used.'
        return
    }

    $protectionStatus = [string]$blv.ProtectionStatus
    $lockStatus = [string]$blv.LockStatus

    Write-Info "BitLocker lock status: $lockStatus"
    Write-Info "BitLocker protection status: $protectionStatus"

    if ($protectionStatus -match 'On|1') {
        Fail 'BitLocker or device encryption appears to be active. Suspend protection first, then run this script again.'
    }
}

function Show-PartitionList {
    param(
        [int]$DiskNumber,
        [int]$OsPartitionNumber = -1,
        [Nullable[int]]$WinREPartitionNumber = $null
    )

    Write-Host ''
    Write-Info "Current partitions on Windows disk ${DiskNumber}:"

    $rows = Get-Partition -DiskNumber $DiskNumber | Sort-Object Offset | ForEach-Object {
        $typeText = [string]$_.Type
        if ([string]::IsNullOrWhiteSpace($typeText)) {
            $typeText = [string]$_.GptType
        }

        $label = @()
        if ($_.PartitionNumber -eq $OsPartitionNumber) {
            $label += 'OS'
        }
        if ($WinREPartitionNumber -ne $null -and $_.PartitionNumber -eq $WinREPartitionNumber) {
            $label += 'WinRE'
        }

        [pscustomobject]@{
            PartitionNumber = $_.PartitionNumber
            DriveLetter     = if ($_.DriveLetter) { $_.DriveLetter } else { '' }
            SizeGB          = [math]::Round($_.Size / 1GB, 3)
            OffsetGB        = [math]::Round($_.Offset / 1GB, 3)
            Type            = $typeText
            Role            = ($label -join ', ')
        }
    }

    $rows | Format-Table -AutoSize | Out-Host
}

function Get-CandidateRecoveryPartitionToRight {
    param(
        [int]$DiskNumber,
        [int]$OsPartitionNumber
    )

    $partitions = Get-Partition -DiskNumber $DiskNumber | Sort-Object Offset
    $osPart = $partitions | Where-Object { $_.PartitionNumber -eq $OsPartitionNumber }
    if (-not $osPart) {
        return $null
    }

    $rightSide = $partitions | Where-Object { $_.Offset -gt $osPart.Offset }
    if (-not $rightSide) {
        return $null
    }

    foreach ($p in $rightSide) {
        $typeText = [string]$p.Type
        $gptTypeText = [string]$p.GptType
        if ($typeText -match 'Recovery' -or $gptTypeText -match 'de94bba4-06d1-4d40-a16a-bfd50179d6ac') {
            return $p
        }
    }

    return $null
}

Write-Info 'Reading Windows RE configuration...'
$winre = Get-WinREInfo

$systemDrive = $env:SystemDrive.TrimEnd(':')
Write-Info "Detecting OS partition for drive ${systemDrive}..."
$osPartition = Get-Partition -DriveLetter $systemDrive
if (-not $osPartition) {
    Fail 'Could not detect the OS partition.'
}

$osDiskNumber = $osPartition.DiskNumber
$osPartitionNumber = $osPartition.PartitionNumber

Write-Info "OS partition: disk $osDiskNumber, partition $osPartitionNumber"
if ($winre.HasLocation) {
    Write-Info "WinRE location from reagentc: disk $($winre.DiskNumber), partition $($winre.PartitionNumber)"
} else {
    Write-WarnMsg 'No WinRE partition location was detected in reagentc output.'
}

Show-PartitionList -DiskNumber $osDiskNumber -OsPartitionNumber $osPartitionNumber -WinREPartitionNumber $winre.PartitionNumber

if (-not $winre.HasLocation) {
    $candidateRecovery = Get-CandidateRecoveryPartitionToRight -DiskNumber $osDiskNumber -OsPartitionNumber $osPartitionNumber
    if ($candidateRecovery) {
        Write-WarnMsg "WinRE does not expose a usable location, but a recovery-like partition still exists to the right of the OS partition: partition $($candidateRecovery.PartitionNumber), size $([math]::Round($candidateRecovery.Size / 1MB)) MB."
        Write-WarnMsg 'Nothing was changed automatically. Review this layout manually before deleting anything.'
        Pause-IfNeeded
        exit 0
    }

    Write-Ok 'Nothing to do. No removable recovery partition was detected to the right of the OS partition.'
    Pause-IfNeeded
    exit 0
}

if ($osDiskNumber -ne $winre.DiskNumber) {
    Fail 'OS partition and WinRE partition are on different disks. Automatic removal is blocked.'
}

Test-BitLockerSafe -DriveLetter $systemDrive

$partitions = Get-Partition -DiskNumber $osDiskNumber | Sort-Object Offset
$osPart = $partitions | Where-Object { $_.PartitionNumber -eq $osPartitionNumber }
$rePart = $partitions | Where-Object { $_.PartitionNumber -eq $winre.PartitionNumber }

if (-not $osPart) {
    Fail 'OS partition not found in partition list.'
}

if (-not $rePart) {
    Fail 'WinRE partition not found in partition list.'
}

if ($rePart.Offset -le $osPart.Offset) {
    Fail 'WinRE partition is not located to the right of the OS partition.'
}

$between = $partitions | Where-Object {
    $_.Offset -gt $osPart.Offset -and $_.Offset -lt $rePart.Offset
}

if ($between.Count -gt 0) {
    Fail 'There are other partitions between the OS and WinRE partitions. Automatic extend is blocked.'
}

Write-Host ''
Write-Host 'Planned actions:' -ForegroundColor Yellow
Write-Host '  1. Disable WinRE'
Write-Host "  2. Remove disk $osDiskNumber partition $($winre.PartitionNumber)"
Write-Host "  3. Extend drive ${systemDrive} to maximum available size"
Write-Host ''

if ($YesIUnderstand) {
    Write-WarnMsg 'Non-interactive confirmation supplied by project operation.'
} else {
    $confirmation = Read-Host 'Type YES to continue'
    if ($confirmation -ne 'YES') {
        Write-WarnMsg 'Operation cancelled by user.'
        Pause-IfNeeded
        exit 0
    }
}

$shouldRun = $true
if (-not $YesIUnderstand) {
    $shouldRun = $PSCmdlet.ShouldProcess("Disk $osDiskNumber / Partition $($winre.PartitionNumber)", 'Disable WinRE, remove recovery partition, extend OS partition')
}

if ($shouldRun) {
    Write-Info 'Disabling WinRE...'
    reagentc /disable | Out-Host
    if ($LASTEXITCODE -ne 0) {
        Fail 'Failed to disable WinRE.'
    }

    $afterDisable = Get-WinREInfo
    if ($afterDisable.HasLocation) {
        Fail 'WinRE still exposes a partition location after disable. Aborting before partition removal.'
    }
    Write-Ok 'WinRE is disabled.'

    Write-Info 'Removing WinRE partition...'
    Remove-Partition -DiskNumber $osDiskNumber -PartitionNumber $winre.PartitionNumber -Confirm:$false
    Write-Ok 'WinRE partition removed.'

    Write-Info 'Calculating maximum supported size for the OS partition...'
    $supported = Get-PartitionSupportedSize -DiskNumber $osDiskNumber -PartitionNumber $osPartitionNumber
    if (-not $supported) {
        Fail 'Could not calculate supported partition size.'
    }

    Write-Info 'Extending OS partition...'
    Resize-Partition -DiskNumber $osDiskNumber -PartitionNumber $osPartitionNumber -Size $supported.SizeMax
    Write-Ok 'OS partition extended.'

    Write-Host ''
    Write-Info 'Final Windows RE status:'
    reagentc /info | Out-Host

    Show-PartitionList -DiskNumber $osDiskNumber -OsPartitionNumber $osPartitionNumber

    Write-Host ''
    Write-Ok 'Completed successfully.'
}

Pause-IfNeeded
