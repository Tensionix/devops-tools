# Audion DevOps Tools — Association Defense: Codex Handoff

> **Historical document, partly superseded (2026-07-27).** SetUserFTA has been
> removed from the project. Snapshots now read `HKCU ... UserChoice\ProgId`
> straight from the registry, there is no restore/apply verb anywhere, and
> `Layer-Snapshot.ps1` is now `Group-Snapshot.ps1`. Every SetUserFTA mention
> below describes how it used to work, not how it works now. Current behaviour:
> `README.md` section 6a and `docs/ASSOCIATION_DEFENSE_RU.md`.

> **Second-auditor model.** This document hands the brick set to Codex for
> review, integration, and (later) a GUI layer. Codex must **independently
> verify** every claim here against the actual sources before acting on it.
> Do not blindly apply — confirm, then proceed, and flag any mismatch.
>
> **Модель второго аудитора.** Документ передаёт набор бриков Codex для ревью,
> интеграции и (позже) GUI-слоя. Codex обязан **независимо проверить** каждое
> утверждение по реальным исходникам, прежде чем действовать. Не применять
> вслепую — сначала подтвердить, затем делать, о расхождениях сообщать.

---

## 1. Purpose / Назначение

A set of version-independent PowerShell bricks that stop Windows 11 (25H2) and
Edge from hijacking file/protocol associations, plus a snapshot safety rope and
a drift watcher. The bricks are the engine; a future NiceGUI layer is a thin
shell over them (see `GUI-TECHMAP.md`).

Набор версионно-независимых PowerShell-бриков, не дающих Windows 11 (25H2) и
Edge перехватывать файловые/протокольные ассоциации, плюс страховочный снапшот и
сторож дрифта. Брики — движок; будущий NiceGUI-слой — тонкая оболочка над ними
(см. `GUI-TECHMAP.md`).

---

## 2. Inventory / Состав

| File | Role | Run directly? |
|------|------|---------------|
| `_Common.ps1` | Shared helpers: admin check, registry, logging, dry-run, toast | No (dot-sourced) |
| `Remove-HijackerApps.ps1` | Remove Photos/Films&TV/Media Player/Clipchamp (+opt Camera) | Yes |
| `Edge-DefaultBlock.ps1` | Block Edge default/association grab via policy | Yes |
| `AppX-ReinstallBlock.ps1` | AppLocker deny rules vs reinstall (Pro/Enterprise) | Yes |
| `Defender-Exclusions.ps1` | Exclude all non-system drive roots + processes | Yes |
| `Golden-Snapshot.ps1` | "Microsoft Snapshot" capture/compare/restore (SetUserFTA) | Yes |
| `Drift-Watch.ps1` | At-logon scheduled task, toasts on drift (warn only) | Yes |
| `Defense.ps1` | Wrapper over all bricks (`-Only <key>`) | Yes |
| `.gitattributes` | Pin CRLF/UTF-8 across machines | n/a |
| `README.md` | Full bilingual user/operator manual | n/a |
| `GUI-TECHMAP.md` | GUI design contract for Codex | n/a |
| `CODEX-HANDOFF.md` | This file | n/a |

---

## 3. Verified conventions / Проверенные соглашения

Codex: confirm each by reading the sources. Do not trust this list alone.

1. **Trinity verbs.** Every brick + wrapper expose `-Status` / `-Enable` /
   `-Disable`. Snapshot maps these to compare/capture/restore; Drift-Watch adds
   an internal `-RunCheck`.
2. **Exit codes.** `0` ok; `1` runtime failure; `2` missing `_Common.ps1` or
   prerequisite; `3` edition/tool gate (e.g. AppLocker on Home, SetUserFTA absent).
   Verify each `exit` statement before the GUI depends on these.
3. **Status is read-only.** Safe to call unelevated and on a timer.
4. **Enable/Disable need admin** (except in `-DryRun`). They call `Assert-Admin`.
5. **`-DryRun`** exists on the destructive bricks only (`Remove-HijackerApps`,
   `Golden-Snapshot`). It skips `Assert-Admin` and performs no mutation.
6. **Logging.** Enable/Disable open a transcript under `.\logs\` (fallback
   `E:\Audion\Logs\...`, `S:\...`), rotated at 30 days. Status is not logged.
7. **Line endings.** All text files are CRLF, UTF-8 **without BOM**. `.gitattributes` pins this.
8. **Subprocess discipline.** No `shell=True` equivalent; SetUserFTA and pwsh are
   invoked with list-style args. The GUI must follow the same rule.
9. **Path resolution.** Tools resolved with fallback order E:\ → S:\ → script dir.
   `_Common.ps1` is loaded from each script's own folder, never the CWD.

---

## 4. Output markers the GUI will parse / Маркеры вывода для GUI

The GUI reads state from stdout, not by re-querying the system. Confirm these
strings in the sources; if you change a brick's output, update the GUI parser
and the Pester contract (if added) together.

| Brick | Key markers |
|-------|-------------|
| Edge | `GUARD: ACTIVE` / `GUARD: PARTIAL/OFF`; per-key `OK` / `OFF` |
| AppX | `GUARD: ACTIVE` / `GUARD: OFF`; `AppIDSvc: <state>` |
| Defender | `RealTimeProtection`, `TamperProtection`; `[SET]` / `[---]` per item |
| Remove | per-target `INSTALLED`/`absent`, `PROVISIONED`/`none` |
| Snapshot | `DRIFT` / `NEW` / `MATCH`; restore `Applied: N, Failed: N` |
| Drift-Watch | `drift-watch.log` lines: `DRIFT N` / `OK no drift` |

---

## 5. Known caveats (verify on real hardware) / Известные оговорки

These are flagged honestly rather than hidden. Codex should reproduce and
confirm, not assume.

1. **AppLocker policy-object constructor** (`AppX-ReinstallBlock.ps1`): the
   allow→deny flip uses `[...PolicyModel.AppLockerPolicy]::FromXml(...)`, which
   can behave differently across PowerShell builds. Fallback path:
   `Set-AppLockerPolicy -XmlPolicy`. Test before trusting.
2. **Toast App ID** (`Drift-Watch.ps1` / `Show-Toast`): uses the system
   PowerShell App ID. May be suppressed by Focus Assist or if PowerShell is not
   a registered toast source. On failure it falls back to the console + log, so
   the signal is never lost. Consider a Start-Menu shortcut App ID for reliability.
3. **Drift-Watch principal**: runs Limited (reading associations needs no admin).
   If `SetUserFTA get` hits a permission wall on a given box, raise the run level.
4. **Snapshot ProgID stability**: raw `SetUserFTA get` dumps are per-machine.
   Restore can fail if a program changed its ProgID across versions (PotPlayer
   73h, FastStone, mpv are the likely offenders) — recapture after such updates.
5. **Defender drive-wide exclusions**: excluding a drive does not silence
   SmartScreen on freshly downloaded executables (separate mechanism).
6. **No static run performed here**: scripts were authored offline; only static
   checks (brace/paren balance, CRLF, no-BOM) were done. Codex should run
   `Invoke-ScriptAnalyzer` and a parse pass (`[scriptblock]::Create`) on each file.

---

## 6. Suggested verification pass for Codex / Предлагаемый проход проверки

1. Parse every `.ps1` with PSScriptAnalyzer; report warnings/errors.
2. Confirm the param blocks match Section 3 (verbs, `-DryRun`, `-IncludeCamera`, `-Name`, `-Machine`, `-Only`, `-RunCheck`).
3. Confirm exit codes match Section 3.2.
4. Dry-run the destructive bricks (`-Enable -DryRun`, `-Disable -DryRun`) and diff the "would do" output against expectations.
5. On a Pro test box: `-Status` → `-Enable` → `-Status` for each brick; capture logs.
6. Install Drift-Watch, run `-RunCheck` manually, confirm log line + toast (or documented fallback).
7. Only then design the GUI per `GUI-TECHMAP.md`, deriving a manifest from the verified contract.

---

## 6b. Pending build task / Отложенная задача на сборку

A separate spec, `CODEX-TASK-LayeredSnapshot.md`, defines a **layered (staged)**
snapshot brick (`Layer-Snapshot.ps1`) that lets the user fix extension→ProgID
bindings group by group as software is installed in stages, instead of one
monolithic snapshot. Implement it against the live machine per that spec; it
depends on confirming the real `SetUserFTA get` output format first.

Отдельная спецификация `CODEX-TASK-LayeredSnapshot.md` описывает **слоёный
(поэтапный)** брик снапшота (`Layer-Snapshot.ps1`): фиксировать связки
расширение→ProgID группами по мере поэтапной установки софта, вместо одного
монолитного снапшота. Реализовать на живой машине по той спецификации; сначала
подтвердить реальный формат вывода `SetUserFTA get`.

---

## 7. Out of scope / Вне зоны

- Setting per-extension ProgIDs — belongs to the `associations` module / SetUserFTA.
- Any permanent Defender disable or Tamper Protection bypass — forbidden.
- Editing snapshot files by hand — use capture/restore + git.
