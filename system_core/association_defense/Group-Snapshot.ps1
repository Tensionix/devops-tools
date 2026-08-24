<#
.SYNOPSIS
    Audion DevOps Tools - Group Snapshot brick.
.DESCRIPTION
    Captures file/protocol association subsets by group. This is the staged
    companion to Golden-Snapshot.ps1: commit photo/audio/video/pdf/browser
    groups as the real applications become installed and their ProgIDs appear
    in the live association map.

    Operations:
        -Status          Show groups, entry counts, drift, and missing ProgIDs.
        -Commit <group>  Capture only a group or custom -Ext list into a group.
        -Compose         Merge existing groups into the monolithic snapshot.

    Groups record state; they do not write associations back. Windows protects
    UserChoice with a per-user hash, and this project refuses to forge it -
    apply defaults through the Policy tab instead.

.EXAMPLE
    .\Group-Snapshot.ps1 -Status
    .\Group-Snapshot.ps1 -Commit photo -DryRun
    .\Group-Snapshot.ps1 -Commit custom-media -Ext ".mp4,.mkv,.flac"
    .\Group-Snapshot.ps1 -Compose
#>

[CmdletBinding(DefaultParameterSetName = 'Status')]
param(
    [Parameter(ParameterSetName = 'Status')] [switch]$Status,
    [Parameter(ParameterSetName = 'Commit', Mandatory = $true)] [ValidateNotNullOrEmpty()] [string]$Commit,
    [Parameter(ParameterSetName = 'Compose')] [switch]$Compose,
    [string]$Ext = '',
    [string]$Name = 'Microsoft Snapshot',
    [string]$Machine = $env:COMPUTERNAME,
    [switch]$DryRun
)

$here = Split-Path -Parent $MyInvocation.MyCommand.Path
$common = Join-Path $here '_Common.ps1'
if (-not (Test-Path -LiteralPath $common)) {
    Write-Host "ERROR: _Common.ps1 not found next to this script." -ForegroundColor Red
    exit 2
}
. $common

$SnapshotDir = Join-Path $here 'snapshots'
$GroupDir = Join-Path $SnapshotDir 'groups'

# Data-driven group model. Adjusting membership is one edit here.
# The lists mirror the file-type classification of Audion Disk Tools, so both
# tools mean the same thing by "photo" or "audio". Extensions with no live
# association are simply reported as missing, never invented.
$GroupExtensions = [ordered]@{
    'photo'   = @(
        '.ani', '.bmp', '.cur', '.dib', '.gif', '.heic', '.heif', '.avif', '.ico', '.jpeg',
        '.jpg', '.jxl', '.png', '.rle', '.webp', '.dpx', '.emf', '.eps', '.exr', '.hdr',
        '.psd', '.svg', '.svgz', '.tif', '.tiff', '.wmf', '.3fr', '.ari', '.arw', '.bay',
        '.braw', '.cap', '.cr2', '.cr3', '.crw', '.dcr', '.dcs', '.dng', '.drf', '.eip',
        '.erf', '.fff', '.gpr', '.iiq', '.k25', '.kdc', '.mdc', '.mef', '.mos', '.mrw',
        '.nef', '.nrw', '.obm', '.orf', '.pef', '.ptx', '.pxn', '.r3d', '.raf', '.raw',
        '.rw2', '.rwl', '.rwz', '.sr2', '.srf', '.srw', '.x3f'
    )
    'audio'   = @(
        '.aif', '.aifc', '.aiff', '.alac', '.ape', '.caf', '.flac', '.tak', '.tta', '.wav',
        '.wv', '.aac', '.aax', '.m4a', '.m4b', '.m4p', '.m4r', '.mp1', '.mp2', '.mp3',
        '.mpga', '.oga', '.ogg', '.opus', '.wma', '.ac3', '.amr', '.dts', '.eac3', '.mka',
        '.mogg', '.vox', '.mid', '.midi', '.mod', '.s3m', '.sid', '.snd', '.spc', '.voc',
        '.xm', '.cda', '.movpkg', '.mpa', '.mpc', '.ra', '.ram', '.rm', '.rmi', '.rmx', '.rv'
    )
    'video'   = @(
        '.mkv', '.mov', '.mp4', '.mxf', '.webm', '.asf', '.avi', '.divx', '.m4v', '.mpe',
        '.mpeg', '.mpg', '.wmv', '.ifo', '.m2p', '.m2s', '.m2t', '.m2ts', '.m2v', '.mts',
        '.vob', '.3g2', '.3gp', '.3gp2', '.3gpp', '.3gpp2', '.3mm', '.amv', '.dv', '.f4v',
        '.flv', '.ogm', '.ogv', '.av1', '.m1v', '.srt', '.ts', '.vp9'
    )
    'pdf'     = @('.pdf', '.djv', '.djvu', '.xps', '.chm')
    'documents' = @(
        '.doc', '.docx', '.xls', '.xlsx', '.ppt', '.pptx', '.accdb', '.pub', '.vsd', '.one',
        '.oft', '.onetoc2', '.rtf', '.txt', '.md', '.markdown', '.csv', '.tab', '.dif',
        '.xml', '.ini', '.cfg'
    )
    'archives' = @('.7z', '.zip', '.rar', '.tar', '.gz', '.bz2', '.cab', '.iso', '.img', '.nrg', '.tib', '.rpm')
    'browser' = @('http', 'https', '.htm', '.html', '.mht')
}

function Get-SafeMachine {
    return (($Machine -replace '[^\w\-]', '_').Trim())
}

function Get-GroupSlug {
    param([Parameter(Mandatory)][string]$GroupName)
    $slug = ($GroupName.Trim().ToLowerInvariant() -replace '[^\w\- ]', '') -replace '\s+', '-'
    $slug = $slug.Trim('-', '_', '.')
    if (-not $slug) {
        Write-Line "ERROR: group name becomes empty after sanitizing: $GroupName" 'Red'
        exit 1
    }
    return $slug
}

function Get-GroupPath {
    param([Parameter(Mandatory)][string]$GroupName)
    $safeMachine = Get-SafeMachine
    $slug = Get-GroupSlug -GroupName $GroupName
    return (Join-Path $GroupDir ("{0}.{1}.txt" -f $slug, $safeMachine))
}

function Get-MonolithicSnapshotPath {
    $slug = ($Name -replace '[^\w\- ]', '') -replace '\s+', '-'
    $safeMachine = Get-SafeMachine
    return (Join-Path $SnapshotDir ("{0}.{1}.txt" -f $slug, $safeMachine))
}

function Convert-ExtTextToList {
    param([string]$Text)
    $items = @()
    foreach ($part in (($Text.Trim()) -split '[,;\s]+')) {
        $value = $part.Trim().ToLowerInvariant()
        if ($value) { $items += $value }
    }
    return @($items | Select-Object -Unique)
}

function Get-ExtensionsForCommit {
    param(
        [Parameter(Mandatory)][string]$GroupName,
        [string]$ExtText = ''
    )
    # PowerShell unrolls an empty array on return, so the call site re-wraps it:
    # under Set-StrictMode a bare $null.Count is a terminating error.
    $custom = @(Convert-ExtTextToList -Text $ExtText)
    if ($custom.Count -gt 0) {
        return $custom
    }
    $slug = Get-GroupSlug -GroupName $GroupName
    if ($GroupExtensions.Contains($slug)) {
        return @($GroupExtensions[$slug])
    }
    Write-Line "ERROR: custom group '$slug' needs -Ext '.a,.b,proto'." 'Red'
    exit 1
}

function Get-GroupNamesFromDisk {
    $safeMachine = Get-SafeMachine
    $names = @()
    foreach ($key in $GroupExtensions.Keys) { $names += [string]$key }
    if (Test-Path -LiteralPath $GroupDir) {
        foreach ($item in (Get-ChildItem -LiteralPath $GroupDir -Filter '*.txt' -File -ErrorAction SilentlyContinue)) {
            $base = [System.IO.Path]::GetFileNameWithoutExtension($item.Name)
            $suffix = ".$safeMachine"
            if ($base.EndsWith($suffix, [System.StringComparison]::OrdinalIgnoreCase)) {
                $group = $base.Substring(0, $base.Length - $suffix.Length)
                if ($group -and ($names -notcontains $group)) {
                    $names += $group
                }
            }
        }
    }
    return @($names)
}

function Read-GroupEntries {
    param([Parameter(Mandatory)][string]$GroupName)
    return @(Read-AssociationEntryFile -Path (Get-GroupPath -GroupName $GroupName))
}

function Show-GroupStatus {
    Write-Line "Group Snapshot status" 'Cyan'
    Write-Line ("Machine: {0}" -f (Get-SafeMachine))
    Write-Line ("Folder : {0}" -f $GroupDir)
    Write-Line ("-" * 84)

    $currentEntries = Get-AssociationDump
    $currentMap = Convert-AssociationEntriesToMap -Entries $currentEntries

    foreach ($group in (Get-GroupNamesFromDisk)) {
        $path = Get-GroupPath -GroupName $group
        if (-not (Test-Path -LiteralPath $path)) {
            Write-Host ("{0,-14} MISSING   entries=0   drift=-   progid=-" -f $group) -ForegroundColor Yellow
            continue
        }

        $entries = Read-AssociationEntryFile -Path $path
        $savedMap = Convert-AssociationEntriesToMap -Entries $entries
        $drift = 0
        foreach ($key in $savedMap.Keys) {
            $current = if ($currentMap.ContainsKey($key)) { $currentMap[$key] } else { '<unset>' }
            if ($current -ne $savedMap[$key]) { $drift++ }
        }
        $missingProgIds = Get-AssociationMissingProgIds -Entries $entries
        $state = if ($drift -eq 0) { 'MATCH' } else { 'DRIFT' }
        $color = if ($drift -eq 0 -and $missingProgIds.Count -eq 0) { 'Green' } else { 'Yellow' }
        Write-Host ("{0,-14} {1,-8} entries={2,-3} drift={3,-3} progid-missing={4}" -f $group, $state, $entries.Count, $drift, $missingProgIds.Count) -ForegroundColor $color
        if ($drift -gt 0) {
            foreach ($key in ($savedMap.Keys | Sort-Object)) {
                $current = if ($currentMap.ContainsKey($key)) { $currentMap[$key] } else { '<unset>' }
                if ($current -ne $savedMap[$key]) {
                    Write-Host ("  DRIFT {0,-12} now={1,-28} group={2}" -f $key, $current, $savedMap[$key]) -ForegroundColor Yellow
                }
            }
        }
        foreach ($missing in ($missingProgIds | Select-Object -First 5)) {
            Write-Host "  MISSING-PROGID $missing" -ForegroundColor DarkYellow
        }
        if ($missingProgIds.Count -gt 5) {
            Write-Host "  ... and $($missingProgIds.Count - 5) more missing ProgIDs" -ForegroundColor DarkYellow
        }
    }
    Write-Line ("-" * 84)
}

function Commit-Group {
    param([Parameter(Mandatory)][string]$GroupName)
    if (-not $DryRun) { Assert-Admin }

    $slug = Get-GroupSlug -GroupName $GroupName
    $wanted = Get-ExtensionsForCommit -GroupName $slug -ExtText $Ext
    $currentEntries = Get-AssociationDump
    $currentMap = Convert-AssociationEntriesToMap -Entries $currentEntries

    $entries = @()
    $missing = @()
    foreach ($identifier in $wanted) {
        $key = Normalize-AssociationIdentifier -Identifier $identifier
        if ($currentMap.ContainsKey($key)) {
            $entries += ("{0}, {1}" -f $key, $currentMap[$key])
        } else {
            $missing += $key
        }
    }

    if ($missing.Count -gt 0) {
        # A group can list dozens of extensions, so the report stays readable:
        # nothing is set for most of them, and that is normal, not an error.
        $shown = @($missing | Select-Object -First 12)
        $tail = if ($missing.Count -gt $shown.Count) { " ... and $($missing.Count - $shown.Count) more" } else { '' }
        Write-Line ("No association set for {0} of {1} type(s): {2}{3}" -f $missing.Count, $wanted.Count, ($shown -join ', '), $tail) 'DarkYellow'
    }
    if ($entries.Count -eq 0) {
        Write-Line "ERROR: no matching live associations found; refusing to overwrite an empty group." 'Red'
        exit 1
    }

    $path = Get-GroupPath -GroupName $slug
    if (Test-DryRun -DryRun:$DryRun -Action "commit group '$slug' with $($entries.Count) entr(y/ies) to $path") {
        $entries | ForEach-Object { Write-Host "    $_" -ForegroundColor DarkGray }
        return
    }

    $header = @(
        "# Group Snapshot: $slug"
        "# Machine : $(Get-SafeMachine)"
        "# Captured: $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')"
        "# Entries : $($entries.Count)"
        "# Ext     : $($wanted -join ' ')"
        "# ---------------------------------------------"
    )
    Write-AssociationEntryFile -Path $path -Lines ([string[]]($header + $entries))
    Write-Line "Committed group '$slug' -> $($entries.Count) entries." 'Green'
    Write-Line "  File: $path"
}

function Compose-MonolithicSnapshot {
    if (-not $DryRun) { Assert-Admin }
    $groups = @(Get-GroupNamesFromDisk | Where-Object { Test-Path -LiteralPath (Get-GroupPath -GroupName $_) })
    if ($groups.Count -eq 0) {
        Write-Line "ERROR: no group files exist under $GroupDir." 'Red'
        exit 1
    }

    $merged = [ordered]@{}
    foreach ($group in $groups) {
        foreach ($line in (Read-AssociationEntryFile -Path (Get-GroupPath -GroupName $group))) {
            $parts = ([string]$line) -split ',', 2
            if ($parts.Count -ne 2) { continue }
            $key = Normalize-AssociationIdentifier -Identifier $parts[0]
            $merged[$key] = ("{0}, {1}" -f $key, $parts[1].Trim())
        }
    }

    $entries = @()
    foreach ($key in $merged.Keys) {
        $entries += $merged[$key]
    }
    $path = Get-MonolithicSnapshotPath
    if (Test-DryRun -DryRun:$DryRun -Action "compose $($entries.Count) entr(y/ies) from $($groups.Count) group(s) into $path") {
        $entries | Select-Object -First 20 | ForEach-Object { Write-Host "    $_" -ForegroundColor DarkGray }
        if ($entries.Count -gt 20) { Write-Host "    ... and $($entries.Count - 20) more" -ForegroundColor DarkGray }
        return
    }

    $header = @(
        "# $Name"
        "# Machine : $(Get-SafeMachine)"
        "# Composed: $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')"
        "# Groups  : $($groups -join ', ')"
        "# Entries : $($entries.Count)"
        "# ---------------------------------------------"
    )
    Write-AssociationEntryFile -Path $path -Lines ([string[]]($header + $entries))
    Write-Line "Composed monolithic snapshot from groups -> $($entries.Count) entries." 'Green'
    Write-Line "  File: $path"
}

$verb = $PSCmdlet.ParameterSetName
$logVerb = switch ($verb) {
    'Commit'  { "Commit-$Commit" }
    'Compose' { 'Compose' }
    default   { 'Status' }
}

Start-BrickLog -BrickName 'Group-Snapshot' -Verb $logVerb -ScriptRoot $here | Out-Null
try {
    switch ($verb) {
        'Commit'   { Commit-Group -GroupName $Commit }
        'Compose'  { Compose-MonolithicSnapshot }
        default    { Show-GroupStatus }
    }
} finally {
    Stop-BrickLog
}
