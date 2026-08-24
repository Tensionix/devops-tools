<#
.SYNOPSIS
    Audion DevOps Tools - Defender Exclusions brick.
.DESCRIPTION
    Manages Microsoft Defender exclusions for the Audion hot paths and
    processes, so Defender stops eating I/O and false-flagging your own
    scripts/tools - WITHOUT disabling Defender.

    This brick deliberately does NOT attempt to permanently disable
    Defender or bypass Tamper Protection. Those bypasses are blocked by
    Windows by design and break the security stack after updates. The
    -Status view reports Tamper Protection so you know whether the manual
    toggle is on, but enabling/disabling it stays a manual UI action.

    Operations (the "holy trinity"):
        -Status   Show exclusions + real-time + tamper state.
        -Enable   Add the Audion exclusion set (paths + processes).
        -Disable  Remove the Audion exclusion set (restore defaults).

.EXAMPLE
    .\Defender-Exclusions.ps1 -Status
    .\Defender-Exclusions.ps1 -Enable
    .\Defender-Exclusions.ps1 -Disable
#>

[CmdletBinding(DefaultParameterSetName = 'Status')]
param(
    [Parameter(ParameterSetName = 'Status')] [switch]$Status,
    [Parameter(ParameterSetName = 'Enable')] [switch]$Enable,
    [Parameter(ParameterSetName = 'Disable')] [switch]$Disable
)

$here = Split-Path -Parent $MyInvocation.MyCommand.Path
$common = Join-Path $here '_Common.ps1'
if (-not (Test-Path $common)) {
    Write-Host "ERROR: _Common.ps1 not found next to this script." -ForegroundColor Red
    exit 2
}
. $common

# System drive is always kept under protection (never excluded).
$SystemDrive = ($env:SystemDrive).TrimEnd(':') + ':\'   # normally 'C:\'

# Per user's explicit choice: exclude every mounted drive root EXCEPT the
# system drive. Only roots of drives that actually exist are applied, so no
# phantom letters are written. C:\ stays under Defender protection.
function Get-CandidatePaths {
    $roots = @()
    Get-PSDrive -PSProvider FileSystem -ErrorAction SilentlyContinue |
        Where-Object { $_.Name -match '^[A-Za-z]$' } |
        ForEach-Object {
            $root = "$($_.Name):\"
            if ($root -ne $SystemDrive) { $roots += $root }
        }
    return ($roots | Sort-Object -Unique)
}

$CandidatePaths = Get-CandidatePaths

$ExcludeProcesses = @(
    'ffmpeg.exe'
    'VSPipe.exe'
    'python.exe'
    'pwsh.exe'
)

function Get-CurrentExclusions {
    try {
        return Get-MpPreference -ErrorAction Stop
    } catch {
        Write-Line "ERROR: Defender cmdlets unavailable: $($_.Exception.Message)" 'Red'
        return $null
    }
}

function Show-Status {
    Write-Line "Defender Exclusions status" 'Cyan'
    Write-Line ("-" * 50)

    $mp = Get-CurrentExclusions
    if ($null -eq $mp) { exit 1 }

    # Real-time + tamper (read-only reporting).
    try {
        $st = Get-MpComputerStatus -ErrorAction Stop
        $rt = -not $st.RealTimeProtectionEnabled
        Write-Host ("RealTimeProtection : {0}" -f $st.RealTimeProtectionEnabled) `
            -ForegroundColor ($(if ($st.RealTimeProtectionEnabled) {'Green'} else {'Yellow'}))
        Write-Host ("TamperProtection   : {0}" -f $st.IsTamperProtected) `
            -ForegroundColor ($(if ($st.IsTamperProtected) {'Green'} else {'Yellow'}))
        Write-Line "  (Tamper toggle is manual-only by design; this brick never bypasses it.)" 'DarkGray'
    } catch {
        Write-Line "Could not read Defender status: $($_.Exception.Message)" 'Yellow'
    }

    Write-Line ("-" * 50)
    Write-Line "Drive-root exclusions (all drives except $SystemDrive):"
    $curPaths = @($mp.ExclusionPath)
    foreach ($p in $CandidatePaths) {
        $present = $curPaths -contains $p
        $mark = if ($present) { 'SET' } else { '---' }
        $color = if ($present) { 'Green' } else { 'Yellow' }
        Write-Host ("  [{0}] {1}" -f $mark, $p) -ForegroundColor $color
    }
    # Surface any extra excluded paths not in the candidate set (manual adds).
    $extra = $curPaths | Where-Object { $_ -and ($CandidatePaths -notcontains $_) }
    if ($extra) {
        Write-Line "  Other existing exclusions:" 'DarkGray'
        $extra | ForEach-Object { Write-Host "    [SET] $_" -ForegroundColor DarkGray }
    }

    Write-Line "Process exclusions:"
    $curProc = @($mp.ExclusionProcess)
    foreach ($pr in $ExcludeProcesses) {
        $present = $curProc -contains $pr
        $mark = if ($present) { 'SET' } else { '---' }
        $color = if ($present) { 'Green' } else { 'Yellow' }
        Write-Host ("  [{0}] {1}" -f $mark, $pr) -ForegroundColor $color
    }
}

function Enable-Guard {
    Assert-Admin
    $applied = 0
    foreach ($p in $CandidatePaths) {
        # CandidatePaths is built from live drives, so each root exists.
        Add-MpPreference -ExclusionPath $p -ErrorAction SilentlyContinue
        Write-Line "  + path  $p" 'Green'
        $applied++
    }
    foreach ($pr in $ExcludeProcesses) {
        Add-MpPreference -ExclusionProcess $pr -ErrorAction SilentlyContinue
        Write-Line "  + proc  $pr" 'Green'
        $applied++
    }
    Write-Line "Defender exclusions ENABLED ($applied entr(y/ies)). System drive $SystemDrive left protected." 'Green'
}

function Disable-Guard {
    Assert-Admin
    foreach ($p in $CandidatePaths) {
        Remove-MpPreference -ExclusionPath $p -ErrorAction SilentlyContinue
        Write-Line "  - path  $p" 'Yellow'
    }
    foreach ($pr in $ExcludeProcesses) {
        Remove-MpPreference -ExclusionProcess $pr -ErrorAction SilentlyContinue
        Write-Line "  - proc  $pr" 'Yellow'
    }
    Write-Line "Defender exclusions DISABLED (Audion set removed)." 'Yellow'
}

$verb = $PSCmdlet.ParameterSetName
Start-BrickLog -BrickName 'Defender-Exclusions' -Verb $verb -ScriptRoot $here | Out-Null
try {
    switch ($verb) {
        'Enable'  { Enable-Guard }
        'Disable' { Disable-Guard }
        default   { Show-Status }
    }
} finally {
    Stop-BrickLog
}
