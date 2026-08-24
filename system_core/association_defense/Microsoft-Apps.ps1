<#
.SYNOPSIS
    Audion DevOps Tools - Microsoft inbox apps brick.
.DESCRIPTION
    Removes and restores the in-box Microsoft Store apps that ship with Windows,
    using only documented Appx/DISM mechanisms:

        Get-AppxPackage -AllUsers          / Remove-AppxPackage -AllUsers
        Get-AppxProvisionedPackage -Online / Remove-AppxProvisionedPackage -Online
        Add-AppxPackage -Register <manifest> / -RegisterByFamilyName
        Add-AppxProvisionedPackage -Online (re-provisioning for new profiles)

    Removing the installed package frees the file associations; removing the
    provisioned copy keeps new user profiles clean. Neither call survives a
    Windows feature update on its own - pair this brick with Appx-Rearm.ps1
    (scheduled re-apply) and/or AppX-ReinstallBlock.ps1 (AppLocker deny rules).

    Operations:
        -Status     Show installed / provisioned state per app.
        -Remove     Remove installed (AllUsers) and provisioned packages.
        -Restore    Bring apps back: staged manifest -> family name -> Store.
        -Provision  Only re-provision, so new profiles get the app again.

    Targets:
        -Target All                 every catalog entry
        -Target group:media         a whole family (media, xbox, social, news, tools)
        -Target ZuneMusic,ZuneVideo explicit keys (comma separated)

.EXAMPLE
    .\Microsoft-Apps.ps1 -Status
    .\Microsoft-Apps.ps1 -Remove -Target ZuneMusic,ZuneVideo -DryRun
    .\Microsoft-Apps.ps1 -Restore -Target group:media
    .\Microsoft-Apps.ps1 -Provision -Target Photos
#>

[CmdletBinding(DefaultParameterSetName = 'Status')]
param(
    [Parameter(ParameterSetName = 'Status')]    [switch]$Status,
    [Parameter(ParameterSetName = 'Remove')]    [switch]$Remove,
    [Parameter(ParameterSetName = 'Restore')]   [switch]$Restore,
    [Parameter(ParameterSetName = 'Provision')] [switch]$Provision,
    [string[]]$Target = @('ZuneMusic', 'ZuneVideo'),
    [switch]$DryRun
)

$here = Split-Path -Parent $MyInvocation.MyCommand.Path
$common = Join-Path $here '_Common.ps1'
if (-not (Test-Path $common)) {
    Write-Host "ERROR: _Common.ps1 not found next to this script." -ForegroundColor Red
    exit 2
}
. $common

# --- Catalog ----------------------------------------------------------------
# Only apps Microsoft itself exposes as removable in Settings > Installed apps.
# System surfaces (Store, Shell, Widgets host, Security) are intentionally absent.
$AppCatalog = [ordered]@{
    'ZuneMusic'             = @{ Package = 'Microsoft.ZuneMusic';                        Family = 'media';  Title = 'Media Player (Zune)';        ProductId = '9WZDNCRFJ3PT' }
    'ZuneVideo'             = @{ Package = 'Microsoft.ZuneVideo';                        Family = 'media';  Title = 'Films & TV (Zune)';          ProductId = '9WZDNCRFJ3P2' }
    'Photos'                = @{ Package = 'Microsoft.Windows.Photos';                   Family = 'media';  Title = 'Photos';                     ProductId = '9WZDNCRFJBH4' }
    'Clipchamp'             = @{ Package = 'Clipchamp.Clipchamp';                        Family = 'media';  Title = 'Clipchamp';                  ProductId = '9P1J8S7CCWWT' }
    'SoundRecorder'         = @{ Package = 'Microsoft.WindowsSoundRecorder';             Family = 'media';  Title = 'Sound Recorder';             ProductId = '9WZDNCRFHWKN' }
    'Camera'                = @{ Package = 'Microsoft.WindowsCamera';                    Family = 'media';  Title = 'Camera';                     ProductId = '9WZDNCRFJBBG'; Caution = $true }
    'Paint'                 = @{ Package = 'Microsoft.Paint';                            Family = 'media';  Title = 'Paint';                      ProductId = '9PCFS5B6T72H'; Caution = $true }
    'ScreenSketch'          = @{ Package = 'Microsoft.ScreenSketch';                     Family = 'media';  Title = 'Snipping Tool';              ProductId = '9MZ95KL8MR0L'; Caution = $true }

    'GamingApp'             = @{ Package = 'Microsoft.GamingApp';                        Family = 'xbox';   Title = 'Xbox';                       ProductId = '9MV0B5HZVK9Z' }
    'XboxGamingOverlay'     = @{ Package = 'Microsoft.XboxGamingOverlay';                Family = 'xbox';   Title = 'Xbox Game Bar';              ProductId = '9NZKPSTSNW4P' }
    'XboxSpeechToTextOverlay'= @{ Package = 'Microsoft.XboxSpeechToTextOverlay';         Family = 'xbox';   Title = 'Xbox game speech overlay' }
    'XboxIdentityProvider'  = @{ Package = 'Microsoft.XboxIdentityProvider';             Family = 'xbox';   Title = 'Xbox Identity Provider';     ProductId = '9WZDNCRD1HKW'; Caution = $true }
    'SolitaireCollection'   = @{ Package = 'Microsoft.MicrosoftSolitaireCollection';     Family = 'xbox';   Title = 'Solitaire Collection';       ProductId = '9WZDNCRFHWD2' }

    'YourPhone'             = @{ Package = 'Microsoft.YourPhone';                        Family = 'social'; Title = 'Phone Link';                 ProductId = '9NMPJ99VJBWV' }
    'People'                = @{ Package = 'Microsoft.People';                           Family = 'social'; Title = 'People';                     ProductId = '9NBLGGH10PG8' }
    'Teams'                 = @{ Package = 'MSTeams';                                    Family = 'social'; Title = 'Microsoft Teams';            ProductId = 'XP8BT8DW290MPQ' }
    'OutlookForWindows'     = @{ Package = 'Microsoft.OutlookForWindows';                Family = 'social'; Title = 'Outlook for Windows';        ProductId = '9NRX63209R7B' }

    'BingNews'              = @{ Package = 'Microsoft.BingNews';                         Family = 'news';   Title = 'News';                       ProductId = '9WZDNCRFHVFW' }
    'BingWeather'           = @{ Package = 'Microsoft.BingWeather';                      Family = 'news';   Title = 'Weather';                    ProductId = '9WZDNCRFJ3Q2' }
    'Getstarted'            = @{ Package = 'Microsoft.Getstarted';                       Family = 'news';   Title = 'Tips';                       ProductId = '9WZDNCRDTBJJ' }
    'FeedbackHub'           = @{ Package = 'Microsoft.WindowsFeedbackHub';               Family = 'news';   Title = 'Feedback Hub';               ProductId = '9NBLGGH4R32N' }
    'WindowsMaps'           = @{ Package = 'Microsoft.WindowsMaps';                      Family = 'news';   Title = 'Maps';                       ProductId = '9WZDNCRDTBVB' }
    'Copilot'               = @{ Package = 'Microsoft.Copilot';                          Family = 'news';   Title = 'Copilot';                    ProductId = '9NHT9RB2F4HD' }

    'StickyNotes'           = @{ Package = 'Microsoft.MicrosoftStickyNotes';             Family = 'tools';  Title = 'Sticky Notes';               ProductId = '9NBLGGH4QGHW' }
    'Todos'                 = @{ Package = 'Microsoft.Todos';                            Family = 'tools';  Title = 'To Do';                      ProductId = '9NBLGGH5R558' }
    'OneNote'               = @{ Package = 'Microsoft.Office.OneNote';                   Family = 'tools';  Title = 'OneNote for Windows';        ProductId = '9WZDNCRFHVJL' }
    'Whiteboard'            = @{ Package = 'Microsoft.Whiteboard';                       Family = 'tools';  Title = 'Whiteboard';                 ProductId = '9MSPC6MP8FM4' }
    'PowerAutomateDesktop'  = @{ Package = 'Microsoft.PowerAutomateDesktop';             Family = 'tools';  Title = 'Power Automate';             ProductId = '9NFTCH6J7FHV' }
    'QuickAssist'           = @{ Package = 'MicrosoftCorporationII.QuickAssist';         Family = 'tools';  Title = 'Quick Assist';               ProductId = '9P7BP5VNWKX5'; Caution = $true }
    'DevHome'               = @{ Package = 'Microsoft.Windows.DevHome';                  Family = 'tools';  Title = 'Dev Home';                   ProductId = '9N8MHTPHNGVV' }
    'Family'                = @{ Package = 'MicrosoftCorporationII.MicrosoftFamily';     Family = 'tools';  Title = 'Microsoft Family';           ProductId = '9NKB9HD8LK0P' }
}

$FamilyOrder = @('media', 'xbox', 'social', 'news', 'tools')

function Get-CatalogEntry {
    param([Parameter(Mandatory)][string]$Key)
    return $AppCatalog[$Key]
}

function Resolve-TargetKeys {
    $allowed = @($AppCatalog.Keys)
    $items = @()
    foreach ($entry in @($Target)) {
        if ([string]::IsNullOrWhiteSpace([string]$entry)) { continue }
        $items += ([string]$entry -split '[,;|]' | ForEach-Object { $_.Trim() } | Where-Object { $_ })
    }
    if (-not $items) { $items = @('ZuneMusic', 'ZuneVideo') }

    $resolved = @()
    foreach ($item in $items) {
        if ($item -ieq 'All') {
            return @($allowed)
        }
        if ($item -imatch '^group:(.+)$') {
            $family = $Matches[1].Trim().ToLowerInvariant()
            $members = @($allowed | Where-Object { $AppCatalog[$_].Family -eq $family })
            if (-not $members) {
                Write-Line "ERROR: unknown app family '$family'. Allowed: $($FamilyOrder -join ', ')" 'Red'
                exit 2
            }
            foreach ($member in $members) {
                if ($resolved -notcontains $member) { $resolved += $member }
            }
            continue
        }
        $match = $allowed | Where-Object { $_ -ieq $item } | Select-Object -First 1
        if (-not $match) {
            Write-Line "ERROR: unknown app '$item'. Use -Status to list catalog keys." 'Red'
            exit 2
        }
        if ($resolved -notcontains $match) { $resolved += $match }
    }
    return @($resolved)
}

$SelectedKeys = @(Resolve-TargetKeys)

$script:LimitedQueryWarningShown = $false

function Write-LimitedQueryWarning {
    if (-not $script:LimitedQueryWarningShown) {
        Write-Line "WARN: full AllUsers/provisioned inventory needs elevation; showing limited read-only data." 'DarkYellow'
        $script:LimitedQueryWarningShown = $true
    }
}

function Get-InstalledPackages {
    param([Parameter(Mandatory)][string]$Name)
    try {
        return @(Get-AppxPackage -AllUsers -Name $Name -ErrorAction Stop)
    } catch {
        if ($DryRun -or -not (Test-IsAdmin)) {
            Write-LimitedQueryWarning
            return @(Get-AppxPackage -Name $Name -ErrorAction SilentlyContinue)
        }
        throw
    }
}

function Get-ProvisionedPackages {
    param([Parameter(Mandatory)][string]$Name)
    try {
        return @(Get-AppxProvisionedPackage -Online -ErrorAction Stop |
            Where-Object { $_.DisplayName -like "$Name*" })
    } catch {
        if ($DryRun -or -not (Test-IsAdmin)) {
            Write-LimitedQueryWarning
            return @()
        }
        throw
    }
}

function Test-PackageInstalled {
    param([Parameter(Mandatory)][string]$Name)
    return (@(Get-InstalledPackages -Name $Name).Count -gt 0)
}

function Show-Status {
    Write-Line "Microsoft inbox apps status" 'Cyan'
    Write-Line ("-" * 74)
    Write-Host ("{0,-24} {1,-12} {2,-13} {3}" -f 'App', 'Installed', 'Provisioned', 'Package') -ForegroundColor DarkGray
    foreach ($family in $FamilyOrder) {
        $keys = @($SelectedKeys | Where-Object { $AppCatalog[$_].Family -eq $family })
        if (-not $keys) { continue }
        Write-Line ("[{0}]" -f $family.ToUpperInvariant()) 'DarkCyan'
        foreach ($key in $keys) {
            $entry = Get-CatalogEntry -Key $key
            $installed = @(Get-InstalledPackages -Name $entry.Package)
            $prov = @(Get-ProvisionedPackages -Name $entry.Package)
            $instMark = if ($installed.Count -gt 0) { 'INSTALLED' } else { 'absent' }
            $provMark = if ($prov.Count -gt 0) { 'PROVISIONED' } else { 'none' }
            $color = if ($installed.Count -gt 0 -or $prov.Count -gt 0) { 'Yellow' } else { 'Green' }
            Write-Host ("  {0,-22} {1,-12} {2,-13} {3}" -f $entry.Title, $instMark, $provMark, $entry.Package) -ForegroundColor $color
        }
    }
    Write-Line ("-" * 74)
    Write-Line "Yellow = still present. Green = removed for every user and for new profiles." 'DarkGray'
    Write-Line "A Windows feature update can bring removed apps back: enable Appx-Rearm.ps1 to re-apply automatically." 'DarkGray'
}

function Remove-TargetApp {
    param([Parameter(Mandatory)][hashtable]$Entry)
    $name = $Entry.Package
    $installed = @(Get-InstalledPackages -Name $name)
    $prov = @(Get-ProvisionedPackages -Name $name)
    if (Test-DryRun -DryRun:$DryRun -Action "remove $name (installed=$($installed.Count), provisioned=$($prov.Count))") {
        return
    }
    if ($installed.Count -eq 0 -and $prov.Count -eq 0) {
        Write-Line "  $($Entry.Title): already absent." 'DarkGray'
        return
    }
    Write-Line "Removing $($Entry.Title) ($name) ..." 'Cyan'
    Get-AppxPackage -AllUsers -Name $name -ErrorAction SilentlyContinue |
        Remove-AppxPackage -AllUsers -ErrorAction SilentlyContinue
    Get-AppxProvisionedPackage -Online -ErrorAction SilentlyContinue |
        Where-Object { $_.DisplayName -like "$name*" } |
        ForEach-Object {
            Remove-AppxProvisionedPackage -Online -PackageName $_.PackageName -ErrorAction SilentlyContinue | Out-Null
        }
}

function Get-StagedManifests {
    param([Parameter(Mandatory)][string]$Name)
    return @(
        Get-ChildItem "$env:ProgramFiles\WindowsApps" -Filter 'AppxManifest.xml' -Recurse -ErrorAction SilentlyContinue |
            Where-Object { $_.FullName -like "*\$Name`_*" }
    )
}

function Restore-FromStagedManifest {
    param([Parameter(Mandatory)][hashtable]$Entry)
    $restored = $false
    foreach ($manifest in (Get-StagedManifests -Name $Entry.Package)) {
        try {
            Add-AppxPackage -DisableDevelopmentMode -Register $manifest.FullName -ErrorAction Stop
            Write-Line "  re-registered from staged manifest: $($manifest.FullName)" 'Green'
            $restored = $true
        } catch {
            Write-Line "  staged manifest failed: $($_.Exception.Message)" 'DarkYellow'
        }
    }
    return $restored
}

function Restore-ByFamilyName {
    param([Parameter(Mandatory)][hashtable]$Entry)
    $package = @(Get-AppxPackage -AllUsers -Name $Entry.Package -ErrorAction SilentlyContinue | Select-Object -First 1)
    if (-not $package) { return $false }
    try {
        Add-AppxPackage -RegisterByFamilyName -MainPackage $package[0].PackageFamilyName -ErrorAction Stop
        Write-Line "  registered by family name: $($package[0].PackageFamilyName)" 'Green'
        return $true
    } catch {
        Write-Line "  RegisterByFamilyName failed: $($_.Exception.Message)" 'DarkYellow'
        return $false
    }
}

function Restore-FromStore {
    param([Parameter(Mandatory)][hashtable]$Entry)
    if (-not $Entry.ContainsKey('ProductId') -or -not $Entry.ProductId) {
        Write-Line "  no Microsoft Store product id in catalog; reinstall manually." 'Yellow'
        return $false
    }
    $winget = Get-Command winget.exe -ErrorAction SilentlyContinue
    if (-not $winget) {
        Write-Line "  winget.exe not found; open ms-windows-store://pdp/?ProductId=$($Entry.ProductId) manually." 'Yellow'
        return $false
    }
    try {
        Write-Line "  installing from Microsoft Store via winget ($($Entry.ProductId)) ..." 'Cyan'
        & $winget.Source 'install' '--source' 'msstore' '--id' $Entry.ProductId `
            '--accept-source-agreements' '--accept-package-agreements' '--disable-interactivity'
        $code = if ($global:LASTEXITCODE -is [int]) { $global:LASTEXITCODE } else { 0 }
        if ($code -eq 0) {
            Write-Line "  winget completed." 'Green'
            return $true
        }
        Write-Line "  winget exit code $code." 'Yellow'
    } catch {
        Write-Line "  winget failed: $($_.Exception.Message)" 'Yellow'
    } finally {
        $global:LASTEXITCODE = 0
    }
    return $false
}

# Re-provisioning: new user profiles get the app again. Needs the .appx/.msix
# payload that ships next to the staged package under ProgramFiles\WindowsApps.
function Add-TargetProvisioning {
    param([Parameter(Mandatory)][hashtable]$Entry)
    $name = $Entry.Package
    if (@(Get-ProvisionedPackages -Name $name).Count -gt 0) {
        Write-Line "  $($Entry.Title): already provisioned." 'DarkGray'
        return $true
    }
    if (Test-DryRun -DryRun:$DryRun -Action "re-provision $name for new user profiles") {
        return $true
    }

    $bundle = Get-ChildItem "$env:ProgramFiles\WindowsApps" -ErrorAction SilentlyContinue |
        Where-Object { $_.PSIsContainer -and $_.Name -like "$name`_*" } |
        Sort-Object Name -Descending |
        Select-Object -First 1
    if ($bundle) {
        $manifest = Join-Path $bundle.FullName 'AppxManifest.xml'
        if (Test-Path -LiteralPath $manifest) {
            try {
                Add-AppxProvisionedPackage -Online -PackagePath $manifest -SkipLicense -ErrorAction Stop | Out-Null
                Write-Line "  provisioned from staged package: $($bundle.Name)" 'Green'
                return $true
            } catch {
                Write-Line "  provisioning from staged package failed: $($_.Exception.Message)" 'DarkYellow'
            }
        }
    }
    Write-Line "  no staged payload found for $name; install it from Microsoft Store first, then run -Provision again." 'Yellow'
    return $false
}

function Invoke-Remove {
    if (-not $DryRun) { Assert-Admin }
    foreach ($key in $SelectedKeys) {
        $entry = Get-CatalogEntry -Key $key
        if ($entry.ContainsKey('Caution') -and $entry.Caution -and -not $DryRun) {
            Write-Line "NOTE: $($entry.Title) is used by other Windows workflows; removing it can break them." 'DarkYellow'
        }
        Remove-TargetApp -Entry $entry
    }
    if ($DryRun) {
        Write-Line "Dry-run complete. Nothing was removed." 'DarkCyan'
        return
    }
    Write-Line "Selected apps removed (AllUsers + provisioned)." 'Green'
    Write-Line "Windows feature updates can restore them: enable Appx-Rearm.ps1 to re-apply after every build change." 'DarkGray'
}

function Invoke-Restore {
    Assert-Admin
    $missing = 0
    foreach ($key in $SelectedKeys) {
        $entry = Get-CatalogEntry -Key $key
        Write-Line "Restoring $($entry.Title) ($($entry.Package)) ..." 'Cyan'
        if (Test-PackageInstalled -Name $entry.Package) {
            Write-Line "  already installed." 'DarkGray'
        } else {
            [void](Restore-FromStagedManifest -Entry $entry)
            if (-not (Test-PackageInstalled -Name $entry.Package)) { [void](Restore-ByFamilyName -Entry $entry) }
            if (-not (Test-PackageInstalled -Name $entry.Package)) { [void](Restore-FromStore -Entry $entry) }
        }
        if (Test-PackageInstalled -Name $entry.Package) {
            [void](Add-TargetProvisioning -Entry $entry)
        } else {
            Write-Line "  still absent after automatic restore attempts." 'Yellow'
            if ($entry.ContainsKey('ProductId') -and $entry.ProductId) {
                Write-Line "  Manual Store link: ms-windows-store://pdp/?ProductId=$($entry.ProductId)" 'Yellow'
            }
            $missing++
        }
    }
    if ($missing -gt 0) {
        Write-Line "Restore finished with $missing app(s) still missing." 'Yellow'
        exit 1
    }
    Write-Line "Restore finished; selected apps are installed and provisioned." 'Green'
}

function Invoke-Provision {
    if (-not $DryRun) { Assert-Admin }
    $failed = 0
    foreach ($key in $SelectedKeys) {
        $entry = Get-CatalogEntry -Key $key
        Write-Line "Provisioning $($entry.Title) ($($entry.Package)) ..." 'Cyan'
        if (-not (Add-TargetProvisioning -Entry $entry)) { $failed++ }
    }
    if ($failed -gt 0) {
        Write-Line "$failed app(s) could not be re-provisioned." 'Yellow'
        exit 1
    }
    Write-Line "Selected apps are provisioned for new user profiles." 'Green'
}

$verb = $PSCmdlet.ParameterSetName
Start-BrickLog -BrickName 'Microsoft-Apps' -Verb $verb -ScriptRoot $here | Out-Null
try {
    switch ($verb) {
        'Remove'    { Invoke-Remove }
        'Restore'   { Invoke-Restore }
        'Provision' { Invoke-Provision }
        default     { Show-Status }
    }
} finally {
    Stop-BrickLog
}
