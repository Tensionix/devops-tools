param(
    [ValidateSet('Status', 'DisableUserProxy', 'ResetWinHttp')]
    [string]$Action = 'Status',

    [bool]$ClearAutoConfig = $true,
    [bool]$DisableAutoDetect = $true,
    [bool]$ClearConnectionCache = $true
)

$ErrorActionPreference = 'Stop'

try {
    $script:Utf8NoBom = [System.Text.UTF8Encoding]::new($false)
    [Console]::OutputEncoding = $script:Utf8NoBom
    $OutputEncoding = $script:Utf8NoBom
}
catch {
}

function Get-ProjectRoot {
    $scriptDir = Split-Path -Parent $PSCommandPath
    return (Resolve-Path (Join-Path $scriptDir '..\..')).Path
}

function New-RunContext {
    $root = Get-ProjectRoot
    $stamp = Get-Date -Format 'yyyyMMdd_HHmmss'
    $backupDir = Join-Path $root "backup\proxy_$stamp"
    $logDir = Join-Path $root 'logs'
    $logFile = Join-Path $logDir "proxy_tool_$stamp.log"
    New-Item -ItemType Directory -Force -Path $backupDir, $logDir | Out-Null
    return [pscustomobject]@{
        Root = $root
        Stamp = $stamp
        BackupDir = $backupDir
        LogDir = $logDir
        LogFile = $logFile
    }
}

function Write-Log {
    param(
        [Parameter(Mandatory=$true)]
        [string]$Message,
        [string]$Level = 'INFO'
    )
    $line = '[{0}] [{1}] {2}' -f (Get-Date -Format 'yyyy-MM-dd HH:mm:ss'), $Level, $Message
    Write-Host $line
    if ($script:Context -and $script:Context.LogFile) {
        Add-Content -LiteralPath $script:Context.LogFile -Value $line -Encoding UTF8
    }
}

function Test-IsAdmin {
    $identity = [Security.Principal.WindowsIdentity]::GetCurrent()
    $principal = New-Object Security.Principal.WindowsPrincipal($identity)
    return $principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
}

function Export-RegKeySafe {
    param(
        [Parameter(Mandatory=$true)]
        [string]$RegPath,
        [Parameter(Mandatory=$true)]
        [string]$FileName
    )
    $outFile = Join-Path $script:Context.BackupDir $FileName
    try {
        & reg.exe export $RegPath $outFile /y *> $null
        if ($LASTEXITCODE -eq 0) {
            Write-Log "Backed up registry key: $RegPath"
        }
        else {
            Write-Log "Registry key was not exported: $RegPath" 'WARN'
        }
    }
    catch {
        Write-Log "Registry export failed for $RegPath. $($_.Exception.Message)" 'WARN'
    }
}

function Invoke-NetshUtf8 {
    param(
        [Parameter(Mandatory=$true)]
        [string[]]$Arguments
    )
    $script:LastNetshExitCode = 0
    $command = 'chcp 65001 >nul & netsh.exe ' + ($Arguments -join ' ')
    $output = & cmd.exe /d /c $command 2>&1
    $script:LastNetshExitCode = if ($LASTEXITCODE -is [int]) { $LASTEXITCODE } else { 0 }
    return $output
}

function Get-UserProxyState {
    $internetPath = 'HKCU:\Software\Microsoft\Windows\CurrentVersion\Internet Settings'
    $values = Get-ItemProperty -LiteralPath $internetPath -ErrorAction SilentlyContinue
    return [pscustomobject]@{
        ProxyEnable  = $values.ProxyEnable
        ProxyServer  = $values.ProxyServer
        ProxyOverride = $values.ProxyOverride
        AutoConfigURL = $values.AutoConfigURL
        AutoDetect = $values.AutoDetect
    }
}

function Ensure-RegKey {
    param(
        [Parameter(Mandatory=$true)]
        [string]$Path
    )
    if (Test-Path -LiteralPath $Path) {
        Write-Log "Registry key exists: $Path"
        return
    }
    New-Item -Path $Path -Force -ErrorAction Stop | Out-Null
    Write-Log "Created registry key: $Path"
}

function Set-RegDwordValue {
    param(
        [Parameter(Mandatory=$true)]
        [string]$Path,
        [Parameter(Mandatory=$true)]
        [string]$Name,
        [Parameter(Mandatory=$true)]
        [int]$Value
    )
    Ensure-RegKey -Path $Path
    New-ItemProperty -LiteralPath $Path -Name $Name -Value $Value -PropertyType DWord -Force -ErrorAction Stop | Out-Null
    Write-Log "Set registry DWORD: $Path\$Name = $Value"
}

function Remove-RegValueIfPresent {
    param(
        [Parameter(Mandatory=$true)]
        [string]$Path,
        [Parameter(Mandatory=$true)]
        [string]$Name
    )
    if (-not (Test-Path -LiteralPath $Path)) {
        Write-Log "Registry key not found, skipping value removal: $Path\$Name" 'WARN'
        return
    }
    $item = Get-ItemProperty -LiteralPath $Path -Name $Name -ErrorAction SilentlyContinue
    if ($null -eq $item) {
        Write-Log "Registry value already absent: $Path\$Name"
        return
    }
    Remove-ItemProperty -LiteralPath $Path -Name $Name -ErrorAction Stop
    Write-Log "Removed registry value: $Path\$Name"
}

function Save-StatusSnapshot {
    $statusFile = Join-Path $script:Context.BackupDir 'status_before.txt'
    $state = Get-UserProxyState
    $lines = New-Object System.Collections.Generic.List[string]
    $lines.Add('Current user WinINet proxy state before action:')
    $lines.Add(('ProxyEnable  : {0}' -f $state.ProxyEnable))
    $lines.Add(('ProxyServer  : {0}' -f $state.ProxyServer))
    $lines.Add(('ProxyOverride: {0}' -f $state.ProxyOverride))
    $lines.Add(('AutoConfigURL: {0}' -f $state.AutoConfigURL))
    $lines.Add(('AutoDetect   : {0}' -f $state.AutoDetect))
    $lines.Add('')
    $lines.Add('WinHTTP proxy state before action:')
    try {
        $winHttp = Invoke-NetshUtf8 -Arguments @('winhttp', 'show', 'proxy')
        foreach ($line in $winHttp) {
            $lines.Add([string]$line)
        }
    }
    catch {
        $lines.Add(('Unable to read WinHTTP proxy state: {0}' -f $_.Exception.Message))
    }
    Set-Content -LiteralPath $statusFile -Value $lines -Encoding UTF8
    Write-Log "Saved status snapshot: $statusFile"
}

function Show-Status {
    Write-Log 'Current user WinINet proxy state:'
    $state = Get-UserProxyState
    Write-Host ('  ProxyEnable  : {0}' -f $state.ProxyEnable)
    Write-Host ('  ProxyServer  : {0}' -f $state.ProxyServer)
    Write-Host ('  ProxyOverride: {0}' -f $state.ProxyOverride)
    Write-Host ('  AutoConfigURL: {0}' -f $state.AutoConfigURL)
    Write-Host ('  AutoDetect   : {0}' -f $state.AutoDetect)
    Write-Host ''
    Write-Log 'WinHTTP proxy state:'
    $winHttp = Invoke-NetshUtf8 -Arguments @('winhttp', 'show', 'proxy')
    foreach ($line in $winHttp) {
        Write-Host $line
    }
}

function Invoke-InternetSettingsRefresh {
    try {
        $typeName = 'Audion.WinInet.NativeMethods'
        $source = @'
using System;
using System.Runtime.InteropServices;
namespace Audion.WinInet {
    public static class NativeMethods {
        [DllImport("wininet.dll", SetLastError = true)]
        public static extern bool InternetSetOption(IntPtr hInternet, int dwOption, IntPtr lpBuffer, int dwBufferLength);
    }
}
'@
        if (-not ($typeName -as [type])) {
            Add-Type -TypeDefinition $source -Language CSharp | Out-Null
        }
        [Audion.WinInet.NativeMethods]::InternetSetOption([IntPtr]::Zero, 39, [IntPtr]::Zero, 0) | Out-Null
        [Audion.WinInet.NativeMethods]::InternetSetOption([IntPtr]::Zero, 37, [IntPtr]::Zero, 0) | Out-Null
        Write-Log 'Notified Windows about proxy settings changes.'
    }
    catch {
        Write-Log "Unable to refresh WinINet settings automatically. $($_.Exception.Message)" 'WARN'
    }
}

function Disable-CurrentUserProxy {
    $internetPath = 'HKCU:\Software\Microsoft\Windows\CurrentVersion\Internet Settings'
    $connectionsPath = Join-Path $internetPath 'Connections'

    Export-RegKeySafe -RegPath 'HKCU\Software\Microsoft\Windows\CurrentVersion\Internet Settings' -FileName 'HKCU_Internet_Settings_before.reg'
    Export-RegKeySafe -RegPath 'HKCU\Software\Microsoft\Windows\CurrentVersion\Internet Settings\Connections' -FileName 'HKCU_Internet_Settings_Connections_before.reg'
    Save-StatusSnapshot

    Write-Log 'Disabling current user manual proxy.'
    Ensure-RegKey -Path $internetPath
    Set-RegDwordValue -Path $internetPath -Name ProxyEnable -Value 0

    foreach ($name in @('ProxyServer', 'ProxyOverride')) {
        Remove-RegValueIfPresent -Path $internetPath -Name $name
    }

    if ($ClearAutoConfig) {
        Remove-RegValueIfPresent -Path $internetPath -Name AutoConfigURL
    }

    if ($DisableAutoDetect) {
        Set-RegDwordValue -Path $internetPath -Name AutoDetect -Value 0
    }

    if ($ClearConnectionCache) {
        foreach ($name in @('DefaultConnectionSettings', 'SavedLegacySettings')) {
            Remove-RegValueIfPresent -Path $connectionsPath -Name $name
        }
    }

    Invoke-InternetSettingsRefresh
    Write-Log 'Current user proxy cleanup completed.'
    Write-Host ''
    Show-Status
}

function Reset-WinHttpProxy {
    Export-RegKeySafe -RegPath 'HKCU\Software\Microsoft\Windows\CurrentVersion\Internet Settings' -FileName 'HKCU_Internet_Settings_before_winhttp_reset.reg'
    Save-StatusSnapshot

    if (-not (Test-IsAdmin)) {
        Write-Log 'This action should be run as Administrator. WinHTTP reset may fail.' 'WARN'
    }

    Write-Log 'Resetting WinHTTP proxy.'
    $output = Invoke-NetshUtf8 -Arguments @('winhttp', 'reset', 'proxy')
    $exitCode = $script:LastNetshExitCode
    foreach ($line in $output) {
        Write-Host $line
        Add-Content -LiteralPath $script:Context.LogFile -Value ([string]$line) -Encoding UTF8
    }

    if ($exitCode -ne 0) {
        Write-Log "netsh winhttp reset proxy failed with exit code $exitCode" 'ERROR'
        exit $exitCode
    }

    Write-Log 'WinHTTP proxy reset completed.'
    Write-Host ''
    Show-Status
}

$script:Context = New-RunContext
Write-Log "Audion Windows Proxy Tool started. Action: $Action"
Write-Log "Project root: $($script:Context.Root)"
Write-Log "Backup directory: $($script:Context.BackupDir)"
Write-Log "Log file: $($script:Context.LogFile)"
Write-Host ''

try {
    switch ($Action) {
        'Status' { Show-Status }
        'DisableUserProxy' { Disable-CurrentUserProxy }
        'ResetWinHttp' { Reset-WinHttpProxy }
    }
    Write-Host ''
    Write-Log 'Done.'
    exit 0
}
catch {
    $lineNumber = $_.InvocationInfo.ScriptLineNumber
    $lineText = ($_.InvocationInfo.Line -replace '\s+', ' ').Trim()
    if ($lineNumber) {
        Write-Log ("{0} (line {1}: {2})" -f $_.Exception.Message, $lineNumber, $lineText) 'ERROR'
    }
    else {
        Write-Log $_.Exception.Message 'ERROR'
    }
    Write-Host ''
    Write-Host 'FAILED. Check the log file above.'
    exit 1
}
