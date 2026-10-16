# Audion DevOps Tools - install notes

## Main Build Paths

Recommended entry point:

```bat
builder_main.cmd
```

Direct CMD Python environment build:

```bat
install\Build_Portable_Env_Build.cmd
```

Optional PowerShell route:

```bat
install\Build_Portable_Env.cmd
```

The PowerShell wrapper resolves PowerShell in this order: the program's own `App\AudionPs.exe` (when the window is built), `pwsh.exe` from PATH, then built-in `powershell.exe`.

Both builds ask before they overwrite `runtime\` and `wheelhouse\` (`/Y` skips the question) and never touch `backup\`.

## Current Builder Order And Dependency Hygiene

`builder_main.cmd` uses fixed numeric entries. Keep the bootstrap order stable: `[01] PYTHON ENV CMD`, `[02] PYTHON ENV PS`, `[03] FZF`, then project-specific payload installers and one-time maintenance/diagnostic actions below.

Current builder install/maintenance map:

```text
[01] PYTHON ENV CMD
[02] PYTHON ENV PS
[03] FZF
[06] WINDOW
[09] PORTABLE OFFLINE
[10] RIPGREP
[70] CLEAN INSTALL CACHE
[71] VERIFY / DOCTOR
[72] CMD ENCODING CHECK
[78] INIT FOLDERS
[90] PROJECT LAUNCHER
[95] OPEN install
[96] OPEN runtime
[97] OPEN wheelhouse
[98] OPEN licenses
[99] OPEN release
[00] EXIT
```

Project-specific payload entries before diagnostics:

[10] RIPGREP

Step `04` installed a portable PowerShell into `system_core\powershell` before 2.0.0. A build map that still names it gets a `[SKIP]` line that says so: the PowerShell of the program is `App\AudionPs.exe`, built with the window.

Dependency hygiene rules:

- Python Embedded tracks the latest `3.12.x`; do not pin a concrete patch version in docs or scripts.
- Use the active embedded Python `_pth` file for path edits; do not hard-code a concrete filename.
- Bootstrap installs must include `setuptools`, `wheel`, and `packaging` before building or installing project wheels.
- `runtime\`, `wheelhouse\`, `system_core\fzf.exe` and project-local `ripgrep\` are reproducible payloads. Install/update scripts may cleanly replace only their owned targets.
- `config\window_settings.json` and `config\terminal_commands.json` are the state of one machine's window (its look and folders, the history of the terminal line): `cleanup_project.cmd` removes the first and resets the second in a copy made for a release.
- GPL or unknown-license external tools are explicit install/update payloads. Prefer buttons of the window where the project exposes them, or fixed builder entries otherwise; do not silently bundle them as default source contents.
- `install\Clean-Install-Cache.cmd` / `.ps1` is the general install-cache cleanup. It removes transient `install\download\` artifacts (preserving `get-pip.py`), the installer staging dir `system_core\_fzf_tmp`, what building `App\` leaves in `bin` and `obj` of `Source\` and `Source\Ps\`, and Python bytecode caches outside runtime, wheelhouse, and user-data zones. The built window in `App\` stays.
- `cleanup_project.cmd` is a separate source/release cleanup tool. It can remove runtime payloads, user-output zones and backup snapshots after explicit confirmation, and it leaves `App\` alone; do not describe it as the general install-cache cleaner and do not wire it into install flow.

## Portable Python Flow

The core environment build creates managed folders, resolves the latest Python Embedded `3.12.x`, extracts it to `runtime\`, enables `import site` in `python3<minor>._pth`, downloads `get-pip.py`, installs `setuptools` / `wheel` / `packaging`, rebuilds `wheelhouse\`, installs the packages of `install\requirements_full.in` from the local wheelhouse, and verifies with `system_core\doctor.py`. The list holds what the engine and its tests run on (`pyyaml`, `pytest`); the window is not built from it.

If `runtime\` and `wheelhouse\` are already populated, install without the network:

```bat
install\install_portable_offline.cmd
```

Verify with:

```bat
install\verify_portable_env.cmd
```

It checks the environment (`system_core\doctor.py`), the console command (`devops_cli.cmd describe`) and the built window: `App\AudionDevOpsTools.exe` checks itself against the manifest of this version. Nothing in it needs the .NET SDK.

## The Window

The window is `App\AudionDevOpsTools.exe`, built from `Source\` (C#, Avalonia) with its own .NET runtime: a machine that runs the program needs nothing installed. Beside it stands `App\AudionPs.exe` - PowerShell 7 under the program's name (`Source\Ps`, Microsoft.PowerShell.SDK), sharing that runtime: the scripts of the operations, the console menus of `cli\` and `tools\`, the command line of the terminal and the scripts of the builder run with it, so no PowerShell of the machine decides how they behave. AppX and AppLocker operations deliberately run with the built-in Windows PowerShell 5.1. `Start.exe` in the root starts the window.

```bat
install\Build-App.cmd
install\Build-StartLauncher.cmd
```

`install\Build-App.cmd` is builder step `[06] WINDOW` and needs the .NET 10 SDK. It runs the tests of the model of the console command (`tests\test_model_record.py`) and of the dictionary of the window (`tests\test_window_i18n.py`), publishes into `._runtime\app_stage`, lets the built window check itself, compares what its forms hand the console command with the record of the parameters (`tests\test_window_values.py`), and only then replaces `App\`; a failed build leaves the working copy in place. The steps of a release update what the engine runs on and do not rebuild `App\`: run step `[06]` after a change in `Source\`.

`install\Build-StartLauncher.cmd` compiles `Start.exe` with the C# compiler of .NET Framework and embeds `system_core\icons\app.ico`. The launcher asks for administrator rights once; a "no" opens the window without them.

## Release Licensing

Third-party notices and license files are generated from the finalized staged release contents during release packaging. They are not generated during routine environment build/install steps.
