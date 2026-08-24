$ErrorActionPreference = "Stop"

. (Join-Path $PSScriptRoot "ShellPaths.ps1")

function Write-Info($msg) { Write-Host "[INFO] $msg" -ForegroundColor Cyan }

$items = @(Get-ShellEnvironmentItems)
$present = @($items | Where-Object { $_.Exists })

foreach ($item in $items) {
  $mark = if ($item.Exists) { "[ OK ]" } else { "[ -- ]" }
  Write-Host ("{0} {1,-42} {2}" -f $mark, $item.Title, $item.Path)
}

Write-Host ""
Write-Info ("Present: {0} of {1}." -f $present.Count, $items.Count)
Write-Info "Absent entries are not a problem: they are simply not configured on this machine."
exit 0
