param(
  [Parameter(Mandatory = $true)][string]$SourceDir
)

# Files go where their id resolves *on this machine*, not where they lived on the
# old one: Documents may be redirected somewhere else here, and the Terminal
# build may be a different flavour. A profile written to a path that this machine
# does not read is the quietest possible failure.

$ErrorActionPreference = "Stop"

. (Join-Path $PSScriptRoot "ShellPaths.ps1")

function Write-Info($msg) { Write-Host "[INFO] $msg" -ForegroundColor Cyan }
function Write-Warn($msg) { Write-Host "[WARN] $msg" -ForegroundColor Yellow }

$mapPath = Join-Path $SourceDir "shell_environment.json"
if (-not (Test-Path -LiteralPath $mapPath)) {
  throw "Shell environment map was not found: $mapPath"
}

$map = Get-Content -LiteralPath $mapPath -Raw -Encoding UTF8 | ConvertFrom-Json
if ([int]$map.format -ne 1) {
  throw "Shell environment map format $($map.format) is not supported."
}

$here = @{}
foreach ($item in @(Get-ShellEnvironmentItems)) { $here[$item.Id] = $item }

$stamp = Get-Date -Format "yyyyMMdd-HHmmss"
$written = 0
$skipped = 0

foreach ($entry in @($map.items)) {
  $stored = Join-Path (Join-Path $SourceDir "files") $entry.file
  if (-not (Test-Path -LiteralPath $stored)) {
    Write-Warn ("Missing in the migration folder: {0}" -f $entry.file)
    $skipped++
    continue
  }
  $target = $here[$entry.id]
  if (-not $target) {
    Write-Warn ("This version does not know where {0} belongs; skipped." -f $entry.id)
    $skipped++
    continue
  }

  $destination = $target.Path
  if (Test-Path -LiteralPath $destination) {
    $same = $false
    try {
      $same = (Get-FileHash -LiteralPath $destination).Hash -eq (Get-FileHash -LiteralPath $stored).Hash
    } catch { $same = $false }
    if ($same) {
      Write-Host ("[SAME] {0,-42} already in place" -f $entry.title)
      $skipped++
      continue
    }
    # What is being replaced is a working file someone edited by hand.
    $spare = "$destination.bak.$stamp"
    Copy-Item -LiteralPath $destination -Destination $spare -Force
    Write-Info "Previous file kept as: $spare"
  }

  New-Item -ItemType Directory -Force -Path (Split-Path -Parent $destination) | Out-Null
  Copy-Item -LiteralPath $stored -Destination $destination -Force
  Write-Host ("[ OK ] {0,-42} {1}" -f $entry.title, $destination)
  $written++
}

Write-Info ("Written: {0}. Already there or skipped: {1}." -f $written, $skipped)
if ($written -gt 0) {
  Write-Info "Open a new shell tab for the profile to take effect."
}
exit 0
