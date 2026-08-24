# Codex Task — Layered (Staged) Snapshot for Association Defense

> **Historical document, delivered and then reworked (2026-07-27).** The brick
> exists as `Group-Snapshot.ps1` ("Groups" in the GUI), but it no longer uses
> SetUserFTA: it reads the registry and has no `-Apply`/`-ApplyAll` verbs.
> Treat the SetUserFTA parts below as history.

> **Second-auditor model.** This is a build specification, not finished code.
> Implement it against the LIVE machine, verifying real `SetUserFTA` behavior at
> each step. Where this spec and reality disagree, trust reality and flag the
> mismatch — do not force the spec.
>
> **Модель второго аудитора.** Это спецификация на сборку, не готовый код.
> Реализуй на ЖИВОЙ машине, проверяя реальное поведение `SetUserFTA` на каждом
> шаге. Где спецификация расходится с реальностью — верь реальности и сообщай о
> расхождении, не подгоняй под спецификацию.

---

## 1. Why / Зачем

Software is installed in stages. The user wants to **fix extension→ProgID
bindings incrementally**, group by group, as each program is installed — instead
of one monolithic snapshot of everything at once. This matches a hard fact about
SetUserFTA: a program's real ProgID is only knowable **after** it is installed
(especially PotPlayer "73h", FastStone, mpv, whose ProgIDs are custom). Staged
commits let the user freeze each group exactly when its program is present and
its ProgID is finally visible via `SetUserFTA get`.

Софт ставится поэтапно. Нужно **фиксировать связки расширение→ProgID
постепенно**, группа за группой, по мере установки программ — вместо одного
монолитного снапшота всего сразу. Это совпадает с фактом про SetUserFTA:
настоящий ProgID программы известен только **после** её установки (особенно
PotPlayer «73h», FastStone, mpv с кастомными ProgID). Поэтапные коммиты
позволяют замораживать каждую группу ровно тогда, когда её программа стоит и
ProgID наконец виден через `SetUserFTA get`.

---

## 2. Deliverable / Результат

A new brick `Layer-Snapshot.ps1`, sibling to `Golden-Snapshot.ps1`, sharing
`_Common.ps1`. Do NOT bloat `Golden-Snapshot.ps1` — monolithic and layered are
distinct usage models and stay in separate files (suite rule: clean single-
purpose bricks). The wrapper `Defense.ps1` gains a `Layers` key for `-Status`.

Новый брик `Layer-Snapshot.ps1`, рядом с `Golden-Snapshot.ps1`, общий
`_Common.ps1`. НЕ раздувать `Golden-Snapshot.ps1` — монолит и слои это разные
модели использования, держать в отдельных файлах (правило сюиты: чистые
однозадачные брики). Враппер `Defense.ps1` получает ключ `Layers` для `-Status`.

---

## 3. Layer model / Модель слоёв

### Storage / Хранение
```
snapshots/
├── Microsoft-Snapshot.<MACHINE>.txt      # existing monolithic snapshot (untouched)
└── layers/
    ├── photo.<MACHINE>.txt
    ├── audio.<MACHINE>.txt
    ├── video.<MACHINE>.txt
    ├── pdf.<MACHINE>.txt
    ├── browser.<MACHINE>.txt
    └── <custom-name>.<MACHINE>.txt        # optional free-form layers
```

Each layer file uses the same raw `ext, ProgID` format as the monolithic
snapshot (one binding per line, `#` comment header). A layer is a SUBSET of the
full map, scoped to one group of extensions.

Каждый файл слоя — тот же сырой формат `ext, ProgID`, что у монолитного снапшота
(одна связка на строку, шапка-комментарий `#`). Слой — это ПОДМНОЖЕСТВО полной
карты, ограниченное одной группой расширений.

### Default groups (confirm/adjust with the user) / Группы по умолчанию
Built-in extension sets. These come from the user's stated preferences; verify
on the live machine and adjust the extension lists as needed:

- **photo**: .jpg .jpeg .png .bmp .gif .tiff .webp .heic  (target: FastStone)
- **audio**: .flac .mp3 .wav .m4a .aac .ogg .opus .wv     (target: foobar2000 or AIMP)
- **video**: .mp4 .mkv .avi .mov .webm .flv .ts .m2ts      (target: PotPlayer 73h; mpv possible)
- **pdf**:   .pdf                                          (target: Acrobat Pro or Chrome)
- **browser**: protocols http https + .html .htm           (target: Chrome / ChromeHTML)

Group→extension mapping must be data-driven (a hashtable or JSON), so adding a
group or moving an extension is one edit, not code surgery.

Привязка группа→расширения должна быть data-driven (хеш-таблица или JSON), чтобы
добавить группу или перенести расширение — одна правка, не операция на коде.

---

## 4. Operations / Операции

Keep the trinity where natural, but layers need verbs that name the staged
nature. Suggested surface (confirm naming with the user):

| Operation | Suggested switch | Effect |
|-----------|------------------|--------|
| List layers | `-Status` | Show each layer: exists? entry count? drift vs live? |
| Commit a layer | `-Commit <group>` | `SetUserFTA get`, keep only this group's extensions, write the layer file |
| Apply a layer | `-Apply <group>` | Replay only that layer's bindings through SetUserFTA |
| Apply all layers | `-ApplyAll` | Replay every layer (photo+audio+video+...) in a defined order |
| Compose full | `-Compose` | Merge all layers into the monolithic Microsoft-Snapshot file |
| Custom layer | `-Commit <name> -Ext ".a,.b,.c"` | Free-form layer from an explicit extension list |

Reuse from `_Common.ps1`: `Start-BrickLog`/`Stop-BrickLog`, `Test-DryRun`,
`Find-Sufta` (lift from Golden-Snapshot or move to _Common). Honour `-DryRun` on
every mutating op (Commit/Apply/ApplyAll/Compose), exactly like the destructive
bricks already do.

Переиспользовать из `_Common.ps1`: логирование, `Test-DryRun`, `Find-Sufta`
(вынести из Golden-Snapshot или перенести в _Common). Соблюдать `-DryRun` на
каждой мутирующей операции.

---

## 5. Critical SetUserFTA mechanics to honour / Критичная механика SetUserFTA

Verify each before trusting. See README section "6a. Understanding SetUserFTA".

1. **Format is `.ext, ProgID`** — comma+space, extension WITH the dot, quoted as
   one arg. CONFIRM the exact `SetUserFTA get` output shape on the live machine;
   versions vary (tab vs comma, extra column). If it differs, adjust the parser
   in BOTH `Golden-Snapshot.ps1` and the new brick, and report it.
2. **SetUserFTA writes only the ProgID**, with a valid UserChoice hash. The
   ProgID→exe path lives in `HKCR\<ProgID>\shell\open\command` (installer's job).
   A layer that references a ProgID whose program is uninstalled will apply
   "successfully" yet click-fail. Consider a `verify` step that checks each
   layer's ProgID exists in HKCR and its command path resolves.
3. **Real ProgIDs are discovered, not invented.** Commit must read them from a
   live `get` AFTER the program is installed and one association is set by hand.
   Never hardcode ProgIDs for PotPlayer 73h / FastStone / mpv.
4. **Protocols** (http/https) use the same tool but confirm the get/set syntax
   for protocols vs file extensions — they can differ slightly. The `browser`
   layer depends on this.
5. **Idempotent + independent**: each `ext, ProgID` write is independent, so
   staged commits never disturb previously committed layers. This is the whole
   premise — preserve it (no "rewrite everything" on a single-group commit).

---

## 6. Interaction with existing bricks / Связь с существующими бриками

- `Golden-Snapshot.ps1` stays the monolithic safety rope. `-Compose` in the new
  brick can REGENERATE the monolithic file from layers, but must not change
  Golden-Snapshot's own behavior.
- `Drift-Watch.ps1` currently diffs against the monolithic snapshot. Optionally
  extend it to also report per-layer drift, but keep monolithic drift working.
- `Defense.ps1` wrapper: add `Layers` to the registry for `-Status` only
  (layered commit/apply are deliberate, never part of bulk enable/disable, same
  guardrail already applied to Snapshot).

---

## 7. Conventions (must match the suite) / Соглашения

- PowerShell, list-style subprocess args, no `shell=True` equivalent.
- Comments / user-facing output / this doc-derived help: ENGLISH only.
- Files: UTF-8 **without BOM**, **CRLF** line endings (see `.gitattributes`).
- Resolve `_Common.ps1` from the script's own folder, tools via E:\ → S:\ → script dir.
- `-Status` read-only and safe unelevated; mutating ops call `Assert-Admin` unless `-DryRun`.
- Logs: Commit/Apply/ApplyAll/Compose logged via transcript; Status not logged.

---

## 8. Verification pass (do on the live box) / Проход проверки (на живой машине)

1. `SetUserFTA get` — capture 5-10 raw lines; confirm parser format. **Report these lines back.**
2. Install one media app, set one association by hand, `-Commit <group> -DryRun`,
   inspect the "would write" output, then real `-Commit`.
3. `-Apply <group> -DryRun` then real apply; confirm no "your app was reset".
4. `-ApplyAll -DryRun`, confirm order and completeness.
5. `-Compose -DryRun`, confirm the merged monolithic file equals the union of layers.
6. Run `Invoke-ScriptAnalyzer` on the new brick; fix warnings.
7. Confirm CRLF/no-BOM on the new file.

---

## 9. Open questions for the user (Codex: ask, do not assume) / Вопросы пользователю

- Exact extension membership per group (the lists in §3 are a starting point).
- Final verb names (§4 suggestions vs the user's preference).
- Whether `browser` should include protocols, file types, or both.
- Whether to keep mpv as a custom layer or fold into `video`.
