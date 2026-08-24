Set-StrictMode -Version 2.0

function New-GuardDirectory {
  param([Parameter(Mandatory = $true)][string]$Path)
  if (-not (Test-Path -LiteralPath $Path)) {
    New-Item -ItemType Directory -Force -Path $Path | Out-Null
  }
}

function Get-GuardStamp {
  Get-Date -Format 'yyyy-MM-dd_HH-mm-ss'
}

function Get-GuardBackupLabelSuffix {
  param([string]$Label = '')
  $text = ([string]$Label).Trim()
  if (-not $text) {
    return ''
  }
  $text = $text -replace '[\\/:*?"<>|]+', '_'
  $text = $text -replace '\s+', '_'
  $text = $text.Trim(' ', '.', '_', '-')
  if ($text.Length -gt 80) {
    $text = $text.Substring(0, 80).Trim(' ', '.', '_', '-')
  }
  if (-not $text) {
    return ''
  }
  return "_$text"
}

function Write-BackupLabelSidecar {
  param(
    [Parameter(Mandatory = $true)][string]$BackupPath,
    [string]$Label = '',
    [string]$Kind = ''
  )
  $text = ([string]$Label).Trim()
  if (-not $text) {
    return
  }
  $notePath = "$BackupPath.note.txt"
  $lines = @(
    "Label: $text",
    "Kind: $Kind",
    "Backup: $BackupPath",
    "Created: $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')"
  )
  $lines | Out-File -LiteralPath $notePath -Encoding utf8
  Write-Host "Backup note: $notePath"
}

function Test-GuardAdministrator {
  try {
    $identity = [Security.Principal.WindowsIdentity]::GetCurrent()
    $principal = [Security.Principal.WindowsPrincipal]::new($identity)
    return $principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
  } catch {
    return $false
  }
}

function Assert-GuardAdministrator {
  if (-not (Test-GuardAdministrator)) {
    throw 'Administrator rights are required. Start launcher_gui.cmd normally, or rerun this action through the GUI UAC layer.'
  }
}

function Get-GuardWindowsEdition {
  try {
    $cv = Get-ItemProperty -Path 'HKLM:\SOFTWARE\Microsoft\Windows NT\CurrentVersion' -ErrorAction Stop
    $productName = [string]$cv.ProductName
    try {
      $os = Get-CimInstance -ClassName Win32_OperatingSystem -ErrorAction Stop
      if ($os.Caption) {
        $productName = [string]$os.Caption
      }
    } catch { }
    return [pscustomobject]@{
      ProductName = $productName
      EditionID = [string]$cv.EditionID
      DisplayVersion = [string]$cv.DisplayVersion
      CurrentBuild = [string]$cv.CurrentBuild
    }
  } catch {
    return [pscustomobject]@{
      ProductName = ''
      EditionID = ''
      DisplayVersion = ''
      CurrentBuild = ''
    }
  }
}

function Test-DefaultAssociationsPolicyEdition {
  $edition = (Get-GuardWindowsEdition).EditionID
  if (-not $edition) {
    return $false
  }
  foreach ($pattern in @('Professional*', 'Enterprise*', 'Education*', 'IoTEnterprise*')) {
    if ($edition -like $pattern) {
      return $true
    }
  }
  return $false
}

function Write-DefaultAssociationsPolicyEdition {
  $edition = Get-GuardWindowsEdition
  $supported = Test-DefaultAssociationsPolicyEdition
  Write-Host "Windows product: $($edition.ProductName)"
  Write-Host "EditionID: $($edition.EditionID)"
  Write-Host "DisplayVersion: $($edition.DisplayVersion)"
  Write-Host "Build: $($edition.CurrentBuild)"
  if ($supported) {
    Write-Host 'DefaultAssociationsConfiguration policy: supported edition according to Microsoft docs'
  } else {
    Write-Host 'DefaultAssociationsConfiguration policy: not documented for this edition; Windows Home/Core should use fallback behavior'
  }
}

function Assert-DefaultAssociationsPolicyEdition {
  param([switch]$AllowUnsupported)
  if (Test-DefaultAssociationsPolicyEdition) {
    return
  }
  if ($AllowUnsupported) {
    Write-Host 'WARNING: This Windows edition is not documented for DefaultAssociationsConfiguration policy. Trying anyway because AllowUnsupported was set.'
    return
  }
  $edition = Get-GuardWindowsEdition
  throw "DefaultAssociationsConfiguration policy is not documented for this Windows edition: ProductName='$($edition.ProductName)', EditionID='$($edition.EditionID)'. On Windows Home/Core, use Status/Snapshot/Rescan only, or enable Allow unsupported edition if you intentionally want to test the registry policy path."
}

function Get-PolicyRegistryPath {
  'HKLM:\SOFTWARE\Policies\Microsoft\Windows\System'
}

function Get-PolicyXmlPath {
  param([Parameter(Mandatory = $true)][string]$PolicyDir)
  Join-Path $PolicyDir 'AppAssociations.xml'
}

function Assert-AssociationXml {
  param([Parameter(Mandatory = $true)][string]$Path)
  if (-not (Test-Path -LiteralPath $Path)) {
    throw "Association XML was not found: $Path"
  }
  try {
    [xml](Get-Content -LiteralPath $Path -Raw -Encoding UTF8) | Out-Null
  } catch {
    throw "Association XML is not valid XML: $Path :: $($_.Exception.Message)"
  }
}

function Save-XmlUtf8NoBom {
  param(
    [Parameter(Mandatory = $true)][xml]$Xml,
    [Parameter(Mandatory = $true)][string]$Path
  )
  $settings = [System.Xml.XmlWriterSettings]::new()
  $settings.Encoding = [System.Text.UTF8Encoding]::new($false)
  $settings.Indent = $true
  $settings.OmitXmlDeclaration = $false
  $writer = [System.Xml.XmlWriter]::Create($Path, $settings)
  try {
    $Xml.Save($writer)
  } finally {
    $writer.Dispose()
  }
}

function Remove-SuggestedAttributes {
  param([Parameter(Mandatory = $true)][string]$Path)
  Assert-AssociationXml -Path $Path
  [xml]$xml = Get-Content -LiteralPath $Path -Raw -Encoding UTF8
  $removed = 0
  foreach ($association in @($xml.DefaultAssociations.Association)) {
    if ($association.HasAttribute('Suggested')) {
      $association.RemoveAttribute('Suggested')
      $removed++
    }
  }
  if ($removed -gt 0) {
    Save-XmlUtf8NoBom -Xml $xml -Path $Path
  }
  Write-Host "Suggested attributes removed: $removed"
}

function Backup-FileIfExists {
  param(
    [Parameter(Mandatory = $true)][string]$Path,
    [Parameter(Mandatory = $true)][string]$BackupDir,
    [Parameter(Mandatory = $true)][string]$Prefix,
    [string]$Label = '',
    [string]$Kind = ''
  )
  if (-not (Test-Path -LiteralPath $Path)) {
    return $null
  }
  New-GuardDirectory -Path $BackupDir
  $name = '{0}_{1}{2}{3}' -f $Prefix, (Get-GuardStamp), (Get-GuardBackupLabelSuffix -Label $Label), ([System.IO.Path]::GetExtension($Path))
  $target = Join-Path $BackupDir $name
  Copy-Item -LiteralPath $Path -Destination $target -Force
  Write-Host "Backup: $target"
  Write-BackupLabelSidecar -BackupPath $target -Label $Label -Kind $Kind
  return $target
}

function Export-CurrentAssociations {
  param([Parameter(Mandatory = $true)][string]$Path)
  $dir = Split-Path -Parent $Path
  New-GuardDirectory -Path $dir
  Write-Host "Exporting current default app associations:"
  Write-Host "  $Path"
  & dism.exe /Online "/Export-DefaultAppAssociations:$Path"
  $code = if ($global:LASTEXITCODE -is [int]) { $global:LASTEXITCODE } else { 0 }
  if ($code -ne 0) {
    throw "DISM export failed with exit code $code."
  }
  Assert-AssociationXml -Path $Path
}

function Invoke-GpUpdate {
  Write-Host 'Running gpupdate /force...'
  & gpupdate.exe /force
  $code = if ($global:LASTEXITCODE -is [int]) { $global:LASTEXITCODE } else { 0 }
  if ($code -ne 0) {
    throw "gpupdate failed with exit code $code."
  }
}

function Write-FileSummary {
  param([Parameter(Mandatory = $true)][string]$Path)
  if (-not (Test-Path -LiteralPath $Path)) {
    Write-Host "Missing: $Path"
    return
  }
  $item = Get-Item -LiteralPath $Path
  $hash = Get-FileHash -LiteralPath $Path -Algorithm SHA256
  Write-Host "File: $Path"
  Write-Host "  Size: $($item.Length) bytes"
  Write-Host "  Modified: $($item.LastWriteTime.ToString('yyyy-MM-dd HH:mm:ss'))"
  Write-Host "  SHA256: $($hash.Hash)"
}

function Get-PolicyValue {
  $regPath = Get-PolicyRegistryPath
  try {
    $props = Get-ItemProperty -Path $regPath -Name DefaultAssociationsConfiguration -ErrorAction Stop
    return [string]$props.DefaultAssociationsConfiguration
  } catch {
    return ''
  }
}

function Get-AssociationFromXml {
  param(
    [Parameter(Mandatory = $true)][string]$Path,
    [Parameter(Mandatory = $true)][string]$Identifier
  )
  if (-not (Test-Path -LiteralPath $Path)) {
    return $null
  }
  try {
    [xml]$xml = Get-Content -LiteralPath $Path -Raw -Encoding UTF8
    $items = @($xml.DefaultAssociations.Association | Where-Object { $_.Identifier -ieq $Identifier })
    if ($items.Count -eq 0) {
      return $null
    }
    return $items[0]
  } catch {
    return $null
  }
}

function Format-AssociationSummary {
  param([AllowNull()]$Association)
  if ($null -eq $Association) {
    return '-'
  }
  $parts = @()
  if ($Association.ProgId) { $parts += [string]$Association.ProgId }
  if ($Association.ApplicationName) { $parts += ('[' + [string]$Association.ApplicationName + ']') }
  if ($Association.Suggested) { $parts += ('Suggested=' + [string]$Association.Suggested) }
  if ($parts.Count -eq 0) {
    return '-'
  }
  return ($parts -join ' ')
}

function Get-UserChoiceSummary {
  param([Parameter(Mandatory = $true)][string]$Identifier)
  if ($Identifier.StartsWith('.')) {
    $path = "HKCU:\Software\Microsoft\Windows\CurrentVersion\Explorer\FileExts\$Identifier\UserChoice"
  } else {
    $path = "HKCU:\Software\Microsoft\Windows\Shell\Associations\UrlAssociations\$Identifier\UserChoice"
  }
  try {
    $props = Get-ItemProperty -Path $path -ErrorAction Stop
    if ($props.ProgId) {
      return [string]$props.ProgId
    }
    return '(UserChoice without ProgId)'
  } catch {
    return '-'
  }
}
