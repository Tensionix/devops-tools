<#
Audion DNS Doctor
Name resolution and the network status icon on this machine.

Two failures look like a dead link while the link is alive:

  * names stop resolving because the adapters point at a local resolver
    (ControlD, YogaDNS, AdGuard, dnscrypt) that is not running - addresses
    still ping, no site opens;
  * sites open while Windows shows "no internet" because NlaSvc, the service
    that probes for a way out and draws the tray icon, is stopped.

The tool reports what it found, repairs what is clearly broken, and can hand
name resolution to a chosen resolver. Tunnel adapters are left alone: the
tunnel sets DNS there itself.

Terminal output is English by design to avoid encoding problems in
CMD/PowerShell consoles.
#>

param(
    [ValidateSet('Status', 'Repair', 'FixIcon', 'UseAuto', 'UseRouter', 'UseCloudflare',
                 'UseGoogle', 'UseQuad9', 'UseYandex', 'UseAdGuard', 'Help')]
    [string]$Mode = 'Status'
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Continue'

# Local resolver services seen on real machines. The list only serves to start
# a stopped service by name; anything else is detected by who holds port 53.
$script:ResolverNames = 'ctrld|yoga|adguard|dnscrypt|technitium|acrylic|unbound|stubby'

# Tunnel adapters: the tunnel sets DNS there, and that is not our business.
$script:TunnelAdapters = 'WireGuard|Amnezia|Wintun|TAP|VPN|OpenVPN'

# Public resolvers. Addresses are open, each has its own temper: Quad9 blocks
# malicious names, AdGuard also ad and tracking ones, Yandex is the closest
# hop from here. The list is not about "better" - it is about choice.
$script:Providers = [ordered]@{
    UseAuto       = @{ Title = 'Router (DHCP)'; Servers = @() }
    UseRouter     = @{ Title = 'The router itself'; Servers = @() }
    UseCloudflare = @{ Title = 'Cloudflare'; Servers = @('1.1.1.1', '1.0.0.1') }
    UseGoogle     = @{ Title = 'Google'; Servers = @('8.8.8.8', '8.8.4.4') }
    UseQuad9      = @{ Title = 'Quad9'; Servers = @('9.9.9.9', '149.112.112.112') }
    UseYandex     = @{ Title = 'Yandex'; Servers = @('77.88.8.8', '77.88.8.1') }
    UseAdGuard    = @{ Title = 'AdGuard'; Servers = @('94.140.14.14', '94.140.15.15') }
}

function Write-Line { param([string]$Text, [string]$Color = 'Gray') Write-Host "  $Text" -ForegroundColor $Color }

function Write-Section {
    param([string]$Title)
    Write-Host ''
    Write-Host "  $Title" -ForegroundColor Cyan
}

function Test-Administrator {
    try {
        $identity = [Security.Principal.WindowsIdentity]::GetCurrent()
        $principal = New-Object Security.Principal.WindowsPrincipal($identity)
        return $principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
    } catch {
        return $false
    }
}

function Get-TargetAdapters {
    <#
        The adapters whose DNS we touch: up and not a tunnel. "Physical" would
        overpromise - a Hyper-V switch or a sandbox adapter lands here too, and
        that is on purpose: they need names just the same.
    #>
    Get-NetAdapter | Where-Object {
        $_.Status -eq 'Up' -and $_.InterfaceDescription -notmatch $script:TunnelAdapters
    }
}

function Get-LocalListener {
    <# Who holds port 53 here. Empty means nobody can answer a name. #>
    $ends = @(Get-NetUDPEndpoint -LocalPort 53 -ErrorAction SilentlyContinue |
        Where-Object { $_.LocalAddress -in @('127.0.0.1', '::1', '0.0.0.0', '::') })
    if (-not $ends) { return $null }
    $proc = Get-Process -Id $ends[0].OwningProcess -ErrorAction SilentlyContinue
    if ($proc) { return $proc.ProcessName }
    return 'unknown process'
}

function Get-DhcpDns {
    <#
        What the router hands out over DHCP. Windows keeps it apart from the
        manual value: the interface key holds both NameServer (typed by hand)
        and DhcpNameServer (received from the router). The second one stays
        there while the first is set, so we can tell in advance what returning
        to automatic mode would give.
    #>
    param([Parameter(Mandatory)]$Adapter)
    $key = 'HKLM:\SYSTEM\CurrentControlSet\Services\Tcpip\Parameters\Interfaces\' + $Adapter.InterfaceGuid
    $p = Get-ItemProperty -Path $key -ErrorAction SilentlyContinue
    if ($p -and $p.PSObject.Properties['DhcpNameServer'] -and $p.DhcpNameServer) {
        return @($p.DhcpNameServer -split '[ ,]+' | Where-Object { $_ })
    }
    return @()
}

function Get-Gateway {
    param([Parameter(Mandatory)]$Adapter)
    try {
        $g = (Get-NetIPConfiguration -InterfaceIndex $Adapter.ifIndex -ErrorAction Stop).IPv4DefaultGateway
        if ($g) { return @($g.NextHop)[0] }
    } catch { }
    return $null
}

function Test-Resolver {
    <# Ask the named address for a name: an answer means it will do. #>
    param([Parameter(Mandatory)][string]$Server)
    try {
        $a = Resolve-DnsName 'ya.ru' -Type A -Server $Server -QuickTimeout -ErrorAction Stop
        return [bool]($a | Where-Object { $_.PSObject.Properties['IPAddress'] -and $_.IPAddress })
    } catch { return $false }
}

function Test-Names {
    <# The proof is a name turning into an address. #>
    try {
        $a = Resolve-DnsName 'ya.ru' -Type A -QuickTimeout -ErrorAction Stop
        $ip = @($a | Where-Object { $_.PSObject.Properties['IPAddress'] -and $_.IPAddress })[0]
        if ($ip) { return $ip.IPAddress }
    } catch { }
    return $null
}

function Get-Upstream {
    <#
        Who ends up asking outward. The router in the "DNS" field is not the
        answer: it asks someone in turn, and so on until a resolver reaches an
        authoritative server. Google keeps a service name that replies with the
        asker's address - that is the last hop; the reverse record often names
        its owner: dns.google, one.one.one.one, a node of the provider.
    #>
    $seen = $null
    foreach ($probe in @(
        @{ Name = 'o-o.myaddr.l.google.com'; Type = 'TXT' },
        @{ Name = 'whoami.akamai.net';       Type = 'A' })) {
        try {
            $a = Resolve-DnsName $probe.Name -Type $probe.Type -QuickTimeout -ErrorAction Stop
            if ($probe.Type -eq 'TXT') {
                $seen = @($a | Where-Object { $_.PSObject.Properties['Strings'] -and $_.Strings } |
                    ForEach-Object { $_.Strings })[0]
            } else {
                $seen = @($a | Where-Object { $_.PSObject.Properties['IPAddress'] -and $_.IPAddress } |
                    ForEach-Object { $_.IPAddress })[0]
            }
            if ($seen) { break }
        } catch { }
    }
    if (-not $seen) { return $null }

    # The reverse name is looked up for both protocols: IPv4 folds its bytes
    # backwards into in-addr.arpa, IPv6 its nibbles into ip6.arpa. Resolvers
    # increasingly answer over IPv6, and without this the owner stayed unknown.
    $who = $null
    try {
        $addr = [System.Net.IPAddress]::Parse($seen)
        $bytes = $addr.GetAddressBytes()
        if ($addr.AddressFamily -eq 'InterNetworkV6') {
            $hex = (($bytes | ForEach-Object { $_.ToString('x2') }) -join '').ToCharArray()
            [array]::Reverse($hex)
            $back = ($hex -join '.') + '.ip6.arpa'
        } else {
            [array]::Reverse($bytes)
            $back = (($bytes | ForEach-Object { $_.ToString() }) -join '.') + '.in-addr.arpa'
        }
        $ptr = Resolve-DnsName $back -Type PTR -QuickTimeout -ErrorAction Stop
        $who = @($ptr | Where-Object { $_.PSObject.Properties['NameHost'] -and $_.NameHost } |
            ForEach-Object { $_.NameHost })[0]
    } catch { }

    return @{ Address = $seen; Name = $who }
}

function Get-NlaState {
    <#
        The tray icon is drawn by NlaSvc - "Network Location Awareness" - not by
        the network itself. It probes a pair of Microsoft addresses and decides
        whether there is a way out. While it is stopped the profile sits on
        LocalNetwork, the tray shows a globe, Windows cannot tell a private
        network from a public one, and the firewall picks a profile blindly.
        Sites open all along: the internet is there, nobody says so.
    #>
    $svc = Get-CimInstance Win32_Service -Filter "Name='NlaSvc'" -ErrorAction SilentlyContinue
    $seen = @()
    try {
        $seen = @(Get-NetConnectionProfile -ErrorAction Stop | ForEach-Object { $_.IPv4Connectivity })
    } catch { }
    return @{
        Service = $svc
        Running = ($svc -and $svc.State -eq 'Running')
        Manual  = ($svc -and $svc.StartMode -ne 'Auto')
        Online  = [bool](@($seen | Where-Object { $_ -eq 'Internet' }).Count)
        Seen    = $seen
    }
}

function Set-Dns {
    <#
        Writes the addresses onto the adapters. Empty means DHCP.

        `PerAdapter` covers the case where each adapter has its own address -
        that is the "router itself" mode. The first gateway found used to be
        written to all of them, so with Ethernet and Wi-Fi on different networks
        one adapter got the neighbour segment's gateway, and lost names as soon
        as that link went down.
    #>
    param([string[]]$Servers, [Parameter(Mandatory)]$Adapters, [hashtable]$PerAdapter)

    foreach ($a in $Adapters) {
        $mine = $(if ($PerAdapter) { @($PerAdapter[[int]$a.ifIndex]) } else { $Servers })
        if ($PerAdapter -and -not $mine) {
            Write-Line ("{0,-26} has no gateway of its own - left as it was" -f $a.Name) Yellow
            continue
        }

        $was = @((Get-DnsClientServerAddress -InterfaceIndex $a.ifIndex -AddressFamily IPv4).ServerAddresses)
        try {
            if ($mine) {
                Set-DnsClientServerAddress -InterfaceIndex $a.ifIndex -ServerAddresses $mine -ErrorAction Stop
            } else {
                Set-DnsClientServerAddress -InterfaceIndex $a.ifIndex -ResetServerAddresses -ErrorAction Stop
            }
            $now = @((Get-DnsClientServerAddress -InterfaceIndex $a.ifIndex -AddressFamily IPv4).ServerAddresses)
            $shown = if ($now) { $now -join ', ' } else { 'router (DHCP)' }
            Write-Line ("{0,-26} was: {1,-20} now: {2}" -f $a.Name, ($was -join ', '), $shown) Green
        } catch {
            Write-Line ("{0,-26} failed: {1}" -f $a.Name, $_.Exception.Message) Yellow
        }
    }
    & ipconfig.exe /flushdns | Out-Null
}

function Show-Status {
    <# Everything the machine knows about its own name resolution. #>
    param([switch]$Quiet)

    Write-Section '[1] What is set now'

    $adapters = @(Get-TargetAdapters)
    if (-not $adapters) { Write-Line 'no network adapters are up - the machine is offline' Yellow }

    $onLocal = @()
    $gateway = $null
    $gateways = @{}
    foreach ($a in $adapters) {
        $dns = @((Get-DnsClientServerAddress -InterfaceIndex $a.ifIndex -AddressFamily IPv4).ServerAddresses)
        $shown = if ($dns) { $dns -join ', ' } else { 'router (DHCP)' }
        Write-Line ("{0,-26} {1}" -f $a.Name, $shown)

        $offer = @(Get-DhcpDns -Adapter $a)
        $gate = Get-Gateway -Adapter $a
        if ($gate) { $gateways[[int]$a.ifIndex] = $gate }
        if (-not $gateway) { $gateway = $gate }
        if ($dns -and $offer) { Write-Line ("{0,-26} router offers: {1}" -f '', ($offer -join ', ')) }
        elseif ($dns -and $gate) { Write-Line ("{0,-26} router offers nothing, gateway: {1}" -f '', $gate) }

        if ($dns -contains '127.0.0.1') { $onLocal += $a }
    }

    $listener = Get-LocalListener
    Write-Line ("port 53: " + $(if ($listener) { "held by $listener" } else { 'nobody is listening' })) `
        $(if ($listener) { 'Gray' } else { 'Yellow' })

    $ip = Test-Names
    Write-Line ("names: " + $(if ($ip) { "resolve, ya.ru -> $ip" } else { 'DO NOT resolve' })) `
        $(if ($ip) { 'Green' } else { 'Yellow' })

    if ($ip -and -not $Quiet) {
        $up = Get-Upstream
        if ($up) {
            $tail = if ($up.Name) { ' ({0})' -f $up.Name.TrimEnd('.') } else { '' }
            Write-Line ("asking outward: {0}{1}" -f $up.Address, $tail)
        } else {
            Write-Line 'asking outward: could not tell'
        }
    }

    $nla = Get-NlaState
    if (-not $nla.Service) {
        Write-Line 'NlaSvc is missing from this system' Yellow
    } elseif (-not $nla.Running) {
        Write-Line ('tray icon: NlaSvc is not running (start type: {0})' -f $nla.Service.StartMode) Yellow
    } elseif ($ip -and -not $nla.Online) {
        Write-Line ('tray icon: Windows sees no way out ({0})' -f (($nla.Seen | Select-Object -Unique) -join ', ')) Yellow
    } else {
        Write-Line 'tray icon: Windows sees a way out' Green
    }

    return @{
        Adapters = $adapters
        OnLocal  = $onLocal
        Gateway  = $gateway
        Gateways = $gateways
        Listener = $listener
        Names    = $ip
        Nla      = $nla
    }
}

function Repair-Resolver {
    <# A stopped local resolver is started: that is a return, not a decision. #>
    param([Parameter(Mandatory)]$State)

    if ($State.Names) {
        Write-Line 'names resolve - nothing to repair here' Green
        return $true
    }

    if ($State.OnLocal.Count -and -not $State.Listener) {
        Write-Line 'adapters send names to 127.0.0.1 and nobody answers there' Yellow
        $service = Get-Service -ErrorAction SilentlyContinue |
            Where-Object { $_.Name -match $script:ResolverNames -or $_.DisplayName -match $script:ResolverNames } |
            Select-Object -First 1

        if ($service) {
            Write-Line ('local resolver found: service {0} ({1})' -f $service.Name, $service.Status)
            if ($service.Status -ne 'Running') {
                try {
                    Start-Service -Name $service.Name -ErrorAction Stop
                    Start-Sleep 3
                    & ipconfig.exe /flushdns | Out-Null
                    if (Test-Names) { Write-Line ('service {0} started, names are back' -f $service.Name) Green; return $true }
                    Write-Line ('service {0} started, names still do not resolve' -f $service.Name) Yellow
                } catch {
                    Write-Line ('could not start {0}: {1}' -f $service.Name, $_.Exception.Message) Yellow
                }
            }
        } else {
            Write-Line 'no resolver service in the system - the addresses outlived the program' Yellow
        }

        # Nothing answers on 127.0.0.1 and there is nothing to start: hand the
        # adapters back to the router. A machine without names is worse than a
        # machine without a chosen resolver.
        Write-Line 'handing name resolution back to the router'
        Set-Dns -Servers @() -Adapters $State.Adapters
        if (Test-Names) { Write-Line 'names are back' Green; return $true }
        Write-Line 'names still do not resolve - check the link itself' Yellow
        return $false
    }

    Write-Line 'the name server does not answer - check the link itself' Yellow
    return $false
}

function Repair-Icon {
    <#
        The icon and the connection profile are put back where Windows itself
        keeps them: automatic start, a running service, an enabled probe. This
        is its own default; what turns it off is usually a "service optimizer".
    #>
    param([Parameter(Mandatory)]$State)

    $nla = $State.Nla
    if (-not $nla.Service) { Write-Line 'NlaSvc is missing - nothing to repair' Yellow; return $false }

    try {
        # The active probe is the pair of requests to Microsoft that Windows
        # judges by. With the probe off the icon stays grey no matter how often
        # the service is restarted.
        $probeKey = 'HKLM:\SYSTEM\CurrentControlSet\Services\NlaSvc\Parameters\Internet'
        $probeProp = Get-ItemProperty -Path $probeKey -ErrorAction SilentlyContinue
        if ($probeProp -and $probeProp.PSObject.Properties['EnableActiveProbing'] -and $probeProp.EnableActiveProbing -eq 0) {
            Set-ItemProperty -Path $probeKey -Name 'EnableActiveProbing' -Value 1 -Type DWord -ErrorAction Stop
            Write-Line 'the internet probe was disabled - enabled' Green
        }
    } catch {
        Write-Line ('could not enable the probe: {0}' -f $_.Exception.Message) Yellow
    }

    try {
        if ($nla.Manual) {
            Set-Service -Name 'NlaSvc' -StartupType Automatic -ErrorAction Stop
            Write-Line 'NlaSvc set to automatic start' Green
        }

        if (-not $nla.Running) {
            Start-Service -Name 'NlaSvc' -ErrorAction Stop
            Start-Sleep 3
            $nla = Get-NlaState
            if ($nla.Running) { Write-Line 'NlaSvc started' Green }
        }

        # The service can be running and still hold an old verdict: it re-checks
        # on network changes, not in a loop. Then sites open while the tray keeps
        # its globe. A restart makes it judge again.
        if ($nla.Running -and -not $nla.Online) {
            Write-Line 'the network verdict is stale - restarting NlaSvc'
            Restart-Service -Name 'NlaSvc' -Force -ErrorAction Stop
            Start-Sleep 5
            $nla = Get-NlaState
        }

        $seen = ($nla.Seen | Select-Object -Unique) -join ', '
        if ($nla.Online) { Write-Line ('Windows sees a way out: {0}' -f $seen) Green; return $true }
        Write-Line ('Windows still says: {0} - the icon may catch up within a minute' -f $seen) Yellow
        return $false
    } catch {
        Write-Line ('NlaSvc: {0}' -f $_.Exception.Message) Yellow
        return $false
    }
}

function Set-Provider {
    <# Hands name resolution to the chosen resolver, checking it first. #>
    param([Parameter(Mandatory)][string]$Key, [Parameter(Mandatory)]$State)

    $picked = $script:Providers[$Key]
    $servers = @($picked.Servers)
    $perAdapter = $null

    if ($Key -eq 'UseRouter') {
        if (-not $State.Gateways.Count) { Write-Line 'no gateway in sight - there is no router to ask' Yellow; return $false }
        # Every adapter has its own router: one on the wire, possibly quite
        # another over the air. So this is a table of "adapter - its gateway",
        # and each one is asked separately.
        $perAdapter = @{}
        foreach ($pair in $State.Gateways.GetEnumerator()) {
            if (Test-Resolver -Server $pair.Value) { $perAdapter[$pair.Key] = @($pair.Value) }
            else { Write-Line ('gateway {0} resolves no name - leaving that adapter alone' -f $pair.Value) Yellow }
        }
        if (-not $perAdapter.Count) { Write-Line 'no router answered with a name - leaving everything as it was' Yellow; return $false }
        $servers = @()
    }

    Write-Section ('[2] Handing names to: {0}' -f $picked.Title)

    # Checked before it is written: a silent resolver would leave the machine
    # without names, and the repair would then be blind.
    if ($servers) {
        Write-Line ('testing {0}' -f ($servers -join ', '))
        $alive = @($servers | Where-Object { Test-Resolver -Server $_ })
        if (-not $alive) {
            Write-Line 'no answer - leaving everything as it was' Yellow
            Write-Line 'this happens where a provider hijacks foreign DNS onto its own' Gray
            return $false
        }
        if ($alive.Count -lt $servers.Count) { Write-Line ('only part answers: taking {0}' -f ($alive -join ', ')) Yellow }
        $servers = $alive
    }

    if ($perAdapter) { Set-Dns -Adapters $State.Adapters -PerAdapter $perAdapter }
    else { Set-Dns -Servers $servers -Adapters $State.Adapters }

    $ip = Test-Names
    if ($ip) {
        Write-Line ('names resolve: ya.ru -> {0}' -f $ip) Green
        $up = Get-Upstream
        if ($up) {
            $tail = if ($up.Name) { ' ({0})' -f $up.Name.TrimEnd('.') } else { '' }
            Write-Line ('asking outward: {0}{1}' -f $up.Address, $tail)
        }
        return $true
    }
    Write-Line 'names still do not resolve' Yellow
    return $false
}

function Show-Help {
    Write-Host ''
    Write-Host '  Audion DNS Doctor' -ForegroundColor Cyan
    Write-Host ''
    Write-Line 'Status         look only: adapters, what the router offers, who holds port 53,'
    Write-Line '               who asks outward, whether a name resolves, and the tray icon'
    Write-Line 'Repair         start a stopped local resolver, or hand names back to the router,'
    Write-Line '               then put the tray icon service back the way Windows keeps it'
    Write-Line 'FixIcon        only the tray icon: NlaSvc start type, the service, the probe'
    Write-Line 'UseAuto        take DNS addresses from the router over DHCP'
    Write-Line 'UseRouter      ask the gateway directly'
    Write-Line 'UseCloudflare  1.1.1.1, 1.0.0.1     fast, filters nothing'
    Write-Line 'UseGoogle      8.8.8.8, 8.8.4.4     the best known one'
    Write-Line 'UseQuad9       9.9.9.9, 149.112.112.112   blocks malicious names'
    Write-Line 'UseYandex      77.88.8.8, 77.88.8.1  closest hop, has its own filters'
    Write-Line 'UseAdGuard     94.140.14.14, 94.140.15.15  blocks ads and trackers'
    Write-Host ''
    Write-Line 'Tunnel adapters are never touched: the tunnel sets DNS there itself.' Gray
    Write-Host ''
}

# --- run ---------------------------------------------------------------------

Write-Host ''
Write-Host '=== Audion DNS Doctor ===' -ForegroundColor Cyan

if ($Mode -eq 'Help') { Show-Help; exit 0 }

$needsAdmin = ($Mode -ne 'Status')
if ($needsAdmin -and -not (Test-Administrator)) {
    Write-Host ''
    Write-Line 'This mode changes services or adapter addresses and needs administrator rights.' Yellow
    Write-Line 'Run the tool elevated and try again.' Yellow
    Write-Host ''
    exit 1
}

$state = Show-Status

switch ($Mode) {
    'Status' {
        Write-Host ''
        Write-Host '  Look only: nothing was changed.' -ForegroundColor Cyan
        Write-Host ''
    }
    'Repair' {
        Write-Section '[2] Repair'
        [void](Repair-Resolver -State $state)
        [void](Repair-Icon -State (Show-Status -Quiet))
        Write-Host ''
    }
    'FixIcon' {
        Write-Section '[2] The tray icon'
        [void](Repair-Icon -State $state)
        Write-Host ''
    }
    default {
        [void](Set-Provider -Key $Mode -State $state)
        Write-Host ''
    }
}

exit 0
