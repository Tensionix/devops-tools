# Audion DevOps Tools

<!-- audion:release -->
<p align="center">
  <a href="https://audion.dev/downloads/devops-tools"><img alt="Windows" src="https://img.shields.io/badge/Windows-10%20%7C%2011-0b6db8?style=flat-square&logo=windows&logoColor=white"></a>
  <a href="https://github.com/Tensionix/devops-tools/releases/latest"><img alt="Release" src="https://img.shields.io/github/v/release/Tensionix/devops-tools?style=flat-square&label=release&color=e08a63"></a>
  <a href="https://github.com/Tensionix/devops-tools/releases"><img alt="Downloads" src="https://img.shields.io/github/downloads/Tensionix/devops-tools/total?style=flat-square&label=downloads&color=5fd08a"></a>
  <a href="https://github.com/Tensionix/devops-tools/blob/main/LICENSE"><img alt="License" src="https://img.shields.io/github/license/Tensionix/devops-tools?style=flat-square&color=5fd08a&logo=apache&logoColor=white&cacheSeconds=3600"></a>
</p>

**Version 1.8.2** · 2026-09-01 · 14.2 MB

- [Direct download](https://dl.audion.dev/devops-tools/1.8.2/Audion_DevOps_Tools_v1.8.2.zip) — unmetered, no rate limits
- [Project page](https://audion.dev/downloads/devops-tools) — every version and how to install

<p align="center"><img src="docs/screenshot.png" alt="The program window" width="560"></p>

`SHA-256: 0d8f943a4105895c1f4ac26d8bfec7ac8f67b4ce6bf48b3e9cd0d23c9cbd9fa5`

---

An **Audion** tool, published by [Tensionix](https://github.com/Tensionix).
<!-- /audion:release -->

Audion DevOps Tools is a Windows-first portable GUI shell for the Audion DevOps utility bundle.



It keeps existing CMD/FZF/PowerShell workflows as the source of truth and adds a safer desktop control layer: forms, pickers, checkboxes, confirmations, a live terminal and persistent command history.



The UI is intentionally technical: command buttons stay short and often English-heavy, visible descriptions stay compact, and the full Windows context, risk, rollback notes and terminology live in tooltips. Logical frames expose pairs and pipelines such as `backup / restore`, `export / import`, `block / unblock`; soft button tones distinguish gentle, normal and strong actions.



Audion DevOps Tools is not a Chris Titus WinUtil clone, a generic Windows tuner, or a debloater. It targets the missing thin hardware/software layer around Windows, WSL, virtualization, hardware policy, storage, networking, default-app policy and secrets. Think of it as a fighter-jet cockpit for controlled system operations: explicit parameters, backups, risk labels, confirmations and logs.



## Features



- NiceGUI + pywebview desktop shell.

- Embedded portable Python runtime in `runtime\`.

- Unified WSL Toolkit: WSL2 features/update, online distro install, local `.wsl`/tar/vhd install/import, list/status/shutdown, backup/clone/move/delete, restore and VHDX registration.

- Virtualization switcher: read-only status/optimization diagnostics, Hyper-V/WSL2 mode, fast third-party VM mode, WHP coexistence, Hyper-V/Sandbox toggles with BCD backup and reboot warnings.

- Network Cleaner: diagnostics, network backup/restore, proxy tools.

- Connectivity: adapter control, SMB login to Windows file sharing through an external `net use` console, sticky Wi-Fi pair, quick LAN/Wi-Fi modes and full Wi-Fi profile management (status/connect/export/import).

- Hosts and Bitrix profiles with local endpoint detection, DNS/hosts status, custom/auto-scanned TCP ports, managed hosts metadata and bitwise depatch from backup.

- Default Apps Guard for Windows default app associations: snapshot/rescan, HKLM policy guard and current/profile/policy comparison.

- Association Defense: in-box Microsoft app control (remove / restore / keep removed), AppLocker reinstall-block, Edge/Defender policy guards, association snapshots (whole map and per group) and change tracking.

- Hardware / Driver Guard: Windows Update driver policy block, NVIDIA driver install restrictions, Driver Store backup/restore, NVIDIA HDMI/DP Audio control and disk procedures: disk inventory, WinRE and SSD/NVMe wizard launch.

- Utilities: AI CLI Backup for backing up, restoring and merging Claude Code and Codex data, OpenSSH KeyKit and Certificate KeyKit for sensitive key/certificate export/import, Configured access and Machine migration for collecting every access into one folder with an inventory, Documentation PDF export, Ubuntu Dev Installer materials, bundled ripgrep and quick folder shortcuts.

- Theme catalog in `config\ui_colors.yaml` with a header theme selector.

- Logical UI blocks, compact descriptions and full tooltips for complex Windows/policy/secrets workflows.

- Live terminal output with robust Windows/WSL decoding.



## Documented Admin Basis



The project wraps documented Windows administrator/deployment mechanisms where possible instead of editing protected state directly:



- Default Apps Guard: DISM default app associations + HKLM `DefaultAssociationsConfiguration` policy; current-user association snapshots live in `Association Defense` and only read the registry.

- Windows Home/Core is not treated as a guaranteed target for the Default Apps Guard policy path: the GUI reports edition support and blocks apply by default on unsupported editions.

- WSL Toolkit: official `wsl.exe` commands.

- Wi-Fi profiles: official `netsh wlan` commands.

- Virtualization switcher: `bcdedit`, DISM optional features, `Win32_DeviceGuard` status, power-plan/Defender/.wslconfig diagnostics and WSL VHDX placement.

- Certificate KeyKit: PowerShell PKI cmdlets over `Cert:\` stores.

- Hardware / Driver Guard: documented Windows Update driver policy and Device Installation Restrictions.

- Storage/WinRE/DISM/features inside Hardware: standard Windows administrator tools with backup/status/confirmation around risky actions.

- OpenSSH KeyKit, Certificate KeyKit PFX backups and Wi-Fi-key backups are sensitive export workflows; generated archives must be stored as secrets.

- `UserChoice` hashes and UCPD are not bypassed by hand.



Relevant Microsoft docs: [ApplicationDefaults Policy CSP](https://learn.microsoft.com/en-us/windows/client-management/mdm/policy-csp-applicationdefaults), [DISM default app associations](https://learn.microsoft.com/en-us/windows-hardware/manufacture/desktop/dism-default-application-association-servicing-command-line-options?view=windows-11), [netsh wlan](https://learn.microsoft.com/en-us/windows-server/administration/windows-commands/netsh-wlan), [WSL basic commands](https://learn.microsoft.com/en-us/windows/wsl/basic-commands).



Hardware helper scripts are project-local under `system_core\windows_driver_guard` and `system_core\nvidia_audio`.



### Default Apps Guard: short workflow



After a fresh Windows setup and manual default-app configuration: run `Check defaults protection`, `Overwrite reference from current Windows defaults`, keep `Remove Suggested=true`, run `Enable / repair defaults protection`, then sign out/sign in or reboot and run `Check defaults protection` again. The detailed Russian guide with Windows gotchas lives in `docs\DEFAULT_APPS_GUARD_RU.md`.



### Bitrix Hosts: short workflow



Current default: `portal.itpgrad.ru -> 192.168.0.130`, port `443`. Workflow: `Detect current endpoint` -> `Status / DNS / ports` -> `Enable override` -> after work `Disable override`. `Disable override` restores `hosts` byte-for-byte from the `backup=hosts_prepatch_....bak` metadata in the managed line. Details: `docs\BITRIX_HOSTS_RU.md`.



## Run



```bat

launcher_gui.cmd

```



The standard launcher requests UAC and starts the whole GUI elevated. That is intentional for DISM, hosts edits, network adapters, disk/WinRE helpers and WSL setup.



Short module entry points:



```bat

launcher_project.cmd

cli\launcher_wsl.cmd

cli\launcher_bitrix.cmd

cli\launcher_default_apps.cmd

cli\launcher_association_defense.cmd

cli\launcher_hardware.cmd

cli\launcher_docs_pdf.cmd

cli\launcher_codex_nuke.cmd

cli\launcher_python_nuke.cmd

```



The WSL, Bitrix, Default Apps and Association Defense launchers use `system_core\cli_operation.py`, so they run through the same manifest/service layer as the GUI. The Nuke launchers are root wrappers for the integrated `tools\...\Nuke.cmd` entry points with UAC elevation and typed confirmations.



Read-only/debug launch without UAC:



```bat

set AUDION_GUI_NO_ELEVATE=1

launcher_gui.cmd

```



## Maintenance



Create missing managed folders:



```bat

init_folders.cmd

```



Run project cleanup:



```bat

cleanup_project.cmd

```



The cleaner preserves scripts, configs, documentation, tracked license docs and folder structure. It removes generated/downloaded payloads: `runtime`, `wheelhouse`, `release`, `install\download`, `system_core\powershell`, `system_core\fzf.exe`, logs, reports, input/output/workspace/data contents and Python caches.



Preview cleanup actions:



```bat

cleanup_project.cmd /DRYRUN /Y

```



## Verification



```bat

runtime\python.exe -m py_compile system_core\ui_nicegui\app.py system_core\services\devops_tools.py system_core\core\jobs.py

runtime\python.exe system_core\ui_nicegui\app.py --smoke

runtime\python.exe system_core\doctor.py

```



## Documentation



- `README_AUDION_DEVOPS_TOOLS_RU.md`

- `USER_GUIDE_RU.md`

- `USER_GUIDE_EN.md`

- `AGENTS.md`

- `docs\AUDION_DEVOPS_TOOLS_RU.md`

- `docs\BITRIX_HOSTS_RU.md`

- `docs\NETWORK_CONNECTIVITY_RU.md`

- `docs\WSL_TOOLKIT_RU.md`

- `docs\VIRTUALIZATION_SWITCHER_RU.md`

- `docs\DEFAULT_APPS_GUARD_RU.md`

- `docs\ASSOCIATION_DEFENSE_RU.md`

- `docs\HARDWARE_DRIVER_GUARD_RU.md`

- `docs\STORAGE_DISK_PROCEDURES_RU.md`

- `docs\OPENSSH_KEYKIT_RU.md`

- `docs\CERTIFICATE_KEYKIT_RU.md`

- `docs\MAINTENANCE_CLEANUP_RU.md`

- `docs\MANIFEST_REFERENCE_RU.md`

- `docs\GUI_TREE_REFACTOR_RU.md`

- `docs\MEMORY.md`

- `docs\SMOKE_TEST_CHECKLIST_RU.md`

- `docs\KNOWN_PITFALLS_RU.md`

