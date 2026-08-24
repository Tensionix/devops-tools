<#
.SYNOPSIS
    Audion DevOps Tools - Microsoft Edge calm-down brick.
.DESCRIPTION
    Makes Microsoft Edge stop pushing itself, without breaking anything that
    depends on it. Everything here is a documented Microsoft Edge / Edge Update
    group policy value under HKLM - no file surgery, no uninstall, no hacks.

    Microsoft Edge WebView2 is explicitly protected: many applications render
    their UI with it, so the brick pins WebView2 installation and updates to
    "allowed" while it calms the browser down.

    Levels:
        Calm   Edge stops asking to be default, stops the first-run flow,
               stops running in the background and stops promo tabs.
        Quiet  Calm plus sidebar, Shopping, Collections, feedback and
               personalization reporting turned off, and extra Edge channels
               (Beta/Dev/Canary) blocked from installing themselves.

    Operations:
        -Status         Show every managed value, the WebView2 state and Edge tasks.
        -Enable         Apply the chosen level (default: Calm).
        -Disable        Remove only the values this brick manages.
        -RepairWebView2 Install the official Evergreen WebView2 Runtime.

    Edge stays installed and patched on purpose. The point is that it stops
    claiming file types and links that already belong to another browser.

.EXAMPLE
    .\Edge-Debloat.ps1 -Status
    .\Edge-Debloat.ps1 -Enable -Level Calm
    .\Edge-Debloat.ps1 -Enable -Level Quiet
    .\Edge-Debloat.ps1 -Disable
    .\Edge-Debloat.ps1 -RepairWebView2
#>

[CmdletBinding(DefaultParameterSetName = 'Status')]
param(
    [Parameter(ParameterSetName = 'Status')]         [switch]$Status,
    [Parameter(ParameterSetName = 'Enable')]         [switch]$Enable,
    [Parameter(ParameterSetName = 'Disable')]        [switch]$Disable,
    [Parameter(ParameterSetName = 'RepairWebView2')] [switch]$RepairWebView2,
    [ValidateSet('Calm', 'Quiet')] [string]$Level = 'Calm',
    [switch]$DryRun
)

$here = Split-Path -Parent $MyInvocation.MyCommand.Path
$common = Join-Path $here '_Common.ps1'
if (-not (Test-Path $common)) {
    Write-Host "ERROR: _Common.ps1 not found next to this script." -ForegroundColor Red
    exit 2
}
. $common

$EdgePolicy       = 'HKLM:\SOFTWARE\Policies\Microsoft\Edge'
$EdgeUpdatePolicy = 'HKLM:\SOFTWARE\Policies\Microsoft\EdgeUpdate'

# Edge Update application ids (documented in the Edge Update policy reference).
$WebView2AppId = '{F3017226-FE2A-4295-8BDF-00C3A9A7E4C5}'
$EdgeBetaAppId = '{2CD8A007-E189-409D-A2C8-9AF4EF3C72AA}'
$EdgeDevAppId  = '{0D50BFEC-CD6A-4F9A-964C-C7416E3ACB10}'
$EdgeCanaryId  = '{65C35B14-6C1D-4122-AC46-7148CC9D6497}'

# Calm: stop the nagging, the background process and the promo surfaces.
$CalmPolicy = [ordered]@{
    'DefaultBrowserSettingEnabled'                  = 0
    'HideFirstRunExperience'                        = 1
    'AutoImportAtFirstRun'                          = 4
    'StartupBoostEnabled'                           = 0
    'BackgroundModeEnabled'                         = 0
    'PromotionalTabsEnabled'                        = 0
    'ShowRecommendationsEnabled'                    = 0
    'SpotlightExperiencesAndRecommendationsEnabled' = 0
    'CreateDesktopShortcutDefault'                  = 0
}

# Quiet: everything above plus the side panels and telemetry-ish extras.
$QuietPolicy = [ordered]@{
    'HubsSidebarEnabled'            = 0
    'EdgeShoppingAssistantEnabled'  = 0
    'EdgeCollectionsEnabled'        = 0
    'WebWidgetAllowed'              = 0
    'PersonalizationReportingEnabled' = 0
    'UserFeedbackAllowed'           = 0
    'EdgeAssetDeliveryServiceEnabled' = 0
}

# WebView2 stays installable and updatable no matter which level is applied.
$WebView2Guard = [ordered]@{
    ("Install$WebView2AppId") = 1
    ("Update$WebView2AppId")  = 1
}

# Quiet also blocks the extra Edge channels from installing themselves.
$ChannelGuard = [ordered]@{
    ("Install$EdgeBetaAppId") = 0
    ("Install$EdgeDevAppId")  = 0
    ("Install$EdgeCanaryId")  = 0
}

function Get-EdgePolicyPlan {
    param([string]$PolicyLevel)
    $plan = [ordered]@{}
    foreach ($name in $CalmPolicy.Keys) { $plan[$name] = $CalmPolicy[$name] }
    if ($PolicyLevel -eq 'Quiet') {
        foreach ($name in $QuietPolicy.Keys) { $plan[$name] = $QuietPolicy[$name] }
    }
    return $plan
}

function Get-EdgeUpdatePlan {
    param([string]$PolicyLevel)
    $plan = [ordered]@{}
    foreach ($name in $WebView2Guard.Keys) { $plan[$name] = $WebView2Guard[$name] }
    if ($PolicyLevel -eq 'Quiet') {
        foreach ($name in $ChannelGuard.Keys) { $plan[$name] = $ChannelGuard[$name] }
    }
    return $plan
}

function Get-WebView2Version {
    $paths = @(
        "HKLM:\SOFTWARE\WOW6432Node\Microsoft\EdgeUpdate\Clients\$WebView2AppId",
        "HKLM:\SOFTWARE\Microsoft\EdgeUpdate\Clients\$WebView2AppId"
    )
    foreach ($path in $paths) {
        try {
            if (-not (Test-Path $path)) { continue }
            $item = Get-ItemProperty -Path $path -ErrorAction Stop
            if ($item.PSObject.Properties.Name -contains 'pv' -and $item.pv) {
                return [string]$item.pv
            }
        } catch { }
    }
    return ''
}

function Show-PolicyBlock {
    param(
        [Parameter(Mandatory)][string]$Title,
        [Parameter(Mandatory)][string]$Path,
        [Parameter(Mandatory)][System.Collections.Specialized.OrderedDictionary]$Plan
    )
    Write-Line $Title 'Cyan'
    $active = 0
    foreach ($name in $Plan.Keys) {
        $current = Get-RegDword -Path $Path -Name $name
        $want = $Plan[$name]
        $ok = ($current -eq $want)
        if ($ok) { $active++ }
        $currentText = if ($null -eq $current) { '<unset>' } else { "$current" }
        $state = if ($ok) { 'OK' } else { 'off' }
        Write-Host ("  {0,-46} cur={1,-8} want={2,-3} {3}" -f $name, $currentText, $want, $state) -ForegroundColor (Get-StateColor -Active $ok)
    }
    return @{ Active = $active; Total = @($Plan.Keys).Count }
}

function Show-Status {
    Write-Line "Microsoft Edge calm-down status (level: $Level)" 'Cyan'
    Write-Line ("-" * 74)

    $edgeResult = Show-PolicyBlock -Title 'Edge browser policy' -Path $EdgePolicy -Plan (Get-EdgePolicyPlan -PolicyLevel $Level)
    Write-Line ''
    $updateResult = Show-PolicyBlock -Title 'Edge Update policy (WebView2 protection)' -Path $EdgeUpdatePolicy -Plan (Get-EdgeUpdatePlan -PolicyLevel $Level)

    Write-Line ''
    Write-Line 'Microsoft Edge WebView2 Runtime' 'Cyan'
    $version = Get-WebView2Version
    if ($version) {
        Write-Line ("  Installed: $version") 'Green'
    } else {
        Write-Line "  Not detected. Applications that render their UI with WebView2 would need the Evergreen Runtime installer." 'Yellow'
    }

    Write-Line ''
    Write-Line 'What opens links and web files right now' 'Cyan'
    $watched = @('http', 'https', '.htm', '.html', '.pdf', '.svg', '.webp')
    $edgeOwned = 0
    foreach ($identifier in $watched) {
        if ($identifier.StartsWith('.')) {
            $path = "HKCU:\Software\Microsoft\Windows\CurrentVersion\Explorer\FileExts\$identifier\UserChoice"
        } else {
            $path = "HKCU:\Software\Microsoft\Windows\Shell\Associations\UrlAssociations\$identifier\UserChoice"
        }
        $progId = ''
        try {
            $props = Get-ItemProperty -Path $path -ErrorAction Stop
            if ($props.PSObject.Properties.Name -contains 'ProgId') { $progId = [string]$props.ProgId }
        } catch { }
        if (-not $progId) {
            Write-Host ("  {0,-8} {1}" -f $identifier, '<not set>') -ForegroundColor DarkGray
            continue
        }
        $isEdge = ($progId -like 'MSEdge*' -or $progId -like 'AppXq0fevzme*')
        if ($isEdge) { $edgeOwned++ }
        $rowColor = if ($isEdge) { 'Yellow' } else { 'Green' }
        Write-Host ("  {0,-8} {1}" -f $identifier, $progId) -ForegroundColor $rowColor
    }
    if ($edgeOwned -gt 0) {
        Write-Line "  Edge currently owns $edgeOwned of them. Set your browser in Windows, then pin the set in the Policy tab." 'Yellow'
    } else {
        Write-Line "  Edge owns none of the watched types." 'Green'
    }

    Write-Line ''
    Write-Line 'Edge scheduled tasks' 'Cyan'
    $tasks = @(Get-ScheduledTask -TaskName 'MicrosoftEdge*' -ErrorAction SilentlyContinue)
    if ($tasks.Count -eq 0) {
        Write-Line "  No MicrosoftEdge* tasks found." 'DarkGray'
    } else {
        foreach ($task in $tasks) {
            Write-Host ("  {0,-42} {1}" -f $task.TaskName, $task.State) -ForegroundColor DarkGray
        }
        Write-Line "  Update tasks are left alone on purpose: they keep Edge and WebView2 patched." 'DarkGray'
    }

    Write-Line ("-" * 74)
    $total = $edgeResult.Total + $updateResult.Total
    $active = $edgeResult.Active + $updateResult.Active
    if ($active -eq $total) {
        Write-Line "STATE: applied ($active/$total values)." 'Green'
    } elseif ($active -eq 0) {
        Write-Line "STATE: not applied (0/$total values). Run -Enable." 'Yellow'
    } else {
        Write-Line "STATE: partial ($active/$total values). Run -Enable to complete." 'Yellow'
    }
    Write-Line "Edge stays installed and updated; it simply stops competing for your file types and links." 'DarkGray'
}

function Enable-Guard {
    if (-not $DryRun) { Assert-Admin }
    $edgePlan = Get-EdgePolicyPlan -PolicyLevel $Level
    $updatePlan = Get-EdgeUpdatePlan -PolicyLevel $Level

    foreach ($name in $edgePlan.Keys) {
        if (Test-DryRun -DryRun:$DryRun -Action "set Edge policy $name = $($edgePlan[$name])") { continue }
        Set-RegDword -Path $EdgePolicy -Name $name -Value $edgePlan[$name]
    }
    foreach ($name in $updatePlan.Keys) {
        if (Test-DryRun -DryRun:$DryRun -Action "set Edge Update policy $name = $($updatePlan[$name])") { continue }
        Set-RegDword -Path $EdgeUpdatePolicy -Name $name -Value $updatePlan[$name]
    }

    if ($DryRun) {
        Write-Line "Dry-run complete. No policy value was written." 'DarkCyan'
        return
    }
    Write-Line "Microsoft Edge calm-down APPLIED (level: $Level)." 'Green'
    Write-Line "  WebView2 stays installable and updatable." 'DarkGray'
    Write-Line "  Restart Edge (or sign out) so every surface picks the policy up." 'DarkGray'
}

function Disable-Guard {
    if (-not $DryRun) { Assert-Admin }
    # Remove every value this brick can write, regardless of the current level.
    $edgeNames = @($CalmPolicy.Keys) + @($QuietPolicy.Keys)
    $updateNames = @($WebView2Guard.Keys) + @($ChannelGuard.Keys)

    foreach ($name in $edgeNames) {
        if (Test-DryRun -DryRun:$DryRun -Action "remove Edge policy $name") { continue }
        Remove-RegValue -Path $EdgePolicy -Name $name
    }
    foreach ($name in $updateNames) {
        if (Test-DryRun -DryRun:$DryRun -Action "remove Edge Update policy $name") { continue }
        Remove-RegValue -Path $EdgeUpdatePolicy -Name $name
    }

    if ($DryRun) {
        Write-Line "Dry-run complete. No policy value was removed." 'DarkCyan'
        return
    }
    Write-Line "Microsoft Edge calm-down REMOVED; stock Edge behavior is back." 'Yellow'
}

# --- WebView2 Evergreen runtime ---------------------------------------------

$UnlockStateDir = Join-Path $env:ProgramData 'Audion\EdgeGuard'
$WebView2Bootstrap = 'https://go.microsoft.com/fwlink/p/?LinkId=2124703'

function Invoke-WebView2Repair {
    if (-not $DryRun) { Assert-Admin }
    $version = Get-WebView2Version
    if ($version) {
        Write-Line "WebView2 Runtime is already installed: $version" 'Green'
        return
    }
    if (Test-DryRun -DryRun:$DryRun -Action 'download and run the official Evergreen WebView2 bootstrapper') {
        return
    }
    if (-not (Test-Path -LiteralPath $UnlockStateDir)) {
        New-Item -ItemType Directory -Path $UnlockStateDir -Force | Out-Null
    }
    $installer = Join-Path $UnlockStateDir 'MicrosoftEdgeWebView2Setup.exe'
    Write-Line "Downloading the official WebView2 Evergreen bootstrapper ..." 'Cyan'
    try {
        Invoke-WebRequest -Uri $WebView2Bootstrap -OutFile $installer -UseBasicParsing -ErrorAction Stop
    } catch {
        Write-Line "ERROR: download failed: $($_.Exception.Message)" 'Red'
        exit 1
    }
    Start-Process -FilePath $installer -ArgumentList @('/silent', '/install') -Wait -WindowStyle Hidden
    $installed = Get-WebView2Version
    if ($installed) {
        Write-Line "WebView2 Runtime installed: $installed" 'Green'
    } else {
        Write-Line "WebView2 Runtime is still not detected; run the installer manually: $installer" 'Yellow'
    }
}

$verb = $PSCmdlet.ParameterSetName
Start-BrickLog -BrickName 'Edge-Debloat' -Verb $verb -ScriptRoot $here | Out-Null
try {
    switch ($verb) {
        'Enable'         { Enable-Guard }
        'Disable'        { Disable-Guard }
        'RepairWebView2' { Invoke-WebView2Repair }
        default          { Show-Status }
    }
} finally {
    Stop-BrickLog
}
