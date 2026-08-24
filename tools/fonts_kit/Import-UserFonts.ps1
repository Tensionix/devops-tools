param(
  [Parameter(Mandatory = $true)][string]$SourceDir
)

# Installs fonts the way "Install for me" does: the file goes into the profile's
# font folder and a value goes under HKCU. No elevation, no writes to
# C:\Windows\Fonts, no HKLM — a per-user install cannot damage the system set.
#
# Copying the file and writing the registry value is enough for the next program
# start; running programs only learn about a new font from WM_FONTCHANGE, so the
# broadcast at the end is what makes the font appear without signing out.

$ErrorActionPreference = "Stop"

function Write-Info($msg) { Write-Host "[INFO] $msg" -ForegroundColor Cyan }
function Write-Warn($msg) { Write-Host "[WARN] $msg" -ForegroundColor Yellow }

$mapPath = Join-Path $SourceDir "fonts.json"
if (-not (Test-Path -LiteralPath $mapPath)) {
  throw "Font map was not found: $mapPath"
}

$map = Get-Content -LiteralPath $mapPath -Raw -Encoding UTF8 | ConvertFrom-Json
if ([int]$map.format -ne 1) {
  throw "Font map format $($map.format) is not supported."
}

$userKey = "HKCU:\Software\Microsoft\Windows NT\CurrentVersion\Fonts"
$userFolder = Join-Path $env:LOCALAPPDATA "Microsoft\Windows\Fonts"
New-Item -ItemType Directory -Force -Path $userFolder | Out-Null
if (-not (Test-Path -LiteralPath $userKey)) {
  New-Item -Path $userKey -Force | Out-Null
}

Add-Type -Name Fonts -Namespace Win32 -MemberDefinition @'
[DllImport("gdi32.dll", CharSet = CharSet.Unicode, SetLastError = true)]
public static extern int AddFontResourceW(string fileName);

[DllImport("user32.dll", SetLastError = true)]
public static extern IntPtr SendMessageTimeout(IntPtr hWnd, uint msg, IntPtr wParam, IntPtr lParam, uint flags, uint timeout, out IntPtr result);
'@

$installed = 0
$skipped = 0
foreach ($font in @($map.fonts)) {
  $stored = Join-Path (Join-Path $SourceDir "files") $font.File
  if (-not (Test-Path -LiteralPath $stored)) {
    Write-Warn ("Missing in the migration folder: {0}" -f $font.File)
    $skipped++
    continue
  }

  $target = Join-Path $userFolder $font.File
  $current = (Get-ItemProperty -LiteralPath $userKey -Name $font.Name -ErrorAction SilentlyContinue).($font.Name)
  if ($current -and (Test-Path -LiteralPath $target)) {
    $sameFile = $false
    try {
      $sameFile = (Get-FileHash -LiteralPath $target).Hash -eq (Get-FileHash -LiteralPath $stored).Hash
    } catch { $sameFile = $false }
    if ($sameFile) {
      Write-Host ("[SAME] {0,-40} already installed" -f $font.Name)
      $skipped++
      continue
    }
  }

  Copy-Item -LiteralPath $stored -Destination $target -Force
  New-ItemProperty -LiteralPath $userKey -Name $font.Name -Value $target -PropertyType String -Force | Out-Null
  [Win32.Fonts]::AddFontResourceW($target) | Out-Null
  Write-Host ("[ OK ] {0,-40} {1}" -f $font.Name, $font.File)
  $installed++
}

if ($installed -gt 0) {
  $result = [IntPtr]::Zero
  # HWND_BROADCAST, WM_FONTCHANGE, SMTO_ABORTIFHUNG
  [Win32.Fonts]::SendMessageTimeout([IntPtr]0xFFFF, 0x001D, [IntPtr]::Zero, [IntPtr]::Zero, 2, 1000, [ref]$result) | Out-Null
  Write-Info "Running programs were told about the new fonts."
}

Write-Info ("Installed: {0}. Already there or missing: {1}." -f $installed, $skipped)
Write-Info "System fonts were not touched."
exit 0
