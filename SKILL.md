---
name: audion-devops-tools
description: Run, check and change Audion DevOps Tools - a portable Windows program for precise system operations - WSL and virtualisation, Windows Update and NVIDIA driver policy, HWID locks, the Driver Store, disks and WinRE, networking (adapters, Wi-Fi profiles, DNS, repair and backup, proxy, hosts and Bitrix, SMB sign-in), default-app associations, Microsoft apps and Edge, export and import of SSH keys, certificates, fonts, shell settings, accesses, bookmarks and AI CLI data, cleanup of Codex, Python and caches. Every operation runs through the console command devops_cli.cmd; the window App\AudionDevOpsTools.exe is its face. Use when asked which operation does a Windows system task, to run or dry-check an operation, to read its fields and options, to explain what it changes and how to roll it back, or to change, build and check the program itself.
---

# Audion DevOps Tools

A portable Windows program for precise system operations. `Start.exe` opens the window
(`App\AudionDevOpsTools.exe`, C# on Avalonia 12, its own .NET runtime); every button of the window is an
operation of the console command `devops_cli.cmd` (Python, `system_core\`), and the window runs nothing the
command cannot. The scripts of the operations run with `App\AudionPs.exe`, PowerShell 7 under the program's name.

It is not a tuner or a debloater: each operation wraps one documented Windows mechanism, with explicit parameters,
a risk label, a backup before a change, a confirmation and a log. Why things are as they are is in `MEMORY.md`;
the human account is `docs\USER_GUIDE_RU.md` / `docs\USER_GUIDE_EN.md`, every operation with its fields is
`docs\COMMANDS_RU.md` / `docs\COMMANDS_EN.md`, the subsystems are `docs\tools\*.md`. Paths below are relative to
the project root; never hardcode the drive.

## The console command

```
devops_cli.cmd describe                                   the manifest, the layout, the paths (JSON)
devops_cli.cmd run --operation ID [--set NAME=VALUE ...]  an operation; its log goes to the console
devops_cli.cmd check --operation ID [--set ...]           whether the form may run, and the question to ask first
devops_cli.cmd options --operation ID --field NAME        the options of a field, asked of its provider
devops_cli.cmd state --page PAGE                          the state of the machine for the switches of a page
devops_cli.cmd smb [--save "PC|USER" | --forget KEY | --clear]
devops_cli.cmd version
```

`run` takes `--source` / `--target` (where imports read from and exports go; `input` and `output` by default, a
relative path counts from the project), `--params FILE` (the values of a form as JSON), `--result FILE` (the
outcome), `--cancel-file FILE` (the stop signal: the operation stops at its next safe point once the file appears).
A plain line of `run` is a line of the log; a line starting with `::devops::` is a service line with JSON.
Exit codes: 0 done, 1 failed, 2 a wrong call (nothing was run), 130 stopped. Exit code 3 of a script is the gate
of the engine (an edition, a policy, a missing tool): the last lines of the log name it.

`run` does not ask: a dangerous operation (`kind: dangerous`) is confirmed by the person before it is run - call
`check` first and put its question to them. A password is never an argument: it goes in the file of `--params`,
and the log shows it replaced.

## The window

| Section | Pages and their main operations |
|---|---|
| СЕТЬ (NETWORK) | ПОДКЛЮЧЕНИЕ: adapters (`network_adapter_apply`), LAN/Wi-Fi modes, Wi-Fi slots, `smb_network_login`; WI-FI: `network_wifi_status`, `network_wifi_connect`, export/import of profiles; DNS: `dns_status`, `dns_use_*`, `dns_repair`; РЕМОНТ: `network_status`, `network_backup`, `network_restore`, light/standard/nuclear repair, proxy; HOSTS: `bitrix_detect_endpoint`, `bitrix_status`, `bitrix_enable`, `bitrix_disable` |
| WSL И VM | WSL: `wsl_system_status`, `wsl_enable_features`, `wsl_update_engine`, `wsl_list_online`, `wsl_install_distro`, `wsl_install_from_file`; НАСТРОЙКА: apt, account, dev packages, micro, mc, neovim; ДИСТРИБУТИВ: `wsl_backup`, `wsl_clone`, `wsl_move`, `wsl_import_in_place`, `wsl_restore_from_backup`, `wsl_register_all_vhdx`, `wsl_delete`; UBUNTU: installer materials; HYPER-V: `virt_status`, `virt_optimization_status`, `virt_mode_*`, Hyper-V and Sandbox toggles |
| ДРАЙВЕРЫ (DRIVERS) | WINDOWS UPDATE: `driver_update_status`, block/unblock; ЗАМОК HWID: `hwid_driver_*`; NVIDIA: `nvidia_install`, driver block, `nvidia_audio_*`; DRIVER STORE: `driver_store_export`, `driver_store_restore`; АУДИТ: `driver_firmware_audit` |
| АССОЦИАЦИИ (DEFAULT APPS) | MICROSOFT `default_apps_microsoft`, EDGE `default_apps_edge`, ПОЛИТИКА `default_apps_policy`, ОТСЛЕЖИВАНИЕ `default_apps_watch`, СНИМОК `default_apps_snapshot`, ГРУППЫ `default_apps_groups`, ОТЧЁТ `default_apps_overview` - each a form whose action field picks the step |
| ЭКСПОРТ И ИМПОРТ | КОМПЛЕКТ `migration_*`; SSH `ssh_keykit_*`; СЕРТИФИКАТЫ `cert_*`; ДОСТУПЫ `access_*`; ШРИФТЫ И ОБОЛОЧКА `fonts_*`, `shell_*`; ЗАКЛАДКИ `browser_bookmarks_*`; AI CLI `ai_backup_export`, `ai_backup_import`, `ai_backup_merge` |
| СИСТЕМА (SYSTEM) | СРЕДА: `preflight_status`, `runtime_status`, long paths; ДИСКИ: `storage_inventory`, `storage_disk_details`, SSD/NVMe wizard, removable disk, WinRE; ОЧИСТКА: `codex_nuke_*`, `python_nuke_*`, `cache_cleaner_*`, `cleanup_workspace`; ПРОГРАММА: `open_tool_folder`, `ripgrep_status` |

`devops_cli.cmd describe` gives every operation with its fields and defaults. Beside the SOURCE and TARGET rows,
`cleanup_input_output` clears `input` and `output` of the program and nothing else.

## Rules

- **The owner is at the machine for live switches.** Network adapters, DNS, Wi-Fi, proxy, hosts, drivers, policies,
  the boot configuration and WSL features can cut the connection or need a reboot: do not run them in a check.
  Operations with `elevated=True` ask UAC even for a status (`network_status`).
- **Documented mechanisms only.** Default apps: DISM default app associations and the HKLM
  `DefaultAssociationsConfiguration` policy; never hand-edit `UserChoice` hashes; association snapshots read
  `UserChoice\ProgId` and never write it; no third-party association writer. `DefaultAssociationsConfiguration` is
  for Pro/Enterprise/Education/IoT Enterprise: on Home/Core apply refuses unless an explicit expert override is set.
  `Suggested="true"` applies once per policy version on Windows 11 22H2+. WSL: official `wsl.exe` commands. Wi-Fi:
  `netsh wlan`. SMB: `net use` in an external console; only computer/user pairs are stored. Drivers:
  `ExcludeWUDriversInQualityUpdate` and Device Installation Restrictions; NVIDIA HDMI/DP audio blocking targets only
  `HDAUDIO\FUNC_01&VEN_10DE...`, never broad `PCI\VEN_10DE...`. UCPD is diagnostic: never disabled or bypassed.
- **Edge is never removed**; it is kept from taking file types by HKLM policies, and WebView2 is protected.
- **A SYSTEM task never runs a file of the program folder**: any user may write there. The task of
  `Appx-Rearm.ps1` runs a copy in `%ProgramData%\Audion\AppxGuard\bin`, locked to Administrators and
  SYSTEM, with the built-in Windows PowerShell 5.1.
- **AppX and AppLocker run with Windows PowerShell 5.1** (`windows_powershell=True`): under PowerShell 7 its modules
  return `Deserialized.*` objects. Everything else resolves PowerShell by `resolve_pwsh()`: `App\AudionPs.exe`,
  then `pwsh.exe` from PATH, then `powershell.exe`. Use `run_ps1()` / `run_ps_command()` of
  `system_core\services\devops_tools.py`.
- **A backup before a change**: the boot configuration, associations, `hosts`, the network state, the Driver Store
  go to `backup\` first. Hosts depatch restores the pre-patch backup byte for byte, never line by line.
- **Interactive destructive wizards stay interactive**: the SSD/NVMe Reset Wizard opens in an external console;
  typed confirmations of `tools\...\Nuke.cmd` stay.
- **Secrets**: exports of SSH keys, PFX with private keys and Wi-Fi keys are secrets; never print their contents.
- **Nothing from neighbour folders**: runtime logic lives in `system_core\` and `tools\`; historical folders beside
  the project are read only for comparison and only when asked.

## Changing the program

- **Engine**: `system_core\` on the Python of `runtime\` (`install\requirements_full.in`: pyyaml, pytest).
  An operation is a node of `config\tool_manifest.yaml` with a concrete `service` (`module:function`), a
  `description` / `description_ru` that feeds the tooltip and the confirmation, `kind` and `risk_level`
  (readonly, project_write, user_write, system_change, destructive, secret_export). Group by user workflow, pair
  `backup / restore`, `export / import`, `block / unblock` in one `action_group`. A dynamic list (`options_source`)
  degrades to an error option, never to an empty section.
- **Window**: `Source\` (C#, Avalonia 12; shell of Audion Get Tools) built into `App\` by `install\Build-App.cmd`,
  builder step `[06] WINDOW`; it needs the .NET 10 SDK, checks the build in `._runtime\app_stage` and replaces
  `App\` only when everything passed. A new operation takes its place by `config\window_layout.yaml` (sections →
  pages → cards: `op`, `switch`, `pick`, `guests`, `block`, `tone`, `shared`, `away`), not by code of the window.
  Texts of the window are Russian with English pairs in `Source\config\i18n.json`. Icons:
  `py -3.12 Source\Tools\build_icons.py`. `Start.exe`: `install\Build-StartLauncher.cmd`.
  The window is checked off screen: `App\AudionDevOpsTools.exe --self-test --to FILE`; a Debug build takes
  screenshots section by section with `-Shot PATH`. Never with the real mouse; close only the processes of this
  project's path. After a build `Source\bin` and `Source\obj` are removed.
- **The record**: what the window hands the services is pinned by `tests\former_window_parameters.json`;
  a deliberate change goes to `ADDED_AFTER_RECORD`, `CHANGED_AFTER_RECORD` or `REMOVED_AFTER_RECORD` of
  `tests\test_model_record.py` with its reason, never into the record.
- **Checks**: `runtime\python.exe -m pytest -q`; `install\verify_portable_env.cmd` (environment, console command,
  built window); `runtime\python.exe system_core\doctor.py`. The list before a release: `docs\SMOKE_TEST_RU.md`.
- **Encoding**: every `.cmd` is UTF-8 without BOM with strict CRLF, every `.sh` UTF-8 without BOM with LF;
  `install\Check-CmdEncoding.cmd -Fix` checks and repairs. Child processes are read as bytes and decoded with
  fallbacks (UTF-8, UTF-16, OEM, cp1251); logs on disk are plain UTF-8 without colour codes.
- **Build and cleanup**: `builder_main.cmd` refreshes the components (runtime, fzf, ripgrep), not `App\`.
  `install\Clean-Install-Cache.cmd` removes download leftovers and `Source\bin`/`obj`; `cleanup_project.cmd` makes a
  release copy lean (it clears every backup folder, the project's and each pack's under `tools\`) and keeps `App\`.
- **Version**: `config\version.json`, SemVer, one bump per logical change set: MAJOR for an incompatible change of
  the console command, the window, the configuration, the data formats, documented paths or workflows, a removed
  capability; MINOR for a feature; PATCH for a fix; none for cleanup, a rebuild or regenerated outputs alone. The
  window and `AudionPs.exe` read their number from it at build time.
