# Removes the all-device Windows Update driver block created by Block-All-WU-Driver-Updates.ps1.
# Run as Administrator.

$ErrorActionPreference = 'Stop'
# PowerShell 7.x can promote native command failures to errors. Keep reg.exe/gpupdate.exe under explicit exit-code control.
$PSNativeCommandUseErrorActionPreference = $false

function Assert-Administrator {
    $identity = [Security.Principal.WindowsIdentity]::GetCurrent()
    $principal = New-Object Security.Principal.WindowsPrincipal($identity)
    if (-not $principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) {
        Write-Host 'ERROR: Run this script as Administrator.' -ForegroundColor Red
        exit 1
    }
}

function New-DirIfMissing {
    param([Parameter(Mandatory=$true)][string]$Path)
    if (-not (Test-Path -LiteralPath $Path)) {
        New-Item -ItemType Directory -Path $Path -Force | Out-Null
    }
}

function Convert-RegExePathToProviderPath {
    param([Parameter(Mandatory=$true)][string]$RegPath)

    $clean = $RegPath.Trim().TrimEnd('\')
    $upper = $clean.ToUpperInvariant()

    if ($upper -eq 'HKLM') { return 'Registry::HKEY_LOCAL_MACHINE' }
    if ($upper.StartsWith('HKLM\')) { return "Registry::HKEY_LOCAL_MACHINE\$($clean.Substring(5))" }

    if ($upper -eq 'HKCU') { return 'Registry::HKEY_CURRENT_USER' }
    if ($upper.StartsWith('HKCU\')) { return "Registry::HKEY_CURRENT_USER\$($clean.Substring(5))" }

    if ($upper -eq 'HKCR') { return 'Registry::HKEY_CLASSES_ROOT' }
    if ($upper.StartsWith('HKCR\')) { return "Registry::HKEY_CLASSES_ROOT\$($clean.Substring(5))" }

    if ($upper -eq 'HKU') { return 'Registry::HKEY_USERS' }
    if ($upper.StartsWith('HKU\')) { return "Registry::HKEY_USERS\$($clean.Substring(4))" }

    if ($upper -eq 'HKCC') { return 'Registry::HKEY_CURRENT_CONFIG' }
    if ($upper.StartsWith('HKCC\')) { return "Registry::HKEY_CURRENT_CONFIG\$($clean.Substring(5))" }

    throw "Unsupported registry path: $RegPath"
}

function Export-RegKeyIfExists {
    param(
        [Parameter(Mandatory=$true)][string]$RegPath,
        [Parameter(Mandatory=$true)][string]$BackupFile
    )

    $providerPath = Convert-RegExePathToProviderPath -RegPath $RegPath
    if (-not (Test-Path -LiteralPath $providerPath)) {
        Write-Host "Backup skipped, key does not exist: $RegPath" -ForegroundColor Yellow
        return
    }

    $oldErrorActionPreference = $ErrorActionPreference
    $ErrorActionPreference = 'Continue'
    try {
        & reg.exe export $RegPath $BackupFile /y *> $null
        $exitCode = $LASTEXITCODE
    } finally {
        $ErrorActionPreference = $oldErrorActionPreference
    }

    if ($exitCode -eq 0 -and (Test-Path -LiteralPath $BackupFile)) {
        Write-Host "Backup: $BackupFile"
    } else {
        Write-Host "WARNING: Backup export failed for $RegPath. reg.exe exit code: $($exitCode)" -ForegroundColor Yellow
    }
}

function Remove-PolicyValueIfExists {
    param(
        [Parameter(Mandatory=$true)][string]$Path,
        [Parameter(Mandatory=$true)][string]$Name
    )
    if (Test-Path -LiteralPath $Path) {
        $prop = Get-ItemProperty -LiteralPath $Path -Name $Name -ErrorAction SilentlyContinue
        if ($null -ne $prop) {
            Remove-ItemProperty -LiteralPath $Path -Name $Name -Force
            Write-Host "Removed: $Path -> $Name"
        } else {
            Write-Host "Already absent: $Path -> $Name"
        }
    } else {
        Write-Host "Key absent: $Path"
    }
}

Assert-Administrator

$ScriptRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$ProjectRoot = (Resolve-Path -LiteralPath (Join-Path $ScriptRoot '..\..')).Path
$BackupDir = Join-Path $ProjectRoot 'backup\driver_guard\policy'
New-DirIfMissing $BackupDir
$Stamp = Get-Date -Format 'yyyyMMdd_HHmmss'

Export-RegKeyIfExists 'HKLM\SOFTWARE\Policies\Microsoft\Windows\WindowsUpdate' (Join-Path $BackupDir "WindowsUpdate_policy_before_unblock_all_$Stamp.reg")
Export-RegKeyIfExists 'HKLM\SOFTWARE\Policies\Microsoft\Windows\DriverSearching' (Join-Path $BackupDir "DriverSearching_policy_before_unblock_all_$Stamp.reg")
Export-RegKeyIfExists 'HKLM\SOFTWARE\Policies\Microsoft\Windows\Device Metadata' (Join-Path $BackupDir "DeviceMetadata_policy_before_unblock_all_$Stamp.reg")
Export-RegKeyIfExists 'HKLM\SOFTWARE\Microsoft\Windows\CurrentVersion\DriverSearching' (Join-Path $BackupDir "DriverSearching_current_before_unblock_all_$Stamp.reg")

Remove-PolicyValueIfExists -Path 'HKLM:\SOFTWARE\Policies\Microsoft\Windows\WindowsUpdate' -Name 'ExcludeWUDriversInQualityUpdate'
Remove-PolicyValueIfExists -Path 'HKLM:\SOFTWARE\Policies\Microsoft\Windows\DriverSearching' -Name 'DriverUpdateWizardWuSearchEnabled'
Remove-PolicyValueIfExists -Path 'HKLM:\SOFTWARE\Policies\Microsoft\Windows\Device Metadata' -Name 'PreventDeviceMetadataFromNetwork'

# Restore normal Windows behavior for the legacy/current setting.
if (-not (Test-Path -LiteralPath 'HKLM:\SOFTWARE\Microsoft\Windows\CurrentVersion\DriverSearching')) {
    New-Item -Path 'HKLM:\SOFTWARE\Microsoft\Windows\CurrentVersion\DriverSearching' -Force | Out-Null
}
New-ItemProperty -Path 'HKLM:\SOFTWARE\Microsoft\Windows\CurrentVersion\DriverSearching' -Name 'SearchOrderConfig' -PropertyType DWord -Value 1 -Force | Out-Null
Write-Host 'Set: HKLM:\SOFTWARE\Microsoft\Windows\CurrentVersion\DriverSearching -> SearchOrderConfig = 1'

Write-Host ''
Write-Host 'Refreshing computer policy...'
& gpupdate.exe /target:computer /force | Out-Host

Write-Host ''
Write-Host 'DONE: all-device Windows Update driver block has been removed.' -ForegroundColor Green
Write-Host 'Recommended next step: reboot.'
