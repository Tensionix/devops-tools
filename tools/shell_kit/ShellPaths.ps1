# Where the shell keeps what you configured.
#
# Nothing here is hard-coded to a profile folder. Documents can be redirected —
# on this machine it is `C:\Audion\Documents`, not the usual place — and Windows
# Terminal exists in three flavours that keep settings in three different
# folders. So each item is found the way the program itself would find it, and
# every item carries a stable id: on the new machine the file goes where that id
# resolves there, not where it happened to live here.

function Get-ShellEnvironmentItems {
  $items = @()
  $documents = [Environment]::GetFolderPath("MyDocuments")

  # PowerShell 7 profiles. $PROFILE knows the real path, redirection included.
  $items += [pscustomobject]@{
    Id    = "pwsh_profile_all_hosts"
    Title = "PowerShell 7 profile (all hosts)"
    Path  = $PROFILE.CurrentUserAllHosts
    Kind  = "profile"
  }
  $items += [pscustomobject]@{
    Id    = "pwsh_profile_console"
    Title = "PowerShell 7 profile (console host)"
    Path  = $PROFILE.CurrentUserCurrentHost
    Kind  = "profile"
  }

  # Windows PowerShell 5.1 keeps its own pair beside the 7.x one.
  $items += [pscustomobject]@{
    Id    = "winps_profile_all_hosts"
    Title = "Windows PowerShell profile (all hosts)"
    Path  = Join-Path $documents "WindowsPowerShell\profile.ps1"
    Kind  = "profile"
  }
  $items += [pscustomobject]@{
    Id    = "winps_profile_console"
    Title = "Windows PowerShell profile (console host)"
    Path  = Join-Path $documents "WindowsPowerShell\Microsoft.PowerShell_profile.ps1"
    Kind  = "profile"
  }

  # Windows Terminal: Store build, Preview build, and the unpackaged one.
  $items += [pscustomobject]@{
    Id    = "terminal_store"
    Title = "Windows Terminal settings (Store)"
    Path  = Join-Path $env:LOCALAPPDATA "Packages\Microsoft.WindowsTerminal_8wekyb3d8bbwe\LocalState\settings.json"
    Kind  = "terminal"
  }
  $items += [pscustomobject]@{
    Id    = "terminal_preview"
    Title = "Windows Terminal settings (Preview)"
    Path  = Join-Path $env:LOCALAPPDATA "Packages\Microsoft.WindowsTerminalPreview_8wekyb3d8bbwe\LocalState\settings.json"
    Kind  = "terminal"
  }
  $items += [pscustomobject]@{
    Id    = "terminal_unpackaged"
    Title = "Windows Terminal settings (unpackaged)"
    Path  = Join-Path $env:LOCALAPPDATA "Microsoft\Windows Terminal\settings.json"
    Kind  = "terminal"
  }

  foreach ($item in $items) {
    $item | Add-Member -NotePropertyName Exists -NotePropertyValue (Test-Path -LiteralPath $item.Path) -Force
    $item
  }
}
