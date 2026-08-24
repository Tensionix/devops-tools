param(
  [switch]$IncludeSystem = $false
)

# Fonts installed "for me" live in the profile and are registered under HKCU.
# Fonts installed "for everyone" live in C:\Windows\Fonts under HKLM, arrive with
# Windows or with an installer, and are none of this pack's business: it reads
# them only to say how many there are, and never writes to them.

$ErrorActionPreference = "Stop"

function Write-Info($msg) { Write-Host "[INFO] $msg" -ForegroundColor Cyan }
function Write-Warn($msg) { Write-Host "[WARN] $msg" -ForegroundColor Yellow }

$userKey = "HKCU:\Software\Microsoft\Windows NT\CurrentVersion\Fonts"
$systemKey = "HKLM:\SOFTWARE\Microsoft\Windows NT\CurrentVersion\Fonts"
$userFolder = Join-Path $env:LOCALAPPDATA "Microsoft\Windows\Fonts"

Write-Info "User font folder: $userFolder"

$entries = @()
if (Test-Path -LiteralPath $userKey) {
  $properties = (Get-ItemProperty -LiteralPath $userKey).PSObject.Properties |
    Where-Object { $_.Name -notlike "PS*" }
  foreach ($property in $properties) {
    $path = [string]$property.Value
    # A bare file name means the file sits in the well-known font folder.
    if ($path -and -not [System.IO.Path]::IsPathRooted($path)) {
      $path = Join-Path $userFolder $path
    }
    $entries += [pscustomobject]@{
      Name   = $property.Name
      Path   = $path
      Exists = (Test-Path -LiteralPath $path)
    }
  }
}

if (-not $entries) {
  Write-Warn "No fonts are installed for this user."
} else {
  Write-Info ("Fonts installed for this user: {0}" -f $entries.Count)
  foreach ($entry in $entries) {
    $mark = if ($entry.Exists) { "[ OK ]" } else { "[MISS]" }
    Write-Host ("{0} {1,-40} {2}" -f $mark, $entry.Name, $entry.Path)
  }
}

if (Test-Path -LiteralPath $systemKey) {
  $systemCount = ((Get-ItemProperty -LiteralPath $systemKey).PSObject.Properties |
    Where-Object { $_.Name -notlike "PS*" }).Count
  Write-Info "Fonts installed for all users: $systemCount (left untouched)"
  if ($IncludeSystem) {
    (Get-ItemProperty -LiteralPath $systemKey).PSObject.Properties |
      Where-Object { $_.Name -notlike "PS*" } |
      ForEach-Object { Write-Host ("       {0,-40} {1}" -f $_.Name, $_.Value) }
  }
}

exit 0
