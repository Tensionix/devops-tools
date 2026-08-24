# Audion DevOps Tools — Association Defense: GUI Layer Tech Map

> **Historical document, delivered (2026-07-27).** The GUI layer described here
> exists: it is the DEFAULT APPS section of the NiceGUI shell, driven by
> `config/tool_manifest.yaml` and `system_core/services/devops_tools.py`. Brick
> names have moved on since this was written (`Remove-HijackerApps.ps1` is now
> `Microsoft-Apps.ps1` + `Appx-Rearm.ps1`, `Edge-DefaultBlock.ps1` is now
> `Edge-Debloat.ps1`). Read it as the design rationale, not as the current
> contract — for that see `README.md` and `docs/ASSOCIATION_DEFENSE_RU.md`.

> Handoff artifact for Codex. **Second-auditor model**: do not blindly scaffold
> a GUI. First verify each claim below against the actual `.ps1` sources, then
> design the layer around the verified contract. Flag any mismatch instead of
> silently working around it.
>
> Передаточный артефакт для Codex. **Модель второго аудитора**: не лепи GUI
> вслепую. Сначала сверь каждое утверждение ниже с реальными исходниками
> `.ps1`, затем проектируй слой вокруг проверенного контракта. О любом
> расхождении — сообщай, а не обходи молча.

---

## 0. What exists / Что уже есть

The CLI layer is complete and is the source of truth. The GUI is a **thin
presentation shell** over it — it must not reimplement logic, only invoke
bricks and render their output. This matches the suite rule: GUI is the primary
product, CLI brick is the engine; the GUI wraps, never forks, the logic.

CLI-слой готов и является источником истины. GUI — **тонкая презентационная
оболочка** над ним: не реализует логику заново, а только вызывает брики и
отображает их вывод. Это соответствует правилу сюиты: GUI — основной продукт,
CLI-брик — движок; GUI оборачивает логику, но не форкает её.

---

## 1. Brick contract (verify before building) / Контракт бриков

Each brick is a self-contained `.ps1` exposing exactly three switches plus
optional parameters. The GUI invokes them as subprocesses (list-based args, no
shell string concatenation, no `shell=True` equivalent).

| Brick (key) | Verbs | Extra params | Needs admin (enable/disable) | Edition gate |
|-------------|-------|--------------|------------------------------|--------------|
| `Remove` | Status/Enable/Disable | `-IncludeCamera` | Yes | none |
| `Edge` | Status/Enable/Disable | — | Yes | none |
| `AppX` | Status/Enable/Disable | — | Yes | **Pro/Enterprise** |
| `Defender` | Status/Enable/Disable | — | Yes | none |
| `Snapshot` | Status/Enable/Disable | `-Name`, `-Machine` | Yes | none |
| `Defense` (wrapper) | Status/Enable/Disable | `-Only <key>` | Yes | none |

Verification tasks for Codex:
1. Confirm the switch names and parameter names by reading each `param(...)` block.
2. Confirm exit codes: `0` ok, `2` missing `_Common.ps1`, `3` edition/tool gate, `1` runtime failure. Do not hardcode until verified.
3. Confirm `-Status` never mutates state (safe to call on a timer / refresh).

Задачи проверки для Codex:
1. Подтвердить имена ключей и параметров, читая каждый блок `param(...)`.
2. Подтвердить коды выхода: `0` ок, `2` нет `_Common.ps1`, `3` редакция/инструмент, `1` сбой. Не хардкодить до проверки.
3. Подтвердить, что `-Status` не меняет состояние (безопасен для таймера/обновления).

---

## 2. Recommended GUI architecture / Рекомендованная архитектура GUI

A single screen, one row per brick, plus a wrapper row at top. Each row is a
**state card**: name, current state badge, three action buttons, last-run log
toggle. This mirrors the trinity 1:1 and keeps the mental model identical to
the CLI.

Один экран, по строке на брик, плюс строка враппера сверху. Каждая строка —
**карточка состояния**: имя, бейдж текущего состояния, три кнопки действий,
переключатель лога последнего запуска. Зеркалит троицу 1:1 и сохраняет
ментальную модель идентичной CLI.

```
┌─ Defense (all) ───────────────────────────[Status][Enable][Disable]┐
├─ Remove Hijacker Apps      ● removed       [Status][Enable][Disable]│
├─ Edge Default-Block        ● active        [Status][Enable][Disable]│
├─ AppX Reinstall-Block      ⚠ Pro required  [Status][Enable][Disable]│
├─ Defender Exclusions       ● set           [Status][Enable][Disable]│
├─ Microsoft Snapshot        ◆ drift: 3      [Compare][Capture][Restore]│
└──────────────────────────────────────────────────────────────────┘
```

Design notes / Заметки по дизайну:
- Snapshot row relabels the verbs to Compare/Capture/Restore but maps to the same switches. Keep the mapping in one place.
- State badge colors come from the brick output, not guessed by the GUI: green = active/ok, yellow = off/partial, gray = unknown until first Status.
- Progressive disclosure (suite habit): show verb buttons by default; reveal raw log only on demand.

---

## 3. Invocation pattern / Шаблон вызова

```python
# Pseudocode — list-based args, never a shell string.
def run_brick(key: str, verb: str, *, only=None, include_camera=False,
              snap_name=None, machine=None) -> BrickResult:
    pwsh = resolve_pwsh()          # portable first: E:\Audion\Tools\PowerShell\pwsh.exe
    script = SCRIPTS[key]          # absolute path, resolved from module dir
    args = [pwsh, "-ExecutionPolicy", "Bypass", "-File", script, verb]
    if only:           args += ["-Only", only]
    if include_camera: args += ["-IncludeCamera"]
    if snap_name:      args += ["-Name", snap_name]
    if machine:        args += ["-Machine", machine]
    # capture stdout/stderr; map exit code; never inject user free-text into args
    return execute(args)
```

Contract rules / Правила контракта:
- Resolve `pwsh.exe`: portable instance first, then PATH. Never hardcode a single path.
- Elevation: Status needs none. Enable/Disable need admin — detect non-admin and offer a single UAC re-launch, do not silently fail.
- Parse state from stdout markers the bricks already print (ACTIVE/OFF/SET/DRIFT/MATCH), not by re-querying the registry from the GUI.

---

## 4. State refresh model / Модель обновления состояния

- On open: run every brick's `-Status` once, in parallel, populate badges.
- Manual "Refresh all" button re-runs all Status.
- After any Enable/Disable: auto-run that brick's Status to confirm the new state. Show the actual post-action state, never an optimistic assumption (suite rule: report truth, not intent).
- Snapshot drift count is part of its Status output — surface the number on the badge.

При открытии: один раз параллельно запустить `-Status` всех бриков. Кнопка
«Обновить всё» перезапускает все Status. После любого Enable/Disable —
авто-Status этого брика, показывать реальное состояние, а не оптимистичное
предположение (правило сюиты: показывать правду, а не намерение). Счётчик
дрифта снапшота — часть его Status, выводить число на бейдж.

---

## 5. Guardrails the GUI must enforce / Предохранители, которые GUI обязан соблюдать

1. **Snapshot is not in bulk Enable/Disable.** The "Defense (all)" row must call the wrapper, which already excludes Snapshot from bulk mutation. The GUI must not separately fire Snapshot Capture/Restore during an "all" action.
2. **Destructive confirmations.** Capture overwrites the baseline; Restore rewrites associations; Remove deletes apps. Each needs an explicit confirm dialog naming what changes.
3. **Edition gate visible.** If AppX brick returns the Home gate (exit 3), show it as a disabled row with reason, not a generic error.
4. **No free-text into args.** `-Name`/`-Machine` come from controlled inputs; sanitize to the same slug rules the brick uses for filenames.
5. **Defender honesty.** Never present a "disable Defender" affordance. The Defender card manages exclusions only and shows Tamper status read-only.

1. **Снапшот не в массовом Enable/Disable.** Строка «Defense (all)» зовёт враппер, который уже исключает снапшот из массовых изменений. GUI не должен отдельно запускать Capture/Restore снапшота при действии «all».
2. **Подтверждения деструктивных действий.** Capture перезаписывает эталон; Restore переписывает ассоциации; Remove удаляет приложения. Для каждого — явный диалог с указанием, что меняется.
3. **Видимый барьер редакции.** Если AppX-брик вернул барьер Home (код 3) — показывать как отключённую строку с причиной, а не общей ошибкой.
4. **Никакого free-text в аргументы.** `-Name`/`-Machine` — из контролируемых полей; санитизировать по тем же slug-правилам, что брик использует для имён файлов.
5. **Честность по Defender.** Никогда не показывать «отключить Defender». Карточка Defender управляет только исключениями и показывает статус Tamper только на чтение.

---

## 6. Suggested manifest shape / Предлагаемая форма манифеста

If you later add a declarative manifest (suite convention), shape it so the GUI
is fully data-driven and adding brick #6 means one manifest entry, no GUI code.

```json
{
  "bricks": [
    {
      "key": "Remove",
      "title": "Remove Hijacker Apps",
      "script": "Remove-HijackerApps.ps1",
      "verbs": { "status": "-Status", "enable": "-Enable", "disable": "-Disable" },
      "params": [{ "name": "IncludeCamera", "flag": "-IncludeCamera", "type": "bool" }],
      "needs_admin": ["enable", "disable"],
      "destructive": ["enable"],
      "edition": "any"
    }
  ]
}
```

Codex task: derive this manifest from the actual scripts, then drive the GUI off
it. Verify every field against the source before trusting it.

Задача Codex: вывести манифест из реальных скриптов, затем строить GUI на его
основе. Каждое поле сверить с источником перед тем, как доверять.

---

## 7. Out of scope for the GUI / Вне зоны GUI

- Setting per-extension ProgIDs — Windows guards that choice with a per-user hash; this GUI records and compares, it does not write it.
- Editing snapshot files by hand — the GUI shows drift and triggers capture/restore; raw editing stays in git/editor.
- Any Defender bypass — explicitly forbidden.

- Выставление ProgID по расширениям — этот выбор Windows защищает хешем пользователя; GUI его фиксирует и сравнивает, но не пишет.
- Ручное редактирование файлов снапшота — GUI показывает дрифт и запускает capture/restore; правка вручную — в git/редакторе.
- Любой обход Defender — явно запрещён.
