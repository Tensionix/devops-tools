<#
.SYNOPSIS
    Audion DevOps Tools - AppX Reinstall-Block brick (Pro/Enterprise).
.DESCRIPTION
    Blocks Windows from reinstalling the built-in "association hijacker"
    apps (Photos, Films & TV, Media Player, Clipchamp) on feature updates,
    using AppLocker packaged-app (Appx) deny rules + the AppIDSvc service.

    Package family names are stable across versions, so these rules do not
    depend on a specific build number.

    Operations (the "holy trinity"):
        -Status   Show whether deny rules are present and AppIDSvc state.
        -Enable   Install deny rules and start/enable AppIDSvc.
        -Disable  Remove the Audion deny rules (leaves other policy intact).

    Requires Windows Pro/Enterprise (AppLocker is not available on Home).

.EXAMPLE
    .\AppX-ReinstallBlock.ps1 -Status
    .\AppX-ReinstallBlock.ps1 -Enable
    .\AppX-ReinstallBlock.ps1 -Disable
#>

[CmdletBinding(DefaultParameterSetName = 'Status')]
param(
    [Parameter(ParameterSetName = 'Status')] [switch]$Status,
    [Parameter(ParameterSetName = 'Enable')] [switch]$Enable,
    [Parameter(ParameterSetName = 'Disable')] [switch]$Disable,
    [string[]]$Target = @('All'),
    [switch]$DryRun
)

$here = Split-Path -Parent $MyInvocation.MyCommand.Path
$common = Join-Path $here '_Common.ps1'
if (-not (Test-Path $common)) {
    Write-Host "ERROR: _Common.ps1 not found next to this script." -ForegroundColor Red
    exit 2
}
. $common

$TargetCatalog = [ordered]@{
    'Photos'    = 'Microsoft.Windows.Photos*'
    'ZuneVideo' = 'Microsoft.ZuneVideo*'
    'ZuneMusic' = 'Microsoft.ZuneMusic*'
    'Clipchamp' = 'Clipchamp.Clipchamp*'
}

function Get-NormalizedTargetNames {
    $allowed = @('All', 'Photos', 'ZuneVideo', 'ZuneMusic', 'Clipchamp')
    $items = @()
    foreach ($entry in @($Target)) {
        if ([string]::IsNullOrWhiteSpace([string]$entry)) { continue }
        $items += ([string]$entry -split '[,;|]' | ForEach-Object { $_.Trim() } | Where-Object { $_ })
    }
    if (-not $items) { return @('All') }
    $normalized = @()
    foreach ($item in $items) {
        $match = $allowed | Where-Object { $_ -ieq $item } | Select-Object -First 1
        if (-not $match) {
            Write-Line "ERROR: unsupported target '$item'. Allowed: $($allowed -join ', ')" 'Red'
            exit 2
        }
        if ($normalized -notcontains $match) { $normalized += $match }
    }
    return @($normalized)
}

$SelectedTargets = @(Get-NormalizedTargetNames)

function Get-SelectedBlockList {
    if (-not $SelectedTargets -or $SelectedTargets -contains 'All') {
        return @($TargetCatalog.Values)
    }
    return @($SelectedTargets | ForEach-Object { $TargetCatalog[$_] })
}

# Package family names to block. Wildcards keep rules version-resilient.
$BlockList = @(Get-SelectedBlockList)

# A stable marker so we can find/remove only OUR rules later.
$RuleTag = 'Audion-Block'
$script:LimitedAppxQueryWarningShown = $false

function Write-LimitedAppxQueryWarning {
    if (-not $script:LimitedAppxQueryWarningShown) {
        Write-Line "WARN: full AllUsers AppX inventory needs elevation on this machine; showing limited current-user candidates." 'DarkYellow'
        $script:LimitedAppxQueryWarningShown = $true
    }
}

function Get-BlockCandidatePackages {
    param([Parameter(Mandatory)][string]$Pattern)
    try {
        return @(Get-AppxPackage -AllUsers -Name $Pattern -ErrorAction Stop)
    } catch {
        if ($DryRun -or -not (Test-IsAdmin)) {
            Write-LimitedAppxQueryWarning
            return @(Get-AppxPackage -Name $Pattern -ErrorAction SilentlyContinue)
        }
        throw
    }
}

function Test-AppLockerAvailable {
    $edition = (Get-CimInstance Win32_OperatingSystem).Caption
    if ($edition -match 'Home') {
        Write-Line "ERROR: AppLocker is not available on Windows Home ($edition)." 'Red'
        Write-Line "Use provisioned-package removal instead (separate brick)." 'Yellow'
        return $false
    }
    return $true
}

function Show-Status {
    Write-Line "AppX Reinstall-Block status" 'Cyan'
    Write-Line "Target: $($SelectedTargets -join ', ')"
    Write-Line ("-" * 50)

    # AppIDSvc is required for AppLocker enforcement.
    $svc = Get-Service -Name AppIDSvc -ErrorAction SilentlyContinue
    if ($svc) {
        $svcColor = if ($svc.Status -eq 'Running') { 'Green' } else { 'Yellow' }
        Write-Host ("AppIDSvc: {0}" -f $svc.Status) -ForegroundColor $svcColor
    } else {
        Write-Line "AppIDSvc: <not found>" 'Red'
    }

    # Inspect current effective AppLocker policy for our tagged rules.
    try {
        [xml]$policy = Get-AppLockerPolicy -Effective -Xml
        $ourRules = @()
        if ($policy.AppLockerPolicy) {
            $nodes = $policy.SelectNodes("//FilePublisherRule[contains(@Name,'$RuleTag')]")
            foreach ($n in $nodes) { $ourRules += $n.Name }
        }
        Write-Line ("-" * 50)
        if ($ourRules.Count -gt 0) {
            Write-Line "GUARD: ACTIVE - Audion deny rules present:" 'Green'
            $ourRules | Sort-Object -Unique | ForEach-Object { Write-Host "  $_" }
        } else {
            Write-Line "GUARD: OFF - no Audion deny rules. Run -Enable." 'Yellow'
        }
    } catch {
        Write-Line "Could not read AppLocker policy: $($_.Exception.Message)" 'Red'
    }
}

function Test-AudionRuleExistsForPattern {
    param([Parameter(Mandatory)][string]$Pattern)
    try {
        [xml]$policy = Get-AppLockerPolicy -Effective -Xml
        if (-not $policy.AppLockerPolicy) { return $false }
        $needle = ($Pattern.TrimEnd('*')).ToUpperInvariant()
        $nodes = $policy.SelectNodes("//FilePublisherRule[contains(@Name,'$RuleTag')]")
        foreach ($n in @($nodes)) {
            $haystack = (($n.Name + ' ' + $n.OuterXml).ToUpperInvariant())
            if ($haystack.Contains($needle)) { return $true }
        }
    } catch {
        return $false
    }
    return $false
}

function Enable-Guard {
    if (-not $DryRun) { Assert-Admin }
    if (-not (Test-AppLockerAvailable)) { exit 3 }

    # Build deny rules from currently installed packages matching the list.
    $added = 0
    $covered = 0
    $failed = 0
    $missing = 0
    foreach ($pattern in $BlockList) {
        if (Test-AudionRuleExistsForPattern -Pattern $pattern) {
            Write-Line "  (Audion deny rule already covers $pattern)" 'DarkGray'
            $covered++
            continue
        }
        $pkgs = @(Get-BlockCandidatePackages -Pattern $pattern)
        if (-not $pkgs) {
            Write-Line "  (no installed package matches $pattern - cannot generate publisher rule from live package)" 'Yellow'
            Write-Line "  Tip: enable reinstall-block before removing the app, or temporarily reinstall it and run this again." 'DarkGray'
            $missing++
        }
        foreach ($pkg in ($pkgs | Select-Object -First 1)) {
            try {
                if (Test-DryRun -DryRun:$DryRun -Action "add AppLocker deny rule for $($pkg.Name)") {
                    continue
                }
                $newPolicy = Get-AppLockerFileInformation -Packages $pkg |
                    New-AppLockerPolicy -RuleType Publisher -User Everyone `
                        -RuleNamePrefix $RuleTag -Optimize -ErrorAction Stop
                # Flip the generated allow rule into a deny rule.
                [xml]$xml = $newPolicy.ToXml()
                $xml.SelectNodes("//FilePublisherRule") | ForEach-Object {
                    $_.SetAttribute('Action', 'Deny')
                }
                $denyPolicy = [Microsoft.Security.ApplicationId.PolicyManagement.PolicyModel.AppLockerPolicy]::FromXml($xml.OuterXml)
                Set-AppLockerPolicy -PolicyObject $denyPolicy -Merge -ErrorAction Stop
                $added++
                Write-Line "  + deny rule for $($pkg.Name)" 'Green'
            } catch {
                Write-Line "  ! failed for $($pkg.Name): $($_.Exception.Message)" 'Red'
                $failed++
            }
        }
    }

    # AppLocker only enforces when AppIDSvc runs.
    if (-not $DryRun) {
        Set-Service -Name AppIDSvc -StartupType Automatic -ErrorAction SilentlyContinue
        Start-Service -Name AppIDSvc -ErrorAction SilentlyContinue
    }

    if ($DryRun) {
        Write-Line "Dry-run complete. No AppLocker policy was changed." 'DarkCyan'
    } elseif ($added -gt 0) {
        Write-Line "AppX Reinstall-Block ENABLED ($added rule(s))." 'Green'
    } elseif ($covered -gt 0) {
        Write-Line "AppX Reinstall-Block already covers selected targets ($covered existing rule(s))." 'Green'
    } else {
        Write-Line "No rules added - target packages may already be removed." 'Yellow'
        Write-Line "Tip: install the app once to capture its publisher, or rely on provisioned-removal."
    }
    if (-not $DryRun -and $failed -gt 0) {
        Write-Line "ERROR: $failed AppLocker rule(s) failed. Lockdown must not continue to removal." 'Red'
        exit 1
    }
    if (-not $DryRun -and $missing -gt 0) {
        Write-Line "SOFT-REFUSAL: $missing target package(s) have no live package and no existing Audion rule." 'Yellow'
        Write-Line "Removal should be skipped until the missing app is restored once and the rule can be captured." 'Yellow'
        exit 4
    }
}

function Disable-Guard {
    Assert-Admin
    if (-not (Test-AppLockerAvailable)) { exit 3 }
    try {
        [xml]$policy = Get-AppLockerPolicy -Local -Xml
        $removed = 0
        $nodes = $policy.SelectNodes("//FilePublisherRule[contains(@Name,'$RuleTag')]")
        foreach ($n in @($nodes)) {
            $n.ParentNode.RemoveChild($n) | Out-Null
            $removed++
        }
        if ($removed -gt 0) {
            $cleanPolicy = [Microsoft.Security.ApplicationId.PolicyManagement.PolicyModel.AppLockerPolicy]::FromXml($policy.OuterXml)
            Set-AppLockerPolicy -PolicyObject $cleanPolicy -ErrorAction Stop
            Write-Line "AppX Reinstall-Block DISABLED ($removed rule(s) removed)." 'Yellow'
        } else {
            Write-Line "No Audion deny rules found - nothing to remove." 'Yellow'
        }
    } catch {
        Write-Line "Failed to update AppLocker policy: $($_.Exception.Message)" 'Red'
        exit 1
    }
}

$verb = $PSCmdlet.ParameterSetName
Start-BrickLog -BrickName 'AppX-ReinstallBlock' -Verb $verb -ScriptRoot $here | Out-Null
try {
    switch ($verb) {
        'Enable'  { Enable-Guard }
        'Disable' { Disable-Guard }
        default   { Show-Status }
    }
} finally {
    Stop-BrickLog
}
