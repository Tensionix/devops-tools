<#
.SYNOPSIS
    Audion DevOps Tools - Appx Rearm brick.
.DESCRIPTION
    Keeps a removal decision valid across Windows feature updates.

    Removing an in-box app (Microsoft-Apps.ps1 -Remove) is a one-time state:
    a feature update installs a new Windows build and can re-provision the very
    packages that were removed. This brick stores the chosen app list and
    registers a scheduled task that re-applies the removal whenever the build
    changes or a removed package reappears. Everything is done with documented
    Appx cmdlets and Task Scheduler - no protected-state hacks.

    The task runs as SYSTEM, so it never runs anything a user can change. -Enable
    locks %ProgramData%\Audion\AppxGuard (owner Administrators; SYSTEM and
    Administrators may write, Users may only read), puts a copy of the three
    scripts the task needs into its bin folder and points the task at that copy,
    run by the built-in Windows PowerShell 5.1 of System32 - the PowerShell the
    Appx cmdlets are meant for. The scripts of the program folder are never run
    by the task: any user may write there.

    Operations:
        -Status   Show the task, the stored app list and the last check result.
        -Enable   Store -Target and register/replace the re-apply task.
        -Disable  Remove the task (the stored list is kept for reference).
        -RunCheck Run one re-apply pass now (this is what the task calls).

.EXAMPLE
    .\Appx-Rearm.ps1 -Enable -Target ZuneMusic,ZuneVideo
    .\Appx-Rearm.ps1 -Status
    .\Appx-Rearm.ps1 -RunCheck
    .\Appx-Rearm.ps1 -Disable
#>

[CmdletBinding(DefaultParameterSetName = 'Status')]
param(
    [Parameter(ParameterSetName = 'Status')]   [switch]$Status,
    [Parameter(ParameterSetName = 'Enable')]   [switch]$Enable,
    [Parameter(ParameterSetName = 'Disable')]  [switch]$Disable,
    [Parameter(ParameterSetName = 'RunCheck')] [switch]$RunCheck,
    [string[]]$Target = @()
)

$here = Split-Path -Parent $MyInvocation.MyCommand.Path
$common = Join-Path $here '_Common.ps1'
if (-not (Test-Path $common)) {
    Write-Host "ERROR: _Common.ps1 not found next to this script." -ForegroundColor Red
    exit 2
}
. $common

$TaskName   = 'Audion-AppxRearm'
$TaskFolder = '\Audion\'
$AppsBrick  = Join-Path $here 'Microsoft-Apps.ps1'
$StateDir   = Join-Path $env:ProgramData 'Audion\AppxGuard'
$TargetFile = Join-Path $StateDir 'targets.txt'
$BuildFile  = Join-Path $StateDir 'last_build.txt'
$RearmLog   = Join-Path $StateDir 'rearm.log'
# The protected copy the task runs, and what it runs it with.
$GuardBin   = Join-Path $StateDir 'bin'
$GuardFiles = @('Appx-Rearm.ps1', '_Common.ps1', 'Microsoft-Apps.ps1')
$TaskHost   = Join-Path $env:SystemRoot 'System32\WindowsPowerShell\v1.0\powershell.exe'

function Get-WindowsBuildTag {
    try {
        $key = Get-ItemProperty -Path 'HKLM:\SOFTWARE\Microsoft\Windows NT\CurrentVersion' -ErrorAction Stop
        return ('{0}.{1}' -f $key.CurrentBuild, $key.UBR)
    } catch {
        return [string][System.Environment]::OSVersion.Version
    }
}

function Get-StoredTargets {
    if (-not (Test-Path -LiteralPath $TargetFile)) { return @() }
    return @(
        Get-Content -LiteralPath $TargetFile -ErrorAction SilentlyContinue |
            ForEach-Object { $_.Trim() } |
            Where-Object { $_ -and $_ -notmatch '^\s*#' }
    )
}

function Set-StoredTargets {
    param([Parameter(Mandatory)][string[]]$Items)
    if (-not (Test-Path -LiteralPath $StateDir)) {
        New-Item -ItemType Directory -Path $StateDir -Force | Out-Null
    }
    [System.IO.File]::WriteAllLines($TargetFile, @($Items), [System.Text.UTF8Encoding]::new($false))
}

function Write-RearmLog {
    param([Parameter(Mandatory)][string]$Text)
    try {
        if (-not (Test-Path -LiteralPath $StateDir)) {
            New-Item -ItemType Directory -Path $StateDir -Force | Out-Null
        }
        Add-Content -LiteralPath $RearmLog -Value $Text -ErrorAction SilentlyContinue
    } catch { }
    Write-Host $Text
}

# The state folder belongs to the machine: owner Administrators, SYSTEM and Administrators may
# write, Users may read. A fresh security descriptor replaces whatever the folder had - a folder a
# user created first (ProgramData lets any user create one) is taken over, not trusted.
function Lock-GuardFolder {
    if (-not (Test-Path -LiteralPath $StateDir)) {
        New-Item -ItemType Directory -Path $StateDir -Force | Out-Null
    }
    $admins = New-Object System.Security.Principal.SecurityIdentifier 'S-1-5-32-544'
    $acl = New-Object System.Security.AccessControl.DirectorySecurity
    $acl.SetOwner($admins)
    $acl.SetAccessRuleProtection($true, $false)
    $inherit = [System.Security.AccessControl.InheritanceFlags]'ContainerInherit, ObjectInherit'
    $none = [System.Security.AccessControl.PropagationFlags]::None
    foreach ($pair in @(@('S-1-5-18', 'FullControl'), @('S-1-5-32-544', 'FullControl'), @('S-1-5-32-545', 'ReadAndExecute'))) {
        $sid = New-Object System.Security.Principal.SecurityIdentifier $pair[0]
        $acl.AddAccessRule((New-Object System.Security.AccessControl.FileSystemAccessRule($sid, $pair[1], $inherit, $none, 'Allow')))
    }
    try {
        Set-Acl -LiteralPath $StateDir -AclObject $acl -ErrorAction Stop
    } catch {
        # A folder whose owner shut the administrators out: they take it over first.
        & takeown.exe /F $StateDir /A /R /D Y | Out-Null
        Set-Acl -LiteralPath $StateDir -AclObject $acl -ErrorAction Stop
    }
    # What lies inside takes the rights of the folder and the same owner: no file keeps a right of its own.
    $children = Join-Path $StateDir '*'
    if (Get-ChildItem -LiteralPath $StateDir -Force -ErrorAction SilentlyContinue) {
        & icacls.exe $children /setowner '*S-1-5-32-544' /T /C /Q | Out-Null
        & icacls.exe $children /reset /T /C /Q | Out-Null
    }
}

# The copy of the scripts the task runs. Everything in the bin folder but the logs of earlier runs goes
# every time: no script a user may have put there before the folder was locked survives.
function Install-GuardCopy {
    if (Test-Path -LiteralPath $GuardBin) {
        Get-ChildItem -LiteralPath $GuardBin -Force | Where-Object { $_.Name -ne 'logs' } | Remove-Item -Recurse -Force -ErrorAction Stop
    } else {
        New-Item -ItemType Directory -Path $GuardBin -Force | Out-Null
    }
    foreach ($name in $GuardFiles) {
        $source = Join-Path $here $name
        if (-not (Test-Path -LiteralPath $source)) { throw "$name not found next to this script." }
        Copy-Item -LiteralPath $source -Destination (Join-Path $GuardBin $name) -Force -ErrorAction Stop
    }
}

# Whether the copy the task runs is the same as the scripts of the program: after an update of the
# program the task keeps the old copy until -Enable runs again.
function Test-GuardCopyCurrent {
    foreach ($name in $GuardFiles) {
        $copy = Join-Path $GuardBin $name
        $source = Join-Path $here $name
        if (-not (Test-Path -LiteralPath $copy) -or -not (Test-Path -LiteralPath $source)) { return $false }
        if ((Get-FileHash -LiteralPath $copy -Algorithm SHA256).Hash -ne (Get-FileHash -LiteralPath $source -Algorithm SHA256).Hash) { return $false }
    }
    return $true
}

function Show-Status {
    Write-Line "Appx Rearm status" 'Cyan'
    Write-Line ("-" * 60)
    Write-Line ("Current Windows build: {0}" -f (Get-WindowsBuildTag))
    if (Test-Path -LiteralPath $BuildFile) {
        Write-Line ("Last applied build   : {0}" -f (Get-Content -LiteralPath $BuildFile -ErrorAction SilentlyContinue))
    } else {
        Write-Line "Last applied build   : <never>"
    }

    $stored = @(Get-StoredTargets)
    if ($stored.Count -gt 0) {
        Write-Line ("Apps kept removed    : {0}" -f ($stored -join ', '))
    } else {
        Write-Line "Apps kept removed    : <none stored yet>" 'Yellow'
    }

    $task = Get-ScheduledTask -TaskName $TaskName -TaskPath $TaskFolder -ErrorAction SilentlyContinue
    if (-not $task) {
        Write-Line "Task '$TaskName' is NOT installed. Run -Enable." 'Yellow'
    } else {
        Write-Line "Task installed: $($task.TaskName)" 'Green'
        Write-Line "  State    : $($task.State)"
        $action = @($task.Actions)[0]
        $taskScript = Join-Path $GuardBin 'Appx-Rearm.ps1'
        Write-Line "  Host     : $($action.Execute)"
        if ($action.Execute -ne $TaskHost -or [string]$action.Arguments -notlike "*$taskScript*") {
            # A task of an earlier version runs the scripts of the program folder, perhaps with a PowerShell that is gone.
            Write-Line "  The task runs an unprotected copy or a PowerShell that may be gone. Run -Enable again." 'Yellow'
        } elseif (-not (Test-Path -LiteralPath $action.Execute)) {
            Write-Line "  The PowerShell of the task is missing. Run -Enable again." 'Yellow'
        } elseif (-not (Test-GuardCopyCurrent)) {
            Write-Line "  The protected copy differs from the scripts of the program. Run -Enable again to refresh it." 'Yellow'
        } else {
            Write-Line "  Script   : $taskScript (protected copy, current)" 'DarkGray'
        }
        $info = Get-ScheduledTaskInfo -TaskName $TaskName -TaskPath $TaskFolder -ErrorAction SilentlyContinue
        if ($info) {
            Write-Line "  Last run : $($info.LastRunTime)"
            Write-Line "  Last code: $($info.LastTaskResult)"
            Write-Line "  Next run : $($info.NextRunTime)"
        }
    }
    if (Test-Path -LiteralPath $RearmLog) {
        $last = Get-Content -LiteralPath $RearmLog -Tail 1 -ErrorAction SilentlyContinue
        if ($last) { Write-Line "  Last check: $last" 'DarkGray' }
    }
    Write-Line ("-" * 60)
    Write-Line "The task only re-applies an already made removal decision; it never removes anything new." 'DarkGray'
}

function Enable-Guard {
    Assert-Admin
    if (-not (Test-Path -LiteralPath $AppsBrick)) {
        Write-Line "ERROR: Microsoft-Apps.ps1 not found next to this script." 'Red'
        exit 2
    }

    $items = @()
    foreach ($entry in @($Target)) {
        if ([string]::IsNullOrWhiteSpace([string]$entry)) { continue }
        $items += ([string]$entry -split '[,;|]' | ForEach-Object { $_.Trim() } | Where-Object { $_ })
    }
    if (-not $items) {
        $items = @(Get-StoredTargets)
    }
    if (-not $items) {
        Write-Line "ERROR: no apps given. Pass -Target with the apps that must stay removed." 'Red'
        exit 2
    }
    if (-not (Test-Path -LiteralPath $TaskHost)) {
        Write-Line "ERROR: Windows PowerShell 5.1 not found: $TaskHost" 'Red'
        exit 2
    }

    Lock-GuardFolder
    Set-StoredTargets -Items $items
    Install-GuardCopy

    $taskScript = Join-Path $GuardBin 'Appx-Rearm.ps1'
    $argString = "-NoProfile -ExecutionPolicy Bypass -WindowStyle Hidden -File `"$taskScript`" -RunCheck"
    $action = New-ScheduledTaskAction -Execute $TaskHost -Argument $argString
    $triggers = @(
        New-ScheduledTaskTrigger -AtStartup
        New-ScheduledTaskTrigger -Daily -At '03:30'
    )
    # Provisioned-package removal is a machine operation: run as SYSTEM.
    $principal = New-ScheduledTaskPrincipal -UserId 'S-1-5-18' -LogonType ServiceAccount -RunLevel Highest
    $settings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries `
        -StartWhenAvailable -ExecutionTimeLimit (New-TimeSpan -Minutes 20)

    Unregister-ScheduledTask -TaskName $TaskName -TaskPath $TaskFolder -Confirm:$false -ErrorAction SilentlyContinue
    Register-ScheduledTask -TaskName $TaskName -TaskPath $TaskFolder `
        -Action $action -Trigger $triggers -Principal $principal -Settings $settings `
        -Description 'Audion: re-apply the Microsoft in-box app removal after Windows feature updates.' `
        -Force | Out-Null

    Write-Line "Appx Rearm ENABLED. Host: $TaskHost" 'Green'
    Write-Line "  Script: $taskScript (protected copy: only Administrators and SYSTEM may change it)" 'DarkGray'
    Write-Line ("  Apps kept removed: {0}" -f ($items -join ', '))
    Write-Line "  Runs at startup and daily; re-applies only the stored list." 'DarkGray'
}

function Disable-Guard {
    Assert-Admin
    $task = Get-ScheduledTask -TaskName $TaskName -TaskPath $TaskFolder -ErrorAction SilentlyContinue
    if (-not $task) {
        Write-Line "Task '$TaskName' not present - nothing to remove." 'Yellow'
        return
    }
    Unregister-ScheduledTask -TaskName $TaskName -TaskPath $TaskFolder -Confirm:$false -ErrorAction SilentlyContinue
    # The copy existed for the task alone; the logs of its runs stay.
    foreach ($name in $GuardFiles) {
        Remove-Item -LiteralPath (Join-Path $GuardBin $name) -Force -ErrorAction SilentlyContinue
    }
    Write-Line "Appx Rearm DISABLED (task removed). Stored app list was kept." 'Yellow'
}

function Invoke-RearmCheck {
    $stamp = Get-Date -Format 'yyyy-MM-dd HH:mm:ss'
    $stored = @(Get-StoredTargets)
    if (-not $stored) {
        Write-RearmLog "$stamp  SKIP   no stored app list"
        return
    }
    if (-not (Test-Path -LiteralPath $AppsBrick)) {
        Write-RearmLog "$stamp  ERROR  Microsoft-Apps.ps1 not found"
        exit 2
    }

    $build = Get-WindowsBuildTag
    $lastBuild = if (Test-Path -LiteralPath $BuildFile) { (Get-Content -LiteralPath $BuildFile -ErrorAction SilentlyContinue | Select-Object -First 1) } else { '' }

    $statusText = & $AppsBrick -Status -Target ($stored -join ',') 2>&1 | Out-String
    $returned = ([regex]::Matches($statusText, 'INSTALLED|PROVISIONED')).Count

    if ($returned -eq 0 -and $build -eq $lastBuild) {
        Write-RearmLog "$stamp  OK     build $build, nothing came back"
        return
    }

    Write-RearmLog "$stamp  REARM  build $build (was '$lastBuild'), $returned package marker(s) present -> re-applying removal"
    & $AppsBrick -Remove -Target ($stored -join ',') 2>&1 | ForEach-Object { Write-Host $_ }
    if (-not (Test-Path -LiteralPath $StateDir)) {
        New-Item -ItemType Directory -Path $StateDir -Force | Out-Null
    }
    [System.IO.File]::WriteAllText($BuildFile, $build, [System.Text.UTF8Encoding]::new($false))
    Write-RearmLog "$stamp  DONE   removal re-applied for: $($stored -join ', ')"
}

switch ($PSCmdlet.ParameterSetName) {
    'Enable'   {
        Start-BrickLog -BrickName 'Appx-Rearm' -Verb 'Enable' -ScriptRoot $here | Out-Null
        try { Enable-Guard } finally { Stop-BrickLog }
    }
    'Disable'  {
        Start-BrickLog -BrickName 'Appx-Rearm' -Verb 'Disable' -ScriptRoot $here | Out-Null
        try { Disable-Guard } finally { Stop-BrickLog }
    }
    'RunCheck' { Invoke-RearmCheck }
    default    { Show-Status }
}
