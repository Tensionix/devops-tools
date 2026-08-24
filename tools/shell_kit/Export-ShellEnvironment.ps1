param(
  [Parameter(Mandatory = $true)][string]$TargetDir
)

$ErrorActionPreference = "Stop"

. (Join-Path $PSScriptRoot "ShellPaths.ps1")

function Write-Info($msg) { Write-Host "[INFO] $msg" -ForegroundColor Cyan }
function Write-Warn($msg) { Write-Host "[WARN] $msg" -ForegroundColor Yellow }

$filesDir = Join-Path $TargetDir "files"
New-Item -ItemType Directory -Force -Path $filesDir | Out-Null

$carried = @()
foreach ($item in @(Get-ShellEnvironmentItems)) {
  if (-not $item.Exists) { continue }
  # The stored name is the id, not the original file name: three of these are
  # called settings.json and two are called profile.ps1.
  $extension = [System.IO.Path]::GetExtension($item.Path)
  $stored = "$($item.Id)$extension"
  Copy-Item -LiteralPath $item.Path -Destination (Join-Path $filesDir $stored) -Force
  $carried += [pscustomobject]@{
    id     = $item.Id
    title  = $item.Title
    kind   = $item.Kind
    file   = $stored
    source = $item.Path
  }
  Write-Host ("[ OK ] {0,-42} {1}" -f $item.Title, $stored)
}

$map = [pscustomobject]@{
  format  = 1
  created = (Get-Date).ToString("yyyy-MM-dd HH:mm:ss")
  machine = $env:COMPUTERNAME
  user    = $env:USERNAME
  items   = $carried
}
$mapPath = Join-Path $TargetDir "shell_environment.json"
$map | ConvertTo-Json -Depth 5 | Set-Content -LiteralPath $mapPath -Encoding UTF8

Write-Info ("Files carried: {0}" -f $carried.Count)
if ($carried.Count -eq 0) {
  Write-Warn "Nothing was configured on this machine, so nothing was carried."
}
Write-Info "Map written: $mapPath"
exit 0
