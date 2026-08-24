<# 
Audion-WSL-Toolkit.ps1
Actions: list, status, shutdown, terminate, backup, clone, rename, move, delete, importinplace, restorefrombackup

Notes:
- Output/messages intentionally in English (encoding-safe).
- Most actions do NOT require Administrator. Installation does.
- Default paths are derived from the Toolkit folder location.
#>

[CmdletBinding()]
param(
  [Parameter(Position=0)]
  [ValidateSet('list','status','shutdown','terminate','backup','clone','rename','move','delete','importinplace','restorefrombackup')]
  [string]$Action = 'list',

  [Parameter()]
  [string]$Name,

  [Parameter()]
  [string]$NewName,

  [Parameter()]
  [string]$Location,

  [Parameter()]
  [string]$VhdxPath,

  [Parameter()]
  [string]$BackupFile,

  [Parameter()]
  [string]$BackupDir,

  [Parameter()]
  [ValidateSet('tar','vhd')]
  [string]$Format = 'tar',

  [Parameter()]
  [switch]$Force
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

$ToolkitDir = Split-Path -Parent $PSCommandPath
$WslRoot = Split-Path -Parent $ToolkitDir

if ([string]::IsNullOrWhiteSpace($BackupDir)) {
  $BackupDir = Join-Path $WslRoot 'Backup'
}

function Ensure-Dir([string]$Path) {
  if ([string]::IsNullOrWhiteSpace($Path)) { throw "Path is empty." }
  if (-not (Test-Path -LiteralPath $Path)) {
    New-Item -ItemType Directory -Force -Path $Path | Out-Null
  }
}

function Require([string]$Value, [string]$ParamName) {
  if ([string]::IsNullOrWhiteSpace($Value)) { throw "$ParamName is required for action '$Action'." }
}

function Confirm([string]$Message) {
  if ($Force) { return }
  $answer = Read-Host "$Message  Type YES to continue"
  if ($answer -ne 'YES') { throw "Cancelled." }
}

function Timestamp() {
  return (Get-Date).ToString("yyyyMMdd-HHmmss")
}

switch ($Action) {
  'list' { wsl --list --verbose; break }
  'status' { wsl --status; break }
  'shutdown' { wsl --shutdown; break }

  'terminate' {
    Require $Name 'Name'
    try { wsl --terminate $Name | Out-Null } catch { }
    Write-Host "Done."
    break
  }

  'backup' {
    Require $Name 'Name'
    Ensure-Dir $BackupDir

    $ts = Timestamp
    $ext = if ($Format -eq 'vhd') { 'vhdx' } else { 'tar' }
    $outDir = Join-Path $BackupDir $Name
    Ensure-Dir $outDir
    $outFile = Join-Path $outDir "$Name`_$ts.$ext"

    try { wsl --terminate $Name | Out-Null } catch { }

    if ($Format -eq 'vhd') {
      wsl --export $Name $outFile --vhd
    } else {
      wsl --export $Name $outFile
    }

    Write-Host "Backup created:"
    Write-Host $outFile
    break
  }

  'clone' {
    Require $Name 'Name'
    Require $NewName 'NewName'
    Require $Location 'Location'
    Ensure-Dir $BackupDir
    Ensure-Dir $Location

    $ts = Timestamp
    $tmpTarDir = Join-Path $BackupDir '_temp'
    Ensure-Dir $tmpTarDir
    $tmpTar = Join-Path $tmpTarDir "$Name`_$ts.tar"

    try { wsl --terminate $Name | Out-Null } catch { }

    wsl --export $Name $tmpTar
    wsl --import $NewName $Location $tmpTar --version 2

    Write-Host "Cloned '$Name' -> '$NewName'"
    Write-Host "Install location: $Location"
    Write-Host "Export file: $tmpTar"
    break
  }

  'rename' {
    Require $Name 'Name'
    Require $NewName 'NewName'
    Require $Location 'Location'
    Ensure-Dir $BackupDir
    Ensure-Dir $Location

    Confirm "This will create '$NewName' and permanently unregister '$Name'."

    $ts = Timestamp
    $tmpTarDir = Join-Path $BackupDir '_temp'
    Ensure-Dir $tmpTarDir
    $tmpTar = Join-Path $tmpTarDir "$Name`_$ts.tar"

    try { wsl --terminate $Name | Out-Null } catch { }

    wsl --export $Name $tmpTar
    wsl --import $NewName $Location $tmpTar --version 2
    wsl --unregister $Name

    Write-Host "Renamed '$Name' -> '$NewName'"
    Write-Host "Install location: $Location"
    break
  }

  'move' {
    Require $Name 'Name'
    Require $Location 'Location'
    Ensure-Dir $BackupDir
    Ensure-Dir $Location

    Confirm "This will move '$Name' to '$Location' via export/import."

    $ts = Timestamp
    $tmpTarDir = Join-Path $BackupDir '_temp'
    Ensure-Dir $tmpTarDir
    $tmpTar = Join-Path $tmpTarDir "$Name`_$ts.tar"

    try { wsl --terminate $Name | Out-Null } catch { }

    wsl --export $Name $tmpTar
    wsl --unregister $Name
    wsl --import $Name $Location $tmpTar --version 2

    Write-Host "Moved '$Name' to: $Location"
    Write-Host "Export file: $tmpTar"
    break
  }

  'importinplace' {
    Require $Name 'Name'
    Require $VhdxPath 'VhdxPath'

    if (-not (Test-Path -LiteralPath $VhdxPath)) { throw "VHDX not found: $VhdxPath" }

    try { wsl --shutdown | Out-Null } catch { }
    wsl --import-in-place $Name $VhdxPath

    Write-Host "Imported in place:"
    Write-Host "Name: $Name"
    Write-Host "VHDX: $VhdxPath"
    break
  }

  'restorefrombackup' {
    Require $Name 'Name'
    Require $Location 'Location'
    Require $BackupFile 'BackupFile'

    if (-not (Test-Path -LiteralPath $BackupFile)) { throw "Backup file not found: $BackupFile" }
    Ensure-Dir $Location

    $ext = [System.IO.Path]::GetExtension($BackupFile).ToLowerInvariant()
    $isVhd = ($ext -eq '.vhd' -or $ext -eq '.vhdx')

    try { wsl --shutdown | Out-Null } catch { }

    if ($isVhd) {
      wsl --import $Name $Location $BackupFile --vhd
    } else {
      wsl --import $Name $Location $BackupFile --version 2
    }

    Write-Host "Restored distro from backup:"
    Write-Host "Name: $Name"
    Write-Host "Location: $Location"
    Write-Host "Backup: $BackupFile"
    break
  }

  'delete' {
    Require $Name 'Name'
    Confirm "This will permanently delete the WSL distribution '$Name'."

    try { wsl --terminate $Name | Out-Null } catch { }
    wsl --unregister $Name

    Write-Host "Deleted: $Name"
    break
  }
}
