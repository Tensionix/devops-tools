<#
    Verified backup, restore and Claude-memory merge for Claude Code and Codex.

    Export creates a fresh bundle atomically and records every data file in
    manifest.json with its SHA-256. Authentication is excluded unless
    -IncludeAuth is supplied. Import validates the whole bundle before writing.

      AI-Backup.ps1 -Mode Export -Path <dir> [-Full] [-IncludeAuth] [-DryRun]
      AI-Backup.ps1 -Mode Import -Path <dir> [-Full] [-IncludeAuth] [-DryRun]
                    [-AllowForeignPaths] [-AllowLegacy] [-Yes]
      AI-Backup.ps1 -Mode Merge  -Path <dir> [-Overwrite] [-DryRun] [-AllowLegacy]

    Profile roots follow CLAUDE_CONFIG_DIR, CODEX_HOME, CODEX_SQLITE_HOME and
    Codex config.toml sqlite_home. Matching files are overwritten on restore;
    unrelated local files are never deleted.
#>
[CmdletBinding()]
param(
    [ValidateSet('Export', 'Import', 'Merge')][string]$Mode,
    [string]$Path,
    [switch]$Full,
    [switch]$IncludeAuth,
    [switch]$Yes,
    [switch]$Overwrite,
    [switch]$DryRun,
    [switch]$AllowForeignPaths,
    [switch]$AllowLegacy,
    [switch]$AllowRunningApps
)

$ErrorActionPreference = 'Stop'
try { [Console]::OutputEncoding = [System.Text.Encoding]::UTF8 } catch { }

$script:BundleSchemaVersion = 1
$script:Utf8NoBom = New-Object System.Text.UTF8Encoding($false)
$script:ProjectRoot = [System.IO.Path]::GetFullPath((Join-Path $PSScriptRoot '..\..'))

function Resolve-AbsolutePath([string]$Value, [string]$Default, [string]$Base) {
    $candidate = if ([string]::IsNullOrWhiteSpace($Value)) { $Default } else { $Value.Trim().Trim('"') }
    $candidate = [Environment]::ExpandEnvironmentVariables($candidate)
    if ($candidate -eq '~') { $candidate = $script:UserProfile }
    elseif ($candidate.StartsWith('~\') -or $candidate.StartsWith('~/')) {
        $candidate = Join-Path $script:UserProfile $candidate.Substring(2)
    }
    if (-not [System.IO.Path]::IsPathRooted($candidate)) { $candidate = Join-Path $Base $candidate }
    return [System.IO.Path]::GetFullPath($candidate)
}

function Read-CodexSqliteHome([string]$CodexRoot, [string]$ConfigPath = '') {
    $configured = $null
    $config = if ($ConfigPath) { $ConfigPath } else { Join-Path $CodexRoot 'config.toml' }
    if (Test-Path -LiteralPath $config -PathType Leaf) {
        $pattern = @'
(?m)^\s*sqlite_home\s*=\s*(?:"(?<double>(?:\\.|[^"])*)"|'(?<single>[^']*)')\s*(?:#.*)?$
'@
        $match = [regex]::Match([System.IO.File]::ReadAllText($config), $pattern)
        if ($match.Success) {
            $configured = if ($match.Groups['double'].Success) {
                $match.Groups['double'].Value.Replace('\"', '"').Replace('\\', '\')
            } else { $match.Groups['single'].Value }
        }
    }
    if (-not [string]::IsNullOrWhiteSpace($configured)) {
        return Resolve-AbsolutePath $configured $CodexRoot (Get-Location).Path
    }
    return Resolve-AbsolutePath $env:CODEX_SQLITE_HOME $CodexRoot (Get-Location).Path
}

function Get-RelativePath([string]$Base, [string]$Child) {
    $baseFull = [System.IO.Path]::GetFullPath($Base).TrimEnd('\') + '\'
    $childFull = [System.IO.Path]::GetFullPath($Child)
    $baseUri = New-Object System.Uri($baseFull)
    $childUri = New-Object System.Uri($childFull)
    return [System.Uri]::UnescapeDataString($baseUri.MakeRelativeUri($childUri).ToString()).Replace('/', '\')
}

function Assert-BundleOutsideProfiles([string]$BundleRoot) {
    $bundle = [System.IO.Path]::GetFullPath($BundleRoot).TrimEnd('\')
    foreach ($profile in @($script:ClaudeHome, $script:CodexHome, $script:CodexSqliteHome) | Select-Object -Unique) {
        if ([string]::IsNullOrWhiteSpace($profile)) { continue }
        $root = [System.IO.Path]::GetFullPath($profile).TrimEnd('\')
        $bundleInside = $bundle.StartsWith($root + '\', [System.StringComparison]::OrdinalIgnoreCase)
        $profileInside = $root.StartsWith($bundle + '\', [System.StringComparison]::OrdinalIgnoreCase)
        if ($bundle.Equals($root, [System.StringComparison]::OrdinalIgnoreCase) -or $bundleInside -or $profileInside) {
            throw "Bundle не должен пересекаться с профилем Claude/Codex: $bundle <-> $root"
        }
    }
}

function Get-SafeBundlePath([string]$Root, [string]$Relative) {
    if ([string]::IsNullOrWhiteSpace($Relative) -or [System.IO.Path]::IsPathRooted($Relative)) {
        throw "Небезопасный путь в manifest: $Relative"
    }
    $parts = @($Relative -split '[\\/]')
    if ($parts -contains '..' -or $parts -contains '.') { throw "Небезопасный путь в manifest: $Relative" }
    $rootFull = [System.IO.Path]::GetFullPath($Root).TrimEnd('\')
    $full = [System.IO.Path]::GetFullPath((Join-Path $rootFull ($Relative.Replace('/', '\'))))
    if (-not $full.StartsWith($rootFull + '\', [System.StringComparison]::OrdinalIgnoreCase)) {
        throw "Путь выходит из bundle: $Relative"
    }
    $current = $rootFull
    foreach ($part in $parts) {
        $current = Join-Path $current $part
        if (Test-Path -LiteralPath $current) {
            $item = Get-Item -LiteralPath $current -Force
            if (($item.Attributes -band [System.IO.FileAttributes]::ReparsePoint) -ne 0) {
                throw "Reparse point внутри bundle запрещён: $Relative"
            }
        }
    }
    return $full
}

function Invoke-Robocopy([string]$Source, [string]$Destination, [string[]]$ExcludeFiles = @()) {
    if (-not (Test-Path -LiteralPath $Source -PathType Container)) { return $false }
    New-Item -ItemType Directory -Force -Path $Destination | Out-Null
    $arguments = @($Source, $Destination, '/E', '/XJ', '/R:2', '/W:1', '/COPY:DAT', '/DCOPY:DAT', '/NFL', '/NDL', '/NJH', '/NJS', '/NP')
    if ($ExcludeFiles.Count) { $arguments += '/XF'; $arguments += $ExcludeFiles }
    $output = @(& robocopy.exe @arguments 2>&1)
    $code = $LASTEXITCODE
    if ($code -ge 8) {
        $tail = ($output | Select-Object -Last 12) -join [Environment]::NewLine
        throw "robocopy завершился с кодом $code`: $Source -> $Destination`n$tail"
    }
    return $true
}

function Copy-OneFile([string]$Source, [string]$Destination) {
    if (-not (Test-Path -LiteralPath $Source -PathType Leaf)) { return $false }
    New-Item -ItemType Directory -Force -Path (Split-Path -Parent $Destination) | Out-Null
    Copy-Item -LiteralPath $Source -Destination $Destination -Force
    return $true
}

function Copy-SelectedItems([string]$Source, [string]$Destination, [string[]]$Items) {
    foreach ($item in $Items) {
        $src = Join-Path $Source $item
        if (-not (Test-Path -LiteralPath $src)) { continue }
        $dst = Join-Path $Destination $item
        if ((Get-Item -LiteralPath $src).PSIsContainer) { [void](Invoke-Robocopy $src $dst) }
        else { [void](Copy-OneFile $src $dst) }
        Write-Host "   $item"
    }
}

function Find-Python {
    $candidates = @()
    if (-not [string]::IsNullOrWhiteSpace($env:AUDION_GUI_PYTHON)) { $candidates += $env:AUDION_GUI_PYTHON }
    $candidates += (Join-Path $script:ProjectRoot 'runtime\python.exe')
    foreach ($name in @('python.exe', 'python')) {
        $command = Get-Command $name -ErrorAction SilentlyContinue
        if ($command) { $candidates += $command.Source }
    }
    foreach ($candidate in $candidates) {
        if ($candidate -and (Test-Path -LiteralPath $candidate -PathType Leaf)) { return [System.IO.Path]::GetFullPath($candidate) }
    }
    throw 'Python не найден: он нужен для согласованного snapshot активных SQLite-баз Codex.'
}

function Save-SqliteSnapshot([string]$Source, [string]$Destination) {
    $python = Find-Python
    $helper = Join-Path $PSScriptRoot 'sqlite_snapshot.py'
    New-Item -ItemType Directory -Force -Path (Split-Path -Parent $Destination) | Out-Null
    & $python $helper snapshot --source $Source --destination $Destination
    if ($LASTEXITCODE -ne 0) { throw "SQLite snapshot не создан: $Source" }
}

function Get-SqliteFiles([switch]$Everything) {
    if (-not (Test-Path -LiteralPath $script:CodexSqliteHome -PathType Container)) { return @() }
    if (-not $Everything) {
        return @('memories_1.sqlite', 'goals_1.sqlite') | ForEach-Object {
            $candidate = Join-Path $script:CodexSqliteHome $_
            if (Test-Path -LiteralPath $candidate -PathType Leaf) { Get-Item -LiteralPath $candidate }
        }
    }
    return @(Get-ChildItem -LiteralPath $script:CodexSqliteHome -Recurse -File -ErrorAction SilentlyContinue | Where-Object {
        $_.Name -notmatch '-(wal|shm|journal)$' -and $_.Extension -in @('.sqlite', '.sqlite3', '.db', '.db3')
    })
}

function Copy-SqliteState([string]$BundleRoot, [switch]$Everything) {
    foreach ($database in @(Get-SqliteFiles -Everything:$Everything)) {
        $relative = Get-RelativePath $script:CodexSqliteHome $database.FullName
        $destination = Join-Path $BundleRoot "codex_sqlite\$relative"
        Save-SqliteSnapshot $database.FullName $destination
        Write-Host "   SQLite snapshot: $relative"
    }
}

function Get-FileCategory([string]$Relative) {
    $path = $Relative.Replace('\', '/').ToLowerInvariant()
    if ($path -in @('claude/.credentials.json', 'codex/auth.json')) { return 'auth' }
    if ($path -eq 'claude.json') { return 'essential' }
    if ($path -match '^claude/(settings\.json|settings\.local\.json|claude\.md)$') { return 'essential' }
    if ($path -match '^claude/(skills|plugins)/') { return 'essential' }
    if ($path -match '^claude/projects/[^/]+/memory/') { return 'essential' }
    if ($path -match '^codex/(config\.toml|agents\.md)$') { return 'essential' }
    if ($path -match '^codex/(memories|rules|automations|skills|plugins)/') { return 'essential' }
    if ($path -match '^codex(_sqlite)?/(memories_1|goals_1)\.sqlite$') { return 'essential' }
    return 'full'
}

function Get-AbsolutePathWarnings([string]$BundleRoot) {
    $warnings = @()
    foreach ($relative in @('claude.json', 'claude\settings.json', 'claude\settings.local.json', 'codex\config.toml')) {
        $file = Join-Path $BundleRoot $relative
        if (-not (Test-Path -LiteralPath $file -PathType Leaf)) { continue }
        $count = 0
        foreach ($line in (Get-Content -LiteralPath $file -ErrorAction SilentlyContinue)) {
            if ($line -match '(?i)(?:[A-Z]:\\|\\\\[^\\]+\\)') { $count++ }
        }
        if ($count) {
            $warnings += [pscustomobject]@{ file = $relative.Replace('\', '/'); absolute_path_lines = $count }
        }
    }
    return $warnings
}

function Write-Manifest([string]$BundleRoot, [bool]$IsFull, [bool]$HasAuth) {
    $entries = @()
    foreach ($file in (Get-ChildItem -LiteralPath $BundleRoot -Recurse -File | Sort-Object FullName)) {
        $relative = (Get-RelativePath $BundleRoot $file.FullName).Replace('\', '/')
        if ($relative -in @('manifest.json', 'BACKUP_INFO.txt')) { continue }
        $entries += [pscustomobject]@{
            path = $relative
            size = [int64]$file.Length
            sha256 = (Get-FileHash -LiteralPath $file.FullName -Algorithm SHA256).Hash.ToLowerInvariant()
            category = Get-FileCategory $relative
        }
    }
    if (-not $entries.Count) { throw 'Не найдено ни одного файла Claude/Codex для экспорта.' }

    $version = 'unknown'
    $versionFile = Join-Path $script:ProjectRoot 'config\version.json'
    if (Test-Path -LiteralPath $versionFile) {
        try { $version = [string]((Get-Content -LiteralPath $versionFile -Raw | ConvertFrom-Json).version) } catch { }
    }
    $manifest = [ordered]@{
        schema_version = $script:BundleSchemaVersion
        bundle_id = [guid]::NewGuid().ToString()
        created_utc = [DateTime]::UtcNow.ToString('o')
        tool_version = $version
        profile_mode = if ($IsFull) { 'full' } else { 'essential' }
        includes_auth = @($entries | Where-Object { $_.category -eq 'auth' }).Count -gt 0
        auth_requested = $HasAuth
        source = [ordered]@{
            computer = $env:COMPUTERNAME
            claude_config_dir = $script:ClaudeHome
            claude_state_file = $script:ClaudeStateFile
            codex_home = $script:CodexHome
            codex_sqlite_home = $script:CodexSqliteHome
        }
        absolute_path_warnings = @(Get-AbsolutePathWarnings $BundleRoot)
        files = $entries
    }
    [System.IO.File]::WriteAllText((Join-Path $BundleRoot 'manifest.json'), ($manifest | ConvertTo-Json -Depth 8), $script:Utf8NoBom)
    return $manifest
}

function Read-AndVerifyManifest([string]$BundleRoot, [switch]$LegacyAllowed) {
    $manifestPath = Join-Path $BundleRoot 'manifest.json'
    if (-not (Test-Path -LiteralPath $manifestPath -PathType Leaf)) {
        if (-not $LegacyAllowed) {
            throw 'manifest.json отсутствует. Старый непроверяемый бэкап можно открыть только с -AllowLegacy.'
        }
        Write-Host 'ВНИМАНИЕ: legacy-бэкап без manifest и хешей.' -ForegroundColor Yellow
        $legacy = @()
        foreach ($file in (Get-ChildItem -LiteralPath $BundleRoot -Recurse -File)) {
            $relative = (Get-RelativePath $BundleRoot $file.FullName).Replace('\', '/')
            if ($relative -eq 'BACKUP_INFO.txt') { continue }
            $legacy += [pscustomobject]@{ path = $relative; size = [int64]$file.Length; sha256 = ''; category = Get-FileCategory $relative }
        }
        return [pscustomobject]@{ schema_version = 0; profile_mode = 'legacy'; includes_auth = $true; source = $null; absolute_path_warnings = @(); files = $legacy }
    }

    $manifest = Get-Content -LiteralPath $manifestPath -Raw | ConvertFrom-Json
    if ([int]$manifest.schema_version -ne $script:BundleSchemaVersion) {
        throw "Неподдерживаемая версия manifest: $($manifest.schema_version)"
    }
    $declared = @{}
    foreach ($entry in @($manifest.files)) {
        $relative = [string]$entry.path
        $key = $relative.ToLowerInvariant()
        if ($declared.ContainsKey($key)) { throw "Повтор пути в manifest: $relative" }
        $expectedCategory = Get-FileCategory $relative
        if ([string]$entry.category -ne $expectedCategory) { throw "Неверная категория в manifest: $relative" }
        $file = Get-SafeBundlePath $BundleRoot $relative
        if (-not (Test-Path -LiteralPath $file -PathType Leaf)) { throw "Файл из manifest отсутствует: $relative" }
        $actualSize = (Get-Item -LiteralPath $file).Length
        if ([int64]$entry.size -ne [int64]$actualSize) { throw "Размер не совпал: $relative" }
        $actualHash = (Get-FileHash -LiteralPath $file -Algorithm SHA256).Hash.ToLowerInvariant()
        if ($actualHash -ne ([string]$entry.sha256).ToLowerInvariant()) { throw "SHA-256 не совпал: $relative" }
        $declared[$key] = $true
    }
    if (-not $declared.Count) { throw 'Manifest не содержит файлов данных.' }
    foreach ($file in (Get-ChildItem -LiteralPath $BundleRoot -Recurse -File)) {
        $relative = (Get-RelativePath $BundleRoot $file.FullName).Replace('\', '/')
        if ($relative -in @('manifest.json', 'BACKUP_INFO.txt')) { continue }
        if (-not $declared.ContainsKey($relative.ToLowerInvariant())) { throw "В bundle есть незаявленный файл: $relative" }
    }
    Write-Host "Manifest и SHA-256: PASS ($($declared.Count) файлов)" -ForegroundColor Green
    return $manifest
}

function Test-ForeignPaths([object]$Manifest) {
    $warnings = @($Manifest.absolute_path_warnings)
    if (-not $warnings.Count -or -not $Manifest.source) { return }
    $foreign = $false
    foreach ($pair in @(
        @([string]$Manifest.source.claude_config_dir, $script:ClaudeHome),
        @([string]$Manifest.source.codex_home, $script:CodexHome),
        @([string]$Manifest.source.codex_sqlite_home, $script:CodexSqliteHome)
    )) {
        if ($pair[0] -and -not $pair[0].Equals($pair[1], [System.StringComparison]::OrdinalIgnoreCase)) { $foreign = $true }
    }
    if ($Manifest.source.computer -and $env:COMPUTERNAME -and -not ([string]$Manifest.source.computer).Equals($env:COMPUTERNAME, [System.StringComparison]::OrdinalIgnoreCase)) {
        $foreign = $true
    }
    if (-not $foreign) { return }
    Write-Host 'В конфигурации обнаружены абсолютные пути другого профиля:' -ForegroundColor Yellow
    foreach ($warning in $warnings) { Write-Host "   $($warning.file): строк с путями $($warning.absolute_path_lines)" }
    if (-not $AllowForeignPaths -and -not $DryRun) {
        throw 'Импорт остановлен. Проверь пути и повтори с -AllowForeignPaths, если они допустимы.'
    }
}

function Resolve-ImportDestination([string]$Relative) {
    $path = $Relative.Replace('\', '/')
    if ($path.Equals('claude.json', [System.StringComparison]::OrdinalIgnoreCase)) { return $script:ClaudeStateFile }
    if ($path -match '(?i)^claude/(.+)$') { return Join-Path $script:ClaudeHome $Matches[1].Replace('/', '\') }
    if ($path -match '(?i)^codex_sqlite/(.+)$') { return Join-Path $script:CodexSqliteHome $Matches[1].Replace('/', '\') }
    if ($path -match '(?i)^codex/((?:memories_1|goals_1)\.sqlite(?:-(?:wal|shm|journal))?)$') {
        return Join-Path $script:CodexSqliteHome $Matches[1]
    }
    if ($path -match '(?i)^codex/(.+)$') { return Join-Path $script:CodexHome $Matches[1].Replace('/', '\') }
    throw "Неизвестный компонент bundle: $Relative"
}

function Assert-AppsStopped([bool]$NeedClaude, [bool]$NeedCodex) {
    if ($AllowRunningApps -or $DryRun) { return }
    $running = @()
    if ($NeedClaude -and @(Get-Process -Name 'claude' -ErrorAction SilentlyContinue).Count) { $running += 'Claude' }
    if ($NeedCodex -and @(Get-Process -Name 'Codex', 'codex' -ErrorAction SilentlyContinue).Count) { $running += 'Codex' }
    if ($running.Count) { throw "Закрой приложения перед импортом: $($running -join ', '). Для аварийного осознанного запуска есть -AllowRunningApps." }
}

function Copy-ManifestEntries([string]$BundleRoot, [object[]]$Entries) {
    $needClaude = @($Entries | Where-Object { ([string]$_.path) -match '(?i)^claude(?:/|\.json$)' }).Count -gt 0
    $needCodex = @($Entries | Where-Object { ([string]$_.path) -match '(?i)^codex(?:/|_)' }).Count -gt 0
    Assert-AppsStopped $needClaude $needCodex
    $added = 0; $replaced = 0; $same = 0
    foreach ($entry in $Entries) {
        $relative = [string]$entry.path
        $source = Get-SafeBundlePath $BundleRoot $relative
        $destination = Resolve-ImportDestination $relative
        $state = 'ADD'
        if (Test-Path -LiteralPath $destination -PathType Leaf) {
            $sourceHash = if ($entry.sha256) { [string]$entry.sha256 } else { (Get-FileHash -LiteralPath $source -Algorithm SHA256).Hash }
            try {
                $destinationHash = (Get-FileHash -LiteralPath $destination -Algorithm SHA256).Hash
                if ($sourceHash.Equals($destinationHash, [System.StringComparison]::OrdinalIgnoreCase)) { $state = 'SAME'; $same++ }
                else { $state = 'REPLACE'; $replaced++ }
            } catch {
                if (-not $DryRun) { throw }
                $state = 'LOCKED'; $replaced++
            }
        } else { $added++ }
        Write-Host ("   {0,-7} {1}" -f $state, $destination)
        if ($DryRun -or $state -eq 'SAME') { continue }
        New-Item -ItemType Directory -Force -Path (Split-Path -Parent $destination) | Out-Null
        $temporary = "$destination.ai-backup-tmp.$([guid]::NewGuid().ToString('N'))"
        try {
            Copy-Item -LiteralPath $source -Destination $temporary -Force
            Move-Item -LiteralPath $temporary -Destination $destination -Force
        } finally {
            if (Test-Path -LiteralPath $temporary) { Remove-Item -LiteralPath $temporary -Force }
        }
    }
    Write-Host ("План/результат: новых {0}, заменено {1}, без изменений {2}" -f $added, $replaced, $same)
}

function Merge-MemoryIndex([string]$SourceIndex, [string]$DestinationIndex) {
    $destinationText = [System.IO.File]::ReadAllText($DestinationIndex)
    $have = @{}
    foreach ($match in [regex]::Matches($destinationText, '\(([^)]+\.md)\)')) { $have[$match.Groups[1].Value] = $true }
    $add = @()
    foreach ($line in (Get-Content -LiteralPath $SourceIndex -Encoding UTF8)) {
        $link = [regex]::Match($line, '\(([^)]+\.md)\)')
        if ($link.Success -and $line -match '^\s*-\s*\[' -and -not $have[$link.Groups[1].Value]) { $add += $line }
    }
    if ($add.Count -and -not $DryRun) {
        $newline = if ($destinationText -match "`r`n") { "`r`n" } else { "`n" }
        $block = $newline + $newline + '<!-- merged -->' + $newline + ($add -join $newline) + $newline
        [System.IO.File]::AppendAllText($DestinationIndex, $block, $script:Utf8NoBom)
    }
}

function Invoke-ClaudeMemoryMerge([string]$BundleRoot, [object]$Manifest) {
    $entries = @($Manifest.files | Where-Object {
        ([string]$_.path) -match '(?i)^claude/projects/[^/]+/memory/[^/]+\.md$'
    })
    if (-not $entries.Count) { throw 'В bundle нет Claude projects/*/memory/*.md.' }
    Assert-AppsStopped $true $false
    $added = 0; $replaced = 0; $conflicts = 0
    $indexes = @()
    foreach ($entry in $entries) {
        $relative = [string]$entry.path
        $source = Get-SafeBundlePath $BundleRoot $relative
        $destination = Resolve-ImportDestination $relative
        if ((Split-Path -Leaf $destination) -ieq 'MEMORY.md') { $indexes += @($source, $destination); continue }
        if (Test-Path -LiteralPath $destination) {
            if (-not $Overwrite) { $conflicts++; Write-Host "   SKIP    $destination"; continue }
            $replaced++; Write-Host "   REPLACE $destination"
        } else { $added++; Write-Host "   ADD     $destination" }
        if (-not $DryRun) {
            New-Item -ItemType Directory -Force -Path (Split-Path -Parent $destination) | Out-Null
            Copy-Item -LiteralPath $source -Destination $destination -Force
        }
    }
    for ($index = 0; $index -lt $indexes.Count; $index += 2) {
        $sourceIndex = $indexes[$index]; $destinationIndex = $indexes[$index + 1]
        if (Test-Path -LiteralPath $destinationIndex) { Merge-MemoryIndex $sourceIndex $destinationIndex }
        elseif (-not $DryRun) {
            New-Item -ItemType Directory -Force -Path (Split-Path -Parent $destinationIndex) | Out-Null
            Copy-Item -LiteralPath $sourceIndex -Destination $destinationIndex -Force
        }
    }
    Write-Host ("Слияние: новых {0}, заменено {1}, конфликтов сохранено {2}" -f $added, $replaced, $conflicts) -ForegroundColor Green
}

function Publish-AtomicBundle([string]$Temporary, [string]$Target) {
    $targetFull = [System.IO.Path]::GetFullPath($Target).TrimEnd('\')
    $parent = Split-Path -Parent $targetFull
    $leaf = Split-Path -Leaf $targetFull
    if (-not $parent -or -not $leaf -or $targetFull -eq [System.IO.Path]::GetPathRoot($targetFull).TrimEnd('\')) {
        throw "Небезопасная целевая папка: $targetFull"
    }
    if (Test-Path -LiteralPath $targetFull -PathType Leaf) { throw "Цель является файлом: $targetFull" }
    if (Test-Path -LiteralPath $targetFull -PathType Container) {
        $contents = @(Get-ChildItem -LiteralPath $targetFull -Force)
        $owned = (Test-Path -LiteralPath (Join-Path $targetFull 'manifest.json')) -or (Test-Path -LiteralPath (Join-Path $targetFull 'BACKUP_INFO.txt'))
        if ($contents.Count -and -not $owned) { throw "Целевая папка не похожа на AI-Backup и не будет перезаписана: $targetFull" }
    }
    $previous = Join-Path $parent (".$leaf.previous." + [guid]::NewGuid().ToString('N'))
    $hadPrevious = Test-Path -LiteralPath $targetFull
    if ($hadPrevious) { Move-Item -LiteralPath $targetFull -Destination $previous }
    try {
        Move-Item -LiteralPath $Temporary -Destination $targetFull
    } catch {
        if ($hadPrevious -and (Test-Path -LiteralPath $previous) -and -not (Test-Path -LiteralPath $targetFull)) {
            Move-Item -LiteralPath $previous -Destination $targetFull
        }
        throw
    }
    if (Test-Path -LiteralPath $previous) { Remove-Item -LiteralPath $previous -Recurse -Force }
}

$script:UserProfile = if ($env:USERPROFILE) { [System.IO.Path]::GetFullPath($env:USERPROFILE) } else { [Environment]::GetFolderPath('UserProfile') }
$script:ClaudeHome = Resolve-AbsolutePath $env:CLAUDE_CONFIG_DIR (Join-Path $script:UserProfile '.claude') (Get-Location).Path
$script:ClaudeStateFile = Join-Path $script:UserProfile '.claude.json'
$script:CodexHome = Resolve-AbsolutePath $env:CODEX_HOME (Join-Path $script:UserProfile '.codex') (Get-Location).Path
$script:CodexSqliteHome = Read-CodexSqliteHome $script:CodexHome

if (-not $Mode) {
    $answer = Read-Host 'Режим: [E] экспорт / [I] импорт-восстановление / [M] слияние памяти'
    $Mode = if ($answer -match '^[iIиИ]') { 'Import' } elseif ($answer -match '^[mMмМ]') { 'Merge' } else { 'Export' }
}
if (-not $Path) { $Path = (Read-Host 'Папка бэкапа').Trim().Trim('"') }
if (-not $Path) { throw 'Путь бэкапа не задан.' }
$bundlePath = [System.IO.Path]::GetFullPath($Path)
Assert-BundleOutsideProfiles $bundlePath

Write-Host "Claude config: $script:ClaudeHome"
Write-Host "Codex home:    $script:CodexHome"
Write-Host "Codex SQLite:  $script:CodexSqliteHome"

if ($Mode -eq 'Export') {
    Write-Host "Экспорт -> $bundlePath" -ForegroundColor Cyan
    Write-Host ("Режим: {0}; авторизация: {1}; dry-run: {2}" -f $(if ($Full) { 'full' } else { 'essential' }), $IncludeAuth.IsPresent, $DryRun.IsPresent)
    if ($DryRun) { Write-Host 'Dry run: файлы не записаны.' -ForegroundColor Green; exit 0 }
    if (-not (Test-Path -LiteralPath $script:ClaudeHome) -and -not (Test-Path -LiteralPath $script:CodexHome)) {
        throw 'Не найден ни профиль Claude, ни профиль Codex.'
    }

    $parent = Split-Path -Parent $bundlePath
    if (-not $parent) { throw "Небезопасная целевая папка: $bundlePath" }
    New-Item -ItemType Directory -Force -Path $parent | Out-Null
    $temporary = Join-Path $parent ('.' + (Split-Path -Leaf $bundlePath) + '.tmp.' + [guid]::NewGuid().ToString('N'))
    New-Item -ItemType Directory -Path $temporary | Out-Null
    try {
        if ($Full) {
            Write-Host 'Claude: полный профиль'
            [void](Invoke-Robocopy $script:ClaudeHome (Join-Path $temporary 'claude') @('.credentials.json'))
            Write-Host 'Codex: полный профиль без machine-id и live SQLite'
            [void](Invoke-Robocopy $script:CodexHome (Join-Path $temporary 'codex') @(
                'auth.json', 'installation_id', '*.sqlite', '*.sqlite3', '*.db', '*.db3',
                '*.sqlite-wal', '*.sqlite-shm', '*.sqlite-journal', '*.db-wal', '*.db-shm', '*.db-journal'
            ))
        } else {
            Write-Host 'Claude: essential'
            Copy-SelectedItems $script:ClaudeHome (Join-Path $temporary 'claude') @('settings.json', 'settings.local.json', 'CLAUDE.md', 'skills', 'plugins')
            $projects = Join-Path $script:ClaudeHome 'projects'
            if (Test-Path -LiteralPath $projects -PathType Container) {
                foreach ($project in (Get-ChildItem -LiteralPath $projects -Directory -ErrorAction SilentlyContinue)) {
                    $memory = Join-Path $project.FullName 'memory'
                    if (Test-Path -LiteralPath $memory -PathType Container) {
                        [void](Invoke-Robocopy $memory (Join-Path $temporary "claude\projects\$($project.Name)\memory"))
                    }
                }
            }
            Write-Host 'Codex: essential'
            Copy-SelectedItems $script:CodexHome (Join-Path $temporary 'codex') @('config.toml', 'AGENTS.md', 'memories', 'rules', 'automations', 'skills', 'plugins')
        }
        if (Test-Path -LiteralPath $script:ClaudeStateFile -PathType Leaf) { [void](Copy-OneFile $script:ClaudeStateFile (Join-Path $temporary 'claude.json')) }
        if ($IncludeAuth) {
            Write-Host 'Авторизация: включена' -ForegroundColor Yellow
            [void](Copy-OneFile (Join-Path $script:ClaudeHome '.credentials.json') (Join-Path $temporary 'claude\.credentials.json'))
            [void](Copy-OneFile (Join-Path $script:CodexHome 'auth.json') (Join-Path $temporary 'codex\auth.json'))
        }
        Copy-SqliteState $temporary -Everything:$Full

        $info = @(
            'Verified backup данных Claude Code и Codex'
            "Создан UTC:     $([DateTime]::UtcNow.ToString('o'))"
            "Режим:          $(if ($Full) { 'full' } else { 'essential' })"
            "Авторизация:    $($IncludeAuth.IsPresent)"
            'Проверка:       manifest.json + SHA-256'
            ''
            'Импорт проверяет весь пакет до записи. Не редактируйте файлы внутри bundle.'
        ) -join "`r`n"
        [System.IO.File]::WriteAllText((Join-Path $temporary 'BACKUP_INFO.txt'), $info, $script:Utf8NoBom)
        $manifest = Write-Manifest $temporary $Full.IsPresent $IncludeAuth.IsPresent
        [void](Read-AndVerifyManifest $temporary)
        Publish-AtomicBundle $temporary $bundlePath
        $temporary = $null
        Write-Host "Готово: $bundlePath ($(@($manifest.files).Count) файлов)" -ForegroundColor Green
    } finally {
        if ($temporary -and (Test-Path -LiteralPath $temporary)) { Remove-Item -LiteralPath $temporary -Recurse -Force }
    }
}
elseif ($Mode -eq 'Merge') {
    Write-Host "Объединение памяти Claude <- $bundlePath" -ForegroundColor Cyan
    $manifest = Read-AndVerifyManifest $bundlePath -LegacyAllowed:$AllowLegacy
    Invoke-ClaudeMemoryMerge $bundlePath $manifest
    if ($DryRun) { Write-Host 'Dry run: файлы не изменены.' -ForegroundColor Green }
}
else {
    Write-Host "Импорт <- $bundlePath" -ForegroundColor Cyan
    $manifest = Read-AndVerifyManifest $bundlePath -LegacyAllowed:$AllowLegacy
    $incomingConfig = Join-Path $bundlePath 'codex\config.toml'
    if (Test-Path -LiteralPath $incomingConfig -PathType Leaf) {
        $script:CodexSqliteHome = Read-CodexSqliteHome $script:CodexHome $incomingConfig
        Assert-BundleOutsideProfiles $bundlePath
        Write-Host "Codex SQLite после импорта: $script:CodexSqliteHome"
    }
    Test-ForeignPaths $manifest
    $selected = @($manifest.files | Where-Object {
        $category = [string]$_.category
        ($category -eq 'essential') -or ($category -eq 'full' -and $Full) -or ($category -eq 'auth' -and $IncludeAuth)
    })
    if (-not $selected.Count) { throw 'После применения параметров не осталось файлов для импорта.' }
    Write-Host ("Режим: {0}; авторизация: {1}; файлов: {2}" -f $(if ($Full) { 'full' } else { 'essential' }), $IncludeAuth.IsPresent, $selected.Count)
    if (-not $DryRun -and -not $Yes) {
        $answer = Read-Host 'Продолжить импорт совпадающих файлов? (y/N)'
        if ($answer -notmatch '^[yYдД]') { Write-Host 'Отменено.'; exit 0 }
    }
    Copy-ManifestEntries $bundlePath $selected
    if ($DryRun) { Write-Host 'Dry run: файлы не изменены.' -ForegroundColor Green }
    else { Write-Host 'Готово. Перезапусти Claude Code и Codex.' -ForegroundColor Green }
}

exit 0
