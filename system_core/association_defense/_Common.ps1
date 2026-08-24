<#
.SYNOPSIS
    Audion DevOps Tools - Shared helpers for the association-defense bricks.
.DESCRIPTION
    Common functions used by Edge / AppX / Defender bricks.
    English-only output. No external dependencies. Self-contained.
#>

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

function Test-IsAdmin {
    $id = [System.Security.Principal.WindowsIdentity]::GetCurrent()
    $principal = New-Object System.Security.Principal.WindowsPrincipal($id)
    return $principal.IsInRole([System.Security.Principal.WindowsBuiltInRole]::Administrator)
}

function Assert-Admin {
    if (-not (Test-IsAdmin)) {
        Write-Host "ERROR: This brick must run elevated (Run as Administrator)." -ForegroundColor Red
        exit 2
    }
}

function Write-Line {
    param([string]$Text, [string]$Color = 'Gray')
    Write-Host $Text -ForegroundColor $Color
}

function Get-StateColor {
    param([bool]$Active)
    if ($Active) { return 'Green' } else { return 'Yellow' }
}

# Reads a registry DWORD, returns $null if path/value is absent (no throw).
function Get-RegDword {
    param([string]$Path, [string]$Name)
    try {
        if (-not (Test-Path $Path)) { return $null }
        $item = Get-ItemProperty -Path $Path -Name $Name -ErrorAction Stop
        return [int]$item.$Name
    } catch {
        return $null
    }
}

# Writes a registry DWORD, creating the key path if needed.
function Set-RegDword {
    param([string]$Path, [string]$Name, [int]$Value)
    if (-not (Test-Path $Path)) {
        New-Item -Path $Path -Force | Out-Null
    }
    New-ItemProperty -Path $Path -Name $Name -Value $Value -PropertyType DWord -Force | Out-Null
}

# Removes a registry value if present (no throw if absent).
function Remove-RegValue {
    param([string]$Path, [string]$Name)
    if (Test-Path $Path) {
        Remove-ItemProperty -Path $Path -Name $Name -ErrorAction SilentlyContinue
    }
}

# --- Transcript logging (Enable/Disable actions only) -----------------------
# Logs are written next to the bricks in .\logs\, with a fallback to known
# drives if that location is not writable. Files are named
# <timestamp>.<machine>.<brick>-<verb>.log and rotated by age.

$script:BrickLogRetentionDays = 30
$script:BrickLogActive = $false

# Resolve a writable log directory: script-local .\logs first, then env-based fallbacks.
function Get-BrickLogDir {
    param([string]$ScriptRoot)
    $candidates = New-Object System.Collections.Generic.List[string]
    $candidates.Add((Join-Path $ScriptRoot 'logs'))
    if ($env:AUDION_ASSOCIATION_DEFENSE_LOG_DIR) {
        $candidates.Add($env:AUDION_ASSOCIATION_DEFENSE_LOG_DIR)
    }
    if ($env:ProgramData) {
        $candidates.Add((Join-Path $env:ProgramData 'Audion\AssociationDefense\Logs'))
    }
    if ($env:LOCALAPPDATA) {
        $candidates.Add((Join-Path $env:LOCALAPPDATA 'Audion\AssociationDefense\Logs'))
    }
    foreach ($dir in @($candidates)) {
        if (-not $dir) { continue }
        try {
            if (-not (Test-Path $dir)) {
                New-Item -ItemType Directory -Path $dir -Force -ErrorAction Stop | Out-Null
            }
            # Confirm we can actually write here.
            $probe = Join-Path $dir ('.write_probe_' + [guid]::NewGuid().ToString('N'))
            Set-Content -Path $probe -Value 'ok' -ErrorAction Stop
            Remove-Item $probe -ErrorAction SilentlyContinue
            return $dir
        } catch {
            continue
        }
    }
    return $null
}

# Delete log files older than the retention window (no throw on failure).
function Invoke-BrickLogRotation {
    param([string]$LogDir)
    try {
        $cutoff = (Get-Date).AddDays(-1 * $script:BrickLogRetentionDays)
        Get-ChildItem -Path $LogDir -Filter '*.log' -File -ErrorAction SilentlyContinue |
            Where-Object { $_.LastWriteTime -lt $cutoff } |
            Remove-Item -Force -ErrorAction SilentlyContinue
    } catch {
        # Rotation is best-effort; never block the action because of it.
    }
}

# Start a transcript for a mutating action. Verb 'Status' is intentionally
# skipped (read-only, noisy). Returns the log path, or $null if logging could
# not start - in which case the action proceeds unlogged.
function Start-BrickLog {
    param(
        [Parameter(Mandatory)][string]$BrickName,
        [Parameter(Mandatory)][string]$Verb,
        [Parameter(Mandatory)][string]$ScriptRoot
    )
    if ($Verb -eq 'Status') { return $null }

    $logDir = Get-BrickLogDir -ScriptRoot $ScriptRoot
    if (-not $logDir) {
        Write-Host "WARN: no writable log directory found; proceeding unlogged." -ForegroundColor DarkYellow
        return $null
    }

    Invoke-BrickLogRotation -LogDir $logDir

    $stamp = Get-Date -Format 'yyyy-MM-dd_HHmmss_fff'
    $machine = ($env:COMPUTERNAME -replace '[^\w\-]', '_')
    $safeBrick = ($BrickName -replace '[^\w\-]', '_')
    $file = "{0}.{1}.{2}-{3}.log" -f $stamp, $machine, $safeBrick, $Verb
    $path = Join-Path $logDir $file

    try {
        Start-Transcript -Path $path -ErrorAction Stop | Out-Null
        $script:BrickLogActive = $true
        Write-Host "Log: $path" -ForegroundColor DarkGray
        return $path
    } catch {
        Write-Host "WARN: could not start transcript: $($_.Exception.Message)" -ForegroundColor DarkYellow
        return $null
    }
}

# Stop the transcript if one is active (safe to call unconditionally).
function Stop-BrickLog {
    if ($script:BrickLogActive) {
        try { Stop-Transcript | Out-Null } catch { }
        $script:BrickLogActive = $false
    }
}

# --- Dry-run helper ---------------------------------------------------------
# Prints a "would do" line in dry-run mode; returns $true if the caller should
# SKIP the real action. Keeps dry-run handling uniform across bricks.
function Test-DryRun {
    param([bool]$DryRun, [string]$Action)
    if ($DryRun) {
        Write-Host "  [dry-run] would: $Action" -ForegroundColor DarkCyan
        return $true
    }
    return $false
}

# --- Association snapshot helpers -------------------------------------------
# One place for the snapshot format so the monolithic and layered bricks read,
# parse, and write it identically. The format is one "identifier, ProgID" pair
# per line; comment lines start with '#'. Reading comes straight from the
# registry - no third-party helper is involved anywhere in this project.

function Get-AssociationDefenseProjectRoot {
    param([Parameter(Mandatory)][string]$ScriptRoot)
    $resolved = (Resolve-Path -LiteralPath $ScriptRoot).Path
    $parent = Split-Path -Parent $resolved
    if ((Split-Path -Leaf $parent) -ieq 'system_core') {
        return (Split-Path -Parent $parent)
    }
    return $resolved
}

function Normalize-AssociationIdentifier {
    param([Parameter(Mandatory)][string]$Identifier)
    return $Identifier.Trim().ToLowerInvariant()
}

function Get-AssociationEntriesFromLines {
    param([object[]]$Lines)
    $entries = @()
    foreach ($line in @($Lines)) {
        $text = ([string]$line).Trim()
        if (-not $text) { continue }
        if ($text -match '^\s*#') { continue }
        if ($text -notmatch ',') { continue }
        $parts = $text -split ',', 2
        if ($parts.Count -ne 2) { continue }
        $identifier = $parts[0].Trim()
        $progId = $parts[1].Trim()
        if (-not $identifier -or -not $progId) { continue }
        $entries += ("{0}, {1}" -f $identifier, $progId)
    }
    return @($entries)
}

function Read-AssociationEntryFile {
    param([Parameter(Mandatory)][string]$Path)
    if (-not (Test-Path -LiteralPath $Path)) {
        Write-Line "ERROR: snapshot file not found: $Path" 'Red'
        exit 1
    }
    return @(Get-AssociationEntriesFromLines -Lines (Get-Content -LiteralPath $Path -ErrorAction Stop))
}

# Read the live per-user association map straight from the registry: file
# extensions from FileExts, protocols from UrlAssociations, both sorted so the
# dump is reproducible. Reading UserChoice is unrestricted by design - only
# writing it is hash-protected, and nothing in this project writes there.
function Get-AssociationDump {
    $roots = @(
        'HKCU:\Software\Microsoft\Windows\CurrentVersion\Explorer\FileExts'
        'HKCU:\Software\Microsoft\Windows\Shell\Associations\UrlAssociations'
    )
    $entries = @()
    foreach ($root in $roots) {
        if (-not (Test-Path -LiteralPath $root)) { continue }
        $names = @(
            Get-ChildItem -LiteralPath $root -ErrorAction SilentlyContinue |
                Select-Object -ExpandProperty PSChildName |
                Sort-Object
        )
        foreach ($name in $names) {
            $identifier = ([string]$name).Trim()
            if (-not $identifier) { continue }
            $choicePath = Join-Path -Path $root -ChildPath ("{0}\UserChoice" -f $identifier)
            $progId = $null
            try {
                $progId = (Get-ItemProperty -LiteralPath $choicePath -Name 'ProgId' -ErrorAction Stop).ProgId
            } catch {
                # No UserChoice under this identifier: Windows falls back to the
                # machine default, and there is nothing to snapshot.
                continue
            }
            $value = ([string]$progId).Trim()
            if ($value) {
                $entries += ("{0}, {1}" -f $identifier, $value)
            }
        }
    }
    return @($entries)
}

function Convert-AssociationEntriesToMap {
    param([object[]]$Entries)
    $map = @{}
    foreach ($line in @($Entries)) {
        $parts = ([string]$line) -split ',', 2
        if ($parts.Count -ne 2) { continue }
        $key = Normalize-AssociationIdentifier -Identifier $parts[0]
        $value = $parts[1].Trim()
        if ($key -and $value) {
            $map[$key] = $value
        }
    }
    return $map
}

function Write-AssociationEntryFile {
    param(
        [Parameter(Mandatory)][string]$Path,
        [Parameter(Mandatory)][string[]]$Lines
    )
    $dir = Split-Path -Parent $Path
    if ($dir -and -not (Test-Path -LiteralPath $dir)) {
        New-Item -ItemType Directory -Path $dir -Force | Out-Null
    }
    [System.IO.File]::WriteAllLines($Path, $Lines, [System.Text.UTF8Encoding]::new($false))
}

function Test-AssociationProgIdExists {
    param([Parameter(Mandatory)][string]$ProgId)
    $text = $ProgId.Trim()
    if (-not $text) { return $false }
    return (Test-Path -LiteralPath ("Registry::HKEY_CLASSES_ROOT\{0}" -f $text))
}

function Get-AssociationMissingProgIds {
    param([object[]]$Entries)
    $missing = @()
    foreach ($line in @($Entries)) {
        $parts = ([string]$line) -split ',', 2
        if ($parts.Count -ne 2) { continue }
        $identifier = $parts[0].Trim()
        $progId = $parts[1].Trim()
        if ($progId -and -not (Test-AssociationProgIdExists -ProgId $progId)) {
            $missing += ("{0} -> {1}" -f $identifier, $progId)
        }
    }
    return @($missing)
}

# --- Toast notification -----------------------------------------------------
# Best-effort Windows toast. Falls back silently to console if the toast APIs
# are unavailable (e.g. Server Core, no user session). Never throws.
function Show-Toast {
    param(
        [Parameter(Mandatory)][string]$Title,
        [Parameter(Mandatory)][string]$Message
    )
    try {
        [void][Windows.UI.Notifications.ToastNotificationManager, Windows.UI.Notifications, ContentType = WindowsRuntime]
        $template = [Windows.UI.Notifications.ToastNotificationManager]::GetTemplateContent(
            [Windows.UI.Notifications.ToastTemplateType]::ToastText02)
        $texts = $template.GetElementsByTagName('text')
        $texts.Item(0).AppendChild($template.CreateTextNode($Title)) | Out-Null
        $texts.Item(1).AppendChild($template.CreateTextNode($Message)) | Out-Null
        $toast = [Windows.UI.Notifications.ToastNotification]::new($template)
        $appId = '{1AC14E77-02E7-4E5D-B744-2EB1AE5198B7}\WindowsPowerShell\v1.0\powershell.exe'
        [Windows.UI.Notifications.ToastNotificationManager]::CreateToastNotifier($appId).Show($toast)
        return $true
    } catch {
        # Fallback: at least surface it on the console.
        Write-Host "[toast unavailable] $Title - $Message" -ForegroundColor Yellow
        return $false
    }
}
