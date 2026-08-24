param(
  [Parameter(Mandatory=$true)]
  [string]$RootDir,

  [string]$ProfileName = $env:COMPUTERNAME,

  [string]$UserName = $env:USERNAME,

  [switch]$IncludeServerKeys = $true
)

$ErrorActionPreference = "Stop"

function Write-Info($msg) { Write-Host "[INFO] $msg" -ForegroundColor Cyan }
function Write-Warn($msg) { Write-Host "[WARN] $msg" -ForegroundColor Yellow }

function Test-IsAdmin {
  $id = [Security.Principal.WindowsIdentity]::GetCurrent()
  $p  = New-Object Security.Principal.WindowsPrincipal($id)
  return $p.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
}

$timestamp  = Get-Date -Format "yyyyMMdd_HHmmss"
$machineDir = Join-Path $RootDir $ProfileName

$destClientRoot = Join-Path $machineDir "users\$UserName\$timestamp"
$destClient     = Join-Path $destClientRoot "client"

$destServerRoot = Join-Path $machineDir "_server\$timestamp"
$destServer     = $destServerRoot

New-Item -ItemType Directory -Force -Path $destClient | Out-Null
New-Item -ItemType Directory -Force -Path $destServer | Out-Null

Write-Info "Export machine: $ProfileName"
Write-Info "Export user:    $UserName"
Write-Info "Export client:  $destClient"
Write-Info "Export server:  $destServer"

# --- Client keys (.ssh) ---
$userSsh = Join-Path $env:USERPROFILE ".ssh"

if (-not (Test-Path $userSsh)) {
  Write-Warn "Client .ssh folder not found: $userSsh"
} else {
  Write-Info "Exporting client SSH files from: $userSsh"

  $patterns = @(
    "id_*",
    "config",
    "known_hosts*",
    "authorized_keys",
    "*.pub"
  )

  foreach ($pat in $patterns) {
    Get-ChildItem -LiteralPath $userSsh -Filter $pat -File -ErrorAction SilentlyContinue |
      ForEach-Object {
        Copy-Item -LiteralPath $_.FullName -Destination (Join-Path $destClient $_.Name) -Force
      }
  }

  $subDirs = @("config.d")
  foreach ($d in $subDirs) {
    $srcDir = Join-Path $userSsh $d
    if (Test-Path $srcDir) {
      Copy-Item -LiteralPath $srcDir -Destination (Join-Path $destClient $d) -Recurse -Force
    }
  }
}

# --- Server host keys (sshd) ---
if ($IncludeServerKeys) {
  if (-not (Test-IsAdmin)) {
    Write-Warn "Not running as Administrator. Skipping server host keys export."
  } else {
    $serverSsh = Join-Path $env:ProgramData "ssh"
    if (-not (Test-Path $serverSsh)) {
      Write-Warn "Server ssh folder not found: $serverSsh"
    } else {
      Write-Info "Exporting server host keys from: $serverSsh"

      Get-ChildItem -LiteralPath $serverSsh -Filter "ssh_host_*" -File -ErrorAction SilentlyContinue |
        ForEach-Object {
          Copy-Item -LiteralPath $_.FullName -Destination (Join-Path $destServer $_.Name) -Force
        }

      $sshdConfig = Join-Path $serverSsh "sshd_config"
      if (Test-Path $sshdConfig) {
        Copy-Item -LiteralPath $sshdConfig -Destination (Join-Path $destServer "sshd_config") -Force
      }
    }
  }
}

Write-Info "Done."
