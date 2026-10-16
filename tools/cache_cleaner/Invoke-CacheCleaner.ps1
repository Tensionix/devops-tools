<#
.SYNOPSIS
    Frees space on the system drive by clearing caches that rebuild themselves.

.DESCRIPTION
    Targets (all per current user, except wintemp):
      pip     - %LOCALAPPDATA%\pip\cache (same as "pip cache purge")
      npm     - %LOCALAPPDATA%\npm-cache\_cacache (same as "npm cache clean --force")
      nuget   - NuGet http cache, plugins cache and scratch folder;
                the package folder ~\.nuget\packages only with -NuGetPackages
                (the next build downloads every package again)
      temp    - %TEMP% entries not touched for -TempAgeHours (default 24);
                anything still open is skipped
      wintemp - %SystemRoot%\Temp entries not touched for -TempAgeHours; needs
                administrator rights and is skipped without them
      claude  - %TEMP%\claude, the scratch of Claude Code: a session folder whose
                newest file is older than -TempAgeHours goes, a session still at
                work stays. The folder %TEMP%\claude itself is touched every day,
                so the temp target alone never reaches what lies inside it
      adobe   - Adobe media cache (Media Cache Files, Media Cache, Peak Files) in
                %APPDATA%\Adobe\Common and where Premiere Pro moved it
                (HKCU\Software\Adobe\Common <version>\Media Cache: FolderPath,
                DatabasePath) - only folders named so are cleared, never the
                place they stand in; skipped while Premiere Pro, After Effects,
                Media Encoder or Audition is running
      chrome  - Chrome's on-device AI model (OptGuideOnDeviceModel, ~4 GB).
                Chrome answers from the cloud anyway; without the policy it
                downloads the model again, so -Mode Clean also sets the Chrome
                policy GenAILocalFoundationalModelSettings = 1 for this user
                (HKCU). Chrome then shows "Managed by your organization".
                Only when named in -Targets; skipped while Chrome is running.

    Nothing here is user data: every folder is a cache its program refills on
    demand. Files are deleted, not moved to the Recycle Bin - moving them there
    would free nothing.

.PARAMETER Mode
    Audit - measure only, change nothing (default)
    Clean - delete

.PARAMETER Targets
    Which caches. Default: pip, npm, nuget, temp, wintemp, claude, adobe. Add chrome explicitly.

.PARAMETER NuGetPackages
    Also clear ~\.nuget\packages.

.PARAMETER TempAgeHours
    Temp entries younger than this stay. Default 24.

.PARAMETER ChromePolicyUndo
    Remove the Chrome policy set by the chrome target and exit.
#>

[CmdletBinding()]
param(
    [ValidateSet('Audit', 'Clean')]
    [string]$Mode = 'Audit',

    [string[]]$Targets = @('pip', 'npm', 'nuget', 'temp', 'wintemp', 'claude', 'adobe'),

    [switch]$NuGetPackages,

    [ValidateRange(1, 8760)]
    [int]$TempAgeHours = 24,

    [switch]$ChromePolicyUndo
)

$ErrorActionPreference = 'Continue'
$clean = $Mode -eq 'Clean'
$local = $env:LOCALAPPDATA
$roaming = $env:APPDATA
$chromePolicyKey = 'HKCU:\Software\Policies\Google\Chrome'
$chromePolicyName = 'GenAILocalFoundationalModelSettings'
$adobeCaches = 'Media Cache Files', 'Media Cache', 'Peak Files'

function Format-Size([double]$bytes) {
    if ($bytes -ge 1GB) { return '{0:N1} GB' -f ($bytes / 1GB) }
    if ($bytes -ge 1MB) { return '{0:N0} MB' -f ($bytes / 1MB) }
    return '{0:N0} KB' -f ($bytes / 1KB)
}

# pwsh 7 walks a tree in .NET, skipping what it cannot read and not following links;
# PowerShell 5.1 has no such option and falls back to Get-ChildItem.
$script:walk = $null
if ([type]::GetType('System.IO.EnumerationOptions')) {
    $script:walk = [IO.EnumerationOptions]::new()
    $script:walk.RecurseSubdirectories = $true
    $script:walk.IgnoreInaccessible = $true
    $script:walk.AttributesToSkip = [IO.FileAttributes]::ReparsePoint
}

function Measure-Path([string]$path) {
    if ([IO.File]::Exists($path)) { return ([IO.FileInfo]::new($path)).Length }
    if (-not [IO.Directory]::Exists($path)) { return 0L }
    $sum = 0L
    if ($script:walk) {
        try { foreach ($f in [IO.DirectoryInfo]::new($path).EnumerateFiles('*', $script:walk)) { $sum += $f.Length } } catch {}
    } else {
        Get-ChildItem -LiteralPath $path -Recurse -File -Force -ErrorAction SilentlyContinue | ForEach-Object { $sum += $_.Length }
    }
    return $sum
}

# The last time anything in an entry was written: the entry itself, or the newest file or folder under it.
function Get-Newest($entry) {
    $newest = $entry.LastWriteTime
    if (-not $entry.PSIsContainer -or ($entry.Attributes -band [IO.FileAttributes]::ReparsePoint)) { return $newest }
    if ($script:walk) {
        try {
            foreach ($item in [IO.DirectoryInfo]::new($entry.FullName).EnumerateFileSystemInfos('*', $script:walk)) {
                if ($item.LastWriteTime -gt $newest) { $newest = $item.LastWriteTime }
            }
        } catch {}
    } else {
        foreach ($item in Get-ChildItem -LiteralPath $entry.FullName -Recurse -Force -ErrorAction SilentlyContinue) {
            if ($item.LastWriteTime -gt $newest) { $newest = $item.LastWriteTime }
        }
    }
    return $newest
}

# Deletes one entry: a folder with all it holds (a link is removed, not followed), or a file.
# Returns $false when it stays - something in it is in use.
function Remove-Entry($entry) {
    try {
        if ($entry.PSIsContainer -and -not ($entry.Attributes -band [IO.FileAttributes]::ReparsePoint)) {
            [IO.Directory]::Delete($entry.FullName, $true)
        } else {
            $entry.Attributes = 'Normal'
            $entry.Delete()
        }
        return $true
    } catch { return $false }
}

# Deletes the contents of a folder (the folder itself stays), one entry at a time
# so a locked file costs only itself. Returns the number of entries left behind.
function Clear-Folder([string]$path, [scriptblock]$Filter = { $true }) {
    if (-not (Test-Path -LiteralPath $path)) { return 0 }
    $left = 0
    foreach ($entry in Get-ChildItem -LiteralPath $path -Force -ErrorAction SilentlyContinue) {
        if (-not (& $Filter $entry)) { continue }
        if (-not (Remove-Entry $entry)) { $left++ }
    }
    return $left
}

function Test-Running([string[]]$names) {
    @(Get-Process -Name $names -ErrorAction SilentlyContinue).Count -gt 0
}

function Test-Administrator {
    ([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
}

# The media caches of Adobe: the usual place, then every place Premiere Pro was told to keep them.
# A place from the registry is cleared only through the cache folders in it (or when it is one of
# them by name): the folder chosen in the preferences may hold anything else besides.
function Get-AdobeCacheFolders {
    $found = New-Object System.Collections.Generic.List[object]
    foreach ($name in $adobeCaches) { $found.Add([pscustomobject]@{ Path = (Join-Path $roaming "Adobe\Common\$name"); Name = $name; Moved = $false }) }
    foreach ($key in @(Get-ChildItem -Path 'HKCU:\Software\Adobe' -ErrorAction SilentlyContinue | Where-Object { $_.PSChildName -like 'Common*' })) {
        foreach ($sub in 'Media Cache', 'MediaCache') {
            $props = Get-ItemProperty -LiteralPath (Join-Path $key.PSPath $sub) -ErrorAction SilentlyContinue
            if (-not $props) { continue }
            foreach ($value in @($props.FolderPath, $props.DatabasePath)) {
                if (-not $value) { continue }
                try { $base = [IO.Path]::GetFullPath([Environment]::ExpandEnvironmentVariables([string]$value)).TrimEnd('\') } catch { continue }
                $leaf = Split-Path -Path $base -Leaf
                if ($adobeCaches -contains $leaf) { $found.Add([pscustomobject]@{ Path = $base; Name = $leaf; Moved = $true }) }
                else { foreach ($name in $adobeCaches) { $found.Add([pscustomobject]@{ Path = (Join-Path $base $name); Name = $name; Moved = $true }) } }
            }
        }
    }
    $seen = @{}
    foreach ($folder in $found) {
        $keyOf = $folder.Path.TrimEnd('\').ToLowerInvariant()
        if ($seen.ContainsKey($keyOf)) { continue }
        $seen[$keyOf] = $true
        $folder
    }
}

if ($ChromePolicyUndo) {
    if (Get-ItemProperty -Path $chromePolicyKey -Name $chromePolicyName -ErrorAction SilentlyContinue) {
        Remove-ItemProperty -Path $chromePolicyKey -Name $chromePolicyName
        Write-Host "Chrome policy $chromePolicyName removed. Chrome may download its model again."
    } else {
        Write-Host "Chrome policy $chromePolicyName is not set."
    }
    exit 0
}

# "-File" hands a comma list over as one string: split it here, then check the names.
$Targets = @($Targets | ForEach-Object { $_ -split '[,;\s]+' } | Where-Object { $_ } | ForEach-Object { $_.ToLowerInvariant() })
$known = 'pip', 'npm', 'nuget', 'temp', 'wintemp', 'claude', 'adobe', 'chrome'
$unknown = @($Targets | Where-Object { $known -notcontains $_ })
if ($unknown.Count -gt 0) { Write-Error ("Unknown target(s): {0}. Known: {1}." -f ($unknown -join ', '), ($known -join ', ')); exit 2 }
$cutoff = (Get-Date).AddHours(-$TempAgeHours)

# Each entry: target, label, folder, filter for its entries, reason to skip (if any), and for a
# target that reaches deeper than the entries of its folder - the list of what goes.
$plan = New-Object System.Collections.Generic.List[object]
function Add-Plan($target, $label, $path, $filter = $null, $skip = '', $items = $null) {
    $plan.Add([pscustomobject]@{ Target = $target; Label = $label; Path = $path; Filter = $filter; Skip = $skip; Items = $items })
}

if ($Targets -contains 'pip') { Add-Plan 'pip' 'pip cache' (Join-Path $local 'pip\cache') }
if ($Targets -contains 'npm') { Add-Plan 'npm' 'npm cache' (Join-Path $local 'npm-cache\_cacache') }
if ($Targets -contains 'nuget') {
    Add-Plan 'nuget' 'NuGet http cache' (Join-Path $local 'NuGet\v3-cache')
    Add-Plan 'nuget' 'NuGet http cache (new)' (Join-Path $local 'NuGet\http-cache')
    Add-Plan 'nuget' 'NuGet plugins cache' (Join-Path $local 'NuGet\plugins-cache')
    Add-Plan 'nuget' 'NuGet scratch' (Join-Path $env:TEMP 'NuGetScratch')
    if ($NuGetPackages) { Add-Plan 'nuget' 'NuGet packages' (Join-Path $env:USERPROFILE '.nuget\packages') }
}
$olderFilter = { param($e) $e.LastWriteTime -lt $cutoff }
if ($Targets -contains 'temp') {
    Add-Plan 'temp' "Temp older than $TempAgeHours h" $env:TEMP $olderFilter
}
if ($Targets -contains 'wintemp') {
    $rights = if (Test-Administrator) { '' } else { 'needs administrator rights' }
    Add-Plan 'wintemp' "Windows Temp older than $TempAgeHours h" (Join-Path $env:SystemRoot 'Temp') $olderFilter $rights
}
if ($Targets -contains 'claude') {
    $claudeRoot = Join-Path $env:TEMP 'claude'
    # A folder of a project holds a folder per session. A session nothing was written in for the
    # age goes; a project all of whose sessions went goes with them.
    $claudeIdle = {
        foreach ($project in @(Get-ChildItem -LiteralPath $claudeRoot -Force -ErrorAction SilentlyContinue)) {
            if (-not $project.PSIsContainer -or ($project.Attributes -band [IO.FileAttributes]::ReparsePoint)) {
                if ($project.LastWriteTime -lt $cutoff) { $project }
                continue
            }
            $sessions = @(Get-ChildItem -LiteralPath $project.FullName -Force -ErrorAction SilentlyContinue)
            $idle = @($sessions | Where-Object { (Get-Newest $_) -lt $cutoff })
            if ($idle.Count -eq $sessions.Count -and $project.LastWriteTime -lt $cutoff) { $project } else { $idle }
        }
    }
    Add-Plan 'claude' "Claude Code sessions idle $TempAgeHours h" $claudeRoot $null '' $claudeIdle
}
if ($Targets -contains 'adobe') {
    $busy = if (Test-Running @('Adobe Premiere Pro', 'AfterFX', 'Adobe Media Encoder', 'Adobe Audition')) { 'an Adobe video/audio app is running' } else { '' }
    foreach ($folder in Get-AdobeCacheFolders) {
        $label = if ($folder.Moved) { "Adobe $($folder.Name) ($(Split-Path -Path $folder.Path -Parent))" } else { "Adobe $($folder.Name)" }
        Add-Plan 'adobe' $label $folder.Path $null $busy
    }
}
if ($Targets -contains 'chrome') {
    $busy = if (Test-Running @('chrome')) { 'Chrome is running - close it first' } else { '' }
    Add-Plan 'chrome' 'Chrome on-device AI model' (Join-Path $local 'Google\Chrome\User Data\OptGuideOnDeviceModel') $null $busy
}

$drive = [IO.DriveInfo]::new([IO.Path]::GetPathRoot($env:LOCALAPPDATA))
$freeBefore = $drive.AvailableFreeSpace

Write-Host ''
Write-Host ("Cache cleaner - mode {0}, drive {1} free {2}" -f $Mode, $drive.Name, (Format-Size $freeBefore))
Write-Host ('-' * 72)

$total = 0L
$failed = 0
foreach ($p in $plan) {
    if (-not (Test-Path -LiteralPath $p.Path)) {
        Write-Host ("{0,-34} {1,10}  not present" -f $p.Label, '-')
        continue
    }
    if ($p.Skip -and $p.Target -eq 'wintemp') {
        # Without the rights the folder cannot even be read: no size to tell.
        Write-Host ("{0,-34} {1,10}  skipped: {2}" -f $p.Label, '-', $p.Skip)
        continue
    }
    $entries = $null
    if ($p.Items) {
        $entries = @(& $p.Items)
        $size = 0L
        foreach ($e in $entries) { $size += Measure-Path $e.FullName }
    } elseif ($p.Filter) {
        $size = 0L
        foreach ($e in Get-ChildItem -LiteralPath $p.Path -Force -ErrorAction SilentlyContinue) {
            if (& $p.Filter $e) { $size += Measure-Path $e.FullName }
        }
    } else {
        $size = Measure-Path $p.Path
    }
    $total += $size
    $note = ''
    if ($p.Skip) {
        $note = "skipped: $($p.Skip)"
    } elseif ($clean) {
        if ($p.Items) {
            $left = 0
            foreach ($e in $entries) { if (-not (Remove-Entry $e)) { $left++ } }
        } else {
            $left = if ($p.Filter) { Clear-Folder $p.Path $p.Filter } else { Clear-Folder $p.Path }
        }
        $failed += $left
        $note = if ($left -gt 0) { "cleared, $left in use and left" } else { 'cleared' }
    } elseif ($p.Items) {
        $note = "$($entries.Count) to go"
    }
    Write-Host ("{0,-34} {1,10}  {2}" -f $p.Label, (Format-Size $size), $note)
}

if ($clean -and $Targets -contains 'chrome') {
    if (-not (Test-Path $chromePolicyKey)) { New-Item -Path $chromePolicyKey -Force | Out-Null }
    New-ItemProperty -Path $chromePolicyKey -Name $chromePolicyName -Value 1 -PropertyType DWord -Force | Out-Null
    Write-Host "Chrome policy $chromePolicyName = 1 set for this user: the model stays away (undo: -ChromePolicyUndo)."
}

Write-Host ('-' * 72)
if ($clean) {
    $drive = [IO.DriveInfo]::new($drive.Name)
    Write-Host ("Freed {0}. Drive {1} free {2}." -f (Format-Size ($drive.AvailableFreeSpace - $freeBefore)), $drive.Name, (Format-Size $drive.AvailableFreeSpace))
} else {
    Write-Host ("Can be freed: {0}. Nothing changed (run with -Mode Clean)." -f (Format-Size $total))
}
exit ([int][bool]($failed -gt 0))
