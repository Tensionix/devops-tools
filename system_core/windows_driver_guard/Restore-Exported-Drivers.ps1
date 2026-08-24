# Restores drivers from an Audion Driver Store backup using pnputil.
# By default, it offers the newest folder under backup\driver_guard\driver_store.

[CmdletBinding()]
param(
    [string]$BackupPath,
    [switch]$NoPrompt
)

$ErrorActionPreference = 'Stop'
try { $PSNativeCommandUseErrorActionPreference = $false } catch { }

function Resolve-DriverFolder {
    param([Parameter(Mandatory=$true)][string]$Path)
    $resolved = (Resolve-Path -LiteralPath $Path -ErrorAction Stop).Path
    $candidate = Join-Path $resolved 'drivers'
    if (Test-Path -LiteralPath $candidate) { return (Resolve-Path -LiteralPath $candidate).Path }
    return $resolved
}

$ScriptRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
if (-not $ScriptRoot) { $ScriptRoot = (Get-Location).Path }
$ProjectRoot = (Resolve-Path -LiteralPath (Join-Path $ScriptRoot '..\..')).Path
$DefaultRoot = Join-Path $ProjectRoot 'backup\driver_guard\driver_store'

Write-Host ''
Write-Host '=== Restore exported drivers ===' -ForegroundColor Cyan

if ([string]::IsNullOrWhiteSpace($BackupPath)) {
    if (-not (Test-Path -LiteralPath $DefaultRoot)) {
        throw "No driver backup folder found: $DefaultRoot"
    }

    $backups = @(Get-ChildItem -LiteralPath $DefaultRoot -Directory -ErrorAction SilentlyContinue |
        Where-Object { Test-Path -LiteralPath (Join-Path $_.FullName 'drivers') } |
        Sort-Object LastWriteTime -Descending)

    if ($backups.Count -eq 0) {
        throw "No driver backup folders with a drivers subfolder were found under: $DefaultRoot"
    }

    Write-Host 'Available backups:'
    for ($i = 0; $i -lt $backups.Count; $i++) {
        Write-Host ('  [{0}] {1}   {2}' -f ($i + 1), $backups[$i].Name, $backups[$i].LastWriteTime.ToString('yyyy-MM-dd HH:mm:ss'))
    }

    if ($NoPrompt) {
        $BackupPath = $backups[0].FullName
    } else {
        Write-Host ''
        $choice = Read-Host 'Press Enter for newest backup, type number, or paste backup path'
        if ([string]::IsNullOrWhiteSpace($choice)) {
            $BackupPath = $backups[0].FullName
        } elseif ($choice -match '^[0-9]+$') {
            $idx = [int]$choice - 1
            if ($idx -lt 0 -or $idx -ge $backups.Count) { throw 'Invalid backup number.' }
            $BackupPath = $backups[$idx].FullName
        } else {
            $BackupPath = $choice
        }
    }
}

$DriversDir = Resolve-DriverFolder -Path $BackupPath
$infFiles = @(Get-ChildItem -LiteralPath $DriversDir -Filter '*.inf' -Recurse -File -ErrorAction SilentlyContinue)
if ($infFiles.Count -eq 0) {
    throw "No INF files were found under: $DriversDir"
}

Write-Host ''
Write-Host "Selected drivers folder: $DriversDir"
Write-Host "INF files found: $($infFiles.Count)"
Write-Host ''
Write-Host 'This will stage and install matching driver packages with pnputil.' -ForegroundColor Yellow
Write-Host 'Recommended: use backups from the same machine or a very similar hardware profile.' -ForegroundColor Yellow
Write-Host ''

if (-not $NoPrompt) {
    $confirm = Read-Host 'Type RESTORE to continue'
    if ($confirm -ne 'RESTORE') {
        Write-Host 'Cancelled.' -ForegroundColor Yellow
        exit 2
    }
}

$pattern = Join-Path $DriversDir '*.inf'
Write-Host ''
Write-Host "Running: pnputil /add-driver `"$pattern`" /subdirs /install"
& pnputil.exe /add-driver $pattern /subdirs /install
$code = $LASTEXITCODE
if ($code -ne 0) {
    throw "pnputil failed with exit code $code"
}

Write-Host ''
Write-Host 'DONE: Restore command completed.' -ForegroundColor Green
Write-Host 'Recommended next step: reboot, then check Device Manager.'
