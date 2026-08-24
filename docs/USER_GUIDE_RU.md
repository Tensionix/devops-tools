# Audion DevOps Tools - User Guide

Актуально для проекта `Audion DevOps Tools` на 2026-06-24.

Это пользовательский guide по всем основным возможностям проекта. Для внутренней архитектуры и правил разработки смотри `docs\AUDION_DEVOPS_TOOLS_RU.md`, `docs\MANIFEST_REFERENCE_RU.md` и `AGENTS.md`.

## Что Это И Чем Не Является

Audion DevOps Tools не является клоном Chris Titus WinUtil, generic Windows tuner или debloater. Он не пытается заменить массовые утилиты для быстрых пользовательских настроек Windows.

Проект закрывает другой слой: тонкие DevOps-операции на границе Windows, WSL, virtualization, hardware policy, storage, network, default-app policy и secrets. Это рабочая кабина истребителя: параметры, backup, явные риски, подтверждения, журнал и возможность действовать через один управляемый project-local контур.

## Быстрый Старт

Обычный запуск GUI:

```cmd
launcher_gui.cmd
```

При обычном запуске GUI запрашивает UAC и работает от администратора. Это удобно, потому что многие операции проекта требуют admin context: DISM, WSL features, hosts, сетевые адаптеры, default-app policy, драйверные policy, WinRE и дисковые процедуры.

Read-only/debug запуск без UAC:

```cmd
set AUDION_GUI_NO_ELEVATE=1
launcher_gui.cmd
```

Если нужен другой Python:

```cmd
set AUDION_GUI_PYTHON=C:\Path\To\python.exe
launcher_gui.cmd
```

GUI запускает локальный NiceGUI shell. По умолчанию используется:

```text
http://127.0.0.1:8092/
```

## Главный Принцип

Все операции должны идти средствами проекта:

- через GUI;
- через `launcher_*.cmd`;
- через `runtime\python.exe system_core\cli_operation.py <operation_id>`.

Это особенно важно для WSL и системных операций. Если тестируется проектный слой, не надо обходить его ручными командами, иначе мы проверяем не проект, а удачу в текущей консоли.

Для прямого CLI-запуска dangerous-операций нужен явный флаг:

```cmd
runtime\python.exe system_core\cli_operation.py operation_id --yes-i-understand
```

## Где Лежат Рабочие Данные

Основные папки:

```text
config\       manifest, terminal history, настройки GUI
system_core\  сервисный слой, GUI, PowerShell modules, WSL assets
tools\        project-local утилиты и wrapper kits
profiles\     управляемые профили, например Default Apps Guard XML
backup\       backup системных и пользовательских состояний
output\       отчеты и экспортированные артефакты
logs\         логи операций
report\       elevated logs и диагностические отчеты
workspace\    рабочие папки инструментов
```

Проект рассчитан на portable-работу. Внешние старые папки могут быть полезны как reference, но runtime-операции должны жить внутри текущего проекта.

`backup` считается ключевой папкой проекта наравне с `input`, `output`, `logs`, `report` и `workspace`: она есть в `ProjectPaths.backup`, создаётся preflight/init-слоем и открывается отдельной кнопкой `BACKUP` в панели GUI. Это не cache и не временный output, а место для rollback/safety snapshots: network snapshots, `.reg`, Driver Store exports, browser master/pre-import, certificates, SSH material, virtualization и hosts backups.

## Риски И Подтверждения

В manifest операции помечены как:

- `safe` - чтение, диагностика или запись только в управляемую проектную область;
- `dangerous` - меняет пользователя, систему, сеть, диски, policy или secrets.

Дополнительный `risk_level` уточняет характер риска:

- `project_write` - пишет в проект;
- `user_write` - меняет текущего пользователя;
- `system_change` - меняет Windows/system policy;
- `destructive` - может удалять данные или разделы;
- `secret_export` - экспортирует секреты, например SSH keys.

GUI требует отдельное подтверждение для dangerous-операций. Некоторые внешние wizard-консоли дополнительно требуют typed confirmations. Встроенные неинтерактивные операции должны иметь явные project-флаги, а не скрытые `Y/YES` prompts.

## Как Читать RU-Интерфейс

RU-интерфейс намеренно гибридный. Названия команд, режимов и параметров часто остаются English-heavy, потому что они совпадают с `operation_id`, журналом операции, PowerShell/Windows API и документацией Microsoft. Тултипы и `description_ru` раскрывают эти названия нормальным русским языком.

Типовая пара выглядит так:

- label/command: `Default Apps Guard`, `Profile XML`, `Enable / repair defaults protection`;
- tooltip/guide: раздел Windows «Приложения по умолчанию», эталон `AppAssociations.xml`, HKLM policy `DefaultAssociationsConfiguration`;
- log/CLI: `default_apps_apply_policy`, `profile_xml`, `program_data_dir`.

Так же читаются `Microsoft`, `Driver Update Blocker`, `DeviceInstall restrictions`, `WinRE layout`, `backup`, `dry run`: короткое имя оставляет техническую точность, а подсказка объясняет, что именно изменится в Windows.

## Легенда UI: Рамки, Цвета И Пары

GUI использует не декоративную раскраску, а приборную маркировку сценариев. Кнопки получают очень слабую цветовую заливку и более читаемую обводку; акцент должен помогать считыванию, но не светить в глаза.

- Рамка вокруг группы означает логическую пару, pipeline или жизненный цикл: `backup / restore`, `export / import`, `block / unblock`, `capture / apply`.
- Входы в разделы и окна остаются обычными синими Quasar-кнопками; цветовой акцент получают только кнопки конкретных действий.
- Зелёный акцент означает щадящий/read-only/status-сценарий либо намеренную отмену в паре `block / unblock`, `enable / disable`, `apply / remove`.
- Бирюзовый акцент означает обычное рабочее изменение: apply, export, import, enable/disable без destructive-смысла, когда это не специальная кнопка отмены в парном блоке.
- Янтарный акцент означает сильное вмешательство, destructive-сценарий или sensitive/secret export.

Цветовой акцент не заменяет `kind`, `risk_level`, подтверждение и журнал. Он помогает быстро понять характер соседних действий внутри одной рамки. Например, `Driver Store: backup / export / restore` показывает три связанных действия в одном блоке, а кнопки различают мягкий manifest, рабочий export и более сильный restore.

Видимое описание команды намеренно короткое: оно должно помочь принять решение за пару секунд. Полное объяснение, Windows-термины, риск и детали отката остаются в tooltip по кнопке или описанию. Диалоги подтверждения dangerous-операций показывают полный текст, чтобы перед запуском не терялись последствия.

Устойчивые пары терминов:

- `backup` - снимок/резервная копия состояния внутри project-local backup.
- `export` - вынести состояние или артефакты наружу в файл/папку.
- `import` - занести файл/папку обратно в систему или профиль.
- `restore` - применить сохранённое состояние обратно.
- `block / unblock` - поставить или снять ограничение/policy.
- `enable / disable` - включить или выключить компонент/режим.
- `capture / apply` - сохранить слой/снимок и применить его обратно.
- `cleanup / nuke` - очистка в выбранном scope; сначала ищи `audit` или `dry run`.

## Runtime And Shell

Этот раздел проверяет базовую готовность проекта и Windows shell окружения.

Основные операции:

- `Preflight snapshot` - снимок elevation, WSL, virtualization, PowerShell, network, Wi-Fi и disk risk flags.
- `PowerShell runtime status` - показывает, какой PowerShell используется.
- `Install portable PowerShell` - ставит project-local `system_core\powershell\pwsh.exe`.
- `Windows Long Paths` - проверка и включение `LongPathsEnabled`.
- `Git Long Paths` - включает `git config --global core.longpaths true`.

Порядок поиска PowerShell:

1. `system_core\powershell\pwsh.exe`
2. `pwsh.exe` из `PATH`
3. `powershell.exe`

Long Paths важны для DEV-папок с `node_modules`, virtualenv, SDK и глубокими workspace. Но лучше всё равно держать проекты в коротких путях вроде `S:\Code\Project`.

## Обслуживание И Очистка

Раздел `Обслуживание и очистка` собирает cleanup-операции софта и managed workspace. Он отделён от `Runtime and shell`, чтобы runtime означал окружение, а destructive-cleanup не смешивался с проверкой оболочки.

В Workbench `Сбросить` возвращает проектные пути `input/output` без удаления, а `Удалить` очищает текущие `Источник` и `Назначение` после подтверждения.

### Codex Nuke И Python Nuke

Это отдельные runtime-cleanup инструменты:

```text
tools\codex_nuke
tools\python_nuke
```

Codex Nuke:

- `Audit` - только анализ;
- `Dry run` - симуляция очистки;
- `Session reset` - soft-reset: убивает процессы, чистит `.codex\sessions`, AppX LocalCache/TempState, но сохраняет auth/install/registry;
- `NUKE, keep CLI state` - чистка с сохранением `~\.codex` для Codex CLI;
- `NUKE full` - полная очистка.

Python Nuke:

- `Audit`;
- `Dry run`;
- `NUKE full`;
- `NUKE, keep winget`.

GUI вызывает конкретный режим напрямую через service layer, а не интерактивное меню `Nuke.cmd`.

Python Nuke удаляет vanilla Python, Store Python/AppX, Python Launcher, pipx, uv, conda, pip caches/config, env vars, Start Menu shortcuts, PATH entries и uninstall registry entries. Он не должен трогать project venvs, ChatGPT app и собственную папку tool. После реального nuke нужен reboot перед новой установкой Python.

## Browser Bookmarks Master

Раздел `Browser Bookmarks Master` живёт в OS -> Браузеры и поддерживает два источника: HTML-export закладок как основной clean-import и нативную backup-папку Chromium-профиля как аварийное восстановление. Нативный режим работает с тремя штатными файлами:

- `Bookmarks`;
- `Favicons`;
- `Favicons-journal`.

В GUI действие выбирается сверху (`Status`, `Import`, `Export`, `Transfer`), а список браузеров меняет тип выбора под действие:

- `Status` - read-only проверка одного или нескольких выбранных браузеров, процессов, папок профиля, трёх файлов и последнего импортируемого backup из Workbench SOURCE.
- `Export master to Workbench TARGET` - браузеры выбираются чекбоксами; закрывает выбранные браузеры и копирует три файла в новые versioned backup-папки под Workbench TARGET.
- `Import master from Workbench SOURCE` - для системного режима браузеры выбираются чекбоксами, для portable указывается один точный профиль. HTML-режим заменяет `Bookmarks`, полностью пересобирает favicon-базу из встроенных `ICON=` и делает rollback по выбору; нативный режим копирует полный выбранный backup.
- `Transfer master between browsers` - источник выбирается radio-кнопкой, приёмники чекбоксами; источник скрыт из приёмников. Операция сначала выгружает источник в project-local backup, затем импортирует этот backup в выбранные приёмники.
- `Open local safety backups` - открывает папку локальных страховочных снимков.

Переключатели операций сделаны широкими кнопками с отчётливым активным состоянием. Цвет помогает навигации, но не заменяет `kind`, `risk_level`, подтверждение и журнал.

Отсутствующий профиль среди выбранных браузеров не останавливает весь запуск: он логируется как `SKIP`, GUI показывает жёлтый toast, а операция продолжается по остальным найденным профилям.

Переключатель `Системный / Portable` определяет расположение профиля. Portable-режиму нужна точная папка профиля с файлом `Bookmarks`, а не только папка браузерного executable.

`Создать rollback` включён по умолчанию для import и отдельной очистки Favicons. Его можно отключить, если текущая favicon-база уже повреждена и сохранять её бессмысленно. `Открыть backup` только открывает `backup\browser_bookmarks` и ничего не копирует.

Отдельная команда `Очистить Favicons` работает со всеми отмеченными системными браузерами или одним portable-профилем. Это полный reset favicon SQLite; браузеры после операций остаются закрытыми и программой автоматически не запускаются. Основной способ ремонта - HTML clean-import, который сразу восстанавливает иконки из встроенных `ICON=`.

Версионирование касается папок backup, а не файлов. Папка получает имя вида `YYYY-MM-DD_HH-MM-SS_<backup_label>_vNN`; `backup_version=auto` выбирает следующий свободный номер, а занятая ручная версия повышается вместо перезаписи. При мульти-экспорте к заданному `backup_label` добавляется ключ браузера. Внутри папки файлы всегда остаются совместимыми с браузером: `Bookmarks`, `Favicons`, `Favicons-journal`.

Workbench `TARGET` используется для export, Workbench `SOURCE` - для import/status. UNC-сетевые пути работают, если Windows-сеанс уже имеет доступ к share. Подробно: `docs\BROWSER_BOOKMARKS_MASTER_RU.md`.

Для UNC-сетевых путей в окне есть конструктор `\\SERVER\Share\Folder`: отдельно вводятся сервер/компьютер, имя `Share` и необязательная папка внутри share. Кнопки `SOURCE`/`TARGET` сохраняют результат как текущий Workbench route.

## Network Cleaner

Раздел для диагностики и ремонта сетевого состояния Windows.

### Диагностика И Backup

`Status snapshot` - read-only baseline. Собирает текущее состояние сети и пишет timestamp-снимок в project-local backup: `ipconfig`, routes, adapters, DNS, proxy, Wi-Fi status, registry/network hints и run log. Ничего не чинит и не сбрасывает.

`Backup network state` - полный снимок без Wi-Fi паролей. Сохраняет adapters, IP/DNS/routes, WinHTTP/WinINet proxy, firewall export, Winsock/network registry exports, `hosts`, Wi-Fi profiles без clear keys, manifest и logs.

`Backup with Wi-Fi keys` - тот же backup плюс Wi-Fi profiles с `key=clear`. Это sensitive export: XML может содержать Wi-Fi passwords открытым текстом. Для обычного переноса профилей часто достаточно экспорта без ключей.

`Open backup folder` - открывает папку снимков Network Cleaner. Там лежат restore manifests, exported files и logs.

### TimeMachine Restore

`Restore latest` и `Restore selected` восстанавливают состояние из снимка Network Cleaner. Перед откатом проект сначала делает новый снимок текущего состояния, чтобы не потерять даже “сломанное сейчас”.

Restore пытается вернуть практический набор сетевого состояния:

- импортирует сохраненные `.reg`;
- восстанавливает `hosts`;
- импортирует firewall `.wfw`;
- прогоняет сохраненный `netsh interface dump`;
- добавляет Wi-Fi profiles обратно;
- обновляет DNS registration/cache.

Это не замена offline-образу диска. Живой сетевой стек Windows, Winsock catalog и adapter database нельзя гарантированно вернуть побайтово из работающей системы, но это контролируемый откат внутри проекта.

### Repair Profiles

`Light repair` - самый мягкий режим. Делает DNS flush/register, ARP cache clear, NetBIOS refresh и targeted DHCP renew для подключенных DHCP interfaces. Не делает `route -f`, Winsock reset, TCP/IP reset, firewall reset и не удаляет Wi-Fi profiles.

`Standard repair` - нормальная эскалация. Делает Winsock reset, TCP/IP reset, WinHTTP proxy reset, DNS refresh и ARP clear. После него лучше reboot.

`Nuclear repair` - тяжелый режим, когда standard не помог. Делает standard repair плюс route flush и дополнительные глубокие шаги оригинального script flow. Внешний script всё ещё держит отдельные typed confirmations для самых разрушительных действий вроде `NETCFG-D`.

Рекомендуемый порядок:

1. `Status snapshot`.
2. `Light repair`.
3. Если не помогло - `Standard repair`.
4. Если стало хуже - `Restore selected`.
5. `Nuclear repair` только когда обычный repair уже не спас.

### Proxy

`Proxy status` - показывает user-level WinINet/System proxy и machine-level WinHTTP proxy.

`Disable user proxy` - отключает proxy текущего пользователя. Перед изменениями proxy tool сохраняет `.reg` backup в `tools\disable_windows_proxy\backup\proxy_YYYYMMDD_HHMMSS`. Команда выключает WinINet/System Proxy, убирает stale `ProxyServer`/`ProxyOverride`, по умолчанию удаляет `AutoConfigURL`, отключает `AutoDetect` и чистит WinINet connection cache values. Полезно после VPN/corporate/local proxy tools, которые оставили stale proxy в профиле.

`Reset WinHTTP proxy` - сбрасывает machine-level WinHTTP proxy, который используют службы и часть системных tools. Это не то же самое, что browser/user proxy.

Restore proxy state вручную: импортировать нужный `.reg` из backup-папки только если осознанно нужно вернуть старое proxy-состояние.

## Подключение И Адаптеры

Раздел `Подключение и адаптеры` собирает Wi-Fi profiles, SMB-вход к Windows file sharing, adapter actions и быстрые LAN/Wi-Fi modes. Это не repair-раздел Network Cleaner, а маршрутизация текущего подключения.

### Wi-Fi Profiles

`Wi-Fi status` - показывает WLAN interfaces и сохраненные profiles.

`Connect profile` - подключает выбранный сохраненный профиль, опционально через выбранный Wi-Fi adapter.

`Profile autoconnect` - переключает профиль между automatic/manual connection mode.

`Export profiles` - экспортирует Wi-Fi XML в выбранную папку. Clear-text keys добавляются только отдельным чекбоксом.

`Import XML file/folder` - импортирует один XML или все XML из папки. Scope `All users` требует admin rights; `Current user` применяет профиль только к текущему пользователю.

### SMB / Windows File Sharing

`SMB вход в сеть` открывает внешнюю консоль для `net use` входа к компьютеру с общими папками Windows.

Это helper для существующего Windows file sharing:

- компьютер указывается как имя без `\\`, например `NAS`, `SERVER01` или имя рабочей станции;
- пользователь вводится как короткое имя, `DOMAIN\User` или `user@example.com`;
- пароль вводится только во внешней консоли, не в GUI;
- DevOps Tools не сохраняет пароль и не получает его в service layer;
- кэш SMB хранит только пары `computer / user` в `config\smb_network_logins.json`;
- после успешного входа можно открыть Explorer на `\\COMPUTER`.

Операция использует `net use \\COMPUTER\IPC$ /user:... * /persistent:yes`, затем показывает `net view \\COMPUTER`. Она не создаёт share, не меняет ACL и не включает SMB-сервер.

Если Windows выдаёт `1219`, значит к этому компьютеру уже есть SMB-сеанс под другим пользователем. Закрой старый сеанс через `net use`, Windows Credential Manager или перезагрузку, затем повтори вход.

### Adapter И LAN/Wi-Fi Modes

Эти операции не ремонтируют сеть, а переключают текущий режим подключения.

Операции:

- `Adapter action` - enable, disable, restart выбранного адаптера;
- `LAN/Wi-Fi switch` - LAN only, Wi-Fi only, both on, cycle Wi-Fi;
- `Wi-Fi sticky pair` - сделать один профиль auto-connect, второй оставить manual.

GUI использует dynamic sources:

- network adapters;
- Wi-Fi adapters;
- сохраненные Wi-Fi profiles.
- SMB login cache без паролей.

Типовой сценарий: быстро переключиться между кабелем и Wi-Fi, не открывая Windows Settings.

Классический sticky-сценарий из tool pack: один Wi-Fi профиль ставится `connectionmode=auto`, второй `connectionmode=manual`, а Ethernet можно включать/выключать через `netsh interface set interface`. Отключение/включение проводного адаптера требует admin rights и может оборвать активное соединение.

## WSL Toolkit

WSL - один из главных модулей проекта. Он построен как единый управляемый слой, а не как набор старых wrapper-скриптов.

Базовые операции:

- `System WSL2 status`;
- `Enable WSL2 features`;
- `Update WSL2`;
- `Installable distros`;
- `Install distro`;
- `Install from image file`;
- `Installed distros`;
- `WSL status`;
- `Shutdown WSL`.

Установка distro поддерживает:

- online catalog `wsl --list --online`;
- pins для частых distro, включая Ubuntu 26.04;
- manual distro override;
- install name override;
- system default location;
- selected folder;
- `no_launch` по умолчанию.

Для быстрых дисков можно ставить distro в выбранную папку, например:

```text
S:\WSL\VHDX\Ubuntu-26.04
```

### Linux Configuration

После установки distro можно настроить Linux-слой:

- `Package update` - apt/dnf metadata update, optional upgrade;
- `Account bootstrap` - создать Linux user, sudo/wheel, default user;
- `Dev packages` - установить baseline dev packages;
- `Micro baseline`;
- `MC skin`;
- `Neovim base`.

Для apt в WSL проект умеет чинить типовые сетевые проблемы:

- Force IPv4;
- HTTPS mirror rewrite;
- retries;
- timeout;
- выбор mirror: archive, azure, kernel, yandex, custom, keep.

Это важно в сетях, где IPv6 физически не проходит или HTTP mirrors ведут себя нестабильно.

### WSL Distro Actions

Операции над установленными distro:

- `Terminate distro`;
- `Backup distro`;
- `Clone distro`;
- `Move distro`;
- `Delete distro`;
- `Import VHDX in place`;
- `Restore from backup`;
- `Register all VHDX`.

`Register all VHDX` по умолчанию работает в dry-run. Он сканирует VHDX root, пропускает уже зарегистрированные VHDX и показывает, что будет сделано.

Для backup VHD проект останавливает WSL перед export, чтобы избежать `ERROR_SHARING_VIOLATION`.

### Ubuntu Dev Installer Kit

Этот kit живет в WSL-разделе, потому что относится к Linux/Ubuntu сценариям:

```text
tools\ubuntu_dev_installer
```

В GUI доступны:

- open kit folder;
- README RU;
- Btrfs/Timeshift guide;
- installer script;
- NVMe prep script;
- package lists.

Это project-local reference kit для Linux setup, а не операция установки WSL distro.

## Виртуализация

Раздел `Виртуализация` управляет режимом Windows hypervisor на уровне host OS:

- `Virtualization status` - read-only статус `hypervisorlaunchtype`, Windows optional features, VBS/Core Isolation и интерпретация текущего режима;
- `Optimization status` - read-only диагностика того, что тормозит VM/WSL: Core Isolation/VBS, активный power plan, Defender exclusions, `.wslconfig` и размещение WSL VHDX;
- `Mode: Hyper-V / WSL2` - включает загрузку гипервизора и `VirtualMachinePlatform`;
- `Mode: Third-party fast` - ставит `hypervisorlaunchtype=Off` для быстрой работы VMware/VirtualBox/эмуляторов, но WSL2/Hyper-V/Sandbox перестают работать до обратного переключения;
- `Mode: Coexist (WHP)` - включает `Windows Hypervisor Platform` и `VirtualMachinePlatform`, чтобы современные сторонние VM работали рядом с Hyper-V/WSL2, обычно медленнее;
- `Enable/Disable Hyper-V`;
- `Enable/Disable Windows Sandbox`.

Каждая изменяющая операция делает BCD backup в:

```text
backup\virtualization
```

и требует reboot, прежде чем режим реально вступит в силу. VBS/Core Isolation модуль только диагностирует: если Core Isolation включён, VT-x может оставаться занятым даже при `hypervisorlaunchtype=Off`.

## Hosts And Bitrix

Раздел управляет `hosts` override для on-prem Bitrix.

Операции:

- `Detect current endpoint`;
- `Status / DNS / ports`;
- `Enable override`;
- `Disable override`;
- `Restore original hosts`.

Текущий default:

```text
portal.itpgrad.ru -> 192.168.0.130
port: 443
```

`Detect current endpoint` делает DNS-only lookup без учета stale `hosts`, принимает только local/private/link-local/loopback IP и сканирует candidate ports.

Важно: Windows `hosts` не хранит port. Поэтому проект пишет IP -> host, а ports сохраняет в managed comment metadata.

`Enable override` сохраняет pre-patch backup и пишет его имя в managed comment. `Disable override` делает bitwise depatch: копирует backup поверх системного `hosts`, а не пытается удалить строки вручную.

Подробнее: `docs\BITRIX_HOSTS_RU.md`.

## Приложения По Умолчанию

Раздел `ПРИЛОЖЕНИЯ ПО УМОЛЧАНИЮ` управляет тем, какими программами Windows
открывает файлы и ссылки, и защищает этот выбор от повторного перехвата
Windows и Edge. Семь вкладок делят работу по ролям:

| Вкладка | Отвечает за |
|---------|-------------|
| `ПОЛИТИКА` | Эталон ассоциаций и закрепление его за Windows (DISM XML + HKLM policy) |
| `MICROSOFT` | Встроенные приложения Microsoft: убрать, вернуть, удержать удалёнными |
| `EDGE` | Отучить Edge перетягивать ссылки и типы файлов; WebView2 остаётся защищённым |
| `ОТСЛЕЖИВАНИЕ` | Предупреждение о смене ассоциаций и исключения Defender для папок Audion |
| `СНИМОК` | Полная карта ассоциаций текущего пользователя: сравнить и сохранить |
| `ГРУППЫ` | Те же снимки, но по группам файлов — фото, аудио, видео, PDF, документы, архивы, браузер |
| `ОБЩИЙ ОТЧЁТ` | Все проверки раздела подряд, одним отчётом, без изменений в системе |

### Граница между снимком и политикой

Личный выбор пользователя (`HKCU ... UserChoice`) Windows защищает проверочной
суммой, привязанной к пользователю и системе. Проект её не подделывает и не
подключает сторонних утилит, которые это делают: снимок только читает `ProgId`
из реестра.

Отсюда разделение ролей. `СНИМОК` и `ГРУППЫ` отвечают на вопрос «что стоит
сейчас и что поменялось», `ОТСЛЕЖИВАНИЕ` предупреждает о смене, а вернуть
программы на место умеет только `ПОЛИТИКА` — через DISM XML и HKLM
`DefaultAssociationsConfiguration`.

### ПОЛИТИКА

Главный слой построен на официальном Microsoft admin/deployment path: DISM
default app associations XML, HKLM policy `DefaultAssociationsConfiguration`,
активный XML в ProgramData и применение при входе пользователя.

Действия (`policy_action`): `Проверить — чем сейчас открываются файлы`,
`Сохранить снимок текущего состояния`, `Экспортировать текущие ассоциации в эталон`,
`Взять эталон из файла`, `Закрепить сохранённые ассоциации`, `Снять закрепление`,
`Убрать старые резервные копии`, плюс три действия «открыть папку».

Ритуал после чистой установки:

1. Поставить программы.
2. Руками выставить defaults в Windows.
3. `Проверить — чем сейчас открываются файлы`.
4. Заполнить `Backup label`, например `golden-before`.
5. `Экспортировать текущие ассоциации в эталон`.
6. Оставить `Remove Suggested=true`.
7. `Закрепить сохранённые ассоциации`.
8. Sign out/sign in или перезагрузка.
9. Снова `Проверить — чем сейчас открываются файлы`.

Восстановление эталона из резервной копии: `Взять эталон из файла` -> выбрать
`Backup XML` из `backup\default_apps` -> `Закрепить сохранённые ассоциации` ->
sign out/sign in.

`Снять закрепление` удаляет значение `DefaultAssociationsConfiguration` и
делает backup policy XML/value. Текущие ассоциации при этом не меняются: снимается
только приказ Windows применять XML при входе.

Windows Home/Core: Microsoft не документирует эту policy как гарантированный
механизм для Home/Core. GUI показывает edition и по умолчанию блокирует apply
на unsupported edition без expert override.

Подробнее: `docs\DEFAULT_APPS_GUARD_RU.md`.

### MICROSOFT

Каталог из 31 встроенного приложения, разложенный по группам: медиа и фото,
игры, связь, новости и промо, заметки и утилиты. Удаление установленного пакета
освобождает ассоциации, удаление provisioned-копии оставляет чистыми новые
профили пользователей.

Действия (`apps_action`): `Проверить — что стоит в системе`, `Удалить отмеченные
приложения`, `Удалить и держать удалёнными`, `Вернуть приложения`, `Починить для
новых пользователей`, `Перестать держать удалёнными`, `Проверить удержание
сейчас`, `Открыть папку удержания`.

`Удалить и держать удалёнными` — это удаление плюс задача планировщика, которая
повторяет его после feature-апдейтов; на Pro/Enterprise дополнительно ставятся
запрещающие правила AppLocker. Начинать всегда со статуса и `dry run`.

### EDGE

Edge не удаляется никогда. Вкладка снимает у него привычку клянчить роль
браузера по умолчанию, работать в фоне и забирать типы файлов — через
документированные политики HKLM. WebView2 при этом явно защищён: многие
приложения рисуют на нём интерфейс.

Уровни: `Спокойно` — без навязывания и фона; `Тихо` — плюс боковые панели,
Shopping, Collections и лишние каналы Edge. Отдельное действие `Починить
WebView2` ставит официальный Evergreen Runtime.

### ОТСЛЕЖИВАНИЕ

Задача планировщика при входе сравнивает текущую карту ассоциаций с эталоном и
показывает toast, если что-то уехало. Только предупреждение — автоматического
восстановления нет. Здесь же живут исключения Microsoft Defender для папок
Audion; сам Defender не отключается.

### СНИМОК и ГРУППЫ

`СНИМОК` сравнивает и сохраняет полную карту ассоциаций текущего пользователя,
читая её прямо из реестра. `ГРУППЫ` делают то же по семействам файлов: `фото`,
`аудио`, `видео`, `PDF и книги`, `документы`, `архивы`, `браузер` или свой набор
расширений. Так состояние удобно фиксировать постепенно, по мере установки
программ. Состав групп совпадает с классификацией файлов в `Audion Disk Tools`.
`Собрать общий снимок из групп` сводит зафиксированные группы в общий файл.

Важно по PowerShell: AppX/AppLocker-команды не являются portable-частью
проекта. Они намеренно запускаются через системный Windows PowerShell 5.1
(`C:\Windows\System32\WindowsPowerShell1.0\powershell.exe`). Portable
PowerShell 7 полезен для других задач, но для этих Windows-модулей может
вернуть `Deserialized.*` объекты вместо живых `AppxPackage`, из-за чего
AppLocker не строит publisher rule.

Для ручного запуска без GUI есть два меню: `cli\launcher_association_defense.cmd`
(все семь вкладок) и `cli\launcher_default_apps.cmd` (только вкладка
`ПОЛИТИКА`, с вопросами про backup label и retention).

```cmd
cli\launcher_association_defense.cmd
cli\launcher_default_apps.cmd
```

Подробнее: `docs\ASSOCIATION_DEFENSE_RU.md`.

## Hardware

Hardware-раздел объединяет driver guard, NVIDIA controls и disk procedures.

### Driver/Firmware Audit

Read-only диагностический отчет по:

- problem devices;
- BIOS / Embedded Controller;
- BIOS registry summary;
- firmware resources;
- firmware resource details;
- key signed drivers.

Key signed drivers фильтруются по практическим платформенным компонентам: Realtek, Intel SST, ME/CSME, Thunderbolt/USB4, Serial IO, Dynamic Tuning, GNA, Lenovo/ThinkPad power/hotkey, fingerprint, camera/IR/MIPI, HID/ELAN, monitor INF. Отчет пишет TXT в `logs`, опционально JSON/CSV, и не требует admin rights для базового сценария.

Модуль строго read-only: он не flashes firmware, не ставит и не удаляет drivers, не меняет registry/settings и ничего не скачивает. Есть кнопки открыть addon folder и README.

### Driver Update Blocker

Операции Windows Update driver policy:

- `Check driver protection`;
- `Block Windows Update drivers`;
- `Unblock Windows Update drivers`;
- `Open policy backups`.

Block включает:

- `ExcludeWUDriversInQualityUpdate=1`;
- отключение driver wizard search through Windows Update;
- policy для device metadata downloads.

Типовой порядок:

1. `Check driver protection`.
2. `Block Windows Update drivers`.
3. Reboot.
4. Снова проверить status.

### NVIDIA Driver Install Restrictions

Операции:

- `Block NVIDIA driver installs`;
- `Unblock NVIDIA driver installs`.

Это Device Installation Restrictions для текущих NVIDIA PCI IDs. Обычно включается после ручной установки нужного NVIDIA driver. `Retroactive block` оставляй выключенным, если нет четкой причины.

Корневой wrapper для быстрого применения без GUI: `cli\Lock-NVIDIA-Driver-Installs.cmd --no-pause`. По умолчанию он блокирует present NVIDIA PCI Hardware IDs без retroactive removal; expert-флаги: `--include-compatible` и `--retroactive`.

### Driver Store Backups

Операции:

- `Save Driver Store manifest`;
- `Export installed drivers`;
- `Restore exported drivers`;
- `Open driver backups`;
- `Open Driver Update Blocker folder`.

Restore запускает `pnputil /add-driver ... /subdirs /install`. Лучше восстанавливать backup с той же машины или очень близкого hardware profile.

В аварийном HWID rank repair target INF должен совпасть не только по версии, но и по HWID. Если совпадения по HWID нет, repair останавливается; expert fallback только по версии включается отдельным advanced checkbox после ручной проверки INF.

### NVIDIA HDMI/DP Audio

Операции:

- `NVIDIA audio status`;
- `Export NVIDIA audio IDs`;
- `Disable NVIDIA HDMI/DP audio`;
- `Enable NVIDIA HDMI/DP audio`;
- `Policy-block NVIDIA HDMI/DP audio`;
- `Unblock policy`;
- open output/backup/tool folders.

Модуль работает только с NVIDIA HDAUDIO codec IDs вида:

```text
HDAUDIO\FUNC_01&VEN_10DE...
```

Он не блокирует GPU PCI IDs и не трогает обычные аудиоинтерфейсы.

Корневой wrapper для быстрого policy-блока без GUI: `cli\Lock-NVIDIA-HDMI-DP-Audio.cmd --no-pause`. Он блокирует NVIDIA HDAUDIO IDs и отключает уже установленные matching HDMI/DP audio devices.

Подробнее: `docs\HARDWARE_DRIVER_GUARD_RU.md`.

## Storage / Disk Procedures

Этот блок находится внутри Hardware.

### Inventory

`Disk and volume inventory` - сводка без изменений по `Get-Disk` и `Get-Volume`: номера дисков, размеры, состояние, буквы томов и файловая система. Команда ничего не размечает и не форматирует.

`Selected disk details` - подробности выбранного диска без изменений: свойства диска и layout таблицы разделов. Нужна перед любыми ручными действиями с дисками, чтобы не перепутать disk number.

### SSD/NVMe Reset Wizard

`Launch SSD/NVMe wizard` открывает оригинальный SSD/NVMe Reset Wizard v4 во внешней консоли. Это отдельный destructive interactive wizard для used SSD/NVMe reset/reprovision flows. GUI только запускает его; разрушительные действия внутри всё равно требуют typed confirmations самого wizard.

`Open SSD/NVMe folder` открывает папку `tools\ssd_nvme_reset_wizard` с README, logs и исходными scripts. Это безопасная операция просмотра.

Wizard предназначен для non-system disks. Он показывает disks/partitions, блокирует текущий system disk по умолчанию, умеет удалить выбранный partition через `delete partition override`, сделать быстрый `DiskPart clean`, медленный `DiskPart clean all`, пересобрать диск как GPT + one NTFS volume и записать log.

Важная граница: `clean` удаляет partition table, `clean all` пишет нули по устройству, но это не равно vendor Secure Erase, NVMe Sanitize, Format/Sanitize или OPAL/PSID revert. Для максимально близкого к factory reset SSD/NVMe лучше использовать vendor utility или controller-level tools.

### WinRE Extend

`WinRE layout status` - проверка без изменений: `reagentc /info` и layout системного диска. Команда показывает, где находится активный WinRE, рядом ли он с `C:`, и какой layout разделов видит Windows.

`Run WinRE extend wizard` запускает project-local script `tools\winre_extend\Remove-WinRE-And-Extend-System.ps1` с project confirmation. Внутренний `YES`-prompt уже закрывается параметром `-YesIUnderstand`, поэтому GUI-confirmation здесь особенно важен.

WinRE extend wizard делает:

1. Отключает WinRE.
2. Удаляет раздел восстановления WinRE справа от C:.
3. Расширяет C: на освободившееся место.

Скрипт блокирует автоматическое выполнение, если WinRE не на том же диске, не справа от `C:` или между `C:` и WinRE есть другие разделы. Но если layout подходит, операция реально удаляет раздел восстановления.

Это операция для понимающих людей и фактически билет в один конец. Нормальная стратегия восстановления после такого решения - полный offline image системы, а не надежда на Windows Recovery partition, которую мы сами удалили. После операции WinRE остаётся disabled, пока его отдельно не пересоздать/перенастроить.

## Utilities

### AI CLI Backup

`Backup (export)` создаёт в `output\ai_backup` новый проверяемый bundle Claude Code и Codex. Инструмент учитывает `CLAUDE_CONFIG_DIR`, `CODEX_HOME`, `CODEX_SQLITE_HOME` и `sqlite_home` из `config.toml`; экспорт собирается во временной папке, получает `manifest.json` с размерами и SHA-256, проверяется и только затем заменяет предыдущий bundle. Повторный экспорт поэтому не сохраняет удалённые старые файлы.

Essential сохраняет память, настройки, skills, plugins, rules и automations. Full добавляет историю сессий и кэш. Активные SQLite-базы Codex сохраняются через SQLite Backup API, а `installation_id` как идентификатор конкретной машины не переносится. Авторизация отделена от состава: опция `Include authentication secrets` добавляет Claude `.credentials.json` и Codex `auth.json`, если используется файловое хранилище. По умолчанию она выключена; bundle с авторизацией храните как пароль.

`Restore (import)` читает bundle, содержимое которого положено прямо в `input`, и до записи проверяет manifest, все SHA-256 и отсутствие незаявленных файлов. Dry run включён по умолчанию и показывает `ADD / REPLACE / SAME`. Essential-импорт не возвращает историю даже из Full-bundle; Full и авторизация включаются независимо. Совпадающие файлы заменяются, остальные локальные файлы не удаляются. Claude и Codex перед реальным импортом нужно закрыть.

При переносе между компьютерами конфиги с абсолютными путями выводятся отдельным предупреждением. Реальный импорт в другой профиль останавливается, пока пользователь после Dry run явно не разрешит `Allow saved absolute paths from another PC`. Старые папки прежнего `AI-Backup.ps1` не имеют manifest и принимаются только с `Allow legacy bundle without manifest`; это совместимость со старым бэкапом инструмента, а не иной формат памяти Claude/Codex.

### OpenSSH KeyKit

OpenSSH KeyKit - project-local export/import helper для SSH material. Это sensitive area: exports могут содержать private keys, `known_hosts`, client config, `authorized_keys`, server host keys и `sshd_config`.

Default backup root:

```text
backup\ssh_keykit
```

Структура snapshot:

```text
backup\ssh_keykit\<Machine>\users\<User>\<Timestamp>\client
backup\ssh_keykit\<Machine>\_server\<Timestamp>
```

`Export client SSH keys` копирует из `%USERPROFILE%\.ssh` файлы `id_*`, `*.pub`, `config`, `known_hosts*`, `authorized_keys` и папку `config.d`, если она есть. Это sensitive export, потому что `id_*` без `.pub` обычно private keys.

`Export client + server SSH keys` делает client export плюс, при admin context, копирует `ProgramData\ssh\ssh_host_*` и `sshd_config`. Если GUI не elevated, server host keys будут пропущены.

`Import client SSH keys` выбирает newest или указанный snapshot, делает backup текущей `%USERPROFILE%\.ssh` в папку вида:

```text
%USERPROFILE%\.ssh.bak.YYYYMMDD_HHMMSS
```

затем копирует client snapshot в `.ssh` и чинит ACL на private keys через `icacls`.

`Import client + server SSH keys` дополнительно импортирует server host keys в `ProgramData\ssh`, чинит ACL, останавливает/запускает `sshd` и ставит service startup в Automatic. Это system-change операция; применять только когда понятно, зачем переносить server identity.

`Open SSH KeyKit folder` открывает `tools\ssh_keykit` со scripts/wrappers.

Практическое правило: client export годится для переноса доступа пользователя; server host keys переносить стоит только если нужно сохранить identity SSH-сервера, иначе клиенты будут видеть другой host key и правильно предупреждать.

### Certificate KeyKit

Certificate KeyKit - project-local helper для Windows certificate stores. Он нужен для честного ответа на вопрос: какие сертификаты можно перенести после переустановки, а какие ключи привязаны к TPM/non-exportable provider и не переживут миграцию как PFX.

Операции:

- `Certificate status` - список выбранного store: subject, thumbprint, срок, private key и exportability;
- `Export personal keys to PFX` - exportable private-key certificates в password-protected `.pfx`;
- `Export store to SST (public)` - публичные Root/CA/intermediate certificates в `.sst` без private keys;
- `Import PFX`;
- `Import certificate / CA`;
- `Open certificate backup folder`.

Default backup root:

```text
backup\certificates
```

`.pfx` содержит private keys и является секретом уровня SSH private keys. Пароль PFX задаётся в Advanced на один запуск; в лог он не пишется. TPM/non-exportable ключи нельзя экспортировать by design: операция помечает их как SKIP.

### ripgrep

`ripgrep version` показывает версию project-local:

```text
ripgrep\rg.exe
```

### Documentation PDF

`Documentation PDF` рендерит Markdown-гайды и инструкции проекта в:

```text
docs\PDF
```

Dry-run автономен и не требует установленного render engine. Реальная генерация использует внешний `dev_markdown_pdf_engine.py`: путь задаётся через `--engine` или `AUDION_MARKDOWN_PDF_ENGINE`; также поддерживается автоматический поиск рядом с семейством проектов Audion.

Операции:

- `Preview PDF export plan` - dry-run, показывает источники и целевые PDF;
- `Generate docs PDFs` - создаёт PDF в темах `dark` и `light-sand` по умолчанию;
- `Open docs PDF folder` - открывает `docs\PDF`.

Рендерятся root guides, `docs\*.md`, `GitHub\*.md` и optional agent instructions (`AGENTS.md`, `CLAUDE.md`). Markdown остаётся source of truth; PDF рядом с исходными `.md` не храним. После генерации PDF отдельная визуальная проверка результата не требуется.

### Open Tool Folder

Открывает project-local utility folders из разрешенного списка.

## Maintenance

В GUI есть две зоны обслуживания:

- `Удалить` - действие очистки текущих `Источник`/`Назначение` в Workbench;
- `Clear Workbench workspace` - в дереве `Обслуживание и очистка`.

Они чистят управляемые рабочие папки, а не произвольные пользовательские пути.

Отдельная source-cleanup процедура:

```cmd
cleanup_project.cmd
```

Dry-run:

```cmd
cleanup_project.cmd /DRYRUN /Y
```

Обычный cleanup очищает generated backup-снимки вместе с остальными управляемыми рабочими зонами, сохраняя структуру папок и `.gitkeep`. Для очистки только project-local backup без остальных зон используется отдельный режим:

```cmd
cleanup_project.cmd /BACKUP
```

Он удаляет только содержимое `backup`, затем восстанавливает managed folder structure через `init_folders.cmd`. Перед реальным backup-only удалением всегда задаётся отдельный вопрос `Y/N/Q`; для проверки плана используйте `cleanup_project.cmd /BACKUP /DRYRUN`.

## Терминал GUI

Правая панель - основной журнал операций:

- статус;
- progress;
- stdout/stderr;
- PowerShell/CMD output;
- итог операции.

Нижняя command bar поддерживает:

- PowerShell или CMD;
- историю последних команд;
- pinned commands;
- рабочую папку через picker;
- файл через picker.

История хранится здесь:

```text
config\terminal_commands.json
```

<!-- BEGIN GENERATED PARAMETER REFERENCE -->
## Полный Справочник Команд И Параметров

Справочник генерируется из `config\tool_manifest.yaml`. Он включает весь текст GUI-подсказок, risk-классификацию, наследуемые поля, defaults и варианты выбора. Практические сценарии и объяснение последствий находятся в ручных разделах выше.

### Среда выполнения и оболочка > Предварительный снимок

- Operation id: `preflight_status`
- Описание: Один снимок в терминале: права администратора, WSL, виртуализация, PowerShell, сеть, Wi-Fi и риски дисков.
- Риск: kind=`safe`, risk_level=`readonly`
- Параметры: нет.

### Среда выполнения и оболочка > Статус PowerShell

- Operation id: `runtime_status`
- Описание: Показать портативный/системный PowerShell и его версию.
- Риск: kind=`safe`, risk_level=`readonly`
- Параметры: нет.

### Среда выполнения и оболочка > Проверить Windows Long Paths

- Operation id: `windows_long_paths_status`
- Описание: Показать HKLM LongPathsEnabled и значения Git core.longpaths. Настройки не меняет.
- Риск: kind=`safe`, risk_level=`readonly`
- Параметры: нет.

### Среда выполнения и оболочка > Включить Windows Long Paths

- Operation id: `windows_long_paths_enable`
- Описание: Установить HKLM LongPathsEnabled=1. Приложениям всё равно нужна поддержка longPathAware.
- Риск: kind=`dangerous`, risk_level=`system_change`
- Параметры: нет.

### Среда выполнения и оболочка > Включить Git Long Paths

- Operation id: `git_long_paths_enable`
- Описание: Установить git config --global core.longpaths true для текущего пользователя.
- Риск: kind=`dangerous`, risk_level=`user_write`
- Параметры: нет.

### Среда выполнения и оболочка > Установить портативный PowerShell

- Operation id: `install_portable_powershell`
- Описание: Скачать и установить pwsh.exe в system_core/powershell.
- Риск: kind=`safe`, risk_level=`readonly`
- Параметры: нет.

### Browser Bookmarks Master > Статус

- Operation id: `browser_bookmarks_status`
- Описание: Проверка без изменений: файлы выбранного профиля, состояние процесса и последний импортируемый backup из Workbench SOURCE. В GUI status можно запускать для одного или нескольких отмеченных браузеров.
- Риск: kind=`safe`, risk_level=`readonly`
- Параметры:
  - `browser_profile` — **Браузер** (type=`select`, default=`chrome`).
  - `backup_label` — **Имя backup** (type=`text`, default=`bookmarks_master`).
  - `backup_version` — **Версия backup** (type=`text`, default=`auto`).
  - `close_browser_process` — **Закрыть браузер перед операцией** (type=`checkbox`, default=true).
  - `browser_profile_path` — **Папка профиля portable-браузера** (type=`folder`).
  - `backup_source_path` — **Source backup папка Workbench** (type=`folder`).
  - `backup_target_path` — **Target backup папка Workbench** (type=`folder`).

### Browser Bookmarks Master > Очистить локальный Favicons cache

- Operation id: `browser_bookmarks_clear_favicons`
- Описание: Создаёт rollback backup, закрывает отмеченные браузеры и удаляет Favicons с sidecar-файлами. Chrome создаёт пустую базу, но возвращает иконки лишь по мере посещения страниц.
- Риск: kind=`dangerous`, risk_level=`user_write`
- Параметры:
  - `browser_profile` — **Браузер** (type=`select`, default=`chrome`).
  - `backup_label` — **Имя backup** (type=`text`, default=`bookmarks_master`).
  - `backup_version` — **Версия backup** (type=`text`, default=`auto`).
  - `close_browser_process` — **Закрыть браузер перед операцией** (type=`checkbox`, default=true).
  - `browser_profile_path` — **Папка профиля portable-браузера** (type=`folder`).
  - `backup_source_path` — **Source backup папка Workbench** (type=`folder`).
  - `backup_target_path` — **Target backup папка Workbench** (type=`folder`).

### Browser Bookmarks Master > Экспорт эталона в Workbench TARGET

- Operation id: `browser_bookmarks_export_master`
- Описание: Закрывает выбранные браузеры и копирует Bookmarks, Favicons и доступные служебные sidecar-файлы Chromium в версионированные папки backup внутри Workbench TARGET.
- Риск: kind=`dangerous`, risk_level=`secret_export`
- Параметры:
  - `browser_profile` — **Браузер** (type=`select`, default=`chrome`).
  - `backup_label` — **Имя backup** (type=`text`, default=`bookmarks_master`).
  - `backup_version` — **Версия backup** (type=`text`, default=`auto`).
  - `close_browser_process` — **Закрыть браузер перед операцией** (type=`checkbox`, default=true).
  - `browser_profile_path` — **Папка профиля portable-браузера** (type=`folder`).
  - `backup_source_path` — **Source backup папка Workbench** (type=`folder`).
  - `backup_target_path` — **Target backup папка Workbench** (type=`folder`).

### Browser Bookmarks Master > Импорт эталона из Workbench SOURCE

- Operation id: `browser_bookmarks_import_master`
- Описание: Импортирует выбранный нативный backup или HTML во все отмеченные системные браузеры; portable-режим работает с одним точным профилем. Для каждого создаётся rollback.
- Риск: kind=`dangerous`, risk_level=`destructive`
- Параметры:
  - `browser_profile` — **Браузер** (type=`select`, default=`chrome`).
  - `backup_label` — **Имя backup** (type=`text`, default=`bookmarks_master`).
  - `backup_version` — **Версия backup** (type=`text`, default=`auto`).
  - `close_browser_process` — **Закрыть браузер перед операцией** (type=`checkbox`, default=true).
  - `browser_profile_path` — **Папка профиля portable-браузера** (type=`folder`).
  - `backup_source_path` — **Source backup папка Workbench** (type=`folder`).
  - `backup_target_path` — **Target backup папка Workbench** (type=`folder`).

### Browser Bookmarks Master > Перенести эталон между браузерами

- Operation id: `browser_bookmarks_transfer_master`
- Описание: Двухэтапный перенос: выгружает выбранный браузер-источник в project-local backup, затем импортирует этот backup в выбранные браузеры-приёмники с pre-import backup и очисткой Favicons.
- Риск: kind=`dangerous`, risk_level=`destructive`
- Параметры:
  - `browser_profile` — **Браузер** (type=`select`, default=`chrome`).
  - `backup_label` — **Имя backup** (type=`text`, default=`bookmarks_master`).
  - `backup_version` — **Версия backup** (type=`text`, default=`auto`).
  - `close_browser_process` — **Закрыть браузер перед операцией** (type=`checkbox`, default=true).
  - `browser_profile_path` — **Папка профиля portable-браузера** (type=`folder`).
  - `backup_source_path` — **Source backup папка Workbench** (type=`folder`).
  - `backup_target_path` — **Target backup папка Workbench** (type=`folder`).

### Browser Bookmarks Master > Открыть локальные safety backups

- Operation id: `browser_bookmarks_open_local_backup`
- Описание: Открыть project-local Browser Bookmarks backup с pre-import snapshots.
- Риск: kind=`safe`, risk_level=`readonly`
- Параметры:
  - `browser_profile` — **Браузер** (type=`select`, default=`chrome`).
  - `backup_label` — **Имя backup** (type=`text`, default=`bookmarks_master`).
  - `backup_version` — **Версия backup** (type=`text`, default=`auto`).
  - `close_browser_process` — **Закрыть браузер перед операцией** (type=`checkbox`, default=true).
  - `browser_profile_path` — **Папка профиля portable-браузера** (type=`folder`).
  - `backup_source_path` — **Source backup папка Workbench** (type=`folder`).
  - `backup_target_path` — **Target backup папка Workbench** (type=`folder`).

### Очистка сети > Снимок статуса

- Operation id: `network_status`
- Описание: Снимок состояния сети без изменений: собирает ipconfig, таблицу маршрутов, сетевые адаптеры, DNS, параметры прокси и Wi-Fi status, затем пишет timestamp backup в backup проекта.
- Риск: kind=`safe`, risk_level=`readonly`
- Параметры: нет.

### Очистка сети > Полный backup сети

- Operation id: `network_backup`
- Описание: Полный снимок Network Cleaner: сетевые адаптеры, IP/DNS, маршруты, прокси, Брандмауэр Защитника Windows, реестр и Wi-Fi XML без открытых ключей.
- Риск: kind=`safe`, risk_level=`readonly`
- Параметры: нет.

### Очистка сети > Полный backup + Wi-Fi ключи

- Operation id: `network_backup_wifi_keys`
- Описание: Тот же полный снимок Network Cleaner плюс Wi-Fi XML с ключами открытым текстом. Для точечного переноса профилей используйте Wi-Fi профили.
- Риск: kind=`dangerous`, risk_level=`secret_export`
- Параметры: нет.

### Очистка сети > Восстановить backup сети > Восстановить последний backup

- Operation id: `network_restore_latest`
- Описание: Восстановить самый свежий снимок Network Cleaner. Сначала сохраняет текущее состояние, затем импортирует сохранённые данные реестра, сети, Брандмауэра Защитника Windows, hosts и Wi-Fi, где они доступны.
- Риск: kind=`dangerous`, risk_level=`system_change`
- Параметры: нет.

### Очистка сети > Восстановить backup сети > Восстановить выбранный backup

- Operation id: `network_restore_selected`
- Описание: Восстановить выбранный снимок Network Cleaner из backup-папки. Используй, когда последний backup не тот, к которому нужно вернуться.
- Риск: kind=`dangerous`, risk_level=`system_change`
- Параметры:
  - `network_restore_snapshot` — **Backup сети** (type=`select`).

### Очистка сети > Профили ремонта > Легкий ремонт

- Operation id: `network_light_repair`
- Описание: Самый мягкий ремонт: flush/register DNS, очистка ARP, обновление NetBIOS и DHCP renew только для подключённых DHCP-интерфейсов.
- Риск: kind=`dangerous`, risk_level=`system_change`
- Параметры: нет.

### Очистка сети > Профили ремонта > Стандартный ремонт

- Operation id: `network_standard_repair`
- Описание: Нормальная эскалация: сбрасывает Winsock, TCP/IP и WinHTTP proxy, затем обновляет DNS и ARP. После рекомендуется перезагрузка.
- Риск: kind=`dangerous`, risk_level=`system_change`
- Параметры: нет.

### Очистка сети > Профили ремонта > Жёсткий ремонт

- Operation id: `network_nuclear_repair`
- Описание: Тяжёлый ремонт: стандартный ремонт плюс очистка маршрутов; оригинальный скрипт отдельно спрашивает перед самыми глубокими reset-шагами.
- Риск: kind=`dangerous`, risk_level=`system_change`
- Параметры: нет.

### Очистка сети > Прокси > Статус прокси

- Operation id: `network_proxy_status`
- Описание: Показать параметры прокси текущего пользователя WinINet/System и системный WinHTTP proxy без изменений.
- Риск: kind=`safe`, risk_level=`readonly`
- Параметры: нет.

### Очистка сети > Прокси > Отключить прокси пользователя

- Operation id: `network_proxy_disable_user`
- Описание: Отключает WinINet/System proxy текущего пользователя. Полезно после корпоративных, VPN или proxy-инструментов, которые оставили устаревшие параметры.
- Риск: kind=`dangerous`, risk_level=`user_write`
- Параметры: нет.

### Очистка сети > Прокси > Сбросить WinHTTP proxy

- Operation id: `network_proxy_reset_winhttp`
- Описание: Сбрасывает системный WinHTTP proxy для служб и части системных инструментов. Не правит прокси браузера и текущего пользователя.
- Риск: kind=`dangerous`, risk_level=`system_change`
- Параметры: нет.

### Очистка сети > Открыть backup

- Operation id: `network_open_backup`
- Описание: Открыть project-local backup Network Cleaner со снимками, restore manifests и run logs.
- Риск: kind=`safe`, risk_level=`readonly`
- Параметры: нет.

### Подключение и адаптеры > Wi-Fi профили > Статус Wi-Fi

- Operation id: `network_wifi_status`
- Описание: Показать wlan interfaces и сохранённые профили Wi-Fi. Настройки сети не меняет.
- Риск: kind=`safe`, risk_level=`readonly`
- Параметры:
  - `wifi_profile` — **Wi-Fi профиль** (type=`select`).
  - `wifi_profile_override` — **Профиль вручную** (type=`text`).
  - `wifi_adapter` — **Wi-Fi адаптер** (type=`select`).

### Подключение и адаптеры > Wi-Fi профили > Подключить профиль

- Operation id: `network_wifi_connect`
- Описание: Подключиться к выбранному сохранённому Wi-Fi профилю, при необходимости через выбранный адаптер.
- Риск: kind=`safe`, risk_level=`readonly`
- Параметры:
  - `wifi_profile` — **Wi-Fi профиль** (type=`select`).
  - `wifi_profile_override` — **Профиль вручную** (type=`text`).
  - `wifi_adapter` — **Wi-Fi адаптер** (type=`select`).

### Подключение и адаптеры > Wi-Fi профили > Автоподключение профиля

- Operation id: `network_wifi_connection_mode`
- Описание: Переключить выбранный Wi-Fi профиль в автоматический или ручной режим подключения.
- Риск: kind=`dangerous`, risk_level=`system_change`
- Параметры:
  - `wifi_profile` — **Wi-Fi профиль** (type=`select`).
  - `wifi_profile_override` — **Профиль вручную** (type=`text`).
  - `wifi_adapter` — **Wi-Fi адаптер** (type=`select`).
  - `connection_mode` — **Режим подключения** (type=`radio`, default=`auto`).
    - Варианты: `auto` — Авто; `manual` — Вручную

### Подключение и адаптеры > Wi-Fi профили > Экспорт профилей

- Operation id: `network_wifi_export`
- Описание: Экспортировать Wi-Fi профили в выбранную папку; ключи открытым текстом включаются только отдельным чекбоксом.
- Риск: kind=`dangerous`, risk_level=`secret_export`
- Параметры:
  - `wifi_profile` — **Wi-Fi профиль** (type=`select`).
  - `wifi_profile_override` — **Профиль вручную** (type=`text`).
  - `wifi_adapter` — **Wi-Fi адаптер** (type=`select`).
  - `target_folder` — **Папка сохранения** (type=`folder`, default=`output\wifi_profiles`).
  - `include_keys` — **Включить ключи открытым текстом** (type=`checkbox`, default=false).

### Подключение и адаптеры > Wi-Fi профили > Импорт профилей > Импорт XML файла

- Operation id: `network_wifi_import_file`
- Описание: Добавить один XML-файл профиля Wi-Fi в Windows.
- Риск: kind=`dangerous`, risk_level=`system_change`
- Параметры:
  - `wifi_profile` — **Wi-Fi профиль** (type=`select`).
  - `wifi_profile_override` — **Профиль вручную** (type=`text`).
  - `wifi_adapter` — **Wi-Fi адаптер** (type=`select`).
  - `import_user_scope` — **Область импорта** (type=`radio`, default=`current`).
    - Варианты: `current` — Текущий пользователь; `all` — Все пользователи
  - `import_profile_xml` — **XML профиль** (type=`file`).

### Подключение и адаптеры > Wi-Fi профили > Импорт профилей > Импорт папки XML

- Operation id: `network_wifi_import_folder`
- Описание: Импортировать все XML-профили Wi-Fi из выбранной папки.
- Риск: kind=`dangerous`, risk_level=`system_change`
- Параметры:
  - `wifi_profile` — **Wi-Fi профиль** (type=`select`).
  - `wifi_profile_override` — **Профиль вручную** (type=`text`).
  - `wifi_adapter` — **Wi-Fi адаптер** (type=`select`).
  - `import_user_scope` — **Область импорта** (type=`radio`, default=`current`).
    - Варианты: `current` — Текущий пользователь; `all` — Все пользователи
  - `import_profile_folder` — **Папка XML профилей** (type=`folder`, default=`output\wifi_profiles`).

### Подключение и адаптеры > SMB вход в сеть

- Operation id: `smb_network_login`
- Описание: Открыть внешнюю консоль для net use входа к компьютеру с общими папками Windows: пароль вводится там, после этого SMB-сеанс доступен в Explorer.
- Риск: kind=`dangerous`, risk_level=`user_write`
- Параметры:
  - `smb_login` — **Кэш SMB-входов** (type=`smb_login_cache`, default=`{computer: '', user: ''}`).
  - `smb_open_explorer` — **Открыть Explorer после входа** (type=`checkbox`, default=true).

### Подключение и адаптеры > Действие адаптера

- Operation id: `network_adapter_apply`
- Описание: Включить, выключить или перезапустить выбранный сетевой адаптер. Может оборвать активное подключение.
- Риск: kind=`dangerous`, risk_level=`system_change`
- Параметры:
  - `adapter` — **Адаптер** (type=`select`).
  - `adapter_action` — **Действие** (type=`radio`, default=`restart`).
    - Варианты: `restart` — Перезапуск; `enable` — Включить; `disable` — Выключить

### Подключение и адаптеры > LAN/Wi-Fi переключатель

- Operation id: `network_lan_wifi_switch`
- Описание: Переключить LAN only, Wi-Fi only, включить оба адаптера или перезапустить Wi-Fi с подключением профиля.
- Риск: kind=`dangerous`, risk_level=`system_change`
- Параметры:
  - `lan_adapter` — **LAN адаптер** (type=`select`).
  - `wifi_adapter` — **Wi-Fi адаптер** (type=`select`).
  - `wifi_profile` — **Wi-Fi профиль** (type=`select`).
  - `wifi_profile_override` — **Wi-Fi профиль вручную** (type=`text`).
  - `switch_mode` — **Режим** (type=`radio`, default=`wifi_only`).
    - Варианты: `wifi_only` — Только Wi-Fi; `lan_only` — Только LAN; `both_on` — Оба включены; `cycle_wifi` — Перезапустить Wi-Fi

### Подключение и адаптеры > Wi-Fi sticky-пара

- Operation id: `network_wifi_sticky_pair`
- Описание: Подключить один сохраненный профиль и сделать его авто-профилем, а второй оставить ручным.
- Риск: kind=`dangerous`, risk_level=`system_change`
- Параметры:
  - `auto_wifi_profile` — **Авто-профиль** (type=`select`).
  - `auto_wifi_profile_override` — **Авто-профиль вручную** (type=`text`).
  - `manual_wifi_profile` — **Ручной профиль** (type=`select`).
  - `manual_wifi_profile_override` — **Ручной профиль вручную** (type=`text`).
  - `wifi_adapter` — **Wi-Fi адаптер** (type=`select`).
  - `connect_auto_profile` — **Подключить авто-профиль** (type=`checkbox`, default=true).

### WSL Toolkit > Базовые и установка > Статус WSL2 в системе

- Operation id: `wsl_system_status`
- Описание: Показать компоненты Windows, WSL status и установленные дистрибутивы.
- Риск: kind=`safe`, risk_level=`readonly`
- Параметры: нет.

### WSL Toolkit > Базовые и установка > Установить WSL2 в Windows

- Operation id: `wsl_enable_features`
- Описание: Включить компоненты Microsoft-Windows-Subsystem-Linux и VirtualMachinePlatform, затем поставить WSL default version 2. Может потребоваться перезагрузка.
- Риск: kind=`dangerous`, risk_level=`system_change`
- Параметры: нет.

### WSL Toolkit > Базовые и установка > Обновить WSL2

- Operation id: `wsl_update_engine`
- Описание: Выполнить wsl --update для Windows WSL engine.
- Риск: kind=`dangerous`, risk_level=`system_change`
- Параметры: нет.

### WSL Toolkit > Базовые и установка > Список для установки

- Operation id: `wsl_list_online`
- Описание: Выполнить wsl --list --online и вывести доступные имена дистрибутивов.
- Риск: kind=`safe`, risk_level=`readonly`
- Параметры: нет.

### WSL Toolkit > Базовые и установка > Установить дистрибутив

- Operation id: `wsl_install_distro`
- Описание: Установить выбранный online WSL-дистрибутив в системное место или в выбранную папку.
- Риск: kind=`dangerous`, risk_level=`system_change`
- Параметры:
  - `install_distro_pins` — **Пины дистрибутивов** (type=`profile_buttons`).
  - `install_distro` — **Дистрибутив** (type=`select`, default=`Ubuntu-26.04`).
  - `install_distro_override` — **Дистрибутив вручную** (type=`text`).
  - `install_name` — **Имя инстанса** (type=`text`).
  - `install_location_mode` — **Место установки** (type=`radio`, default=`custom`).
    - Варианты: `custom` — Выбранная папка; `system` — Системное место
  - `install_location` — **Папка установки** (type=`folder`).
  - `no_launch` — **Не запускать после установки** (type=`checkbox`, default=true).

### WSL Toolkit > Базовые и установка > Установить из файла образа

- Operation id: `wsl_install_from_file`
- Описание: Установить локальный .wsl образ, например ubuntu-26.04-wsl-amd64.wsl, или импортировать tar/vhd/vhdx в выбранную папку.
- Риск: kind=`dangerous`, risk_level=`system_change`
- Параметры:
  - `install_image_file` — **Файл образа WSL** (type=`file`).
  - `install_name` — **Имя дистрибутива** (type=`text`).
  - `install_location` — **Папка установки** (type=`folder`).
  - `no_launch` — **Не запускать после установки** (type=`checkbox`, default=true).

### WSL Toolkit > Базовые и установка > Список установленных

- Operation id: `wsl_list`
- Описание: Выполнить wsl --list --verbose.
- Риск: kind=`safe`, risk_level=`readonly`
- Параметры: нет.

### WSL Toolkit > Базовые и установка > Статус WSL

- Operation id: `wsl_status`
- Описание: Выполнить wsl --status.
- Риск: kind=`safe`, risk_level=`readonly`
- Параметры: нет.

### WSL Toolkit > Базовые и установка > Shutdown WSL

- Operation id: `wsl_shutdown`
- Описание: Остановить все WSL-дистрибутивы.
- Риск: kind=`dangerous`, risk_level=`system_change`
- Параметры: нет.

### WSL Toolkit > Linux-конфигурация > Package update

- Operation id: `wsl_linux_apt_update`
- Описание: Выполнить apt/dnf update metadata и при желании upgrade внутри выбранного WSL-дистрибутива.
- Риск: kind=`dangerous`, risk_level=`system_change`
- Параметры:
  - `wsl_name` — **Дистрибутив** (type=`select`).
  - `wsl_name_override` — **Имя вручную** (type=`text`).
  - `linux_username` — **Linux-пользователь** (type=`text`).
  - `wsl_apt_upgrade` — **Upgrade** (type=`radio`, default=`none`).
    - Варианты: `none` — Только update; `upgrade` — Upgrade; `full-upgrade` — Full upgrade / sync
  - `wsl_apt_network_repair` — **Устойчивый apt network mode** (type=`checkbox`, default=true).
  - `wsl_apt_force_ipv4` — **Force IPv4 для apt** (type=`checkbox`, default=true).
  - `wsl_apt_mirror` — **Ubuntu apt mirror** (type=`select`, default=`https_archive`).
    - Варианты: `https_archive` — archive.ubuntu.com через HTTPS; `https_azure` — azure.archive.ubuntu.com через HTTPS; `https_kernel` — mirrors.edge.kernel.org через HTTPS; `https_yandex` — mirror.yandex.ru через HTTPS; `keep` — Оставить текущие sources; `custom` — Custom mirror
  - `wsl_apt_custom_mirror` — **Custom apt mirror** (type=`text`).
  - `wsl_apt_retries` — **APT retries** (type=`number`, default=`4`).
  - `wsl_apt_timeout` — **APT timeout seconds** (type=`number`, default=`20`).

### WSL Toolkit > Linux-конфигурация > Учётка Linux

- Operation id: `wsl_linux_account`
- Описание: Создать/обновить пользователя Linux, пароль, sudo/wheel group и WSL default user.
- Риск: kind=`dangerous`, risk_level=`system_change`
- Параметры:
  - `wsl_name` — **Дистрибутив** (type=`select`).
  - `wsl_name_override` — **Имя вручную** (type=`text`).
  - `linux_username` — **Linux-пользователь** (type=`text`).
  - `linux_password` — **Пароль** (type=`password`).
  - `linux_set_password` — **Задать пароль** (type=`checkbox`, default=true).
  - `linux_add_sudo` — **Добавить в sudo/wheel** (type=`checkbox`, default=true).
  - `linux_set_default_user` — **Сделать WSL default user** (type=`checkbox`, default=true).
  - `linux_shell` — **Shell** (type=`text`, default=`/bin/bash`).

### WSL Toolkit > Linux-конфигурация > Dev-пакеты

- Operation id: `wsl_linux_dev_packages`
- Описание: Установить Audion WSL Dev packages. Heavy/Desktop пакеты не выбраны.
- Риск: kind=`dangerous`, risk_level=`system_change`
- Параметры:
  - `wsl_name` — **Дистрибутив** (type=`select`).
  - `wsl_name_override` — **Имя вручную** (type=`text`).
  - `linux_username` — **Linux-пользователь** (type=`text`).
  - `wsl_packages_baseline` — **Baseline пакеты** (type=`checkboxes`, default=`[ca-certificates, curl, wget, rsync, zstd, git, git-lfs, jq, tree, ripgrep, fd-find,
  fzf, unzip, zip, 7zip, htop, btop, ncdu, mc, far2l, micro, neovim, tmux, shellcheck,
  tree-sitter-cli, build-essential, gcc, g++, make, cmake, pkg-config, python3, python3-pip,
  python3-venv, pipx, openssh-client, rclone, net-tools, nmap, traceroute]`).
  - `wsl_packages_media_cli` — **Media CLI пакеты** (type=`checkboxes`, default=`[]`).
  - `wsl_packages_sync` — **Sync/network пакеты** (type=`checkboxes`, default=`[]`).
  - `wsl_packages_lab` — **Lab/container пакеты** (type=`checkboxes`, default=`[]`).
  - `wsl_apt_update_first` — **Сначала обновить package metadata** (type=`checkbox`, default=true).
  - `wsl_apt_network_repair` — **Устойчивый apt network mode** (type=`checkbox`, default=true).
  - `wsl_apt_force_ipv4` — **Force IPv4 для apt** (type=`checkbox`, default=true).
  - `wsl_apt_mirror` — **Ubuntu apt mirror** (type=`select`, default=`https_archive`).
    - Варианты: `https_archive` — archive.ubuntu.com через HTTPS; `https_azure` — azure.archive.ubuntu.com через HTTPS; `https_kernel` — mirrors.edge.kernel.org через HTTPS; `https_yandex` — mirror.yandex.ru через HTTPS; `keep` — Оставить текущие sources; `custom` — Custom mirror
  - `wsl_apt_custom_mirror` — **Custom apt mirror** (type=`text`).
  - `wsl_apt_retries` — **APT retries** (type=`number`, default=`4`).
  - `wsl_apt_timeout` — **APT timeout seconds** (type=`number`, default=`20`).
  - `wsl_install_recommends` — **Ставить recommended packages** (type=`checkbox`, default=false).
  - `wsl_selinux_permissive` — **Усыпить SELinux (Fedora)** (type=`checkbox`, default=false).
  - `wsl_flatpak_flathub` — **Flatpak + Flathub remote** (type=`checkbox`, default=false).
  - `wsl_optional_packages` — **Опциональные пакеты** (type=`textarea`).

### WSL Toolkit > Linux-конфигурация > Micro baseline

- Operation id: `wsl_micro_baseline`
- Описание: Поставить Audion-настройки micro и keybindings для выбранного Linux-пользователя.
- Риск: kind=`dangerous`, risk_level=`user_write`
- Параметры:
  - `wsl_name` — **Дистрибутив** (type=`select`).
  - `wsl_name_override` — **Имя вручную** (type=`text`).
  - `linux_username` — **Linux-пользователь** (type=`text`).

### WSL Toolkit > Linux-конфигурация > MC skin

- Operation id: `wsl_mc_skin`
- Описание: Поставить Audion skin для Midnight Commander и при желании сделать активным.
- Риск: kind=`dangerous`, risk_level=`user_write`
- Параметры:
  - `wsl_name` — **Дистрибутив** (type=`select`).
  - `wsl_name_override` — **Имя вручную** (type=`text`).
  - `linux_username` — **Linux-пользователь** (type=`text`).
  - `mc_skin` — **Skin** (type=`radio`, default=`electricblue256`).
    - Варианты: `electricblue256` — Electric Blue; `audion256` — Audion
  - `mc_apply_skin` — **Сделать активным skin MC** (type=`checkbox`, default=true).

### WSL Toolkit > Linux-конфигурация > Neovim base

- Operation id: `wsl_neovim_base`
- Описание: Поставить Audion-профиль Neovim без AI-провайдеров.
- Риск: kind=`dangerous`, risk_level=`user_write`
- Параметры:
  - `wsl_name` — **Дистрибутив** (type=`select`).
  - `wsl_name_override` — **Имя вручную** (type=`text`).
  - `linux_username` — **Linux-пользователь** (type=`text`).
  - `nvim_appname` — **NVIM_APPNAME** (type=`text`, default=`audion-ide`).
  - `nvim_profile` — **Профиль** (type=`radio`, default=`lite`).
    - Варианты: `lite` — Lite; `lazyvim` — LazyVim

### WSL Toolkit > Ubuntu Dev Installer Kit > Открыть папку kit

- Operation id: `ubuntu_dev_open_folder`
- Описание: Открыть tools/ubuntu_dev_installer.
- Риск: kind=`safe`, risk_level=`readonly`
- Параметры: нет.

### WSL Toolkit > Ubuntu Dev Installer Kit > Открыть README RU

- Operation id: `ubuntu_dev_open_readme_ru`
- Описание: Открыть README RU для project-local Ubuntu kit.
- Риск: kind=`safe`, risk_level=`readonly`
- Параметры: нет.

### WSL Toolkit > Ubuntu Dev Installer Kit > Открыть Btrfs guide

- Operation id: `ubuntu_dev_open_btrfs_guide`
- Описание: Открыть Btrfs/Timeshift LiveUSB guide.
- Риск: kind=`safe`, risk_level=`readonly`
- Параметры: нет.

### WSL Toolkit > Ubuntu Dev Installer Kit > Открыть installer script

- Operation id: `ubuntu_dev_open_installer_script`
- Описание: Открыть главный Ubuntu dev installer script из project-local kit.
- Риск: kind=`safe`, risk_level=`readonly`
- Параметры: нет.

### WSL Toolkit > Ubuntu Dev Installer Kit > Открыть NVMe prep script

- Operation id: `ubuntu_dev_open_nvme_prep_script`
- Описание: Открыть Btrfs/LUKS Ubuntu LiveUSB prep script из project-local kit.
- Риск: kind=`safe`, risk_level=`readonly`
- Параметры: нет.

### WSL Toolkit > Ubuntu Dev Installer Kit > Открыть списки пакетов

- Operation id: `ubuntu_dev_open_packages`
- Описание: Открыть папку package-list, которую использует kit.
- Риск: kind=`safe`, risk_level=`readonly`
- Параметры: нет.

### WSL Toolkit > Действия с дистрибутивом > Остановить дистрибутив

- Operation id: `wsl_terminate`
- Описание: Остановить выбранный WSL-дистрибутив.
- Риск: kind=`dangerous`, risk_level=`system_change`
- Параметры:
  - `wsl_name` — **Дистрибутив** (type=`select`).
  - `wsl_name_override` — **Имя вручную** (type=`text`).

### WSL Toolkit > Действия с дистрибутивом > Backup дистрибутива

- Operation id: `wsl_backup`
- Описание: Экспортировать дистрибутив в tar или vhd.
- Риск: kind=`dangerous`, risk_level=`secret_export`
- Параметры:
  - `wsl_name` — **Дистрибутив** (type=`select`).
  - `wsl_name_override` — **Имя вручную** (type=`text`).
  - `format` — **Формат** (type=`radio`, default=`tar`).
    - Варианты: `tar` — tar; `vhd` — vhd
  - `backup_dir` — **Папка backup вручную** (type=`folder`).

### WSL Toolkit > Действия с дистрибутивом > Клонировать дистрибутив

- Operation id: `wsl_clone`
- Описание: Экспортировать и импортировать под новым именем.
- Риск: kind=`dangerous`, risk_level=`system_change`
- Параметры:
  - `wsl_name` — **Дистрибутив** (type=`select`).
  - `wsl_name_override` — **Имя вручную** (type=`text`).
  - `new_name` — **Новое имя** (type=`text`).
  - `location` — **Папка установки** (type=`folder`).
  - `backup_dir` — **Временная папка backup** (type=`folder`).

### WSL Toolkit > Действия с дистрибутивом > Перенести дистрибутив

- Operation id: `wsl_move`
- Описание: Перенести дистрибутив через export/import. Операция использует временный backup и затем unregister старого имени; сначала проверь target и папку backup.
- Риск: kind=`dangerous`, risk_level=`destructive`
- Параметры:
  - `wsl_name` — **Дистрибутив** (type=`select`).
  - `wsl_name_override` — **Имя вручную** (type=`text`).
  - `location` — **Новая папка установки** (type=`folder`).
  - `backup_dir` — **Временная папка backup** (type=`folder`).

### WSL Toolkit > Действия с дистрибутивом > Удалить дистрибутив

- Operation id: `wsl_delete`
- Описание: Навсегда unregister выбранного WSL-дистрибутива: Windows удалит регистрацию и файловую систему дистрибутива. Перед этим сделай Backup дистрибутива, если нужен откат.
- Риск: kind=`dangerous`, risk_level=`destructive`
- Параметры:
  - `wsl_name` — **Дистрибутив** (type=`select`).
  - `wsl_name_override` — **Имя вручную** (type=`text`).

### WSL Toolkit > Import и restore > Import VHDX in-place

- Operation id: `wsl_import_in_place`
- Описание: Зарегистрировать существующий ext4.vhdx как WSL-дистрибутив.
- Риск: kind=`dangerous`, risk_level=`system_change`
- Параметры:
  - `wsl_name_override` — **Имя дистрибутива** (type=`text`).
  - `vhdx_path` — **VHDX файл** (type=`select`).
  - `vhdx_path_manual` — **VHDX файл вручную** (type=`file`).

### WSL Toolkit > Import и restore > Restore из backup

- Operation id: `wsl_restore_from_backup`
- Описание: Импортировать tar/vhd/vhdx backup как WSL-дистрибутив.
- Риск: kind=`dangerous`, risk_level=`system_change`
- Параметры:
  - `wsl_name_override` — **Имя дистрибутива** (type=`text`).
  - `location` — **Папка установки** (type=`folder`).
  - `backup_file` — **Backup файл** (type=`select`).
  - `backup_file_manual` — **Backup файл вручную** (type=`file`).

### WSL Toolkit > Регистрация VHDX пачкой > Зарегистрировать все VHDX

- Operation id: `wsl_register_all_vhdx`
- Описание: Неинтерактивный batch import-in-place. По умолчанию dry run; существующие имена дистрибутивов пропускаются.
- Риск: kind=`dangerous`, risk_level=`system_change`
- Параметры:
  - `register_root` — **Корень VHDX** (type=`folder`).
  - `filter` — **Фильтр файлов** (type=`text`, default=`ext4.vhdx`).
  - `dry_run` — **Dry-run** (type=`checkbox`, default=true).

### Виртуализация > Статус виртуализации

- Operation id: `virt_status`
- Описание: Показать hypervisorlaunchtype, состояние компонентов Hyper-V/VMPlatform/WHP/Sandbox/WSL, VBS/Core Isolation и интерпретированный текущий режим.
- Риск: kind=`safe`, risk_level=`readonly`
- Параметры: нет.

### Виртуализация > Статус оптимизации

- Operation id: `virt_optimization_status`
- Описание: Только чтение: что тормозит VM/WSL - Core Isolation/VBS, активная схема электропитания, исключения Microsoft Defender для путей WSL/VM, наличие .wslconfig и расположение WSL VHDX.
- Риск: kind=`safe`, risk_level=`readonly`
- Параметры: нет.

### Виртуализация > Режим: Hyper-V / WSL2

- Operation id: `virt_mode_hyperv`
- Описание: hypervisorlaunchtype=Auto и включение VirtualMachinePlatform. Заработают Hyper-V/WSL2/Windows Sandbox; сторонние VM - только через WHP или не стартуют. Backup: backup\virtualization. Нужна перезагрузка.
- Риск: kind=`dangerous`, risk_level=`system_change`
- Параметры: нет.

### Виртуализация > Режим: Сторонние VM (быстро)

- Operation id: `virt_mode_thirdparty`
- Описание: hypervisorlaunchtype=Off. VMware/VirtualBox на полной скорости; WSL2/Hyper-V/Windows Sandbox перестанут работать до обратного переключения. При включённом VBS/Core Isolation VT-x всё равно может быть занят. Backup: backup\virtualization. Нужна перезагрузка.
- Риск: kind=`dangerous`, risk_level=`system_change`
- Параметры: нет.

### Виртуализация > Режим: Сосуществование (WHP)

- Operation id: `virt_mode_coexist`
- Описание: hypervisorlaunchtype=Auto + включение Windows Hypervisor Platform и VirtualMachinePlatform, чтобы современные VMware/VirtualBox работали рядом с Hyper-V/WSL2 (медленнее). Backup: backup\virtualization. Нужна перезагрузка.
- Риск: kind=`dangerous`, risk_level=`system_change`
- Параметры: нет.

### Виртуализация > Включить Hyper-V

- Operation id: `virt_hyperv_enable`
- Описание: Включить Microsoft-Hyper-V-All (Диспетчер Hyper-V + платформа) и hypervisorlaunchtype=Auto. Backup: backup\virtualization. Нужна перезагрузка.
- Риск: kind=`dangerous`, risk_level=`system_change`
- Параметры: нет.

### Виртуализация > Выключить Hyper-V

- Operation id: `virt_hyperv_disable`
- Описание: Выключить Microsoft-Hyper-V-All. Для полной скорости сторонних VM также примените режим «Сторонние VM» (hypervisorlaunchtype=Off). Backup: backup\virtualization. Нужна перезагрузка.
- Риск: kind=`dangerous`, risk_level=`system_change`
- Параметры: нет.

### Виртуализация > Включить Windows Sandbox

- Operation id: `virt_sandbox_enable`
- Описание: Включить Containers-DisposableClientVM (Windows Sandbox). Требует включённый гипервизор (режим Hyper-V/WSL2). Backup: backup\virtualization. Нужна перезагрузка.
- Риск: kind=`dangerous`, risk_level=`system_change`
- Параметры: нет.

### Виртуализация > Выключить Windows Sandbox

- Operation id: `virt_sandbox_disable`
- Описание: Выключить Containers-DisposableClientVM (Windows Sandbox). Backup: backup\virtualization. Нужна перезагрузка.
- Риск: kind=`dangerous`, risk_level=`system_change`
- Параметры: нет.

### Hosts и Bitrix > Найти текущий endpoint

- Operation id: `bitrix_detect_endpoint`
- Описание: DNS-only lookup игнорирует старые hosts-записи, принимает только локальные/частные IP-адреса, сканирует порты-кандидаты и подставляет IP/ports в поля без изменения hosts.
- Риск: kind=`safe`, risk_level=`readonly`
- Параметры:
  - `hosts_presets` — **Пины** (type=`profile_buttons`).
  - `host_name` — **Host name** (type=`text`, default=`portal.itpgrad.ru`).
  - `ip_address` — **IP address** (type=`text`, default=`192.168.0.130`).
  - `bitrix_ports` — **Ручные TCP ports** (type=`text`, default=`443`).
  - `bitrix_auto_scan_ports` — **Авто-скан открытых портов** (type=`checkbox`, default=true).
  - `bitrix_port_scan_candidates` — **Кандидаты портов** (type=`text`, default=`80,443,8080,8443,8890,8891,8892`).

### Hosts и Bitrix > Статус / DNS / ports

- Operation id: `bitrix_status`
- Описание: Показать hosts override, фактический resolved IP, DNS-ответ, авто-скан портов и TCP-проверку.
- Риск: kind=`safe`, risk_level=`readonly`
- Параметры:
  - `hosts_presets` — **Пины** (type=`profile_buttons`).
  - `host_name` — **Host name** (type=`text`, default=`portal.itpgrad.ru`).
  - `ip_address` — **IP address** (type=`text`, default=`192.168.0.130`).
  - `bitrix_ports` — **Ручные TCP ports** (type=`text`, default=`443`).
  - `bitrix_auto_scan_ports` — **Авто-скан открытых портов** (type=`checkbox`, default=true).
  - `bitrix_port_scan_candidates` — **Кандидаты портов** (type=`text`, default=`80,443,8080,8443,8890,8891,8892`).

### Hosts и Bitrix > Включить override

- Operation id: `bitrix_enable`
- Описание: Применить hosts override для host и IP; найденные/custom порты сохраняются в управляемом комментарии hosts.
- Риск: kind=`dangerous`, risk_level=`system_change`
- Параметры:
  - `hosts_presets` — **Пины** (type=`profile_buttons`).
  - `host_name` — **Host name** (type=`text`, default=`portal.itpgrad.ru`).
  - `ip_address` — **IP address** (type=`text`, default=`192.168.0.130`).
  - `bitrix_ports` — **Ручные TCP ports** (type=`text`, default=`443`).
  - `bitrix_auto_scan_ports` — **Авто-скан открытых портов** (type=`checkbox`, default=true).
  - `bitrix_port_scan_candidates` — **Кандидаты портов** (type=`text`, default=`80,443,8080,8443,8890,8891,8892`).

### Hosts и Bitrix > Выключить override

- Operation id: `bitrix_disable`
- Описание: Побитовый depatch: восстановить точный pre-patch backup hosts, указанный в managed hosts line.
- Риск: kind=`dangerous`, risk_level=`system_change`
- Параметры:
  - `hosts_presets` — **Пины** (type=`profile_buttons`).
  - `host_name` — **Host name** (type=`text`, default=`portal.itpgrad.ru`).
  - `ip_address` — **IP address** (type=`text`, default=`192.168.0.130`).
  - `bitrix_ports` — **Ручные TCP ports** (type=`text`, default=`443`).
  - `bitrix_auto_scan_ports` — **Авто-скан открытых портов** (type=`checkbox`, default=true).
  - `bitrix_port_scan_candidates` — **Кандидаты портов** (type=`text`, default=`80,443,8080,8443,8890,8891,8892`).

### Hosts и Bitrix > Восстановить hosts

- Operation id: `bitrix_restore`
- Описание: Восстановить hosts из последнего pre-patch backup, когда явный depatch по managed-line недоступен.
- Риск: kind=`dangerous`, risk_level=`system_change`
- Параметры:
  - `hosts_presets` — **Пины** (type=`profile_buttons`).
  - `host_name` — **Host name** (type=`text`, default=`portal.itpgrad.ru`).
  - `ip_address` — **IP address** (type=`text`, default=`192.168.0.130`).
  - `bitrix_ports` — **Ручные TCP ports** (type=`text`, default=`443`).
  - `bitrix_auto_scan_ports` — **Авто-скан открытых портов** (type=`checkbox`, default=true).
  - `bitrix_port_scan_candidates` — **Кандидаты портов** (type=`text`, default=`80,443,8080,8443,8890,8891,8892`).

### Приложения по умолчанию > Политика

- Operation id: `default_apps_policy`
- Описание: Запоминает, какими программами открываются ваши файлы, и заставляет Windows возвращать этот набор при каждом входе.
- Риск: kind=`dangerous`, risk_level=`system_change`
- Параметры:
  - `policy_action` — **Что сделать** (type=`radio`, default=`status`).
    - Варианты: `status` — Проверить — чем сейчас открываются файлы; `snapshot` — Сохранить снимок текущего состояния; `export` — Экспортировать текущие ассоциации в эталон; `import` — Взять эталон из файла; `apply` — Закрепить сохранённые ассоциации; `remove` — Снять закрепление; `cleanup` — Убрать старые резервные копии; `open_profiles` — Открыть папку эталона; `open_policy` — Открыть папку закреплённого набора; `open_backups` — Открыть папку резервных копий
  - `profile_xml` — **Файл эталона** (type=`file`, default=`profiles\default_apps\AppAssociations.xml`).
  - `import_backup_xml` — **Сохранённый снимок** (type=`select`, default=``).
  - `import_profile_xml` — **Файл с другого компьютера** (type=`file`, default=``).
  - `strip_suggested` — **Закреплять жёстко** (type=`checkbox`, default=true).
  - `backup_label` — **Метка резервной копии** (type=`text`, default=``).
  - `check_identifiers` — **Какие типы файлов отслеживать** (type=`checkboxes`, default=`[http, https, .htm, .html, .pdf, .txt, .md, .rtf, .doc, .docx, .xls, .xlsx, .ppt,
  .pptx, .zip, .7z, .rar, .tar, .gz, .jpg, .jpeg, .png, .webp, .gif, .bmp, .tif, .tiff,
  .svg, .avif, .heic, .psd, .mp4, .mkv, .webm, .avi, .mov, .mxf, .mp3, .flac, .wav,
  .m4a, .aac, .ogg, .opus, .alac, .m3u, .m3u8, .pls]`).
    - Варианты: `http` — http; `https` — https; `.htm` — .htm; `.html` — .html; `.pdf` — .pdf; `.txt` — .txt; `.md` — .md; `.rtf` — .rtf; `.doc` — .doc; `.docx` — .docx; `.xls` — .xls; `.xlsx` — .xlsx; `.ppt` — .ppt; `.pptx` — .pptx; `.zip` — .zip; `.7z` — .7z; `.rar` — .rar; `.tar` — .tar; `.gz` — .gz; `.jpg` — .jpg; `.jpeg` — .jpeg; `.png` — .png; `.webp` — .webp; `.gif` — .gif; `.bmp` — .bmp; `.tif` — .tif; `.tiff` — .tiff; `.svg` — .svg; `.avif` — .avif; `.heic` — .heic; `.psd` — .psd; `.mp4` — .mp4; `.mkv` — .mkv; `.webm` — .webm; `.avi` — .avi; `.mov` — .mov; `.mxf` — .mxf; `.mp3` — .mp3; `.flac` — .flac; `.wav` — .wav; `.m4a` — .m4a; `.aac` — .aac; `.ogg` — .ogg; `.opus` — .opus; `.alac` — .alac; `.m3u` — .m3u; `.m3u8` — .m3u8; `.pls` — .pls
  - `extra_identifiers` — **Добавить свои типы** (type=`text`, default=``).
  - `include_dism_inventory` — **Полный список Windows** (type=`checkbox`, default=false).
  - `remove_policy_xml` — **Удалить и закреплённый файл** (type=`checkbox`, default=false).
  - `allow_unsupported_policy_edition` — **Разрешить неподдерживаемую редакцию** (type=`checkbox`, default=false).
  - `program_data_dir` — **Системная папка набора** (type=`folder`, default=`%ProgramData%\Audion\DefaultApps`).
  - `backup_dir` — **Папка резервных копий** (type=`folder`, default=`backup\default_apps`).
  - `backup_retention_days` — **Хранить копии, дней** (type=`number`, default=`30`).
  - `cleanup_dry_run` — **Очистка: пробный запуск** (type=`checkbox`, default=true).

### Приложения по умолчанию > Microsoft

- Operation id: `default_apps_microsoft`
- Описание: Убирает или возвращает встроенные приложения Microsoft и удерживает результат после обновлений Windows.
- Риск: kind=`dangerous`, risk_level=`system_change`
- Параметры:
  - `apps_action` — **Что сделать** (type=`radio`, default=`status`).
    - Варианты: `status` — Проверить — что стоит в системе; `remove` — Удалить отмеченные приложения; `keep_removed` — Удалить и держать удалёнными; `restore` — Вернуть приложения; `provision` — Починить для новых пользователей; `allow_back` — Перестать держать удалёнными; `rearm_check` — Проверить удержание сейчас; `open_logs` — Открыть папку удержания
  - `apps` — **Приложения** (type=`checkboxes`, default=`[ZuneMusic, ZuneVideo]`).
    - Варианты: `ZuneMusic` — Медиаплеер (Zune); `ZuneVideo` — Кино и ТВ (Zune); `Photos` — Фотографии; `Clipchamp` — Clipchamp; `SoundRecorder` — Запись голоса; `Camera` — Камера (нужна сканерам и QR); `Paint` — Paint (правка картинок); `ScreenSketch` — Ножницы (Win+Shift+S); `GamingApp` — Xbox; `XboxGamingOverlay` — Игровая панель Xbox; `XboxSpeechToTextOverlay` — Речевая панель Xbox; `XboxIdentityProvider` — Удостоверения Xbox (вход в играх); `SolitaireCollection` — Коллекция пасьянсов; `YourPhone` — Связь с телефоном; `People` — Люди; `Teams` — Microsoft Teams; `OutlookForWindows` — Outlook для Windows; `BingNews` — Новости; `BingWeather` — Погода; `Getstarted` — Советы; `FeedbackHub` — Центр отзывов; `WindowsMaps` — Карты; `Copilot` — Copilot; `StickyNotes` — Записки; `Todos` — To Do; `OneNote` — OneNote для Windows; `Whiteboard` — Доска; `PowerAutomateDesktop` — Power Automate; `QuickAssist` — Быстрая поддержка (удалённая помощь); `DevHome` — Dev Home; `Family` — Семья Microsoft
  - `dry_run` — **Пробный запуск** (type=`checkbox`, default=true).

### Приложения по умолчанию > Edge

- Operation id: `default_apps_edge`
- Описание: Оставляет Edge на месте, но отучает его перетягивать ссылки и типы файлов у вашего основного браузера.
- Риск: kind=`dangerous`, risk_level=`system_change`
- Параметры:
  - `edge_owned_now` — **Что сейчас закреплено за Edge** (type=`info_badges`).
  - `edge_action` — **Что сделать** (type=`radio`, default=`status`).
    - Варианты: `status` — Проверить — что сейчас держит Edge; `apply` — Запретить Edge перетягивать ассоциации; `revert` — Вернуть Edge как было; `webview2` — Починить WebView2
  - `edge_level` — **Насколько тихо** (type=`radio`, default=`calm`).
    - Варианты: `calm` — Спокойно — без навязывания и фона; `quiet` — Тихо — плюс боковые панели и лишнее
  - `dry_run` — **Пробный запуск** (type=`checkbox`, default=true).

### Приложения по умолчанию > Отслеживание

- Operation id: `default_apps_watch`
- Описание: Отслеживает смену ассоциаций и управляет исключениями Defender для папок Audion.
- Риск: kind=`dangerous`, risk_level=`system_change`
- Параметры:
  - `guard_action` — **Что сделать** (type=`radio`, default=`status`).
    - Варианты: `status` — Проверить; `enable` — Включить; `disable` — Выключить; `run_check` — Проверить изменения прямо сейчас
  - `guard_targets` — **Что включить** (type=`checkboxes`, default=`[Drift]`).
    - Варианты: `Drift` — Отслеживание смены ассоциаций; `Defender` — Исключения Defender для папок Audion

### Приложения по умолчанию > Снимок

- Operation id: `default_apps_snapshot`
- Описание: Сохраняет и сравнивает карту ассоциаций текущего пользователя.
- Риск: kind=`dangerous`, risk_level=`user_write`
- Параметры:
  - `snapshot_action` — **Что сделать** (type=`radio`, default=`status`).
    - Варианты: `status` — Сравнить снимок с текущим состоянием; `capture` — Сохранить текущие ассоциации; `open_snapshots` — Открыть папку снимков
  - `snapshot_name` — **Имя снимка** (type=`text`, default=`Microsoft Snapshot`).
  - `snapshot_machine` — **Метка машины** (type=`text`, default=``).
  - `dry_run` — **Пробный запуск** (type=`checkbox`, default=true).

### Приложения по умолчанию > Группы

- Operation id: `default_apps_groups`
- Описание: Сохраняет ассоциации по группам — фото, аудио, видео, PDF, браузер — пока нужные программы установлены.
- Риск: kind=`dangerous`, risk_level=`user_write`
- Параметры:
  - `group_action` — **Что сделать** (type=`radio`, default=`status`).
    - Варианты: `status` — Проверить группы; `commit` — Сохранить выбранную группу; `compose` — Собрать общий снимок из групп
  - `group_name` — **Группа** (type=`radio`, default=`photo`).
    - Варианты: `photo` — Фото; `audio` — Аудио; `video` — Видео; `pdf` — PDF и книги; `documents` — Документы; `archives` — Архивы; `browser` — Браузер; `custom` — Свой
  - `group_custom_name` — **Имя своей группы** (type=`text`, default=``).
  - `group_ext` — **Свои расширения** (type=`text`, default=``).
  - `snapshot_name` — **Имя общего снимка** (type=`text`, default=`Microsoft Snapshot`).
  - `snapshot_machine` — **Метка машины** (type=`text`, default=``).
  - `dry_run` — **Пробный запуск** (type=`checkbox`, default=true).

### Приложения по умолчанию > Общий отчёт

- Operation id: `default_apps_overview`
- Описание: Прогоняет все проверки этого раздела подряд и печатает единый отчёт.
- Риск: kind=`safe`, risk_level=`readonly`
- Параметры: нет.

### Hardware > Driver/Firmware Audit

- Operation id: `driver_firmware_audit`
- Описание: Диагностический отчёт без изменений: проблемные устройства из Диспетчера устройств, BIOS/EC, firmware/UEFI resources и ключевые подписанные драйверы.
- Риск: kind=`safe`, risk_level=`project_write`
- Параметры:
  - `output_dir` — **Папка отчёта** (type=`folder`, default=`logs`).
  - `json` — **Писать JSON** (type=`checkbox`, default=true).
  - `csv` — **Писать CSV key drivers** (type=`checkbox`, default=true).
  - `open_report` — **Открыть отчёт в Notepad** (type=`checkbox`, default=false).

### Hardware > Материалы Driver/Firmware Audit > Открыть папку аддона

- Operation id: `driver_firmware_audit_open_folder`
- Описание: Открыть tools/driver_firmware_audit.
- Риск: kind=`safe`, risk_level=`readonly`
- Параметры: нет.

### Hardware > Материалы Driver/Firmware Audit > Открыть README

- Operation id: `driver_firmware_audit_open_readme`
- Описание: Открыть README аддона из project-local copy.
- Риск: kind=`safe`, risk_level=`readonly`
- Параметры: нет.

### Hardware > Driver Update Blocker > Windows Update driver policy > Проверить защиту драйверов

- Operation id: `driver_update_status`
- Описание: Статус без изменений: Windows Update driver policy, параметры поиска драйверов, device metadata policy, DeviceInstall restrictions и текущие NVIDIA PCI устройства.
- Риск: kind=`safe`, risk_level=`readonly`
- Параметры: нет.

### Hardware > Driver Update Blocker > Windows Update driver policy > Блокировать драйверы Windows Update

- Operation id: `driver_update_block_all`
- Описание: Делает backup policy-ключей, ставит ExcludeWUDriversInQualityUpdate=1, выключает поиск драйверов через мастер установки оборудования и загрузку метаданных устройств, затем запускает gpupdate. Рекомендуется перезагрузка.
- Риск: kind=`dangerous`, risk_level=`system_change`
- Параметры: нет.

### Hardware > Driver Update Blocker > Windows Update driver policy > Разблокировать драйверы Windows Update

- Operation id: `driver_update_unblock_all`
- Описание: Делает backup policy-ключей, удаляет значения блокировки драйверов Центра обновления Windows, возвращает обычное поведение driver search, затем запускает gpupdate. Рекомендуется перезагрузка.
- Риск: kind=`dangerous`, risk_level=`system_change`
- Параметры: нет.

### Hardware > Driver Update Blocker > Windows Update driver policy > Открыть policy backups

- Operation id: `driver_update_open_policy_backups`
- Описание: Открыть backups policy-ключей реестра, которые создаются перед block/unblock операциями.
- Риск: kind=`safe`, risk_level=`readonly`
- Параметры: нет.

### Hardware > Driver Update Blocker > HWID-защита драйвера устройства > Проверить текущий lock

- Operation id: `hwid_driver_status`
- Описание: Проверка без изменений: показывает, залочен ли этот HWID и какой драйвер сейчас best-ranked/installed.
- Риск: kind=`safe`, risk_level=`readonly`
- Параметры:
  - `hwid_builtin_cache_pins` — **Preset** (type=`profile_buttons`).
  - `hwid_guard_identity_badges` — **Идентификация** (type=`info_badges`).
  - `target_hardware_ids` — **HWID для защиты** (type=`textarea`, default=`PCI\VEN_8086&DEV_46A8&SUBSYS_22E717AA
`).
  - `target_device_instance_id` — **Device Instance ID** (type=`text`).
  - `hwid_retroactive` — **Retroactive block** (type=`checkbox`, default=false).
  - `hwid_keep_global_wu_block` — **Оставить global WU driver block** (type=`checkbox`, default=false).

### Hardware > Driver Update Blocker > HWID-защита драйвера устройства > 1. Разблокировать перед обновлением

- Operation id: `hwid_driver_unblock`
- Описание: Нажать перед установкой нужного manual/generic драйвера. Удаляет matching HWID locks, сохраняя чужие policy entries.
- Риск: kind=`dangerous`, risk_level=`system_change`
- Параметры:
  - `hwid_builtin_cache_pins` — **Preset** (type=`profile_buttons`).
  - `hwid_guard_identity_badges` — **Идентификация** (type=`info_badges`).
  - `target_hardware_ids` — **HWID для защиты** (type=`textarea`, default=`PCI\VEN_8086&DEV_46A8&SUBSYS_22E717AA
`).
  - `target_device_instance_id` — **Device Instance ID** (type=`text`).
  - `hwid_retroactive` — **Retroactive block** (type=`checkbox`, default=false).
  - `hwid_keep_global_wu_block` — **Оставить global WU driver block** (type=`checkbox`, default=false).

### Hardware > Driver Update Blocker > HWID-защита драйвера устройства > 2. Заблокировать после установки

- Operation id: `hwid_driver_block`
- Описание: Нажать после установки и проверки нужного драйвера. Добавляет этот HWID в DenyDeviceIDs, чтобы Windows Driver Store/WU не подменил его молча.
- Риск: kind=`dangerous`, risk_level=`system_change`
- Параметры:
  - `hwid_builtin_cache_pins` — **Preset** (type=`profile_buttons`).
  - `hwid_guard_identity_badges` — **Идентификация** (type=`info_badges`).
  - `target_hardware_ids` — **HWID для защиты** (type=`textarea`, default=`PCI\VEN_8086&DEV_46A8&SUBSYS_22E717AA
`).
  - `target_device_instance_id` — **Device Instance ID** (type=`text`).
  - `hwid_retroactive` — **Retroactive block** (type=`checkbox`, default=false).
  - `hwid_keep_global_wu_block` — **Оставить global WU driver block** (type=`checkbox`, default=false).

### Hardware > Driver Update Blocker > Аварийный rank repair по HWID > Проверить rank target

- Operation id: `hwid_driver_rank_status`
- Описание: Read-only проверка target: определяет устройство по HWID, показывает current signed driver data и pnputil driver/rank report.
- Риск: kind=`safe`, risk_level=`readonly`
- Параметры:
  - `hwid_builtin_cache_pins` — **Preset** (type=`profile_buttons`).
  - `hwid_repair_identity_badges` — **Repair markers** (type=`info_badges`).
  - `target_hardware_ids` — **HWID для ремонта** (type=`textarea`, default=`PCI\VEN_8086&DEV_46A8&SUBSYS_22E717AA
`).
  - `target_device_instance_id` — **Device Instance ID** (type=`text`).
  - `bad_driver_version` — **Bad driver version** (type=`text`, default=`32.0.101.7026`).
  - `target_driver_version` — **Target driver version** (type=`text`, default=`32.0.101.7085`).
  - `target_inf_name_pattern` — **Target INF pattern** (type=`text`, default=`*.inf`).
  - `target_inf_path` — **Target INF path** (type=`text`).
  - `driver_rank_class` — **Driver class** (type=`text`, default=`Display`).
  - `skip_current_version_check` — **Пропустить current version check** (type=`checkbox`, default=false).
  - `allow_version_only_target_inf_fallback` — **Разрешить INF fallback только по версии** (type=`checkbox`, default=false).
  - `no_policy_block_after_repair` — **Не блокировать HWID после ремонта** (type=`checkbox`, default=false).
  - `hwid_keep_global_wu_block` — **Оставить global WU driver block** (type=`checkbox`, default=false).

### Hardware > Driver Update Blocker > Аварийный rank repair по HWID > Починить driver rank по HWID

- Operation id: `hwid_driver_rank_repair`
- Описание: Создаёт REG/JSON preflight backup, экспортирует старый package, удаляет bad current INF package, ставит target INF, делает rescan/restart устройства, затем применяет targeted HWID block. Используй только после проверки target.
- Риск: kind=`dangerous`, risk_level=`system_change`
- Параметры:
  - `hwid_builtin_cache_pins` — **Preset** (type=`profile_buttons`).
  - `hwid_repair_identity_badges` — **Repair markers** (type=`info_badges`).
  - `target_hardware_ids` — **HWID для ремонта** (type=`textarea`, default=`PCI\VEN_8086&DEV_46A8&SUBSYS_22E717AA
`).
  - `target_device_instance_id` — **Device Instance ID** (type=`text`).
  - `bad_driver_version` — **Bad driver version** (type=`text`, default=`32.0.101.7026`).
  - `target_driver_version` — **Target driver version** (type=`text`, default=`32.0.101.7085`).
  - `target_inf_name_pattern` — **Target INF pattern** (type=`text`, default=`*.inf`).
  - `target_inf_path` — **Target INF path** (type=`text`).
  - `driver_rank_class` — **Driver class** (type=`text`, default=`Display`).
  - `skip_current_version_check` — **Пропустить current version check** (type=`checkbox`, default=false).
  - `allow_version_only_target_inf_fallback` — **Разрешить INF fallback только по версии** (type=`checkbox`, default=false).
  - `no_policy_block_after_repair` — **Не блокировать HWID после ремонта** (type=`checkbox`, default=false).
  - `hwid_keep_global_wu_block` — **Оставить global WU driver block** (type=`checkbox`, default=false).

### Hardware > Driver Update Blocker > NVIDIA driver install restrictions > Блокировать NVIDIA driver installs

- Operation id: `nvidia_driver_block`
- Описание: Находит текущие NVIDIA PCI устройства, пишет их Hardware IDs в Device Installation Restrictions и запускает gpupdate. Полезно после установки заведомо хорошего manual/NVCleanstall драйвера.
- Риск: kind=`dangerous`, risk_level=`system_change`
- Параметры:
  - `include_compatible_ids` — **Добавить compatible IDs** (type=`checkbox`, default=false).
  - `nvidia_retroactive` — **Retroactive block** (type=`checkbox`, default=false).

### Hardware > Driver Update Blocker > NVIDIA driver install restrictions > Разблокировать NVIDIA driver installs

- Operation id: `nvidia_driver_unblock`
- Описание: Удаляет NVIDIA PCI IDs из Device Installation Restrictions, сохраняя не-NVIDIA entries в тех же policy lists.
- Риск: kind=`dangerous`, risk_level=`system_change`
- Параметры:
  - `include_compatible_ids` — **Добавить compatible IDs** (type=`checkbox`, default=false).
  - `nvidia_retroactive` — **Retroactive block** (type=`checkbox`, default=false).

### Hardware > Driver Update Blocker > Driver Store backups > Сохранить Driver Store manifest

- Operation id: `driver_store_manifest`
- Описание: Сохраняет отчёты pnputil, systeminfo и Get-WindowsDriver без экспорта driver packages.
- Риск: kind=`safe`, risk_level=`readonly`
- Параметры:
  - `driver_backup_select` — **Driver backup** (type=`select`).
  - `driver_backup_path` — **Backup folder вручную** (type=`folder`).

### Hardware > Driver Update Blocker > Driver Store backups > Экспортировать установленные драйверы

- Operation id: `driver_store_export`
- Описание: Экспортирует текущие third-party drivers из Driver Store в timestamp backup через Export-WindowsDriver или DISM fallback.
- Риск: kind=`safe`, risk_level=`project_write`
- Параметры:
  - `driver_backup_select` — **Driver backup** (type=`select`).
  - `driver_backup_path` — **Backup folder вручную** (type=`folder`).

### Hardware > Driver Update Blocker > Driver Store backups > Восстановить экспортированные драйверы

- Operation id: `driver_store_restore`
- Описание: Запускает pnputil /add-driver по выбранному backup без интерактивных prompts. Используй backups с той же машины или очень близкого железа.
- Риск: kind=`dangerous`, risk_level=`system_change`
- Параметры:
  - `driver_backup_select` — **Driver backup** (type=`select`).
  - `driver_backup_path` — **Backup folder вручную** (type=`folder`).

### Hardware > Driver Update Blocker > Driver Store backups > Открыть driver backups

- Operation id: `driver_store_open_backups`
- Описание: Открыть папку экспортированных driver backups.
- Риск: kind=`safe`, risk_level=`readonly`
- Параметры:
  - `driver_backup_select` — **Driver backup** (type=`select`).
  - `driver_backup_path` — **Backup folder вручную** (type=`folder`).

### Hardware > Driver Update Blocker > Открыть папку Driver Update Blocker

- Operation id: `driver_update_open_tool`
- Описание: Открыть проектную PowerShell-папку модуля, которую используют GUI и project launchers.
- Риск: kind=`safe`, risk_level=`readonly`
- Параметры: нет.

### Hardware > NVIDIA HDMI/DP Audio > Статус NVIDIA audio

- Operation id: `nvidia_audio_status`
- Описание: Статус без изменений: найденные NVIDIA HDMI/DP audio devices, выбранные HDAUDIO Hardware IDs и текущие DeviceInstall policy entries.
- Риск: kind=`safe`, risk_level=`readonly`
- Параметры: нет.

### Hardware > NVIDIA HDMI/DP Audio > Экспортировать NVIDIA audio IDs

- Operation id: `nvidia_audio_export_ids`
- Описание: Пишет device details и candidate IDs для policy-block в output-папку оригинальной утилиты.
- Риск: kind=`safe`, risk_level=`readonly`
- Параметры: нет.

### Hardware > NVIDIA HDMI/DP Audio > Отключить NVIDIA HDMI/DP audio

- Operation id: `nvidia_audio_disable`
- Описание: Отключает текущие matching NVIDIA HDMI/DP audio devices через Disable-PnpDevice. Обычные audio interfaces не трогает.
- Риск: kind=`dangerous`, risk_level=`system_change`
- Параметры: нет.

### Hardware > NVIDIA HDMI/DP Audio > Включить NVIDIA HDMI/DP audio

- Operation id: `nvidia_audio_enable`
- Описание: Снова включает matching NVIDIA HDMI/DP audio devices. Если policy block активен, сначала сними policy.
- Риск: kind=`dangerous`, risk_level=`system_change`
- Параметры: нет.

### Hardware > NVIDIA HDMI/DP Audio > Policy-block NVIDIA HDMI/DP audio

- Operation id: `nvidia_audio_block_policy`
- Описание: Делает backup DeviceInstall policy, добавляет только NVIDIA HDAUDIO codec IDs в DenyDeviceIDs, отключает matching devices и запускает PnP rescan.
- Риск: kind=`dangerous`, risk_level=`system_change`
- Параметры: нет.

### Hardware > NVIDIA HDMI/DP Audio > Снять policy-block NVIDIA HDMI/DP audio

- Operation id: `nvidia_audio_unblock_policy`
- Описание: Удаляет известные NVIDIA HDAUDIO IDs из DeviceInstall policy, запускает PnP rescan и пытается включить matching devices.
- Риск: kind=`dangerous`, risk_level=`system_change`
- Параметры: нет.

### Hardware > NVIDIA HDMI/DP Audio > Открыть NVIDIA audio output

- Operation id: `nvidia_audio_open_output`
- Описание: Открыть output-папку с экспортированными NVIDIA HDMI/DP audio device IDs.
- Риск: kind=`safe`, risk_level=`readonly`
- Параметры: нет.

### Hardware > NVIDIA HDMI/DP Audio > Открыть NVIDIA audio backup

- Operation id: `nvidia_audio_open_backup`
- Описание: Открыть DeviceInstall policy backups, созданные перед изменениями NVIDIA audio policy.
- Риск: kind=`safe`, risk_level=`readonly`
- Параметры: нет.

### Hardware > NVIDIA HDMI/DP Audio > Открыть папку NVIDIA audio tool

- Operation id: `nvidia_audio_open_tool`
- Описание: Открыть проектную папку NVIDIA HDMI/DP Audio module, которую используют GUI и project launchers.
- Риск: kind=`safe`, risk_level=`readonly`
- Параметры: нет.

### Hardware > Накопители / дисковые процедуры > Инвентаризация дисков

- Operation id: `storage_inventory`
- Описание: Сводка без изменений по Get-Disk/Get-Volume: номера дисков, размеры, буквы томов, файловая система и состояние.
- Риск: kind=`safe`, risk_level=`readonly`
- Параметры: нет.

### Hardware > Накопители / дисковые процедуры > Детали выбранного диска

- Operation id: `storage_disk_details`
- Описание: Layout диска без изменений и разделы для выбранного номера диска перед ручной работой со storage.
- Риск: kind=`safe`, risk_level=`readonly`
- Параметры:
  - `disk_number` — **Диск** (type=`select`).

### Hardware > Накопители / дисковые процедуры > Запустить SSD/NVMe wizard

- Operation id: `storage_ssd_reset_wizard`
- Описание: Открыть оригинальный wizard во внешней консоли; destructive-действия всё равно требуют typed confirmations внутри него.
- Риск: kind=`dangerous`, risk_level=`destructive`
- Параметры: нет.

### Hardware > Накопители / дисковые процедуры > Открыть папку SSD/NVMe

- Operation id: `storage_ssd_open_folder`
- Описание: Открыть папку SSD/NVMe wizard с README, logs и original scripts; без изменений дисков.
- Риск: kind=`safe`, risk_level=`readonly`
- Параметры: нет.

### Hardware > Накопители / дисковые процедуры > Статус WinRE layout

- Operation id: `storage_winre_status`
- Описание: Проверка без изменений: reagentc и layout системного диска, активная WinRE и соседние разделы.
- Риск: kind=`safe`, risk_level=`readonly`
- Параметры: нет.

### Hardware > Накопители / дисковые процедуры > Запустить WinRE wizard

- Operation id: `storage_winre_wizard`
- Описание: Отключает WinRE, удаляет раздел восстановления справа от C: и расширяет C: после подтверждения в проекте.
- Риск: kind=`dangerous`, risk_level=`destructive`
- Параметры:
  - `winre_typed_confirm` — **Подтверждение** (type=`text`).

### OpenSSH KeyKit > Проверить связность доступов

- Operation id: `ssh_keykit_check_links`
- Описание: Читает ssh и rclone конфигурацию и показывает каждый путь к ключу, known_hosts и прокси, которого больше нет.
- Риск: kind=`safe`, risk_level=`readonly`
- Параметры:
  - `ssh_root` — **Папка ключей** (type=`folder`, default=``).
  - `profile_name` — **Machine/profile name** (type=`text`, default=``).
  - `user_name` — **Windows user** (type=`text`, default=``).
  - `ssh_config_path` — **Файл ssh config для проверки** (type=`file`, default=``).
  - `rclone_config_path` — **Файл rclone.conf для проверки** (type=`file`, default=``).
  - `links_report_path` — **Сохранить отчёт в CSV** (type=`text`, default=``).
  - `fail_on_broken` — **Считать ошибкой отсутствующий путь** (type=`checkbox`, default=true).
  - `snapshot` — **Snapshot для import** (type=`text`, default=``).

### OpenSSH KeyKit > Экспорт client SSH keys

- Operation id: `ssh_keykit_export_client`
- Описание: Экспортировать .ssh keys/config/known_hosts/authorized_keys текущего пользователя в output\ssh_keykit.
- Риск: kind=`dangerous`, risk_level=`secret_export`
- Параметры:
  - `ssh_root` — **Папка ключей** (type=`folder`, default=``).
  - `profile_name` — **Machine/profile name** (type=`text`, default=``).
  - `user_name` — **Windows user** (type=`text`, default=``).
  - `ssh_config_path` — **Файл ssh config для проверки** (type=`file`, default=``).
  - `rclone_config_path` — **Файл rclone.conf для проверки** (type=`file`, default=``).
  - `links_report_path` — **Сохранить отчёт в CSV** (type=`text`, default=``).
  - `fail_on_broken` — **Считать ошибкой отсутствующий путь** (type=`checkbox`, default=true).
  - `snapshot` — **Snapshot для import** (type=`text`, default=``).

### OpenSSH KeyKit > Экспорт client + server SSH keys

- Operation id: `ssh_keykit_export_all`
- Описание: Экспортировать .ssh текущего пользователя плюс ProgramData\ssh host keys и sshd_config при запуске с правами администратора.
- Риск: kind=`dangerous`, risk_level=`secret_export`
- Параметры:
  - `ssh_root` — **Папка ключей** (type=`folder`, default=``).
  - `profile_name` — **Machine/profile name** (type=`text`, default=``).
  - `user_name` — **Windows user** (type=`text`, default=``).
  - `ssh_config_path` — **Файл ssh config для проверки** (type=`file`, default=``).
  - `rclone_config_path` — **Файл rclone.conf для проверки** (type=`file`, default=``).
  - `links_report_path` — **Сохранить отчёт в CSV** (type=`text`, default=``).
  - `fail_on_broken` — **Считать ошибкой отсутствующий путь** (type=`checkbox`, default=true).
  - `snapshot` — **Snapshot для import** (type=`text`, default=``).

### OpenSSH KeyKit > Импорт client SSH keys

- Operation id: `ssh_keykit_import_client`
- Описание: Отложить текущую .ssh копией .ssh.bak.timestamp, импортировать свежий/выбранный client snapshot из input и починить ACL закрытых ключей.
- Риск: kind=`dangerous`, risk_level=`user_write`
- Параметры:
  - `ssh_root` — **Папка ключей** (type=`folder`, default=``).
  - `profile_name` — **Machine/profile name** (type=`text`, default=``).
  - `user_name` — **Windows user** (type=`text`, default=``).
  - `ssh_config_path` — **Файл ssh config для проверки** (type=`file`, default=``).
  - `rclone_config_path` — **Файл rclone.conf для проверки** (type=`file`, default=``).
  - `links_report_path` — **Сохранить отчёт в CSV** (type=`text`, default=``).
  - `fail_on_broken` — **Считать ошибкой отсутствующий путь** (type=`checkbox`, default=true).
  - `snapshot` — **Snapshot для import** (type=`text`, default=``).

### OpenSSH KeyKit > Импорт client + server SSH keys

- Operation id: `ssh_keykit_import_all`
- Описание: Импортировать client keys плюс server host keys из input, починить ACL, перезапустить sshd и поставить startup type Automatic при запуске с правами администратора.
- Риск: kind=`dangerous`, risk_level=`system_change`
- Параметры:
  - `ssh_root` — **Папка ключей** (type=`folder`, default=``).
  - `profile_name` — **Machine/profile name** (type=`text`, default=``).
  - `user_name` — **Windows user** (type=`text`, default=``).
  - `ssh_config_path` — **Файл ssh config для проверки** (type=`file`, default=``).
  - `rclone_config_path` — **Файл rclone.conf для проверки** (type=`file`, default=``).
  - `links_report_path` — **Сохранить отчёт в CSV** (type=`text`, default=``).
  - `fail_on_broken` — **Считать ошибкой отсутствующий путь** (type=`checkbox`, default=true).
  - `snapshot` — **Snapshot для import** (type=`text`, default=``).

### OpenSSH KeyKit > Открыть папку скриптов KeyKit

- Operation id: `ssh_keykit_open_folder`
- Описание: Открыть tools\ssh_keykit со scripts/wrappers export/import; без изменений ключей.
- Риск: kind=`safe`, risk_level=`readonly`
- Параметры:
  - `ssh_root` — **Папка ключей** (type=`folder`, default=``).
  - `profile_name` — **Machine/profile name** (type=`text`, default=``).
  - `user_name` — **Windows user** (type=`text`, default=``).
  - `ssh_config_path` — **Файл ssh config для проверки** (type=`file`, default=``).
  - `rclone_config_path` — **Файл rclone.conf для проверки** (type=`file`, default=``).
  - `links_report_path` — **Сохранить отчёт в CSV** (type=`text`, default=``).
  - `fail_on_broken` — **Считать ошибкой отсутствующий путь** (type=`checkbox`, default=true).
  - `snapshot` — **Snapshot для import** (type=`text`, default=``).

### Бэкап AI CLI > Бэкап (экспорт)

- Operation id: `ai_backup_export`
- Описание: Атомарно экспортировать Claude и Codex в output\ai_backup, затем проверить manifest и SHA-256.
- Риск: kind=`dangerous`, risk_level=`secret_export`
- Параметры:
  - `essentials` — **Перенести самое необходимое** (type=`checkbox`, default=true).
  - `include_auth` — **Включить секреты авторизации** (type=`checkbox`, default=false).

### Бэкап AI CLI > Восстановить (импорт)

- Operation id: `ai_backup_import`
- Описание: Проверить бэкап в input, по умолчанию показать план, затем заменить только выбранные совпадающие файлы; остальные локальные файлы сохраняются.
- Риск: kind=`dangerous`, risk_level=`user_write`
- Параметры:
  - `essentials` — **Восстановить только необходимое** (type=`checkbox`, default=true).
  - `include_auth` — **Восстановить секреты авторизации** (type=`checkbox`, default=false).
  - `dry_run` — **Пробный запуск** (type=`checkbox`, default=true).
  - `allow_foreign_paths` — **Разрешить абсолютные пути другого ПК** (type=`checkbox`, default=false).
  - `allow_legacy` — **Разрешить старый бэкап без manifest** (type=`checkbox`, default=false).

### Бэкап AI CLI > Объединение памяти

- Operation id: `ai_backup_merge`
- Описание: Проверить бэкап в input и объединить .md-память Claude с текущей, по умолчанию показав план. Совпадения сохраняются, пока не включён Overwrite.
- Риск: kind=`dangerous`, risk_level=`user_write`
- Параметры:
  - `overwrite` — **Перезаписывать совпадения** (type=`checkbox`, default=false).
  - `dry_run` — **Пробный запуск** (type=`checkbox`, default=true).
  - `allow_legacy` — **Разрешить старый бэкап без manifest** (type=`checkbox`, default=false).

### Бэкап AI CLI > Открыть папку инструмента

- Operation id: `ai_backup_open`
- Описание: Открыть tools\ai_backup со скриптом и обёртками.
- Риск: kind=`safe`, risk_level=`readonly`
- Параметры: нет.

### Сертификаты (экспорт/импорт) > Статус сертификатов

- Operation id: `cert_status`
- Описание: Список выбранного store: subject, thumbprint, срок действия, закрытый ключ и exportability (помечает TPM/non-exportable).
- Риск: kind=`safe`, risk_level=`readonly`
- Параметры:
  - `cert_store` — **Хранилище сертификатов** (type=`select`, default=`CurrentUser\My`).
    - Варианты: `CurrentUser\My` — CurrentUser\My (personal); `LocalMachine\My` — LocalMachine\My (personal); `CurrentUser\Root` — CurrentUser\Root (trusted roots); `LocalMachine\Root` — LocalMachine\Root (trusted roots); `CurrentUser\CA` — CurrentUser\CA (intermediate); `LocalMachine\CA` — LocalMachine\CA (intermediate)
  - `cert_backup_dir` — **Папка сертификатов** (type=`folder`, default=``).
  - `pfx_password` — **Пароль PFX** (type=`text`, default=``).
  - `import_file` — **Файл импорта (.pfx/.cer/.crt/.sst)** (type=`file`, default=``).
  - `import_store` — **Целевое хранилище импорта** (type=`select`, default=`CurrentUser\My`).
    - Варианты: `CurrentUser\My` — CurrentUser\My (personal); `LocalMachine\My` — LocalMachine\My (personal); `CurrentUser\Root` — CurrentUser\Root (trusted roots); `LocalMachine\Root` — LocalMachine\Root (trusted roots); `CurrentUser\CA` — CurrentUser\CA (intermediate); `LocalMachine\CA` — LocalMachine\CA (intermediate)

### Сертификаты (экспорт/импорт) > Экспорт personal ключей в PFX

- Operation id: `cert_export_pfx`
- Описание: Экспорт сертификатов с экспортируемым закрытым ключом из выбранного store в password-protected .pfx в output\certificates. TPM-ключи пропускаются. Файлы СОДЕРЖАТ закрытые ключи.
- Риск: kind=`dangerous`, risk_level=`secret_export`
- Параметры:
  - `cert_store` — **Хранилище сертификатов** (type=`select`, default=`CurrentUser\My`).
    - Варианты: `CurrentUser\My` — CurrentUser\My (personal); `LocalMachine\My` — LocalMachine\My (personal); `CurrentUser\Root` — CurrentUser\Root (trusted roots); `LocalMachine\Root` — LocalMachine\Root (trusted roots); `CurrentUser\CA` — CurrentUser\CA (intermediate); `LocalMachine\CA` — LocalMachine\CA (intermediate)
  - `cert_backup_dir` — **Папка сертификатов** (type=`folder`, default=``).
  - `pfx_password` — **Пароль PFX** (type=`text`, default=``).
  - `import_file` — **Файл импорта (.pfx/.cer/.crt/.sst)** (type=`file`, default=``).
  - `import_store` — **Целевое хранилище импорта** (type=`select`, default=`CurrentUser\My`).
    - Варианты: `CurrentUser\My` — CurrentUser\My (personal); `LocalMachine\My` — LocalMachine\My (personal); `CurrentUser\Root` — CurrentUser\Root (trusted roots); `LocalMachine\Root` — LocalMachine\Root (trusted roots); `CurrentUser\CA` — CurrentUser\CA (intermediate); `LocalMachine\CA` — LocalMachine\CA (intermediate)

### Сертификаты (экспорт/импорт) > Экспорт store в SST (публично)

- Operation id: `cert_export_roots`
- Описание: Экспорт публичных сертификатов выбранного store (без закрытых ключей) в .sst с timestamp в output\certificates.
- Риск: kind=`safe`, risk_level=`project_write`
- Параметры:
  - `cert_store` — **Хранилище сертификатов** (type=`select`, default=`CurrentUser\My`).
    - Варианты: `CurrentUser\My` — CurrentUser\My (personal); `LocalMachine\My` — LocalMachine\My (personal); `CurrentUser\Root` — CurrentUser\Root (trusted roots); `LocalMachine\Root` — LocalMachine\Root (trusted roots); `CurrentUser\CA` — CurrentUser\CA (intermediate); `LocalMachine\CA` — LocalMachine\CA (intermediate)
  - `cert_backup_dir` — **Папка сертификатов** (type=`folder`, default=``).
  - `pfx_password` — **Пароль PFX** (type=`text`, default=``).
  - `import_file` — **Файл импорта (.pfx/.cer/.crt/.sst)** (type=`file`, default=``).
  - `import_store` — **Целевое хранилище импорта** (type=`select`, default=`CurrentUser\My`).
    - Варианты: `CurrentUser\My` — CurrentUser\My (personal); `LocalMachine\My` — LocalMachine\My (personal); `CurrentUser\Root` — CurrentUser\Root (trusted roots); `LocalMachine\Root` — LocalMachine\Root (trusted roots); `CurrentUser\CA` — CurrentUser\CA (intermediate); `LocalMachine\CA` — LocalMachine\CA (intermediate)

### Сертификаты (экспорт/импорт) > Импорт PFX

- Operation id: `cert_import_pfx`
- Описание: Импортировать выбранный .pfx (с паролем) в целевой store, пометив ключ exportable. Меняет хранилище сертификатов; перезагрузка не нужна. Файл и пароль - в Advanced.
- Риск: kind=`dangerous`, risk_level=`system_change`
- Параметры:
  - `cert_store` — **Хранилище сертификатов** (type=`select`, default=`CurrentUser\My`).
    - Варианты: `CurrentUser\My` — CurrentUser\My (personal); `LocalMachine\My` — LocalMachine\My (personal); `CurrentUser\Root` — CurrentUser\Root (trusted roots); `LocalMachine\Root` — LocalMachine\Root (trusted roots); `CurrentUser\CA` — CurrentUser\CA (intermediate); `LocalMachine\CA` — LocalMachine\CA (intermediate)
  - `cert_backup_dir` — **Папка сертификатов** (type=`folder`, default=``).
  - `pfx_password` — **Пароль PFX** (type=`text`, default=``).
  - `import_file` — **Файл импорта (.pfx/.cer/.crt/.sst)** (type=`file`, default=``).
  - `import_store` — **Целевое хранилище импорта** (type=`select`, default=`CurrentUser\My`).
    - Варианты: `CurrentUser\My` — CurrentUser\My (personal); `LocalMachine\My` — LocalMachine\My (personal); `CurrentUser\Root` — CurrentUser\Root (trusted roots); `LocalMachine\Root` — LocalMachine\Root (trusted roots); `CurrentUser\CA` — CurrentUser\CA (intermediate); `LocalMachine\CA` — LocalMachine\CA (intermediate)

### Сертификаты (экспорт/импорт) > Импорт всех PFX из папки

- Operation id: `cert_import_pfx_folder`
- Описание: Импортирует каждый .pfx из certificates.json в то хранилище, откуда он был выгружен, одним паролем. Меняет хранилище сертификатов.
- Риск: kind=`dangerous`, risk_level=`system_change`
- Параметры:
  - `cert_store` — **Хранилище сертификатов** (type=`select`, default=`CurrentUser\My`).
    - Варианты: `CurrentUser\My` — CurrentUser\My (personal); `LocalMachine\My` — LocalMachine\My (personal); `CurrentUser\Root` — CurrentUser\Root (trusted roots); `LocalMachine\Root` — LocalMachine\Root (trusted roots); `CurrentUser\CA` — CurrentUser\CA (intermediate); `LocalMachine\CA` — LocalMachine\CA (intermediate)
  - `cert_backup_dir` — **Папка сертификатов** (type=`folder`, default=``).
  - `pfx_password` — **Пароль PFX** (type=`text`, default=``).
  - `import_file` — **Файл импорта (.pfx/.cer/.crt/.sst)** (type=`file`, default=``).
  - `import_store` — **Целевое хранилище импорта** (type=`select`, default=`CurrentUser\My`).
    - Варианты: `CurrentUser\My` — CurrentUser\My (personal); `LocalMachine\My` — LocalMachine\My (personal); `CurrentUser\Root` — CurrentUser\Root (trusted roots); `LocalMachine\Root` — LocalMachine\Root (trusted roots); `CurrentUser\CA` — CurrentUser\CA (intermediate); `LocalMachine\CA` — LocalMachine\CA (intermediate)

### Сертификаты (экспорт/импорт) > Импорт сертификата / CA

- Operation id: `cert_import_cert`
- Описание: Импортировать публичный .cer/.crt/.sst в целевой store (например, доверие корпоративному root CA). Меняет доверие; выбирайте store аккуратно. Файл - в Advanced.
- Риск: kind=`dangerous`, risk_level=`system_change`
- Параметры:
  - `cert_store` — **Хранилище сертификатов** (type=`select`, default=`CurrentUser\My`).
    - Варианты: `CurrentUser\My` — CurrentUser\My (personal); `LocalMachine\My` — LocalMachine\My (personal); `CurrentUser\Root` — CurrentUser\Root (trusted roots); `LocalMachine\Root` — LocalMachine\Root (trusted roots); `CurrentUser\CA` — CurrentUser\CA (intermediate); `LocalMachine\CA` — LocalMachine\CA (intermediate)
  - `cert_backup_dir` — **Папка сертификатов** (type=`folder`, default=``).
  - `pfx_password` — **Пароль PFX** (type=`text`, default=``).
  - `import_file` — **Файл импорта (.pfx/.cer/.crt/.sst)** (type=`file`, default=``).
  - `import_store` — **Целевое хранилище импорта** (type=`select`, default=`CurrentUser\My`).
    - Варианты: `CurrentUser\My` — CurrentUser\My (personal); `LocalMachine\My` — LocalMachine\My (personal); `CurrentUser\Root` — CurrentUser\Root (trusted roots); `LocalMachine\Root` — LocalMachine\Root (trusted roots); `CurrentUser\CA` — CurrentUser\CA (intermediate); `LocalMachine\CA` — LocalMachine\CA (intermediate)

### Сертификаты (экспорт/импорт) > Открыть папку экспорта сертификатов

- Operation id: `cert_open_folder`
- Описание: Открыть output\certificates; без изменений сертификатов.
- Риск: kind=`safe`, risk_level=`readonly`
- Параметры:
  - `cert_store` — **Хранилище сертификатов** (type=`select`, default=`CurrentUser\My`).
    - Варианты: `CurrentUser\My` — CurrentUser\My (personal); `LocalMachine\My` — LocalMachine\My (personal); `CurrentUser\Root` — CurrentUser\Root (trusted roots); `LocalMachine\Root` — LocalMachine\Root (trusted roots); `CurrentUser\CA` — CurrentUser\CA (intermediate); `LocalMachine\CA` — LocalMachine\CA (intermediate)
  - `cert_backup_dir` — **Папка сертификатов** (type=`folder`, default=``).
  - `pfx_password` — **Пароль PFX** (type=`text`, default=``).
  - `import_file` — **Файл импорта (.pfx/.cer/.crt/.sst)** (type=`file`, default=``).
  - `import_store` — **Целевое хранилище импорта** (type=`select`, default=`CurrentUser\My`).
    - Варианты: `CurrentUser\My` — CurrentUser\My (personal); `LocalMachine\My` — LocalMachine\My (personal); `CurrentUser\Root` — CurrentUser\Root (trusted roots); `LocalMachine\Root` — LocalMachine\Root (trusted roots); `CurrentUser\CA` — CurrentUser\CA (intermediate); `LocalMachine\CA` — LocalMachine\CA (intermediate)

### Шрифты пользователя > Показать мои шрифты

- Operation id: `fonts_status`
- Описание: Перечисляет шрифты, установленные для этого пользователя, с пометкой [ OK ] или [MISS], и считает системные. Ничего не меняет.
- Риск: kind=`safe`, risk_level=`readonly`
- Параметры:
  - `fonts_folder` — **Папка шрифтов** (type=`folder`, default=``).
  - `include_system` — **Показывать и системные шрифты** (type=`checkbox`, default=false).

### Шрифты пользователя > Экспорт моих шрифтов

- Operation id: `fonts_export`
- Описание: Копирует файлы пользовательских шрифтов в output\fonts вместе с картой их зарегистрированных имён. Системные не копируются.
- Риск: kind=`safe`, risk_level=`project_write`
- Параметры:
  - `fonts_folder` — **Папка шрифтов** (type=`folder`, default=``).
  - `include_system` — **Показывать и системные шрифты** (type=`checkbox`, default=false).

### Шрифты пользователя > Импорт шрифтов

- Operation id: `fonts_import`
- Описание: Ставит собранные шрифты только для этого пользователя: файл в профиль, имя в HKCU, запущенным программам сообщается. Прав администратора не нужно, C:\Windows\Fonts не затрагивается.
- Риск: kind=`dangerous`, risk_level=`user_write`
- Параметры:
  - `fonts_folder` — **Папка шрифтов** (type=`folder`, default=``).
  - `include_system` — **Показывать и системные шрифты** (type=`checkbox`, default=false).

### Шрифты пользователя > Открыть папку шрифтов

- Operation id: `fonts_open_folder`
- Описание: Открыть output\fonts; ничего не собирает.
- Риск: kind=`safe`, risk_level=`readonly`
- Параметры:
  - `fonts_folder` — **Папка шрифтов** (type=`folder`, default=``).
  - `include_system` — **Показывать и системные шрифты** (type=`checkbox`, default=false).

### Среда оболочки > Показать файлы оболочки

- Operation id: `shell_status`
- Описание: Перечисляет настройки Windows Terminal и профили PowerShell, которые есть на этой машине, с пометкой [ OK ] или [ -- ]. Ничего не меняет.
- Риск: kind=`safe`, risk_level=`readonly`
- Параметры:
  - `shell_folder` — **Папка среды оболочки** (type=`folder`, default=``).

### Среда оболочки > Экспорт файлов оболочки

- Operation id: `shell_export`
- Описание: Копирует найденные настройки и профили в output\shell вместе с картой, что есть что.
- Риск: kind=`safe`, risk_level=`project_write`
- Параметры:
  - `shell_folder` — **Папка среды оболочки** (type=`folder`, default=``).

### Среда оболочки > Импорт файлов оболочки

- Operation id: `shell_import`
- Описание: Кладёт каждый собранный файл туда, где его место на этой машине, сохраняя копию с датой у заменяемого. Совпадающий файл не трогает.
- Риск: kind=`dangerous`, risk_level=`user_write`
- Параметры:
  - `shell_folder` — **Папка среды оболочки** (type=`folder`, default=``).

### Среда оболочки > Открыть папку среды оболочки

- Operation id: `shell_open_folder`
- Описание: Открыть output\shell; ничего не собирает.
- Риск: kind=`safe`, risk_level=`readonly`
- Параметры:
  - `shell_folder` — **Папка среды оболочки** (type=`folder`, default=``).

### Доступы из конфигурации > Показать, что названо в конфигурации

- Operation id: `access_status`
- Описание: Перечисляет каждый ключ, known_hosts, сертификат и путь к прокси из конфигурации ssh и rclone с пометкой [ OK ] или [MISS]. Ничего не меняет.
- Риск: kind=`safe`, risk_level=`readonly`
- Параметры:
  - `access_folder` — **Папка доступов** (type=`folder`, default=``).
  - `access_key_root` — **Куда лягут ключи здесь** (type=`folder`, default=``).
  - `ssh_config_path` — **Файл ssh config** (type=`file`, default=``).
  - `rclone_config_path` — **Файл rclone.conf** (type=`file`, default=``).

### Доступы из конфигурации > Экспорт файлов доступов

- Operation id: `access_export`
- Описание: Копирует ssh config, rclone.conf и каждый названный ими файл в output\access вместе с картой происхождения. Содержит ЗАКРЫТЫЕ КЛЮЧИ.
- Риск: kind=`dangerous`, risk_level=`secret_export`
- Параметры:
  - `access_folder` — **Папка доступов** (type=`folder`, default=``).
  - `access_key_root` — **Куда лягут ключи здесь** (type=`folder`, default=``).
  - `ssh_config_path` — **Файл ssh config** (type=`file`, default=``).
  - `rclone_config_path` — **Файл rclone.conf** (type=`file`, default=``).

### Доступы из конфигурации > Импорт файлов доступов

- Operation id: `access_import`
- Описание: Кладёт привезённые файлы в выбранную папку, переписывает под них конфигурацию ssh и rclone, ограничивает права на ключи и проверяет связность. Заменяет оба файла конфигурации, сохраняя копию с датой.
- Риск: kind=`dangerous`, risk_level=`user_write`
- Параметры:
  - `access_folder` — **Папка доступов** (type=`folder`, default=``).
  - `access_key_root` — **Куда лягут ключи здесь** (type=`folder`, default=``).
  - `ssh_config_path` — **Файл ssh config** (type=`file`, default=``).
  - `rclone_config_path` — **Файл rclone.conf** (type=`file`, default=``).

### Переезд на новую машину > Показать состав переезда

- Operation id: `migration_plan`
- Описание: Читает config\migration_plan.yaml и перечисляет строки состава: пак, папку и можно ли развернуть без рук. Ничего не меняет.
- Риск: kind=`safe`, risk_level=`readonly`
- Параметры:
  - `migration_folder` — **Папка переезда** (type=`folder`, default=``).
  - `profile_name` — **Имя машины в названии папки** (type=`text`, default=``).
  - `user_name` — **Пользователь Windows** (type=`text`, default=``).
  - `pfx_password` — **Пароль PFX** (type=`text`, default=``).

### Переезд на новую машину > Проверить доступы после переезда

- Operation id: `migration_verify`
- Описание: Тот же разбор путей, что и в паке SSH: каждый ключ, known_hosts и прокси, названные в конфигурации ssh и rclone.
- Риск: kind=`safe`, risk_level=`readonly`
- Параметры:
  - `migration_folder` — **Папка переезда** (type=`folder`, default=``).
  - `profile_name` — **Имя машины в названии папки** (type=`text`, default=``).
  - `user_name` — **Пользователь Windows** (type=`text`, default=``).
  - `pfx_password` — **Пароль PFX** (type=`text`, default=``).

### Переезд на новую машину > Экспорт переезда

- Operation id: `migration_export`
- Описание: Идёт по составу, зовёт паки и собирает всё в output\migration\<машина>_<время> вместе с описью. Содержит ЗАКРЫТЫЕ КЛЮЧИ и пароли Wi-Fi открытым текстом.
- Риск: kind=`dangerous`, risk_level=`secret_export`
- Параметры:
  - `migration_folder` — **Папка переезда** (type=`folder`, default=``).
  - `profile_name` — **Имя машины в названии папки** (type=`text`, default=``).
  - `user_name` — **Пользователь Windows** (type=`text`, default=``).
  - `pfx_password` — **Пароль PFX** (type=`text`, default=``).

### Переезд на новую машину > Импорт переезда

- Operation id: `migration_import`
- Описание: Читает опись из input, отдаёт каждую строку своему паку и заканчивает проверкой доступов. Заменяет SSH-материал этого пользователя и добавляет профили Wi-Fi.
- Риск: kind=`dangerous`, risk_level=`system_change`
- Параметры:
  - `migration_folder` — **Папка переезда** (type=`folder`, default=``).
  - `profile_name` — **Имя машины в названии папки** (type=`text`, default=``).
  - `user_name` — **Пользователь Windows** (type=`text`, default=``).
  - `pfx_password` — **Пароль PFX** (type=`text`, default=``).

### Переезд на новую машину > Открыть папку переезда

- Operation id: `migration_open_folder`
- Описание: Открыть output\migration; ничего не собирает.
- Риск: kind=`safe`, risk_level=`readonly`
- Параметры:
  - `migration_folder` — **Папка переезда** (type=`folder`, default=``).
  - `profile_name` — **Имя машины в названии папки** (type=`text`, default=``).
  - `user_name` — **Пользователь Windows** (type=`text`, default=``).
  - `pfx_password` — **Пароль PFX** (type=`text`, default=``).

### Утилиты > Документация PDF > Показать план PDF export

- Operation id: `docs_pdf_plan`
- Описание: Dry run: показать Markdown-источники и целевые PDF без записи файлов.
- Риск: kind=`safe`, risk_level=`readonly`
- Параметры:
  - `docs_pdf_theme` — **Тема** (type=`select`, default=`both`).
    - Варианты: `both` — Обе: dark + light-sand; `dark` — Dark; `light-sand` — Light Sand
  - `docs_pdf_include_agent_instructions` — **Включить agent instructions** (type=`checkbox`, default=true).

### Утилиты > Документация PDF > Сгенерировать PDF документации

- Operation id: `docs_pdf_render`
- Описание: Сгенерировать PDF для root guides, docs\*.md, GitHub README и optional agent instructions в docs\PDF. Markdown остаётся source of truth.
- Риск: kind=`safe`, risk_level=`project_write`
- Параметры:
  - `docs_pdf_theme` — **Тема** (type=`select`, default=`both`).
    - Варианты: `both` — Обе: dark + light-sand; `dark` — Dark; `light-sand` — Light Sand
  - `docs_pdf_include_agent_instructions` — **Включить agent instructions** (type=`checkbox`, default=true).

### Утилиты > Документация PDF > Открыть папку docs PDF

- Operation id: `docs_pdf_open`
- Описание: Открыть docs\PDF.
- Риск: kind=`safe`, risk_level=`readonly`
- Параметры:
  - `docs_pdf_theme` — **Тема** (type=`select`, default=`both`).
    - Варианты: `both` — Обе: dark + light-sand; `dark` — Dark; `light-sand` — Light Sand
  - `docs_pdf_include_agent_instructions` — **Включить agent instructions** (type=`checkbox`, default=true).

### Утилиты > Версия ripgrep

- Operation id: `ripgrep_status`
- Описание: Показать версию проектного ripgrep\rg.exe.
- Риск: kind=`safe`, risk_level=`readonly`
- Параметры: нет.

### Утилиты > Открыть папку утилиты

- Operation id: `open_tool_folder`
- Описание: Открыть project-local utility folder.
- Риск: kind=`safe`, risk_level=`readonly`
- Параметры:
  - `folder` — **Папка** (type=`select`).
    - Варианты: `ripgrep` — ripgrep; `tools/network_cleaner` — tools/network_cleaner; `WSL` — WSL; `tools/codex_nuke` — tools/codex_nuke; `tools/python_nuke` — tools/python_nuke; `tools/driver_firmware_audit` — tools/driver_firmware_audit; `tools/ssh_keykit` — tools/ssh_keykit; `tools/ubuntu_dev_installer` — tools/ubuntu_dev_installer; `tools/ssd_nvme_reset_wizard` — tools/ssd_nvme_reset_wizard; `tools/winre_extend` — tools/winre_extend; `tools/bitrix_hosts_toggle_pack` — tools/bitrix_hosts_toggle_pack; `tools/disable_windows_proxy` — tools/disable_windows_proxy; `tools/wires_wireless` — tools/wires_wireless; `tools/wsl` — tools/wsl

### Обслуживание и очистка > Очистка Codex > Аудит Codex

- Operation id: `codex_nuke_audit`
- Описание: Проверить артефакты Codex Desktop без изменений.
- Риск: kind=`safe`, risk_level=`readonly`
- Параметры: нет.

### Обслуживание и очистка > Очистка Codex > Симуляция очистки Codex

- Operation id: `codex_nuke_dryrun`
- Описание: Показать план очистки Codex без изменений системы.
- Риск: kind=`safe`, risk_level=`readonly`
- Параметры: нет.

### Обслуживание и очистка > Очистка Codex > Сброс сессии Codex

- Operation id: `codex_nuke_session_reset`
- Описание: Мягкий reset: остановить Codex и очистить sessions/cache, сохранив auth, config и install.
- Риск: kind=`dangerous`, risk_level=`user_write`
- Параметры: нет.

### Обслуживание и очистка > Очистка Codex > Полная очистка Codex, сохранить CLI state

- Operation id: `codex_nuke_keep_cli_state`
- Описание: Удалить артефакты Codex Desktop, сохранив ~/.codex для Codex CLI state. Сначала используй аудит/dry-run и проверь scope очистки.
- Риск: kind=`dangerous`, risk_level=`destructive`
- Параметры: нет.

### Обслуживание и очистка > Очистка Codex > Полная очистка Codex

- Operation id: `codex_nuke_full`
- Описание: Полное удаление Codex Desktop, включая общий пользовательский state Codex.
- Риск: kind=`dangerous`, risk_level=`destructive`
- Параметры: нет.

### Обслуживание и очистка > Очистка Python > Аудит Python

- Operation id: `python_nuke_audit`
- Описание: Проверить Python installs, launchers, caches, переменные среды и PATH entries без изменений.
- Риск: kind=`safe`, risk_level=`readonly`
- Параметры: нет.

### Обслуживание и очистка > Очистка Python > Симуляция очистки Python

- Operation id: `python_nuke_dryrun`
- Описание: Показать план очистки Python без изменений системы.
- Риск: kind=`safe`, risk_level=`readonly`
- Параметры: нет.

### Обслуживание и очистка > Очистка Python > Полная очистка Python

- Operation id: `python_nuke_full`
- Описание: Удалить распространённые Python installs, launchers, pip cache, переменные среды и PATH entries. Сначала используй аудит/dry-run и проверь, какие installs попали в scope.
- Риск: kind=`dangerous`, risk_level=`destructive`
- Параметры: нет.

### Обслуживание и очистка > Очистка Python > Очистка Python без winget uninstall

- Operation id: `python_nuke_keep_winget`
- Описание: Запустить очистку Python, но пропустить winget uninstall pass. Всё равно чистит launchers/cache/env/PATH в выбранном scope; сначала используй аудит/dry-run.
- Риск: kind=`dangerous`, risk_level=`destructive`
- Параметры: нет.

### Обслуживание и очистка > Очистить workspace

- Operation id: `cleanup_workspace`
- Описание: Удалить только файлы внутри управляемой папки workspace.
- Риск: kind=`dangerous`, risk_level=`destructive`
- Параметры: нет.

### Обслуживание > Очистить I/O

- Operation id: `cleanup_input_output`
- Описание: Удалить содержимое управляемых папок input и output.
- Риск: kind=`dangerous`, risk_level=`destructive`
- Параметры: нет.

<!-- END GENERATED PARAMETER REFERENCE -->

## CLI Операции

Показать статус WSL:

```cmd
runtime\python.exe system_core\cli_operation.py wsl_status
```

Запустить dangerous operation:

```cmd
runtime\python.exe system_core\cli_operation.py storage_winre_wizard --yes-i-understand
```

Передаваемые параметры:

```cmd
runtime\python.exe system_core\cli_operation.py wsl_install_distro --yes-i-understand --param install_distro=Ubuntu-26.04 --param install_location_mode=custom --param install_location=S:\WSL\VHDX\Ubuntu-26.04 --param no_launch=true
```

## Проверка Проекта

Минимальная проверка после изменений:

```cmd
runtime\python.exe -m py_compile system_core\ui_nicegui\app.py system_core\services\devops_tools.py system_core\core\jobs.py
runtime\python.exe system_core\ui_nicegui\app.py --smoke
runtime\python.exe system_core\doctor.py
```

GUI server вручную:

```cmd
runtime\python.exe system_core\ui_nicegui\app.py --host 127.0.0.1 --port 8092 --no-browser
```

## Что Читать Дальше

- `README_AUDION_DEVOPS_TOOLS_RU.md` - краткий README проекта.
- `docs\AUDION_DEVOPS_TOOLS_RU.md` - архитектура и правила развития.
- `docs\BITRIX_HOSTS_RU.md` - Bitrix hosts workflow.
- `docs\NETWORK_CONNECTIVITY_RU.md` - Network Cleaner, Wi-Fi profiles, SMB login, adapters и proxy.
- `docs\BROWSER_BOOKMARKS_MASTER_RU.md` - Chromium Bookmarks/Favicons master export/import.
- `docs\WSL_TOOLKIT_RU.md` - WSL install/import/backup/restore/move/delete.
- `docs\VIRTUALIZATION_SWITCHER_RU.md` - virtualization modes, Hyper-V/WSL2 и VM diagnostics.
- `docs\DEFAULT_APPS_GUARD_RU.md` - default apps ritual и gotchas.
- `docs\ASSOCIATION_DEFENSE_RU.md` - встроенные приложения Microsoft, блокировка переустановки AppLocker, снимки ассоциаций и ограничение PowerShell 5.1/7.
- `docs\HARDWARE_DRIVER_GUARD_RU.md` - driver/NVIDIA/storage details.
- `docs\STORAGE_DISK_PROCEDURES_RU.md` - WinRE, SSD/NVMe и disk inventory.
- `docs\OPENSSH_KEYKIT_RU.md` - SSH client/server key backup и restore.
- `docs\CERTIFICATE_KEYKIT_RU.md` - certificate/PFX backup и restore.
- `docs\MAINTENANCE_CLEANUP_RU.md` - Codex/Python nuke и workspace cleanup.
- `docs\MANIFEST_REFERENCE_RU.md` - правила manifest/service слоя GUI.
- `docs\SMOKE_TEST_CHECKLIST_RU.md` - smoke checklist.
- `docs\KNOWN_PITFALLS_RU.md` - типовые ловушки.
## Канонические названия Workbench

Workbench использует единый публичный словарь Audion Image Tools во всех проектах. Кнопки всегда расположены и называются одинаково: **Источник**, **Добавить файл...**, **Назначение**, **Сбросить**, **Удалить**, **Список**.

`Сбросить` возвращает проектные `input/output` и не удаляет файлы; `Удалить` очищает текущие `Источник` и `Назначение` только после подтверждения. В английском интерфейсе точные названия: **Source**, **Add file...**, **Target**, **Reset**, **Delete**, **List**. Варианты `Цель`, `Очистить`, `Destination` и `Clear` для этих элементов Workbench не используются.
