$ErrorActionPreference = 'Continue'
$OutputEncoding = [System.Text.UTF8Encoding]::new($false)
try { [Console]::OutputEncoding = $OutputEncoding } catch { }

function Write-Flag([string]$Name, [string]$State, [string]$Detail) {
  "{0,-28} {1,-7} {2}" -f $Name, $State, $Detail | Write-Host
}

Write-Host "=== Audion DevOps preflight ==="
$admin = $false
try {
  $identity = [Security.Principal.WindowsIdentity]::GetCurrent()
  $principal = [Security.Principal.WindowsPrincipal]::new($identity)
  $admin = $principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
} catch { }
Write-Flag "Admin/elevated" ($(if ($admin) { "OK" } else { "WARN" })) ($(if ($admin) { "running as Administrator" } else { "not elevated; UAC may be required" }))
Write-Flag "PowerShell" "OK" ("{0} {1}" -f $PSVersionTable.PSEdition, $PSVersionTable.PSVersion)

Write-Host ""
Write-Host "=== Windows virtualization / WSL ==="
try {
  $cpu = Get-CimInstance Win32_Processor -ErrorAction Stop | Select-Object -First 1
  $virt = [bool]$cpu.VirtualizationFirmwareEnabled
  Write-Flag "Firmware virtualization" ($(if ($virt) { "OK" } else { "WARN" })) ("SLAT={0}; VMMonitor={1}" -f $cpu.SecondLevelAddressTranslationExtensions, $cpu.VMMonitorModeExtensions)
} catch {
  Write-Flag "Firmware virtualization" "WARN" $_.Exception.Message
}
try {
  $cs = Get-CimInstance Win32_ComputerSystem -ErrorAction Stop
  Write-Flag "Hypervisor present" ($(if ($cs.HypervisorPresent) { "OK" } else { "INFO" })) ("HypervisorPresent={0}" -f $cs.HypervisorPresent)
} catch {
  Write-Flag "Hypervisor present" "WARN" $_.Exception.Message
}
foreach ($feature in @("Microsoft-Windows-Subsystem-Linux", "VirtualMachinePlatform", "Microsoft-Hyper-V-All")) {
  try {
    $item = Get-WindowsOptionalFeature -Online -FeatureName $feature -ErrorAction Stop
    Write-Flag $feature ($(if ($item.State -eq "Enabled") { "OK" } else { "WARN" })) $item.State
  } catch {
    Write-Flag $feature "WARN" $_.Exception.Message
  }
}
if (Get-Command wsl.exe -ErrorAction SilentlyContinue) {
  & wsl.exe --status *> $null
  $wslExit = $LASTEXITCODE
  Write-Flag "WSL status" ($(if ($wslExit -eq 0) { "OK" } else { "WARN" })) ("exit={0}" -f $wslExit)
} else {
  Write-Flag "WSL status" "WARN" "wsl.exe not found"
}

Write-Host ""
Write-Host "=== Network ==="
try {
  $adapters = @(Get-NetAdapter -ErrorAction Stop)
  $up = @($adapters | Where-Object Status -eq "Up").Count
  Write-Flag "Network adapters" ($(if ($up -gt 0) { "OK" } else { "WARN" })) ("total={0}; up={1}" -f $adapters.Count, $up)
  $adapters | Select-Object -First 8 Name, Status, LinkSpeed, MacAddress | Format-Table -AutoSize | Out-String -Width 180 | Write-Host
} catch {
  Write-Flag "Network adapters" "WARN" $_.Exception.Message
}
try {
  $profiles = netsh.exe wlan show profiles 2>&1
  $profileCount = @($profiles | Select-String -Pattern "All User Profile|Профиль всех пользователей|Все профили пользователей").Count
  Write-Flag "Wi-Fi profiles" ($(if ($profileCount -gt 0) { "OK" } else { "INFO" })) ("count={0}" -f $profileCount)
} catch {
  Write-Flag "Wi-Fi profiles" "WARN" $_.Exception.Message
}

Write-Host ""
Write-Host "=== Disk risk flags ==="
try {
  $low = @()
  Get-CimInstance Win32_LogicalDisk -Filter "DriveType=3" -ErrorAction Stop | ForEach-Object {
    $freeGiB = [math]::Round($_.FreeSpace / 1GB, 1)
    $sizeGiB = [math]::Round($_.Size / 1GB, 1)
    $freePct = if ($_.Size) { [math]::Round(($_.FreeSpace / $_.Size) * 100, 1) } else { 0 }
    if ($freeGiB -lt 20 -or $freePct -lt 10) {
      $low += ("{0} free={1}GiB/{2}%" -f $_.DeviceID, $freeGiB, $freePct)
    }
    "{0,-6} free={1,8}GiB size={2,8}GiB free%={3,5}" -f $_.DeviceID, $freeGiB, $sizeGiB, $freePct | Write-Host
  }
  Write-Flag "Free space risk" ($(if ($low.Count -gt 0) { "WARN" } else { "OK" })) ($(if ($low.Count -gt 0) { $low -join "; " } else { "no low-space fixed drives" }))
} catch {
  Write-Flag "Free space risk" "WARN" $_.Exception.Message
}
try {
  $risks = @()
  Get-Disk -ErrorAction Stop | ForEach-Object {
    if ($_.PartitionStyle -eq "RAW" -or $_.OperationalStatus -ne "Online" -or $_.IsReadOnly -or $_.IsOffline) {
      $risks += ("Disk {0}: style={1}; status={2}; offline={3}; readonly={4}" -f $_.Number, $_.PartitionStyle, ($_.OperationalStatus -join ","), $_.IsOffline, $_.IsReadOnly)
    }
  }
  Write-Flag "Disk layout risk" ($(if ($risks.Count -gt 0) { "WARN" } else { "OK" })) ($(if ($risks.Count -gt 0) { $risks -join "; " } else { "no RAW/offline/readonly disks" }))
} catch {
  Write-Flag "Disk layout risk" "WARN" $_.Exception.Message
}

exit 0
