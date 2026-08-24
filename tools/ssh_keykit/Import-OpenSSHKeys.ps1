param(
  [Parameter(Mandatory=$true)]
  [string]$RootDir,

  [string]$ProfileName = $env:COMPUTERNAME,

  [string]$UserName = $env:USERNAME,

  [string]$Snapshot = "",

  [switch]$ImportServerKeys = $true
)

$ErrorActionPreference = "Stop"

function Write-Info($msg) { Write-Host "[INFO] $msg" -ForegroundColor Cyan }
function Write-Warn($msg) { Write-Host "[WARN] $msg" -ForegroundColor Yellow }

function Test-IsAdmin {
  $id = [Security.Principal.WindowsIdentity]::GetCurrent()
  $p  = New-Object Security.Principal.WindowsPrincipal($id)
  return $p.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
}

function Get-LatestSnapshot($base) {
  if (-not (Test-Path $base)) { return "" }
  $dirs = Get-ChildItem -LiteralPath $base -Directory | Sort-Object Name -Descending
  if ($dirs.Count -eq 0) { return "" }
  return $dirs[0].Name
}

function Ensure-Dir($path) {
  if (-not (Test-Path $path)) { New-Item -ItemType Directory -Force -Path $path | Out-Null }
}

function Backup-Dir($path) {
  if (Test-Path $path) {
    $stamp = Get-Date -Format "yyyyMMdd_HHmmss"
    $bak = "$path.bak.$stamp"
    Copy-Item -LiteralPath $path -Destination $bak -Recurse -Force
    Write-Info "Backup created: $bak"
  }
}

function Set-ClientKeyAcl($filePath) {
  $user = "$env:USERDOMAIN\$env:USERNAME"
  & icacls $filePath /inheritance:r | Out-Null
  & icacls $filePath /grant:r "${user}:(F)" "SYSTEM:(F)" "Administrators:(F)" | Out-Null
}

function Set-ServerHostKeyAcl($filePath) {
  & icacls $filePath /inheritance:r | Out-Null
  & icacls $filePath /grant:r "SYSTEM:(F)" "Administrators:(F)" | Out-Null
}

$machineDir = Join-Path $RootDir $ProfileName

$userSnapshotsRoot = Join-Path $machineDir "users\$UserName"
$serverSnapshotsRoot = Join-Path $machineDir "_server"

if (-not $Snapshot) {
  $Snapshot = Get-LatestSnapshot $userSnapshotsRoot
  if (-not $Snapshot) {
    throw "No user snapshots found in: $userSnapshotsRoot"
  }
}

$srcUser = Join-Path $userSnapshotsRoot $Snapshot
$srcClient = Join-Path $srcUser "client"

if (-not (Test-Path $srcClient)) {
  throw "Client snapshot not found: $srcClient"
}

Write-Info "Import machine: $ProfileName"
Write-Info "Import user:    $UserName"
Write-Info "Import snapshot: $Snapshot"

# --- Import client files (.ssh) ---
$userSsh = Join-Path $env:USERPROFILE ".ssh"
Ensure-Dir $userSsh
Backup-Dir $userSsh

Write-Info "Importing client SSH files into: $userSsh"
Copy-Item -LiteralPath (Join-Path $srcClient "*") -Destination $userSsh -Recurse -Force

Get-ChildItem -LiteralPath $userSsh -File -Filter "id_*" -ErrorAction SilentlyContinue |
  Where-Object { $_.Name -notlike "*.pub" } |
  ForEach-Object { Set-ClientKeyAcl $_.FullName }

Write-Info "Client import done."

# --- Import server host keys ---
if ($ImportServerKeys) {
  if (-not (Test-IsAdmin)) {
    Write-Warn "Not running as Administrator. Skipping server host keys import."
  } else {
    $serverSsh = Join-Path $env:ProgramData "ssh"
    Ensure-Dir $serverSsh

    $serverSnapToUse = $Snapshot
    $srcServer = Join-Path $serverSnapshotsRoot $serverSnapToUse

    if (-not (Test-Path $srcServer)) {
      $serverSnapToUse = Get-LatestSnapshot $serverSnapshotsRoot
      if ($serverSnapToUse) {
        $srcServer = Join-Path $serverSnapshotsRoot $serverSnapToUse
        Write-Warn "Matching server snapshot not found. Using latest server snapshot: $serverSnapToUse"
      } else {
        Write-Warn "No server snapshots found in: $serverSnapshotsRoot"
        $srcServer = ""
      }
    }

    if ($srcServer) {
      Write-Info "Stopping sshd (if running)..."
      try { Stop-Service sshd -ErrorAction SilentlyContinue } catch {}

      Write-Info "Importing server host keys into: $serverSsh"
      Get-ChildItem -LiteralPath $srcServer -Filter "ssh_host_*" -File -ErrorAction SilentlyContinue |
        ForEach-Object {
          $dstFile = Join-Path $serverSsh $_.Name
          Copy-Item -LiteralPath $_.FullName -Destination $dstFile -Force
          Set-ServerHostKeyAcl $dstFile
        }

      $sshdCfgSrc = Join-Path $srcServer "sshd_config"
      if (Test-Path $sshdCfgSrc) {
        Copy-Item -LiteralPath $sshdCfgSrc -Destination (Join-Path $serverSsh "sshd_config") -Force
      }

      Write-Info "Starting sshd..."
      try {
        Start-Service sshd
        Set-Service -Name sshd -StartupType Automatic
      } catch {
        Write-Warn "Failed to start sshd. You may need to install OpenSSH Server or check logs."
      }

      Write-Info "Server import done."
    }
  }
}

Write-Info "All done."
