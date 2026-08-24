# Audion DevOps Tools - User Guide

Current for `Audion DevOps Tools` as of 2026-06-24.

This is the user-facing guide for the project capabilities. For architecture and development rules, see `docs\AUDION_DEVOPS_TOOLS_RU.md`, `docs\MANIFEST_REFERENCE_RU.md` and `AGENTS.md`.

## What It Is

Audion DevOps Tools is not a Chris Titus WinUtil clone, a generic Windows tuner, or a debloater. It does not try to replace mass-market tools for quick Windows preference changes.

The project targets a different layer: precise DevOps operations across Windows, WSL, virtualization, hardware policy, storage, networking, default-app policy and secrets. Think of it as a fighter-jet cockpit: parameters, backups, explicit risks, confirmations, logs and a single project-local control surface.

## Quick Start

Start the GUI:

```cmd
launcher_gui.cmd
```

The normal launcher requests UAC and runs the whole GUI as Administrator. This is intentional: many project operations need an admin context, including DISM, WSL features, hosts, network adapters, default-app policy, driver policies, WinRE and disk procedures.

Read-only/debug launch without UAC:

```cmd
set AUDION_GUI_NO_ELEVATE=1
launcher_gui.cmd
```

Use a custom Python:

```cmd
set AUDION_GUI_PYTHON=C:\Path\To\python.exe
launcher_gui.cmd
```

The GUI runs a local NiceGUI shell. Default endpoint:

```text
http://127.0.0.1:8092/
```

## Main Rule

Run project operations through project entry points:

- the GUI;
- `launcher_*.cmd`;
- `runtime\python.exe system_core\cli_operation.py <operation_id>`.

This matters most for WSL and system changes. If the goal is to test the project layer, do not bypass it with manual commands.

Direct CLI runs of dangerous operations require an explicit flag:

```cmd
runtime\python.exe system_core\cli_operation.py operation_id --yes-i-understand
```

## Working Folders

Main folders:

```text
config\       manifest, terminal history, GUI settings
system_core\  service layer, GUI, PowerShell modules, WSL assets
tools\        project-local utilities and wrapper kits
profiles\     managed profiles, for example Default Apps Guard XML
backup\       backups of system and user state
output\       reports and exported artifacts
logs\         operation logs
report\       elevated logs and diagnostics
workspace\    tool working folders
```

The project is designed as a portable bundle. Old adjacent folders can be useful as references, but runtime operations should live inside this project tree.

`backup` is a first-class project folder alongside `input`, `output`, `logs`, `report` and `workspace`: it is exposed as `ProjectPaths.backup`, created by the init/preflight layer and opened by the `BACKUP` button in the GUI panel. It is not cache or temporary output; it stores rollback and safety snapshots: network snapshots, `.reg` files, Driver Store exports, browser master/pre-import backups, certificates, SSH material, virtualization and hosts backups.

## Risk And Confirmations

Manifest operations are marked as:

- `safe` - read-only, diagnostics, or writes only inside managed project areas;
- `dangerous` - changes user state, system state, network, disks, policy or secrets.

Additional `risk_level` values describe the blast radius:

- `project_write` - writes inside the project;
- `user_write` - changes the current user;
- `system_change` - changes Windows or system policy;
- `destructive` - can delete data or partitions;
- `secret_export` - exports secrets, such as SSH keys.

The GUI asks for an extra confirmation before dangerous operations. Some external wizard consoles still require typed confirmations. Non-interactive integrated operations should use explicit project flags instead of hidden `Y/YES` prompts.

## Reading The UI

The interface is intentionally hybrid. Command labels, mode names and identifiers often stay English-heavy because they match operation ids, PowerShell/Windows API terms and the operation log. Visible descriptions stay compact so the screen can be scanned quickly. Full explanations, Windows terminology, risks and rollback notes live in tooltips on the button or description.

Logical frames around neighboring commands mark pairs, pipelines or lifecycles:

- `backup / restore`;
- `export / import`;
- `block / unblock`;
- `capture / apply`.

Button tones are soft instrument markers, not warning sirens. Buttons use a very low-opacity tinted fill plus a clearer border so the cue is readable without glowing:

- Section/window entry buttons keep the standard blue Quasar style; only concrete action buttons receive the color accent.
- green/friendly - read-only/status/soft inspection, or the intentional undo side of a paired `block / unblock`, `enable / disable`, `apply / remove` workflow;
- teal/medium - normal working change, import/export/apply/enable/disable when it is not the paired undo action;
- amber/danger - stronger intervention, destructive workflow or sensitive/secret export.

The color accent does not replace `kind`, `risk_level`, confirmations or the terminal log. Dangerous confirmation dialogs keep the full text visible before execution.

## Runtime And Shell

This section checks the basic project and Windows shell environment.

Operations:

- `Preflight snapshot` - one snapshot of elevation, WSL, virtualization, PowerShell, network, Wi-Fi and disk risk flags.
- `PowerShell runtime status` - shows the PowerShell runtime selected by the project.
- `Install portable PowerShell` - installs project-local `system_core\powershell\pwsh.exe`.
- `Windows Long Paths` - checks and enables `LongPathsEnabled`.
- `Git Long Paths` - runs `git config --global core.longpaths true`.

PowerShell resolution order:

1. `system_core\powershell\pwsh.exe`
2. `pwsh.exe` from `PATH`
3. `powershell.exe`

Long Paths help with DEV trees containing `node_modules`, virtualenvs, SDKs and deep workspaces. Short project paths such as `S:\Code\Project` are still preferable.

## Maintenance And Cleanup

The `Maintenance & Cleanup` section collects software cleanup and managed workspace operations. It is separate from `Runtime and shell`, so runtime means environment while destructive cleanup stays in its own area.

Workbench `Reset` returns to project `input/output` without deleting files; `Delete` clears the current `Source` and `Target` after confirmation.

### Codex Nuke And Python Nuke

These are separate runtime cleanup tools:

```text
tools\codex_nuke
tools\python_nuke
```

Codex Nuke operations:

- `Audit`;
- `Dry run`;
- `Session reset` - soft reset: kills processes, clears `.codex\sessions`, AppX LocalCache/TempState, but keeps auth/install/registry;
- `NUKE, keep CLI state` - cleanup while preserving `~\.codex` for Codex CLI;
- `NUKE full`.

Python Nuke operations:

- `Audit`;
- `Dry run`;
- `NUKE full`;
- `NUKE, keep winget`.

The GUI runs a selected mode directly through the service layer, not through the interactive `Nuke.cmd` menu.

Python Nuke removes vanilla Python, Store Python/AppX, Python Launcher, pipx, uv, conda, pip caches/config, env vars, Start Menu shortcuts, PATH entries and uninstall registry entries. It should not touch project venvs, the ChatGPT app or the tool folder itself. Reboot after a real nuke before reinstalling Python.

## Browser Bookmarks Master

`Browser Bookmarks Master` lives under OS -> Browsers and supports both native Chromium profile backups and HTML bookmark exports. Native backup mode copies the profile files:

- `Bookmarks`;
- `Favicons`;
- `Favicons-journal`.

In the GUI, the action is selected at the top (`Status`, `Import`, `Export`, `Transfer`), and the browser selector adapts to the action:

- `Status` - read-only check of one or several selected browsers, processes, profile folders, three files and newest importable backup from Workbench SOURCE.
- `Export master to Workbench TARGET` - browsers are selected with checkboxes; closes the selected browsers and copies the three files into new versioned backup folders under Workbench TARGET.
- `Import master from Workbench SOURCE` - check one or several system browsers, or select one exact portable profile. Native mode copies a complete backup. HTML mode performs a clean import: replaces `Bookmarks`, clears old favicon tables and immediately restores embedded `ICON=` images into SQLite. Each target gets a rollback backup.
- `Transfer master between browsers` - the source is selected with a radio button and targets with checkboxes; the source is hidden from targets. The operation first exports the source into a project-local backup, then imports that backup into selected targets.
- `Open local safety backups` - opens the local pre-import backup folder.

The top toggles are marked by border intent: `Status` and `Export` are dark green, while `Import` and `Transfer` are dark orange.

Use `SYSTEM` for standard installed browser profiles. Use `PORTABLE` and choose the exact profile folder containing `Bookmarks` for custom or portable installations; the executable folder alone does not identify `--user-data-dir`.

`Create rollback` is enabled by default for import and standalone Favicons cleanup. Disable it when the current favicon database is already damaged and not worth preserving. `Open backup` only opens `backup\browser_bookmarks`; it does not create a backup by itself.

A missing selected profile does not stop the whole run: it is logged as `SKIP`, the GUI shows a yellow warning toast, and the operation continues with the remaining available profiles.

Standalone Favicons cleanup creates a rollback first and applies to all checked system browsers or one portable profile. It is not the primary HTML repair path: clean HTML import rebuilds the favicon tables directly from embedded ICON data. Operations leave browsers closed and never launch them automatically.

Versioning applies to backup folders, not to files. Folder names use `YYYY-MM-DD_HH-MM-SS_<backup_label>_vNN`; `backup_version=auto` picks the next free number, and an occupied manual version is bumped instead of overwritten. During multi-export the selected browser key is appended to the requested `backup_label`. Inside the folder, file names stay browser-compatible: `Bookmarks`, `Favicons`, `Favicons-journal`.

Workbench `TARGET` is used for export, Workbench `SOURCE` for import/status. UNC network paths work when the Windows session already has access to the share. More detail: `docs\BROWSER_BOOKMARKS_MASTER_RU.md`.

The window includes a UNC builder for network paths like `\\SERVER\Share\Folder`: enter the server/computer, the `Share` name and an optional folder inside the share. The `SOURCE`/`TARGET` buttons save the result as the current Workbench route.

## Network Cleaner

This section handles Windows network diagnostics, backup and repair.

### Diagnostics And Backup

`Status snapshot` - read-only baseline. It collects the current network state and writes a timestamped project-local snapshot: `ipconfig`, routes, adapters, DNS, proxy, Wi-Fi status, registry/network hints and the run log. It does not repair or reset anything.

`Backup network state` - full snapshot without Wi-Fi passwords. It saves adapters, IP/DNS/routes, WinHTTP/WinINet proxy, firewall export, Winsock/network registry exports, `hosts`, Wi-Fi profiles without clear keys, restore manifest and logs.

`Backup with Wi-Fi keys` - the same backup plus Wi-Fi profiles exported with `key=clear`. This is sensitive: exported XML files can contain Wi-Fi passwords in plain text. For simple profile transfer, XML without clear keys is often enough.

`Open backup folder` - opens the Network Cleaner snapshot folder. It contains restore manifests, exported files and logs.

### TimeMachine Restore

`Restore latest` and `Restore selected` restore network state from a Network Cleaner snapshot. Before rollback, the project first captures the current state so even the currently broken state is not lost.

Restore attempts to bring back the practical network state:

- imports saved `.reg` files;
- restores `hosts`;
- imports firewall `.wfw`;
- runs the saved `netsh interface dump`;
- adds Wi-Fi profiles back;
- refreshes DNS registration/cache.

This is not a replacement for an offline disk image. A live Windows network stack, Winsock catalog and adapter database cannot be guaranteed byte-for-byte from a running system, but this is a controlled project-local rollback.

### Repair Profiles

`Light repair` - the softest mode. It flushes/registers DNS, clears ARP cache, refreshes NetBIOS and renews DHCP only for connected DHCP interfaces. It does not run `route -f`, Winsock reset, TCP/IP reset, firewall reset or Wi-Fi profile deletion.

`Standard repair` - normal escalation. It resets Winsock, TCP/IP and WinHTTP proxy, then refreshes DNS and ARP. Reboot is recommended afterwards.

`Nuclear repair` - heavy mode for cases where standard repair did not help. It runs standard repair plus route flush and the deeper original script flow. The external script still keeps separate typed confirmations for the most destructive actions such as `NETCFG-D`.

Recommended order:

1. `Status snapshot`.
2. `Light repair`.
3. If it does not help - `Standard repair`.
4. If the result is worse - `Restore selected`.
5. Use `Nuclear repair` only when normal repair is no longer enough.

### Proxy

`Proxy status` - shows current-user WinINet/System proxy and machine-level WinHTTP proxy.

`Disable user proxy` - disables proxy settings for the current user. Before changes, the proxy tool saves a `.reg` backup under `tools\disable_windows_proxy\backup\proxy_YYYYMMDD_HHMMSS`. The command disables WinINet/System Proxy, removes stale `ProxyServer`/`ProxyOverride`, removes `AutoConfigURL` by default, disables `AutoDetect` by default and clears WinINet connection cache values. Useful after VPN, corporate or local proxy tools leave stale values in the user profile.

`Reset WinHTTP proxy` - resets machine-level WinHTTP proxy used by services and some system tools. This is not the same as browser/user proxy.

Manual restore: import the needed `.reg` from the backup folder only when you intentionally want to bring the previous proxy state back.

## Connectivity And Adapters

The `Connectivity` section collects Wi-Fi profiles, SMB login for Windows file sharing, adapter actions and quick LAN/Wi-Fi modes. It is not the Network Cleaner repair area; it routes the current connection state.

### Wi-Fi Profiles

`Wi-Fi status` - shows WLAN interfaces and saved profiles.

`Connect profile` - connects a selected saved profile, optionally through a selected Wi-Fi adapter.

`Profile autoconnect` - switches a profile between automatic and manual connection mode.

`Export profiles` - exports Wi-Fi XML files to a selected folder. Clear-text keys are included only when the checkbox is enabled.

`Import XML file/folder` - imports one XML file or all XML files from a folder. `All users` scope requires administrator rights; `Current user` applies the profile only to the current user.

### SMB / Windows File Sharing

`SMB network login` opens an external console for `net use` authentication to a Windows file-sharing computer.

This helper is for existing Windows file sharing:

- enter the computer name without `\\`, for example `NAS`, `SERVER01` or a workstation name;
- enter the user as a short name, `DOMAIN\User` or `user@example.com`;
- the password is typed only in the external console, not in the GUI;
- DevOps Tools does not receive or store the password;
- the SMB cache stores only `computer / user` pairs in `config\smb_network_logins.json`;
- after a successful login, Explorer can open `\\COMPUTER`.

The operation uses `net use \\COMPUTER\IPC$ /user:... * /persistent:yes`, then shows `net view \\COMPUTER`. It does not create shares, change ACLs or enable the SMB server.

If Windows returns `1219`, there is already an SMB session to that computer under another user. Close the old session through `net use`, Windows Credential Manager or a reboot, then retry.

### Adapter And LAN/Wi-Fi Modes

These operations switch connection modes rather than repairing the network stack.

Operations:

- `Adapter action` - enable, disable or restart the selected adapter;
- `LAN/Wi-Fi switch` - LAN only, Wi-Fi only, both on, or cycle Wi-Fi;
- `Wi-Fi sticky pair` - make one profile auto-connect and keep another profile manual.

The GUI uses dynamic sources for adapters, saved Wi-Fi profiles and an SMB login cache without passwords.

Classic sticky flow from the tool pack: one Wi-Fi profile is set to `connectionmode=auto`, another to `connectionmode=manual`, and Ethernet can be enabled/disabled through `netsh interface set interface`. Enabling/disabling a wired adapter requires administrator rights and can interrupt active connections.

## WSL Toolkit

WSL is one of the main modules. It is a managed project layer, not a loose pile of old wrappers.

Basic operations:

- `System WSL2 status`;
- `Enable WSL2 features`;
- `Update WSL2`;
- `Installable distros`;
- `Install distro`;
- `Install from image file`;
- `Installed distros`;
- `WSL status`;
- `Shutdown WSL`.

Distro install supports:

- the online `wsl --list --online` catalog;
- pinned common distros, including Ubuntu 26.04;
- manual distro override;
- custom instance name;
- system default location;
- selected folder;
- `no_launch` by default.

Example fast-disk custom location:

```text
S:\WSL\VHDX\Ubuntu-26.04
```

### Linux Configuration

After distro installation, the project can configure the Linux layer:

- `Package update` - apt/dnf metadata update and optional upgrade;
- `Account bootstrap` - Linux user, sudo/wheel and default WSL user;
- `Dev packages` - baseline development packages;
- `Micro baseline`;
- `MC skin`;
- `Neovim base`.

For apt inside WSL, the project can handle common network issues:

- Force IPv4;
- HTTPS mirror rewrite;
- retries;
- timeouts;
- mirror choice: archive, azure, kernel, yandex, custom or keep.

This is useful on networks where IPv6 does not physically pass or HTTP mirrors are unreliable.

### WSL Distro Actions

Operations for installed distributions:

- `Terminate distro`;
- `Backup distro`;
- `Clone distro`;
- `Move distro`;
- `Delete distro`;
- `Import VHDX in place`;
- `Restore from backup`;
- `Register all VHDX`.

`Register all VHDX` uses dry-run by default. It scans the VHDX root, skips VHDX files that are already registered, and shows the planned actions.

For VHD backup, the project shuts down WSL before export to avoid `ERROR_SHARING_VIOLATION`.

### Ubuntu Dev Installer Kit

This kit lives in the WSL section because it belongs to Linux/Ubuntu workflows:

```text
tools\ubuntu_dev_installer
```

GUI shortcuts:

- open kit folder;
- README RU;
- Btrfs/Timeshift guide;
- installer script;
- NVMe prep script;
- package lists.

This is a project-local Linux setup reference kit, not the WSL distro installer itself.

## Virtualization

The `Virtualization` section controls the host Windows hypervisor mode:

- `Virtualization status` - read-only `hypervisorlaunchtype`, Windows optional features, VBS/Core Isolation and interpreted current mode;
- `Optimization status` - read-only diagnostics for what slows VM/WSL: Core Isolation/VBS, active power plan, Defender exclusions, `.wslconfig` and WSL VHDX placement;
- `Mode: Hyper-V / WSL2` - turns the hypervisor on and enables `VirtualMachinePlatform`;
- `Mode: Third-party fast` - sets `hypervisorlaunchtype=Off` for fast VMware/VirtualBox/emulator workloads, while WSL2/Hyper-V/Sandbox stop until switched back;
- `Mode: Coexist (WHP)` - enables `Windows Hypervisor Platform` and `VirtualMachinePlatform` so modern third-party VMs can run alongside Hyper-V/WSL2, usually slower;
- `Enable/Disable Hyper-V`;
- `Enable/Disable Windows Sandbox`.

Every changing operation writes a BCD backup to:

```text
backup\virtualization
```

and requires a reboot before the new mode is active. VBS/Core Isolation is diagnostic only: if Core Isolation is enabled, VT-x may still be held even when `hypervisorlaunchtype=Off`.

## Hosts And Bitrix

This section manages a `hosts` override for on-prem Bitrix.

Operations:

- `Detect current endpoint`;
- `Status / DNS / ports`;
- `Enable override`;
- `Disable override`;
- `Restore original hosts`.

Current default:

```text
portal.itpgrad.ru -> 192.168.0.130
port: 443
```

`Detect current endpoint` performs DNS-only lookup without stale `hosts`, accepts only local/private/link-local/loopback IPs and scans candidate ports.

Important: Windows `hosts` cannot store a port. The project writes IP -> host, while ports are stored in a managed comment metadata line.

`Enable override` saves a pre-patch backup and writes its name into the managed comment. `Disable override` performs a bitwise depatch by copying that backup over the system `hosts` file.

More details: `docs\BITRIX_HOSTS_RU.md`.

## Default Apps

The `DEFAULT APPS` section controls which programs Windows uses to open files
and links, and protects that choice from being reclaimed by Windows or Edge.
Seven tabs split the work by role:

| Tab | Responsible for |
|-----|-----------------|
| `POLICY` | The reference association set and pinning it to Windows (DISM XML + HKLM policy) |
| `MICROSOFT` | In-box Microsoft apps: remove, restore, keep removed |
| `EDGE` | Stop Edge reclaiming links and file types; WebView2 stays protected |
| `TRACKING` | Warning when associations change, plus Defender exclusions for Audion folders |
| `SNAPSHOT` | The full association map of the current user: compare and capture |
| `GROUPS` | The same snapshots per file family - photo, audio, video, PDF, documents, archives, browser |
| `OVERVIEW` | Every check in the section, one report, no system changes |

### Snapshot Versus Policy

Windows protects the per-user choice (`HKCU ... UserChoice`) with a hash bound
to the user and the machine. This project neither forges that hash nor ships a
third-party helper that does: snapshots only read `ProgId` from the registry.

That splits the roles. `SNAPSHOT` and `GROUPS` answer "what is set now and what
changed", `TRACKING` warns when it changes, and only `POLICY` puts defaults back
- through DISM XML and the HKLM `DefaultAssociationsConfiguration` policy.

### POLICY

The primary layer uses the official Microsoft admin/deployment path: DISM
default app associations XML, the HKLM policy
`DefaultAssociationsConfiguration`, the active XML under ProgramData, and
application at user sign-in.

Actions (`policy_action`): check what opens files now, capture a snapshot of the
current state, make the current state the reference, take the reference from a
file, pin the set to Windows, remove the pin, prune old backups, plus three
"open folder" actions.

Fresh Windows ritual:

1. Install your applications.
2. Set defaults manually in Windows.
3. Run the check action.
4. Fill `Backup label`, for example `golden-before`.
5. Make the current state the reference.
6. Keep `Remove Suggested=true` enabled.
7. Pin the set to Windows.
8. Sign out/sign in or reboot.
9. Run the check action again.

Restoring the reference from a backup: take the reference from a file -> select
`Backup XML` from `backup\default_apps` -> pin the set to Windows -> sign
out/sign in.

Removing the pin deletes the `DefaultAssociationsConfiguration` registry value
and backs up the policy XML/value. It does not immediately change current
associations - it only removes the instruction that tells Windows to apply the
XML at user sign-in.

Windows Home/Core: Microsoft does not document this policy as a guaranteed
mechanism for Home/Core. The GUI reports the edition and blocks apply by default
on unsupported editions unless expert override is enabled.

More details: `docs\DEFAULT_APPS_GUARD_RU.md`.

### MICROSOFT

A catalog of 31 in-box apps grouped as media and photos, games, communication,
news and promo, notes and tools. Removing the installed package frees the
associations; removing the provisioned copy keeps new user profiles clean.

Actions (`apps_action`): status, remove selected apps, remove and keep removed,
restore apps, re-provision for new users, stop keeping them removed, run the
keep-removed check now, open the keep-removed folder.

"Remove and keep removed" is a removal plus a scheduled task that re-applies it
after feature updates; on Pro/Enterprise it also adds AppLocker deny rules.
Always start with status and `dry run`.

### EDGE

Edge is never uninstalled. This tab stops it from nagging to be the default
browser, running in the background and claiming file types - through documented
HKLM policies. WebView2 is explicitly protected: many applications render their
UI with it.

Levels: `Calm` - no nagging, no background mode; `Quiet` - plus sidebar,
Shopping, Collections and the extra Edge channels. A separate action installs
the official Evergreen WebView2 Runtime.

### TRACKING

A scheduled task compares the live association map against the baseline at each
logon and raises a toast when something moved. Warning only - there is no
automatic restore. Microsoft Defender exclusions for Audion folders live here
too; Defender itself is never disabled.

### SNAPSHOT and GROUPS

`SNAPSHOT` compares and captures the full association map of the current user,
read straight from the registry. `GROUPS` does the same per file family:
`photo`, `audio`, `video`, `pdf`, `documents`, `archives`, `browser` or a custom
extension list, which is convenient while applications are still being
installed. Group membership matches the file classification of `Audion Disk
Tools`. "Compose" merges the committed groups into the shared snapshot file.

A note on PowerShell: the AppX/AppLocker commands are not part of the portable
layer. They deliberately run under system Windows PowerShell 5.1
(`C:\Windows\System32\WindowsPowerShell\v1.0\powershell.exe`). Portable
PowerShell 7 may return `Deserialized.*` objects instead of live `AppxPackage`
objects, which stops AppLocker from building a publisher rule.

Two manual launchers are available: `cli\launcher_association_defense.cmd`
covers all seven tabs, `cli\launcher_default_apps.cmd` drives the `POLICY` tab
only, asking for a backup label and a retention window.

```cmd
cli\launcher_association_defense.cmd
cli\launcher_default_apps.cmd
```

More details: `docs\ASSOCIATION_DEFENSE_RU.md`.

## Hardware

The Hardware section combines driver guards, NVIDIA controls and disk procedures.

### Driver/Firmware Audit

Read-only diagnostics for:

- problem devices;
- BIOS / Embedded Controller;
- BIOS registry summary;
- firmware resources;
- firmware resource details;
- key signed drivers.

Key signed drivers are filtered around practical platform components: Realtek, Intel SST, ME/CSME, Thunderbolt/USB4, Serial IO, Dynamic Tuning, GNA, Lenovo/ThinkPad power/hotkey, fingerprint, camera/IR/MIPI, HID/ELAN and monitor INF. The report writes TXT into `logs`, optionally JSON/CSV, and does not require administrator rights for the basic path.

The module is strictly read-only: it does not flash firmware, install or remove drivers, edit registry/settings or download anything. There are shortcuts to open the addon folder and README.

### Driver Update Blocker

Windows Update driver policy operations:

- `Check driver protection`;
- `Block Windows Update drivers`;
- `Unblock Windows Update drivers`;
- `Open policy backups`.

Block enables:

- `ExcludeWUDriversInQualityUpdate=1`;
- disabled driver wizard search through Windows Update;
- device metadata download policy.

Typical order:

1. Run `Check driver protection`.
2. Run `Block Windows Update drivers`.
3. Reboot.
4. Check status again.

### NVIDIA Driver Install Restrictions

Operations:

- `Block NVIDIA driver installs`;
- `Unblock NVIDIA driver installs`.

This uses Device Installation Restrictions for current NVIDIA PCI IDs. It is normally enabled after manually installing a known-good NVIDIA driver. Leave `Retroactive block` off unless you have a specific reason.

Root wrapper for quick use without the GUI: `cli\Lock-NVIDIA-Driver-Installs.cmd --no-pause`. By default it blocks present NVIDIA PCI Hardware IDs without retroactive removal; expert flags are `--include-compatible` and `--retroactive`.

### Driver Store Backups

Operations:

- `Save Driver Store manifest`;
- `Export installed drivers`;
- `Restore exported drivers`;
- `Open driver backups`;
- `Open Driver Update Blocker folder`.

Restore runs `pnputil /add-driver ... /subdirs /install`. Prefer backups from the same machine or a very similar hardware profile.

In emergency HWID rank repair, the target INF must match by version and by HWID. If no HWID match is found, repair stops; the version-only fallback is an explicit advanced checkbox for manually verified INF files only.

### NVIDIA HDMI/DP Audio

Operations:

- `NVIDIA audio status`;
- `Export NVIDIA audio IDs`;
- `Disable NVIDIA HDMI/DP audio`;
- `Enable NVIDIA HDMI/DP audio`;
- `Policy-block NVIDIA HDMI/DP audio`;
- unblock policy;
- open output/backup/tool folders.

The module targets only NVIDIA HDAUDIO codec IDs like:

```text
HDAUDIO\FUNC_01&VEN_10DE...
```

It does not block GPU PCI IDs and does not touch normal audio interfaces.

Root wrapper for a quick policy block without the GUI: `cli\Lock-NVIDIA-HDMI-DP-Audio.cmd --no-pause`. It blocks NVIDIA HDAUDIO IDs and disables already installed matching HDMI/DP audio devices.

More details: `docs\HARDWARE_DRIVER_GUARD_RU.md`.

## Storage / Disk Procedures

This block is inside Hardware.

### Inventory

`Disk and volume inventory` - read-only `Get-Disk` and `Get-Volume` summary: disk numbers, sizes, status, volume letters and filesystems. It does not partition or format anything.

`Selected disk details` - read-only details for one selected disk: disk properties and partition layout. Use it before manual disk work to avoid mixing up disk numbers.

### SSD/NVMe Reset Wizard

`Launch SSD/NVMe wizard` opens the original SSD/NVMe Reset Wizard v4 in an external console. This is a separate destructive interactive wizard for used SSD/NVMe reset/reprovision flows. The GUI only starts it; destructive actions still require the wizard's own typed confirmations.

`Open SSD/NVMe folder` opens `tools\ssd_nvme_reset_wizard` with README, logs and original scripts. This is a safe browse operation.

The wizard is intended for non-system disks. It shows disks/partitions, blocks the current system disk by default, can delete one selected partition with `delete partition override`, run fast `DiskPart clean`, run slow `DiskPart clean all`, rebuild the disk as GPT + one NTFS volume and write a log.

Important boundary: `clean` removes the partition table and `clean all` writes zeroes across the device, but neither is the same as vendor Secure Erase, NVMe Sanitize, Format/Sanitize or OPAL/PSID revert. For the closest SSD/NVMe factory-reset workflow, use a vendor utility or controller-level tools.

### WinRE Extend

`WinRE layout status` - read-only `reagentc /info` and system disk layout check. It shows where active WinRE lives, whether it is adjacent to `C:`, and which partition layout Windows sees.

`Run WinRE extend wizard` starts the project-local script `tools\winre_extend\Remove-WinRE-And-Extend-System.ps1` after project confirmation. The internal `YES` prompt is satisfied with `-YesIUnderstand`, so the GUI confirmation is especially important here.

The WinRE extend wizard:

1. Disables WinRE.
2. Removes the WinRE recovery partition to the right of C:.
3. Extends C: into the freed space.

The script blocks automatic execution if WinRE is not on the same disk, is not to the right of `C:`, or another partition sits between `C:` and WinRE. But when the layout is valid, it really deletes the recovery partition.

This is an expert one-way operation. A full offline system image is the proper recovery strategy after deciding to remove the WinRE partition, not relying on the Windows Recovery partition that was deliberately removed. WinRE remains disabled afterwards unless it is recreated/reconfigured separately.

## Utilities

### AI CLI Backup

`Backup (export)` creates a fresh, verifiable Claude Code and Codex bundle in `output\ai_backup`. The tool follows `CLAUDE_CONFIG_DIR`, `CODEX_HOME`, `CODEX_SQLITE_HOME` and `sqlite_home` from `config.toml`; it builds into a temporary directory, writes `manifest.json` with sizes and SHA-256 hashes, verifies it, and only then replaces the previous bundle. Repeated exports therefore cannot retain deleted stale files.

Essential keeps memory, settings, skills, plugins, rules and automations. Full also adds session history and caches. Live Codex SQLite databases are captured through the SQLite Backup API, while the machine-specific `installation_id` is not transferred. Authentication is independent: `Include authentication secrets` adds Claude `.credentials.json` and Codex `auth.json` when file-backed authentication is present. It is off by default; protect an auth-bearing bundle like a password.

`Restore (import)` reads a bundle staged directly in `input` and validates its manifest, every SHA-256 hash and the absence of undeclared files before writing. Dry run is on by default and reports `ADD / REPLACE / SAME`. Essential restore ignores history even when the staged bundle is Full; Full and auth are selected independently. Matching files are replaced and unrelated local files are never deleted. Close Claude and Codex before a real restore.

When moving between computers, configuration files containing absolute paths are reported separately. A real restore into different profile roots stops until the user reviews Dry run and explicitly enables `Allow saved absolute paths from another PC`. Folders made by the previous `AI-Backup.ps1` have no manifest and require `Allow legacy bundle without manifest`; this is compatibility with an older tool backup, not a different Claude/Codex memory format.

### OpenSSH KeyKit

OpenSSH KeyKit is a project-local export/import helper for SSH material. This is a sensitive area: exports can contain private keys, `known_hosts`, client config, `authorized_keys`, server host keys and `sshd_config`.

Default backup root:

```text
backup\ssh_keykit
```

Snapshot layout:

```text
backup\ssh_keykit\<Machine>\users\<User>\<Timestamp>\client
backup\ssh_keykit\<Machine>\_server\<Timestamp>
```

`Export client SSH keys` copies `%USERPROFILE%\.ssh` files matching `id_*`, `*.pub`, `config`, `known_hosts*`, `authorized_keys` and the `config.d` folder when present. This is a sensitive export because `id_*` files without `.pub` are usually private keys.

`Export client + server SSH keys` runs client export plus, when elevated, copies `ProgramData\ssh\ssh_host_*` and `sshd_config`. Without elevation, server host keys are skipped.

`Import client SSH keys` uses the newest or selected snapshot, backs up the current `%USERPROFILE%\.ssh` to a folder like:

```text
%USERPROFILE%\.ssh.bak.YYYYMMDD_HHMMSS
```

then copies the client snapshot into `.ssh` and fixes private key ACLs with `icacls`.

`Import client + server SSH keys` also imports server host keys into `ProgramData\ssh`, fixes ACLs, stops/starts `sshd` and sets the service startup to Automatic. This is a system-change operation; use it only when preserving SSH server identity is intentional.

`Open SSH KeyKit folder` opens `tools\ssh_keykit` with scripts/wrappers.

Practical rule: client export is for moving user access. Server host keys should be moved only when the SSH server identity must remain the same; otherwise clients will see a different host key and warn, correctly.

### Certificate KeyKit

Certificate KeyKit is a project-local helper for Windows certificate stores. It answers which certificates can survive reinstall and which private keys are TPM-bound/non-exportable and cannot be migrated as PFX.

Operations:

- `Certificate status` - selected store list with subject, thumbprint, expiry, private key and exportability;
- `Export personal keys to PFX` - exportable private-key certificates into password-protected `.pfx`;
- `Export store to SST (public)` - public Root/CA/intermediate certificates into `.sst` without private keys;
- `Import PFX`;
- `Import certificate / CA`;
- `Open certificate backup folder`.

Default backup root:

```text
backup\certificates
```

`.pfx` files contain private keys and are secrets on the same level as SSH private keys. The PFX password is entered in Advanced for one run and is not logged. TPM/non-exportable keys cannot be exported by design; the operation reports them as SKIP.

### ripgrep

`ripgrep version` shows the project-local executable version:

```text
ripgrep\rg.exe
```

### Documentation PDF

`Documentation PDF` renders project Markdown guides and instructions into:

```text
docs\PDF
```

Dry-run is autonomous and does not require the render engine. Real generation uses the external `dev_markdown_pdf_engine.py`; set its path with `--engine` or `AUDION_MARKDOWN_PDF_ENGINE`, or let the wrapper discover a neighboring Audion Office OCR AI project.

Operations:

- `Preview PDF export plan` - dry run: shows source Markdown files and target PDFs;
- `Generate docs PDFs` - creates both `dark` and `light-sand` PDFs by default;
- `Open docs PDF folder` - opens `docs\PDF`.

The export includes root guides, `docs\*.md`, `GitHub\*.md` and optional agent instructions (`AGENTS.md`, `CLAUDE.md`). Markdown remains the source of truth; PDFs are not stored beside source `.md` files. No separate visual PDF verification is required after generation.

### Open Tool Folder

Opens approved project-local utility folders.

## Maintenance

GUI has two maintenance zones:

- `Delete` - clears the current Workbench `Source`/`Target` after confirmation;
- `Clear Workbench workspace` - in the `Maintenance & Cleanup` command tree.

They clean managed working folders, not arbitrary user paths.

Separate source-cleanup procedure:

```cmd
cleanup_project.cmd
```

Dry-run:

```cmd
cleanup_project.cmd /DRYRUN /Y
```

Regular cleanup clears generated backup snapshots together with the other managed working zones while preserving the folder structure and `.gitkeep` files. To clear only project-local backup snapshots without touching the other zones, use the separate backup-only mode:

```cmd
cleanup_project.cmd /BACKUP
```

It removes only `backup` contents, then recreates the managed folder structure through `init_folders.cmd`. A real run always asks its own `Y/N/Q` question; preview the plan with `cleanup_project.cmd /BACKUP /DRYRUN`.

## GUI Terminal

The right panel is the main operation log:

- status;
- progress;
- stdout/stderr;
- PowerShell/CMD output;
- final operation result.

The bottom command bar supports:

- PowerShell or CMD;
- command history;
- pinned commands;
- working directory picker;
- file picker.

History location:

```text
config\terminal_commands.json
```

<!-- BEGIN GENERATED PARAMETER REFERENCE -->
## Complete Command And Parameter Reference

This reference is generated from `config\tool_manifest.yaml`. It includes every GUI description, risk classification, inherited field, default and selectable option. Practical workflows and consequence notes remain in the authored sections above.

### Runtime and shell > Preflight snapshot

- Operation id: `preflight_status`
- Description: One terminal snapshot: elevation, WSL, virtualization, PowerShell, network, Wi-Fi and disk risk flags.
- Risk: kind=`safe`, risk_level=`readonly`
- Parameters: none.

### Runtime and shell > PowerShell runtime status

- Operation id: `runtime_status`
- Description: Show portable/system PowerShell resolution and version.
- Risk: kind=`safe`, risk_level=`readonly`
- Parameters: none.

### Runtime and shell > Check Windows Long Paths

- Operation id: `windows_long_paths_status`
- Description: Show HKLM LongPathsEnabled and Git core.longpaths values. Does not change settings.
- Risk: kind=`safe`, risk_level=`readonly`
- Parameters: none.

### Runtime and shell > Enable Windows Long Paths

- Operation id: `windows_long_paths_enable`
- Description: Set HKLM LongPathsEnabled=1. Apps still need longPathAware manifest support.
- Risk: kind=`dangerous`, risk_level=`system_change`
- Parameters: none.

### Runtime and shell > Enable Git Long Paths

- Operation id: `git_long_paths_enable`
- Description: Set git config --global core.longpaths true for the current user.
- Risk: kind=`dangerous`, risk_level=`user_write`
- Parameters: none.

### Runtime and shell > Install portable PowerShell

- Operation id: `install_portable_powershell`
- Description: Download and install pwsh.exe into system_core/powershell.
- Risk: kind=`safe`, risk_level=`readonly`
- Parameters: none.

### Browser Bookmarks Master > Status

- Operation id: `browser_bookmarks_status`
- Description: Read-only check: selected browser profile files, process state and latest importable backup from Workbench SOURCE. GUI status can run for one or several checked browsers.
- Risk: kind=`safe`, risk_level=`readonly`
- Parameters:
  - `browser_profile` — **Browser** (type=`select`, default=`chrome`).
  - `backup_label` — **Backup label** (type=`text`, default=`bookmarks_master`).
  - `backup_version` — **Backup version** (type=`text`, default=`auto`).
  - `close_browser_process` — **Close browser before file operation** (type=`checkbox`, default=true).
  - `browser_profile_path` — **Portable browser profile folder** (type=`folder`).
  - `backup_source_path` — **Workbench source backup folder** (type=`folder`).
  - `backup_target_path` — **Workbench target backup folder** (type=`folder`).

### Browser Bookmarks Master > Clear local Favicons cache

- Operation id: `browser_bookmarks_clear_favicons`
- Description: Create a rollback backup, close selected browsers, then delete Favicons and sidecars. Chrome rebuilds an empty database but refetches icons only as pages are visited.
- Risk: kind=`dangerous`, risk_level=`user_write`
- Parameters:
  - `browser_profile` — **Browser** (type=`select`, default=`chrome`).
  - `backup_label` — **Backup label** (type=`text`, default=`bookmarks_master`).
  - `backup_version` — **Backup version** (type=`text`, default=`auto`).
  - `close_browser_process` — **Close browser before file operation** (type=`checkbox`, default=true).
  - `browser_profile_path` — **Portable browser profile folder** (type=`folder`).
  - `backup_source_path` — **Workbench source backup folder** (type=`folder`).
  - `backup_target_path` — **Workbench target backup folder** (type=`folder`).

### Browser Bookmarks Master > Export master to Workbench TARGET

- Operation id: `browser_bookmarks_export_master`
- Description: Close selected browsers and copy Bookmarks, Favicons and available Chromium sidecar files into versioned backup folders under Workbench TARGET.
- Risk: kind=`dangerous`, risk_level=`secret_export`
- Parameters:
  - `browser_profile` — **Browser** (type=`select`, default=`chrome`).
  - `backup_label` — **Backup label** (type=`text`, default=`bookmarks_master`).
  - `backup_version` — **Backup version** (type=`text`, default=`auto`).
  - `close_browser_process` — **Close browser before file operation** (type=`checkbox`, default=true).
  - `browser_profile_path` — **Portable browser profile folder** (type=`folder`).
  - `backup_source_path` — **Workbench source backup folder** (type=`folder`).
  - `backup_target_path` — **Workbench target backup folder** (type=`folder`).

### Browser Bookmarks Master > Import master from Workbench SOURCE

- Operation id: `browser_bookmarks_import_master`
- Description: Import an explicitly selected native backup or HTML file into all checked system browsers; portable mode uses one exact profile. Each target gets a rollback backup.
- Risk: kind=`dangerous`, risk_level=`destructive`
- Parameters:
  - `browser_profile` — **Browser** (type=`select`, default=`chrome`).
  - `backup_label` — **Backup label** (type=`text`, default=`bookmarks_master`).
  - `backup_version` — **Backup version** (type=`text`, default=`auto`).
  - `close_browser_process` — **Close browser before file operation** (type=`checkbox`, default=true).
  - `browser_profile_path` — **Portable browser profile folder** (type=`folder`).
  - `backup_source_path` — **Workbench source backup folder** (type=`folder`).
  - `backup_target_path` — **Workbench target backup folder** (type=`folder`).

### Browser Bookmarks Master > Transfer master between browsers

- Operation id: `browser_bookmarks_transfer_master`
- Description: Two-stage transfer: export the selected source browser into a project-local backup, then import that backup into selected target browsers with pre-import backups and Favicons cleanup.
- Risk: kind=`dangerous`, risk_level=`destructive`
- Parameters:
  - `browser_profile` — **Browser** (type=`select`, default=`chrome`).
  - `backup_label` — **Backup label** (type=`text`, default=`bookmarks_master`).
  - `backup_version` — **Backup version** (type=`text`, default=`auto`).
  - `close_browser_process` — **Close browser before file operation** (type=`checkbox`, default=true).
  - `browser_profile_path` — **Portable browser profile folder** (type=`folder`).
  - `backup_source_path` — **Workbench source backup folder** (type=`folder`).
  - `backup_target_path` — **Workbench target backup folder** (type=`folder`).

### Browser Bookmarks Master > Open local safety backups

- Operation id: `browser_bookmarks_open_local_backup`
- Description: Open project-local Browser Bookmarks backup folder with pre-import snapshots.
- Risk: kind=`safe`, risk_level=`readonly`
- Parameters:
  - `browser_profile` — **Browser** (type=`select`, default=`chrome`).
  - `backup_label` — **Backup label** (type=`text`, default=`bookmarks_master`).
  - `backup_version` — **Backup version** (type=`text`, default=`auto`).
  - `close_browser_process` — **Close browser before file operation** (type=`checkbox`, default=true).
  - `browser_profile_path` — **Portable browser profile folder** (type=`folder`).
  - `backup_source_path` — **Workbench source backup folder** (type=`folder`).
  - `backup_target_path` — **Workbench target backup folder** (type=`folder`).

### Network Cleaner > Status snapshot

- Operation id: `network_status`
- Description: Read-only baseline: collects ipconfig/routes/adapters/DNS/proxy/Wi-Fi status and writes a timestamped project-local diagnostic snapshot.
- Risk: kind=`safe`, risk_level=`readonly`
- Parameters: none.

### Network Cleaner > Backup network state

- Operation id: `network_backup`
- Description: Full Network Cleaner snapshot: adapters, IP/DNS/routes, proxy, firewall, registry and Wi-Fi XML without clear-text keys.
- Risk: kind=`safe`, risk_level=`readonly`
- Parameters: none.

### Network Cleaner > Backup with Wi-Fi keys

- Operation id: `network_backup_wifi_keys`
- Description: Sensitive snapshot: exports Wi-Fi profiles with clear-text keys into the Network Cleaner backup folder.
- Risk: kind=`dangerous`, risk_level=`secret_export`
- Parameters: none.

### Network Cleaner > Restore network backup > Restore latest

- Operation id: `network_restore_latest`
- Description: Restore the newest Network Cleaner snapshot. First captures the current state, then imports saved registry/network/firewall/hosts/Wi-Fi data where available.
- Risk: kind=`dangerous`, risk_level=`system_change`
- Parameters: none.

### Network Cleaner > Restore network backup > Restore selected

- Operation id: `network_restore_selected`
- Description: Restore a selected Network Cleaner snapshot from the backup folder. Use when latest is not the state you want to return to.
- Risk: kind=`dangerous`, risk_level=`system_change`
- Parameters:
  - `network_restore_snapshot` — **Network backup** (type=`select`).

### Network Cleaner > Repair profiles > Light repair

- Operation id: `network_light_repair`
- Description: Lowest-risk repair: flush/register DNS, clear ARP cache, refresh NetBIOS and renew DHCP only for connected DHCP interfaces.
- Risk: kind=`dangerous`, risk_level=`system_change`
- Parameters: none.

### Network Cleaner > Repair profiles > Standard repair

- Operation id: `network_standard_repair`
- Description: Normal escalation: resets Winsock, TCP/IP and WinHTTP proxy, then refreshes DNS and ARP. Reboot is recommended afterwards.
- Risk: kind=`dangerous`, risk_level=`system_change`
- Parameters: none.

### Network Cleaner > Repair profiles > Nuclear repair

- Operation id: `network_nuclear_repair`
- Description: Heavy repair: Standard repair plus route flush; the original script still asks separately before the deepest reset steps.
- Risk: kind=`dangerous`, risk_level=`system_change`
- Parameters: none.

### Network Cleaner > Proxy > Proxy status

- Operation id: `network_proxy_status`
- Description: Show current-user WinINet/System proxy and machine-level WinHTTP proxy without changing them.
- Risk: kind=`safe`, risk_level=`readonly`
- Parameters: none.

### Network Cleaner > Proxy > Disable user proxy

- Operation id: `network_proxy_disable_user`
- Description: Turns off current-user WinINet/System proxy settings. Useful after corporate/VPN/proxy tools leave stale proxy values.
- Risk: kind=`dangerous`, risk_level=`user_write`
- Parameters: none.

### Network Cleaner > Proxy > Reset WinHTTP proxy

- Operation id: `network_proxy_reset_winhttp`
- Description: Resets machine-level WinHTTP proxy used by services and some system tools. Does not edit browser/user proxy settings.
- Risk: kind=`dangerous`, risk_level=`system_change`
- Parameters: none.

### Network Cleaner > Open backup folder

- Operation id: `network_open_backup`
- Description: Open the project-local Network Cleaner backup folder with snapshots, restore manifests and run logs.
- Risk: kind=`safe`, risk_level=`readonly`
- Parameters: none.

### Connectivity > Wi-Fi profiles > Wi-Fi status

- Operation id: `network_wifi_status`
- Description: Show wlan interfaces and saved profiles. Does not change network settings.
- Risk: kind=`safe`, risk_level=`readonly`
- Parameters:
  - `wifi_profile` — **Wi-Fi profile** (type=`select`).
  - `wifi_profile_override` — **Manual profile** (type=`text`).
  - `wifi_adapter` — **Wi-Fi adapter** (type=`select`).

### Connectivity > Wi-Fi profiles > Connect profile

- Operation id: `network_wifi_connect`
- Description: Connect to the selected saved Wi-Fi profile, optionally through a selected adapter.
- Risk: kind=`safe`, risk_level=`readonly`
- Parameters:
  - `wifi_profile` — **Wi-Fi profile** (type=`select`).
  - `wifi_profile_override` — **Manual profile** (type=`text`).
  - `wifi_adapter` — **Wi-Fi adapter** (type=`select`).

### Connectivity > Wi-Fi profiles > Profile autoconnect

- Operation id: `network_wifi_connection_mode`
- Description: Set the selected Wi-Fi profile to automatic or manual connection mode.
- Risk: kind=`dangerous`, risk_level=`system_change`
- Parameters:
  - `wifi_profile` — **Wi-Fi profile** (type=`select`).
  - `wifi_profile_override` — **Manual profile** (type=`text`).
  - `wifi_adapter` — **Wi-Fi adapter** (type=`select`).
  - `connection_mode` — **Connection mode** (type=`radio`, default=`auto`).
    - Options: `auto` — Auto; `manual` — Manual

### Connectivity > Wi-Fi profiles > Export profiles

- Operation id: `network_wifi_export`
- Description: Export Wi-Fi profiles to a selected folder; clear keys are included only when the checkbox is enabled.
- Risk: kind=`dangerous`, risk_level=`secret_export`
- Parameters:
  - `wifi_profile` — **Wi-Fi profile** (type=`select`).
  - `wifi_profile_override` — **Manual profile** (type=`text`).
  - `wifi_adapter` — **Wi-Fi adapter** (type=`select`).
  - `target_folder` — **Target folder** (type=`folder`, default=`output\wifi_profiles`).
  - `include_keys` — **Include clear-text keys** (type=`checkbox`, default=false).

### Connectivity > Wi-Fi profiles > Import profiles > Import XML file

- Operation id: `network_wifi_import_file`
- Description: Add one Wi-Fi profile XML file to Windows.
- Risk: kind=`dangerous`, risk_level=`system_change`
- Parameters:
  - `wifi_profile` — **Wi-Fi profile** (type=`select`).
  - `wifi_profile_override` — **Manual profile** (type=`text`).
  - `wifi_adapter` — **Wi-Fi adapter** (type=`select`).
  - `import_user_scope` — **User scope** (type=`radio`, default=`current`).
    - Options: `current` — Current user; `all` — All users
  - `import_profile_xml` — **Profile XML** (type=`file`).

### Connectivity > Wi-Fi profiles > Import profiles > Import XML folder

- Operation id: `network_wifi_import_folder`
- Description: Import all Wi-Fi profile XML files from a selected folder.
- Risk: kind=`dangerous`, risk_level=`system_change`
- Parameters:
  - `wifi_profile` — **Wi-Fi profile** (type=`select`).
  - `wifi_profile_override` — **Manual profile** (type=`text`).
  - `wifi_adapter` — **Wi-Fi adapter** (type=`select`).
  - `import_user_scope` — **User scope** (type=`radio`, default=`current`).
    - Options: `current` — Current user; `all` — All users
  - `import_profile_folder` — **Profile XML folder** (type=`folder`, default=`output\wifi_profiles`).

### Connectivity > SMB network login

- Operation id: `smb_network_login`
- Description: Open an external console for net use authentication to a Windows file-sharing computer; type the password there and the SMB session becomes available for Explorer.
- Risk: kind=`dangerous`, risk_level=`user_write`
- Parameters:
  - `smb_login` — **SMB login cache** (type=`smb_login_cache`, default=`{computer: '', user: ''}`).
  - `smb_open_explorer` — **Open Explorer after login** (type=`checkbox`, default=true).

### Connectivity > Adapter action

- Operation id: `network_adapter_apply`
- Description: Enable, disable or restart the selected network adapter. Can interrupt active network connections.
- Risk: kind=`dangerous`, risk_level=`system_change`
- Parameters:
  - `adapter` — **Adapter** (type=`select`).
  - `adapter_action` — **Action** (type=`radio`, default=`restart`).
    - Options: `restart` — Restart; `enable` — Enable; `disable` — Disable

### Connectivity > LAN/Wi-Fi switch

- Operation id: `network_lan_wifi_switch`
- Description: Switch to LAN only, Wi-Fi only, both enabled, or cycle Wi-Fi and reconnect a saved profile.
- Risk: kind=`dangerous`, risk_level=`system_change`
- Parameters:
  - `lan_adapter` — **LAN adapter** (type=`select`).
  - `wifi_adapter` — **Wi-Fi adapter** (type=`select`).
  - `wifi_profile` — **Wi-Fi profile** (type=`select`).
  - `wifi_profile_override` — **Manual Wi-Fi profile** (type=`text`).
  - `switch_mode` — **Mode** (type=`radio`, default=`wifi_only`).
    - Options: `wifi_only` — Wi-Fi only; `lan_only` — LAN only; `both_on` — Both on; `cycle_wifi` — Cycle Wi-Fi

### Connectivity > Wi-Fi sticky pair

- Operation id: `network_wifi_sticky_pair`
- Description: Connect one saved profile and make it auto-connect while keeping the second profile manual.
- Risk: kind=`dangerous`, risk_level=`system_change`
- Parameters:
  - `auto_wifi_profile` — **Auto profile** (type=`select`).
  - `auto_wifi_profile_override` — **Auto profile manually** (type=`text`).
  - `manual_wifi_profile` — **Manual profile** (type=`select`).
  - `manual_wifi_profile_override` — **Manual profile manually** (type=`text`).
  - `wifi_adapter` — **Wi-Fi adapter** (type=`select`).
  - `connect_auto_profile` — **Connect auto profile** (type=`checkbox`, default=true).

### WSL Toolkit > Basic and install > System WSL2 status

- Operation id: `wsl_system_status`
- Description: Show Windows optional features, WSL status and installed distributions.
- Risk: kind=`safe`, risk_level=`readonly`
- Parameters: none.

### WSL Toolkit > Basic and install > Enable WSL2 features

- Operation id: `wsl_enable_features`
- Description: Enable Microsoft-Windows-Subsystem-Linux and VirtualMachinePlatform, then set WSL default version to 2. Reboot may be required.
- Risk: kind=`dangerous`, risk_level=`system_change`
- Parameters: none.

### WSL Toolkit > Basic and install > Update WSL2

- Operation id: `wsl_update_engine`
- Description: Run wsl --update for the Windows WSL engine.
- Risk: kind=`dangerous`, risk_level=`system_change`
- Parameters: none.

### WSL Toolkit > Basic and install > Installable distros

- Operation id: `wsl_list_online`
- Description: Run wsl --list --online and print available distro names.
- Risk: kind=`safe`, risk_level=`readonly`
- Parameters: none.

### WSL Toolkit > Basic and install > Install distro

- Operation id: `wsl_install_distro`
- Description: Install the selected online WSL distro either into the system default location or into a selected folder.
- Risk: kind=`dangerous`, risk_level=`system_change`
- Parameters:
  - `install_distro_pins` — **Pinned distros** (type=`profile_buttons`).
  - `install_distro` — **Distro** (type=`select`, default=`Ubuntu-26.04`).
  - `install_distro_override` — **Manual distro** (type=`text`).
  - `install_name` — **Instance name** (type=`text`).
  - `install_location_mode` — **Install location** (type=`radio`, default=`custom`).
    - Options: `custom` — Selected folder; `system` — System default
  - `install_location` — **Install folder** (type=`folder`).
  - `no_launch` — **Do not launch after install** (type=`checkbox`, default=true).

### WSL Toolkit > Basic and install > Install from image file

- Operation id: `wsl_install_from_file`
- Description: Install a local .wsl image such as ubuntu-26.04-wsl-amd64.wsl, or import tar/vhd/vhdx into a selected folder.
- Risk: kind=`dangerous`, risk_level=`system_change`
- Parameters:
  - `install_image_file` — **WSL source image** (type=`file`).
  - `install_name` — **Distro name** (type=`text`).
  - `install_location` — **Install folder** (type=`folder`).
  - `no_launch` — **Do not launch after install** (type=`checkbox`, default=true).

### WSL Toolkit > Basic and install > Installed distros

- Operation id: `wsl_list`
- Description: Run wsl --list --verbose.
- Risk: kind=`safe`, risk_level=`readonly`
- Parameters: none.

### WSL Toolkit > Basic and install > WSL status

- Operation id: `wsl_status`
- Description: Run wsl --status.
- Risk: kind=`safe`, risk_level=`readonly`
- Parameters: none.

### WSL Toolkit > Basic and install > Shutdown WSL

- Operation id: `wsl_shutdown`
- Description: Stop all WSL distributions.
- Risk: kind=`dangerous`, risk_level=`system_change`
- Parameters: none.

### WSL Toolkit > Linux configuration > Package update

- Operation id: `wsl_linux_apt_update`
- Description: Run apt/dnf package metadata update and optionally upgrade packages inside the selected WSL distro.
- Risk: kind=`dangerous`, risk_level=`system_change`
- Parameters:
  - `wsl_name` — **Distro** (type=`select`).
  - `wsl_name_override` — **Manual distro name** (type=`text`).
  - `linux_username` — **Linux user** (type=`text`).
  - `wsl_apt_upgrade` — **Upgrade** (type=`radio`, default=`none`).
    - Options: `none` — Update only; `upgrade` — Upgrade; `full-upgrade` — Full upgrade / sync
  - `wsl_apt_network_repair` — **Resilient apt network mode** (type=`checkbox`, default=true).
  - `wsl_apt_force_ipv4` — **Force IPv4 for apt** (type=`checkbox`, default=true).
  - `wsl_apt_mirror` — **Ubuntu apt mirror** (type=`select`, default=`https_archive`).
    - Options: `https_archive` — archive.ubuntu.com over HTTPS; `https_azure` — azure.archive.ubuntu.com over HTTPS; `https_kernel` — mirrors.edge.kernel.org over HTTPS; `https_yandex` — mirror.yandex.ru over HTTPS; `keep` — Keep current sources; `custom` — Custom mirror
  - `wsl_apt_custom_mirror` — **Custom apt mirror** (type=`text`).
  - `wsl_apt_retries` — **APT retries** (type=`number`, default=`4`).
  - `wsl_apt_timeout` — **APT timeout seconds** (type=`number`, default=`20`).

### WSL Toolkit > Linux configuration > Account bootstrap

- Operation id: `wsl_linux_account`
- Description: Create/update a Linux user, set password, sudo/wheel group and WSL default user.
- Risk: kind=`dangerous`, risk_level=`system_change`
- Parameters:
  - `wsl_name` — **Distro** (type=`select`).
  - `wsl_name_override` — **Manual distro name** (type=`text`).
  - `linux_username` — **Linux user** (type=`text`).
  - `linux_password` — **Password** (type=`password`).
  - `linux_set_password` — **Set password** (type=`checkbox`, default=true).
  - `linux_add_sudo` — **Add to sudo/wheel** (type=`checkbox`, default=true).
  - `linux_set_default_user` — **Set as WSL default user** (type=`checkbox`, default=true).
  - `linux_shell` — **Shell** (type=`text`, default=`/bin/bash`).

### WSL Toolkit > Linux configuration > Dev packages

- Operation id: `wsl_linux_dev_packages`
- Description: Install Audion WSL Dev packages. Heavy/Desktop packages are not selected.
- Risk: kind=`dangerous`, risk_level=`system_change`
- Parameters:
  - `wsl_name` — **Distro** (type=`select`).
  - `wsl_name_override` — **Manual distro name** (type=`text`).
  - `linux_username` — **Linux user** (type=`text`).
  - `wsl_packages_baseline` — **Baseline packages** (type=`checkboxes`, default=`[ca-certificates, curl, wget, rsync, zstd, git, git-lfs, jq, tree, ripgrep, fd-find,
  fzf, unzip, zip, 7zip, htop, btop, ncdu, mc, far2l, micro, neovim, tmux, shellcheck,
  tree-sitter-cli, build-essential, gcc, g++, make, cmake, pkg-config, python3, python3-pip,
  python3-venv, pipx, openssh-client, rclone, net-tools, nmap, traceroute]`).
  - `wsl_packages_media_cli` — **Media CLI packages** (type=`checkboxes`, default=`[]`).
  - `wsl_packages_sync` — **Sync/network packages** (type=`checkboxes`, default=`[]`).
  - `wsl_packages_lab` — **Lab/container packages** (type=`checkboxes`, default=`[]`).
  - `wsl_apt_update_first` — **Update package metadata first** (type=`checkbox`, default=true).
  - `wsl_apt_network_repair` — **Resilient apt network mode** (type=`checkbox`, default=true).
  - `wsl_apt_force_ipv4` — **Force IPv4 for apt** (type=`checkbox`, default=true).
  - `wsl_apt_mirror` — **Ubuntu apt mirror** (type=`select`, default=`https_archive`).
    - Options: `https_archive` — archive.ubuntu.com over HTTPS; `https_azure` — azure.archive.ubuntu.com over HTTPS; `https_kernel` — mirrors.edge.kernel.org over HTTPS; `https_yandex` — mirror.yandex.ru over HTTPS; `keep` — Keep current sources; `custom` — Custom mirror
  - `wsl_apt_custom_mirror` — **Custom apt mirror** (type=`text`).
  - `wsl_apt_retries` — **APT retries** (type=`number`, default=`4`).
  - `wsl_apt_timeout` — **APT timeout seconds** (type=`number`, default=`20`).
  - `wsl_install_recommends` — **Install recommended packages** (type=`checkbox`, default=false).
  - `wsl_selinux_permissive` — **Set SELinux permissive (Fedora)** (type=`checkbox`, default=false).
  - `wsl_flatpak_flathub` — **Flatpak + Flathub remote** (type=`checkbox`, default=false).
  - `wsl_optional_packages` — **Optional packages** (type=`textarea`).

### WSL Toolkit > Linux configuration > Micro baseline

- Operation id: `wsl_micro_baseline`
- Description: Install Audion micro settings and keybindings for the selected Linux user.
- Risk: kind=`dangerous`, risk_level=`user_write`
- Parameters:
  - `wsl_name` — **Distro** (type=`select`).
  - `wsl_name_override` — **Manual distro name** (type=`text`).
  - `linux_username` — **Linux user** (type=`text`).

### WSL Toolkit > Linux configuration > MC skin

- Operation id: `wsl_mc_skin`
- Description: Install Audion Midnight Commander skin and optionally set it active.
- Risk: kind=`dangerous`, risk_level=`user_write`
- Parameters:
  - `wsl_name` — **Distro** (type=`select`).
  - `wsl_name_override` — **Manual distro name** (type=`text`).
  - `linux_username` — **Linux user** (type=`text`).
  - `mc_skin` — **Skin** (type=`radio`, default=`electricblue256`).
    - Options: `electricblue256` — Electric Blue; `audion256` — Audion
  - `mc_apply_skin` — **Set as active MC skin** (type=`checkbox`, default=true).

### WSL Toolkit > Linux configuration > Neovim base

- Operation id: `wsl_neovim_base`
- Description: Install an Audion Neovim profile without AI providers.
- Risk: kind=`dangerous`, risk_level=`user_write`
- Parameters:
  - `wsl_name` — **Distro** (type=`select`).
  - `wsl_name_override` — **Manual distro name** (type=`text`).
  - `linux_username` — **Linux user** (type=`text`).
  - `nvim_appname` — **NVIM_APPNAME** (type=`text`, default=`audion-ide`).
  - `nvim_profile` — **Profile** (type=`radio`, default=`lite`).
    - Options: `lite` — Lite; `lazyvim` — LazyVim

### WSL Toolkit > Ubuntu Dev Installer Kit > Open kit folder

- Operation id: `ubuntu_dev_open_folder`
- Description: Open tools/ubuntu_dev_installer.
- Risk: kind=`safe`, risk_level=`readonly`
- Parameters: none.

### WSL Toolkit > Ubuntu Dev Installer Kit > Open README RU

- Operation id: `ubuntu_dev_open_readme_ru`
- Description: Open the Russian README for the project-local Ubuntu kit.
- Risk: kind=`safe`, risk_level=`readonly`
- Parameters: none.

### WSL Toolkit > Ubuntu Dev Installer Kit > Open Btrfs guide

- Operation id: `ubuntu_dev_open_btrfs_guide`
- Description: Open the Btrfs/Timeshift LiveUSB guide.
- Risk: kind=`safe`, risk_level=`readonly`
- Parameters: none.

### WSL Toolkit > Ubuntu Dev Installer Kit > Open installer script

- Operation id: `ubuntu_dev_open_installer_script`
- Description: Open the main Ubuntu dev installer script from the project-local kit.
- Risk: kind=`safe`, risk_level=`readonly`
- Parameters: none.

### WSL Toolkit > Ubuntu Dev Installer Kit > Open NVMe prep script

- Operation id: `ubuntu_dev_open_nvme_prep_script`
- Description: Open the Btrfs/LUKS Ubuntu LiveUSB prep script from the project-local kit.
- Risk: kind=`safe`, risk_level=`readonly`
- Parameters: none.

### WSL Toolkit > Ubuntu Dev Installer Kit > Open package lists

- Operation id: `ubuntu_dev_open_packages`
- Description: Open the package-list folder used by the kit.
- Risk: kind=`safe`, risk_level=`readonly`
- Parameters: none.

### WSL Toolkit > Distro actions > Terminate distro

- Operation id: `wsl_terminate`
- Description: Terminate the selected WSL distribution.
- Risk: kind=`dangerous`, risk_level=`system_change`
- Parameters:
  - `wsl_name` — **Distro** (type=`select`).
  - `wsl_name_override` — **Manual distro name** (type=`text`).

### WSL Toolkit > Distro actions > Backup distro

- Operation id: `wsl_backup`
- Description: Export selected distribution as tar or vhd.
- Risk: kind=`dangerous`, risk_level=`secret_export`
- Parameters:
  - `wsl_name` — **Distro** (type=`select`).
  - `wsl_name_override` — **Manual distro name** (type=`text`).
  - `format` — **Format** (type=`radio`, default=`tar`).
    - Options: `tar` — tar; `vhd` — vhd
  - `backup_dir` — **Backup folder override** (type=`folder`).

### WSL Toolkit > Distro actions > Clone distro

- Operation id: `wsl_clone`
- Description: Export selected distro and import it under a new name.
- Risk: kind=`dangerous`, risk_level=`system_change`
- Parameters:
  - `wsl_name` — **Distro** (type=`select`).
  - `wsl_name_override` — **Manual distro name** (type=`text`).
  - `new_name` — **New name** (type=`text`).
  - `location` — **Install location** (type=`folder`).
  - `backup_dir` — **Temp backup folder** (type=`folder`).

### WSL Toolkit > Distro actions > Move distro

- Operation id: `wsl_move`
- Description: Move the selected distro through export/import.
- Risk: kind=`dangerous`, risk_level=`destructive`
- Parameters:
  - `wsl_name` — **Distro** (type=`select`).
  - `wsl_name_override` — **Manual distro name** (type=`text`).
  - `location` — **New install location** (type=`folder`).
  - `backup_dir` — **Temp backup folder** (type=`folder`).

### WSL Toolkit > Distro actions > Delete distro

- Operation id: `wsl_delete`
- Description: Permanently unregister the selected WSL distribution.
- Risk: kind=`dangerous`, risk_level=`destructive`
- Parameters:
  - `wsl_name` — **Distro** (type=`select`).
  - `wsl_name_override` — **Manual distro name** (type=`text`).

### WSL Toolkit > Import and restore > Import VHDX in place

- Operation id: `wsl_import_in_place`
- Description: Register an existing ext4.vhdx as a WSL distribution.
- Risk: kind=`dangerous`, risk_level=`system_change`
- Parameters:
  - `wsl_name_override` — **Distro name** (type=`text`).
  - `vhdx_path` — **VHDX file** (type=`select`).
  - `vhdx_path_manual` — **Manual VHDX file** (type=`file`).

### WSL Toolkit > Import and restore > Restore from backup

- Operation id: `wsl_restore_from_backup`
- Description: Import a tar/vhd/vhdx backup as a WSL distribution.
- Risk: kind=`dangerous`, risk_level=`system_change`
- Parameters:
  - `wsl_name_override` — **Distro name** (type=`text`).
  - `location` — **Install location** (type=`folder`).
  - `backup_file` — **Backup file** (type=`select`).
  - `backup_file_manual` — **Manual backup file** (type=`file`).

### WSL Toolkit > Register VHDX batch > Register all VHDX

- Operation id: `wsl_register_all_vhdx`
- Description: Non-interactive batch import-in-place. Dry-run is enabled by default; existing distro names are skipped.
- Risk: kind=`dangerous`, risk_level=`system_change`
- Parameters:
  - `register_root` — **VHDX root** (type=`folder`).
  - `filter` — **File filter** (type=`text`, default=`ext4.vhdx`).
  - `dry_run` — **Dry run** (type=`checkbox`, default=true).

### Virtualization > Virtualization status

- Operation id: `virt_status`
- Description: Show hypervisorlaunchtype, Hyper-V/VMPlatform/WHP/Sandbox/WSL feature state, VBS/Core Isolation, and the interpreted current mode.
- Risk: kind=`safe`, risk_level=`readonly`
- Parameters: none.

### Virtualization > Optimization status

- Operation id: `virt_optimization_status`
- Description: Read-only check of what slows VM/WSL: Core Isolation/VBS, active power plan, Defender exclusions for WSL/VM paths, .wslconfig presence and WSL VHDX placement.
- Risk: kind=`safe`, risk_level=`readonly`
- Parameters: none.

### Virtualization > Mode: Hyper-V / WSL2

- Operation id: `virt_mode_hyperv`
- Description: Set hypervisorlaunchtype=Auto and enable VirtualMachinePlatform. Hyper-V/WSL2/Sandbox work; third-party VMs run only via WHP or fail. Backup: backup\virtualization. Needs reboot.
- Risk: kind=`dangerous`, risk_level=`system_change`
- Parameters: none.

### Virtualization > Mode: Third-party fast

- Operation id: `virt_mode_thirdparty`
- Description: Set hypervisorlaunchtype=Off. VMware/VirtualBox run at full speed; WSL2/Hyper-V/Sandbox stop until you switch back. If VBS/Core Isolation is on, VT-x can still be held. Backup: backup\virtualization. Needs reboot.
- Risk: kind=`dangerous`, risk_level=`system_change`
- Parameters: none.

### Virtualization > Mode: Coexist (WHP)

- Operation id: `virt_mode_coexist`
- Description: Keep hypervisorlaunchtype=Auto and enable Windows Hypervisor Platform + VirtualMachinePlatform so modern VMware/VirtualBox run alongside Hyper-V/WSL2 (slower). Backup: backup\virtualization. Needs reboot.
- Risk: kind=`dangerous`, risk_level=`system_change`
- Parameters: none.

### Virtualization > Enable Hyper-V

- Operation id: `virt_hyperv_enable`
- Description: Enable Microsoft-Hyper-V-All (Hyper-V Manager + platform) and set hypervisorlaunchtype=Auto. Backup: backup\virtualization. Needs reboot.
- Risk: kind=`dangerous`, risk_level=`system_change`
- Parameters: none.

### Virtualization > Disable Hyper-V

- Operation id: `virt_hyperv_disable`
- Description: Disable Microsoft-Hyper-V-All. To give third-party VMs full speed also use Mode: Third-party fast (hypervisorlaunchtype=Off). Backup: backup\virtualization. Needs reboot.
- Risk: kind=`dangerous`, risk_level=`system_change`
- Parameters: none.

### Virtualization > Enable Windows Sandbox

- Operation id: `virt_sandbox_enable`
- Description: Enable Containers-DisposableClientVM (Windows Sandbox). Requires the hypervisor (Hyper-V/WSL2 mode). Backup: backup\virtualization. Needs reboot.
- Risk: kind=`dangerous`, risk_level=`system_change`
- Parameters: none.

### Virtualization > Disable Windows Sandbox

- Operation id: `virt_sandbox_disable`
- Description: Disable Containers-DisposableClientVM (Windows Sandbox). Backup: backup\virtualization. Needs reboot.
- Risk: kind=`dangerous`, risk_level=`system_change`
- Parameters: none.

### Hosts and Bitrix > Detect current endpoint

- Operation id: `bitrix_detect_endpoint`
- Description: DNS-only lookup ignores stale hosts entries, accepts only local/private IPs, scans candidate ports and fills IP/port fields without changing hosts.
- Risk: kind=`safe`, risk_level=`readonly`
- Parameters:
  - `hosts_presets` — **Pins** (type=`profile_buttons`).
  - `host_name` — **Host name** (type=`text`, default=`portal.itpgrad.ru`).
  - `ip_address` — **IP address** (type=`text`, default=`192.168.0.130`).
  - `bitrix_ports` — **Custom TCP ports** (type=`text`, default=`443`).
  - `bitrix_auto_scan_ports` — **Auto-scan open ports** (type=`checkbox`, default=true).
  - `bitrix_port_scan_candidates` — **Port scan candidates** (type=`text`, default=`80,443,8080,8443,8890,8891,8892`).

### Hosts and Bitrix > Status / DNS / ports

- Operation id: `bitrix_status`
- Description: Show hosts override, effective resolved IP, DNS answer, auto-scanned ports and TCP checks.
- Risk: kind=`safe`, risk_level=`readonly`
- Parameters:
  - `hosts_presets` — **Pins** (type=`profile_buttons`).
  - `host_name` — **Host name** (type=`text`, default=`portal.itpgrad.ru`).
  - `ip_address` — **IP address** (type=`text`, default=`192.168.0.130`).
  - `bitrix_ports` — **Custom TCP ports** (type=`text`, default=`443`).
  - `bitrix_auto_scan_ports` — **Auto-scan open ports** (type=`checkbox`, default=true).
  - `bitrix_port_scan_candidates` — **Port scan candidates** (type=`text`, default=`80,443,8080,8443,8890,8891,8892`).

### Hosts and Bitrix > Enable override

- Operation id: `bitrix_enable`
- Description: Apply hosts override for selected host and IP; detected/custom ports are saved in the managed hosts comment.
- Risk: kind=`dangerous`, risk_level=`system_change`
- Parameters:
  - `hosts_presets` — **Pins** (type=`profile_buttons`).
  - `host_name` — **Host name** (type=`text`, default=`portal.itpgrad.ru`).
  - `ip_address` — **IP address** (type=`text`, default=`192.168.0.130`).
  - `bitrix_ports` — **Custom TCP ports** (type=`text`, default=`443`).
  - `bitrix_auto_scan_ports` — **Auto-scan open ports** (type=`checkbox`, default=true).
  - `bitrix_port_scan_candidates` — **Port scan candidates** (type=`text`, default=`80,443,8080,8443,8890,8891,8892`).

### Hosts and Bitrix > Disable override

- Operation id: `bitrix_disable`
- Description: Bitwise depatch: restore the exact pre-patch hosts backup referenced by the managed hosts line.
- Risk: kind=`dangerous`, risk_level=`system_change`
- Parameters:
  - `hosts_presets` — **Pins** (type=`profile_buttons`).
  - `host_name` — **Host name** (type=`text`, default=`portal.itpgrad.ru`).
  - `ip_address` — **IP address** (type=`text`, default=`192.168.0.130`).
  - `bitrix_ports` — **Custom TCP ports** (type=`text`, default=`443`).
  - `bitrix_auto_scan_ports` — **Auto-scan open ports** (type=`checkbox`, default=true).
  - `bitrix_port_scan_candidates` — **Port scan candidates** (type=`text`, default=`80,443,8080,8443,8890,8891,8892`).

### Hosts and Bitrix > Restore original hosts

- Operation id: `bitrix_restore`
- Description: Restore hosts from the latest pre-patch backup when an explicit managed-line depatch is not available.
- Risk: kind=`dangerous`, risk_level=`system_change`
- Parameters:
  - `hosts_presets` — **Pins** (type=`profile_buttons`).
  - `host_name` — **Host name** (type=`text`, default=`portal.itpgrad.ru`).
  - `ip_address` — **IP address** (type=`text`, default=`192.168.0.130`).
  - `bitrix_ports` — **Custom TCP ports** (type=`text`, default=`443`).
  - `bitrix_auto_scan_ports` — **Auto-scan open ports** (type=`checkbox`, default=true).
  - `bitrix_port_scan_candidates` — **Port scan candidates** (type=`text`, default=`80,443,8080,8443,8890,8891,8892`).

### Default apps and Microsoft apps > Policy

- Operation id: `default_apps_policy`
- Description: Save the current set of default programs and make Windows restore it at every sign-in.
- Risk: kind=`dangerous`, risk_level=`system_change`
- Parameters:
  - `policy_action` — **Action** (type=`radio`, default=`status`).
    - Options: `status` — Check - show what opens what; `snapshot` — Save a snapshot of the current state; `export` — Make the current state the reference; `import` — Take the reference from a file; `apply` — Enable / repair the protection; `remove` — Turn the protection off; `cleanup` — Prune old backups; `open_profiles` — Open the reference folder; `open_policy` — Open the active policy folder; `open_backups` — Open the backup folder
  - `profile_xml` — **Reference file** (type=`file`, default=`profiles\default_apps\AppAssociations.xml`).
  - `import_backup_xml` — **Saved snapshot** (type=`select`, default=``).
  - `import_profile_xml` — **File from another machine** (type=`file`, default=``).
  - `strip_suggested` — **Enforce hard** (type=`checkbox`, default=true).
  - `backup_label` — **Backup label** (type=`text`, default=``).
  - `check_identifiers` — **Tracked file types** (type=`checkboxes`, default=`[http, https, .htm, .html, .pdf, .txt, .md, .rtf, .doc, .docx, .xls, .xlsx, .ppt,
  .pptx, .zip, .7z, .rar, .tar, .gz, .jpg, .jpeg, .png, .webp, .gif, .bmp, .tif, .tiff,
  .svg, .avif, .heic, .psd, .mp4, .mkv, .webm, .avi, .mov, .mxf, .mp3, .flac, .wav,
  .m4a, .aac, .ogg, .opus, .alac, .m3u, .m3u8, .pls]`).
    - Options: `http` — http; `https` — https; `.htm` — .htm; `.html` — .html; `.pdf` — .pdf; `.txt` — .txt; `.md` — .md; `.rtf` — .rtf; `.doc` — .doc; `.docx` — .docx; `.xls` — .xls; `.xlsx` — .xlsx; `.ppt` — .ppt; `.pptx` — .pptx; `.zip` — .zip; `.7z` — .7z; `.rar` — .rar; `.tar` — .tar; `.gz` — .gz; `.jpg` — .jpg; `.jpeg` — .jpeg; `.png` — .png; `.webp` — .webp; `.gif` — .gif; `.bmp` — .bmp; `.tif` — .tif; `.tiff` — .tiff; `.svg` — .svg; `.avif` — .avif; `.heic` — .heic; `.psd` — .psd; `.mp4` — .mp4; `.mkv` — .mkv; `.webm` — .webm; `.avi` — .avi; `.mov` — .mov; `.mxf` — .mxf; `.mp3` — .mp3; `.flac` — .flac; `.wav` — .wav; `.m4a` — .m4a; `.aac` — .aac; `.ogg` — .ogg; `.opus` — .opus; `.alac` — .alac; `.m3u` — .m3u; `.m3u8` — .m3u8; `.pls` — .pls
  - `extra_identifiers` — **Extra file types** (type=`text`, default=``).
  - `include_dism_inventory` — **Full Windows list** (type=`checkbox`, default=false).
  - `remove_policy_xml` — **Also delete the active file** (type=`checkbox`, default=false).
  - `allow_unsupported_policy_edition` — **Allow unsupported edition** (type=`checkbox`, default=false).
  - `program_data_dir` — **Policy folder** (type=`folder`, default=`%ProgramData%\Audion\DefaultApps`).
  - `backup_dir` — **Backup folder** (type=`folder`, default=`backup\default_apps`).
  - `backup_retention_days` — **Keep backups, days** (type=`number`, default=`30`).
  - `cleanup_dry_run` — **Cleanup dry run** (type=`checkbox`, default=true).

### Default apps and Microsoft apps > Microsoft

- Operation id: `default_apps_microsoft`
- Description: Remove or bring back the built-in Microsoft apps, and keep the decision valid after Windows updates.
- Risk: kind=`dangerous`, risk_level=`system_change`
- Parameters:
  - `apps_action` — **Action** (type=`radio`, default=`status`).
    - Options: `status` — Check - what is installed; `remove` — Remove selected apps; `keep_removed` — Remove and keep them removed; `restore` — Bring the apps back; `provision` — Repair for new profiles only; `allow_back` — Stop holding them removed; `rearm_check` — Run the re-apply check now; `open_logs` — Open the guard folder
  - `apps` — **Applications** (type=`checkboxes`, default=`[ZuneMusic, ZuneVideo]`).
    - Options: `ZuneMusic` — Media Player (Zune); `ZuneVideo` — Films & TV (Zune); `Photos` — Photos; `Clipchamp` — Clipchamp; `SoundRecorder` — Sound Recorder; `Camera` — Camera (used by scanners and QR flows); `Paint` — Paint (default for many image edits); `ScreenSketch` — Snipping Tool (Win+Shift+S); `GamingApp` — Xbox; `XboxGamingOverlay` — Xbox Game Bar; `XboxSpeechToTextOverlay` — Xbox speech overlay; `XboxIdentityProvider` — Xbox Identity Provider (games sign-in); `SolitaireCollection` — Solitaire Collection; `YourPhone` — Phone Link; `People` — People; `Teams` — Microsoft Teams; `OutlookForWindows` — Outlook for Windows; `BingNews` — News; `BingWeather` — Weather; `Getstarted` — Tips; `FeedbackHub` — Feedback Hub; `WindowsMaps` — Maps; `Copilot` — Copilot; `StickyNotes` — Sticky Notes; `Todos` — To Do; `OneNote` — OneNote for Windows; `Whiteboard` — Whiteboard; `PowerAutomateDesktop` — Power Automate; `QuickAssist` — Quick Assist (remote help); `DevHome` — Dev Home; `Family` — Microsoft Family
  - `dry_run` — **Dry run** (type=`checkbox`, default=true).

### Default apps and Microsoft apps > Edge

- Operation id: `default_apps_edge`
- Description: Keep Edge, but stop it from claiming links and file types that belong to another browser.
- Risk: kind=`dangerous`, risk_level=`system_change`
- Parameters:
  - `edge_owned_now` — **Что сейчас закреплено за Edge** (type=`info_badges`).
  - `edge_action` — **Action** (type=`radio`, default=`status`).
    - Options: `status` — Check - what Edge is allowed to do; `apply` — Stop Edge from claiming associations; `revert` — Give Edge its freedom back; `webview2` — Repair WebView2 Runtime
  - `edge_level` — **How far to go** (type=`radio`, default=`calm`).
    - Options: `calm` — Calm - stop the nagging and the background; `quiet` — Quiet - also turn off side panels and extras
  - `dry_run` — **Dry run** (type=`checkbox`, default=true).

### Default apps and Microsoft apps > Tracking

- Operation id: `default_apps_watch`
- Description: Track association changes and manage the Audion Defender exclusions.
- Risk: kind=`dangerous`, risk_level=`system_change`
- Parameters:
  - `guard_action` — **Action** (type=`radio`, default=`status`).
    - Options: `status` — Check; `enable` — Turn on; `disable` — Turn off; `run_check` — Check the defaults right now
  - `guard_targets` — **Targets** (type=`checkboxes`, default=`[Drift]`).
    - Options: `Drift` — Association change tracking; `Defender` — Defender exclusions for Audion folders

### Default apps and Microsoft apps > Snapshot

- Operation id: `default_apps_snapshot`
- Description: Save and compare the association map of the current user.
- Risk: kind=`dangerous`, risk_level=`user_write`
- Parameters:
  - `snapshot_action` — **Action** (type=`radio`, default=`status`).
    - Options: `status` — Compare the snapshot with what you have now; `capture` — Save the current associations; `open_snapshots` — Open the snapshot folder
  - `snapshot_name` — **Snapshot name** (type=`text`, default=`Microsoft Snapshot`).
  - `snapshot_machine` — **Machine tag** (type=`text`, default=``).
  - `dry_run` — **Dry run** (type=`checkbox`, default=true).

### Default apps and Microsoft apps > Groups

- Operation id: `default_apps_groups`
- Description: Capture associations group by group while the right apps are installed.
- Risk: kind=`dangerous`, risk_level=`user_write`
- Parameters:
  - `group_action` — **Action** (type=`radio`, default=`status`).
    - Options: `status` — Check the groups; `commit` — Save the selected group; `compose` — Build one snapshot from the groups
  - `group_name` — **Group** (type=`radio`, default=`photo`).
    - Options: `photo` — Photo; `audio` — Audio; `video` — Video; `pdf` — PDF and books; `documents` — Documents; `archives` — Archives; `browser` — Browser; `custom` — Custom
  - `group_custom_name` — **Custom group name** (type=`text`, default=``).
  - `group_ext` — **Custom extensions** (type=`text`, default=``).
  - `snapshot_name` — **Snapshot name** (type=`text`, default=`Microsoft Snapshot`).
  - `snapshot_machine` — **Machine tag** (type=`text`, default=``).
  - `dry_run` — **Dry run** (type=`checkbox`, default=true).

### Default apps and Microsoft apps > Full report

- Operation id: `default_apps_overview`
- Description: Run every read-only check in this section at once.
- Risk: kind=`safe`, risk_level=`readonly`
- Parameters: none.

### Hardware > Driver/Firmware Audit

- Operation id: `driver_firmware_audit`
- Description: Read-only Windows diagnostic report for problem devices, BIOS/EC, firmware resources and key signed drivers.
- Risk: kind=`safe`, risk_level=`project_write`
- Parameters:
  - `output_dir` — **Output folder** (type=`folder`, default=`logs`).
  - `json` — **Write JSON** (type=`checkbox`, default=true).
  - `csv` — **Write key-driver CSV** (type=`checkbox`, default=true).
  - `open_report` — **Open report in Notepad** (type=`checkbox`, default=false).

### Hardware > Driver/Firmware Audit materials > Open addon folder

- Operation id: `driver_firmware_audit_open_folder`
- Description: Open tools/driver_firmware_audit.
- Risk: kind=`safe`, risk_level=`readonly`
- Parameters: none.

### Hardware > Driver/Firmware Audit materials > Open README

- Operation id: `driver_firmware_audit_open_readme`
- Description: Open the addon README from the project-local copy.
- Risk: kind=`safe`, risk_level=`readonly`
- Parameters: none.

### Hardware > Driver Update Blocker > Windows Update driver policy > Check driver protection

- Operation id: `driver_update_status`
- Description: Read-only status: Windows Update driver policy, driver-search settings, device metadata policy, DeviceInstall restrictions, and present NVIDIA PCI devices.
- Risk: kind=`safe`, risk_level=`readonly`
- Parameters: none.

### Hardware > Driver Update Blocker > Windows Update driver policy > Block Windows Update drivers

- Operation id: `driver_update_block_all`
- Description: Backs up current policy keys, sets ExcludeWUDriversInQualityUpdate=1, disables driver-wizard WU search and device metadata downloads, then runs gpupdate. Reboot is recommended.
- Risk: kind=`dangerous`, risk_level=`system_change`
- Parameters: none.

### Hardware > Driver Update Blocker > Windows Update driver policy > Unblock Windows Update drivers

- Operation id: `driver_update_unblock_all`
- Description: Backs up current policy keys, removes the Windows Update driver block values, restores normal driver-search behavior, then runs gpupdate. Reboot is recommended.
- Risk: kind=`dangerous`, risk_level=`system_change`
- Parameters: none.

### Hardware > Driver Update Blocker > Windows Update driver policy > Open policy backups

- Operation id: `driver_update_open_policy_backups`
- Description: Open registry-policy backup files created before block/unblock operations.
- Risk: kind=`safe`, risk_level=`readonly`
- Parameters: none.

### Hardware > Driver Update Blocker > Device driver HWID guard > Check current lock

- Operation id: `hwid_driver_status`
- Description: Read-only check: shows whether this HWID is locked and which driver is currently best-ranked/installed.
- Risk: kind=`safe`, risk_level=`readonly`
- Parameters:
  - `hwid_builtin_cache_pins` — **Preset** (type=`profile_buttons`).
  - `hwid_guard_identity_badges` — **Driver identity** (type=`info_badges`).
  - `target_hardware_ids` — **HWID to protect** (type=`textarea`, default=`PCI\VEN_8086&DEV_46A8&SUBSYS_22E717AA
`).
  - `target_device_instance_id` — **Device Instance ID** (type=`text`).
  - `hwid_retroactive` — **Retroactive block** (type=`checkbox`, default=false).
  - `hwid_keep_global_wu_block` — **Keep global WU driver block** (type=`checkbox`, default=false).

### Hardware > Driver Update Blocker > Device driver HWID guard > 1. Unblock before driver update

- Operation id: `hwid_driver_unblock`
- Description: Use before installing the wanted manual/generic driver. Removes matching HWID locks while preserving unrelated policy entries.
- Risk: kind=`dangerous`, risk_level=`system_change`
- Parameters:
  - `hwid_builtin_cache_pins` — **Preset** (type=`profile_buttons`).
  - `hwid_guard_identity_badges` — **Driver identity** (type=`info_badges`).
  - `target_hardware_ids` — **HWID to protect** (type=`textarea`, default=`PCI\VEN_8086&DEV_46A8&SUBSYS_22E717AA
`).
  - `target_device_instance_id` — **Device Instance ID** (type=`text`).
  - `hwid_retroactive` — **Retroactive block** (type=`checkbox`, default=false).
  - `hwid_keep_global_wu_block` — **Keep global WU driver block** (type=`checkbox`, default=false).

### Hardware > Driver Update Blocker > Device driver HWID guard > 2. Block after driver install

- Operation id: `hwid_driver_block`
- Description: Use after the wanted driver is installed and active. Adds this HWID to DenyDeviceIDs so Windows Driver Store/WU cannot replace it silently.
- Risk: kind=`dangerous`, risk_level=`system_change`
- Parameters:
  - `hwid_builtin_cache_pins` — **Preset** (type=`profile_buttons`).
  - `hwid_guard_identity_badges` — **Driver identity** (type=`info_badges`).
  - `target_hardware_ids` — **HWID to protect** (type=`textarea`, default=`PCI\VEN_8086&DEV_46A8&SUBSYS_22E717AA
`).
  - `target_device_instance_id` — **Device Instance ID** (type=`text`).
  - `hwid_retroactive` — **Retroactive block** (type=`checkbox`, default=false).
  - `hwid_keep_global_wu_block` — **Keep global WU driver block** (type=`checkbox`, default=false).

### Hardware > Driver Update Blocker > Emergency rank repair by HWID > Check rank target

- Operation id: `hwid_driver_rank_status`
- Description: Read-only target check: resolves the device by HWID, shows current signed driver data and pnputil driver/rank report.
- Risk: kind=`safe`, risk_level=`readonly`
- Parameters:
  - `hwid_builtin_cache_pins` — **Preset** (type=`profile_buttons`).
  - `hwid_repair_identity_badges` — **Repair markers** (type=`info_badges`).
  - `target_hardware_ids` — **HWID to repair** (type=`textarea`, default=`PCI\VEN_8086&DEV_46A8&SUBSYS_22E717AA
`).
  - `target_device_instance_id` — **Device Instance ID** (type=`text`).
  - `bad_driver_version` — **Bad driver version** (type=`text`, default=`32.0.101.7026`).
  - `target_driver_version` — **Target driver version** (type=`text`, default=`32.0.101.7085`).
  - `target_inf_name_pattern` — **Target INF pattern** (type=`text`, default=`*.inf`).
  - `target_inf_path` — **Target INF path** (type=`text`).
  - `driver_rank_class` — **Driver class** (type=`text`, default=`Display`).
  - `skip_current_version_check` — **Skip current version check** (type=`checkbox`, default=false).
  - `allow_version_only_target_inf_fallback` — **Allow version-only INF fallback** (type=`checkbox`, default=false).
  - `no_policy_block_after_repair` — **Do not block HWID after repair** (type=`checkbox`, default=false).
  - `hwid_keep_global_wu_block` — **Keep global WU driver block** (type=`checkbox`, default=false).

### Hardware > Driver Update Blocker > Emergency rank repair by HWID > Repair driver rank by HWID

- Operation id: `hwid_driver_rank_repair`
- Description: Creates a REG/JSON preflight backup, exports the old package, removes the bad current INF package, installs the target INF, rescans/restarts the device, then applies the targeted HWID block. Use only after checking the target.
- Risk: kind=`dangerous`, risk_level=`system_change`
- Parameters:
  - `hwid_builtin_cache_pins` — **Preset** (type=`profile_buttons`).
  - `hwid_repair_identity_badges` — **Repair markers** (type=`info_badges`).
  - `target_hardware_ids` — **HWID to repair** (type=`textarea`, default=`PCI\VEN_8086&DEV_46A8&SUBSYS_22E717AA
`).
  - `target_device_instance_id` — **Device Instance ID** (type=`text`).
  - `bad_driver_version` — **Bad driver version** (type=`text`, default=`32.0.101.7026`).
  - `target_driver_version` — **Target driver version** (type=`text`, default=`32.0.101.7085`).
  - `target_inf_name_pattern` — **Target INF pattern** (type=`text`, default=`*.inf`).
  - `target_inf_path` — **Target INF path** (type=`text`).
  - `driver_rank_class` — **Driver class** (type=`text`, default=`Display`).
  - `skip_current_version_check` — **Skip current version check** (type=`checkbox`, default=false).
  - `allow_version_only_target_inf_fallback` — **Allow version-only INF fallback** (type=`checkbox`, default=false).
  - `no_policy_block_after_repair` — **Do not block HWID after repair** (type=`checkbox`, default=false).
  - `hwid_keep_global_wu_block` — **Keep global WU driver block** (type=`checkbox`, default=false).

### Hardware > Driver Update Blocker > NVIDIA driver install restrictions > Block NVIDIA driver installs

- Operation id: `nvidia_driver_block`
- Description: Detects present NVIDIA PCI devices, writes their Hardware IDs into Device Installation Restrictions and runs gpupdate. Use before trusting a known-good manual/NVCleanstall driver.
- Risk: kind=`dangerous`, risk_level=`system_change`
- Parameters:
  - `include_compatible_ids` — **Include compatible IDs** (type=`checkbox`, default=false).
  - `nvidia_retroactive` — **Retroactive block** (type=`checkbox`, default=false).

### Hardware > Driver Update Blocker > NVIDIA driver install restrictions > Unblock NVIDIA driver installs

- Operation id: `nvidia_driver_unblock`
- Description: Removes NVIDIA PCI IDs from Device Installation Restrictions while preserving non-NVIDIA entries in the same policy lists.
- Risk: kind=`dangerous`, risk_level=`system_change`
- Parameters:
  - `include_compatible_ids` — **Include compatible IDs** (type=`checkbox`, default=false).
  - `nvidia_retroactive` — **Retroactive block** (type=`checkbox`, default=false).

### Hardware > Driver Update Blocker > Driver Store backups > Save Driver Store manifest

- Operation id: `driver_store_manifest`
- Description: Saves pnputil, systeminfo and Get-WindowsDriver reports without exporting driver packages.
- Risk: kind=`safe`, risk_level=`readonly`
- Parameters:
  - `driver_backup_select` — **Driver backup** (type=`select`).
  - `driver_backup_path` — **Manual backup folder** (type=`folder`).

### Hardware > Driver Update Blocker > Driver Store backups > Export installed drivers

- Operation id: `driver_store_export`
- Description: Exports currently staged third-party drivers from Driver Store into a timestamped backup folder using Export-WindowsDriver or DISM fallback.
- Risk: kind=`safe`, risk_level=`project_write`
- Parameters:
  - `driver_backup_select` — **Driver backup** (type=`select`).
  - `driver_backup_path` — **Manual backup folder** (type=`folder`).

### Hardware > Driver Update Blocker > Driver Store backups > Restore exported drivers

- Operation id: `driver_store_restore`
- Description: Runs pnputil /add-driver on the selected backup without interactive prompts. Use backups from the same machine or a very similar hardware profile.
- Risk: kind=`dangerous`, risk_level=`system_change`
- Parameters:
  - `driver_backup_select` — **Driver backup** (type=`select`).
  - `driver_backup_path` — **Manual backup folder** (type=`folder`).

### Hardware > Driver Update Blocker > Driver Store backups > Open driver backups

- Operation id: `driver_store_open_backups`
- Description: Open the exported driver backup folder.
- Risk: kind=`safe`, risk_level=`readonly`
- Parameters:
  - `driver_backup_select` — **Driver backup** (type=`select`).
  - `driver_backup_path` — **Manual backup folder** (type=`folder`).

### Hardware > Driver Update Blocker > Open Driver Update Blocker folder

- Operation id: `driver_update_open_tool`
- Description: Open the project-local PowerShell module folder used by the GUI and project launchers.
- Risk: kind=`safe`, risk_level=`readonly`
- Parameters: none.

### Hardware > NVIDIA HDMI/DP Audio > NVIDIA audio status

- Operation id: `nvidia_audio_status`
- Description: Read-only status: matching NVIDIA HDMI/DP audio devices, selected HDAUDIO Hardware IDs and current DeviceInstall policy entries.
- Risk: kind=`safe`, risk_level=`readonly`
- Parameters: none.

### Hardware > NVIDIA HDMI/DP Audio > Export NVIDIA audio IDs

- Operation id: `nvidia_audio_export_ids`
- Description: Writes device details and policy-block candidate IDs to the original tool output folder.
- Risk: kind=`safe`, risk_level=`readonly`
- Parameters: none.

### Hardware > NVIDIA HDMI/DP Audio > Disable NVIDIA HDMI/DP audio

- Operation id: `nvidia_audio_disable`
- Description: Disables currently installed matching NVIDIA HDMI/DP audio devices through Disable-PnpDevice. It does not remove normal audio interfaces.
- Risk: kind=`dangerous`, risk_level=`system_change`
- Parameters: none.

### Hardware > NVIDIA HDMI/DP Audio > Enable NVIDIA HDMI/DP audio

- Operation id: `nvidia_audio_enable`
- Description: Enables matching NVIDIA HDMI/DP audio devices again. If policy block remains active, unblock policy first.
- Risk: kind=`dangerous`, risk_level=`system_change`
- Parameters: none.

### Hardware > NVIDIA HDMI/DP Audio > Block NVIDIA HDMI/DP audio policy

- Operation id: `nvidia_audio_block_policy`
- Description: Backs up DeviceInstall policy, adds only NVIDIA HDAUDIO codec IDs to DenyDeviceIDs, disables matching devices and rescans PnP.
- Risk: kind=`dangerous`, risk_level=`system_change`
- Parameters: none.

### Hardware > NVIDIA HDMI/DP Audio > Unblock NVIDIA HDMI/DP audio policy

- Operation id: `nvidia_audio_unblock_policy`
- Description: Removes known NVIDIA HDAUDIO IDs from DeviceInstall policy, rescans PnP and tries to enable matching devices.
- Risk: kind=`dangerous`, risk_level=`system_change`
- Parameters: none.

### Hardware > NVIDIA HDMI/DP Audio > Open NVIDIA audio output

- Operation id: `nvidia_audio_open_output`
- Description: Open the output folder with exported NVIDIA HDMI/DP audio device IDs.
- Risk: kind=`safe`, risk_level=`readonly`
- Parameters: none.

### Hardware > NVIDIA HDMI/DP Audio > Open NVIDIA audio backup

- Operation id: `nvidia_audio_open_backup`
- Description: Open DeviceInstall policy backups created before NVIDIA audio policy changes.
- Risk: kind=`safe`, risk_level=`readonly`
- Parameters: none.

### Hardware > NVIDIA HDMI/DP Audio > Open NVIDIA audio tool folder

- Operation id: `nvidia_audio_open_tool`
- Description: Open the project-local NVIDIA HDMI/DP Audio module folder used by the GUI and project launchers.
- Risk: kind=`safe`, risk_level=`readonly`
- Parameters: none.

### Hardware > Storage / Disk procedures > Disk and volume inventory

- Operation id: `storage_inventory`
- Description: Read-only Get-Disk/Get-Volume summary: disk numbers, sizes, volume letters, filesystem and health.
- Risk: kind=`safe`, risk_level=`readonly`
- Parameters: none.

### Hardware > Storage / Disk procedures > Selected disk details

- Operation id: `storage_disk_details`
- Description: Read-only disk and partition layout for the selected disk number before manual storage work.
- Risk: kind=`safe`, risk_level=`readonly`
- Parameters:
  - `disk_number` — **Disk** (type=`select`).

### Hardware > Storage / Disk procedures > Launch SSD/NVMe wizard

- Operation id: `storage_ssd_reset_wizard`
- Description: Open the original wizard in an external console; destructive actions still require its own typed confirmations.
- Risk: kind=`dangerous`, risk_level=`destructive`
- Parameters: none.

### Hardware > Storage / Disk procedures > Open SSD/NVMe folder

- Operation id: `storage_ssd_open_folder`
- Description: Open the SSD/NVMe wizard folder with README, logs and original scripts; no disk changes.
- Risk: kind=`safe`, risk_level=`readonly`
- Parameters: none.

### Hardware > Storage / Disk procedures > WinRE layout status

- Operation id: `storage_winre_status`
- Description: Read-only reagentc and OS disk layout check: shows active WinRE location and adjacent partitions.
- Risk: kind=`safe`, risk_level=`readonly`
- Parameters: none.

### Hardware > Storage / Disk procedures > Run WinRE extend wizard

- Operation id: `storage_winre_wizard`
- Description: Disable WinRE, delete the recovery partition to the right of C:, and extend C: after project confirmation.
- Risk: kind=`dangerous`, risk_level=`destructive`
- Parameters:
  - `winre_typed_confirm` — **Typed confirmation** (type=`text`).

### OpenSSH KeyKit > Check access links

- Operation id: `ssh_keykit_check_links`
- Description: Read ssh and rclone configuration and report every key, known_hosts and proxy path that no longer exists.
- Risk: kind=`safe`, risk_level=`readonly`
- Parameters:
  - `ssh_root` — **Keys folder** (type=`folder`, default=``).
  - `profile_name` — **Machine/profile name** (type=`text`, default=``).
  - `user_name` — **Windows user** (type=`text`, default=``).
  - `ssh_config_path` — **ssh config to check** (type=`file`, default=``).
  - `rclone_config_path` — **rclone config to check** (type=`file`, default=``).
  - `links_report_path` — **Save report to CSV** (type=`text`, default=``).
  - `fail_on_broken` — **Fail when a path is missing** (type=`checkbox`, default=true).
  - `snapshot` — **Snapshot for import** (type=`text`, default=``).

### OpenSSH KeyKit > Export client SSH keys

- Operation id: `ssh_keykit_export_client`
- Description: Export current user's .ssh keys/config/known_hosts/authorized_keys into output\ssh_keykit.
- Risk: kind=`dangerous`, risk_level=`secret_export`
- Parameters:
  - `ssh_root` — **Keys folder** (type=`folder`, default=``).
  - `profile_name` — **Machine/profile name** (type=`text`, default=``).
  - `user_name` — **Windows user** (type=`text`, default=``).
  - `ssh_config_path` — **ssh config to check** (type=`file`, default=``).
  - `rclone_config_path` — **rclone config to check** (type=`file`, default=``).
  - `links_report_path` — **Save report to CSV** (type=`text`, default=``).
  - `fail_on_broken` — **Fail when a path is missing** (type=`checkbox`, default=true).
  - `snapshot` — **Snapshot for import** (type=`text`, default=``).

### OpenSSH KeyKit > Export client + server SSH keys

- Operation id: `ssh_keykit_export_all`
- Description: Export current user's .ssh plus ProgramData\ssh host keys and sshd_config when elevated.
- Risk: kind=`dangerous`, risk_level=`secret_export`
- Parameters:
  - `ssh_root` — **Keys folder** (type=`folder`, default=``).
  - `profile_name` — **Machine/profile name** (type=`text`, default=``).
  - `user_name` — **Windows user** (type=`text`, default=``).
  - `ssh_config_path` — **ssh config to check** (type=`file`, default=``).
  - `rclone_config_path` — **rclone config to check** (type=`file`, default=``).
  - `links_report_path` — **Save report to CSV** (type=`text`, default=``).
  - `fail_on_broken` — **Fail when a path is missing** (type=`checkbox`, default=true).
  - `snapshot` — **Snapshot for import** (type=`text`, default=``).

### OpenSSH KeyKit > Import client SSH keys

- Operation id: `ssh_keykit_import_client`
- Description: Copy current .ssh aside as .ssh.bak.timestamp, import the newest/selected client snapshot from input and fix private-key ACLs.
- Risk: kind=`dangerous`, risk_level=`user_write`
- Parameters:
  - `ssh_root` — **Keys folder** (type=`folder`, default=``).
  - `profile_name` — **Machine/profile name** (type=`text`, default=``).
  - `user_name` — **Windows user** (type=`text`, default=``).
  - `ssh_config_path` — **ssh config to check** (type=`file`, default=``).
  - `rclone_config_path` — **rclone config to check** (type=`file`, default=``).
  - `links_report_path` — **Save report to CSV** (type=`text`, default=``).
  - `fail_on_broken` — **Fail when a path is missing** (type=`checkbox`, default=true).
  - `snapshot` — **Snapshot for import** (type=`text`, default=``).

### OpenSSH KeyKit > Import client + server SSH keys

- Operation id: `ssh_keykit_import_all`
- Description: Import client keys plus server host keys from input, fix ACLs, restart sshd and set it Automatic when elevated.
- Risk: kind=`dangerous`, risk_level=`system_change`
- Parameters:
  - `ssh_root` — **Keys folder** (type=`folder`, default=``).
  - `profile_name` — **Machine/profile name** (type=`text`, default=``).
  - `user_name` — **Windows user** (type=`text`, default=``).
  - `ssh_config_path` — **ssh config to check** (type=`file`, default=``).
  - `rclone_config_path` — **rclone config to check** (type=`file`, default=``).
  - `links_report_path` — **Save report to CSV** (type=`text`, default=``).
  - `fail_on_broken` — **Fail when a path is missing** (type=`checkbox`, default=true).
  - `snapshot` — **Snapshot for import** (type=`text`, default=``).

### OpenSSH KeyKit > Open KeyKit scripts folder

- Operation id: `ssh_keykit_open_folder`
- Description: Open tools\ssh_keykit with export/import scripts and wrapper commands; no key changes.
- Risk: kind=`safe`, risk_level=`readonly`
- Parameters:
  - `ssh_root` — **Keys folder** (type=`folder`, default=``).
  - `profile_name` — **Machine/profile name** (type=`text`, default=``).
  - `user_name` — **Windows user** (type=`text`, default=``).
  - `ssh_config_path` — **ssh config to check** (type=`file`, default=``).
  - `rclone_config_path` — **rclone config to check** (type=`file`, default=``).
  - `links_report_path` — **Save report to CSV** (type=`text`, default=``).
  - `fail_on_broken` — **Fail when a path is missing** (type=`checkbox`, default=true).
  - `snapshot` — **Snapshot for import** (type=`text`, default=``).

### AI CLI Backup > Backup (export)

- Operation id: `ai_backup_export`
- Description: Atomically export Claude and Codex into output\ai_backup, then verify its manifest and SHA-256 hashes.
- Risk: kind=`dangerous`, risk_level=`secret_export`
- Parameters:
  - `essentials` — **Move only the essentials** (type=`checkbox`, default=true).
  - `include_auth` — **Include authentication secrets** (type=`checkbox`, default=false).

### AI CLI Backup > Restore (import)

- Operation id: `ai_backup_import`
- Description: Verify the backup staged in input, preview changes by default, then overwrite only selected matching files; unrelated local files stay.
- Risk: kind=`dangerous`, risk_level=`user_write`
- Parameters:
  - `essentials` — **Restore only the essentials** (type=`checkbox`, default=true).
  - `include_auth` — **Restore authentication secrets** (type=`checkbox`, default=false).
  - `dry_run` — **Dry run** (type=`checkbox`, default=true).
  - `allow_foreign_paths` — **Allow saved absolute paths from another PC** (type=`checkbox`, default=false).
  - `allow_legacy` — **Allow legacy bundle without manifest** (type=`checkbox`, default=false).

### AI CLI Backup > Merge memory

- Operation id: `ai_backup_merge`
- Description: Verify the staged bundle and merge Claude .md memory, previewing by default. Name clashes are kept unless Overwrite is enabled.
- Risk: kind=`dangerous`, risk_level=`user_write`
- Parameters:
  - `overwrite` — **Overwrite name clashes** (type=`checkbox`, default=false).
  - `dry_run` — **Dry run** (type=`checkbox`, default=true).
  - `allow_legacy` — **Allow legacy bundle without manifest** (type=`checkbox`, default=false).

### AI CLI Backup > Open tool folder

- Operation id: `ai_backup_open`
- Description: Open tools\ai_backup with the script and wrapper commands.
- Risk: kind=`safe`, risk_level=`readonly`
- Parameters: none.

### Certificate KeyKit > Certificate status

- Operation id: `cert_status`
- Description: List the selected store: subject, thumbprint, expiry, private key and exportability (flags TPM/non-exportable keys).
- Risk: kind=`safe`, risk_level=`readonly`
- Parameters:
  - `cert_store` — **Certificate store** (type=`select`, default=`CurrentUser\My`).
    - Options: `CurrentUser\My` — CurrentUser\My (personal); `LocalMachine\My` — LocalMachine\My (personal); `CurrentUser\Root` — CurrentUser\Root (trusted roots); `LocalMachine\Root` — LocalMachine\Root (trusted roots); `CurrentUser\CA` — CurrentUser\CA (intermediate); `LocalMachine\CA` — LocalMachine\CA (intermediate)
  - `cert_backup_dir` — **Certificates folder** (type=`folder`, default=``).
  - `pfx_password` — **PFX password** (type=`text`, default=``).
  - `import_file` — **Import file (.pfx/.cer/.crt/.sst)** (type=`file`, default=``).
  - `import_store` — **Import target store** (type=`select`, default=`CurrentUser\My`).
    - Options: `CurrentUser\My` — CurrentUser\My (personal); `LocalMachine\My` — LocalMachine\My (personal); `CurrentUser\Root` — CurrentUser\Root (trusted roots); `LocalMachine\Root` — LocalMachine\Root (trusted roots); `CurrentUser\CA` — CurrentUser\CA (intermediate); `LocalMachine\CA` — LocalMachine\CA (intermediate)

### Certificate KeyKit > Export personal keys to PFX

- Operation id: `cert_export_pfx`
- Description: Export exportable private-key certs from the selected store to password-protected .pfx in output\certificates. TPM-bound keys are skipped. Output contains PRIVATE KEYS.
- Risk: kind=`dangerous`, risk_level=`secret_export`
- Parameters:
  - `cert_store` — **Certificate store** (type=`select`, default=`CurrentUser\My`).
    - Options: `CurrentUser\My` — CurrentUser\My (personal); `LocalMachine\My` — LocalMachine\My (personal); `CurrentUser\Root` — CurrentUser\Root (trusted roots); `LocalMachine\Root` — LocalMachine\Root (trusted roots); `CurrentUser\CA` — CurrentUser\CA (intermediate); `LocalMachine\CA` — LocalMachine\CA (intermediate)
  - `cert_backup_dir` — **Certificates folder** (type=`folder`, default=``).
  - `pfx_password` — **PFX password** (type=`text`, default=``).
  - `import_file` — **Import file (.pfx/.cer/.crt/.sst)** (type=`file`, default=``).
  - `import_store` — **Import target store** (type=`select`, default=`CurrentUser\My`).
    - Options: `CurrentUser\My` — CurrentUser\My (personal); `LocalMachine\My` — LocalMachine\My (personal); `CurrentUser\Root` — CurrentUser\Root (trusted roots); `LocalMachine\Root` — LocalMachine\Root (trusted roots); `CurrentUser\CA` — CurrentUser\CA (intermediate); `LocalMachine\CA` — LocalMachine\CA (intermediate)

### Certificate KeyKit > Export store to SST (public)

- Operation id: `cert_export_roots`
- Description: Export the selected store's public certificates (no private keys) to a timestamped .sst bundle in output\certificates.
- Risk: kind=`safe`, risk_level=`project_write`
- Parameters:
  - `cert_store` — **Certificate store** (type=`select`, default=`CurrentUser\My`).
    - Options: `CurrentUser\My` — CurrentUser\My (personal); `LocalMachine\My` — LocalMachine\My (personal); `CurrentUser\Root` — CurrentUser\Root (trusted roots); `LocalMachine\Root` — LocalMachine\Root (trusted roots); `CurrentUser\CA` — CurrentUser\CA (intermediate); `LocalMachine\CA` — LocalMachine\CA (intermediate)
  - `cert_backup_dir` — **Certificates folder** (type=`folder`, default=``).
  - `pfx_password` — **PFX password** (type=`text`, default=``).
  - `import_file` — **Import file (.pfx/.cer/.crt/.sst)** (type=`file`, default=``).
  - `import_store` — **Import target store** (type=`select`, default=`CurrentUser\My`).
    - Options: `CurrentUser\My` — CurrentUser\My (personal); `LocalMachine\My` — LocalMachine\My (personal); `CurrentUser\Root` — CurrentUser\Root (trusted roots); `LocalMachine\Root` — LocalMachine\Root (trusted roots); `CurrentUser\CA` — CurrentUser\CA (intermediate); `LocalMachine\CA` — LocalMachine\CA (intermediate)

### Certificate KeyKit > Import PFX

- Operation id: `cert_import_pfx`
- Description: Import the selected .pfx (with password) into the target store, marking the key exportable. Changes the certificate store; reboot not required. Pick file and password in Advanced.
- Risk: kind=`dangerous`, risk_level=`system_change`
- Parameters:
  - `cert_store` — **Certificate store** (type=`select`, default=`CurrentUser\My`).
    - Options: `CurrentUser\My` — CurrentUser\My (personal); `LocalMachine\My` — LocalMachine\My (personal); `CurrentUser\Root` — CurrentUser\Root (trusted roots); `LocalMachine\Root` — LocalMachine\Root (trusted roots); `CurrentUser\CA` — CurrentUser\CA (intermediate); `LocalMachine\CA` — LocalMachine\CA (intermediate)
  - `cert_backup_dir` — **Certificates folder** (type=`folder`, default=``).
  - `pfx_password` — **PFX password** (type=`text`, default=``).
  - `import_file` — **Import file (.pfx/.cer/.crt/.sst)** (type=`file`, default=``).
  - `import_store` — **Import target store** (type=`select`, default=`CurrentUser\My`).
    - Options: `CurrentUser\My` — CurrentUser\My (personal); `LocalMachine\My` — LocalMachine\My (personal); `CurrentUser\Root` — CurrentUser\Root (trusted roots); `LocalMachine\Root` — LocalMachine\Root (trusted roots); `CurrentUser\CA` — CurrentUser\CA (intermediate); `LocalMachine\CA` — LocalMachine\CA (intermediate)

### Certificate KeyKit > Import every PFX in the folder

- Operation id: `cert_import_pfx_folder`
- Description: Import every .pfx listed in certificates.json, each into the store it was exported from, using one password. Changes the certificate store.
- Risk: kind=`dangerous`, risk_level=`system_change`
- Parameters:
  - `cert_store` — **Certificate store** (type=`select`, default=`CurrentUser\My`).
    - Options: `CurrentUser\My` — CurrentUser\My (personal); `LocalMachine\My` — LocalMachine\My (personal); `CurrentUser\Root` — CurrentUser\Root (trusted roots); `LocalMachine\Root` — LocalMachine\Root (trusted roots); `CurrentUser\CA` — CurrentUser\CA (intermediate); `LocalMachine\CA` — LocalMachine\CA (intermediate)
  - `cert_backup_dir` — **Certificates folder** (type=`folder`, default=``).
  - `pfx_password` — **PFX password** (type=`text`, default=``).
  - `import_file` — **Import file (.pfx/.cer/.crt/.sst)** (type=`file`, default=``).
  - `import_store` — **Import target store** (type=`select`, default=`CurrentUser\My`).
    - Options: `CurrentUser\My` — CurrentUser\My (personal); `LocalMachine\My` — LocalMachine\My (personal); `CurrentUser\Root` — CurrentUser\Root (trusted roots); `LocalMachine\Root` — LocalMachine\Root (trusted roots); `CurrentUser\CA` — CurrentUser\CA (intermediate); `LocalMachine\CA` — LocalMachine\CA (intermediate)

### Certificate KeyKit > Import certificate / CA

- Operation id: `cert_import_cert`
- Description: Import a public .cer/.crt/.sst into the target store (e.g. trust a corporate root CA). Changes trust; choose target store carefully. Pick file in Advanced.
- Risk: kind=`dangerous`, risk_level=`system_change`
- Parameters:
  - `cert_store` — **Certificate store** (type=`select`, default=`CurrentUser\My`).
    - Options: `CurrentUser\My` — CurrentUser\My (personal); `LocalMachine\My` — LocalMachine\My (personal); `CurrentUser\Root` — CurrentUser\Root (trusted roots); `LocalMachine\Root` — LocalMachine\Root (trusted roots); `CurrentUser\CA` — CurrentUser\CA (intermediate); `LocalMachine\CA` — LocalMachine\CA (intermediate)
  - `cert_backup_dir` — **Certificates folder** (type=`folder`, default=``).
  - `pfx_password` — **PFX password** (type=`text`, default=``).
  - `import_file` — **Import file (.pfx/.cer/.crt/.sst)** (type=`file`, default=``).
  - `import_store` — **Import target store** (type=`select`, default=`CurrentUser\My`).
    - Options: `CurrentUser\My` — CurrentUser\My (personal); `LocalMachine\My` — LocalMachine\My (personal); `CurrentUser\Root` — CurrentUser\Root (trusted roots); `LocalMachine\Root` — LocalMachine\Root (trusted roots); `CurrentUser\CA` — CurrentUser\CA (intermediate); `LocalMachine\CA` — LocalMachine\CA (intermediate)

### Certificate KeyKit > Open certificate export folder

- Operation id: `cert_open_folder`
- Description: Open output\certificates; no certificate changes.
- Risk: kind=`safe`, risk_level=`readonly`
- Parameters:
  - `cert_store` — **Certificate store** (type=`select`, default=`CurrentUser\My`).
    - Options: `CurrentUser\My` — CurrentUser\My (personal); `LocalMachine\My` — LocalMachine\My (personal); `CurrentUser\Root` — CurrentUser\Root (trusted roots); `LocalMachine\Root` — LocalMachine\Root (trusted roots); `CurrentUser\CA` — CurrentUser\CA (intermediate); `LocalMachine\CA` — LocalMachine\CA (intermediate)
  - `cert_backup_dir` — **Certificates folder** (type=`folder`, default=``).
  - `pfx_password` — **PFX password** (type=`text`, default=``).
  - `import_file` — **Import file (.pfx/.cer/.crt/.sst)** (type=`file`, default=``).
  - `import_store` — **Import target store** (type=`select`, default=`CurrentUser\My`).
    - Options: `CurrentUser\My` — CurrentUser\My (personal); `LocalMachine\My` — LocalMachine\My (personal); `CurrentUser\Root` — CurrentUser\Root (trusted roots); `LocalMachine\Root` — LocalMachine\Root (trusted roots); `CurrentUser\CA` — CurrentUser\CA (intermediate); `LocalMachine\CA` — LocalMachine\CA (intermediate)

### User fonts > Show my fonts

- Operation id: `fonts_status`
- Description: List the fonts installed for this user with [ OK ] or [MISS], and count the system ones. Changes nothing.
- Risk: kind=`safe`, risk_level=`readonly`
- Parameters:
  - `fonts_folder` — **Fonts folder** (type=`folder`, default=``).
  - `include_system` — **List system fonts too** (type=`checkbox`, default=false).

### User fonts > Export my fonts

- Operation id: `fonts_export`
- Description: Copy the user's font files into output\fonts with a map of their registered names. System fonts are not copied.
- Risk: kind=`safe`, risk_level=`project_write`
- Parameters:
  - `fonts_folder` — **Fonts folder** (type=`folder`, default=``).
  - `include_system` — **List system fonts too** (type=`checkbox`, default=false).

### User fonts > Import fonts

- Operation id: `fonts_import`
- Description: Install the collected fonts for this user only: file into the profile, name under HKCU, running programs notified. Needs no administrator and leaves C:\Windows\Fonts alone.
- Risk: kind=`dangerous`, risk_level=`user_write`
- Parameters:
  - `fonts_folder` — **Fonts folder** (type=`folder`, default=``).
  - `include_system` — **List system fonts too** (type=`checkbox`, default=false).

### User fonts > Open fonts folder

- Operation id: `fonts_open_folder`
- Description: Open output\fonts; collects nothing.
- Risk: kind=`safe`, risk_level=`readonly`
- Parameters:
  - `fonts_folder` — **Fonts folder** (type=`folder`, default=``).
  - `include_system` — **List system fonts too** (type=`checkbox`, default=false).

### Shell environment > Show shell files

- Operation id: `shell_status`
- Description: List the Windows Terminal settings and PowerShell profiles this machine has, with [ OK ] or [ -- ]. Changes nothing.
- Risk: kind=`safe`, risk_level=`readonly`
- Parameters:
  - `shell_folder` — **Shell folder** (type=`folder`, default=``).

### Shell environment > Export shell files

- Operation id: `shell_export`
- Description: Copy the found settings and profiles into output\shell with a map of what each file is.
- Risk: kind=`safe`, risk_level=`project_write`
- Parameters:
  - `shell_folder` — **Shell folder** (type=`folder`, default=``).

### Shell environment > Import shell files

- Operation id: `shell_import`
- Description: Put each collected file where it belongs on this machine, keeping a dated copy of anything replaced. A file identical to the one already there is left alone.
- Risk: kind=`dangerous`, risk_level=`user_write`
- Parameters:
  - `shell_folder` — **Shell folder** (type=`folder`, default=``).

### Shell environment > Open shell folder

- Operation id: `shell_open_folder`
- Description: Open output\shell; collects nothing.
- Risk: kind=`safe`, risk_level=`readonly`
- Parameters:
  - `shell_folder` — **Shell folder** (type=`folder`, default=``).

### Configured access > Show what configuration names

- Operation id: `access_status`
- Description: List every key, known_hosts, certificate and proxy path named in ssh and rclone configuration, with [ OK ] or [MISS]. Changes nothing.
- Risk: kind=`safe`, risk_level=`readonly`
- Parameters:
  - `access_folder` — **Access folder** (type=`folder`, default=``).
  - `access_key_root` — **Where keys land here** (type=`folder`, default=``).
  - `ssh_config_path` — **ssh config** (type=`file`, default=``).
  - `rclone_config_path` — **rclone config** (type=`file`, default=``).

### Configured access > Export configured access

- Operation id: `access_export`
- Description: Copy ssh config, rclone.conf and every file they name into output\access with a map of where each came from. Contains PRIVATE KEYS.
- Risk: kind=`dangerous`, risk_level=`secret_export`
- Parameters:
  - `access_folder` — **Access folder** (type=`folder`, default=``).
  - `access_key_root` — **Where keys land here** (type=`folder`, default=``).
  - `ssh_config_path` — **ssh config** (type=`file`, default=``).
  - `rclone_config_path` — **rclone config** (type=`file`, default=``).

### Configured access > Import configured access

- Operation id: `access_import`
- Description: Put the carried files under the chosen root, rewrite ssh and rclone configuration to match, restrict key ACLs, then check the links. Replaces both configuration files, keeping a dated copy of each.
- Risk: kind=`dangerous`, risk_level=`user_write`
- Parameters:
  - `access_folder` — **Access folder** (type=`folder`, default=``).
  - `access_key_root` — **Where keys land here** (type=`folder`, default=``).
  - `ssh_config_path` — **ssh config** (type=`file`, default=``).
  - `rclone_config_path` — **rclone config** (type=`file`, default=``).

### Machine migration > Show what travels

- Operation id: `migration_plan`
- Description: Read config\migration_plan.yaml and list every item, its pack, its folder and whether it can be imported unattended. Changes nothing.
- Risk: kind=`safe`, risk_level=`readonly`
- Parameters:
  - `migration_folder` — **Migration folder** (type=`folder`, default=``).
  - `profile_name` — **Machine name for the folder** (type=`text`, default=``).
  - `user_name` — **Windows user** (type=`text`, default=``).
  - `pfx_password` — **PFX password** (type=`text`, default=``).

### Machine migration > Check access after a move

- Operation id: `migration_verify`
- Description: Run the same access-link check the SSH pack runs: every key, known_hosts and proxy path named in ssh and rclone configuration.
- Risk: kind=`safe`, risk_level=`readonly`
- Parameters:
  - `migration_folder` — **Migration folder** (type=`folder`, default=``).
  - `profile_name` — **Machine name for the folder** (type=`text`, default=``).
  - `user_name` — **Windows user** (type=`text`, default=``).
  - `pfx_password` — **PFX password** (type=`text`, default=``).

### Machine migration > Export the migration

- Operation id: `migration_export`
- Description: Walk the plan, call each pack and collect everything into output\migration\<machine>_<time> with an inventory file. Contains PRIVATE KEYS and clear Wi-Fi passwords.
- Risk: kind=`dangerous`, risk_level=`secret_export`
- Parameters:
  - `migration_folder` — **Migration folder** (type=`folder`, default=``).
  - `profile_name` — **Machine name for the folder** (type=`text`, default=``).
  - `user_name` — **Windows user** (type=`text`, default=``).
  - `pfx_password` — **PFX password** (type=`text`, default=``).

### Machine migration > Import the migration

- Operation id: `migration_import`
- Description: Read the inventory from input, hand every item back to its pack, then check access links. Replaces this user's SSH material and adds Wi-Fi profiles.
- Risk: kind=`dangerous`, risk_level=`system_change`
- Parameters:
  - `migration_folder` — **Migration folder** (type=`folder`, default=``).
  - `profile_name` — **Machine name for the folder** (type=`text`, default=``).
  - `user_name` — **Windows user** (type=`text`, default=``).
  - `pfx_password` — **PFX password** (type=`text`, default=``).

### Machine migration > Open migration folder

- Operation id: `migration_open_folder`
- Description: Open output\migration; collects nothing.
- Risk: kind=`safe`, risk_level=`readonly`
- Parameters:
  - `migration_folder` — **Migration folder** (type=`folder`, default=``).
  - `profile_name` — **Machine name for the folder** (type=`text`, default=``).
  - `user_name` — **Windows user** (type=`text`, default=``).
  - `pfx_password` — **PFX password** (type=`text`, default=``).

### Utilities > Documentation PDF > Preview PDF export plan

- Operation id: `docs_pdf_plan`
- Description: Dry run: list Markdown sources and target PDF files without writing PDFs.
- Risk: kind=`safe`, risk_level=`readonly`
- Parameters:
  - `docs_pdf_theme` — **Theme** (type=`select`, default=`both`).
    - Options: `both` — Both: dark + light-sand; `dark` — Dark; `light-sand` — Light Sand
  - `docs_pdf_include_agent_instructions` — **Include agent instructions** (type=`checkbox`, default=true).

### Utilities > Documentation PDF > Generate docs PDFs

- Operation id: `docs_pdf_render`
- Description: Render root guides, docs\*.md, GitHub README files and optional agent instructions into docs\PDF. Markdown remains the source of truth.
- Risk: kind=`safe`, risk_level=`project_write`
- Parameters:
  - `docs_pdf_theme` — **Theme** (type=`select`, default=`both`).
    - Options: `both` — Both: dark + light-sand; `dark` — Dark; `light-sand` — Light Sand
  - `docs_pdf_include_agent_instructions` — **Include agent instructions** (type=`checkbox`, default=true).

### Utilities > Documentation PDF > Open docs PDF folder

- Operation id: `docs_pdf_open`
- Description: Open docs\PDF.
- Risk: kind=`safe`, risk_level=`readonly`
- Parameters:
  - `docs_pdf_theme` — **Theme** (type=`select`, default=`both`).
    - Options: `both` — Both: dark + light-sand; `dark` — Dark; `light-sand` — Light Sand
  - `docs_pdf_include_agent_instructions` — **Include agent instructions** (type=`checkbox`, default=true).

### Utilities > ripgrep version

- Operation id: `ripgrep_status`
- Description: Show project-local ripgrep\rg.exe version.
- Risk: kind=`safe`, risk_level=`readonly`
- Parameters: none.

### Utilities > Open tool folder

- Operation id: `open_tool_folder`
- Description: Open a project-local utility folder.
- Risk: kind=`safe`, risk_level=`readonly`
- Parameters:
  - `folder` — **Folder** (type=`select`).
    - Options: `ripgrep` — ripgrep; `tools/network_cleaner` — tools/network_cleaner; `WSL` — WSL; `tools/codex_nuke` — tools/codex_nuke; `tools/python_nuke` — tools/python_nuke; `tools/driver_firmware_audit` — tools/driver_firmware_audit; `tools/ssh_keykit` — tools/ssh_keykit; `tools/ubuntu_dev_installer` — tools/ubuntu_dev_installer; `tools/ssd_nvme_reset_wizard` — tools/ssd_nvme_reset_wizard; `tools/winre_extend` — tools/winre_extend; `tools/bitrix_hosts_toggle_pack` — tools/bitrix_hosts_toggle_pack; `tools/disable_windows_proxy` — tools/disable_windows_proxy; `tools/wires_wireless` — tools/wires_wireless; `tools/wsl` — tools/wsl

### Maintenance & Cleanup > Codex Nuke > Codex Nuke audit

- Operation id: `codex_nuke_audit`
- Description: Read-only scan of Codex desktop artifacts.
- Risk: kind=`safe`, risk_level=`readonly`
- Parameters: none.

### Maintenance & Cleanup > Codex Nuke > Codex Nuke dry run

- Operation id: `codex_nuke_dryrun`
- Description: Simulate Codex Nuke without changing the system.
- Risk: kind=`safe`, risk_level=`readonly`
- Parameters: none.

### Maintenance & Cleanup > Codex Nuke > Codex session reset

- Operation id: `codex_nuke_session_reset`
- Description: Soft reset: kill Codex processes and clear sessions/cache while keeping auth, config and install.
- Risk: kind=`dangerous`, risk_level=`user_write`
- Parameters: none.

### Maintenance & Cleanup > Codex Nuke > Codex NUKE, keep CLI state

- Operation id: `codex_nuke_keep_cli_state`
- Description: Remove Codex desktop artifacts while preserving ~/.codex for Codex CLI state.
- Risk: kind=`dangerous`, risk_level=`destructive`
- Parameters: none.

### Maintenance & Cleanup > Codex Nuke > Codex NUKE full

- Operation id: `codex_nuke_full`
- Description: Full Codex desktop removal, including shared Codex user state.
- Risk: kind=`dangerous`, risk_level=`destructive`
- Parameters: none.

### Maintenance & Cleanup > Python Nuke > Python Nuke audit

- Operation id: `python_nuke_audit`
- Description: Read-only scan of Python installs, launchers, caches, env vars and PATH entries.
- Risk: kind=`safe`, risk_level=`readonly`
- Parameters: none.

### Maintenance & Cleanup > Python Nuke > Python Nuke dry run

- Operation id: `python_nuke_dryrun`
- Description: Simulate Python Nuke without changing the system.
- Risk: kind=`safe`, risk_level=`readonly`
- Parameters: none.

### Maintenance & Cleanup > Python Nuke > Python NUKE full

- Operation id: `python_nuke_full`
- Description: Remove common Python installs, launchers, pip cache, env vars and PATH entries.
- Risk: kind=`dangerous`, risk_level=`destructive`
- Parameters: none.

### Maintenance & Cleanup > Python Nuke > Python NUKE, keep winget

- Operation id: `python_nuke_keep_winget`
- Description: Run Python Nuke but skip the winget uninstall pass.
- Risk: kind=`dangerous`, risk_level=`destructive`
- Parameters: none.

### Maintenance & Cleanup > Clear Workbench workspace

- Operation id: `cleanup_workspace`
- Description: Delete only files inside the managed workspace folder.
- Risk: kind=`dangerous`, risk_level=`destructive`
- Parameters: none.

### Maintenance > Clear Workbench I/O

- Operation id: `cleanup_input_output`
- Description: Delete contents of managed input and output folders.
- Risk: kind=`dangerous`, risk_level=`destructive`
- Parameters: none.

<!-- END GENERATED PARAMETER REFERENCE -->

## CLI Operations

Show WSL status:

```cmd
runtime\python.exe system_core\cli_operation.py wsl_status
```

Run a dangerous operation:

```cmd
runtime\python.exe system_core\cli_operation.py storage_winre_wizard --yes-i-understand
```

Pass parameters:

```cmd
runtime\python.exe system_core\cli_operation.py wsl_install_distro --yes-i-understand --param install_distro=Ubuntu-26.04 --param install_location_mode=custom --param install_location=S:\WSL\VHDX\Ubuntu-26.04 --param no_launch=true
```

## Project Checks

Minimal checks after changes:

```cmd
runtime\python.exe -m py_compile system_core\ui_nicegui\app.py system_core\services\devops_tools.py system_core\core\jobs.py
runtime\python.exe system_core\ui_nicegui\app.py --smoke
runtime\python.exe system_core\doctor.py
```

Manual GUI server:

```cmd
runtime\python.exe system_core\ui_nicegui\app.py --host 127.0.0.1 --port 8092 --no-browser
```

## Further Reading

- `README_AUDION_DEVOPS_TOOLS_RU.md` - short project README.
- `docs\AUDION_DEVOPS_TOOLS_RU.md` - architecture and development rules.
- `docs\BITRIX_HOSTS_RU.md` - Bitrix hosts workflow.
- `docs\NETWORK_CONNECTIVITY_RU.md` - Network Cleaner, Wi-Fi profiles, SMB login, adapters and proxy.
- `docs\BROWSER_BOOKMARKS_MASTER_RU.md` - Chromium Bookmarks/Favicons master export/import.
- `docs\WSL_TOOLKIT_RU.md` - WSL install, import, backup, restore, move and delete.
- `docs\VIRTUALIZATION_SWITCHER_RU.md` - virtualization modes, Hyper-V/WSL2 and VM diagnostics.
- `docs\DEFAULT_APPS_GUARD_RU.md` - default apps ritual and gotchas.
- `docs\ASSOCIATION_DEFENSE_RU.md` - in-box Microsoft apps, AppLocker reinstall-block and association snapshots.
- `docs\HARDWARE_DRIVER_GUARD_RU.md` - driver, NVIDIA and storage details.
- `docs\STORAGE_DISK_PROCEDURES_RU.md` - WinRE, SSD/NVMe and disk inventory.
- `docs\OPENSSH_KEYKIT_RU.md` - SSH client/server key backup and restore.
- `docs\CERTIFICATE_KEYKIT_RU.md` - certificate/PFX backup and restore.
- `docs\MAINTENANCE_CLEANUP_RU.md` - Codex/Python nuke and workspace cleanup.
- `docs\MANIFEST_REFERENCE_RU.md` - GUI manifest/service layer rules.
- `docs\SMOKE_TEST_CHECKLIST_RU.md` - smoke checklist.
- `docs\KNOWN_PITFALLS_RU.md` - common pitfalls.
## Canonical Workbench labels

Workbench uses the same Audion Image Tools public vocabulary in every project. Its buttons always keep the same order and labels: **Source**, **Add file...**, **Target**, **Reset**, **Delete**, **List**.

`Reset` returns to project `input/output` and does not delete files; `Delete` clears the current `Source` and `Target` only after confirmation. The exact Russian labels are **Источник**, **Добавить файл...**, **Назначение**, **Сбросить**, **Удалить**, **Список**. The Workbench variants `Destination`, `Clear`, `Цель`, and `Очистить` are not used.
