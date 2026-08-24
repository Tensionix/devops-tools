param(
    [ValidateSet('menu','status','enable','disable','restore')]
    [string]$Mode = 'menu',

    [string]$IpAddress = '',

    [string]$HostName = 'portal.itpgrad.ru'
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

$DefaultIpAddress = '192.168.0.100'

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

function Test-BhtIsAdministrator {
    $identity  = [Security.Principal.WindowsIdentity]::GetCurrent()
    $principal = [Security.Principal.WindowsPrincipal]::new($identity)
    return $principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
}

function Get-BhtHostsPath {
    return Join-Path $env:WINDIR 'System32\drivers\etc\hosts'
}

function Get-BhtOriginalPath {
    $dir = if ($PSScriptRoot) { $PSScriptRoot } `
           elseif ($PSCommandPath) { Split-Path -LiteralPath $PSCommandPath -Parent } `
           else { (Get-Location).Path }
    return Join-Path $dir 'backup\hosts'
}

function Read-BhtHostsLines {
    param([string]$Path)

    if (-not (Test-Path -LiteralPath $Path)) { return @() }
    $lines = [System.IO.File]::ReadAllLines($Path)
    if ($null -eq $lines) { return @() }
    return @($lines)
}

function Write-BhtHostsLines {
    param([string]$Path, [string[]]$Lines)

    if ($null -eq $Lines) { $Lines = @() }
    $encoding = [System.Text.UTF8Encoding]::new($false)

    if ($Lines.Count -eq 0) {
        [System.IO.File]::WriteAllText($Path, '', $encoding)
        return
    }

    $content = [string]::Join([Environment]::NewLine, $Lines) + [Environment]::NewLine
    [System.IO.File]::WriteAllText($Path, $content, $encoding)
}

# ---------------------------------------------------------------------------
# Core logic
# ---------------------------------------------------------------------------

function ConvertFrom-BhtHostsLine {
    param([string]$Line)

    if ([string]::IsNullOrWhiteSpace($Line)) { return $null }
    if ($Line -match '^\s*#') { return $null }

    $tokens = [regex]::Split($Line.Trim(), '\s+') | Where-Object { $_ -ne '' }
    if ($tokens.Count -lt 2) { return $null }

    return [pscustomobject]@{
        IPAddress = $tokens[0]
        Hosts     = @($tokens[1..($tokens.Count - 1)])
    }
}

function Get-BhtMatchingEntries {
    param([string[]]$Lines, [string]$TargetHost, [string]$TargetIp = '')

    $results = [System.Collections.Generic.List[psobject]]::new()

    for ($i = 0; $i -lt $Lines.Count; $i++) {
        $parsed = ConvertFrom-BhtHostsLine -Line $Lines[$i]
        if ($null -eq $parsed) { continue }

        $containsHost = $false
        foreach ($h in $parsed.Hosts) {
            if ($h.Equals($TargetHost, [System.StringComparison]::OrdinalIgnoreCase)) {
                $containsHost = $true; break
            }
        }
        if (-not $containsHost) { continue }

        if (-not [string]::IsNullOrWhiteSpace($TargetIp)) {
            if (-not $parsed.IPAddress.Equals($TargetIp, [System.StringComparison]::OrdinalIgnoreCase)) { continue }
        }

        $results.Add([pscustomobject]@{
            LineNumber = $i + 1
            RawLine    = $Lines[$i]
            IPAddress  = $parsed.IPAddress
            Hosts      = $parsed.Hosts
        })
    }

    return @($results.ToArray())
}

function Remove-BhtHostEntries {
    param([string[]]$Lines, [string]$TargetHost, [string]$TargetIp = '')

    $newLines    = [System.Collections.Generic.List[string]]::new()
    $removedCount = 0

    foreach ($line in $Lines) {
        if ([string]::IsNullOrWhiteSpace($line) -or $line -match '^\s*#') {
            $newLines.Add($line) | Out-Null; continue
        }

        $parsed = ConvertFrom-BhtHostsLine -Line $line
        if ($null -eq $parsed) { $newLines.Add($line) | Out-Null; continue }

        if (-not [string]::IsNullOrWhiteSpace($TargetIp)) {
            if (-not $parsed.IPAddress.Equals($TargetIp, [System.StringComparison]::OrdinalIgnoreCase)) {
                $newLines.Add($line) | Out-Null; continue
            }
        }

        $keep       = @()
        $removedHere = 0
        foreach ($h in $parsed.Hosts) {
            if ($h.Equals($TargetHost, [System.StringComparison]::OrdinalIgnoreCase)) { $removedHere++ }
            else { $keep += $h }
        }

        if ($removedHere -eq 0) { $newLines.Add($line) | Out-Null; continue }

        $removedCount += $removedHere
        if ($keep.Count -gt 0) {
            $newLines.Add(("{0} {1}" -f $parsed.IPAddress, ($keep -join ' '))) | Out-Null
        }
    }

    return [pscustomobject]@{ Lines = @($newLines.ToArray()); RemovedCount = $removedCount }
}

# ---------------------------------------------------------------------------
# Commands
# ---------------------------------------------------------------------------

function Show-BhtStatus {
    param([string]$HostsPath, [string]$TargetHost, [string]$TargetIp = '')

    $lines = Read-BhtHostsLines -Path $HostsPath
    $found = @(Get-BhtMatchingEntries -Lines $lines -TargetHost $TargetHost -TargetIp $TargetIp)

    Write-Host ("Hosts file : {0}" -f $HostsPath)
    Write-Host ("Target host: {0}" -f $TargetHost)
    Write-Host ("Filter IP  : {0}" -f $(if ([string]::IsNullOrWhiteSpace($TargetIp)) { '<any>' } else { $TargetIp }))
    Write-Host ''

    if ($found.Count -eq 0) {
        Write-Host 'Status     : no active hosts override found.'
        return
    }

    Write-Host ("Status     : {0} active override(s) found." -f $found.Count)
    Write-Host ''
    foreach ($item in $found) {
        Write-Host ("Line {0}: {1}" -f $item.LineNumber, $item.RawLine)
    }
}

function Invoke-BhtRestore {
    param([string]$HostsPath)

    $originalPath = Get-BhtOriginalPath

    if (-not (Test-Path -LiteralPath $originalPath)) {
        throw "Original hosts not found: $originalPath"
    }

    # backup\hosts is the factory file that ships with the pack, not a copy of
    # this machine's. Restoring therefore discards whatever hosts holds now, so
    # the outgoing file is kept first and an accidental restore stays undoable.
    if (Test-Path -LiteralPath $HostsPath) {
        $stamp    = Get-Date -Format 'yyyyMMdd_HHmmss'
        $keptPath = Join-Path (Split-Path -LiteralPath $originalPath -Parent) "hosts_replaced_$stamp"
        Copy-Item -LiteralPath $HostsPath -Destination $keptPath -Force
        Write-Host ("Previous hosts kept as: {0}" -f $keptPath)
    }

    Copy-Item -LiteralPath $originalPath -Destination $HostsPath -Force
    Write-Host ("Hosts restored from: {0}" -f $originalPath)
}

function Enable-BhtHostOverride {
    param([string]$HostsPath, [string]$TargetHost, [string]$TargetIp)

    if ([string]::IsNullOrWhiteSpace($TargetIp)) {
        throw 'IpAddress is required for enable mode.'
    }

    # This used to overwrite hosts with the shipped original whenever the live
    # file differed from it by a single byte — which is to say, almost always,
    # because anything else in hosts counts as a difference. A domain the owner
    # blocked, an entry another project needs, a colleague's note: all gone, and
    # the message said "restored to original", which does not sound like loss.
    #
    # It bought nothing. Remove-BhtHostEntries below already takes out every line
    # for this host — and only that host, keeping the other names sharing a line —
    # so a duplicate entry was never possible in the first place.
    $existingLines = Read-BhtHostsLines -Path $HostsPath
    $removeResult  = Remove-BhtHostEntries -Lines $existingLines -TargetHost $TargetHost

    $newLines = [System.Collections.Generic.List[string]]::new()
    foreach ($line in $removeResult.Lines) { $newLines.Add($line) | Out-Null }

    if ($newLines.Count -gt 0 -and -not [string]::IsNullOrWhiteSpace($newLines[$newLines.Count - 1])) {
        $newLines.Add('') | Out-Null
    }

    $newEntry = "{0} {1}" -f $TargetIp, $TargetHost
    $newLines.Add($newEntry) | Out-Null

    Write-BhtHostsLines -Path $HostsPath -Lines @($newLines.ToArray())
    Write-Host ("Enabled: {0}" -f $newEntry)
}

function Disable-BhtHostOverride {
    param([string]$HostsPath, [string]$TargetHost, [string]$TargetIp = '')

    $existingLines = Read-BhtHostsLines -Path $HostsPath
    $removeResult  = Remove-BhtHostEntries -Lines $existingLines -TargetHost $TargetHost -TargetIp $TargetIp

    if ($removeResult.RemovedCount -eq 0) {
        Write-Host 'Nothing to remove. No matching active override was found.'
        return
    }

    Write-BhtHostsLines -Path $HostsPath -Lines @($removeResult.Lines)

    if ([string]::IsNullOrWhiteSpace($TargetIp)) {
        Write-Host ("Removed override(s) for {0}." -f $TargetHost)
    } else {
        Write-Host ("Removed override(s) for {0} @ {1}." -f $TargetHost, $TargetIp)
    }
}

# ---------------------------------------------------------------------------
# Interactive menu
# ---------------------------------------------------------------------------

function Invoke-BhtInteractiveMenu {
    param([string]$HostsPath, [string]$TargetHost)

    while ($true) {
        Write-Host ''
        Write-Host '========================================='
        Write-Host '  BITRIX HOSTS TOGGLE'
        Write-Host '========================================='
        Write-Host '1. Status'
        Write-Host '2. Enable'
        Write-Host '3. Disable'
        Write-Host '4. Exit'
        Write-Host ''

        $choice = (Read-Host 'Select').Trim()

        switch ($choice) {
            '1' { Show-BhtStatus -HostsPath $HostsPath -TargetHost $TargetHost }
            '2' {
                $ip = (Read-Host ("IP address [{0}]" -f $DefaultIpAddress)).Trim()
                if ([string]::IsNullOrWhiteSpace($ip)) { $ip = $DefaultIpAddress }
                Enable-BhtHostOverride -HostsPath $HostsPath -TargetHost $TargetHost -TargetIp $ip
            }
            '3' { Invoke-BhtRestore -HostsPath $HostsPath }
            '4' { return }
            default { Write-Host 'Unknown option.' }
        }

        Write-Host ''
        [void](Read-Host 'Press Enter to continue')
    }
}

# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if (-not (Test-BhtIsAdministrator)) {
    throw 'Please run this script as Administrator.'
}

$hostsPath = Get-BhtHostsPath

switch ($Mode) {
    'menu'    { Invoke-BhtInteractiveMenu -HostsPath $hostsPath -TargetHost $HostName }
    'status'  { Show-BhtStatus           -HostsPath $hostsPath -TargetHost $HostName -TargetIp $IpAddress }
    'enable'  { Enable-BhtHostOverride   -HostsPath $hostsPath -TargetHost $HostName -TargetIp $IpAddress }
    'disable' { Disable-BhtHostOverride  -HostsPath $hostsPath -TargetHost $HostName -TargetIp $IpAddress }
    'restore' { Invoke-BhtRestore        -HostsPath $hostsPath }
}
