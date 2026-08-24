<#
.SYNOPSIS
    Universal Python removal for Windows.

.DESCRIPTION
    Removes every common Python footprint: vanilla python.org installer,
    Microsoft Store AppX Python, Python Launcher (py.exe), pipx, uv, conda
    (Miniconda / Anaconda system-wide AND per-user), pip caches and config,
    related env vars, Start Menu shortcuts, PATH entries, and uninstall
    registry entries.

    Does NOT touch:
      - per-project virtual envs (.venv, venv folders) under user projects
      - pwsh / PowerShell (they are not Python)
      - the Microsoft Store app itself

    Idempotent: re-running on a clean machine reports 0 artifacts.

.PARAMETER Mode
    Audit   - read-only scan, list everything that would be removed
    DryRun  - simulate the run, no changes
    Nuke    - actually remove everything

.PARAMETER KeepWinget
    Skip the winget uninstall pass (just delete files / registry).

.PARAMETER KeepProjectVenvs
    Skip scanning under user home for stray .venv / venv folders.
    Default is to NOT touch project venvs - this switch is for forward
    compatibility if we later add such scanning.

.PARAMETER PathPattern
    Regex matched against PATH entries to decide if an entry is a Python
    one and should be stripped. Default catches python.org installer,
    py.exe launcher, conda, pipx, uv. Anchored to avoid false positives
    on user folders that happen to contain "Python" mid-path.

.PARAMETER LogPath
    Transcript path. Default: script-dir\Logs\nuke-<timestamp>.log
#>

[CmdletBinding()]
param(
    [ValidateSet('Audit','DryRun','Nuke')]
    [string]$Mode = 'Audit',

    [switch]$KeepWinget,
    [switch]$KeepProjectVenvs,

    # Deprecated compatibility switch. Microsoft App Execution Alias
    # stubs under WindowsApps are owned by the OS/user alias settings and
    # are always kept, even in Nuke mode.
    [switch]$RemoveStoreAliases,

    [string]$PathPattern = '(?i)(\\Programs\\Python(\\|$)|\\Python3?\d{0,2}(\\Scripts)?(\\|$)|\\py(thon)?launcher(\\|$)|\\Miniconda3?(\\|$)|\\Anaconda3?(\\|$)|\\pipx(\\|$)|\\\.pipx(\\|$)|\\uv(\\|$))',

    [string]$LogPath = (Join-Path $PSScriptRoot ("Logs\nuke-{0}.log" -f (Get-Date -Format 'yyyyMMdd-HHmmss')))
)

$ErrorActionPreference = 'Continue'
$script:Remaining = 0
$script:WriteMode = ($Mode -eq 'Nuke')
$script:DryRun    = ($Mode -eq 'DryRun')
$script:AuditOnly = ($Mode -eq 'Audit')
# Any non-write mode (Audit + DryRun). Replaces the older pattern of
# bumping the counter only in Audit, which under-counted DryRun.
$script:Speculative = $script:AuditOnly -or $script:DryRun
# Set to true when a check could not produce a confident result (e.g.
# Get-AppxProvisionedPackage threw Access Denied). Final summary uses
# this to avoid a misleading "Clean: 0".
$script:AuditUnknown = $false

# --- Log dir + transcript ---------------------------------------------------
try {
    $logDir = Split-Path -Parent $LogPath
    if ($logDir -and -not (Test-Path -LiteralPath $logDir)) {
        New-Item -ItemType Directory -Path $logDir -Force | Out-Null
    }
} catch {}
try { Start-Transcript -Path $LogPath -Force | Out-Null } catch {}

function Write-Section($title) {
    Write-Host ""
    Write-Host ("=" * 70) -ForegroundColor Cyan
    Write-Host (" $title") -ForegroundColor Cyan
    Write-Host ("=" * 70) -ForegroundColor Cyan
}
function Write-Action($msg) {
    $tag = switch ($Mode) { 'Audit' {'[FOUND]'} 'DryRun' {'[WOULDDO]'} 'Nuke' {'[ACT]'} }
    Write-Host "$tag $msg" -ForegroundColor Yellow
}
function Write-Ok($msg) { Write-Host "[OK]    $msg" -ForegroundColor Green }
function Write-Skip($msg) { Write-Host "[SKIP]  $msg" -ForegroundColor DarkGray }
function Write-Err($msg) { Write-Host "[ERR]   $msg" -ForegroundColor Red }
function Bump-Remaining { $script:Remaining++ }
$script:ToolkitRoot = try { (Resolve-Path -LiteralPath $PSScriptRoot -ErrorAction Stop).ProviderPath.TrimEnd('\') } catch { $PSScriptRoot.TrimEnd('\') }
function Test-IsOwnToolkitFolder {
    param([string]$Path)
    if (-not $Path) { return $false }
    $fullPath = try { (Resolve-Path -LiteralPath $Path -ErrorAction Stop).ProviderPath.TrimEnd('\') } catch { $Path.TrimEnd('\') }
    $toolkitPrefix = $script:ToolkitRoot + '\'
    return ($fullPath -ieq $script:ToolkitRoot) -or $fullPath.StartsWith($toolkitPrefix, [System.StringComparison]::OrdinalIgnoreCase)
}

# --- Privilege ---------------------------------------------------------------
$id = [System.Security.Principal.WindowsIdentity]::GetCurrent()
$pr = New-Object System.Security.Principal.WindowsPrincipal($id)
$IsAdmin = $pr.IsInRole([System.Security.Principal.WindowsBuiltinRole]::Administrator)
if ($script:WriteMode -and -not $IsAdmin) {
    Write-Err "Nuke mode requires administrator rights. Re-launch via Nuke.cmd."
    try { Stop-Transcript | Out-Null } catch {}
    exit 255
}
if (-not $IsAdmin) {
    Write-Host "[INFO]  Running non-elevated. Machine PATH and HKLM hidden." -ForegroundColor DarkYellow
}

Write-Section "Python Nuke - Mode: $Mode"
Write-Host "User : $($id.Name)"
Write-Host "Host : $env:COMPUTERNAME"
Write-Host "Log  : $LogPath"

# --- Helpers ----------------------------------------------------------------
function Remove-FolderHard {
    param([string]$Path)
    if (-not (Test-Path -LiteralPath $Path)) { return $true }
    if ($script:AuditOnly -or $script:DryRun) { return $true }
    try {
        Remove-Item -LiteralPath $Path -Recurse -Force -ErrorAction Stop
        Write-Ok "  Deleted: $Path"
        return $true
    } catch {
        Write-Host "  Fast delete failed ($($_.Exception.Message.Trim())). Escalating..." -ForegroundColor DarkGray
    }
    try {
        & takeown /F $Path /R /D Y 2>&1 | Out-Null
        & icacls $Path /grant "*S-1-5-32-544:(F)" /T /C /Q 2>&1 | Out-Null
        & cmd /c rd /s /q "$Path" 2>&1 | Out-Null
    } catch {}
    if (Test-Path -LiteralPath $Path) {
        Write-Err "  Could not delete '$Path'."
        return $false
    }
    Write-Ok "  Deleted (escalated): $Path"
    return $true
}

function Remove-FileHard {
    param([string]$Path)
    if (-not (Test-Path -LiteralPath $Path)) { return $true }
    if ($script:AuditOnly -or $script:DryRun) { return $true }
    try {
        Remove-Item -LiteralPath $Path -Force -ErrorAction Stop
        Write-Ok "  Deleted: $Path"
        return $true
    } catch {
        try {
            & takeown /F $Path 2>&1 | Out-Null
            & icacls $Path /grant "*S-1-5-32-544:(F)" /C /Q 2>&1 | Out-Null
            Remove-Item -LiteralPath $Path -Force -ErrorAction Stop
            Write-Ok "  Deleted (escalated): $Path"
            return $true
        } catch {
            Write-Err "  Could not delete '$Path': $_"
            return $false
        }
    }
}

function Remove-RegKeyTreeSafe {
    param([string]$PSPath)
    if (-not (Test-Path $PSPath)) { return $true }
    if ($script:AuditOnly -or $script:DryRun) { return $true }
    try {
        Remove-Item -Path $PSPath -Recurse -Force -ErrorAction Stop
        Write-Ok "  Deleted: $PSPath"
        return $true
    } catch {
        Write-Err "  Remove $PSPath -> $_"
        return $false
    }
}

# ============================================================================
# PHASE 1 - Stop processes
# ============================================================================
Write-Section "1. Stopping Python-related processes"
$procNames = @('python','pythonw','py','pyw','pip','pip3','pipx','uv','conda','ipython','jupyter','jupyter-notebook','jupyter-lab')
$found = @()
foreach ($n in $procNames) {
    $ps = Get-Process -Name $n -ErrorAction SilentlyContinue
    if ($ps) { $found += $ps }
}
if ($found) {
    foreach ($p in $found) {
        Write-Action "Process PID=$($p.Id) Name=$($p.ProcessName) Path=$($p.Path)"
        if ($script:WriteMode) {
            try { Stop-Process -Id $p.Id -Force -ErrorAction Stop; Write-Ok "Killed PID $($p.Id)" }
            catch { Write-Err "Kill PID $($p.Id) -> $_"; Bump-Remaining }
        } elseif ($script:Speculative) { Bump-Remaining }
    }
} else { Write-Skip "No Python-related processes." }

# ============================================================================
# PHASE 2 - winget uninstall
# ============================================================================
Write-Section "2. winget uninstall (dynamic)"
if ($KeepWinget) {
    Write-Skip "-KeepWinget set."
} else {
    $winget = Get-Command winget.exe -ErrorAction SilentlyContinue
    if (-not $winget) {
        Write-Skip "winget not in PATH."
    } else {
        # Dynamic: list any installed package whose Id starts with "Python." or matches Python Launcher
        $rawList = $null
        try { $rawList = & winget list --disable-interactivity 2>$null } catch {}
        $hits = @()
        if ($rawList) {
            $hits = $rawList | Where-Object { $_ -match '^\s*(Python(\.|\s+Launcher)|Anaconda|Miniconda|Astral\.uv|Astral\.Ruff)' }
        }
        if ($hits) {
            foreach ($line in $hits) {
                # Parse the Id column. winget list output: Name   Id   Version   Source
                # We can't safely parse fixed-width; use winget show / search instead.
                Write-Action "winget candidate: $($line.Trim())"
            }
        } else {
            Write-Skip "No winget-installed Python/conda/uv candidates."
        }

        # Fall back to known IDs (covers most cases including 3.8..3.14)
        $ids = @(
            'Python.Python.3.8','Python.Python.3.9','Python.Python.3.10',
            'Python.Python.3.11','Python.Python.3.12','Python.Python.3.13','Python.Python.3.14',
            'Python.Launcher',
            'Anaconda.Anaconda3','Anaconda.Miniconda3',
            'Astral.uv'
        )
        foreach ($id in $ids) {
            if ($script:WriteMode) {
                Write-Action "winget uninstall --id $id"
                try {
                    $out = & winget uninstall --id $id -e --silent --disable-interactivity 2>&1
                    # winget returns 0x8a15002b = not installed; we don't care
                    if ($LASTEXITCODE -eq 0) { Write-Ok "  Uninstalled $id" }
                    else { Write-Skip "  $id not installed or no-op (code 0x$([Convert]::ToString($LASTEXITCODE,16)))" }
                } catch { Write-Err "  winget $id -> $_" }
            }
            # Note: in Audit/DryRun we deliberately do NOT enumerate hard-coded
            # IDs. They are blind-attempt fallbacks for Nuke mode only and
            # would create false-positive "found" entries in the audit.
        }
    }
}

# ============================================================================
# PHASE 3 - Microsoft Store AppX Python
# ============================================================================
Write-Section "3. Microsoft Store AppX Python"
$apx = @()
try {
    if ($IsAdmin) {
        $apx = Get-AppxPackage -AllUsers -ErrorAction SilentlyContinue | Where-Object {
            $_.Name -match 'Python' -or $_.PublisherDisplayName -match 'Python Software Foundation'
        }
    }
    if (-not $apx) {
        $apx = Get-AppxPackage -ErrorAction SilentlyContinue | Where-Object {
            $_.Name -match 'Python' -or $_.PublisherDisplayName -match 'Python Software Foundation'
        }
    }
} catch {}
if ($apx) {
    foreach ($p in $apx) {
        Write-Action "Appx $($p.PackageFullName)"
        if ($script:WriteMode) {
            try { Remove-AppxPackage -Package $p.PackageFullName -AllUsers -ErrorAction Stop; Write-Ok "Removed (AllUsers)" }
            catch {
                try { Remove-AppxPackage -Package $p.PackageFullName -ErrorAction Stop; Write-Ok "Removed (current user)" }
                catch { Write-Err "Remove-AppxPackage -> $_"; Bump-Remaining }
            }
        } elseif ($script:Speculative) { Bump-Remaining }
    }
} else { Write-Skip "No AppX Python packages." }

# Provisioned image-level Python
if ($IsAdmin) {
    try {
        $prov = Get-AppxProvisionedPackage -Online -ErrorAction Stop | Where-Object { $_.DisplayName -match 'Python' }
        foreach ($pp in $prov) {
            Write-Action "Provisioned $($pp.PackageName)"
            if ($script:WriteMode) {
                try { Remove-AppxProvisionedPackage -Online -PackageName $pp.PackageName -ErrorAction Stop | Out-Null; Write-Ok "Removed provisioned" }
                catch { Write-Err "Remove-AppxProvisionedPackage -> $_"; Bump-Remaining }
            } elseif ($script:Speculative) { Bump-Remaining }
        }
    } catch {
        Write-Skip "Get-AppxProvisionedPackage failed: $($_.Exception.Message.Trim())"
        # Could not enumerate provisioned packages -> final result is
        # not authoritative.
        $script:AuditUnknown = $true
    }
}

# AppExecutionAlias stubs (python.exe / python3.exe / py.exe under WindowsApps)
# These are OS/user alias settings, not Python-install footprint. Deleting
# them while the Settings toggle stays enabled creates a broken half-state
# that breaks Python CLI resolution even after a fresh install. Always keep.
$aliasDir = Join-Path $env:LOCALAPPDATA 'Microsoft\WindowsApps'
if (Test-Path $aliasDir) {
    if ($RemoveStoreAliases) {
        Write-Skip "-RemoveStoreAliases is deprecated; WindowsApps alias stubs are always kept."
    }
    $stubs = Get-ChildItem $aliasDir -Force -ErrorAction SilentlyContinue |
        Where-Object { $_.Name -match '^(python(\d(\.\d+)?)?|py|idle)\.exe$' -and $_.Length -eq 0 }
    foreach ($s in $stubs) {
        Write-Host "[KEEP]  $($s.FullName) (system AppExecutionAlias)" -ForegroundColor DarkCyan
    }
}

# ============================================================================
# PHASE 4 - Leftover folders (user + machine + ProgramData + C:\)
# ============================================================================
Write-Section "4. Leftover folders"
$folders = @(
    "$env:LOCALAPPDATA\Programs\Python",
    "$env:APPDATA\Python",
    "$env:LOCALAPPDATA\pip",
    "$env:APPDATA\pip",
    "$env:LOCALAPPDATA\pypoetry",
    "$env:APPDATA\pypoetry",
    "$env:LOCALAPPDATA\pdm",
    "$env:LOCALAPPDATA\virtualenv",
    "$env:APPDATA\virtualenv",
    "$env:LOCALAPPDATA\pipx",
    "$env:USERPROFILE\.pipx",
    "$env:LOCALAPPDATA\uv",
    "$env:APPDATA\uv",
    "$env:USERPROFILE\.cache\uv",
    "$env:USERPROFILE\.conda",
    "$env:USERPROFILE\.condarc",
    "$env:USERPROFILE\.condarc.bak",
    "$env:USERPROFILE\Miniconda3",
    "$env:USERPROFILE\Anaconda3",
    "$env:USERPROFILE\miniforge3",
    "$env:USERPROFILE\mambaforge",
    "$env:USERPROFILE\.ipython",
    "$env:USERPROFILE\.jupyter",
    'C:\ProgramData\Miniconda3',
    'C:\ProgramData\Anaconda3',
    'C:\ProgramData\miniforge3',
    'C:\ProgramData\mambaforge',
    'C:\Miniconda3',
    'C:\Anaconda3',
    'C:\miniforge3',
    'C:\mambaforge'
)
# Wildcarded top-level (Python27, Python311, etc.)
$wildFolders = @(
    'C:\Python*',
    "$env:ProgramFiles\Python*",
    "${env:ProgramFiles(x86)}\Python*"
)
$allFolders = @()
foreach ($f in $folders) { if (Test-Path -LiteralPath $f) { $allFolders += $f } }
foreach ($pat in $wildFolders) {
    Get-Item -Path $pat -ErrorAction SilentlyContinue | ForEach-Object {
        # Skip our own toolkit folder if user named a project "Python..."
        if (-not (Test-IsOwnToolkitFolder $_.FullName)) { $allFolders += $_.FullName }
    }
}
if ($allFolders) {
    foreach ($f in $allFolders) {
        Write-Action "Folder $f"
        if ($script:WriteMode) {
            if (-not (Remove-FolderHard $f)) { Bump-Remaining }
        } elseif ($script:Speculative) { Bump-Remaining }
    }
} else { Write-Skip "No leftover folders." }

# ============================================================================
# PHASE 5 - py.exe launcher (PEP 397) loose files
# ============================================================================
Write-Section "5. py.exe launcher (PEP 397)"
foreach ($f in @('C:\Windows\py.exe','C:\Windows\pyw.exe','C:\Windows\py-launcher.msi.bak')) {
    if (Test-Path -LiteralPath $f) {
        Write-Action "File $f"
        if ($script:WriteMode) {
            if (-not (Remove-FileHard $f)) { Bump-Remaining }
        } elseif ($script:Speculative) { Bump-Remaining }
    }
}

# ============================================================================
# PHASE 6 - PATH cleanup (User + Machine)
# ============================================================================
Write-Section "6. PATH cleanup"
# PATH is stored as REG_EXPAND_SZ, so entries like %SystemRoot%\system32 are kept
# as tokens. [Environment]::GetEnvironmentVariable hands back the expanded text,
# and writing that back bakes C:\Windows in permanently — the tokens are gone for
# good, on a variable nothing else will ever repair.
#
# This reads the untouched text instead. It returns nothing when the value holds
# no tokens, which is the common case, and then the old path through the .NET API
# is used exactly as before.
function Get-RawPathValue {
    param([string]$Scope)
    $key = if ($Scope -eq 'Machine') {
        'HKLM:\SYSTEM\CurrentControlSet\Control\Session Manager\Environment'
    } else {
        'HKCU:\Environment'
    }
    try {
        $item = Get-Item -LiteralPath $key -ErrorAction Stop
        if ($item.GetValueKind('Path') -ne 'ExpandString') { return $null }
        $raw = $item.GetValue('Path', $null, 'DoNotExpandEnvironmentNames')
        if (-not $raw -or $raw -notmatch '%[^%]+%') { return $null }
        return $raw
    } catch { return $null }
}

function Set-RawPathValue {
    param([string]$Scope, [string]$Value)
    $key = if ($Scope -eq 'Machine') {
        'HKLM:\SYSTEM\CurrentControlSet\Control\Session Manager\Environment'
    } else {
        'HKCU:\Environment'
    }
    Set-ItemProperty -LiteralPath $key -Name 'Path' -Value $Value -Type ExpandString -ErrorAction Stop
}

function Clean-Path {
    param([string]$Scope)
    $raw = Get-RawPathValue -Scope $Scope
    $p = if ($raw) { $raw } else { [Environment]::GetEnvironmentVariable("Path", $Scope) }
    if (-not $p) { return }
    $parts  = $p -split ';' | Where-Object { $_ -and $_.Trim() -ne '' }
    $keep   = @()
    $strip  = @()
    foreach ($e in $parts) {
        if ($e -match $PathPattern) { $strip += $e } else { $keep += $e }
    }
    if (-not $strip) {
        Write-Skip "$Scope PATH already clean."
        return
    }
    foreach ($s in $strip) { Write-Action "PATH/$Scope strip: $s" }
    if ($script:WriteMode) {
        try {
            if ($raw) {
                Set-RawPathValue -Scope $Scope -Value ($keep -join ';')
                Write-Ok "$Scope PATH rewritten ($($strip.Count) entries removed, %VARIABLES% preserved)."
                Write-Host "        Open a new session for the change to be seen." -ForegroundColor DarkGray
            } else {
                [Environment]::SetEnvironmentVariable("Path", ($keep -join ';'), $Scope)
                Write-Ok "$Scope PATH rewritten ($($strip.Count) entries removed)."
            }
        } catch { Write-Err "Set Path/$Scope -> $_"; foreach ($s in $strip) { Bump-Remaining } }
    } elseif ($script:AuditOnly) { foreach ($s in $strip) { Bump-Remaining } }
}
Clean-Path 'User'
if ($IsAdmin) { Clean-Path 'Machine' } else { Write-Skip "Machine PATH skipped (not admin)." }

# ============================================================================
# PHASE 7 - Python-related env vars
# ============================================================================
Write-Section "7. Python env vars"
$envNames = @('PYTHONPATH','PYTHONHOME','PYTHONUSERBASE','PYTHONSTARTUP','PYTHONDONTWRITEBYTECODE','PYTHONIOENCODING','PYTHONUTF8','PIP_CONFIG_FILE','PIP_INDEX_URL','PIP_REQUIRE_VIRTUALENV','VIRTUAL_ENV','CONDA_PREFIX','CONDA_DEFAULT_ENV','CONDA_PYTHON_EXE','CONDA_EXE','CONDA_SHLVL','_CE_M','_CE_CONDA','UV_CACHE_DIR','UV_PYTHON','PIPX_HOME','PIPX_BIN_DIR')
foreach ($scope in @('User','Machine')) {
    if ($scope -eq 'Machine' -and -not $IsAdmin) { continue }
    foreach ($e in $envNames) {
        $v = [Environment]::GetEnvironmentVariable($e, $scope)
        if ($v) {
            Write-Action "$scope env $e = $v"
            if ($script:WriteMode) {
                try { [Environment]::SetEnvironmentVariable($e, $null, $scope); Write-Ok "Cleared $scope!$e" }
                catch { Write-Err "Clear $scope!$e -> $_"; Bump-Remaining }
            } elseif ($script:Speculative) { Bump-Remaining }
        }
    }
}

# ============================================================================
# PHASE 8 - Registry: Python keys + Uninstall entries
# ============================================================================
Write-Section "8. Registry cleanup"

# 8a. Standard Python keys
$pyKeys = @(
    'HKCU:\Software\Python',
    'HKLM:\SOFTWARE\Python',
    'HKLM:\SOFTWARE\WOW6432Node\Python'
)
foreach ($k in $pyKeys) {
    if (Test-Path $k) {
        Write-Action "Reg $k"
        if ($script:WriteMode) {
            if (-not (Remove-RegKeyTreeSafe $k)) { Bump-Remaining }
        } elseif ($script:Speculative) { Bump-Remaining }
    }
}

# 8b. Uninstall registry entries with DisplayName matching Python/Conda
$uninstallBases = @(
    'HKCU:\SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall',
    'HKLM:\SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall',
    'HKLM:\SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall'
)
$uninstallPattern = '(?i)^(Python|Anaconda|Miniconda|Miniforge|Mambaforge|pipx|uv|Astral\.uv|Python\s+Launcher)'
foreach ($base in $uninstallBases) {
    if (-not (Test-Path $base)) { continue }
    Get-ChildItem -Path $base -ErrorAction SilentlyContinue | ForEach-Object {
        $dn = (Get-ItemProperty -Path $_.PSPath -Name DisplayName -ErrorAction SilentlyContinue).DisplayName
        if ($dn -and ($dn -match $uninstallPattern)) {
            Write-Action "Uninstall entry '$dn' at $($_.PSPath)"
            if ($script:WriteMode) {
                if (-not (Remove-RegKeyTreeSafe $_.PSPath)) { Bump-Remaining }
            } elseif ($script:Speculative) { Bump-Remaining }
        }
    }
}

# 8c. App Paths (HKCU + HKLM)
$appPathsBases = @(
    'HKCU:\SOFTWARE\Microsoft\Windows\CurrentVersion\App Paths',
    'HKLM:\SOFTWARE\Microsoft\Windows\CurrentVersion\App Paths'
)
foreach ($base in $appPathsBases) {
    if (-not (Test-Path $base)) { continue }
    Get-ChildItem -Path $base -ErrorAction SilentlyContinue | Where-Object {
        $_.PSChildName -match '^(python(\d(\.\d+)?)?|py|pythonw|idle)\.exe$'
    } | ForEach-Object {
        Write-Action "App Paths entry $($_.PSPath)"
        if ($script:WriteMode) {
            if (-not (Remove-RegKeyTreeSafe $_.PSPath)) { Bump-Remaining }
        } elseif ($script:Speculative) { Bump-Remaining }
    }
}

# ============================================================================
# PHASE 9 - Start Menu shortcuts
# ============================================================================
Write-Section "9. Start Menu shortcuts"
$startMenus = @(
    "$env:APPDATA\Microsoft\Windows\Start Menu",
    "$env:ProgramData\Microsoft\Windows\Start Menu"
)
foreach ($sm in $startMenus) {
    if (-not (Test-Path $sm)) { continue }
    Get-ChildItem $sm -Recurse -Force -Include *.lnk -ErrorAction SilentlyContinue | ForEach-Object {
        $lnk = $_.FullName
        # Inspect target via WScript.Shell
        try {
            $sh = New-Object -ComObject WScript.Shell
            $sc = $sh.CreateShortcut($lnk)
            $target = $sc.TargetPath
            if ($target -match '(?i)\\python(\d(\.\d+)?)?\.exe$' -or
                $target -match '(?i)\\py(thon)?launcher\.exe$' -or
                $target -match '(?i)\\(idle|pythonw)\.exe$' -or
                $target -match '(?i)\\(conda|anaconda|miniconda)' -or
                $lnk    -match '(?i)\\Python\b' -or
                $lnk    -match '(?i)\\Anaconda\b' -or
                $lnk    -match '(?i)\\Miniconda\b' -or
                $lnk    -match '(?i)\\IDLE\b') {
                Write-Action "Shortcut $lnk -> $target"
                if ($script:WriteMode) {
                    if (-not (Remove-FileHard $lnk)) { Bump-Remaining }
                } elseif ($script:Speculative) { Bump-Remaining }
            }
        } catch {}
    }
}

# Drop now-empty Python/Anaconda program folders under Start Menu/Programs
foreach ($sm in $startMenus) {
    $prog = Join-Path $sm 'Programs'
    if (-not (Test-Path $prog)) { continue }
    Get-ChildItem $prog -Directory -Force -ErrorAction SilentlyContinue | Where-Object {
        $_.Name -match '^(Python|Anaconda|Miniconda|Miniforge|Mambaforge)' -and
        -not (Get-ChildItem $_.FullName -Recurse -Force -File -ErrorAction SilentlyContinue)
    } | ForEach-Object {
        Write-Action "Empty Start Menu group: $($_.FullName)"
        if ($script:WriteMode) {
            try { Remove-Item -LiteralPath $_.FullName -Recurse -Force -ErrorAction Stop; Write-Ok "Removed" }
            catch { Write-Err "Remove $($_.FullName) -> $_"; Bump-Remaining }
        } elseif ($script:Speculative) { Bump-Remaining }
    }
}

# ============================================================================
# PHASE 10 - Final audit
# ============================================================================
Write-Section "10. Final audit"

$auditBreakdown = [ordered]@{}
$script:auditCountRef = [ref]0
function Audit-Bump([string]$Category, [int]$Count) {
    if ($Count -le 0) { return }
    $auditBreakdown[$Category] = ($auditBreakdown[$Category] + $Count)
    $script:auditCountRef.Value += $Count
}

# 1. Installed Python launchers (winget / python.org / py.exe).
#    Filter out WindowsApps stubs (the AppExecutionAliases we intentionally keep).
$pyExe = @(
    (Get-Command python -ErrorAction SilentlyContinue),
    (Get-Command py -ErrorAction SilentlyContinue),
    (Get-Command pythonw -ErrorAction SilentlyContinue)
) | Where-Object { $_ -and $_.Source -and $_.Source -notmatch 'WindowsApps' }
Audit-Bump 'Python launcher in PATH'        @($pyExe).Count

# 2. AppX Python packages (not the alias stubs)
Audit-Bump 'AppX Python package'            @(Get-AppxPackage -ErrorAction SilentlyContinue | Where-Object { $_.Name -match 'Python' -or $_.PublisherDisplayName -match 'Python Software Foundation' }).Count

# 3. Folder leftovers
$folderHits = 0
foreach ($f in $folders) { if (Test-Path -LiteralPath $f) { $folderHits++ } }
foreach ($pat in $wildFolders) {
    Get-Item -Path $pat -ErrorAction SilentlyContinue | Where-Object { -not (Test-IsOwnToolkitFolder $_.FullName) } | ForEach-Object { $folderHits++ }
}
Audit-Bump 'Python folder'                  $folderHits

# 4. py.exe launcher
Audit-Bump 'py.exe / pyw.exe'               @(@('C:\Windows\py.exe','C:\Windows\pyw.exe') | Where-Object { Test-Path -LiteralPath $_ }).Count

# 5. PATH entries
$pathHits = 0
foreach ($scope in @('User','Machine')) {
    if ($scope -eq 'Machine' -and -not $IsAdmin) { continue }
    $pp = [Environment]::GetEnvironmentVariable("Path", $scope)
    if ($pp) {
        $pathHits += @($pp -split ';' | Where-Object { $_ -match $PathPattern }).Count
    }
}
Audit-Bump 'PATH entry'                     $pathHits

# 6. Env vars
$envHits = 0
$envNames = @('PYTHONPATH','PYTHONHOME','PYTHONUSERBASE','PYTHONSTARTUP','PYTHONDONTWRITEBYTECODE','PYTHONIOENCODING','PYTHONUTF8','PIP_CONFIG_FILE','PIP_INDEX_URL','PIP_REQUIRE_VIRTUALENV','VIRTUAL_ENV','CONDA_PREFIX','CONDA_DEFAULT_ENV','CONDA_PYTHON_EXE','CONDA_EXE','CONDA_SHLVL','_CE_M','_CE_CONDA','UV_CACHE_DIR','UV_PYTHON','PIPX_HOME','PIPX_BIN_DIR')
foreach ($scope in @('User','Machine')) {
    if ($scope -eq 'Machine' -and -not $IsAdmin) { continue }
    foreach ($e in $envNames) {
        if ([Environment]::GetEnvironmentVariable($e, $scope)) { $envHits++ }
    }
}
Audit-Bump 'Python env var'                 $envHits

# 7. Registry: Software\Python + App Paths + Uninstall entries
foreach ($k in @('HKCU:\Software\Python','HKLM:\SOFTWARE\Python','HKLM:\SOFTWARE\WOW6432Node\Python')) {
    if (Test-Path $k) { Audit-Bump 'Software\Python key' 1 }
}
$appPathsHits = 0
foreach ($base in @('HKCU:\SOFTWARE\Microsoft\Windows\CurrentVersion\App Paths','HKLM:\SOFTWARE\Microsoft\Windows\CurrentVersion\App Paths')) {
    if (-not (Test-Path $base)) { continue }
    $appPathsHits += @(Get-ChildItem -Path $base -ErrorAction SilentlyContinue | Where-Object {
        $_.PSChildName -match '^(python(\d(\.\d+)?)?|py|pythonw|idle)\.exe$'
    }).Count
}
Audit-Bump 'App Paths entry'                $appPathsHits
$uninstallHits = 0
$uninstallPattern = '(?i)^(Python|Anaconda|Miniconda|Miniforge|Mambaforge|pipx|uv|Astral\.uv|Python\s+Launcher)'
foreach ($base in @(
    'HKCU:\SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall',
    'HKLM:\SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall',
    'HKLM:\SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall'
)) {
    if (-not (Test-Path $base)) { continue }
    Get-ChildItem -Path $base -ErrorAction SilentlyContinue | ForEach-Object {
        $dn = (Get-ItemProperty -Path $_.PSPath -Name DisplayName -ErrorAction SilentlyContinue).DisplayName
        if ($dn -and $dn -match $uninstallPattern) { $uninstallHits++ }
    }
}
Audit-Bump 'Uninstall registry entry'       $uninstallHits

$auditCount = $script:auditCountRef.Value

Write-Host ""
Write-Host "Mode             : $Mode"
$statusColor = if ($script:AuditUnknown) {'Yellow'} elseif ($auditCount -eq 0 -and $script:Remaining -eq 0) {'Green'} else {'Red'}
if ($script:AuditOnly) {
    Write-Host "Items found      : $($script:Remaining)" -ForegroundColor $statusColor
} elseif ($script:DryRun) {
    Write-Host "Items that would be removed : $($script:Remaining)" -ForegroundColor Yellow
} else {
    Write-Host "Items acted on   : $($script:Remaining)" -ForegroundColor Yellow
    $remainText = if ($script:AuditUnknown) {
        "$auditCount confirmed + inconclusive checks (see above)"
    } else { "$auditCount" }
    Write-Host "Items remaining  : $remainText" -ForegroundColor $statusColor
}
if ($auditBreakdown.Count -gt 0) {
    Write-Host ""
    Write-Host "  Breakdown:" -ForegroundColor DarkGray
    foreach ($cat in $auditBreakdown.Keys) {
        Write-Host ("    {0,-40} : {1}" -f $cat, $auditBreakdown[$cat]) -ForegroundColor DarkGray
    }
}
if ($script:WriteMode -and $auditCount -gt 0) {
    Write-Host ""
    Write-Host "Some leftovers remain. A reboot often releases any locks. Re-run after reboot." -ForegroundColor DarkYellow
}
if ($script:AuditUnknown) {
    Write-Host ""
    Write-Host "STATUS: results inconclusive - one or more checks failed (e.g." -ForegroundColor Yellow
    Write-Host "  Get-AppxProvisionedPackage Access Denied). Re-run elevated." -ForegroundColor DarkYellow
}
Write-Host "Log file         : $LogPath"

try { Stop-Transcript | Out-Null } catch {}

if ($script:AuditOnly -or $script:DryRun) {
    $script:FinalExit = $script:Remaining
} else {
    $script:FinalExit = $auditCount
}

Write-Host ""
Write-Host "Exit code: $script:FinalExit" -ForegroundColor $(if ($script:FinalExit -eq 0) {'Green'} else {'Red'})

exit $script:FinalExit
