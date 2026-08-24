<# 
Register-All-WSL-VHDX.ps1
Purpose:
- After restoring Windows from an image, re-register all WSL distros stored under ..\VHDX (e.g. X:\WSL\VHDX\Ubuntu\ext4.vhdx)
- Prompts for a distro name per found VHDX (default: parent folder name)

Notes:
- Messages intentionally in English (encoding-safe).
- Safe by default: does NOT unregister existing distros automatically.
- Default Root and LogDir are derived from the Toolkit folder location.
#>

[CmdletBinding()]
param(
  [string]$Root,
  [string]$Filter = 'ext4.vhdx',
  [switch]$DryRun,
  [string]$LogDir
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

$ToolkitDir = Split-Path -Parent $PSCommandPath
$WslRoot = Split-Path -Parent $ToolkitDir

if ([string]::IsNullOrWhiteSpace($Root)) {
  $Root = Join-Path $WslRoot 'VHDX'
}

if ([string]::IsNullOrWhiteSpace($LogDir)) {
  $LogDir = Join-Path $WslRoot 'Logs'
}

function Ensure-Dir([string]$Path) {
  if (-not (Test-Path -LiteralPath $Path)) {
    New-Item -ItemType Directory -Force -Path $Path | Out-Null
  }
}

function Timestamp() {
  return (Get-Date).ToString('yyyyMMdd-HHmmss')
}

if (-not (Test-Path -LiteralPath $Root)) {
  throw "Root not found: $Root"
}

Ensure-Dir $LogDir
$logPath = Join-Path $LogDir ('register-all-' + (Timestamp) + '.log')

"Root: $Root" | Out-File -FilePath $logPath -Encoding utf8
"DryRun: $DryRun" | Out-File -FilePath $logPath -Encoding utf8 -Append
'' | Out-File -FilePath $logPath -Encoding utf8 -Append

Write-Host "Scanning for '$Filter' under: $Root"
$files = Get-ChildItem -LiteralPath $Root -Recurse -File -Filter $Filter -ErrorAction Stop

if (-not $files -or $files.Count -eq 0) {
  Write-Host 'No VHDX files found.'
  'No VHDX files found.' | Out-File -FilePath $logPath -Encoding utf8 -Append
  exit 0
}

$existing = @()
try { $existing = (wsl -l -q) | ForEach-Object { $_.Trim() } | Where-Object { $_ -ne '' } } catch { $existing = @() }

Write-Host ''
Write-Host "Found $($files.Count) VHDX file(s)."
Write-Host "Log: $logPath"
Write-Host ''

try { wsl --shutdown | Out-Null } catch { }

foreach ($f in $files) {
  $path = $f.FullName
  $suggest = $f.Directory.Name

  Write-Host '------------------------------------------------------------'
  Write-Host "VHDX: $path"
  Write-Host "Suggested name: $suggest"
  Write-Host 'Press ENTER to accept suggested.'
  Write-Host 'Type SKIP to skip this VHDX.'
  $name = Read-Host 'Name'

  if ([string]::IsNullOrWhiteSpace($name)) { $name = $suggest }
  if ($name -eq 'SKIP') {
    Write-Host 'Skipped.'
    "SKIP: $path" | Out-File -FilePath $logPath -Encoding utf8 -Append
    continue
  }

  if ($existing -contains $name) {
    Write-Host "Name already exists in WSL: $name"
    Write-Host 'Type NEW to enter another name, or SKIP to skip.'
    $choice = Read-Host 'Choice'
    if ($choice -eq 'SKIP') {
      Write-Host 'Skipped.'
      "SKIP (exists): $name  $path" | Out-File -FilePath $logPath -Encoding utf8 -Append
      continue
    }
    if ($choice -eq 'NEW') {
      $name2 = Read-Host 'NewName'
      if ([string]::IsNullOrWhiteSpace($name2)) {
        Write-Host 'Skipped (empty name).'
        "SKIP (empty new name): $path" | Out-File -FilePath $logPath -Encoding utf8 -Append
        continue
      }
      $name = $name2
      if ($existing -contains $name) {
        Write-Host 'Still exists. Skipping.'
        "SKIP (still exists): $name  $path" | Out-File -FilePath $logPath -Encoding utf8 -Append
        continue
      }
    } else {
      Write-Host 'Skipped.'
      "SKIP (exists default): $name  $path" | Out-File -FilePath $logPath -Encoding utf8 -Append
      continue
    }
  }

  $cmd = "wsl --import-in-place `"$name`" `"$path`""
  Write-Host "Registering: $cmd"
  $cmd | Out-File -FilePath $logPath -Encoding utf8 -Append

  if ($DryRun) {
    Write-Host 'DryRun: not executing.'
    'DRYRUN' | Out-File -FilePath $logPath -Encoding utf8 -Append
    continue
  }

  try {
    wsl --import-in-place $name $path
    Write-Host "OK: $name"
    "OK: $name" | Out-File -FilePath $logPath -Encoding utf8 -Append
    $existing += $name
  } catch {
    Write-Host "FAILED: $name"
    Write-Host $_
    "FAILED: $name" | Out-File -FilePath $logPath -Encoding utf8 -Append
    $_ | Out-File -FilePath $logPath -Encoding utf8 -Append
  }
}

Write-Host ''
Write-Host 'Done. Log saved to:'
Write-Host $logPath
