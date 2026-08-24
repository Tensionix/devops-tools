# Exports currently staged third-party drivers from the online Windows Driver Store.
# Uses Export-WindowsDriver when available, with DISM fallback.
# The result is intended as a local repair/offline reinstall driver cache.

[CmdletBinding()]
param(
    [string]$DestinationRoot
)

$ErrorActionPreference = 'Stop'
try { $PSNativeCommandUseErrorActionPreference = $false } catch { }

function New-SafeDirectory {
    param([Parameter(Mandatory=$true)][string]$Path)
    New-Item -ItemType Directory -Force -Path $Path | Out-Null
    return (Resolve-Path -LiteralPath $Path).Path
}

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
    } catch {
        Write-TextFileUtf8 -Path $Path -Text ("ERROR: {0}" -f $_.Exception.Message)
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
    } catch {
        Write-TextFileUtf8 -Path $Path -Text ("ERROR: {0}" -f $_.Exception.Message)
    }
}

$ScriptRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
if (-not $ScriptRoot) { $ScriptRoot = (Get-Location).Path }
$ProjectRoot = (Resolve-Path -LiteralPath (Join-Path $ScriptRoot '..\..')).Path

if ([string]::IsNullOrWhiteSpace($DestinationRoot)) {
    $DestinationRoot = Join-Path $ProjectRoot 'backup\driver_guard\driver_store'
}

$DestinationRoot = New-SafeDirectory -Path $DestinationRoot
$stamp = Get-Date -Format 'yyyyMMdd_HHmmss'
$safeComputer = ($env:COMPUTERNAME -replace '[^A-Za-z0-9_.-]', '_')
$BackupRoot = Join-Path $DestinationRoot ("{0}_{1}" -f $safeComputer, $stamp)
$DriversDir = Join-Path $BackupRoot 'drivers'
$ManifestDir = Join-Path $BackupRoot 'manifest'

New-SafeDirectory -Path $DriversDir | Out-Null
New-SafeDirectory -Path $ManifestDir | Out-Null

Write-Host ''
Write-Host '=== Export installed third-party drivers ===' -ForegroundColor Cyan
Write-Host "Backup root: $BackupRoot"
Write-Host "Drivers:     $DriversDir"
Write-Host "Manifest:    $ManifestDir"
Write-Host ''

$summary = [System.Collections.Generic.List[string]]::new()
$summary.Add('Audion Driver Store Backup')
$summary.Add(('Created: {0}' -f (Get-Date -Format 'yyyy-MM-dd HH:mm:ss')))
$summary.Add(('ComputerName: {0}' -f $env:COMPUTERNAME))
$summary.Add(('UserDomain: {0}' -f $env:USERDOMAIN))
$summary.Add(('UserName: {0}' -f $env:USERNAME))
$summary.Add(('PowerShell: {0}' -f $PSVersionTable.PSVersion.ToString()))
$summary.Add(('BackupRoot: {0}' -f $BackupRoot))
$summary.Add(('DriversDir: {0}' -f $DriversDir))

Write-Host 'Saving pre-export manifests...'
Save-NativeCommandOutput -Path (Join-Path $ManifestDir 'pnputil_enum_drivers_before_export.txt') -FilePath 'pnputil.exe' -Arguments '/enum-drivers'
Save-CommandOutput -Path (Join-Path $ManifestDir 'systeminfo.txt') -Command { systeminfo.exe }
try {
    Get-WindowsDriver -Online -ErrorAction Stop |
        Select-Object Driver, OriginalFileName, ProviderName, ClassName, Date, Version, BootCritical, Inbox |
        Export-Csv -LiteralPath (Join-Path $ManifestDir 'Get-WindowsDriver_Online.csv') -NoTypeInformation -Encoding UTF8
} catch {
    Write-TextFileUtf8 -Path (Join-Path $ManifestDir 'Get-WindowsDriver_Online_ERROR.txt') -Text $_.Exception.Message
}

$exportOk = $false
$exportMethod = ''
try {
    Write-Host 'Trying Export-WindowsDriver...'
    $exported = @(Export-WindowsDriver -Online -Destination $DriversDir -ErrorAction Stop)
    $exportMethod = 'Export-WindowsDriver'
    $exportOk = $true
    try {
        $exported | Select-Object * | Export-Csv -LiteralPath (Join-Path $ManifestDir 'Export-WindowsDriver_Result.csv') -NoTypeInformation -Encoding UTF8
    } catch { }
} catch {
    Write-Host "Export-WindowsDriver failed: $($_.Exception.Message)" -ForegroundColor Yellow
    Write-Host 'Trying DISM fallback...'
    & dism.exe /online /export-driver /destination:$DriversDir
    $dismCode = $LASTEXITCODE
    $exportMethod = 'DISM /export-driver'
    if ($dismCode -eq 0) {
        $exportOk = $true
    } else {
        throw "DISM export failed with exit code $dismCode"
    }
}

Write-Host 'Saving post-export manifest...'
Save-NativeCommandOutput -Path (Join-Path $ManifestDir 'pnputil_enum_drivers_after_export.txt') -FilePath 'pnputil.exe' -Arguments '/enum-drivers'

$infFiles = @(Get-ChildItem -LiteralPath $DriversDir -Filter '*.inf' -Recurse -File -ErrorAction SilentlyContinue)
$summary.Add(('ExportMethod: {0}' -f $exportMethod))
$summary.Add(('ExportedInfCount: {0}' -f $infFiles.Count))
$summary.Add('')
$summary.Add('Restore command:')
$summary.Add(('pnputil /add-driver "{0}\*.inf" /subdirs /install' -f $DriversDir))
Write-TextFileUtf8 -Path (Join-Path $BackupRoot 'README_DRIVER_BACKUP.txt') -Text ($summary -join "`r`n")

Write-Host ''
Write-Host 'DONE: Driver Store export completed.' -ForegroundColor Green
Write-Host "Method: $exportMethod"
Write-Host "Exported INF files: $($infFiles.Count)"
Write-Host "Backup root: $BackupRoot"
Write-Host ''
Write-Host 'Note: this exports INF-based third-party driver packages from Driver Store.' -ForegroundColor Yellow
Write-Host 'It does not download new drivers and does not replace OEM installer applications.' -ForegroundColor Yellow
