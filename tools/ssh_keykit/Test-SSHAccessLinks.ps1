param(
  [string]$SshConfig = "",

  [string]$RcloneConfig = "",

  [string]$ReportPath = "",

  [switch]$FailOnBroken = $true
)

# Access breaks quietly. Keys stay where they are, configuration files stay
# where they are, and only the paths inside them stop matching reality: a key
# moved to another folder, a proxy client removed, a known_hosts renamed. Every
# file involved still exists, so nothing looks wrong until the first connection
# of the day fails.
#
# This check reads the configuration the way ssh and rclone read it, resolves
# every path it names, and says plainly which ones lead nowhere.

$ErrorActionPreference = "Stop"

function Write-Info($msg) { Write-Host "[INFO] $msg" -ForegroundColor Cyan }
function Write-Warn($msg) { Write-Host "[WARN] $msg" -ForegroundColor Yellow }
function Write-Bad($msg)  { Write-Host "[MISS] $msg" -ForegroundColor Red }
function Write-Good($msg) { Write-Host "[ OK ] $msg" -ForegroundColor Green }

if (-not $SshConfig)    { $SshConfig    = Join-Path $env:USERPROFILE ".ssh\config" }
if (-not $RcloneConfig) { $RcloneConfig = Join-Path $env:APPDATA "rclone\rclone.conf" }

$findings = New-Object System.Collections.Generic.List[object]

function Add-Finding {
  param(
    [string]$Source,
    [string]$Scope,
    [string]$Setting,
    [string]$Path
  )
  # An empty value is not a finding: ssh and rclone both treat it as "use the
  # default", and reporting it as broken would bury the real breakage in noise.
  if (-not $Path) { return }

  # Both spellings are kept. The expanded one answers "is the file there"; the
  # raw one is what the configuration file actually says, and it is the only
  # thing a migration can search for when it rewrites paths for a new machine.
  $raw = $Path.Trim('"').Trim()
  $expanded = [Environment]::ExpandEnvironmentVariables($raw)
  if ($expanded -match '^~[\\/]') {
    $expanded = Join-Path $env:USERPROFILE ($expanded -replace '^~[\\/]', '')
  }

  $exists = $false
  try { $exists = Test-Path -LiteralPath $expanded } catch { $exists = $false }

  $findings.Add([pscustomobject]@{
    Source  = $Source
    Scope   = $Scope
    Setting = $Setting
    Path    = $expanded
    Raw     = $raw
    Exists  = $exists
  })
}

# --- ssh client configuration ------------------------------------------------
# Read per Host block, because a path that is missing matters differently
# depending on which host it belongs to: the operator needs to know what
# exactly stopped being reachable, not that "some key is gone".
if (Test-Path -LiteralPath $SshConfig) {
  Write-Info "ssh config: $SshConfig"
  $host_ = "(global)"
  foreach ($line in Get-Content -LiteralPath $SshConfig -Encoding UTF8) {
    $trimmed = $line.Trim()
    if (-not $trimmed -or $trimmed.StartsWith("#")) { continue }

    if ($trimmed -match '^(?i)Host\s+(.+)$') {
      $host_ = $Matches[1].Trim()
      continue
    }
    if ($trimmed -match '^(?i)(IdentityFile|UserKnownHostsFile|CertificateFile|Include)\s+(.+)$') {
      Add-Finding -Source "ssh" -Scope $host_ -Setting $Matches[1] -Path $Matches[2]
      continue
    }
    # ProxyCommand carries an executable as its first token; the rest are
    # arguments and must not be probed as files.
    if ($trimmed -match '^(?i)ProxyCommand\s+(.+)$') {
      $command = $Matches[1].Trim()
      $exe = if ($command.StartsWith('"')) { ($command -split '"')[1] } else { ($command -split '\s+')[0] }
      Add-Finding -Source "ssh" -Scope $host_ -Setting "ProxyCommand" -Path $exe
    }
  }
} else {
  Write-Warn "ssh config not found: $SshConfig"
}

# --- rclone remotes ----------------------------------------------------------
if (Test-Path -LiteralPath $RcloneConfig) {
  Write-Info "rclone config: $RcloneConfig"
  $remote = "(global)"
  foreach ($line in Get-Content -LiteralPath $RcloneConfig -Encoding UTF8) {
    $trimmed = $line.Trim()
    if (-not $trimmed -or $trimmed.StartsWith("#") -or $trimmed.StartsWith(";")) { continue }

    if ($trimmed -match '^\[(.+)\]$') {
      $remote = $Matches[1].Trim()
      continue
    }
    if ($trimmed -match '^(?i)(key_file|known_hosts_file|pubkey_file|service_account_file)\s*=\s*(.+)$') {
      Add-Finding -Source "rclone" -Scope $remote -Setting $Matches[1] -Path $Matches[2]
    }
  }
} else {
  Write-Warn "rclone config not found: $RcloneConfig"
}

# --- report ------------------------------------------------------------------
Write-Host ""
if ($findings.Count -eq 0) {
  Write-Warn "No path settings found. Nothing to verify."
  exit 0
}

$broken = @($findings | Where-Object { -not $_.Exists })

foreach ($item in $findings) {
  $label = "{0,-7} {1,-22} {2,-20} {3}" -f $item.Source, $item.Scope, $item.Setting, $item.Path
  if ($item.Exists) { Write-Good $label } else { Write-Bad $label }
}

Write-Host ""
Write-Info ("Checked: {0}. Broken: {1}." -f $findings.Count, $broken.Count)

if ($ReportPath) {
  $dir = Split-Path -Parent $ReportPath
  if ($dir -and -not (Test-Path -LiteralPath $dir)) {
    New-Item -ItemType Directory -Force -Path $dir | Out-Null
  }
  $findings | Sort-Object Source, Scope, Setting |
    Export-Csv -LiteralPath $ReportPath -NoTypeInformation -Encoding UTF8
  Write-Info "Report written: $ReportPath"
}

if ($broken.Count -gt 0) {
  Write-Host ""
  Write-Warn "These settings name files that are not there. Until they are fixed,"
  Write-Warn "the affected hosts and remotes will fail on the next connection."
  foreach ($item in $broken) {
    Write-Bad ("{0} / {1}: {2} -> {3}" -f $item.Source, $item.Scope, $item.Setting, $item.Path)
  }
  if ($FailOnBroken) { exit 1 }
}

exit 0
