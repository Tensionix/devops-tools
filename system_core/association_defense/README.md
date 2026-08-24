# Audion DevOps Tools — Association Defense

> Bilingual document. Each section is **English first**, then **Russian** (`— RU —`).
> Двуязычный документ. Каждый раздел сначала **на английском**, затем **на русском** (`— RU —`).

Version-independent PowerShell bricks that stop Windows 11 (25H2) and Microsoft
Edge from hijacking file and protocol associations. Nothing here depends on app
versions, install paths, or ProgIDs — the bricks operate on policies,
packaged-app rules, Defender exclusions, and association snapshots, so they port
cleanly across all your machines. Setting the per-extension ProgID choices is a
separate job, done through the Policy tab (DISM `AppAssociations.xml` plus the
HKLM `DefaultAssociationsConfiguration` policy) — see §6a for why.

**— RU —**
Версионно-независимые PowerShell-брики, которые не дают Windows 11 (25H2) и
Microsoft Edge перехватывать файловые и протокольные ассоциации. Ничто здесь не
зависит от версий программ, путей установки или ProgID — брики работают на
уровне политик, правил для пакетов, исключений Defender и снимков ассоциаций,
поэтому переносятся между всеми твоими машинами без правок. Выставление ProgID
по расширениям — отдельная работа вкладки ПОЛИТИКА (DISM `AppAssociations.xml`
плюс политика HKLM `DefaultAssociationsConfiguration`), почему так — см. §6a.

---

## 1. The "holy trinity" — three verbs / «Святая троица» — три глагола

The guard bricks and the wrapper expose exactly three switches. `-Status` is
always read-only and safe to run unelevated. `-Enable` and `-Disable` change
system state and require an elevated session.

| Verb | Meaning (guard bricks) | Meaning for `Golden-Snapshot.ps1` |
|------|------------------------|-----------------------------------|
| `-Status`  | Report current state, no changes | Compare live state vs baseline (drift) |
| `-Enable`  | Apply the guard | Capture the baseline |
| `-Disable` | Remove the guard | **not available** — see §6a |

Two bricks speak their own verbs, because "enable/disable" says nothing useful
about them: `Microsoft-Apps.ps1` uses `-Remove` / `-Restore` / `-Provision`, and
`Group-Snapshot.ps1` uses `-Commit <group>` / `-Compose`.

**— RU —**
Брики-защиты и враппер имеют ровно три ключа. `-Status` всегда только читает и
безопасен без прав администратора. `-Enable` и `-Disable` меняют состояние
системы и требуют запуска от имени администратора.

| Глагол | Смысл (брики-защиты) | Смысл для `Golden-Snapshot.ps1` |
|--------|-----------------------|-----------------------------------|
| `-Status`  | Показать состояние, без изменений | Сравнить текущее с эталоном (дрифт) |
| `-Enable`  | Включить защиту | Снять эталон |
| `-Disable` | Снять защиту | **нет такого ключа** — см. §6a |

У двух бриков глаголы свои, потому что «включить/выключить» о них ничего не
говорит: у `Microsoft-Apps.ps1` это `-Remove` / `-Restore` / `-Provision`, у
`Group-Snapshot.ps1` — `-Commit <группа>` / `-Compose`.

---

## 2. Brick overview / Обзор бриков

| Brick | Guards against | Mechanism | Edition |
|-------|----------------|-----------|---------|
| `Microsoft-Apps.ps1` | In-box apps (Photos / Films&TV / Media Player / Clipchamp and 27 more) grabbing associations | Appx/DISM removal, restore, re-provision | Any |
| `Appx-Rearm.ps1` | A feature update re-provisioning what you removed | Stored app list + scheduled re-apply task | Any |
| `Edge-Debloat.ps1` | Edge nagging for default + reclaiming associations | HKLM policy keys (WebView2 stays protected) | Any |
| `AppX-ReinstallBlock.ps1` | Removed apps returning after feature updates | AppLocker deny rules | **Pro/Enterprise** |
| `Defender-Exclusions.ps1` | Defender I/O drag + false positives on your tools | Defender path/process exclusions | Any |
| `Golden-Snapshot.ps1` | Any future association drift Redmond introduces | Registry capture/compare (whole map) | Any |
| `Group-Snapshot.ps1` | The same drift, recorded group by group as apps arrive | Registry capture/compare (per group) | Any |
| `Drift-Watch.ps1` | Silent drift you would notice weeks later | At-logon scheduled check + toast | Any |
| `Defense.ps1` | — | Wrapper over all bricks | Any |
| `_Common.ps1` | — | Shared helper library (not run directly) | — |

**— RU —**

| Брик | От чего защищает | Механизм | Редакция |
|------|-------------------|----------|----------|
| `Microsoft-Apps.ps1` | Встроенные приложения (Photos / Кино и ТВ / Media Player / Clipchamp и ещё 27), перехватывающие ассоциации | Удаление/возврат/перепровижининг через Appx и DISM | Любая |
| `Appx-Rearm.ps1` | Feature-апдейт возвращает то, что ты удалил | Сохранённый список + задача повторного применения | Любая |
| `Edge-Debloat.ps1` | Edge клянчит дефолт и забирает ассоциации | Ключи политик HKLM (WebView2 защищён) | Любая |
| `AppX-ReinstallBlock.ps1` | Возврат удалённых приложений после feature-апдейтов | Deny-правила AppLocker | **Pro/Enterprise** |
| `Defender-Exclusions.ps1` | Тормоза I/O от Defender и ложные срабатывания на твоих инструментах | Исключения путей/процессов Defender | Любая |
| `Golden-Snapshot.ps1` | Любой будущий дрифт ассоциаций от Редмонда | Снятие и сравнение по реестру (вся карта) | Любая |
| `Group-Snapshot.ps1` | Тот же дрифт, но фиксируется группами по мере установки программ | Снятие и сравнение по реестру (по группам) | Любая |
| `Drift-Watch.ps1` | Тихий дрифт, который заметишь через недели | Проверка задачей при входе + toast | Любая |
| `Defense.ps1` | — | Враппер над всеми бриками | Любая |
| `_Common.ps1` | — | Общая библиотека хелперов (не запускается напрямую) | — |

---

## 3. `Microsoft-Apps.ps1` + `Appx-Rearm.ps1`

### English

`Microsoft-Apps.ps1` removes and restores the in-box Microsoft apps that grab
photo / audio / video / document associations. Removing the installed package
frees the associations; removing the provisioned copy keeps new user profiles
clean. Everything uses documented Appx/DISM calls — no protected-state hacks.

The catalog holds 31 apps and can be targeted three ways: `-Target All`,
`-Target group:media` (families: `media`, `xbox`, `social`, `news`, `tools`) or
an explicit comma-separated list such as `-Target ZuneMusic,ZuneVideo`.

| Action | Command | Effect |
|--------|---------|--------|
| Status | `.\Microsoft-Apps.ps1 -Status -Target All` | Installed / provisioned state per app |
| Remove | `.\Microsoft-Apps.ps1 -Remove -Target ZuneMusic,ZuneVideo` | Removes installed (AllUsers) + provisioned copies |
| Restore | `.\Microsoft-Apps.ps1 -Restore -Target group:media` | Staged manifest → family name → Store |
| Provision | `.\Microsoft-Apps.ps1 -Provision -Target Photos` | Re-provisions only, so new profiles get the app |

Removal alone is not permanent: a feature update can re-provision the very
packages you removed. `Appx-Rearm.ps1` stores the chosen list and registers a
scheduled task that re-applies the removal when the build changes or a removed
package reappears. On Pro/Enterprise, pair it with `AppX-ReinstallBlock.ps1`.

| Action | Command | Effect |
|--------|---------|--------|
| Status | `.\Appx-Rearm.ps1 -Status` | Task state, stored app list, last check result |
| Enable | `.\Appx-Rearm.ps1 -Enable -Target ZuneMusic,ZuneVideo` | Stores the list, registers the re-apply task |
| Disable | `.\Appx-Rearm.ps1 -Disable` | Removes the task (the stored list is kept) |
| RunCheck | `.\Appx-Rearm.ps1 -RunCheck` | One re-apply pass now (what the task calls) |

### — RU —

`Microsoft-Apps.ps1` удаляет и возвращает встроенные приложения Microsoft,
перехватывающие ассоциации фото / аудио / видео / документов. Удаление
установленного пакета освобождает ассоциации; удаление provisioned-копии
оставляет чистыми новые профили. Всё — на документированных вызовах Appx/DISM,
без обходов защищённого состояния.

В каталоге 31 приложение, цель задаётся тремя способами: `-Target All`,
`-Target group:media` (семейства: `media`, `xbox`, `social`, `news`, `tools`)
или явным списком через запятую, например `-Target ZuneMusic,ZuneVideo`.

| Действие | Команда | Эффект |
|----------|---------|--------|
| Статус | `.\Microsoft-Apps.ps1 -Status -Target All` | Состояние installed / provisioned по каждому |
| Удалить | `.\Microsoft-Apps.ps1 -Remove -Target ZuneMusic,ZuneVideo` | Удаляет установленные (AllUsers) и provisioned-копии |
| Вернуть | `.\Microsoft-Apps.ps1 -Restore -Target group:media` | Staged-манифест → family name → Store |
| Перепровижинить | `.\Microsoft-Apps.ps1 -Provision -Target Photos` | Только перепровижининг, чтобы новые профили получили приложение |

Одно удаление не вечно: feature-апдейт может перепровиженить ровно те пакеты,
которые ты снёс. `Appx-Rearm.ps1` запоминает выбранный список и ставит задачу
планировщика, которая повторяет удаление при смене сборки или возврате пакета.
На Pro/Enterprise используй его в паре с `AppX-ReinstallBlock.ps1`.

| Действие | Команда | Эффект |
|----------|---------|--------|
| Статус | `.\Appx-Rearm.ps1 -Status` | Состояние задачи, сохранённый список, результат последней проверки |
| Включить | `.\Appx-Rearm.ps1 -Enable -Target ZuneMusic,ZuneVideo` | Сохраняет список, регистрирует задачу |
| Откат | `.\Appx-Rearm.ps1 -Disable` | Удаляет задачу (список сохраняется) |
| RunCheck | `.\Appx-Rearm.ps1 -RunCheck` | Один прогон повторного применения сейчас |

---

## 4. `Edge-Debloat.ps1`

### English

Stops Edge from pushing itself: nagging to become the default browser, running
in the background, opening promo tabs and reclaiming file/protocol
associations. Pure policy under `HKLM:\SOFTWARE\Policies\Microsoft\Edge`;
independent of the Edge build. Policy outranks user choice, which is why this is
the cleanest lever available.

Edge is never uninstalled, and **WebView2 is explicitly protected** — its
installation and updates stay pinned to "allowed", because many applications
render their UI with it.

| Level | What it does |
|-------|--------------|
| `Calm` | No default-browser nagging, no first-run flow, no background mode, no promo tabs |
| `Quiet` | Calm plus sidebar, Shopping, Collections, feedback and personalization off; Beta/Dev/Canary channels blocked |

| Action | Command | Effect |
|--------|---------|--------|
| Status | `.\Edge-Debloat.ps1 -Status` | Every managed value, the WebView2 state and Edge tasks |
| Enable | `.\Edge-Debloat.ps1 -Enable -Level Calm` | Applies the chosen level |
| Disable | `.\Edge-Debloat.ps1 -Disable` | Removes only the values this brick manages |
| WebView2 | `.\Edge-Debloat.ps1 -RepairWebView2` | Installs the official Evergreen WebView2 Runtime |

A sign-out or reboot ensures every Edge surface picks up the change.

### — RU —

Отучает Edge продвигать себя: клянчить роль браузера по умолчанию, крутиться в
фоне, открывать промо-вкладки и забирать файловые/протокольные ассоциации.
Чистые политики в `HKLM:\SOFTWARE\Policies\Microsoft\Edge`, без зависимости от
сборки Edge. Политика выше пользовательского выбора — поэтому это самый чистый
рычаг.

Edge никогда не удаляется, а **WebView2 защищён явно**: его установка и
обновления зафиксированы как «разрешено», потому что множество приложений
рисует на нём свой интерфейс.

| Уровень | Что делает |
|---------|------------|
| `Calm` | Не клянчит дефолт, нет first-run, нет фонового режима и промо-вкладок |
| `Quiet` | Всё из Calm плюс выключены боковая панель, Shopping, Collections, отзывы и персонализация; каналы Beta/Dev/Canary заблокированы |

| Действие | Команда | Эффект |
|----------|---------|--------|
| Статус | `.\Edge-Debloat.ps1 -Status` | Все управляемые значения, состояние WebView2 и задачи Edge |
| Включить | `.\Edge-Debloat.ps1 -Enable -Level Calm` | Применяет выбранный уровень |
| Откат | `.\Edge-Debloat.ps1 -Disable` | Снимает только те значения, которыми управляет брик |
| WebView2 | `.\Edge-Debloat.ps1 -RepairWebView2` | Ставит официальный Evergreen WebView2 Runtime |

Выход из системы или перезагрузка гарантируют, что все поверхности Edge
подхватят изменение.

---

## 5. `AppX-ReinstallBlock.ps1`  (Pro/Enterprise only)

### English

Blocks Windows from reinstalling the hijacker apps on feature updates, using
AppLocker packaged-app **deny** rules plus the Application Identity service
(`AppIDSvc`), which AppLocker needs to enforce. Package family names are stable
across versions, so the rules survive updates. This is the **"keep removed"**
layer that complements `Microsoft-Apps.ps1`.

| Action | Command | Effect |
|--------|---------|--------|
| Status | `.\AppX-ReinstallBlock.ps1 -Status` | Shows `AppIDSvc` state + any `Audion-Block` deny rules |
| Enable | `.\AppX-ReinstallBlock.ps1 -Enable` | Adds deny rules, sets `AppIDSvc` to Automatic + starts it |
| Disable | `.\AppX-ReinstallBlock.ps1 -Disable` | Removes only the `Audion-Block` rules; leaves other policy intact |

Rules are tagged `Audion-Block` so `-Disable` removes only ours. Requires
Windows Pro or Enterprise — the brick refuses to run on Home and points you to
provisioned-removal instead. If the AppLocker policy-object constructor errors
on a given PowerShell build, fall back to importing the XML policy directly
(`Set-AppLockerPolicy -XmlPolicy`).

### — RU —

Не даёт Windows переустанавливать приложения-перехватчики при feature-апдейтах —
через **deny**-правила AppLocker для пакетов плюс службу Application Identity
(`AppIDSvc`), без которой AppLocker не применяется. Имена семейств пакетов
стабильны между версиями, поэтому правила переживают апдейты. Это слой
**«держать удалённым»**, дополняющий `Microsoft-Apps.ps1`.

| Действие | Команда | Эффект |
|----------|---------|--------|
| Статус | `.\AppX-ReinstallBlock.ps1 -Status` | Состояние `AppIDSvc` + наличие deny-правил `Audion-Block` |
| Включить | `.\AppX-ReinstallBlock.ps1 -Enable` | Добавляет deny-правила, ставит `AppIDSvc` в Automatic и запускает |
| Откат | `.\AppX-ReinstallBlock.ps1 -Disable` | Удаляет только правила `Audion-Block`, чужую политику не трогает |

Правила помечены тегом `Audion-Block`, поэтому `-Disable` снимает только наши.
Нужна Windows Pro или Enterprise — на Home брик откажется работать и подскажет
использовать provisioned-removal. Если конструктор объекта политики AppLocker
ругнётся на конкретной сборке PowerShell — откатывайся на прямой импорт
XML-политики (`Set-AppLockerPolicy -XmlPolicy`).

---

## 6. `Defender-Exclusions.ps1`

### English

Manages Microsoft Defender exclusions so it stops eating I/O and false-flagging
your own scripts and tools — **without disabling Defender**. Per your explicit
choice, it excludes **every mounted drive root except the system drive**; drive
letters are read live from `Get-PSDrive`, so no phantom letters are written and
new drives are picked up on the next `-Enable`. Process exclusions: `ffmpeg.exe`,
`VSPipe.exe`, `python.exe`, `pwsh.exe`.

| Action | Command | Effect |
|--------|---------|--------|
| Status | `.\Defender-Exclusions.ps1 -Status` | Shows real-time + Tamper state, then each drive/process exclusion |
| Enable | `.\Defender-Exclusions.ps1 -Enable` | Adds the drive-root + process exclusions |
| Disable | `.\Defender-Exclusions.ps1 -Disable` | Removes the Audion exclusion set |

This brick **never** bypasses Tamper Protection — it only *reports* its state.
Permanently disabling Defender from script is blocked by Windows by design, and
bypasses break the security stack after updates. Note: excluding a drive does
not silence SmartScreen on freshly downloaded executables — that is a separate
mechanism handled in Edge/Explorer.

### — RU —

Управляет исключениями Microsoft Defender, чтобы он перестал есть I/O и ложно
флагать твои скрипты и инструменты — **не отключая сам Defender**. По твоему
явному выбору исключаются **все смонтированные корни дисков, кроме системного**;
буквы читаются вживую через `Get-PSDrive`, поэтому фантомные не пишутся, а новые
диски подхватятся при следующем `-Enable`. Исключения процессов: `ffmpeg.exe`,
`VSPipe.exe`, `python.exe`, `pwsh.exe`.

| Действие | Команда | Эффект |
|----------|---------|--------|
| Статус | `.\Defender-Exclusions.ps1 -Status` | Показывает real-time + статус Tamper, затем исключения дисков/процессов |
| Включить | `.\Defender-Exclusions.ps1 -Enable` | Добавляет исключения корней дисков + процессов |
| Откат | `.\Defender-Exclusions.ps1 -Disable` | Удаляет набор исключений Audion |

Этот брик **никогда** не обходит Tamper Protection — только *показывает* его
статус. Постоянное отключение Defender из скрипта заблокировано Windows by
design, а обходы ломают security-стек после апдейтов. Замечание: исключение
диска не глушит SmartScreen на свежескачанных .exe — это отдельный механизм,
управляемый в Edge/проводнике.

---

## 6a. How associations are read / Как читаются ассоциации

`Golden-Snapshot.ps1`, `Group-Snapshot.ps1` and `Drift-Watch.ps1` read the live
association map straight from the registry. No third-party helper is involved.

`Golden-Snapshot.ps1`, `Group-Snapshot.ps1` и `Drift-Watch.ps1` читают живую
карту ассоциаций прямо из реестра. Никакой сторонней утилиты в этом нет.

### Where the truth lives / Где лежит правда

**English.** Per-user defaults live in two registry roots:

```text
HKCU\Software\Microsoft\Windows\CurrentVersion\Explorer\FileExts\<.ext>\UserChoice   -> ProgId
HKCU\Software\Microsoft\Windows\Shell\Associations\UrlAssociations\<proto>\UserChoice -> ProgId
```

`Get-AssociationDump` in `_Common.ps1` walks both, sorts the result, and emits
`identifier, ProgID` lines. Reading is unrestricted; only writing is guarded.

**— RU —** Пользовательские умолчания живут в двух ветках реестра (выше).
`Get-AssociationDump` в `_Common.ps1` обходит обе, сортирует и выдаёт строки
`идентификатор, ProgID`. Чтение ничем не ограничено — защищена только запись.

### Why there is no restore / Почему нет восстановления

**English.** Alongside `ProgId`, Windows stores a `Hash` bound to the user SID,
the extension, the ProgID and a system salt. The shell verifies it on every use:
a hand-written `ProgId` without a matching hash resets the association to the
default — that is the "your app was reset" message. Since 2024 a kernel driver
(`UCPD.sys`) additionally denies writes to these keys for common tools.

This project does not forge that hash and ships no helper that does. Snapshots
record state; putting defaults back is the job of the policy path — DISM
`AppAssociations.xml` plus HKLM `DefaultAssociationsConfiguration`.

**— RU —** Рядом с `ProgId` Windows хранит `Hash`, привязанный к SID пользователя,
расширению, ProgID и системной соли. Оболочка проверяет его при каждом открытии
файла: `ProgId`, записанный руками без верного хеша, приводит к сбросу ассоциации
на умолчание — это и есть сообщение «приложение было сброшено». С 2024 года
запись в эти ключи для типовых утилит дополнительно запрещает драйвер `UCPD.sys`.

Проект этот хеш не подделывает и не тащит утилиту, которая это делает. Снимок
фиксирует состояние; вернуть умолчания — работа policy-слоя: DISM
`AppAssociations.xml` и HKLM `DefaultAssociationsConfiguration`.

### Snapshot file format / Формат файла снимка

**English.** One `identifier, ProgID` pair per line; lines starting with `#` are
comments and are skipped by the readers. The format is the project's own and is
shared by the monolithic snapshot and the per-group files.

**— RU —** По одной паре `идентификатор, ProgID` в строке; строки с `#` —
комментарии, читатели их пропускают. Формат свой, общий для монолитного снимка
и файлов групп.

---

## 7. `Golden-Snapshot.ps1`  — "Microsoft Snapshot"

### English

The safety rope on top of every other brick. Captures, compares, and restores a
full per-machine snapshot of file/protocol associations from the registry.
Whatever Redmond reclaims after an update, restore puts the whole map back in
one glance. Snapshots are `identifier, ProgID` dumps saved under `snapshots/`
as `<Name>.<Machine>.txt`; the default name is **"Microsoft Snapshot"**.

| Action | Command | Effect |
|--------|---------|--------|
| Status (compare) | `.\Golden-Snapshot.ps1 -Status` | Shows `DRIFT` / `NEW` / `MATCH` vs the baseline |
| Enable (capture) | `.\Golden-Snapshot.ps1 -Enable` | Saves the current map to the snapshot file |
| (no restore) | - | Windows guards `UserChoice` with a per-user hash; use the policy path |

Parameters: `-Name <text>` (snapshot label, default "Microsoft Snapshot"),
`-Machine <id>` (filename tag, default `$env:COMPUTERNAME`). Commit the
`snapshots/` files to git to freeze each machine's baseline. `DRIFT` = an entry
changed from baseline; `NEW` = an extension present now but not in the baseline;
`MATCH` = nothing moved.

### — RU —

Страховочный трос поверх всех остальных бриков. Снимает, сравнивает и
восстанавливает полный per-machine снапшот файловых/протокольных ассоциаций
по реестру. Что бы Редмонд ни перехватил после апдейта — сравнение показывает
всю картину целиком. Снапшоты — это дампы `идентификатор, ProgID`
в папке `snapshots/` под именем `<Name>.<Machine>.txt`; имя по умолчанию —
**«Microsoft Snapshot»**.

| Действие | Команда | Эффект |
|----------|---------|--------|
| Статус (сравнить) | `.\Golden-Snapshot.ps1 -Status` | Показывает `DRIFT` / `NEW` / `MATCH` относительно эталона |
| Включить (снять) | `.\Golden-Snapshot.ps1 -Enable` | Сохраняет текущую карту в файл снапшота |
| (восстановления нет) | - | Windows защищает `UserChoice` хешем пользователя; возврат — через policy-слой |

Параметры: `-Name <текст>` (метка снапшота, по умолчанию «Microsoft Snapshot»),
`-Machine <id>` (тег в имени файла, по умолчанию `$env:COMPUTERNAME`). Коммить
файлы из `snapshots/` в git, чтобы заморозить эталон каждой машины. `DRIFT` =
запись изменилась относительно эталона; `NEW` = расширение есть сейчас, но не
было в эталоне; `MATCH` = ничего не сдвинулось.

---

## 8. `Defense.ps1`  — the wrapper / враппер

### English

One entry point over all bricks. Verbs map straight through to each brick.
Enable order is deliberate: block reinstall first, while publisher identities
are still discoverable, then the rest. Disable runs in reverse.

| Command | Effect |
|---------|--------|
| `.\Defense.ps1 -Status` | Runs every brick's `-Status` (incl. snapshot drift) |
| `.\Defense.ps1 -Enable` | Applies every guard (snapshot excluded — see below) |
| `.\Defense.ps1 -Disable` | Removes every guard, reverse order (snapshot excluded) |
| `.\Defense.ps1 -Enable -Only Edge` | Targets a single brick |

Valid `-Only` values: `Apps`, `Rearm`, `Edge`, `AppX`, `Defender`, `Snapshot`, `Groups`, `Drift`.

Deliberate-act safety: in a bulk `-Enable`/`-Disable`, `Golden-Snapshot.ps1`,
`Group-Snapshot.ps1` and `Microsoft-Apps.ps1` take part in **`-Status` only**.
Capturing a baseline, committing a group and removing an in-box app must be
explicit, so you never freeze a drifted state as the baseline and never lose an
app as a side effect of "apply everything". `-Only Groups` and `-Only Apps`
therefore accept `-Status` only; use the bricks directly for the rest.

### — RU —

Единая точка входа над всеми бриками. Глаголы пробрасываются прямо в каждый
брик. Порядок при включении продуман: сначала блокировка реинсталла, пока
издатели пакетов ещё определяются, затем остальное. Откат — в обратном порядке.

| Команда | Эффект |
|---------|--------|
| `.\Defense.ps1 -Status` | Запускает `-Status` всех бриков (вкл. дрифт снапшота) |
| `.\Defense.ps1 -Enable` | Включает все защиты (снапшот исключён — см. ниже) |
| `.\Defense.ps1 -Disable` | Снимает все защиты в обратном порядке (снапшот исключён) |
| `.\Defense.ps1 -Enable -Only Edge` | Точечно один брик |

Допустимые значения `-Only`: `Apps`, `Rearm`, `Edge`, `AppX`, `Defender`, `Snapshot`, `Groups`, `Drift`.

Безопасность осознанных действий: при массовом `-Enable`/`-Disable`
`Golden-Snapshot.ps1`, `Group-Snapshot.ps1` и `Microsoft-Apps.ps1` участвуют
**только в `-Status`**. Снять эталон, зафиксировать группу и удалить встроенное
приложение можно только явно — чтобы не заморозить дрифтнутое состояние как
эталон и не потерять приложение побочным эффектом «применить всё». Поэтому
`-Only Groups` и `-Only Apps` принимают только `-Status`; остальное — прямым
вызовом брика.

---

## 9. Requirements / Требования

### English
- Windows 11. `AppX-ReinstallBlock.ps1` needs **Pro/Enterprise**; all others run on Home too.
- Run **elevated** for `-Enable` / `-Disable`. `-Status` is read-only and safe unelevated.
- No external tool is required: the snapshot bricks read the registry directly.
- Every script loads `_Common.ps1` from its **own folder**, not the current directory — keep the folder intact.

### — RU —
- Windows 11. `AppX-ReinstallBlock.ps1` требует **Pro/Enterprise**; остальные работают и на Home.
- Запуск **от администратора** для `-Enable` / `-Disable`. `-Status` только читает и безопасен без прав.
- Сторонние утилиты не нужны: брики снимков читают реестр напрямую.
- Каждый скрипт грузит `_Common.ps1` из **своей папки**, а не из текущего каталога — не разбивай папку.

---

## 10. Portable PowerShell (work machine) / Портативный PowerShell (рабочая машина)

### English
On PC #3, invoke the portable host explicitly instead of relying on `pwsh` in PATH:

```cmd
E:\Audion\Tools\PowerShell\pwsh.exe -ExecutionPolicy Bypass -File .\Defense.ps1 -Status
```

### — RU —
На PC #3 вызывай портативный хост явно, не полагаясь на `pwsh` в PATH:

```cmd
E:\Audion\Tools\PowerShell\pwsh.exe -ExecutionPolicy Bypass -File .\Defense.ps1 -Status
```

---

## 11. Recommended workflow / Рекомендованный сценарий

### English
1. Set your associations in Windows Settings, by hand.
2. `Microsoft-Apps.ps1 -Remove -Target ...` then `Appx-Rearm.ps1 -Enable -Target ...` — remove the in-box apps and keep them removed.
3. `Defense.ps1 -Enable` — block reinstall, calm Edge down, exclude drives.
4. `Golden-Snapshot.ps1 -Enable` — capture the "Microsoft Snapshot" baseline, commit to git.
5. After each feature update: `Defense.ps1 -Status` → if drifted, fix the types in Windows Settings and recapture. There is no restore verb (§6a).

### — RU —
1. Выстави ассоциации вручную в параметрах Windows.
2. `Microsoft-Apps.ps1 -Remove -Target ...`, затем `Appx-Rearm.ps1 -Enable -Target ...` — снести встроенные приложения и удержать их снесёнными.
3. `Defense.ps1 -Enable` — заблокировать реинсталл, прижать Edge, исключить диски.
4. `Golden-Snapshot.ps1 -Enable` — снять эталон «Microsoft Snapshot», закоммитить в git.
5. После каждого feature-апдейта: `Defense.ps1 -Status` → при дрифте поправить типы в параметрах Windows и переснять эталон. Ключа восстановления нет (§6a).

---

## 12. What this set deliberately does NOT do / Что набор намеренно НЕ делает

### English
- It does **not** permanently disable Defender. Tamper Protection blocks that by design; bypasses break the security stack after updates.
- It does **not** set per-extension ProgIDs — Windows guards that choice with a per-user hash. This set keeps the environment from fighting back.
- It does **not** touch the system drive in Defender exclusions — `C:\` stays protected.

### — RU —
- **Не** отключает Defender навсегда. Tamper Protection блокирует это by design; обходы ломают security-стек после апдейтов.
- **Не** выставляет ProgID по расширениям — этот выбор Windows защищает хешем пользователя. Этот набор лишь не даёт окружению сопротивляться.
- **Не** трогает системный диск в исключениях Defender — `C:\` остаётся под защитой.

---

## 13. Troubleshooting / Диагностика

### English
| Symptom | Likely cause | Fix |
|---------|--------------|-----|
| "must run elevated" | Not an admin session | Re-run from an elevated terminal |
| `_Common.ps1 not found` | Folder split apart | Keep all scripts in one folder |
| AppLocker brick refuses | Windows Home | Use `Microsoft-Apps.ps1 -Remove` + `Appx-Rearm.ps1` instead |
| Snapshot shows DRIFT you did not cause | An app reclaimed a type after an update | Fix it in Windows Settings, then recapture |
| Edge still nags | Surfaces not refreshed | Sign out / reboot after `-Enable` |

### — RU —
| Симптом | Вероятная причина | Решение |
|---------|--------------------|---------|
| «must run elevated» | Сессия не админская | Перезапусти из терминала с правами администратора |
| `_Common.ps1 not found` | Папка разбита | Держи все скрипты в одной папке |
| Брик AppLocker отказывает | Windows Home | Вместо него `Microsoft-Apps.ps1 -Remove` + `Appx-Rearm.ps1` |
| Снимок показывает DRIFT, которого ты не делал | Приложение забрало тип после апдейта | Поправить в параметрах Windows и переснять эталон |
| Edge всё ещё клянчит | Поверхности не обновились | Выйти из системы / перезагрузиться после `-Enable` |

---

## 13a. Dry-run (`-DryRun`) / Сухой прогон

### English
The bricks that change state accept `-DryRun`: it walks the full action and
prints what *would* happen without changing anything (and without requiring
admin). Use it as a preview before committing.

```powershell
.\Microsoft-Apps.ps1 -Remove -Target group:media -DryRun   # apps that would be removed
.\Edge-Debloat.ps1 -Enable -Level Quiet -DryRun            # policy values that would be written
.\AppX-ReinstallBlock.ps1 -Enable -Target Photos -DryRun   # AppLocker rules that would be added
.\Golden-Snapshot.ps1 -Enable -DryRun                      # capture that would overwrite the baseline
.\Group-Snapshot.ps1 -Commit photo -DryRun                 # group that would be committed
```

### — RU —
Брики, меняющие состояние, принимают `-DryRun`: проходит весь путь действия и
печатает, что *было бы* сделано, ничего не меняя (и без прав администратора).
Используй как предпросмотр перед реальным запуском.

```powershell
.\Microsoft-Apps.ps1 -Remove -Target group:media -DryRun   # какие приложения были бы удалены
.\Edge-Debloat.ps1 -Enable -Level Quiet -DryRun            # какие значения политик были бы записаны
.\AppX-ReinstallBlock.ps1 -Enable -Target Photos -DryRun   # какие правила AppLocker были бы добавлены
.\Golden-Snapshot.ps1 -Enable -DryRun                      # какой снимок перезаписал бы эталон
.\Group-Snapshot.ps1 -Commit photo -DryRun                 # какая группа была бы зафиксирована
```

---

## 13b. Drift Watch (`Drift-Watch.ps1`) / Слежение за дрифтом

### English
Installs a scheduled task that runs **at each logon**, compares the live
association map against the "Microsoft Snapshot" baseline, and raises a Windows
**toast** if drift is found. Warning only — it never auto-restores.

| Action | Command | Effect |
|--------|---------|--------|
| Status | `.\Drift-Watch.ps1 -Status` | Shows task state, last run/result, last check line |
| Enable | `.\Drift-Watch.ps1 -Enable` | Installs/replaces the at-logon task |
| Disable | `.\Drift-Watch.ps1 -Disable` | Removes the task |
| RunCheck | `.\Drift-Watch.ps1 -RunCheck` | One check now (what the task calls) |

The task is registered under `\Audion\Audion-AssociationDriftWatch`, runs as the
logged-on user (needed for toast) at Limited level, and uses the portable
`pwsh.exe` if present. Each check appends a line to `logs\drift-watch.log`. On
drift it toasts and names the types that moved; putting them back is a manual
decision — through Windows Settings or the Policy tab, never a forged hash.

### — RU —
Ставит задачу планировщика, которая запускается **при каждом входе в систему**,
сравнивает текущую карту ассоциаций с эталоном «Microsoft Snapshot» и при
обнаружении дрифта показывает **toast**-уведомление Windows. Только
предупреждение — автовосстановления нет.

| Действие | Команда | Эффект |
|----------|---------|--------|
| Статус | `.\Drift-Watch.ps1 -Status` | Состояние задачи, последний запуск/результат, строка последней проверки |
| Включить | `.\Drift-Watch.ps1 -Enable` | Ставит/заменяет задачу при входе |
| Откат | `.\Drift-Watch.ps1 -Disable` | Удаляет задачу |
| RunCheck | `.\Drift-Watch.ps1 -RunCheck` | Одна проверка сейчас (её зовёт задача) |

Задача регистрируется как `\Audion\Audion-AssociationDriftWatch`, работает от
имени вошедшего пользователя (нужно для toast) на уровне Limited и использует
портативный `pwsh.exe`, если он есть. Каждая проверка дописывает строку в
`logs\drift-watch.log`. При дрифте показывает toast и указывает на
какие типы уехали; вернуть их — ручное решение: через параметры Windows или
вкладку ПОЛИТИКА, но никогда через подделку хеша.

---

## 14. Logging / Логирование

### English
Every `-Enable` / `-Disable` action is recorded via a PowerShell transcript.
`-Status` is **not** logged (read-only, noisy). Logs are written to `.\logs\`
next to the bricks, falling back to `E:\Audion\Logs\AssociationDefense` then
`S:\Audion\Logs\AssociationDefense` if the script folder is not writable.

File naming: `<timestamp>.<machine>.<brick>-<verb>.log`, e.g.
`2026-06-11_143022.AUDION-BASE.Edge-Enable.log`. The snapshot brick uses its
action name (`Capture`). Files older than **30 days** are deleted
automatically at the start of each logged run. If no writable location is
found, the action proceeds **unlogged** with a warning — logging never blocks
the operation.

### — RU —
Каждое действие `-Enable` / `-Disable` записывается через транскрипт
PowerShell. `-Status` **не** логируется (только чтение, шумно). Логи пишутся в
`.\logs\` рядом с бриками, с фолбэком на `E:\Audion\Logs\AssociationDefense`,
затем `S:\Audion\Logs\AssociationDefense`, если папка скрипта недоступна на
запись.

Имя файла: `<timestamp>.<machine>.<brick>-<verb>.log`, например
`2026-06-11_143022.AUDION-BASE.Edge-Enable.log`. Брик снапшота использует свои
своё имя действия (`Capture`). Файлы старше **30 дней** удаляются
автоматически в начале каждого логируемого запуска. Если доступной на запись
папки нет — действие выполняется **без лога** с предупреждением; логирование
никогда не блокирует операцию.

---

## 15. Files / Файлы

```
association_defense/
├── _Common.ps1               # shared helpers (not run directly)
├── Microsoft-Apps.ps1        # in-box apps: remove / restore / re-provision
├── Appx-Rearm.ps1            # keep a removal valid across feature updates
├── Edge-Debloat.ps1          # calm Edge down (WebView2 protected)
├── AppX-ReinstallBlock.ps1   # block reinstall (Pro/Enterprise)
├── Defender-Exclusions.ps1   # drive/process exclusions
├── Golden-Snapshot.ps1       # "Microsoft Snapshot" capture/compare
├── Group-Snapshot.ps1        # per-group capture/compare, compose into the snapshot
├── Drift-Watch.ps1           # at-logon drift toast (warn only, no auto-restore)
├── Defense.ps1               # wrapper over all bricks
├── snapshots/                # whole-map snapshot dumps (commit to git)
│   └── groups/               # per-group dumps
├── logs/                     # transcript logs of state-changing runs (rotated 30d)
└── README.md                 # this file
```
