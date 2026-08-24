CODEX NUKE
==========

Universal removal of the OpenAI Codex desktop app from Windows.
Cleans: Appx package, sandbox local users (CodexSandboxOffline/Online),
profile folders, firewall rules, Windows Search indexer entries,
AppModel StateRepository cache, RegisteredApplications, NotifyIconSettings,
MrtCache, IE audio policy entries, ProfileList, InstallService CategoryCache.

FILES
-----
  Nuke.cmd               Double-click launcher (interactive UX layer).
                         Self-elevates via UAC, shows a menu, calls
                         Invoke-CodexNuke.ps1, then pauses so you can
                         read the result before returning to the menu.
                         Prefers PowerShell 7 (pwsh), falls back to PS 5.
  Invoke-CodexNuke.ps1   Main script - pure logic, never blocks on input.
                         Suitable for embedding in a cmd wrapper, GUI
                         uninstaller, scheduled task or MSI custom action.
                         Modes: Audit / DryRun / Nuke.
  Logs\nuke-*.log        Transcript of each run (auto-created).
                         Override location with -LogPath <path>.

QUICK START
-----------
  1. Double-click Nuke.cmd.
  2. Approve the UAC prompt.
  3. Pick a mode:
        [1] Audit          - just list what would be removed.
        [2] DryRun         - simulate (no changes).
        [3] NUKE           - actually remove everything (type NUKE).
        [4] Nuke + KeepCaches - skip TrustedInstaller-protected caches
                                (StateRepository / MrtCache). Faster
                                and does not stop WSearch / SR.
        [5] SessionReset   - soft: kill Codex + clear session/cache state
                                only. Does NOT uninstall, does NOT touch
                                auth/config/registry/firewall. Use FIRST
                                when xhigh-compaction hangs your Codex -
                                restart the app afterwards; if the hang
                                survives, escalate to [3] NUKE.

WHEN TO USE WHICH MODE
----------------------
  Codex won't respond, compaction stuck
                                  -> [5] SessionReset, then relaunch
  SessionReset didn't fix it
  / install is corrupted
  / "Cannot find Codex.exe"
  / SSH broken / firewall weird   -> [3] NUKE, reboot, reinstall
  Just want to see the damage     -> [1] Audit
  Want to know what NUKE will do  -> [2] DryRun

DIRECT INVOCATION (already-elevated shell)
------------------------------------------
  powershell -ExecutionPolicy Bypass -File .\Invoke-CodexNuke.ps1 -Mode Audit
  powershell -ExecutionPolicy Bypass -File .\Invoke-CodexNuke.ps1 -Mode DryRun
  powershell -ExecutionPolicy Bypass -File .\Invoke-CodexNuke.ps1 -Mode Nuke
  powershell -ExecutionPolicy Bypass -File .\Invoke-CodexNuke.ps1 -Mode Nuke -KeepCaches -SkipReboot

PARAMETERS
----------
  -Mode <Audit|DryRun|Nuke>     Required behaviour mode.
  -KeepCaches                   Skip StateRepository + MrtCache cleanup.
  -SkipReboot                   Do not schedule locked files for delete
                                on next reboot.
  -KeepCliState                 Preserve ~/.codex/ (auth tokens, sessions).
                                Use ONLY if you also have the Codex CLI
                                (npm-installed, separate from the Store
                                Desktop App). Removing ~/.codex/ breaks
                                the CLI in a silent way per openai/codex
                                issue #14087: CLI launches and accepts
                                input but produces no response.
                                If you don't have / don't use the CLI,
                                leave this off.
  -SkipStoreReset               Skip the post-nuke wsreset.exe call.
                                By default, after a real Nuke we reset
                                the Microsoft Store cache so the next
                                Store-install of Codex doesn't try to
                                launch the deleted Codex.exe ("ghost
                                install"). Disable only if your GUI
                                handles Store sanitation separately.
  -PackageNamePattern <regex>   Default: ^OpenAI\.Codex
                                Matched against Appx Package.Name and
                                folder names under AppData\Local\Packages.
  -PackageInPathPattern <regex> Default: OpenAI\.Codex   (no ^ anchor)
                                Matched against registry VALUES that
                                contain paths like {GUID}\WindowsApps\
                                OpenAI.Codex_...\app\Codex.exe.
  -UserNamePattern <regex>      Default: ^CodexSandbox
  -FirewallRulePattern <regex>  Default: ^codex_
  -LogPath <path>               Override log file location.

EXIT CODES
----------
   0    Clean (Nuke mode) or nothing to do (Audit/DryRun).
   N    N artifacts remain (Nuke) or N artifacts found (Audit/DryRun).
   255  Fatal error (typically: not running as administrator).

KNOWN UPSTREAM ISSUES
---------------------
This nuke addresses a documented gap in Codex itself - per the OpenAI
Codex repo there is no clean uninstall on Windows. References:
  - openai/codex#15343  No way to do a clean uninstall of Codex CLI on
                        Windows that reverts system sandbox changes
  - openai/codex#12226  Codex install broke SSH
  - openai/codex#14087  Uninstalling Codex Desktop App breaks Codex CLI
                        (the CLI keeps shared state in ~/.codex/ that
                        the Store uninstaller corrupts). See
                        -KeepCliState above if affected.

NOTES
-----
- REBOOT after a real Nuke before reinstalling Codex.
  wsreset clears the on-disk Store cache, but in-memory state inside
  AppXSvc / StateRepository / ClipSVC and the Store process itself can
  survive a clean session. A reboot is the only 100% reliable way to
  drop that in-memory state. Without a reboot, a fresh Store install of
  Codex MAY succeed - but if it fails it will usually fail with the
  "Cannot find ...\Codex.exe" ghost-install error. The reboot is
  insurance, not a cure for our script.
- Microsoft Store may auto-reinstall Codex shortly after removal if your
  account has it linked. If you want it to stay gone:
    * Microsoft Store -> Library -> "..." next to Codex -> Hide
    * Settings -> Apps -> Advanced -> Microsoft Store -> turn off
      "App updates" (only if you don't mind disabling all Store updates).
  Or run this nuke periodically.
- Idempotent. Re-run any time. A clean machine reports 0.
- For TrustedInstaller-owned registry keys the script takes ownership
  via SeTakeOwnership, grants Administrators full control, then deletes.
  Services WSearch and StateRepository are briefly stopped and restarted
  for this to work (skip with -KeepCaches).
- Locked profile files (SFAP cache etc.) are scheduled for deletion on
  next reboot via MoveFileEx (skip with -SkipReboot).
- All actions are logged to nuke-<timestamp>.log in this folder.
