<#
.SYNOPSIS
    Audion DevOps Tools - Drift Watch brick.
.DESCRIPTION
    Installs a scheduled task that, at every user logon, checks the live
    association map against the "Microsoft Snapshot" baseline and raises a
    Windows toast if drift is detected. It is a WARNING system only - it never
    auto-restores. You decide whether to run Golden-Snapshot.ps1 -Disable.

    Operations (the "holy trinity"):
        -Status   Show whether the scheduled task is installed + last result.
        -Enable   Install/replace the at-logon drift-watch task.
        -Disable  Remove the drift-watch task.

    Internal:
        -RunCheck One drift check now (this is what the task invokes). Writes a
                  drift log line and toasts if drifted. Safe to run manually.

.EXAMPLE
    .\Drift-Watch.ps1 -Status
    .\Drift-Watch.ps1 -Enable
    .\Drift-Watch.ps1 -Disable
    .\Drift-Watch.ps1 -RunCheck
#>

[CmdletBinding(DefaultParameterSetName = 'Status')]
param(
    [Parameter(ParameterSetName = 'Status')]   [switch]$Status,
    [Parameter(ParameterSetName = 'Enable')]   [switch]$Enable,
    [Parameter(ParameterSetName = 'Disable')]  [switch]$Disable,
    [Parameter(ParameterSetName = 'RunCheck')] [switch]$RunCheck
)

$here = Split-Path -Parent $MyInvocation.MyCommand.Path
$common = Join-Path $here '_Common.ps1'
if (-not (Test-Path $common)) {
    Write-Host "ERROR: _Common.ps1 not found next to this script." -ForegroundColor Red
    exit 2
}
. $common

$TaskName   = 'Audion-AssociationDriftWatch'
$TaskFolder = '\Audion\'
$SnapshotBrick = Join-Path $here 'Golden-Snapshot.ps1'

# Resolve the host that the task should use: portable pwsh first, then system.
function Resolve-PwshForTask {
    $projectRoot = Get-AssociationDefenseProjectRoot -ScriptRoot $here
    $candidates = @(
        (Join-Path $projectRoot 'system_core\powershell\pwsh.exe')
        (Get-Command pwsh.exe -ErrorAction SilentlyContinue).Source
        "$env:SystemRoot\System32\WindowsPowerShell\v1.0\powershell.exe"
    )
    foreach ($c in $candidates) {
        if ($c -and (Test-Path $c)) { return $c }
    }
    return "$env:SystemRoot\System32\WindowsPowerShell\v1.0\powershell.exe"
}

function Show-Status {
    Write-Line "Drift Watch status" 'Cyan'
    Write-Line ("-" * 50)
    $task = Get-ScheduledTask -TaskName $TaskName -TaskPath $TaskFolder -ErrorAction SilentlyContinue
    if (-not $task) {
        Write-Line "Task '$TaskName' is NOT installed. Run -Enable." 'Yellow'
        return
    }
    Write-Line "Task installed: $($task.TaskName)" 'Green'
    Write-Line "  State   : $($task.State)"
    $info = Get-ScheduledTaskInfo -TaskName $TaskName -TaskPath $TaskFolder -ErrorAction SilentlyContinue
    if ($info) {
        Write-Line "  Last run: $($info.LastRunTime)"
        Write-Line "  Last code: $($info.LastTaskResult)"
        Write-Line "  Next run: $($info.NextRunTime)"
    }
    # Surface the most recent drift log line, if any.
    $logDir = Get-BrickLogDir -ScriptRoot $here
    if ($logDir) {
        $driftLog = Join-Path $logDir 'drift-watch.log'
        if (Test-Path $driftLog) {
            $last = Get-Content $driftLog -Tail 1 -ErrorAction SilentlyContinue
            if ($last) { Write-Line "  Last check: $last" 'DarkGray' }
        }
    }
}

function Enable-Guard {
    Assert-Admin
    if (-not (Test-Path $SnapshotBrick)) {
        Write-Line "ERROR: Golden-Snapshot.ps1 not found next to this script." 'Red'
        exit 2
    }
    $pwsh = Resolve-PwshForTask
    # The task calls THIS brick with -RunCheck.
    $argString = "-NoProfile -ExecutionPolicy Bypass -WindowStyle Hidden -File `"$($MyInvocation.MyCommand.Path)`" -RunCheck"
    $action  = New-ScheduledTaskAction -Execute $pwsh -Argument $argString
    $trigger = New-ScheduledTaskTrigger -AtLogOn
    # Run as the logged-on user (needed for toast); least privilege.
    $principal = New-ScheduledTaskPrincipal -GroupId 'S-1-5-32-545' -RunLevel Limited
    $settings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries `
        -StartWhenAvailable -ExecutionTimeLimit (New-TimeSpan -Minutes 5)

    # Replace any existing instance idempotently.
    Unregister-ScheduledTask -TaskName $TaskName -TaskPath $TaskFolder -Confirm:$false -ErrorAction SilentlyContinue
    Register-ScheduledTask -TaskName $TaskName -TaskPath $TaskFolder `
        -Action $action -Trigger $trigger -Principal $principal -Settings $settings `
        -Description 'Audion: warn on file-association drift vs the Microsoft Snapshot baseline (no auto-restore).' `
        -Force | Out-Null

    Write-Line "Drift Watch ENABLED (at logon). Host: $pwsh" 'Green'
    Write-Line "  It warns only - it never auto-restores associations." 'DarkGray'
}

function Disable-Guard {
    Assert-Admin
    $task = Get-ScheduledTask -TaskName $TaskName -TaskPath $TaskFolder -ErrorAction SilentlyContinue
    if (-not $task) {
        Write-Line "Task '$TaskName' not present - nothing to remove." 'Yellow'
        return
    }
    Unregister-ScheduledTask -TaskName $TaskName -TaskPath $TaskFolder -Confirm:$false -ErrorAction SilentlyContinue
    Write-Line "Drift Watch DISABLED (task removed)." 'Yellow'
}

# Invoked by the scheduled task. Runs a single drift check, logs, toasts.
function Invoke-DriftCheck {
    $logDir = Get-BrickLogDir -ScriptRoot $here
    $driftLog = if ($logDir) { Join-Path $logDir 'drift-watch.log' } else { $null }
    $stamp = Get-Date -Format 'yyyy-MM-dd HH:mm:ss'

    # Ask the snapshot brick for status; count DRIFT lines in its output.
    $output = & $SnapshotBrick -Status 2>&1 | Out-String
    $driftCount = ([regex]::Matches($output, '(?m)^DRIFT\b')).Count

    $line = if ($driftCount -gt 0) {
        "$stamp  DRIFT  $driftCount entr(y/ies) differ from baseline"
    } else {
        "$stamp  OK     no drift"
    }
    if ($driftLog) { Add-Content -Path $driftLog -Value $line -ErrorAction SilentlyContinue }
    Write-Host $line

    if ($driftCount -gt 0) {
        Show-Toast -Title 'Association drift detected' `
            -Message "$driftCount association(s) changed from the Microsoft Snapshot. Run Golden-Snapshot.ps1 -Disable to restore." | Out-Null
    }
}

switch ($PSCmdlet.ParameterSetName) {
    'Enable'   {
        Start-BrickLog -BrickName 'Drift-Watch' -Verb 'Enable' -ScriptRoot $here | Out-Null
        try { Enable-Guard } finally { Stop-BrickLog }
    }
    'Disable'  {
        Start-BrickLog -BrickName 'Drift-Watch' -Verb 'Disable' -ScriptRoot $here | Out-Null
        try { Disable-Guard } finally { Stop-BrickLog }
    }
    'RunCheck' { Invoke-DriftCheck }
    default    { Show-Status }
}
