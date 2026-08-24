<#
.SYNOPSIS
    Audion DevOps Tools - Microsoft Snapshot brick.
.DESCRIPTION
    Captures and compares a full per-machine snapshot of file/protocol
    associations. This is the evidence layer under every other defense brick:
    whatever Redmond reclaims after a feature update, the snapshot shows
    exactly what moved and when.

    Snapshots are read straight from the registry (HKCU UserChoice) and stored
    per machine, so the git history honestly reflects each box. Default
    snapshot name is "Microsoft Snapshot" (no nameless snapshots).

    Operations:
        -Status   (compare) Current state vs the saved file; show drift.
        -Enable   (capture)  Save current associations to the snapshot file.

    There is deliberately no "restore" verb: Windows protects UserChoice with a
    per-user hash, and this project refuses to forge it. Put associations back
    through the Policy tab (DISM XML / HKLM DefaultAssociationsConfiguration).

    -Name <text>   Snapshot label (default 'Microsoft Snapshot').
    -Machine <id>  Machine tag for the filename (default $env:COMPUTERNAME).

.EXAMPLE
    .\Golden-Snapshot.ps1 -Enable
    .\Golden-Snapshot.ps1 -Status
    .\Golden-Snapshot.ps1 -Enable -Name "Microsoft Snapshot" -Machine AUDION-BASE
#>

[CmdletBinding(DefaultParameterSetName = 'Status')]
param(
    [Parameter(ParameterSetName = 'Status')]  [switch]$Status,
    [Parameter(ParameterSetName = 'Enable')]  [switch]$Enable,
    [string]$Name = 'Microsoft Snapshot',
    [string]$Machine = $env:COMPUTERNAME,
    [switch]$DryRun
)

$here = Split-Path -Parent $MyInvocation.MyCommand.Path
$common = Join-Path $here '_Common.ps1'
if (-not (Test-Path $common)) {
    Write-Host "ERROR: _Common.ps1 not found next to this script." -ForegroundColor Red
    exit 2
}
. $common

# Snapshots live next to the brick, in a git-friendly folder.
$SnapshotDir = Join-Path $here 'snapshots'

function Get-SnapshotPath {
    # Sanitize the label into a filename-safe slug; keep machine tag explicit.
    $slug = ($Name -replace '[^\w\- ]', '') -replace '\s+', '-'
    $safeMachine = ($Machine -replace '[^\w\-]', '_')
    return (Join-Path $SnapshotDir ("{0}.{1}.txt" -f $slug, $safeMachine))
}

# Read the live association map (".ext, ProgID" / "proto, ProgID").
function Get-CurrentDump {
    return @(Get-AssociationDump)
}

function Capture-Snapshot {
    if (-not $DryRun) { Assert-Admin }
    $path = Get-SnapshotPath
    $lines = Get-CurrentDump
    if (Test-DryRun -DryRun:$DryRun -Action "capture $($lines.Count) entries to $path (overwrites existing baseline if present)") {
        return
    }
    if (-not (Test-Path $SnapshotDir)) {
        New-Item -ItemType Directory -Path $SnapshotDir -Force | Out-Null
    }
    # Header is comment-only; the readers skip lines without a comma.
    $header = @(
        "# $Name"
        "# Machine : $Machine"
        "# Captured: $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')"
        "# Entries : $($lines.Count)"
        "# ---------------------------------------------"
    )
    Write-AssociationEntryFile -Path $path -Lines ([string[]]($header + $lines))
    Write-Line "Captured '$Name' for $Machine -> $($lines.Count) entries." 'Green'
    Write-Line "  File: $path"
    Write-Line "  Commit it to git to freeze this baseline." 'DarkGray'
}

function Read-SnapshotEntries {
    param([string]$Path)
    return @(Read-AssociationEntryFile -Path $Path)
}

function Compare-Snapshot {
    $path = Get-SnapshotPath
    Write-Line "Microsoft Snapshot status" 'Cyan'
    Write-Line ("Name   : {0}" -f $Name)
    Write-Line ("Machine: {0}" -f $Machine)
    Write-Line ("File   : {0}" -f $path)
    Write-Line ("-" * 70)
    if (-not (Test-Path $path)) {
        Write-Line "No saved snapshot yet. Run -Enable to capture a baseline." 'Yellow'
        return
    }

    $saved = Read-SnapshotEntries -Path $path
    $current = Get-CurrentDump

    # Build ext->progid maps for a precise comparison.
    $savedMap = @{}
    foreach ($l in $saved)   { $k, $v = $l -split ',', 2; $savedMap[$k.Trim().ToLower()] = $v.Trim() }
    $curMap = @{}
    foreach ($l in $current) { $k, $v = $l -split ',', 2; $curMap[$k.Trim().ToLower()]   = $v.Trim() }

    $drift = 0
    foreach ($ext in ($savedMap.Keys | Sort-Object)) {
        $want = $savedMap[$ext]
        $cur = if ($curMap.ContainsKey($ext)) { $curMap[$ext] } else { '<unset>' }
        if ($cur -ne $want) {
            Write-Host ("DRIFT {0,-12} now={1,-26} baseline={2}" -f $ext, $cur, $want) -ForegroundColor Yellow
            $drift++
        }
    }
    # New extensions present now but not in the baseline (informational).
    $newOnes = $curMap.Keys | Where-Object { -not $savedMap.ContainsKey($_) }
    foreach ($ext in ($newOnes | Sort-Object)) {
        Write-Host ("NEW   {0,-12} now={1}" -f $ext, $curMap[$ext]) -ForegroundColor DarkCyan
    }

    Write-Line ("-" * 70)
    if ($drift -eq 0) {
        Write-Line "MATCH: current state equals baseline. Redmond hasn't moved anything." 'Green'
    } else {
        Write-Line "$drift entr(y/ies) drifted from baseline." 'Yellow'
        Write-Line "Put them back through the Policy tab (DISM XML / HKLM DefaultAssociationsConfiguration)." 'DarkGray'
    }
}

$verb = $PSCmdlet.ParameterSetName
# Map to snapshot-specific action names for clearer log filenames.
$logVerb = switch ($verb) { 'Enable' { 'Capture' } default { 'Status' } }
Start-BrickLog -BrickName 'Microsoft-Snapshot' -Verb $logVerb -ScriptRoot $here | Out-Null
try {
    switch ($verb) {
        'Enable'  { Capture-Snapshot }
        default   { Compare-Snapshot }
    }
} finally {
    Stop-BrickLog
}
