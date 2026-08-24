# Saves Driver Store manifests and optionally prints pnputil output to console.

[CmdletBinding()]
param(
    [switch]$Show,
    [string]$OutputRoot
)

$ErrorActionPreference = 'Continue'
try { $PSNativeCommandUseErrorActionPreference = $false } catch { }

function Write-TextFileUtf8 {
    param(
        [Parameter(Mandatory=$true)][string]$Path,
        [AllowNull()][string]$Text
    )
    if ($null -eq $Text) { $Text = '' }
    $utf8NoBom = [System.Text.UTF8Encoding]::new($false)
    [System.IO.File]::WriteAllText($Path, $Text, $utf8NoBom)
}

function Save-CommandOutput {
    param(
        [Parameter(Mandatory=$true)][string]$Path,
        [Parameter(Mandatory=$true)][scriptblock]$Command
    )
    try {
        $output = & $Command 2>&1 | Out-String -Width 4096
        Write-TextFileUtf8 -Path $Path -Text $output
        return $output
    } catch {
        $msg = "ERROR: {0}" -f $_.Exception.Message
        Write-TextFileUtf8 -Path $Path -Text $msg
        return $msg
    }
}

function Get-WindowsAnsiEncoding {
    try {
        [System.Text.Encoding]::RegisterProvider([System.Text.CodePagesEncodingProvider]::Instance)
    } catch { }
    try {
        return [System.Text.Encoding]::GetEncoding([System.Globalization.CultureInfo]::CurrentCulture.TextInfo.ANSICodePage)
    } catch {
        return [Console]::OutputEncoding
    }
}

function Invoke-NativeText {
    param(
        [Parameter(Mandatory=$true)][string]$FilePath,
        [AllowNull()][string]$Arguments
    )
    $psi = [System.Diagnostics.ProcessStartInfo]::new()
    $psi.FileName = $FilePath
    $psi.Arguments = if ($null -eq $Arguments) { '' } else { $Arguments }
    $psi.UseShellExecute = $false
    $psi.RedirectStandardOutput = $true
    $psi.RedirectStandardError = $true
    $psi.CreateNoWindow = $true
    $encoding = Get-WindowsAnsiEncoding
    try { $psi.StandardOutputEncoding = $encoding } catch { }
    try { $psi.StandardErrorEncoding = $encoding } catch { }

    $proc = [System.Diagnostics.Process]::new()
    $proc.StartInfo = $psi
    [void]$proc.Start()
    $stdout = $proc.StandardOutput.ReadToEnd()
    $stderr = $proc.StandardError.ReadToEnd()
    $proc.WaitForExit()
    if ([string]::IsNullOrWhiteSpace($stderr)) { return $stdout }
    return ($stdout.TrimEnd() + "`r`n" + $stderr)
}

function Save-NativeCommandOutput {
    param(
        [Parameter(Mandatory=$true)][string]$Path,
        [Parameter(Mandatory=$true)][string]$FilePath,
        [AllowNull()][string]$Arguments
    )
    try {
        $output = Invoke-NativeText -FilePath $FilePath -Arguments $Arguments
        Write-TextFileUtf8 -Path $Path -Text $output
        return $output
    } catch {
        $msg = "ERROR: {0}" -f $_.Exception.Message
        Write-TextFileUtf8 -Path $Path -Text $msg
        return $msg
    }
}

$ScriptRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
if (-not $ScriptRoot) { $ScriptRoot = (Get-Location).Path }
$ProjectRoot = (Resolve-Path -LiteralPath (Join-Path $ScriptRoot '..\..')).Path
if ([string]::IsNullOrWhiteSpace($OutputRoot)) {
    $OutputRoot = Join-Path $ProjectRoot 'backup\driver_guard\manifests'
}

$stamp = Get-Date -Format 'yyyyMMdd_HHmmss'
$safeComputer = ($env:COMPUTERNAME -replace '[^A-Za-z0-9_.-]', '_')
$ManifestDir = Join-Path $OutputRoot ("DriverStore_{0}_{1}" -f $safeComputer, $stamp)
New-Item -ItemType Directory -Force -Path $ManifestDir | Out-Null

Write-Host ''
Write-Host '=== Driver Store manifest ===' -ForegroundColor Cyan
Write-Host "Manifest folder: $ManifestDir"
Write-Host ''

$pnputilText = Save-NativeCommandOutput -Path (Join-Path $ManifestDir 'pnputil_enum_drivers.txt') -FilePath 'pnputil.exe' -Arguments '/enum-drivers'
Save-CommandOutput -Path (Join-Path $ManifestDir 'systeminfo.txt') -Command { systeminfo.exe }

try {
    Get-WindowsDriver -Online -ErrorAction Stop |
        Select-Object Driver, OriginalFileName, ProviderName, ClassName, Date, Version, BootCritical, Inbox |
        Export-Csv -LiteralPath (Join-Path $ManifestDir 'Get-WindowsDriver_Online.csv') -NoTypeInformation -Encoding UTF8
} catch {
    Write-TextFileUtf8 -Path (Join-Path $ManifestDir 'Get-WindowsDriver_Online_ERROR.txt') -Text $_.Exception.Message
}

$oemCount = ([regex]::Matches($pnputilText, 'oem\d+\.inf', [System.Text.RegularExpressions.RegexOptions]::IgnoreCase)).Count
Write-Host "Detected oem*.inf references in pnputil output: $oemCount"
Write-Host 'Manifest saved.' -ForegroundColor Green

if ($Show) {
    Write-Host ''
    Write-Host '=== pnputil /enum-drivers ===' -ForegroundColor Cyan
    Write-Host $pnputilText
}
