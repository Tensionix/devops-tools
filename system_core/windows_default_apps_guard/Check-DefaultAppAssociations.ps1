param(
  [string]$PolicyDir = '',
  [string]$ProfileXml = '',
  [string]$BackupDir = '',
  [string[]]$Identifiers = @(),
  [switch]$IncludeDismInventory
)

$ErrorActionPreference = 'Continue'
. "$PSScriptRoot\Common.ps1"

if (-not $PolicyDir) { throw 'PolicyDir is empty.' }
if (-not $BackupDir) { throw 'BackupDir is empty.' }

$policyXml = Get-PolicyXmlPath -PolicyDir $PolicyDir
$policyValue = Get-PolicyValue
$defaultIdentifiers = @('http', 'https', '.pdf', '.jpg', '.jpeg', '.png', '.webp', '.gif', '.mp4', '.mkv', '.mp3', '.flac', '.wav')
if (-not $Identifiers -or $Identifiers.Count -eq 0) {
  $Identifiers = $defaultIdentifiers
}
$normalizedIdentifiers = New-Object System.Collections.Generic.List[string]
foreach ($rawIdentifier in $Identifiers) {
  foreach ($part in ([regex]::Split([string]$rawIdentifier, '[,;\s]+'))) {
    $item = $part.Trim()
    if ($item -and -not $normalizedIdentifiers.Contains($item)) {
      [void]$normalizedIdentifiers.Add($item)
    }
  }
}
if ($normalizedIdentifiers.Count -eq 0) {
  foreach ($item in $defaultIdentifiers) {
    [void]$normalizedIdentifiers.Add($item)
  }
}
$Identifiers = $normalizedIdentifiers.ToArray()

Write-Host '=== Default Apps Guard status ==='
$isAdmin = $false
try {
  $identity = [Security.Principal.WindowsIdentity]::GetCurrent()
  $principal = [Security.Principal.WindowsPrincipal]::new($identity)
  $isAdmin = $principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
} catch { }
Write-Host "Administrator: $isAdmin"
Write-Host "Policy dir: $PolicyDir"
Write-Host "Backup dir: $BackupDir"
Write-Host "Profile XML: $ProfileXml"
Write-Host ''

Write-Host '=== Windows edition ==='
Write-DefaultAssociationsPolicyEdition
Write-Host ''

Write-Host '=== HKLM policy ==='
Write-Host ('Registry path: ' + (Get-PolicyRegistryPath))
if ($policyValue) {
  Write-Host "DefaultAssociationsConfiguration: $policyValue"
} else {
  Write-Host 'DefaultAssociationsConfiguration: not set'
}
Write-Host ''

Write-Host '=== Active policy XML ==='
Write-FileSummary -Path $policyXml
Write-Host ''

Write-Host '=== Profile XML ==='
if ($ProfileXml) {
  Write-FileSummary -Path $ProfileXml
} else {
  Write-Host 'Profile XML path is empty.'
}
Write-Host ''

Write-Host '=== Policy XML associations ==='
if (Test-Path -LiteralPath $policyXml) {
  try {
    [xml]$xml = Get-Content -LiteralPath $policyXml -Raw -Encoding UTF8
    foreach ($id in $Identifiers) {
      $items = @($xml.DefaultAssociations.Association | Where-Object { $_.Identifier -ieq $id })
      if ($items.Count -eq 0) {
        Write-Host "$id -> missing in policy XML"
      } else {
        foreach ($item in $items) {
          $suggested = if ($item.Suggested) { " Suggested=$($item.Suggested)" } else { '' }
          Write-Host "$id -> ProgId=$($item.ProgId) App=$($item.ApplicationName)$suggested"
        }
      }
    }
  } catch {
    Write-Host ('Could not parse policy XML: ' + $_.Exception.Message)
  }
} else {
  Write-Host 'Active policy XML does not exist.'
}
Write-Host ''

Write-Host '=== Tracked associations compare ==='
foreach ($id in $Identifiers) {
  $current = Get-UserChoiceSummary -Identifier $id
  $profile = Format-AssociationSummary -Association (Get-AssociationFromXml -Path $ProfileXml -Identifier $id)
  $policy = Format-AssociationSummary -Association (Get-AssociationFromXml -Path $policyXml -Identifier $id)
  Write-Host "$id"
  Write-Host "  Current user: $current"
  Write-Host "  Profile XML : $profile"
  Write-Host "  Policy XML  : $policy"
}
Write-Host ''

Write-Host '=== Current user UserChoice ==='
foreach ($id in $Identifiers) {
  if ($id.StartsWith('.')) {
    $path = "HKCU:\Software\Microsoft\Windows\CurrentVersion\Explorer\FileExts\$id\UserChoice"
  } else {
    $path = "HKCU:\Software\Microsoft\Windows\Shell\Associations\UrlAssociations\$id\UserChoice"
  }
  try {
    $props = Get-ItemProperty -Path $path -ErrorAction Stop
    $hashText = if ($props.PSObject.Properties.Name -contains 'Hash') { $props.Hash } else { '' }
    Write-Host "$id -> ProgId=$($props.ProgId) Hash=$hashText"
  } catch {
    Write-Host "$id -> no UserChoice"
  }
}
Write-Host ''

Write-Host '=== DISM default associations inventory ==='
if ($IncludeDismInventory) {
  try {
    & dism.exe /Online /Get-DefaultAppAssociations
  } catch {
    Write-Host ('DISM inventory failed: ' + $_.Exception.Message)
  }
} else {
  Write-Host 'Skipped. Enable "DISM inventory" for the full Windows default-associations list.'
}
Write-Host ''

Write-Host '=== UCPD guard hint ==='
try {
  $ucpd = Get-ItemProperty -Path 'HKLM:\SYSTEM\CurrentControlSet\Services\UCPD' -ErrorAction Stop
  Write-Host "UCPD service Start: $($ucpd.Start)"
} catch {
  Write-Host 'UCPD service: not found'
}
try {
  $task = Get-ScheduledTask -TaskPath '\Microsoft\Windows\AppxDeploymentClient\' -TaskName 'UCPD velocity' -ErrorAction Stop
  Write-Host "UCPD velocity task: $($task.State)"
} catch {
  Write-Host 'UCPD velocity task: not found'
}
