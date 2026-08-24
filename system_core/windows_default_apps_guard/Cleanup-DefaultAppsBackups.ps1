param(
  [string]$BackupDir = '',
  [int]$RetentionDays = 30,
  [switch]$DryRun
)

$ErrorActionPreference = 'Stop'
. "$PSScriptRoot\Common.ps1"

if (-not $BackupDir) { throw 'BackupDir is empty.' }
if ($RetentionDays -lt 1) { throw 'RetentionDays must be 1 or greater.' }

Write-Host '=== Default Apps Guard backup cleanup ==='
Write-Host "Backup dir: $BackupDir"
Write-Host "Retention days: $RetentionDays"
Write-Host "Dry run: $DryRun"
Write-Host 'Cleanup rule: remove only unlabeled timestamp backups; named backups and .note.txt files are kept.'

if (-not (Test-Path -LiteralPath $BackupDir)) {
  Write-Host 'Backup folder does not exist.'
  exit 0
}

function Test-UnlabeledTimestampBackup {
  param([Parameter(Mandatory = $true)][System.IO.FileInfo]$File)
  if ($File.Name.EndsWith('.note.txt', [System.StringComparison]::OrdinalIgnoreCase)) {
    return $false
  }
  $patterns = @(
    '^AppAssociations_export_\d{4}-\d{2}-\d{2}_\d{2}-\d{2}-\d{2}\.xml$',
    '^BeforeApply_current_user_\d{4}-\d{2}-\d{2}_\d{2}-\d{2}-\d{2}\.xml$',
    '^PreviousPolicyXml_\d{4}-\d{2}-\d{2}_\d{2}-\d{2}-\d{2}\.xml$',
    '^PreviousProfileXml_\d{4}-\d{2}-\d{2}_\d{2}-\d{2}-\d{2}\.xml$',
    '^RemovedPolicyXml_\d{4}-\d{2}-\d{2}_\d{2}-\d{2}-\d{2}\.xml$',
    '^RemovedPolicyRegistryValue_\d{4}-\d{2}-\d{2}_\d{2}-\d{2}-\d{2}\.txt$'
  )
  foreach ($pattern in $patterns) {
    if ($File.Name -match $pattern) {
      return $true
    }
  }
  return $false
}

$cutoff = (Get-Date).AddDays(-$RetentionDays)
$oldFiles = @(
  Get-ChildItem -LiteralPath $BackupDir -File -ErrorAction Stop |
    Where-Object { $_.LastWriteTime -lt $cutoff }
)

$files = @($oldFiles | Where-Object { Test-UnlabeledTimestampBackup -File $_ })
$kept = @($oldFiles | Where-Object { -not (Test-UnlabeledTimestampBackup -File $_) })

if ($files.Count -eq 0) {
  Write-Host 'No old unlabeled timestamp backup files found.'
  if ($kept.Count -gt 0) {
    Write-Host "Old files kept because they are named/manual/note files: $($kept.Count)"
  }
  exit 0
}

foreach ($file in $files) {
  if ($DryRun) {
    Write-Host "[DRY] $($file.FullName)"
  } else {
    Write-Host "Removing: $($file.FullName)"
    Remove-Item -LiteralPath $file.FullName -Force
  }
}

Write-Host ''
Write-Host "Old unlabeled timestamp backup files matched: $($files.Count)"
Write-Host "Old named/manual/note files kept: $($kept.Count)"
if ($DryRun) {
  Write-Host 'Dry run only. Disable dry run to delete these files.'
}
