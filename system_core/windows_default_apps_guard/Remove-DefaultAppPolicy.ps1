param(
  [string]$PolicyDir = '',
  [string]$BackupDir = '',
  [string]$BackupLabel = '',
  [switch]$RemovePolicyXml
)

$ErrorActionPreference = 'Stop'
. "$PSScriptRoot\Common.ps1"

Assert-GuardAdministrator

if (-not $PolicyDir) { throw 'PolicyDir is empty.' }
if (-not $BackupDir) { throw 'BackupDir is empty.' }

New-GuardDirectory -Path $BackupDir
$regPath = Get-PolicyRegistryPath
$policyXml = Get-PolicyXmlPath -PolicyDir $PolicyDir
$currentValue = Get-PolicyValue

if ($currentValue) {
  $valueBackup = Join-Path $BackupDir ('RemovedPolicyRegistryValue_' + (Get-GuardStamp) + (Get-GuardBackupLabelSuffix -Label $BackupLabel) + '.txt')
  $currentValue | Out-File -LiteralPath $valueBackup -Encoding utf8
  Write-Host "Registry value backup: $valueBackup"
  Write-BackupLabelSidecar -BackupPath $valueBackup -Label $BackupLabel -Kind 'removed_policy_registry_value'
} else {
  Write-Host 'Registry policy value is not set.'
}

Backup-FileIfExists -Path $policyXml -BackupDir $BackupDir -Prefix 'RemovedPolicyXml' -Label $BackupLabel -Kind 'removed_policy_xml' | Out-Null

if (Test-Path -Path $regPath) {
  Remove-ItemProperty -Path $regPath -Name DefaultAssociationsConfiguration -ErrorAction SilentlyContinue
}
if ($RemovePolicyXml -and (Test-Path -LiteralPath $policyXml)) {
  Remove-Item -LiteralPath $policyXml -Force
  Write-Host "Removed inactive policy XML: $policyXml"
}
Invoke-GpUpdate

Write-Host ''
Write-Host '=== Default app policy removed ==='
Write-Host "Registry: $regPath"
Write-Host 'Sign out/sign in or reboot is recommended.'
