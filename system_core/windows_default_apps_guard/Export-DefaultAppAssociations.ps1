param(
  [string]$ProfileXml = '',
  [string]$BackupDir = '',
  [string]$BackupLabel = '',
  [switch]$StripSuggested,
  [switch]$BackupOnly
)

$ErrorActionPreference = 'Stop'
. "$PSScriptRoot\Common.ps1"

if (-not $BackupDir) { throw 'BackupDir is empty.' }
if (-not $BackupOnly -and -not $ProfileXml) { throw 'ProfileXml is empty.' }

New-GuardDirectory -Path $BackupDir
if (-not $BackupOnly) {
  New-GuardDirectory -Path (Split-Path -Parent $ProfileXml)
}

$stamp = Get-GuardStamp
$labelSuffix = Get-GuardBackupLabelSuffix -Label $BackupLabel
$backupXml = Join-Path $BackupDir "AppAssociations_export_$stamp$labelSuffix.xml"

Export-CurrentAssociations -Path $backupXml
Write-BackupLabelSidecar -BackupPath $backupXml -Label $BackupLabel -Kind ($(if ($BackupOnly) { 'snapshot_current' } else { 'export_profile_reference' }))

if (-not $BackupOnly) {
  Copy-Item -LiteralPath $backupXml -Destination $ProfileXml -Force
  if ($StripSuggested) {
    Remove-SuggestedAttributes -Path $ProfileXml
  }
}

Write-Host ''
if ($BackupOnly) {
  Write-Host '=== Snapshot complete ==='
  Write-FileSummary -Path $backupXml
  Write-Host 'Profile XML was not overwritten.'
} else {
  Write-Host '=== Export complete ==='
  Write-FileSummary -Path $ProfileXml
}
Write-Host "Timestamp backup: $backupXml"
