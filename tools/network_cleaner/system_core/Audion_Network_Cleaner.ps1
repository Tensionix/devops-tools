<#
Audion Network Cleaner v2 - TimeMachine edition
Controlled Windows network repair pack.
All backups and restore artifacts are stored inside the project backup folder.
Terminal output is English by design to avoid encoding problems in CMD/PowerShell consoles.
#>

param(
    [ValidateSet('Status','Backup','BackupWithWiFiKeys','LightRepair','StandardRepair','NuclearRepair','GodzillaStrike','RestoreLatest','RestoreSelect','OpenBackup','Help')]
    [string]$Mode = 'Status'
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Continue'

$script:ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$script:ProjectRoot = Split-Path -Parent $script:ScriptDir
$script:BackupRoot = Join-Path $script:ProjectRoot 'backup'
$script:BackupDir = $null
$script:LogFile = $null

function Test-Administrator {
    try {
        $identity = [Security.Principal.WindowsIdentity]::GetCurrent()
        $principal = New-Object Security.Principal.WindowsPrincipal($identity)
        return $principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
    }
    catch {
        return $false
    }
}

function Write-Log {
    param([string]$Message)
    $stamp = Get-Date -Format 'yyyy-MM-dd HH:mm:ss'
    $line = "[$stamp] $Message"
    Write-Host $Message
    if ($script:LogFile) {
        try { Add-Content -LiteralPath $script:LogFile -Value $line -Encoding UTF8 } catch { }
    }
}

function Write-Section {
    param([string]$Title)
    Write-Log ''
    Write-Log ('=' * 72)
    Write-Log $Title
    Write-Log ('=' * 72)
}

function New-BackupSnapshot {
    param([string]$Reason)

    if (-not (Test-Path -LiteralPath $script:BackupRoot)) {
        New-Item -ItemType Directory -Path $script:BackupRoot -Force | Out-Null
    }

    $stamp = Get-Date -Format 'yyyyMMdd_HHmmss'
    $safeReason = ($Reason -replace '[^a-zA-Z0-9_-]', '_')
    $dirName = "network_backup_${stamp}_${safeReason}"
    $script:BackupDir = Join-Path $script:BackupRoot $dirName
    New-Item -ItemType Directory -Path $script:BackupDir -Force | Out-Null

    $script:LogFile = Join-Path $script:BackupDir 'run_log.txt'
    New-Item -ItemType File -Path $script:LogFile -Force | Out-Null

    $readme = @"
Audion Network Cleaner backup snapshot
Reason: $Reason
Created: $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')
Computer: $env:COMPUTERNAME
User: $env:USERNAME
Project root: $script:ProjectRoot

This folder contains diagnostics, registry exports, netsh dumps and selected file backups made before repair actions.
By default, Wi-Fi profiles are exported without saved keys.
Use BackupWithWiFiKeys or the Godzilla pre-backup prompt only when you intentionally want clear-text Wi-Fi keys stored inside this project backup folder.
"@
    Set-Content -LiteralPath (Join-Path $script:BackupDir '00_README.txt') -Value $readme -Encoding UTF8
    Set-Content -LiteralPath (Join-Path $script:BackupRoot '_last_snapshot.txt') -Value $script:BackupDir -Encoding UTF8

    Write-Section "Backup snapshot created"
    Write-Log "Backup folder: $script:BackupDir"
}

function Assert-SnapshotUsable {
    <#
        The whole pack rests on one promise: a snapshot exists before anything is
        broken, and the TimeMachine can put it back. $ErrorActionPreference is
        Continue here, deliberately, because the diagnostics call dozens of
        external tools that are allowed to fail. That tolerance must not extend to
        the snapshot itself: a backup folder that could not be created only prints
        an error, every Save-TextFile then warns, and the repair would proceed and
        destroy the network configuration with nothing to restore from.

        Worse, _last_snapshot.txt would already point at that empty folder, so the
        TimeMachine would offer to restore from it.
    #>
    param([string]$Stage)

    $problems = @()

    if (-not $script:BackupDir -or -not (Test-Path -LiteralPath $script:BackupDir -PathType Container)) {
        $problems += "backup folder was not created: $script:BackupDir"
    }
    else {
        $manifest = Join-Path $script:BackupDir 'restore_manifest.json'
        if (-not (Test-Path -LiteralPath $manifest -PathType Leaf)) {
            $problems += 'restore_manifest.json is missing, so the snapshot cannot be restored'
        }

        $saved = @(Get-ChildItem -LiteralPath $script:BackupDir -File -ErrorAction SilentlyContinue)
        if ($saved.Count -lt 10) {
            $problems += ('the snapshot holds only ' + $saved.Count + ' files, which is far short of a usable backup')
        }

        $registryExports = @($saved | Where-Object { $_.Extension -eq '.reg' -and $_.Length -gt 0 })
        if ($registryExports.Count -eq 0) {
            $problems += 'no registry export was written, so the network keys could not be restored'
        }
    }

    if ($problems.Count -eq 0) {
        Write-Log ('Snapshot verified before ' + $Stage + '.')
        return
    }

    Write-Section 'Snapshot verification failed'
    foreach ($problem in $problems) {
        Write-Log ('PROBLEM: ' + $problem)
    }
    Write-Log ($Stage + ' was NOT started. Nothing on this machine has been changed.')
    Write-Log 'Fix the backup folder — free space, permissions, antivirus — and run again.'
    exit 1
}

function Save-TextFile {
    param(
        [string]$FileName,
        [string[]]$Lines
    )
    $path = Join-Path $script:BackupDir $FileName
    try {
        $Lines | Out-File -LiteralPath $path -Encoding UTF8 -Force
        Write-Log "Saved: $FileName"
    }
    catch {
        Write-Log "WARN: Could not save $FileName"
        Write-Log $_.Exception.Message
    }
}

function Invoke-ExternalToFile {
    param(
        [string]$FileName,
        [string]$CommandLine,
        [switch]$AlsoConsole
    )

    $path = Join-Path $script:BackupDir $FileName
    try {
        Add-Content -LiteralPath $path -Value "> $CommandLine" -Encoding UTF8
        Add-Content -LiteralPath $path -Value '' -Encoding UTF8
        Write-Log "Running: $CommandLine"
        $output = cmd.exe /d /c $CommandLine 2>&1
        if ($null -eq $output) { $output = @() }
        $output | Out-File -LiteralPath $path -Append -Encoding UTF8
        if ($AlsoConsole) {
            foreach ($line in $output) { Write-Host $line }
        }
        Write-Log "Exit code: $LASTEXITCODE"
        return $LASTEXITCODE
    }
    catch {
        Add-Content -LiteralPath $path -Value $_.Exception.Message -Encoding UTF8
        Write-Log "WARN: Command failed: $CommandLine"
        Write-Log $_.Exception.Message
        return 9999
    }
}

function Export-ObjectSnapshot {
    param(
        [string]$BaseName,
        [scriptblock]$Block,
        [int]$JsonDepth = 16
    )

    $txtPath = Join-Path $script:BackupDir ($BaseName + '.txt')
    $jsonPath = Join-Path $script:BackupDir ($BaseName + '.json')

    try {
        $data = & $Block
        if ($null -eq $data) {
            'No data returned.' | Out-File -LiteralPath $txtPath -Encoding UTF8 -Force
            'null' | Out-File -LiteralPath $jsonPath -Encoding UTF8 -Force
        }
        else {
            $data | Format-List * | Out-String -Width 4096 | Out-File -LiteralPath $txtPath -Encoding UTF8 -Force
            $data | ConvertTo-Json -Depth $JsonDepth | Out-File -LiteralPath $jsonPath -Encoding UTF8 -Force
        }
        Write-Log "Saved: $BaseName.txt and $BaseName.json"
    }
    catch {
        "ERROR: $($_.Exception.Message)" | Out-File -LiteralPath $txtPath -Encoding UTF8 -Force
        Write-Log "WARN: Could not export $BaseName"
        Write-Log $_.Exception.Message
    }
}

function Export-RegistryKey {
    param(
        [string]$Key,
        [string]$FileName
    )

    $dest = Join-Path $script:BackupDir $FileName
    $logName = $FileName + '.log.txt'
    $command = 'reg.exe export "' + $Key + '" "' + $dest + '" /y'
    Invoke-ExternalToFile -FileName $logName -CommandLine $command | Out-Null
}

function Copy-IfExists {
    param(
        [string]$Source,
        [string]$DestinationName
    )

    try {
        if (Test-Path -LiteralPath $Source) {
            $dest = Join-Path $script:BackupDir $DestinationName
            Copy-Item -LiteralPath $Source -Destination $dest -Force
            Write-Log "Copied: $DestinationName"
            try {
                Get-FileHash -LiteralPath $Source -Algorithm SHA256 | Format-List * | Out-File -LiteralPath (Join-Path $script:BackupDir ($DestinationName + '.source.sha256.txt')) -Encoding UTF8 -Force
                Get-FileHash -LiteralPath $dest -Algorithm SHA256 | Format-List * | Out-File -LiteralPath (Join-Path $script:BackupDir ($DestinationName + '.backup.sha256.txt')) -Encoding UTF8 -Force
            }
            catch { }
        }
        else {
            Write-Log "Skipped missing file: $Source"
        }
    }
    catch {
        Write-Log "WARN: Could not copy $Source"
        Write-Log $_.Exception.Message
    }
}

function Save-NetworkState {
    param([switch]$IncludeWiFiKeys)

    Write-Section 'Saving network diagnostics and restore inputs'

    Invoke-ExternalToFile -FileName 'ipconfig_all.txt' -CommandLine 'ipconfig /all' | Out-Null
    Invoke-ExternalToFile -FileName 'route_print.txt' -CommandLine 'route print' | Out-Null
    Invoke-ExternalToFile -FileName 'netsh_interface_dump.txt' -CommandLine 'netsh -c interface dump' | Out-Null
    Invoke-ExternalToFile -FileName 'netsh_int_ip_show_config.txt' -CommandLine 'netsh int ip show config' | Out-Null
    Invoke-ExternalToFile -FileName 'netsh_ipv4_interfaces.txt' -CommandLine 'netsh interface ipv4 show interfaces' | Out-Null
    Invoke-ExternalToFile -FileName 'netsh_ipv4_dnsservers.txt' -CommandLine 'netsh interface ipv4 show dnsservers' | Out-Null
    Invoke-ExternalToFile -FileName 'netsh_ipv4_addresses.txt' -CommandLine 'netsh interface ipv4 show addresses' | Out-Null
    Invoke-ExternalToFile -FileName 'netsh_ipv4_route.txt' -CommandLine 'netsh interface ipv4 show route' | Out-Null
    Invoke-ExternalToFile -FileName 'netsh_ipv6_interfaces.txt' -CommandLine 'netsh interface ipv6 show interfaces' | Out-Null
    Invoke-ExternalToFile -FileName 'netsh_winhttp_proxy.txt' -CommandLine 'netsh winhttp show proxy' | Out-Null
    Invoke-ExternalToFile -FileName 'winsock_catalog.txt' -CommandLine 'netsh winsock show catalog' | Out-Null
    Invoke-ExternalToFile -FileName 'firewall_profiles.txt' -CommandLine 'netsh advfirewall show allprofiles' | Out-Null

    $firewallDest = Join-Path $script:BackupDir 'firewall_policy_backup.wfw'
    Invoke-ExternalToFile -FileName 'firewall_export.log.txt' -CommandLine ('netsh advfirewall export "' + $firewallDest + '"') | Out-Null

    $wifiDir = Join-Path $script:BackupDir 'wifi_profiles_no_keys'
    New-Item -ItemType Directory -Path $wifiDir -Force | Out-Null
    Invoke-ExternalToFile -FileName 'wifi_profiles_export_no_keys.log.txt' -CommandLine ('netsh wlan export profile folder="' + $wifiDir + '"') | Out-Null
    Invoke-ExternalToFile -FileName 'wifi_interfaces.txt' -CommandLine 'netsh wlan show interfaces' | Out-Null
    Invoke-ExternalToFile -FileName 'wifi_profiles_list.txt' -CommandLine 'netsh wlan show profiles' | Out-Null

    if ($IncludeWiFiKeys) {
        $wifiKeyDir = Join-Path $script:BackupDir 'wifi_profiles_WITH_CLEAR_KEYS_SENSITIVE'
        New-Item -ItemType Directory -Path $wifiKeyDir -Force | Out-Null
        Invoke-ExternalToFile -FileName 'wifi_profiles_export_WITH_CLEAR_KEYS_SENSITIVE.log.txt' -CommandLine ('netsh wlan export profile key=clear folder="' + $wifiKeyDir + '"') | Out-Null
        Write-Log 'Sensitive Wi-Fi profile export requested. Clear-text Wi-Fi keys may be present in XML files.'
    }

    Export-ObjectSnapshot -BaseName 'ps_get_netadapter' -Block { Get-NetAdapter | Sort-Object Name }
    Export-ObjectSnapshot -BaseName 'ps_get_netadapter_advanced_property' -Block { Get-NetAdapterAdvancedProperty -ErrorAction SilentlyContinue | Sort-Object Name, DisplayName } -JsonDepth 32
    Export-ObjectSnapshot -BaseName 'ps_get_netipconfiguration' -Block { Get-NetIPConfiguration } -JsonDepth 32
    Export-ObjectSnapshot -BaseName 'ps_get_netipaddress' -Block { Get-NetIPAddress | Sort-Object InterfaceAlias, AddressFamily, IPAddress } -JsonDepth 32
    Export-ObjectSnapshot -BaseName 'ps_get_netroute' -Block { Get-NetRoute | Sort-Object InterfaceAlias, DestinationPrefix, NextHop } -JsonDepth 10
    Export-ObjectSnapshot -BaseName 'ps_get_dnsclientserveraddress' -Block { Get-DnsClientServerAddress | Sort-Object InterfaceAlias, AddressFamily } -JsonDepth 32
    Export-ObjectSnapshot -BaseName 'ps_get_dnsclient' -Block { Get-DnsClient | Sort-Object InterfaceAlias } -JsonDepth 32
    Export-ObjectSnapshot -BaseName 'ps_get_netconnectionprofile' -Block { Get-NetConnectionProfile | Sort-Object Name } -JsonDepth 10
    Export-ObjectSnapshot -BaseName 'ps_get_netipinterface' -Block { Get-NetIPInterface | Sort-Object InterfaceAlias, AddressFamily } -JsonDepth 32
    Export-ObjectSnapshot -BaseName 'ps_get_vpnconnection_user' -Block { Get-VpnConnection -ErrorAction SilentlyContinue } -JsonDepth 10
    Export-ObjectSnapshot -BaseName 'ps_get_vpnconnection_alluser' -Block { Get-VpnConnection -AllUserConnection -ErrorAction SilentlyContinue } -JsonDepth 10
    Export-ObjectSnapshot -BaseName 'ps_get_windows_os' -Block { Get-CimInstance -ClassName Win32_OperatingSystem | Select-Object Caption, Version, BuildNumber, OSArchitecture, InstallDate, LastBootUpTime }

    Export-RegistryKey -Key 'HKLM\SYSTEM\CurrentControlSet\Services\Tcpip\Parameters' -FileName 'reg_hklm_tcpip_parameters.reg'
    Export-RegistryKey -Key 'HKLM\SYSTEM\CurrentControlSet\Services\Tcpip\Parameters\Interfaces' -FileName 'reg_hklm_tcpip_interfaces.reg'
    Export-RegistryKey -Key 'HKLM\SYSTEM\CurrentControlSet\Services\Tcpip6\Parameters' -FileName 'reg_hklm_tcpip6_parameters.reg'
    Export-RegistryKey -Key 'HKLM\SYSTEM\CurrentControlSet\Services\Tcpip6\Parameters\Interfaces' -FileName 'reg_hklm_tcpip6_interfaces.reg'
    Export-RegistryKey -Key 'HKLM\SYSTEM\CurrentControlSet\Services\WinSock2\Parameters' -FileName 'reg_hklm_winsock2_parameters.reg'
    Export-RegistryKey -Key 'HKLM\SYSTEM\CurrentControlSet\Services\NetBT\Parameters' -FileName 'reg_hklm_netbt_parameters.reg'
    Export-RegistryKey -Key 'HKLM\SYSTEM\CurrentControlSet\Services\NetBT\Parameters\Interfaces' -FileName 'reg_hklm_netbt_interfaces.reg'
    Export-RegistryKey -Key 'HKLM\SOFTWARE\Microsoft\Windows NT\CurrentVersion\NetworkList\Profiles' -FileName 'reg_hklm_network_profiles.reg'
    Export-RegistryKey -Key 'HKLM\SOFTWARE\Microsoft\Windows NT\CurrentVersion\NetworkList\Signatures' -FileName 'reg_hklm_network_signatures.reg'
    Export-RegistryKey -Key 'HKLM\SOFTWARE\Microsoft\Windows\CurrentVersion\Internet Settings\Connections' -FileName 'reg_hklm_internet_settings_connections.reg'
    Export-RegistryKey -Key 'HKCU\Software\Microsoft\Windows\CurrentVersion\Internet Settings' -FileName 'reg_hkcu_internet_settings.reg'

    Copy-IfExists -Source (Join-Path $env:SystemRoot 'System32\drivers\etc\hosts') -DestinationName 'hosts_backup_original.bin'

    $manifest = [ordered]@{
        tool = 'Audion Network Cleaner'
        version = '2.0-TimeMachine'
        created = (Get-Date -Format 'yyyy-MM-dd HH:mm:ss')
        reason = (Split-Path -Leaf $script:BackupDir)
        computer = $env:COMPUTERNAME
        user = $env:USERNAME
        include_wifi_keys = [bool]$IncludeWiFiKeys
        backup_dir = $script:BackupDir
        restore_inputs = @(
            'hosts_backup_original.bin',
            'netsh_interface_dump.txt',
            'firewall_policy_backup.wfw',
            'wifi_profiles_no_keys/*.xml',
            'wifi_profiles_WITH_CLEAR_KEYS_SENSITIVE/*.xml',
            'reg_*.reg'
        )
    }
    $manifest | ConvertTo-Json -Depth 8 | Out-File -LiteralPath (Join-Path $script:BackupDir 'restore_manifest.json') -Encoding UTF8 -Force

    Write-Log 'Network diagnostics and restore inputs saved.'
}

function Show-StatusSummary {
    Write-Section 'Network status summary'

    try {
        Write-Host ''
        Write-Host 'Active adapters:'
        Get-NetAdapter | Where-Object { $_.Status -eq 'Up' } | Sort-Object Name | Format-Table -AutoSize Name, InterfaceDescription, LinkSpeed, MacAddress | Out-Host
    }
    catch {
        Write-Log 'WARN: Could not read active adapters.'
    }

    try {
        Write-Host ''
        Write-Host 'Connection profiles:'
        Get-NetConnectionProfile | Sort-Object Name | Format-Table -AutoSize Name, InterfaceAlias, NetworkCategory, IPv4Connectivity, IPv6Connectivity | Out-Host
    }
    catch {
        Write-Log 'WARN: Could not read connection profiles.'
    }

    try {
        Write-Host ''
        Write-Host 'DNS servers:'
        Get-DnsClientServerAddress | Where-Object { $_.ServerAddresses } | Sort-Object InterfaceAlias, AddressFamily | Format-Table -AutoSize InterfaceAlias, AddressFamily, ServerAddresses | Out-Host
    }
    catch {
        Write-Log 'WARN: Could not read DNS servers.'
    }

    try {
        Write-Host ''
        Write-Host 'Default routes:'
        Get-NetRoute -DestinationPrefix '0.0.0.0/0' -ErrorAction SilentlyContinue | Sort-Object RouteMetric | Format-Table -AutoSize InterfaceAlias, NextHop, RouteMetric, ifMetric | Out-Host
        Get-NetRoute -DestinationPrefix '::/0' -ErrorAction SilentlyContinue | Sort-Object RouteMetric | Format-Table -AutoSize InterfaceAlias, NextHop, RouteMetric, ifMetric | Out-Host
    }
    catch {
        Write-Log 'WARN: Could not read default routes.'
    }

    Invoke-ExternalToFile -FileName 'status_winhttp_proxy_console.txt' -CommandLine 'netsh winhttp show proxy' -AlsoConsole | Out-Null

    Write-Log "Status backup folder: $script:BackupDir"
}

function Invoke-LightRepair {
    Write-Section 'Light Repair'
    Write-Log 'This mode avoids route reset, TCP/IP reset, Winsock reset, firewall reset, event log cleanup, and Wi-Fi profile deletion.'

    Invoke-ExternalToFile -FileName 'repair_flushdns.txt' -CommandLine 'ipconfig /flushdns' -AlsoConsole | Out-Null
    Invoke-ExternalToFile -FileName 'repair_registerdns.txt' -CommandLine 'ipconfig /registerdns' -AlsoConsole | Out-Null
    Invoke-ExternalToFile -FileName 'repair_arp_cache.txt' -CommandLine 'netsh interface ip delete arpcache' -AlsoConsole | Out-Null
    Invoke-ExternalToFile -FileName 'repair_nbtstat_R.txt' -CommandLine 'nbtstat -R' -AlsoConsole | Out-Null
    Invoke-ExternalToFile -FileName 'repair_nbtstat_RR.txt' -CommandLine 'nbtstat -RR' -AlsoConsole | Out-Null

    try {
        $dhcpIfs = Get-NetIPInterface -AddressFamily IPv4 -ErrorAction SilentlyContinue | Where-Object { $_.Dhcp -eq 'Enabled' -and $_.ConnectionState -eq 'Connected' }
        if ($dhcpIfs) {
            foreach ($iface in $dhcpIfs) {
                $alias = [string]$iface.InterfaceAlias
                $safeName = ($alias -replace '[^a-zA-Z0-9_-]', '_')
                Invoke-ExternalToFile -FileName "repair_ipconfig_renew_${safeName}.txt" -CommandLine ('ipconfig /renew "' + $alias + '"') -AlsoConsole | Out-Null
            }
        }
        else {
            Write-Log 'No connected DHCP IPv4 interfaces found for targeted renew.'
        }
    }
    catch {
        Write-Log 'WARN: Targeted DHCP renew failed.'
        Write-Log $_.Exception.Message
    }

    Write-Log 'Light Repair completed.'
}

function Invoke-StandardRepair {
    Write-Section 'Standard Repair'
    Write-Log 'This mode resets Winsock, TCP/IP stack, WinHTTP proxy, DNS cache, and ARP cache.'
    Write-Log 'It does not reset firewall, does not delete Wi-Fi profiles, does not clean event logs, and does not run route -f.'

    Invoke-ExternalToFile -FileName 'repair_winsock_reset.txt' -CommandLine 'netsh winsock reset' -AlsoConsole | Out-Null

    $tcpLog = Join-Path $script:BackupDir 'tcpip_reset_native.log'
    Invoke-ExternalToFile -FileName 'repair_tcpip_reset.txt' -CommandLine ('netsh int ip reset "' + $tcpLog + '"') -AlsoConsole | Out-Null

    Invoke-ExternalToFile -FileName 'repair_winhttp_reset_proxy.txt' -CommandLine 'netsh winhttp reset proxy' -AlsoConsole | Out-Null
    Invoke-ExternalToFile -FileName 'repair_flushdns.txt' -CommandLine 'ipconfig /flushdns' -AlsoConsole | Out-Null
    Invoke-ExternalToFile -FileName 'repair_registerdns.txt' -CommandLine 'ipconfig /registerdns' -AlsoConsole | Out-Null
    Invoke-ExternalToFile -FileName 'repair_arp_cache.txt' -CommandLine 'netsh interface ip delete arpcache' -AlsoConsole | Out-Null

    Write-Log 'Standard Repair completed.'
    Write-Log 'Reboot is strongly recommended before judging the result.'
}

function Invoke-NuclearRepair {
    Write-Section 'Nuclear Repair warning'
    Write-Host ''
    Write-Host 'This mode is intentionally dangerous but still recover-oriented.'
    Write-Host 'It runs Standard Repair and additionally flushes the routing table with route -f.'
    Write-Host 'It still does not delete Wi-Fi profiles, does not reset firewall, does not clean event logs, and does not touch hosts.'
    Write-Host ''
    $confirm = Read-Host 'Type NUCLEAR to continue, or press Enter to abort'
    if ($confirm -ne 'NUCLEAR') {
        Write-Log 'Nuclear Repair aborted by user.'
        return
    }

    Invoke-StandardRepair
    Invoke-ExternalToFile -FileName 'repair_route_f_DANGEROUS.txt' -CommandLine 'route -f' -AlsoConsole | Out-Null

    Write-Host ''
    Write-Host 'Optional adapter reinstall step: netcfg -d'
    Write-Host 'This removes and reinstalls network adapters after reboot. VPN, Hyper-V, WSL and virtual adapters may need repair.'
    $netcfgConfirm = Read-Host 'Type NETCFG-D to run it, or press Enter to skip'
    if ($netcfgConfirm -eq 'NETCFG-D') {
        Invoke-ExternalToFile -FileName 'repair_netcfg_d_VERY_DANGEROUS.txt' -CommandLine 'netcfg -d' -AlsoConsole | Out-Null
        Write-Log 'netcfg -d was executed. Reboot is required.'
    }
    else {
        Write-Log 'netcfg -d skipped.'
    }

    Write-Log 'Nuclear Repair completed.'
    Write-Log 'Reboot is required.'
}

function Invoke-GodzillaStrike {
    Write-Section 'Godzilla Strike warning'
    Write-Host ''
    Write-Host 'This is the final destructive network strike.'
    Write-Host 'Use it only when Windows is already considered disposable or before reinstall.'
    Write-Host 'It can reset firewall, routes, TCP/IP, Winsock, WinHTTP, DNS, DHCP, and optionally Wi-Fi profiles and adapter database.'
    Write-Host ''
    $confirm = Read-Host 'Type GODZILLA to continue, or press Enter to abort'
    if ($confirm -ne 'GODZILLA') {
        Write-Log 'Godzilla Strike aborted by user.'
        return
    }

    Invoke-ExternalToFile -FileName 'godzilla_winsock_reset_catalog.txt' -CommandLine 'netsh winsock reset catalog' -AlsoConsole | Out-Null
    Invoke-ExternalToFile -FileName 'godzilla_int_ip_reset.txt' -CommandLine ('netsh int ip reset "' + (Join-Path $script:BackupDir 'godzilla_tcpip_reset_native.log') + '"') -AlsoConsole | Out-Null
    Invoke-ExternalToFile -FileName 'godzilla_int_ipv4_reset.txt' -CommandLine 'netsh int ipv4 reset' -AlsoConsole | Out-Null
    Invoke-ExternalToFile -FileName 'godzilla_int_ipv6_reset.txt' -CommandLine 'netsh int ipv6 reset' -AlsoConsole | Out-Null
    Invoke-ExternalToFile -FileName 'godzilla_winhttp_reset_proxy.txt' -CommandLine 'netsh winhttp reset proxy' -AlsoConsole | Out-Null
    Invoke-ExternalToFile -FileName 'godzilla_flushdns.txt' -CommandLine 'ipconfig /flushdns' -AlsoConsole | Out-Null
    Invoke-ExternalToFile -FileName 'godzilla_registerdns.txt' -CommandLine 'ipconfig /registerdns' -AlsoConsole | Out-Null
    Invoke-ExternalToFile -FileName 'godzilla_release_all.txt' -CommandLine 'ipconfig /release' -AlsoConsole | Out-Null
    Invoke-ExternalToFile -FileName 'godzilla_route_f.txt' -CommandLine 'route -f' -AlsoConsole | Out-Null
    Invoke-ExternalToFile -FileName 'godzilla_arp_cache.txt' -CommandLine 'netsh interface ip delete arpcache' -AlsoConsole | Out-Null

    Write-Host ''
    $fwConfirm = Read-Host 'Type FIREWALL-RESET to reset Windows Firewall rules, or press Enter to skip'
    if ($fwConfirm -eq 'FIREWALL-RESET') {
        Invoke-ExternalToFile -FileName 'godzilla_advfirewall_reset.txt' -CommandLine 'netsh advfirewall reset' -AlsoConsole | Out-Null
    }
    else {
        Write-Log 'Firewall reset skipped.'
    }

    Write-Host ''
    $wifiConfirm = Read-Host 'Type DELETE-WIFI-PROFILES to delete all Wi-Fi profiles, or press Enter to skip'
    if ($wifiConfirm -eq 'DELETE-WIFI-PROFILES') {
        Invoke-ExternalToFile -FileName 'godzilla_delete_wifi_profiles.txt' -CommandLine 'netsh wlan delete profile name=*' -AlsoConsole | Out-Null
    }
    else {
        Write-Log 'Wi-Fi profile deletion skipped.'
    }

    Write-Host ''
    $netcfgConfirm = Read-Host 'Type NETCFG-D to remove/reinstall all network adapters after reboot, or press Enter to skip'
    if ($netcfgConfirm -eq 'NETCFG-D') {
        Invoke-ExternalToFile -FileName 'godzilla_netcfg_d.txt' -CommandLine 'netcfg -d' -AlsoConsole | Out-Null
    }
    else {
        Write-Log 'netcfg -d skipped.'
    }

    Write-Host ''
    $renewConfirm = Read-Host 'Type RENEW to attempt ipconfig /renew now, or press Enter to skip and reboot first'
    if ($renewConfirm -eq 'RENEW') {
        Invoke-ExternalToFile -FileName 'godzilla_renew_all.txt' -CommandLine 'ipconfig /renew' -AlsoConsole | Out-Null
    }
    else {
        Write-Log 'DHCP renew skipped.'
    }

    Write-Log 'Godzilla Strike completed.'
    Write-Log 'Reboot is required.'
}

function Get-BackupSnapshots {
    if (-not (Test-Path -LiteralPath $script:BackupRoot)) { return @() }
    return @(Get-ChildItem -LiteralPath $script:BackupRoot -Directory -ErrorAction SilentlyContinue | Where-Object { $_.Name -like 'network_backup_*' } | Sort-Object LastWriteTime -Descending)
}

function Resolve-RestoreSnapshot {
    param([string]$SelectionMode)

    $snapshots = Get-BackupSnapshots
    if (-not $snapshots -or $snapshots.Count -eq 0) {
        Write-Log 'ERROR: No backup snapshots found.'
        return $null
    }

    if ($SelectionMode -eq 'Latest') {
        $lastFile = Join-Path $script:BackupRoot '_last_snapshot.txt'
        if (Test-Path -LiteralPath $lastFile) {
            try {
                $lastPath = (Get-Content -LiteralPath $lastFile -Raw -ErrorAction Stop).Trim()
                if ($lastPath -and (Test-Path -LiteralPath $lastPath)) {
                    return $lastPath
                }
            }
            catch { }
        }
        return $snapshots[0].FullName
    }

    Write-Host ''
    Write-Host 'Available snapshots:'
    for ($i = 0; $i -lt $snapshots.Count; $i++) {
        $n = $i + 1
        Write-Host ("{0}. {1}  {2}" -f $n, $snapshots[$i].LastWriteTime.ToString('yyyy-MM-dd HH:mm:ss'), $snapshots[$i].Name)
    }
    Write-Host ''
    $answer = Read-Host 'Enter snapshot number to restore, or press Enter to abort'
    if ([string]::IsNullOrWhiteSpace($answer)) { return $null }
    $index = 0
    if (-not [int]::TryParse($answer, [ref]$index)) {
        Write-Log 'ERROR: Invalid selection.'
        return $null
    }
    if ($index -lt 1 -or $index -gt $snapshots.Count) {
        Write-Log 'ERROR: Selection is out of range.'
        return $null
    }
    return $snapshots[$index - 1].FullName
}

function Import-RegIfExists {
    param(
        [string]$SnapshotDir,
        [string]$FileName
    )
    $path = Join-Path $SnapshotDir $FileName
    if (Test-Path -LiteralPath $path) {
        Invoke-ExternalToFile -FileName ('restore_' + $FileName + '.log.txt') -CommandLine ('reg.exe import "' + $path + '"') -AlsoConsole | Out-Null
    }
    else {
        Write-Log "Skipped missing registry backup: $FileName"
    }
}

function Restore-HostsIfExists {
    param([string]$SnapshotDir)
    $source = Join-Path $SnapshotDir 'hosts_backup_original.bin'
    $target = Join-Path $env:SystemRoot 'System32\drivers\etc\hosts'
    if (-not (Test-Path -LiteralPath $source)) {
        Write-Log 'Skipped hosts restore: backup file is missing.'
        return
    }
    try {
        $before = Join-Path $script:BackupDir 'hosts_before_restore_current.bin'
        if (Test-Path -LiteralPath $target) {
            Copy-Item -LiteralPath $target -Destination $before -Force
        }
        Copy-Item -LiteralPath $source -Destination $target -Force
        Write-Log 'hosts restored from binary backup.'
        try {
            Get-FileHash -LiteralPath $source -Algorithm SHA256 | Format-List * | Out-File -LiteralPath (Join-Path $script:BackupDir 'hosts_restore_source.sha256.txt') -Encoding UTF8 -Force
            Get-FileHash -LiteralPath $target -Algorithm SHA256 | Format-List * | Out-File -LiteralPath (Join-Path $script:BackupDir 'hosts_restore_target.sha256.txt') -Encoding UTF8 -Force
        }
        catch { }
    }
    catch {
        Write-Log 'WARN: hosts restore failed.'
        Write-Log $_.Exception.Message
    }
}

function Restore-WiFiProfilesIfExist {
    param([string]$SnapshotDir)

    $dirs = @(
        (Join-Path $SnapshotDir 'wifi_profiles_WITH_CLEAR_KEYS_SENSITIVE'),
        (Join-Path $SnapshotDir 'wifi_profiles_no_keys')
    )

    foreach ($dir in $dirs) {
        if (Test-Path -LiteralPath $dir) {
            $profiles = @(Get-ChildItem -LiteralPath $dir -Filter '*.xml' -File -ErrorAction SilentlyContinue)
            foreach ($p in $profiles) {
                $safe = ($p.BaseName -replace '[^a-zA-Z0-9_-]', '_')
                Invoke-ExternalToFile -FileName "restore_wifi_profile_${safe}.log.txt" -CommandLine ('netsh wlan add profile filename="' + $p.FullName + '" user=all') -AlsoConsole | Out-Null
            }
        }
    }
}

function Invoke-TimeMachineRestore {
    param([string]$SelectionMode)

    Write-Section 'TimeMachine Restore'
    $snapshot = Resolve-RestoreSnapshot -SelectionMode $SelectionMode
    if (-not $snapshot) {
        Write-Log 'Restore aborted: no snapshot selected.'
        return
    }

    Write-Host ''
    Write-Host 'Selected snapshot:'
    Write-Host $snapshot
    Write-Host ''
    Write-Host 'This will import saved registry exports, restore hosts, restore firewall policy, run saved netsh interface dump, and re-add saved Wi-Fi profiles.'
    Write-Host 'A fresh backup of the current broken state will be created first.'
    Write-Host ''
    $confirm = Read-Host 'Type RESTORE to continue, or press Enter to abort'
    if ($confirm -ne 'RESTORE') {
        Write-Log 'Restore aborted by user.'
        return
    }

    New-BackupSnapshot -Reason 'BeforeTimeMachineRestore'
    Save-NetworkState
    try {
        Set-Content -LiteralPath (Join-Path $script:BackupRoot '_last_snapshot.txt') -Value $snapshot -Encoding UTF8
    }
    catch { }

    Write-Section 'Restoring selected snapshot'
    Write-Log "Restore source: $snapshot"

    Restore-HostsIfExists -SnapshotDir $snapshot

    Import-RegIfExists -SnapshotDir $snapshot -FileName 'reg_hkcu_internet_settings.reg'
    Import-RegIfExists -SnapshotDir $snapshot -FileName 'reg_hklm_internet_settings_connections.reg'
    Import-RegIfExists -SnapshotDir $snapshot -FileName 'reg_hklm_network_profiles.reg'
    Import-RegIfExists -SnapshotDir $snapshot -FileName 'reg_hklm_network_signatures.reg'
    Import-RegIfExists -SnapshotDir $snapshot -FileName 'reg_hklm_tcpip_parameters.reg'
    Import-RegIfExists -SnapshotDir $snapshot -FileName 'reg_hklm_tcpip_interfaces.reg'
    Import-RegIfExists -SnapshotDir $snapshot -FileName 'reg_hklm_tcpip6_parameters.reg'
    Import-RegIfExists -SnapshotDir $snapshot -FileName 'reg_hklm_tcpip6_interfaces.reg'
    Import-RegIfExists -SnapshotDir $snapshot -FileName 'reg_hklm_netbt_parameters.reg'
    Import-RegIfExists -SnapshotDir $snapshot -FileName 'reg_hklm_netbt_interfaces.reg'
    Import-RegIfExists -SnapshotDir $snapshot -FileName 'reg_hklm_winsock2_parameters.reg'

    $firewall = Join-Path $snapshot 'firewall_policy_backup.wfw'
    if (Test-Path -LiteralPath $firewall) {
        Invoke-ExternalToFile -FileName 'restore_firewall_import.log.txt' -CommandLine ('netsh advfirewall import "' + $firewall + '"') -AlsoConsole | Out-Null
    }
    else {
        Write-Log 'Skipped firewall restore: .wfw backup is missing.'
    }

    $netshDump = Join-Path $snapshot 'netsh_interface_dump.txt'
    if (Test-Path -LiteralPath $netshDump) {
        Invoke-ExternalToFile -FileName 'restore_netsh_interface_dump.log.txt' -CommandLine ('netsh -f "' + $netshDump + '"') -AlsoConsole | Out-Null
    }
    else {
        Write-Log 'Skipped netsh interface restore: dump is missing.'
    }

    Restore-WiFiProfilesIfExist -SnapshotDir $snapshot

    Invoke-ExternalToFile -FileName 'restore_flushdns.txt' -CommandLine 'ipconfig /flushdns' -AlsoConsole | Out-Null
    Invoke-ExternalToFile -FileName 'restore_registerdns.txt' -CommandLine 'ipconfig /registerdns' -AlsoConsole | Out-Null

    Write-Log 'TimeMachine Restore completed.'
    Write-Log 'Reboot is strongly recommended before judging the result.'
}

function Show-Help {
    Write-Host 'Audion Network Cleaner v2 - TimeMachine edition'
    Write-Host ''
    Write-Host 'Modes:'
    Write-Host '  Status             Save diagnostics and show current network summary.'
    Write-Host '  Backup             Save diagnostics and restore inputs only.'
    Write-Host '  BackupWithWiFiKeys Save diagnostics and Wi-Fi profiles with clear keys. Sensitive.'
    Write-Host '  LightRepair        Safe DNS, ARP, NetBIOS refresh and targeted DHCP renew.'
    Write-Host '  StandardRepair     Winsock, TCP/IP, WinHTTP proxy, DNS and ARP reset.'
    Write-Host '  NuclearRepair      Standard Repair plus route -f and optional netcfg -d.'
    Write-Host '  RestoreLatest      Restore from the last snapshot, after backing up current state.'
    Write-Host '  RestoreSelect      Select snapshot to restore, after backing up current state.'
    Write-Host '  GodzillaStrike     Final destructive network strike. Use only before reinstall.'
    Write-Host '  OpenBackup         Open project backup folder.'
}

function Open-BackupFolder {
    if (-not (Test-Path -LiteralPath $script:BackupRoot)) {
        New-Item -ItemType Directory -Path $script:BackupRoot -Force | Out-Null
    }
    Start-Process explorer.exe -ArgumentList ('"' + $script:BackupRoot + '"')
}

if ($Mode -eq 'Help') {
    Show-Help
    exit 0
}

if ($Mode -eq 'OpenBackup') {
    Open-BackupFolder
    exit 0
}

if (-not (Test-Administrator)) {
    Write-Host 'ERROR: This script must run as Administrator.' -ForegroundColor Red
    Write-Host 'Use the CMD launchers from the project root. They request UAC automatically.'
    exit 1
}

try {
    switch ($Mode) {
        'Status' {
            New-BackupSnapshot -Reason 'Status'
            Save-NetworkState
            Show-StatusSummary
        }
        'Backup' {
            New-BackupSnapshot -Reason 'Backup'
            Save-NetworkState
            Write-Log "Backup completed: $script:BackupDir"
        }
        'BackupWithWiFiKeys' {
            Write-Host 'WARNING: This exports Wi-Fi profiles with clear-text keys into the project backup folder.'
            $confirm = Read-Host 'Type WIFI-KEYS to continue, or press Enter to abort'
            if ($confirm -ne 'WIFI-KEYS') { Write-Host 'Aborted.'; exit 0 }
            New-BackupSnapshot -Reason 'BackupWithWiFiKeys_SENSITIVE'
            Save-NetworkState -IncludeWiFiKeys
            Write-Log "Sensitive backup completed: $script:BackupDir"
        }
        'LightRepair' {
            New-BackupSnapshot -Reason 'LightRepair'
            Save-NetworkState
            Assert-SnapshotUsable -Stage 'Light Repair'
            Invoke-LightRepair
        }
        'StandardRepair' {
            New-BackupSnapshot -Reason 'StandardRepair'
            Save-NetworkState
            Assert-SnapshotUsable -Stage 'Standard Repair'
            Invoke-StandardRepair
        }
        'NuclearRepair' {
            New-BackupSnapshot -Reason 'NuclearRepair'
            Save-NetworkState
            Assert-SnapshotUsable -Stage 'Nuclear Repair'
            Invoke-NuclearRepair
        }
        'GodzillaStrike' {
            Write-Host 'Godzilla mode can optionally export Wi-Fi profiles with clear keys before destructive steps.'
            $keyAnswer = Read-Host 'Type WIFI-KEYS to include clear Wi-Fi keys in the pre-strike backup, or press Enter for normal backup'
            New-BackupSnapshot -Reason 'GodzillaStrike_PreBackup'
            if ($keyAnswer -eq 'WIFI-KEYS') {
                Save-NetworkState -IncludeWiFiKeys
            }
            else {
                Save-NetworkState
            }
            Assert-SnapshotUsable -Stage 'Godzilla Strike'
            Invoke-GodzillaStrike
        }
        'RestoreLatest' {
            Invoke-TimeMachineRestore -SelectionMode 'Latest'
        }
        'RestoreSelect' {
            Invoke-TimeMachineRestore -SelectionMode 'Select'
        }
    }
}
catch {
    Write-Log 'ERROR: Unhandled failure.'
    Write-Log $_.Exception.Message
    exit 1
}

Write-Log ''
Write-Log 'Done.'
exit 0
