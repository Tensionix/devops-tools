PYTHON NUKE
===========

Universal removal of every common Python footprint from Windows.

Covers:
  * Vanilla python.org installer (per-user + per-machine)
  * Microsoft Store Python (AppX, including provisioned image-level)
  * Python Launcher (PEP 397) py.exe at C:\Windows\py.exe
  * pipx, uv, conda (Miniconda / Anaconda / Miniforge / Mambaforge),
    both system-wide (C:\, C:\ProgramData) and per-user
  * Pip caches and config (pip.ini in %APPDATA% AND %LOCALAPPDATA%)
  * Poetry / PDM / virtualenv caches
  * .ipython / .jupyter user dirs
  * PATH entries (User + Machine if admin) - regex anchored so user
    folders containing "Python" mid-path are NOT touched
  * Env vars: PYTHONPATH, PYTHONHOME, PYTHONUSERBASE, PYTHONSTARTUP,
    PYTHONDONTWRITEBYTECODE, PYTHONIOENCODING, PYTHONUTF8,
    PIP_*, VIRTUAL_ENV, CONDA_*, UV_*, PIPX_*
  * Registry: HK*U\Software\Python, App Paths\python*.exe,
    Uninstall\{...} entries for Python/Anaconda/Miniconda/pipx/uv
  * Start Menu shortcuts whose target is python.exe / py.exe / IDLE /
    conda, and empty Python/Anaconda program folders left behind

Does NOT touch (by default):
  * Project venvs (.venv / venv folders under your projects)
  * The Microsoft Store app itself
  * ChatGPT / Codex / unrelated AppX
  * pwsh / Windows PowerShell
  * Microsoft App Execution Alias stubs in
        %LOCALAPPDATA%\Microsoft\WindowsApps\python.exe
        %LOCALAPPDATA%\Microsoft\WindowsApps\python3.exe
        %LOCALAPPDATA%\Microsoft\WindowsApps\py.exe
        %LOCALAPPDATA%\Microsoft\WindowsApps\idle.exe
    These are 0-byte reparse points managed by Windows itself, not part
    of any Python install. The on-disk file is paired with a toggle
    under Settings -> Apps -> Advanced app settings -> App execution
    aliases. Deleting ONLY the file while leaving the toggle enabled
    creates a half-broken state where Python CLI calls misbehave even
    after a fresh install. This tool always keeps those alias stubs.

FILES
-----
  Nuke.cmd               Double-click launcher (interactive UX).
                         Self-elevates via UAC, picks pwsh 7 if present
                         (PS 5.1 fallback), shows menu, runs the script,
                         pauses for review, returns to menu.
  Invoke-PythonNuke.ps1  Main script. Pure logic, never blocks on input.
                         Suitable for GUI / installer / scheduler use.
                         Modes: Audit / DryRun / Nuke.
  Logs\nuke-*.log        Transcript of each run (auto-created).

QUICK START
-----------
  1. Double-click Nuke.cmd
  2. Approve UAC
  3. Pick mode:
        [1] Audit    - list what would be removed
        [2] DryRun   - simulate (no changes)
        [3] NUKE     - actually remove (type NUKE to confirm)
        [4] Nuke + KeepWinget - skip winget uninstall pass
  4. Read result, press any key to return to menu, Q to quit

DIRECT INVOCATION (already-elevated GUI / shell)
------------------------------------------------
  pwsh -ExecutionPolicy Bypass -File .\Invoke-PythonNuke.ps1 -Mode Audit
  pwsh -ExecutionPolicy Bypass -File .\Invoke-PythonNuke.ps1 -Mode Nuke
  pwsh -ExecutionPolicy Bypass -File .\Invoke-PythonNuke.ps1 -Mode Nuke -KeepWinget

PARAMETERS
----------
  -Mode <Audit|DryRun|Nuke>     Required behaviour mode.
  -KeepWinget                   Skip the winget uninstall pass.
  -KeepProjectVenvs             Reserved (no-op today).
  -RemoveStoreAliases           Deprecated compatibility switch. Ignored:
                                WindowsApps App Execution Alias stubs
                                are always kept.
  -PathPattern <regex>          Override the regex used to identify
                                Python entries in PATH.
  -LogPath <path>               Override transcript path.

EXIT CODES
----------
   0    Clean / nothing to do.
   N    N artifacts remain (Nuke) or N artifacts found (Audit/DryRun).
   255  Fatal (Nuke mode without administrator rights).

NOTES
-----
- After a real Nuke, reboot before reinstalling Python so PATH and env
  vars fully refresh in all sessions.
- Recommended fresh install after the nuke:
    winget install --id Python.Python.3.12 -e --scope user
    pip config set global.require-virtualenv true
- The PATH regex is intentionally anchored. It only matches:
    ...\Programs\Python(\... or end)
    ...\Python3?<digits>(\Scripts)?(\... or end)
    ...\pylauncher(\... or end)
    ...\Miniconda3? / \Anaconda3?(\... or end)
    ...\pipx / \.pipx / \uv (\... or end)
  Custom user dirs like C:\dev\Python\samples are safe.
