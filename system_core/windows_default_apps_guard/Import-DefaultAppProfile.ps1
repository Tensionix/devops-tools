param(
  [string]$SourceXml = '',
  [string]$ProfileXml = '',
  [string]$BackupDir = '',
  [switch]$StripSuggested
)

$ErrorActionPreference = 'Stop'
. "$PSScriptRoot\Common.ps1"

if (-not $SourceXml) { throw 'SourceXml is empty.' }
if (-not $ProfileXml) { throw 'ProfileXml is empty.' }
if (-not $BackupDir) { throw 'BackupDir is empty.' }

Assert-AssociationXml -Path $SourceXml
New-GuardDirectory -Path (Split-Path -Parent $ProfileXml)
New-GuardDirectory -Path $BackupDir

Backup-FileIfExists -Path $ProfileXml -BackupDir $BackupDir -Prefix 'PreviousProfileXml' | Out-Null
Copy-Item -LiteralPath $SourceXml -Destination $ProfileXml -Force
if ($StripSuggested) {
  Remove-SuggestedAttributes -Path $ProfileXml
}
Assert-AssociationXml -Path $ProfileXml

Write-Host ''
Write-Host '=== Default app profile imported ==='
Write-Host "Source: $SourceXml"
Write-FileSummary -Path $ProfileXml
