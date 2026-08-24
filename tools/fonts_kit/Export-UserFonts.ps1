param(
  [Parameter(Mandatory = $true)][string]$TargetDir
)

# Copies the fonts this user installed for themselves, and nothing else. The
# system set stays where it is: it is reinstalled with Windows, and copying it
# into a migration would both bloat the folder and invite a restore that
# overwrites files Windows owns.

$ErrorActionPreference = "Stop"

function Write-Info($msg) { Write-Host "[INFO] $msg" -ForegroundColor Cyan }
function Write-Warn($msg) { Write-Host "[WARN] $msg" -ForegroundColor Yellow }

$userKey = "HKCU:\Software\Microsoft\Windows NT\CurrentVersion\Fonts"
$userFolder = Join-Path $env:LOCALAPPDATA "Microsoft\Windows\Fonts"
$filesDir = Join-Path $TargetDir "files"

New-Item -ItemType Directory -Force -Path $filesDir | Out-Null

$carried = @()
$missing = @()

if (Test-Path -LiteralPath $userKey) {
  $properties = (Get-ItemProperty -LiteralPath $userKey).PSObject.Properties |
    Where-Object { $_.Name -notlike "PS*" }
  foreach ($property in $properties) {
    $path = [string]$property.Value
    if ($path -and -not [System.IO.Path]::IsPathRooted($path)) {
      $path = Join-Path $userFolder $path
    }
    if (-not (Test-Path -LiteralPath $path)) {
      Write-Warn ("Registered but not on disk: {0} -> {1}" -f $property.Name, $path)
      $missing += [pscustomobject]@{ Name = $property.Name; Path = $path }
      continue
    }
    $fileName = Split-Path -Leaf $path
    Copy-Item -LiteralPath $path -Destination (Join-Path $filesDir $fileName) -Force
    $carried += [pscustomobject]@{
      Name   = $property.Name
      File   = $fileName
      Source = $path
    }
    Write-Host ("[ OK ] {0,-40} {1}" -f $property.Name, $fileName)
  }
}

$map = [pscustomobject]@{
  format  = 1
  created = (Get-Date).ToString("yyyy-MM-dd HH:mm:ss")
  machine = $env:COMPUTERNAME
  user    = $env:USERNAME
  fonts   = $carried
  missing = $missing
}
$mapPath = Join-Path $TargetDir "fonts.json"
$map | ConvertTo-Json -Depth 5 | Set-Content -LiteralPath $mapPath -Encoding UTF8

Write-Info ("Fonts carried: {0}" -f $carried.Count)
if ($missing.Count -gt 0) {
  Write-Warn ("Registered but missing on disk: {0}" -f $missing.Count)
}
Write-Info "Map written: $mapPath"
exit 0
