<#
.SYNOPSIS
    Audion DevOps Tools - Association Defense wrapper.
.DESCRIPTION
    One entry point for the defense bricks:
        Edge-Debloat.ps1        (Edge stops pushing itself; WebView2 protected)
        AppX-ReinstallBlock.ps1 (block reinstall of removed apps - Pro)
        Microsoft-Apps.ps1      (in-box app removal/restore - status only here)
        Appx-Rearm.ps1          (re-apply removal after feature updates)
        Defender-Exclusions.ps1 (hot-path exclusions, no Defender bypass)

    Unified "holy trinity" across all bricks:
        -Status   Run every brick's status.
        -Enable   Apply every guard.
        -Disable  Remove every guard.

    Target a single brick with -Only:
        -Only Edge | AppX | Apps | Rearm | Defender | Snapshot | Groups | Drift

.EXAMPLE
    .\Defense.ps1 -Status
    .\Defense.ps1 -Enable
    .\Defense.ps1 -Enable -Only Edge
    .\Defense.ps1 -Disable
#>

[CmdletBinding(DefaultParameterSetName = 'Status')]
param(
    [Parameter(ParameterSetName = 'Status')]  [switch]$Status,
    [Parameter(ParameterSetName = 'Enable')]  [switch]$Enable,
    [Parameter(ParameterSetName = 'Disable')] [switch]$Disable,
    [ValidateSet('Apps', 'Edge', 'AppX', 'Rearm', 'Defender', 'Snapshot', 'Groups', 'Drift')] [string]$Only
)

$here = Split-Path -Parent $MyInvocation.MyCommand.Path

# Brick registry: key -> script file. Order matters for Enable:
# block AppX reinstall first while publisher identities are still discoverable,
# then remove the hijacker apps.
$Bricks = [ordered]@{
    'AppX'     = 'AppX-ReinstallBlock.ps1'
    'Apps'     = 'Microsoft-Apps.ps1'
    'Rearm'    = 'Appx-Rearm.ps1'
    'Edge'     = 'Edge-Debloat.ps1'
    'Defender' = 'Defender-Exclusions.ps1'
    'Snapshot' = 'Golden-Snapshot.ps1'
    'Groups'   = 'Group-Snapshot.ps1'
    'Drift'    = 'Drift-Watch.ps1'
}

# Snapshot capture, group commit/compose and in-box app removal are deliberate
# acts - never folded into bulk -Enable/-Disable. In bulk runs they participate
# in -Status only.
$StatusOnlyMutationKeys = @('Snapshot', 'Groups', 'Apps')

function Resolve-Verb {
    switch ($PSCmdlet.ParameterSetName) {
        'Enable'  { return 'Enable' }
        'Disable' { return 'Disable' }
        default   { return 'Status' }
    }
}

$verbName = Resolve-Verb
$verb = "-$verbName"
$targets = if ($Only) { @($Only) } else { @($Bricks.Keys) }

# In bulk runs, Snapshot takes part in -Status only. Capture/restore must be
# explicit (-Only Snapshot), never a side effect of bulk enable/disable.
if (-not $Only -and $verb -ne '-Status') {
    $targets = $targets | Where-Object { $StatusOnlyMutationKeys -notcontains $_ }
}

if ($Only -eq 'Groups' -and $verb -ne '-Status') {
    Write-Host "ERROR: Groups support Status through this wrapper only. Use Group-Snapshot.ps1 for Commit/Compose." -ForegroundColor Red
    exit 1
}

if ($Only -eq 'Apps' -and $verb -ne '-Status') {
    Write-Host "ERROR: in-box app removal is never a bulk action. Use Microsoft-Apps.ps1 with -Remove / -Restore / -Provision." -ForegroundColor Red
    exit 1
}

# Disable in reverse order so guards come down cleanly.
if ($verb -eq '-Disable' -and -not $Only) {
    $targets = $targets | Sort-Object -Descending
}

$failures = 0
foreach ($key in $targets) {
    $script = Join-Path $here $Bricks[$key]
    Write-Host ""
    Write-Host ("==== {0} {1} ====" -f $key, $verb) -ForegroundColor Magenta
    if (-not (Test-Path $script)) {
        Write-Host "ERROR: brick not found: $script" -ForegroundColor Red
        $failures++
        continue
    }
    # Each brick self-checks for admin where it mutates state.
    $scriptParams = @{ $verbName = $true }
    $global:LASTEXITCODE = 0
    & $script @scriptParams
    $childExitCode = if ($null -ne $LASTEXITCODE) { [int]$LASTEXITCODE } else { 0 }
    if ($childExitCode -ne 0) {
        Write-Host "  (brick '$key' exited with code $childExitCode)" -ForegroundColor DarkYellow
        $failures++
    }
    $global:LASTEXITCODE = 0
}

Write-Host ""
if ($failures -eq 0) {
    Write-Host "All requested bricks completed ($verb)." -ForegroundColor Green
} elseif ($verbName -eq 'Status') {
    Write-Host "$failures brick(s) reported status warnings. Review output above." -ForegroundColor Yellow
    exit 0
} else {
    Write-Host "$failures brick(s) reported a problem. Review output above." -ForegroundColor Yellow
    exit 1
}
