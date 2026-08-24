<#
.SYNOPSIS
    Universal Codex App removal for Windows.

.DESCRIPTION
    Removes every known artifact installed by the OpenAI Codex desktop app:
      - Appx package (per-user + provisioned)
      - User-profile folders (.codex, Codex_Cache_Quarantine,
        Codex_Nuclear_Quarantine, AppData\Local\OpenAI\Codex)
      - Sandbox local user accounts (CodexSandboxOffline/Online)
      - Sandbox profile folders (C:\Users\CodexSandbox*)
      - Firewall rules (codex_sandbox_*)
      - HKCU: RegisteredApplications, NotifyIconSettings, MrtCache,
        IE LowRegistry Audio policy entries
      - HKLM: Windows Search indexer rules, AppModel StateRepository cache,
        InstallService CategoryCache, ProfileList (TrustedInstaller-protected
        keys are taken over via SeTakeOwnership + ACL rewrite)
      - Stops/starts WSearch + StateRepository to release locks
      - MoveFileEx-schedules locked files for deletion on next reboot

    Idempotent: re-running on a clean machine reports 0 artifacts.

.PARAMETER Mode
    Audit         - read-only scan, list everything that would be removed.
    DryRun        - simulate a full Nuke, no changes.
    Nuke          - actually remove everything (the canonical mode).
    SessionReset  - SOFT mode: kill Codex processes and clear ONLY the
                    session/cache state (.codex/sessions/, AppX package
                    LocalCache + TempState). Keeps auth, config, the
                    AppX package itself, sandbox users, firewall, and
                    every registry artifact. Use when the GPT 5.5
                    xhigh-compaction bug hangs your Codex - restart the
                    app after this and it should come back clean. If it
                    does not, fall through to -Mode Nuke.

.PARAMETER KeepCaches
    Skip TrustedInstaller-protected caches (StateRepository, MrtCache).
    Use if you don't want to stop WSearch/StateRepository services.

.PARAMETER SkipReboot
    Do not schedule any leftover files for deletion on next reboot.

.PARAMETER PackageNamePattern
    Regex matched against Appx Package.Name. Default: ^OpenAI\.Codex

.PARAMETER UserNamePattern
    Regex matched against local user names. Default: ^CodexSandbox

.PARAMETER FirewallRulePattern
    Regex matched against firewall rule Name/DisplayName. Default: ^codex_

.PARAMETER LogPath
    Transcript path. Default: script folder + nuke-<timestamp>.log

.EXAMPLE
    .\Invoke-CodexNuke.ps1 -Mode Audit
.EXAMPLE
    .\Invoke-CodexNuke.ps1 -Mode Nuke
.EXAMPLE
    .\Invoke-CodexNuke.ps1 -Mode Nuke -KeepCaches -SkipReboot
#>

[CmdletBinding()]
param(
    [ValidateSet('Audit','DryRun','Nuke','SessionReset')]
    [string]$Mode = 'Audit',

    [switch]$KeepCaches,
    [switch]$SkipReboot,

    # If you have the Codex CLI installed (npm-based, separate from the
    # Desktop App), it shares authentication / session state with the
    # Desktop App via ~/.codex/. Removing the folder breaks the CLI in a
    # known, silent way (see openai/codex#14087): CLI still launches and
    # accepts input but never produces a response. Pass -KeepCliState to
    # keep ~/.codex/ intact while removing everything else.
    [switch]$KeepCliState,

    # By default we run wsreset.exe at the very end of a Nuke pass so that
    # Microsoft Store sees a fully clean slate and can reinstall Codex
    # without hitting "ghost install" errors. Pass -SkipStoreReset to
    # disable (useful in GUI pipelines that handle Store separately).
    [switch]$SkipStoreReset,

    [string]$PackageNamePattern   = '^OpenAI\.Codex',
    [string]$PackageInPathPattern = 'OpenAI\.Codex',
    [string]$UserNamePattern      = '^CodexSandbox',
    [string]$FirewallRulePattern  = '^codex_',

    [string]$LogPath = (Join-Path $PSScriptRoot ("Logs\nuke-{0}.log" -f (Get-Date -Format 'yyyyMMdd-HHmmss')))
)
# Ensure the log directory exists. Done before Start-Transcript so the
# very first call on a fresh install doesn't fail.
try {
    $logDir = Split-Path -Parent $LogPath
    if ($logDir -and -not (Test-Path -LiteralPath $logDir)) {
        New-Item -ItemType Directory -Path $logDir -Force | Out-Null
    }
} catch {}
# Note: this script never blocks on input. It is a pure-logic library
# suitable for embedding in a cmd wrapper, GUI uninstaller, scheduled
# task or MSI custom action. Any "press ENTER to close" UX belongs in
# the calling wrapper (see Nuke.cmd).

$ErrorActionPreference = 'Continue'
$script:Remaining = 0
$script:WriteMode = ($Mode -eq 'Nuke')
$script:DryRun    = ($Mode -eq 'DryRun')
$script:AuditOnly = ($Mode -eq 'Audit')
$script:SessionReset = ($Mode -eq 'SessionReset')
# True when something during the run prevented us from being sure about
# the post-state of a check (e.g. Get-AppxProvisionedPackage threw Access
# Denied). Final summary uses this to avoid a misleading "Clean: 0".
$script:AuditUnknown = $false
# True when Audit or DryRun (no actual writes). Replaces the older
# pattern of bumping only in Audit, which under-counted DryRun.
$script:Speculative = $script:AuditOnly -or $script:DryRun

# --- Logging ----------------------------------------------------------------
try { Start-Transcript -Path $LogPath -Force | Out-Null } catch {}

function Write-Section($title) {
    Write-Host ""
    Write-Host ("=" * 70) -ForegroundColor Cyan
    Write-Host (" $title") -ForegroundColor Cyan
    Write-Host ("=" * 70) -ForegroundColor Cyan
}

function Write-Action($msg) {
    $tag = switch ($Mode) { 'Audit' {'[FOUND]'} 'DryRun' {'[WOULDDO]'} 'Nuke' {'[ACT]'} 'SessionReset' {'[ACT]'} }
    Write-Host "$tag $msg" -ForegroundColor Yellow
}

function Write-Ok($msg) { Write-Host "[OK]    $msg" -ForegroundColor Green }
function Write-Skip($msg) { Write-Host "[SKIP]  $msg" -ForegroundColor DarkGray }
function Write-Err($msg) { Write-Host "[ERR]   $msg" -ForegroundColor Red }

function Bump-Remaining { $script:Remaining++ }
function Test-PathQuiet {
    param([string]$Path)
    try {
        return (Test-Path -LiteralPath $Path -ErrorAction Stop)
    } catch {
        $script:AuditUnknown = $true
        Write-Skip "Cannot access path: $Path ($($_.Exception.Message))"
        return $false
    }
}

# --- Privilege check --------------------------------------------------------
$id = [System.Security.Principal.WindowsIdentity]::GetCurrent()
$pr = New-Object System.Security.Principal.WindowsPrincipal($id)
$IsAdmin = $pr.IsInRole([System.Security.Principal.WindowsBuiltinRole]::Administrator)
if ($script:WriteMode -and -not $IsAdmin) {
    Write-Err "Nuke mode requires administrator rights. Re-launch via Nuke.cmd."
    try { Stop-Transcript | Out-Null } catch {}
    exit 255
}
# SessionReset is the only mutating mode that does NOT require admin -
# everything it touches lives in the current user's profile.
if (-not $IsAdmin) {
    Write-Host "[INFO]  Running non-elevated. Some HKLM keys may be hidden." -ForegroundColor DarkYellow
}

Write-Section "Codex Nuke - Mode: $Mode"
Write-Host "User    : $($id.Name)"
Write-Host "Host    : $env:COMPUTERNAME"
Write-Host "Log     : $LogPath"
Write-Host "Pattern : pkg=$PackageNamePattern user=$UserNamePattern fw=$FirewallRulePattern"

# ============================================================================
# SESSION RESET (soft mode) - early exit
# ============================================================================
# This is the lightweight "unstick xhigh-compaction" path. It deliberately
# does NOT remove the Codex install or any of the system-level artifacts.
# If your hang is caused by stale session/cache state on disk, this should
# fix it without a Store reinstall. If the hang survives, run -Mode Nuke.
if ($script:SessionReset) {
    Write-Section "SessionReset - kill Codex + clear sessions/caches"

    # 1. Kill running processes (same as Phase 1)
    $procs = Get-Process -ErrorAction SilentlyContinue | Where-Object {
        $_.ProcessName -match 'odex' -or
        ($_.Path -and $_.Path -match '\\(?:OpenAI\\Codex|WindowsApps\\OpenAI\.Codex)')
    }
    if ($procs) {
        foreach ($p in $procs) {
            Write-Action "Kill PID=$($p.Id) Name=$($p.ProcessName)"
            try { Stop-Process -Id $p.Id -Force -ErrorAction Stop; Write-Ok "Killed" }
            catch { Write-Err "Kill PID $($p.Id) -> $_" }
        }
    } else { Write-Skip "No Codex processes." }

    # 2. Targets: only session / cache subdirectories. NEVER the whole
    #    .codex/ folder (that holds auth tokens - see openai/codex#14087).
    $sessionTargets = @()
    foreach ($u in (Get-ChildItem 'C:\Users' -Directory -Force -ErrorAction SilentlyContinue)) {
        $sessionTargets += (Join-Path $u.FullName '.codex\sessions')
        $sessionTargets += (Join-Path $u.FullName '.codex\cache')
        $sessionTargets += (Join-Path $u.FullName '.codex\logs')
        $sessionTargets += (Join-Path $u.FullName 'AppData\Local\OpenAI\Codex\Cache')
        $sessionTargets += (Join-Path $u.FullName 'AppData\Local\OpenAI\Codex\logs')
        # AppX package LocalCache + TempState (safe to wipe - AppX rebuilds).
        $pkgsDir = Join-Path $u.FullName 'AppData\Local\Packages'
        if (Test-Path -LiteralPath $pkgsDir) {
            Get-ChildItem -LiteralPath $pkgsDir -Directory -Force -ErrorAction SilentlyContinue |
                Where-Object { $_.Name -match $PackageNamePattern } | ForEach-Object {
                    $sessionTargets += (Join-Path $_.FullName 'LocalCache')
                    $sessionTargets += (Join-Path $_.FullName 'TempState')
                }
        }
    }

    $cleared = 0; $missed = 0
    foreach ($t in $sessionTargets) {
        if (-not (Test-Path -LiteralPath $t)) { continue }
        Write-Action "Clear $t"
        try {
            # Empty the directory but keep it (so the app doesn't recreate
            # it with different ACLs / settings on next start).
            Get-ChildItem -LiteralPath $t -Recurse -Force -ErrorAction SilentlyContinue |
                Sort-Object @{Expression={$_.FullName.Length}; Descending=$true} |
                Remove-Item -Force -Recurse -ErrorAction SilentlyContinue
            $cleared++
            Write-Ok "  Cleared"
        } catch {
            Write-Err "  Failed: $_"
            $missed++
        }
    }

    Write-Host ""
    Write-Host "Mode             : SessionReset"
    Write-Host "Locations cleared: $cleared"
    if ($missed -gt 0) {
        Write-Host "Locations failed : $missed" -ForegroundColor Yellow
    }
    Write-Host "Log file         : $LogPath"
    Write-Host ""
    Write-Host "NEXT STEP: launch Codex again (no reinstall needed)." -ForegroundColor Cyan
    Write-Host "  Auth, settings and the AppX install are untouched." -ForegroundColor DarkCyan
    Write-Host "  If the hang persists, escalate to -Mode Nuke." -ForegroundColor DarkCyan

    try { Stop-Transcript | Out-Null } catch {}
    exit $missed
}

# --- Token privileges (for TrustedInstaller key takeover) ------------------
if ($script:WriteMode -and -not $KeepCaches) {
    try {
        Add-Type -ErrorAction Stop -TypeDefinition @"
using System;
using System.Runtime.InteropServices;
public class TokenPriv {
    [DllImport("advapi32.dll", ExactSpelling=true, SetLastError=true)]
    static extern bool AdjustTokenPrivileges(IntPtr htok, bool disall, ref TokPriv1Luid newst, int len, IntPtr prev, IntPtr relen);
    [DllImport("advapi32.dll", ExactSpelling=true, SetLastError=true)]
    static extern bool OpenProcessToken(IntPtr h, int acc, ref IntPtr phtok);
    [DllImport("advapi32.dll", SetLastError=true)]
    static extern bool LookupPrivilegeValue(string host, string name, ref long pluid);
    [StructLayout(LayoutKind.Sequential, Pack=1)]
    public struct TokPriv1Luid { public int Count; public long Luid; public int Attr; }
    [DllImport("kernel32.dll", ExactSpelling=true)]
    public static extern IntPtr GetCurrentProcess();
    public static bool EnablePrivilege(string priv) {
        IntPtr hproc = GetCurrentProcess();
        IntPtr htok = IntPtr.Zero;
        if (!OpenProcessToken(hproc, 0x28, ref htok)) return false;
        TokPriv1Luid tp;
        tp.Count = 1; tp.Luid = 0; tp.Attr = 0x2;
        if (!LookupPrivilegeValue(null, priv, ref tp.Luid)) return false;
        return AdjustTokenPrivileges(htok, false, ref tp, 0, IntPtr.Zero, IntPtr.Zero);
    }
}
"@
        [void][TokenPriv]::EnablePrivilege('SeTakeOwnershipPrivilege')
        [void][TokenPriv]::EnablePrivilege('SeRestorePrivilege')
        [void][TokenPriv]::EnablePrivilege('SeBackupPrivilege')
    } catch {
        Write-Err "Failed to enable ownership privileges: $_"
    }
}

if ($script:WriteMode -and -not $SkipReboot) {
    try {
        Add-Type -ErrorAction Stop -TypeDefinition @"
using System;
using System.Runtime.InteropServices;
public class MoveFile {
    [DllImport("kernel32.dll", CharSet=CharSet.Unicode, SetLastError=true)]
    public static extern bool MoveFileEx(string lpExistingFileName, string lpNewFileName, int dwFlags);
}
"@
    } catch {}
}

$adminSid = New-Object System.Security.Principal.SecurityIdentifier('S-1-5-32-544')
$adminNT  = $adminSid.Translate([System.Security.Principal.NTAccount])

# --- Helpers ---------------------------------------------------------------

function Take-RegKeyOwnership {
    param([Parameter(Mandatory)] [Microsoft.Win32.RegistryHive]$Hive, [Parameter(Mandatory)] [string]$SubKey)
    try {
        $base = [Microsoft.Win32.RegistryKey]::OpenBaseKey($Hive, [Microsoft.Win32.RegistryView]::Default)
        $k = $base.OpenSubKey(
            $SubKey,
            [Microsoft.Win32.RegistryKeyPermissionCheck]::ReadWriteSubTree,
            [System.Security.AccessControl.RegistryRights]::TakeOwnership)
        if ($null -eq $k) { return $false }
        $acl = $k.GetAccessControl()
        $acl.SetOwner($adminNT)
        $k.SetAccessControl($acl); $k.Close()

        $k = $base.OpenSubKey(
            $SubKey,
            [Microsoft.Win32.RegistryKeyPermissionCheck]::ReadWriteSubTree,
            [System.Security.AccessControl.RegistryRights]::ChangePermissions)
        $acl = $k.GetAccessControl()
        $rule = New-Object System.Security.AccessControl.RegistryAccessRule(
            $adminNT, 'FullControl', 'ContainerInherit', 'None', 'Allow')
        $acl.AddAccessRule($rule)
        $k.SetAccessControl($acl); $k.Close()
        return $true
    } catch { Write-Err "Take-RegKeyOwnership $Hive\$SubKey -> $_"; return $false }
}

function Remove-RegKeyTree {
    param([Parameter(Mandatory)] [Microsoft.Win32.RegistryHive]$Hive, [Parameter(Mandatory)] [string]$SubKey)
    if ($script:AuditOnly -or $script:DryRun) { return $true }
    try {
        $base = [Microsoft.Win32.RegistryKey]::OpenBaseKey($Hive, [Microsoft.Win32.RegistryView]::Default)
        $base.DeleteSubKeyTree($SubKey, $false)
        return $true
    } catch { Write-Err "Delete $Hive\$SubKey -> $_"; return $false }
}

function Remove-RegValue {
    param([string]$PSPath, [string]$Name)
    if ($script:AuditOnly -or $script:DryRun) { return }
    try { Remove-ItemProperty -Path $PSPath -Name $Name -Force -ErrorAction Stop }
    catch { Write-Err "Remove-ItemProperty ${PSPath}!${Name} -> $_" }
}

# Service-state snapshot. We only restart services that WE stopped; if
# the user/admin had a service already stopped before our run, we leave
# it stopped.
$script:ServiceWasRunning = @{}

function Stop-ServiceSafe { param([string]$Name)
    if ($script:Speculative) { return }
    $s = Get-Service -Name $Name -ErrorAction SilentlyContinue
    if (-not $s) { return }
    # Snapshot pre-run status the first time we touch this service.
    if (-not $script:ServiceWasRunning.ContainsKey($Name)) {
        $script:ServiceWasRunning[$Name] = ($s.Status -eq 'Running')
    }
    if ($s.Status -eq 'Running') {
        try { Stop-Service -Name $Name -Force -ErrorAction Stop; Write-Ok "Stopped $Name" }
        catch { Write-Err "Stop $Name -> $_" }
    }
}

function Start-ServiceSafe { param([string]$Name)
    if ($script:Speculative) { return }
    # Only start if the service was running BEFORE we touched it.
    # Skip otherwise - the user may have stopped it on purpose.
    if (-not $script:ServiceWasRunning.ContainsKey($Name)) {
        return
    }
    if (-not $script:ServiceWasRunning[$Name]) {
        Write-Skip "$Name was not running before; leaving it stopped."
        return
    }
    $s = Get-Service -Name $Name -ErrorAction SilentlyContinue
    if ($s -and $s.StartType -ne 'Disabled' -and $s.Status -ne 'Running') {
        try { Start-Service -Name $Name -ErrorAction Stop; Write-Ok "Started $Name (restored pre-run state)" }
        catch { Write-Err "Start $Name -> $_" }
    }
}

function Remove-FolderHard {
    param([string]$Path)
    if (-not (Test-Path -LiteralPath $Path)) { return $true }
    if ($script:AuditOnly -or $script:DryRun) { return $true }

    # Fast path: try simple recursive delete (works for user-owned folders).
    try {
        Remove-Item -LiteralPath $Path -Recurse -Force -ErrorAction Stop
        Write-Ok "  Deleted (fast): $Path"
        return $true
    } catch {
        Write-Host "  Fast delete failed ($($_.Exception.Message.Trim())). Escalating..." -ForegroundColor DarkGray
    }

    # Escalation: takeown + grant Admins FullControl, then rd /s /q.
    try {
        & takeown /F $Path /R /D Y 2>&1 | Out-Null
        & icacls $Path /grant "*S-1-5-32-544:(F)" /T /C /Q 2>&1 | Out-Null
        & cmd /c rd /s /q "$Path" 2>&1 | Out-Null
    } catch {}

    if (Test-Path -LiteralPath $Path) {
        # Last resort: schedule remaining items for delete on next reboot.
        # Order matters: a directory can only be removed once it is empty,
        # so schedule the deepest entries first. PendingFileRenameOperations
        # is processed in registry order, and we want children before
        # parents - sort by full-path length (deepest paths are longest).
        if (-not $SkipReboot) {
            $items = Get-ChildItem -LiteralPath $Path -Recurse -Force -ErrorAction SilentlyContinue |
                Sort-Object @{Expression={$_.FullName.Length}; Descending=$true}
            foreach ($it in $items) { [void][MoveFile]::MoveFileEx($it.FullName, $null, 4) }
            # Root last - after all children are scheduled for removal.
            [void][MoveFile]::MoveFileEx($Path, $null, 4)
            Write-Action "  Scheduled '$Path' (and $($items.Count) descendants, deepest-first) for delete-on-reboot."
            return $false
        }
        Write-Err "  Could not delete '$Path' and -SkipReboot was set."
        return $false
    }
    Write-Ok "  Deleted (escalated): $Path"
    return $true
}

# ============================================================================
# PHASE 1 - Running processes
# ============================================================================
Write-Section "1. Running processes"
$procs = Get-Process -ErrorAction SilentlyContinue | Where-Object {
    $_.ProcessName -match 'odex' -or
    ($_.Path -and $_.Path -match '\\(?:OpenAI\\Codex|WindowsApps\\OpenAI\.Codex)')
}
if ($procs) {
    foreach ($p in $procs) {
        Write-Action "Process PID=$($p.Id) Name=$($p.ProcessName) Path=$($p.Path)"
        if ($script:WriteMode) {
            try { Stop-Process -Id $p.Id -Force -ErrorAction Stop; Write-Ok "Killed PID $($p.Id)" }
            catch { Write-Err "Kill PID $($p.Id) -> $_"; Bump-Remaining }
        } elseif ($script:Speculative) { Bump-Remaining }
    }
} else { Write-Skip "No Codex processes." }

# ============================================================================
# PHASE 2 - Appx packages (per-user + provisioned)
# ============================================================================
Write-Section "2. Appx packages"
if ($IsAdmin) {
    $pkgs = Get-AppxPackage -AllUsers -ErrorAction SilentlyContinue | Where-Object { $_.Name -match $PackageNamePattern }
} else { $pkgs = $null }
if (-not $pkgs) { $pkgs = Get-AppxPackage -ErrorAction SilentlyContinue | Where-Object { $_.Name -match $PackageNamePattern } }
if ($pkgs) {
    foreach ($pkg in $pkgs) {
        Write-Action "Appx $($pkg.PackageFullName)"
        if ($script:WriteMode) {
            try { Remove-AppxPackage -Package $pkg.PackageFullName -AllUsers -ErrorAction Stop; Write-Ok "Removed $($pkg.Name)" }
            catch {
                try { Remove-AppxPackage -Package $pkg.PackageFullName -ErrorAction Stop; Write-Ok "Removed $($pkg.Name) (current user)" }
                catch { Write-Err "Remove-AppxPackage -> $_"; Bump-Remaining }
            }
        } elseif ($script:Speculative) { Bump-Remaining }
    }
} else { Write-Skip "No Appx packages match $PackageNamePattern." }

$prov = $null
if ($IsAdmin) {
    try {
        $prov = Get-AppxProvisionedPackage -Online -ErrorAction Stop | Where-Object { $_.DisplayName -match $PackageNamePattern }
    } catch {
        Write-Skip "Get-AppxProvisionedPackage failed: $($_.Exception.Message.Trim())"
        # We could not enumerate provisioned packages, so we cannot
        # honestly say "0 remaining". Flag the run as inconclusive.
        $script:AuditUnknown = $true
    }
}
if ($prov) {
    foreach ($pp in $prov) {
        Write-Action "Provisioned $($pp.PackageName)"
        if ($script:WriteMode) {
            try { Remove-AppxProvisionedPackage -Online -PackageName $pp.PackageName -ErrorAction Stop | Out-Null; Write-Ok "Removed provisioned $($pp.DisplayName)" }
            catch { Write-Err "Remove-AppxProvisionedPackage -> $_"; Bump-Remaining }
        } elseif ($script:Speculative) { Bump-Remaining }
    }
} else { Write-Skip "No provisioned packages match." }

# ============================================================================
# PHASE 3 - Folders in every user profile
# ============================================================================
Write-Section "3. User-profile folders"
$folderNames = if ($KeepCliState) {
    @('Codex_Cache_Quarantine','Codex_Nuclear_Quarantine')
} else {
    @('.codex','Codex_Cache_Quarantine','Codex_Nuclear_Quarantine')
}
$userRoots = Get-ChildItem 'C:\Users' -Directory -Force -ErrorAction SilentlyContinue
foreach ($u in $userRoots) {
    foreach ($f in $folderNames) {
        $p = Join-Path $u.FullName $f
        if (Test-PathQuiet $p) {
            Write-Action "Folder $p"
            if ($script:WriteMode) {
                if (-not (Remove-FolderHard $p)) { Bump-Remaining }
            } elseif ($script:Speculative) { Bump-Remaining }
        }
    }
    $oai = Join-Path $u.FullName 'AppData\Local\OpenAI\Codex'
    if (Test-Path -LiteralPath $oai) {
        Write-Action "Folder $oai"
        if ($script:WriteMode) {
            if (-not (Remove-FolderHard $oai)) { Bump-Remaining }
            # Try to remove the now-empty parent OpenAI folder
            $parent = Split-Path $oai -Parent
            if ((Test-Path -LiteralPath $parent) -and -not (Get-ChildItem -LiteralPath $parent -Force -ErrorAction SilentlyContinue)) {
                Remove-Item -LiteralPath $parent -Force -ErrorAction SilentlyContinue
            }
        } elseif ($script:Speculative) { Bump-Remaining }
    }
    # Per-package Packages\ folder
    $pkgsDir = Join-Path $u.FullName 'AppData\Local\Packages'
    if (Test-Path -LiteralPath $pkgsDir) {
        Get-ChildItem -LiteralPath $pkgsDir -Directory -Force -ErrorAction SilentlyContinue |
            Where-Object { $_.Name -match $PackageNamePattern } | ForEach-Object {
                Write-Action "Folder $($_.FullName)"
                if ($script:WriteMode) {
                    if (-not (Remove-FolderHard $_.FullName)) { Bump-Remaining }
                } elseif ($script:Speculative) { Bump-Remaining }
            }
    }
}

# ============================================================================
# PHASE 4 - Sandbox local user accounts
# ============================================================================
Write-Section "4. Sandbox local users"
$users = Get-LocalUser -ErrorAction SilentlyContinue | Where-Object { $_.Name -match $UserNamePattern }
foreach ($u in $users) {
    Write-Action "User $($u.Name) SID=$($u.SID)"
    if ($script:WriteMode) {
        try { Remove-LocalUser -SID $u.SID -ErrorAction Stop; Write-Ok "Removed $($u.Name)" }
        catch {
            try { & net user $u.Name /delete 2>&1 | Out-Null; Write-Ok "Removed via net user $($u.Name)" }
            catch { Write-Err "Remove-LocalUser -> $_"; Bump-Remaining }
        }
    } elseif ($script:Speculative) { Bump-Remaining }
}
if (-not $users) { Write-Skip "No local users match $UserNamePattern." }

# Sandbox profile folders + ProfileList entries
$sbxFolders = Get-ChildItem 'C:\Users' -Directory -Force -ErrorAction SilentlyContinue | Where-Object { $_.Name -match $UserNamePattern }
foreach ($sf in $sbxFolders) {
    Write-Action "Folder $($sf.FullName)"
    if ($script:WriteMode) {
        if (-not (Remove-FolderHard $sf.FullName)) { Bump-Remaining }
    } elseif ($script:Speculative) { Bump-Remaining }
}

# ProfileList registry entries pointing at CodexSandbox profiles
foreach ($plBase in @(
    'SOFTWARE\Microsoft\Windows NT\CurrentVersion\ProfileList',
    'SOFTWARE\WOW6432Node\Microsoft\Windows NT\CurrentVersion\ProfileList'
)) {
    $psPath = "Registry::HKEY_LOCAL_MACHINE\$plBase"
    if (-not (Test-Path $psPath)) { continue }
    Get-ChildItem -Path $psPath -ErrorAction SilentlyContinue | ForEach-Object {
        $img = (Get-ItemProperty -Path $_.PSPath -Name ProfileImagePath -ErrorAction SilentlyContinue).ProfileImagePath
        if ($img -and ($img -match $UserNamePattern)) {
            $sub = "$plBase\$($_.PSChildName)"
            Write-Action "Reg $sub -> $img"
            if ($script:WriteMode) {
                [void](Take-RegKeyOwnership -Hive LocalMachine -SubKey $sub)
                if (-not (Remove-RegKeyTree -Hive LocalMachine -SubKey $sub)) { Bump-Remaining }
                else { Write-Ok "Deleted $sub" }
            } elseif ($script:Speculative) { Bump-Remaining }
        }
    }
}

# ============================================================================
# PHASE 5 - Firewall rules
# ============================================================================
Write-Section "5. Firewall rules"
$fwRules = Get-NetFirewallRule -ErrorAction SilentlyContinue | Where-Object {
    $_.Name -match $FirewallRulePattern -or $_.DisplayName -match $FirewallRulePattern
}
foreach ($r in $fwRules) {
    Write-Action "FW $($r.Name) [$($r.DisplayName)]"
    if ($script:WriteMode) {
        try { Remove-NetFirewallRule -Name $r.Name -ErrorAction Stop; Write-Ok "Removed $($r.Name)" }
        catch { Write-Err "Remove-NetFirewallRule -> $_"; Bump-Remaining }
    } elseif ($script:Speculative) { Bump-Remaining }
}
if (-not $fwRules) { Write-Skip "No firewall rules match $FirewallRulePattern." }

# ============================================================================
# PHASE 6 - HKCU cleanup
# ============================================================================
Write-Section "6. HKCU cleanup"

# 6a. NotifyIconSettings
$nis = 'HKCU:\Control Panel\NotifyIconSettings'
if (Test-Path $nis) {
    Get-ChildItem -Path $nis -ErrorAction SilentlyContinue | ForEach-Object {
        $val = (Get-ItemProperty -Path $_.PSPath -Name ExecutablePath -ErrorAction SilentlyContinue).ExecutablePath
        if ($val -and $val -match $PackageInPathPattern) {
            Write-Action "Reg HKCU\Control Panel\NotifyIconSettings\$($_.PSChildName) -> $val"
            if ($script:WriteMode) {
                try { Remove-Item -Path $_.PSPath -Recurse -Force -ErrorAction Stop; Write-Ok "Removed NotifyIcon $($_.PSChildName)" }
                catch { Write-Err "Remove NotifyIcon -> $_"; Bump-Remaining }
            } elseif ($script:Speculative) { Bump-Remaining }
        }
    }
}

# 6b. MrtCache
$mrt = 'HKCU:\Software\Classes\Local Settings\MrtCache'
if (Test-Path $mrt) {
    Get-ChildItem -Path $mrt -Recurse -ErrorAction SilentlyContinue | Where-Object { $_.Name -match $PackageInPathPattern } | ForEach-Object {
        Write-Action "Reg $($_.Name)"
        if ($script:WriteMode) {
            try { Remove-Item -Path "Registry::$($_.Name)" -Recurse -Force -ErrorAction Stop; Write-Ok "Removed MrtCache" }
            catch { Write-Err "Remove MrtCache -> $_"; Bump-Remaining }
        } elseif ($script:Speculative) { Bump-Remaining }
    }
}

# 6c. IE LowRegistry Audio PolicyConfig PropertyStore
$audio = 'HKCU:\Software\Microsoft\Internet Explorer\LowRegistry\Audio\PolicyConfig\PropertyStore'
if (Test-Path $audio) {
    Get-ChildItem -Path $audio -ErrorAction SilentlyContinue | ForEach-Object {
        $def = (Get-ItemProperty -Path $_.PSPath -Name '(Default)' -ErrorAction SilentlyContinue).'(Default)'
        if ($def -and ($def -match 'Codex\.exe' -or $def -match $PackageInPathPattern)) {
            Write-Action "Reg HKCU IE Audio PropertyStore\$($_.PSChildName)"
            if ($script:WriteMode) {
                try { Remove-Item -Path $_.PSPath -Recurse -Force -ErrorAction Stop; Write-Ok "Removed audio policy entry" }
                catch { Write-Err "Remove audio policy -> $_"; Bump-Remaining }
            } elseif ($script:Speculative) { Bump-Remaining }
        }
    }
}

# 6d. RegisteredApplications
$ra = 'HKCU:\Software\RegisteredApplications'
if (Test-Path $ra) {
    $props = Get-ItemProperty -Path $ra -ErrorAction SilentlyContinue
    if ($props) {
        $props.PSObject.Properties | Where-Object { $_.Name -notmatch '^PS' -and $_.Value -match $PackageInPathPattern } | ForEach-Object {
            Write-Action "Reg HKCU\Software\RegisteredApplications!$($_.Name) = $($_.Value)"
            if ($script:WriteMode) {
                try { Remove-ItemProperty -Path $ra -Name $_.Name -Force -ErrorAction Stop; Write-Ok "Removed RegApp $($_.Name)" }
                catch { Write-Err "Remove RegApp -> $_"; Bump-Remaining }
            } elseif ($script:Speculative) { Bump-Remaining }
        }
    }
}

# ============================================================================
# PHASE 7 - HKLM cleanup (TrustedInstaller-protected)
# ============================================================================
Write-Section "7. HKLM cleanup"

if (-not $KeepCaches) {
    Stop-ServiceSafe -Name 'WSearch'
    Stop-ServiceSafe -Name 'StateRepository'
    if ($script:WriteMode) { Start-Sleep -Seconds 2 }
}

# 7a. Windows Search indexer
$searchBases = @(
  'SOFTWARE\Microsoft\Windows Search\CrawlScopeManager\Windows\SystemIndex\WorkingSetRules',
  'SOFTWARE\Microsoft\Windows Search\Gather\Windows\SystemIndex\Sites\LocalHost\Paths',
  'SOFTWARE\WOW6432Node\Microsoft\Windows Search\CrawlScopeManager\Windows\SystemIndex\WorkingSetRules',
  'SOFTWARE\WOW6432Node\Microsoft\Windows Search\Gather\Windows\SystemIndex\Sites\LocalHost\Paths'
)
foreach ($base in $searchBases) {
    $psPath = "Registry::HKEY_LOCAL_MACHINE\$base"
    if (-not (Test-Path $psPath)) { continue }
    Get-ChildItem -Path $psPath -ErrorAction SilentlyContinue | ForEach-Object {
        $blob = (Get-ItemProperty -Path $_.PSPath -ErrorAction SilentlyContinue | Out-String)
        if ($blob -match '[Cc]odex') {
            $sub = "$base\$($_.PSChildName)"
            Write-Action "Reg HKLM\$sub"
            if ($script:WriteMode) {
                [void](Take-RegKeyOwnership -Hive LocalMachine -SubKey $sub)
                if (-not (Remove-RegKeyTree -Hive LocalMachine -SubKey $sub)) { Bump-Remaining }
                else { Write-Ok "Deleted $sub" }
            } elseif ($script:Speculative) { Bump-Remaining }
        }
    }
}

# 7b. AppModel StateRepository cache
if (-not $KeepCaches) {
    $srBases = @(
      'SOFTWARE\Microsoft\Windows\CurrentVersion\AppModel\StateRepository\Cache\Activation\Data',
      'SOFTWARE\Microsoft\Windows\CurrentVersion\AppModel\StateRepository\Cache\PackageFamily\Data'
    )
    foreach ($base in $srBases) {
        $psPath = "Registry::HKEY_LOCAL_MACHINE\$base"
        if (-not (Test-Path $psPath)) { continue }
        Get-ChildItem -Path $psPath -ErrorAction SilentlyContinue | ForEach-Object {
            $blob = (Get-ItemProperty -Path $_.PSPath -ErrorAction SilentlyContinue | Out-String)
            # Match either the full package name OR Codex.exe activation entries
            if ($blob -match $PackageInPathPattern -or $blob -match 'Codex\.exe') {
                $sub = "$base\$($_.PSChildName)"
                Write-Action "Reg HKLM\$sub"
                if ($script:WriteMode) {
                    [void](Take-RegKeyOwnership -Hive LocalMachine -SubKey $sub)
                    if (-not (Remove-RegKeyTree -Hive LocalMachine -SubKey $sub)) { Bump-Remaining }
                    else { Write-Ok "Deleted $sub" }
                } elseif ($script:Speculative) { Bump-Remaining }
            }
        }
    }
} else { Write-Skip "KeepCaches: not touching StateRepository." }

# 7c. InstallService CategoryCache (Store install records)
$ccPath = 'HKLM:\SOFTWARE\Microsoft\Windows\CurrentVersion\InstallService\State\CategoryCache'
if (Test-Path $ccPath) {
    $props = Get-ItemProperty -Path $ccPath -ErrorAction SilentlyContinue
    if ($props) {
        $props.PSObject.Properties | Where-Object { $_.Name -notmatch '^PS' -and $_.Value -match $PackageInPathPattern } | ForEach-Object {
            Write-Action "Reg InstallService CategoryCache!$($_.Name)"
            if ($script:WriteMode) {
                Remove-RegValue -PSPath $ccPath -Name $_.Name
                Write-Ok "Removed CategoryCache $($_.Name)"
            } elseif ($script:Speculative) { Bump-Remaining }
        }
    }
}

# 7d. FirewallPolicy registry leftovers (rules whose data references codex)
$fwBases = @(
  'SYSTEM\CurrentControlSet\Services\SharedAccess\Parameters\FirewallPolicy\FirewallRules',
  'SYSTEM\ControlSet001\Services\SharedAccess\Parameters\FirewallPolicy\FirewallRules'
)
foreach ($base in $fwBases) {
    $psPath = "Registry::HKEY_LOCAL_MACHINE\$base"
    if (-not (Test-Path $psPath)) { continue }
    $props = Get-ItemProperty -Path $psPath -ErrorAction SilentlyContinue
    if ($props) {
        $props.PSObject.Properties | Where-Object { $_.Name -notmatch '^PS' -and $_.Value -match 'codex_sandbox' } | ForEach-Object {
            Write-Action "Reg HKLM\$base!$($_.Name)"
            if ($script:WriteMode) {
                Remove-RegValue -PSPath $psPath -Name $_.Name
                Write-Ok "Removed FirewallRules $($_.Name)"
            } elseif ($script:Speculative) { Bump-Remaining }
        }
    }
}

if (-not $KeepCaches) {
    Start-ServiceSafe -Name 'StateRepository'
    Start-ServiceSafe -Name 'WSearch'
}

# ============================================================================
# PHASE 8 - Post-nuke sanitation (Microsoft Store reset)
# ============================================================================
# WHY THIS EXISTS:
# After a full Nuke, Microsoft Store sometimes keeps a stale in-memory view
# of the package (we cleared its on-disk caches, but the Store process and
# its data-tier database can still hold a "this is installed" belief).
# When the user clicks Install, Store tries to launch the now-deleted
# Codex.exe instead of downloading fresh files, producing the
# "Can't find C:\Program Files\WindowsApps\...\Codex.exe" error.
#
# wsreset.exe is the official cure: it restarts the Store, flushes its
# cache database, and forces a re-sync with the Store servers on next
# launch. Without this, a clean reinstall may require a Windows reboot.
Write-Section "8. Post-nuke sanitation (Store reset)"
if ($SkipStoreReset) {
    Write-Skip "-SkipStoreReset set."
} elseif (-not $script:WriteMode) {
    Write-Skip "Sanitation only runs in Nuke mode."
} else {
    Write-Action "Running wsreset.exe (clears Store cache, restarts Store service)"
    try {
        $proc = Start-Process -FilePath 'wsreset.exe' -WindowStyle Hidden -PassThru -ErrorAction Stop
        # wsreset normally opens the Store window once finished. We don't
        # want to block forever waiting for the user to close it, so cap
        # the wait at 20 seconds and then move on.
        if (-not $proc.WaitForExit(20000)) {
            Write-Ok "wsreset launched (running in background)"
        } else {
            Write-Ok "wsreset completed (exit $($proc.ExitCode))"
        }
    } catch {
        Write-Err "wsreset failed: $_"
    }

    # NOTE: We intentionally do NOT Restart-Service AppXSvc / ClipSVC /
    # StateRepository here.
    # - AppXSvc is a Trigger-Start service protected by Windows (SCM
    #   refuses Stop with "stop failed" - terminating error in PS7 that
    #   has aborted scripts in testing).
    # - wsreset above already bounces the Store-relevant in-memory state.
    # - Windows will re-spin these services automatically on the next
    #   Store / AppX operation. No manual restart needed.
    Write-Skip "Skipping service restarts (wsreset already cycled Store state)."
}

# ============================================================================
# PHASE 9 - Final audit
# ============================================================================
Write-Section "9. Final audit"

$auditCount = 0
$auditBreakdown = [ordered]@{}

function Audit-Bump([string]$Category, [int]$Count) {
    if ($Count -le 0) { return }
    $auditBreakdown[$Category] = ($auditBreakdown[$Category] + $Count)
    $script:auditCountRef.Value += $Count
}
# PowerShell closures over $auditCount don't work; use a [ref]
$script:auditCountRef = [ref]0

# 1. Appx (per-user + AllUsers)
$apx = if ($IsAdmin) {
    Get-AppxPackage -AllUsers -ErrorAction SilentlyContinue | Where-Object { $_.Name -match $PackageNamePattern }
} else {
    Get-AppxPackage -ErrorAction SilentlyContinue | Where-Object { $_.Name -match $PackageNamePattern }
}
Audit-Bump 'Appx package'                  @($apx).Count

# 2. Sandbox users + their profile folders + ProfileList reg entries
Audit-Bump 'Sandbox local user'            @(Get-LocalUser -ErrorAction SilentlyContinue | Where-Object { $_.Name -match $UserNamePattern }).Count
Audit-Bump 'Sandbox profile folder'        @(Get-ChildItem 'C:\Users' -Force -ErrorAction SilentlyContinue | Where-Object { $_.Name -match $UserNamePattern }).Count
$profileListHits = 0
foreach ($plBase in @(
    'HKLM:\SOFTWARE\Microsoft\Windows NT\CurrentVersion\ProfileList',
    'HKLM:\SOFTWARE\WOW6432Node\Microsoft\Windows NT\CurrentVersion\ProfileList'
)) {
    if (-not (Test-Path $plBase)) { continue }
    Get-ChildItem -Path $plBase -ErrorAction SilentlyContinue | ForEach-Object {
        $img = (Get-ItemProperty -Path $_.PSPath -Name ProfileImagePath -ErrorAction SilentlyContinue).ProfileImagePath
        if ($img -and ($img -match $UserNamePattern)) { $profileListHits++ }
    }
}
Audit-Bump 'ProfileList reg'               $profileListHits

# 3. Firewall rules
Audit-Bump 'Firewall rule'                 @(Get-NetFirewallRule -ErrorAction SilentlyContinue | Where-Object { $_.Name -match $FirewallRulePattern -or $_.DisplayName -match $FirewallRulePattern }).Count

# 4. User-profile folders
foreach ($u in (Get-ChildItem 'C:\Users' -Directory -Force -ErrorAction SilentlyContinue)) {
    $auditFolders = if ($KeepCliState) {
        @('Codex_Cache_Quarantine','Codex_Nuclear_Quarantine','AppData\Local\OpenAI\Codex')
    } else {
        @('.codex','Codex_Cache_Quarantine','Codex_Nuclear_Quarantine','AppData\Local\OpenAI\Codex')
    }
    foreach ($f in $auditFolders) {
        if (Test-PathQuiet (Join-Path $u.FullName $f)) {
            Audit-Bump 'User profile folder' 1
        }
    }
    # Per-package Packages\OpenAI.Codex_*
    $pkgsDir = Join-Path $u.FullName 'AppData\Local\Packages'
    if (Test-Path -LiteralPath $pkgsDir) {
        $matches = Get-ChildItem -LiteralPath $pkgsDir -Directory -Force -ErrorAction SilentlyContinue |
            Where-Object { $_.Name -match $PackageNamePattern }
        Audit-Bump 'Packages\OpenAI.Codex_* folder' @($matches).Count
    }
}

# 5. HKCU residue (NotifyIconSettings / MrtCache / IE audio / RegisteredApplications)
$nis = 'HKCU:\Control Panel\NotifyIconSettings'
if (Test-Path $nis) {
    $nisHits = 0
    Get-ChildItem -Path $nis -ErrorAction SilentlyContinue | ForEach-Object {
        $v = (Get-ItemProperty -Path $_.PSPath -Name ExecutablePath -ErrorAction SilentlyContinue).ExecutablePath
        if ($v -and $v -match $PackageInPathPattern) { $nisHits++ }
    }
    Audit-Bump 'HKCU NotifyIconSettings'    $nisHits
}
$mrt = 'HKCU:\Software\Classes\Local Settings\MrtCache'
if (Test-Path $mrt) {
    $mrtHits = @(Get-ChildItem -Path $mrt -Recurse -ErrorAction SilentlyContinue | Where-Object { $_.Name -match $PackageInPathPattern }).Count
    Audit-Bump 'HKCU MrtCache'              $mrtHits
}
$audio = 'HKCU:\Software\Microsoft\Internet Explorer\LowRegistry\Audio\PolicyConfig\PropertyStore'
if (Test-Path $audio) {
    $audioHits = 0
    Get-ChildItem -Path $audio -ErrorAction SilentlyContinue | ForEach-Object {
        $def = (Get-ItemProperty -Path $_.PSPath -Name '(Default)' -ErrorAction SilentlyContinue).'(Default)'
        if ($def -and ($def -match 'Codex\.exe' -or $def -match $PackageInPathPattern)) { $audioHits++ }
    }
    Audit-Bump 'HKCU IE audio policy'       $audioHits
}
$ra = 'HKCU:\Software\RegisteredApplications'
if (Test-Path $ra) {
    $raProps = Get-ItemProperty -Path $ra -ErrorAction SilentlyContinue
    if ($raProps) {
        $raHits = @($raProps.PSObject.Properties | Where-Object { $_.Name -notmatch '^PS' -and $_.Value -match $PackageInPathPattern }).Count
        Audit-Bump 'HKCU RegisteredApplications' $raHits
    }
}

# 6. HKLM residue (Windows Search, StateRepository, InstallService, FirewallPolicy)
$searchBases = @(
  'HKLM:\SOFTWARE\Microsoft\Windows Search\CrawlScopeManager\Windows\SystemIndex\WorkingSetRules',
  'HKLM:\SOFTWARE\Microsoft\Windows Search\Gather\Windows\SystemIndex\Sites\LocalHost\Paths',
  'HKLM:\SOFTWARE\WOW6432Node\Microsoft\Windows Search\CrawlScopeManager\Windows\SystemIndex\WorkingSetRules',
  'HKLM:\SOFTWARE\WOW6432Node\Microsoft\Windows Search\Gather\Windows\SystemIndex\Sites\LocalHost\Paths'
)
foreach ($base in $searchBases) {
    if (-not (Test-Path $base)) { continue }
    $hits = 0
    Get-ChildItem -Path $base -ErrorAction SilentlyContinue | ForEach-Object {
        $blob = (Get-ItemProperty -Path $_.PSPath -ErrorAction SilentlyContinue | Out-String)
        if ($blob -match '[Cc]odex') { $hits++ }
    }
    Audit-Bump 'HKLM Windows Search rule'   $hits
}
$srBases = @(
  'HKLM:\SOFTWARE\Microsoft\Windows\CurrentVersion\AppModel\StateRepository\Cache\Activation\Data',
  'HKLM:\SOFTWARE\Microsoft\Windows\CurrentVersion\AppModel\StateRepository\Cache\PackageFamily\Data'
)
foreach ($base in $srBases) {
    if (-not (Test-Path $base)) { continue }
    $hits = 0
    Get-ChildItem -Path $base -ErrorAction SilentlyContinue | ForEach-Object {
        $blob = (Get-ItemProperty -Path $_.PSPath -ErrorAction SilentlyContinue | Out-String)
        if ($blob -match $PackageInPathPattern -or $blob -match 'Codex\.exe') { $hits++ }
    }
    Audit-Bump 'HKLM StateRepository cache' $hits
}
$ccPath = 'HKLM:\SOFTWARE\Microsoft\Windows\CurrentVersion\InstallService\State\CategoryCache'
if (Test-Path $ccPath) {
    $ccProps = Get-ItemProperty -Path $ccPath -ErrorAction SilentlyContinue
    if ($ccProps) {
        $ccHits = @($ccProps.PSObject.Properties | Where-Object { $_.Name -notmatch '^PS' -and $_.Value -match $PackageInPathPattern }).Count
        Audit-Bump 'HKLM InstallService CategoryCache' $ccHits
    }
}
$fwBases = @(
  'HKLM:\SYSTEM\CurrentControlSet\Services\SharedAccess\Parameters\FirewallPolicy\FirewallRules',
  'HKLM:\SYSTEM\ControlSet001\Services\SharedAccess\Parameters\FirewallPolicy\FirewallRules'
)
foreach ($base in $fwBases) {
    if (-not (Test-Path $base)) { continue }
    $props = Get-ItemProperty -Path $base -ErrorAction SilentlyContinue
    if ($props) {
        $fwHits = @($props.PSObject.Properties | Where-Object { $_.Name -notmatch '^PS' -and $_.Value -match 'codex_sandbox' }).Count
        Audit-Bump 'HKLM FirewallRules reg'  $fwHits
    }
}

$auditCount = $script:auditCountRef.Value

Write-Host ""
Write-Host "Mode             : $Mode"
Write-Host "Items acted on   : $($script:Remaining)" -ForegroundColor Yellow
$statusColor = if ($script:AuditUnknown) {'Yellow'} elseif ($auditCount -eq 0) {'Green'} else {'Red'}
$statusText  = if ($script:AuditUnknown) {
    "$auditCount confirmed + inconclusive checks (see above)"
} else { "$auditCount" }
Write-Host "Items remaining  : $statusText" -ForegroundColor $statusColor
if ($auditBreakdown.Count -gt 0) {
    Write-Host ""
    Write-Host "  Breakdown:" -ForegroundColor DarkGray
    foreach ($cat in $auditBreakdown.Keys) {
        Write-Host ("    {0,-40} : {1}" -f $cat, $auditBreakdown[$cat]) -ForegroundColor DarkGray
    }
}
Write-Host "Log file         : $LogPath"
if ($script:WriteMode) {
    Write-Host ""
    if ($script:AuditUnknown) {
        Write-Host "STATUS: Clean except provisioned package check failed." -ForegroundColor Yellow
        Write-Host "  Re-run elevated to verify Get-AppxProvisionedPackage state." -ForegroundColor DarkYellow
    } elseif ($auditCount -eq 0) {
        Write-Host "RECOMMENDED: reboot Windows before reinstalling Codex." -ForegroundColor Cyan
        Write-Host "  wsreset cleared the on-disk Store cache, but in-memory state" -ForegroundColor DarkCyan
        Write-Host "  inside AppXSvc / StateRepository / ClipSVC and the Store" -ForegroundColor DarkCyan
        Write-Host "  process can survive a clean session. A reboot guarantees no" -ForegroundColor DarkCyan
        Write-Host "  'ghost install' or stale AppX registration on next install." -ForegroundColor DarkCyan
    } else {
        Write-Host "REBOOT REQUIRED: $auditCount artifact(s) remain. Some are file/reg" -ForegroundColor Yellow
        Write-Host "  locks held by Windows services. Reboot, then re-run -Mode Nuke." -ForegroundColor Yellow
    }
}

try { Stop-Transcript | Out-Null } catch {}

# Exit code conveys remaining-artifact count for the wrapper.
# Wrapper (Nuke.cmd / GUI / installer) decides what UX to show.
if ($script:AuditOnly -or $script:DryRun) {
    $script:FinalExit = $script:Remaining
} else {
    $script:FinalExit = $auditCount
}

Write-Host ""
Write-Host "Exit code: $script:FinalExit" -ForegroundColor $(if ($script:FinalExit -eq 0) {'Green'} else {'Red'})

exit $script:FinalExit
