param(
  [string]$SourceXml = '',
  [string]$PolicyDir = '',
  [string]$BackupDir = '',
  [string]$BackupLabel = '',
  [switch]$StripSuggested,
  [switch]$AllowUnsupportedPolicyEdition
)

$ErrorActionPreference = 'Stop'
. "$PSScriptRoot\Common.ps1"

Assert-GuardAdministrator
Assert-DefaultAssociationsPolicyEdition -AllowUnsupported:$AllowUnsupportedPolicyEdition

if (-not $SourceXml) { throw 'SourceXml is empty.' }
if (-not $PolicyDir) { throw 'PolicyDir is empty.' }
if (-not $BackupDir) { throw 'BackupDir is empty.' }

Assert-AssociationXml -Path $SourceXml
New-GuardDirectory -Path $PolicyDir
New-GuardDirectory -Path $BackupDir

$policyXml = Get-PolicyXmlPath -PolicyDir $PolicyDir
$beforeExport = Join-Path $BackupDir ('BeforeApply_current_user_' + (Get-GuardStamp) + (Get-GuardBackupLabelSuffix -Label $BackupLabel) + '.xml')
Export-CurrentAssociations -Path $beforeExport
Write-BackupLabelSidecar -BackupPath $beforeExport -Label $BackupLabel -Kind 'before_apply_current_user'

Backup-FileIfExists -Path $policyXml -BackupDir $BackupDir -Prefix 'PreviousPolicyXml' -Label $BackupLabel -Kind 'previous_policy_xml' | Out-Null
Copy-Item -LiteralPath $SourceXml -Destination $policyXml -Force
if ($StripSuggested) {
  Remove-SuggestedAttributes -Path $policyXml
}
Assert-AssociationXml -Path $policyXml

$regPath = Get-PolicyRegistryPath
New-Item -Path $regPath -Force | Out-Null
Set-ItemProperty -Path $regPath -Name DefaultAssociationsConfiguration -Type String -Value $policyXml
Invoke-GpUpdate

Write-Host ''
Write-Host '=== Default app policy applied ==='
Write-Host "Registry: $regPath"
Write-Host "Value: DefaultAssociationsConfiguration = $policyXml"
Write-FileSummary -Path $policyXml
Write-Host ''
Write-Host 'Sign out/sign in or reboot is required before Windows reapplies the policy.'
