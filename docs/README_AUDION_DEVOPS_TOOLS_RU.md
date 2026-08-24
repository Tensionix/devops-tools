# Audion DevOps Tools

Portable GUI-shell для набора Audion micro/macro utilities.

GUI не заменяет существующие CMD/FZF/PowerShell-слои. Он добавляет управляемую оболочку: поля, списки, чекбоксы, picker-кнопки, подтверждения, терминальный журнал и быстрый ручной запуск команд.

Финальный UI-слой работает как приборная панель: короткие English-heavy кнопки, компактное видимое описание, логические рамки для пар `backup / restore`, `export / import`, `block / unblock`, мягкие тона кнопок для щадящих/обычных/сильных действий и полный Windows-контекст в tooltip. Опасные подтверждения показывают полный текст, чтобы перед запуском не терялись последствия.

## Позиционирование

Audion DevOps Tools не пытается быть клоном Chris Titus WinUtil, generic Windows tuner или debloater. Цель проекта - закрыть недостающий тонкий программно-аппаратный слой: WSL lifecycle, host virtualization modes, driver policy, WinRE/storage procedures, network state, default-app policy, hosts overrides, certificates and SSH keys.

Это не набор твиков ради твиков. Это рабочая кабина истребителя для людей, которые понимают последствия системных операций и хотят видеть кнопки, параметры, подтверждения, backup и terminal log в одном контролируемом контуре.

## Запуск

```cmd
launcher_gui.cmd
```

GUI использует portable Python runtime из папки проекта. Если нужно временно указать другой Python:

```cmd
set AUDION_GUI_PYTHON=C:\Path\To\python.exe
launcher_gui.cmd
```

Обычный запуск теперь запрашивает UAC и поднимает весь GUI от имени администратора. Это удобнее для DevOps-сценариев с DISM, hosts, сетевыми адаптерами, diskpart/WinRE и WSL setup.

Для read-only отладки без UAC:

```cmd
set AUDION_GUI_NO_ELEVATE=1
launcher_gui.cmd
```

Локальный сервер по умолчанию:

```text
http://127.0.0.1:8092/
```

Есть и короткие модульные CMD-входы для аварийной/ручной работы без открытия всего GUI:

```cmd
launcher_project_ru.cmd
cli\launcher_wsl.cmd
cli\launcher_bitrix.cmd
cli\launcher_default_apps.cmd
cli\launcher_association_defense.cmd
cli\launcher_hardware.cmd
cli\launcher_docs_pdf.cmd
cli\launcher_codex_nuke.cmd
cli\launcher_python_nuke.cmd
```

`cli\launcher_wsl.cmd`, `cli\launcher_bitrix.cmd`, `cli\launcher_default_apps.cmd` и `cli\launcher_association_defense.cmd` вызывают тот же manifest/service layer через `system_core\cli_operation.py`, поэтому не дублируют логику GUI. `cli\launcher_docs_pdf.cmd` вызывает `system_core\docs_pdf.py`: dry-run строит автономный план, а реальный рендер использует внешний Markdown PDF engine из `--engine`, `AUDION_MARKDOWN_PDF_ENGINE` или автоматически найденного соседнего проекта. `cli\launcher_codex_nuke.cmd` и `cli\launcher_python_nuke.cmd` являются корневыми wrapper-входами в встроенные `tools\...\Nuke.cmd`, где сохраняются UAC elevation и typed confirmations. Прямой CLI-запуск `kind: dangerous` требует `--yes-i-understand`.

## Обслуживание Папок

Создать недостающие рабочие папки после переноса/распаковки:

```cmd
init_folders.cmd
```

Деликатная очистка проекта:

```cmd
cleanup_project.cmd
```

Cleaner оставляет скрипты, конфиги, документацию, tracked license docs и сами папки. Он удаляет всё сгенерированное, скачанное или появившееся в управляемых зонах проекта: `runtime`, `wheelhouse`, `release`, `ripgrep`, `install\download`, `system_core\powershell`, `system_core\fzf.exe`, `input`, `output`, `logs`, `report`, `workspace`, `data` и Python-кэши.

`backup` - ключевая project-local папка и отдельный путь `ProjectPaths.backup`. Там лежат rollback/safety snapshots для Network, Default Apps, Driver Guard, Browser Bookmarks, NVIDIA Audio, сертификатов, SSH, virtualization и hosts-операций. Это generated state: обычный cleaner очищает содержимое `backup` вместе с другими рабочими зонами, затем восстанавливает структуру и `.gitkeep`.

Очистка охватывает **каждую** папку резервов, а не только корневую: свои держат паки под `tools\` - `network_cleaner`, `disable_windows_proxy`, `bitrix_hosts_toggle_pack` и оба блока `wsl`. В их снимках состояние конкретной машины - MAC- и IP-адреса, DNS-серверы, имена сетей Wi-Fi, экспорт брандмауэра и реестра, - и в релиз этому попадать нельзя. Папки находятся по имени, а не перечисляются, поэтому новый пак со своими резервами попадает под очистку сам. Переживают её два вида файлов: `.gitkeep` / `.keep` и файл `tools\bitrix_hosts_toggle_pack\backup\hosts` - заводской эталон, из которого этот пак восстанавливает; он не в git, и заново его никто не создаст.

Для очистки только backup без остальных зон остаётся отдельный режим:

```cmd
cleanup_project.cmd /BACKUP
```

Перед реальным backup-only удалением этот режим всегда спрашивает `Y/N/Q`; для проверки его узкого плана используйте `cleanup_project.cmd /BACKUP /DRYRUN`.

Проверить план без удаления:

```cmd
cleanup_project.cmd /DRYRUN /Y
```

`/Y` только пропускает вопрос подтверждения. При отдельном запуске cleaner всё равно ждёт клавишу на финальном экране; закрытие без паузы включается только явным `/NOPAUSE` для launcher/automation-сценариев.

В `builder_main.cmd` оставлены install/diagnostic операции: `Init folders`, `[70] CLEAN INSTALL CACHE`, doctor/smoke и release checks. `cleanup_project.cmd` не является пунктом builder-меню: это отдельная destructive source-cleanup процедура для явного ручного запуска. Для install cache используйте `install\Clean-Install-Cache.cmd`, а не `cleanup_project.cmd`.

Портативная сборка окружения:

```cmd
install\Build_Portable_Env.cmd
```

Build-скрипты пересобирают runtime/wheelhouse, ставят пакеты из локального wheelhouse и в финале запускают `system_core\doctor.py` плюс NiceGUI smoke. Перед перезаписью generated install-зон они показывают `Y/N/Q`; `backup` не входит в зону пересборки. Для автоматического rebuild есть явный `/Y`.

## Portable PowerShell

PowerShell ищется в таком порядке:

1. `system_core\powershell\pwsh.exe`
2. `pwsh.exe` из `PATH`
3. `powershell.exe`

Установка portable PowerShell доступна из GUI:

```text
Runtime and shell -> Install portable PowerShell
```

или вручную:

```cmd
install\Install-Portable-PowerShell.cmd /NOPAUSE
```

## Разделы GUI

Экранные описания в разделах намеренно короткие: они помогают за пару секунд понять, нажимать команду или нет. Подробности, Windows-термины, риски и откат раскрываются в tooltip по кнопке или описанию. Рамки группируют пары и pipeline-сценарии, а цвет кнопки только мягко показывает силу действия; он не заменяет `kind`, `risk_level`, confirmation и terminal log.

- `Runtime and shell` - preflight, проверка/установка PowerShell runtime и Windows DEV-настройки.
- `Browser Bookmarks Master` - Chromium-закладки и favicon-cache: status, очистка cache, export/import эталона через Workbench SOURCE/TARGET с версионированными папками backup.
- `Network Cleaner` - диагностика, backup/restore, proxy и repair profiles.
- `Подключение и адаптеры` - управление адаптерами, Wi-Fi profiles, SMB-вход к Windows file sharing, быстрые LAN/Wi-Fi modes и sticky-pair.
- `WSL Toolkit` - единый WSL-модуль: WSL2 features/update, online distro install, установка из `.wsl`/tar/vhd, list/status/shutdown, backup/clone/move/delete, import/restore, register all VHDX.
- `Виртуализация` - read-only status/optimization diagnostics, режимы Hyper-V/WSL2, быстрые сторонние VM, WHP coexist, Hyper-V/Sandbox enable/disable с BCD backup и reboot warning.
- `Hosts and Bitrix` - detect current local on-prem endpoint, status/enable/disable/restore hosts override, DNS, auto-scanned/custom TCP-port diagnostics, managed hosts metadata and bitwise depatch from backup.
- `Default Apps Guard` - snapshot/rescan Windows default associations, HKLM policy guard и comparison current/profile/policy без сторонних прослоек.
- `Association Defense` - компактный защитный слой вокруг Windows/Edge association hijacking: встроенные приложения Microsoft с чекбоксами, policy guards, снимки ассоциаций (общий и по группам) и отслеживание смены.
- `Hardware` - Driver Update Blocker, NVIDIA driver install restrictions, Driver Store backup/restore, NVIDIA HDMI/DP Audio control и дисковые процедуры: disk inventory, WinRE, SSD/NVMe Reset Wizard v4.
- `Utilities` - OpenSSH KeyKit, Certificate KeyKit, Documentation PDF export, Ubuntu Dev Installer materials, проектный `ripgrep\rg.exe` и быстрый доступ к папкам набора.
- `Обслуживание и очистка` - встроенные инструменты очистки Codex/Python и managed workspace cleanup.

### Windows DEV Long Paths

В `Runtime and shell -> Windows DEV settings` есть три команды:

- `Check Windows Long Paths` - показывает `Windows LongPathsEnabled`, `Git global core.longpaths` и `Git system core.longpaths`.
- `Enable Windows Long Paths` - ставит `HKLM\SYSTEM\CurrentControlSet\Control\FileSystem\LongPathsEnabled=1` через admin/UAC.
- `Enable Git Long Paths` - ставит `git config --global core.longpaths true` для текущего пользователя.

Нюанс важный: это не полностью отключает `MAX_PATH` для всей Windows. Нужны системная настройка `LongPathsEnabled=1` и поддержка `longPathAware` со стороны конкретного Win32-приложения. Для DEV это полезно, особенно с `node_modules`, virtualenv, vendored SDK и глубокими workspace-папками, но проекты всё равно лучше держать в коротких путях вроде `S:\Code\Project`, `E:\Dev\Project`, `C:\Dev\Project`.

### Browser Bookmarks Master За 45 Секунд

Если Chromium-синхронизация сломала иконки или нужно перенести эталон закладок без облачного merge:

1. Выбери Workbench `TARGET` для export или `SOURCE` для import.
2. Вверху выбери действие: `Status`, `Import`, `Export` или `Transfer`.
3. Для `Status` и `Export` браузеры выбираются чекбоксами, можно несколько сразу.
4. Для `Import` в системном режиме браузеры выбираются чекбоксами; portable-режим принимает один точный профиль.
5. Для `Transfer` источник выбирается radio-кнопкой, приёмники чекбоксами; совпадающий источник скрыт из приёмников.
6. Запусти `Export master to Workbench TARGET`, `Import master from Workbench SOURCE` или `Transfer master between browsers`.

Переключатели сверху сделаны широкими кнопками с отчётливым активным состоянием; цвет служит навигации и не заменяет подтверждение риска.

Если выбранный браузер не имеет живого профиля, он логируется как `SKIP`, GUI показывает жёлтый toast и продолжает работу с остальными выбранными браузерами.

Перед import и transfer локальный `Favicons`/`Favicons-journal` у приёмников очищается автоматически; это не отдельный режим, а постоянный служебный шаг.

Для сетевого backup внутри окна есть UNC-конструктор `\\SERVER\Share\Folder`: поля `сервер/компьютер`, `Share`, необязательная `папка внутри Share` сохраняют текущий Workbench `SOURCE` или `TARGET`.

Версионирование применяется к папкам backup: `YYYY-MM-DD_HH-MM-SS_<backup_label>_vNN`. Сами файлы внутри остаются браузерными и совместимыми: `Bookmarks`, `Favicons`, `Favicons-journal`.

### Bitrix Hosts За 30 Секунд

Текущий default для on-prem Bitrix: `portal.itpgrad.ru -> 192.168.0.130`, port `443`, URL `https://192.168.0.130`.

Ритуал:

1. `Hosts and Bitrix -> Detect current endpoint`.
2. Проверить, что подставился local/private IP и порт.
3. `Status / DNS / ports`.
4. `Enable override`.
5. После работы: `Disable override`.

`Disable override` делает не "удаление строки", а побитовый depatch: берёт `backup=hosts_prepatch_....bak` из managed-комментария и копирует этот backup поверх системного `hosts`. Подробно: `docs\BITRIX_HOSTS_RU.md`.

## Официальный Admin-Слой

Системные операции в проекте намеренно строятся вокруг документированных Windows admin/deployment механизмов, а не вокруг случайной правки реестра.

- `Default Apps Guard` использует DISM XML export/import/list/remove и HKLM policy `DefaultAssociationsConfiguration`.
- `AppAssociations.xml` применяется Windows policy при входе пользователя. Без `Suggested="true"` association применяется при каждом sign-in; с `Suggested="true"` - мягко/однократно для текущей версии policy.
- Windows 11 Home/Core не является гарантированным target для этой policy: Microsoft документирует `DefaultAssociationsConfiguration` для Pro/Enterprise/Education/IoT Enterprise. На Home/Core GUI показывает edition в status и по умолчанию блокирует apply, чтобы не обещать ложную защиту.
- `UserChoice` и его защищённые hash-значения не редактируются вручную. Правильный путь: snapshot/rescan/import XML, затем apply/repair policy, затем sign out/sign in или reboot.
- Снимки ассоциаций текущего пользователя только читают `UserChoice\ProgId` из реестра и живут в `Association Defense`. Сторонних утилит, пишущих защищённый hash, в проекте нет; вернуть программы на место можно через policy-слой.
- WSL-операции идут через официальный `wsl.exe`: install/list/update/export/import/import-in-place/unregister/location.
- Wi-Fi profile export/import/connect/status идут через официальный `netsh wlan`.
- SMB-вход в `Подключение и адаптеры` использует `net use` во внешней консоли: пароль вводится там, не сохраняется в GUI и не пишется в log.
- Driver Update Blocker использует documented policy `ExcludeWUDriversInQualityUpdate` и Device Installation Restrictions, а не удаление драйверов вслепую.
- NVIDIA HDMI/DP Audio block ограничен NVIDIA HDAUDIO codec IDs `HDAUDIO\FUNC_01&VEN_10DE...`; GPU PCI IDs не блокируются этим модулем.
- DISM, Optional Features, WinRE, diskpart/storage и hosts edits остаются admin-действиями: backup, статус и confirmation обязательны для опасных сценариев.
- UCPD в проекте только диагностируется; модуль не отключает и не обходит его.

Документация Microsoft:

- [ApplicationDefaults Policy CSP](https://learn.microsoft.com/en-us/windows/client-management/mdm/policy-csp-applicationdefaults)
- [DISM default app associations](https://learn.microsoft.com/en-us/windows-hardware/manufacture/desktop/dism-default-application-association-servicing-command-line-options?view=windows-11)
- [Export or import default application associations](https://learn.microsoft.com/en-us/windows-hardware/manufacture/desktop/export-or-import-default-application-associations?view=windows-11)
- [netsh wlan](https://learn.microsoft.com/en-us/windows-server/administration/windows-commands/netsh-wlan)
- [WSL basic commands](https://learn.microsoft.com/en-us/windows/wsl/basic-commands)
- [Update Policy CSP / ExcludeWUDriversInQualityUpdate](https://learn.microsoft.com/en-us/windows/client-management/mdm/policy-csp-update#excludewudriversinqualityupdate)
- [Manage device installation with Group Policy](https://learn.microsoft.com/en-us/windows/client-management/manage-device-installation-with-group-policy/)

### Default Apps Guard За 60 Секунд

Если Windows уже установлена, программы стоят, defaults выставлены вручную, и нужно не дать Edge снова стать браузером или PDF-читалкой:

1. `Default Apps Guard -> Проверить защиту defaults`.
2. При важной точке отката заполнить `Метка backup`, например `golden-before`.
3. `Перезаписать эталон текущими defaults`.
4. Оставить `Remove Suggested=true`.
5. `Включить / починить защиту defaults`.
6. Sign out/sign in или reboot.
7. Снова `Проверить защиту defaults`.

`Метка backup` добавляется в имя timestamp backup-файла и в `.note.txt` рядом с ним, чтобы потом было видно, какой снимок был “до FastStone”, “golden before” или “clean Windows + Office”.
Восстановление собственного снимка делается через `Заменить эталон из backup/XML`: штатные XML из `backup\default_apps` выбираются из dropdown `Backup XML`; `Внешний XML` нужен только для файла извне.
`Очистить устаревшие резервные копии` удаляет только безымянные timestamp backups; файлы с меткой, ручные XML/TXT и `.note.txt` остаются.
Список `Отслеживать` находится в `Дополнительно`: он задаёт область диагностики/сравнения, а не сам policy XML. Для него есть быстрые пресеты `Все`, `Снять`, `По умолчанию`, `WEB`, `IMAGE`, `VIDEO`, `AUDIO`, `OFFICE` и соседние группы.

Тонкости и забавности Windows описаны отдельно: `docs\DEFAULT_APPS_GUARD_RU.md`.

На Windows 11 Home этот сценарий становится ограниченным: status/snapshot/rescan/import остаются полезными, но policy-слой не считается Microsoft-documented гарантом. Снимки ассоциаций в `Association Defense` работают на любой редакции — они только читают реестр.

### Hardware / Driver Guard За 45 Секунд

Если Windows любит подменять рабочие драйверы:

1. `Hardware -> Driver Update Blocker -> Проверить защиту драйверов`.
2. `Блокировать драйверы Windows Update`.
3. Reboot.
4. Снова проверить статус.

После ручной установки хорошего NVIDIA-драйвера можно дополнительно включить `Блокировать NVIDIA driver installs`, оставив `Retroactive block` выключенным. Быстрый корневой wrapper для автозагрузки или Task Scheduler: `cli\Lock-NVIDIA-Driver-Installs.cmd --no-pause`.

Для надоедливого звука мониторов через NVIDIA HDMI/DP: `NVIDIA audio status`, затем `Disable` или `Policy-block`. Быстрый корневой wrapper для жесткого policy-блока: `cli\Lock-NVIDIA-HDMI-DP-Audio.cmd --no-pause`.

Скрипты встроены в проект: `system_core\windows_driver_guard` и `system_core\nvidia_audio`. Старые внешние папки больше не нужны. CLI-доступ есть в `cli\launcher_hardware.cmd`; `launcher_project.cmd` / `launcher_project_ru.cmd` открывают его из общего меню. Это короткий набор основных команд из прототипов, не полный дубль GUI.

### Utilities За 30 Секунд

Раздел `Utilities` не является складом случайных кнопок. Там лежат небольшие, но рабочие project-local helpers:

- OpenSSH KeyKit: export/import client keys и client+server SSH material. Это sensitive export: backup может содержать private keys, `known_hosts`, client config, `authorized_keys`, server host keys и `sshd_config`.
- Certificate KeyKit: status/export/import Windows certificates. PFX backup содержит private keys; TPM/non-exportable ключи честно помечаются и не экспортируются.
- Documentation PDF: автономно строит dry-run план для корневых guides, `docs\*.md`, `GitHub\*.md` и optional agent instructions; реальный рендер в `docs\PDF` использует внешний engine из `--engine`, `AUDION_MARKDOWN_PDF_ENGINE` или автоматически найденного соседнего проекта.
- Ubuntu Dev Installer Kit: README, Btrfs/Timeshift guide, installer script, NVMe prep script и package lists для portable Linux/NVMe сценариев.
- ripgrep: проверка проектного `ripgrep\rg.exe`.
- folder shortcuts: быстрый доступ к папкам набора.

Generated PDF-документы складываются в `docs\PDF`. Source Markdown остается в корне, `docs` и `GitHub`; PDF рядом с исходными MD не храним. После генерации отдельную визуальную проверку PDF не выполняем: итог считается артефактом Markdown source + общего PDF engine.

<!-- BEGIN GENERATED COMMAND CATALOG -->
## Полный Каталог Команд

Этот каталог генерируется из `config\tool_manifest.yaml`. Он содержит все команды и полный текст, который используется как пользовательская подсказка в GUI. Цвет кнопки не заменяет `kind`, `risk_level`, подтверждение и журнал.

### Среда выполнения и оболочка

- **Среда выполнения и оболочка > Предварительный снимок** (`preflight_status`) — Один снимок в терминале: права администратора, WSL, виртуализация, PowerShell, сеть, Wi-Fi и риски дисков. _kind=`safe`, risk_level=`readonly`._
- **Среда выполнения и оболочка > Статус PowerShell** (`runtime_status`) — Показать портативный/системный PowerShell и его версию. _kind=`safe`, risk_level=`readonly`._
- **Среда выполнения и оболочка > Проверить Windows Long Paths** (`windows_long_paths_status`) — Показать HKLM LongPathsEnabled и значения Git core.longpaths. Настройки не меняет. _kind=`safe`, risk_level=`readonly`._
- **Среда выполнения и оболочка > Включить Windows Long Paths** (`windows_long_paths_enable`) — Установить HKLM LongPathsEnabled=1. Приложениям всё равно нужна поддержка longPathAware. _kind=`dangerous`, risk_level=`system_change`._
- **Среда выполнения и оболочка > Включить Git Long Paths** (`git_long_paths_enable`) — Установить git config --global core.longpaths true для текущего пользователя. _kind=`dangerous`, risk_level=`user_write`._
- **Среда выполнения и оболочка > Установить портативный PowerShell** (`install_portable_powershell`) — Скачать и установить pwsh.exe в system_core/powershell. _kind=`safe`, risk_level=`readonly`._
### Browser Bookmarks Master

- **Browser Bookmarks Master > Статус** (`browser_bookmarks_status`) — Проверка без изменений: файлы выбранного профиля, состояние процесса и последний импортируемый backup из Workbench SOURCE. В GUI status можно запускать для одного или нескольких отмеченных браузеров. _kind=`safe`, risk_level=`readonly`._
- **Browser Bookmarks Master > Очистить локальный Favicons cache** (`browser_bookmarks_clear_favicons`) — Создаёт rollback backup, закрывает отмеченные браузеры и удаляет Favicons с sidecar-файлами. Chrome создаёт пустую базу, но возвращает иконки лишь по мере посещения страниц. _kind=`dangerous`, risk_level=`user_write`._
- **Browser Bookmarks Master > Экспорт эталона в Workbench TARGET** (`browser_bookmarks_export_master`) — Закрывает выбранные браузеры и копирует Bookmarks, Favicons и доступные служебные sidecar-файлы Chromium в версионированные папки backup внутри Workbench TARGET. _kind=`dangerous`, risk_level=`secret_export`._
- **Browser Bookmarks Master > Импорт эталона из Workbench SOURCE** (`browser_bookmarks_import_master`) — Импортирует выбранный нативный backup или HTML во все отмеченные системные браузеры; portable-режим работает с одним точным профилем. Для каждого создаётся rollback. _kind=`dangerous`, risk_level=`destructive`._
- **Browser Bookmarks Master > Перенести эталон между браузерами** (`browser_bookmarks_transfer_master`) — Двухэтапный перенос: выгружает выбранный браузер-источник в project-local backup, затем импортирует этот backup в выбранные браузеры-приёмники с pre-import backup и очисткой Favicons. _kind=`dangerous`, risk_level=`destructive`._
- **Browser Bookmarks Master > Открыть локальные safety backups** (`browser_bookmarks_open_local_backup`) — Открыть project-local Browser Bookmarks backup с pre-import snapshots. _kind=`safe`, risk_level=`readonly`._
### Очистка сети

- **Очистка сети > Снимок статуса** (`network_status`) — Снимок состояния сети без изменений: собирает ipconfig, таблицу маршрутов, сетевые адаптеры, DNS, параметры прокси и Wi-Fi status, затем пишет timestamp backup в backup проекта. _kind=`safe`, risk_level=`readonly`._
- **Очистка сети > Полный backup сети** (`network_backup`) — Полный снимок Network Cleaner: сетевые адаптеры, IP/DNS, маршруты, прокси, Брандмауэр Защитника Windows, реестр и Wi-Fi XML без открытых ключей. _kind=`safe`, risk_level=`readonly`._
- **Очистка сети > Полный backup + Wi-Fi ключи** (`network_backup_wifi_keys`) — Тот же полный снимок Network Cleaner плюс Wi-Fi XML с ключами открытым текстом. Для точечного переноса профилей используйте Wi-Fi профили. _kind=`dangerous`, risk_level=`secret_export`._
- **Очистка сети > Восстановить backup сети > Восстановить последний backup** (`network_restore_latest`) — Восстановить самый свежий снимок Network Cleaner. Сначала сохраняет текущее состояние, затем импортирует сохранённые данные реестра, сети, Брандмауэра Защитника Windows, hosts и Wi-Fi, где они доступны. _kind=`dangerous`, risk_level=`system_change`._
- **Очистка сети > Восстановить backup сети > Восстановить выбранный backup** (`network_restore_selected`) — Восстановить выбранный снимок Network Cleaner из backup-папки. Используй, когда последний backup не тот, к которому нужно вернуться. _kind=`dangerous`, risk_level=`system_change`._
- **Очистка сети > Профили ремонта > Легкий ремонт** (`network_light_repair`) — Самый мягкий ремонт: flush/register DNS, очистка ARP, обновление NetBIOS и DHCP renew только для подключённых DHCP-интерфейсов. _kind=`dangerous`, risk_level=`system_change`._
- **Очистка сети > Профили ремонта > Стандартный ремонт** (`network_standard_repair`) — Нормальная эскалация: сбрасывает Winsock, TCP/IP и WinHTTP proxy, затем обновляет DNS и ARP. После рекомендуется перезагрузка. _kind=`dangerous`, risk_level=`system_change`._
- **Очистка сети > Профили ремонта > Жёсткий ремонт** (`network_nuclear_repair`) — Тяжёлый ремонт: стандартный ремонт плюс очистка маршрутов; оригинальный скрипт отдельно спрашивает перед самыми глубокими reset-шагами. _kind=`dangerous`, risk_level=`system_change`._
- **Очистка сети > Прокси > Статус прокси** (`network_proxy_status`) — Показать параметры прокси текущего пользователя WinINet/System и системный WinHTTP proxy без изменений. _kind=`safe`, risk_level=`readonly`._
- **Очистка сети > Прокси > Отключить прокси пользователя** (`network_proxy_disable_user`) — Отключает WinINet/System proxy текущего пользователя. Полезно после корпоративных, VPN или proxy-инструментов, которые оставили устаревшие параметры. _kind=`dangerous`, risk_level=`user_write`._
- **Очистка сети > Прокси > Сбросить WinHTTP proxy** (`network_proxy_reset_winhttp`) — Сбрасывает системный WinHTTP proxy для служб и части системных инструментов. Не правит прокси браузера и текущего пользователя. _kind=`dangerous`, risk_level=`system_change`._
- **Очистка сети > Открыть backup** (`network_open_backup`) — Открыть project-local backup Network Cleaner со снимками, restore manifests и run logs. _kind=`safe`, risk_level=`readonly`._
### Подключение и адаптеры

- **Подключение и адаптеры > Wi-Fi профили > Статус Wi-Fi** (`network_wifi_status`) — Показать wlan interfaces и сохранённые профили Wi-Fi. Настройки сети не меняет. _kind=`safe`, risk_level=`readonly`._
- **Подключение и адаптеры > Wi-Fi профили > Подключить профиль** (`network_wifi_connect`) — Подключиться к выбранному сохранённому Wi-Fi профилю, при необходимости через выбранный адаптер. _kind=`safe`, risk_level=`readonly`._
- **Подключение и адаптеры > Wi-Fi профили > Автоподключение профиля** (`network_wifi_connection_mode`) — Переключить выбранный Wi-Fi профиль в автоматический или ручной режим подключения. _kind=`dangerous`, risk_level=`system_change`._
- **Подключение и адаптеры > Wi-Fi профили > Экспорт профилей** (`network_wifi_export`) — Экспортировать Wi-Fi профили в выбранную папку; ключи открытым текстом включаются только отдельным чекбоксом. _kind=`dangerous`, risk_level=`secret_export`._
- **Подключение и адаптеры > Wi-Fi профили > Импорт профилей > Импорт XML файла** (`network_wifi_import_file`) — Добавить один XML-файл профиля Wi-Fi в Windows. _kind=`dangerous`, risk_level=`system_change`._
- **Подключение и адаптеры > Wi-Fi профили > Импорт профилей > Импорт папки XML** (`network_wifi_import_folder`) — Импортировать все XML-профили Wi-Fi из выбранной папки. _kind=`dangerous`, risk_level=`system_change`._
- **Подключение и адаптеры > SMB вход в сеть** (`smb_network_login`) — Открыть внешнюю консоль для net use входа к компьютеру с общими папками Windows: пароль вводится там, после этого SMB-сеанс доступен в Explorer. _kind=`dangerous`, risk_level=`user_write`._
- **Подключение и адаптеры > Действие адаптера** (`network_adapter_apply`) — Включить, выключить или перезапустить выбранный сетевой адаптер. Может оборвать активное подключение. _kind=`dangerous`, risk_level=`system_change`._
- **Подключение и адаптеры > LAN/Wi-Fi переключатель** (`network_lan_wifi_switch`) — Переключить LAN only, Wi-Fi only, включить оба адаптера или перезапустить Wi-Fi с подключением профиля. _kind=`dangerous`, risk_level=`system_change`._
- **Подключение и адаптеры > Wi-Fi sticky-пара** (`network_wifi_sticky_pair`) — Подключить один сохраненный профиль и сделать его авто-профилем, а второй оставить ручным. _kind=`dangerous`, risk_level=`system_change`._
### WSL Toolkit

- **WSL Toolkit > Базовые и установка > Статус WSL2 в системе** (`wsl_system_status`) — Показать компоненты Windows, WSL status и установленные дистрибутивы. _kind=`safe`, risk_level=`readonly`._
- **WSL Toolkit > Базовые и установка > Установить WSL2 в Windows** (`wsl_enable_features`) — Включить компоненты Microsoft-Windows-Subsystem-Linux и VirtualMachinePlatform, затем поставить WSL default version 2. Может потребоваться перезагрузка. _kind=`dangerous`, risk_level=`system_change`._
- **WSL Toolkit > Базовые и установка > Обновить WSL2** (`wsl_update_engine`) — Выполнить wsl --update для Windows WSL engine. _kind=`dangerous`, risk_level=`system_change`._
- **WSL Toolkit > Базовые и установка > Список для установки** (`wsl_list_online`) — Выполнить wsl --list --online и вывести доступные имена дистрибутивов. _kind=`safe`, risk_level=`readonly`._
- **WSL Toolkit > Базовые и установка > Установить дистрибутив** (`wsl_install_distro`) — Установить выбранный online WSL-дистрибутив в системное место или в выбранную папку. _kind=`dangerous`, risk_level=`system_change`._
- **WSL Toolkit > Базовые и установка > Установить из файла образа** (`wsl_install_from_file`) — Установить локальный .wsl образ, например ubuntu-26.04-wsl-amd64.wsl, или импортировать tar/vhd/vhdx в выбранную папку. _kind=`dangerous`, risk_level=`system_change`._
- **WSL Toolkit > Базовые и установка > Список установленных** (`wsl_list`) — Выполнить wsl --list --verbose. _kind=`safe`, risk_level=`readonly`._
- **WSL Toolkit > Базовые и установка > Статус WSL** (`wsl_status`) — Выполнить wsl --status. _kind=`safe`, risk_level=`readonly`._
- **WSL Toolkit > Базовые и установка > Shutdown WSL** (`wsl_shutdown`) — Остановить все WSL-дистрибутивы. _kind=`dangerous`, risk_level=`system_change`._
- **WSL Toolkit > Linux-конфигурация > Package update** (`wsl_linux_apt_update`) — Выполнить apt/dnf update metadata и при желании upgrade внутри выбранного WSL-дистрибутива. _kind=`dangerous`, risk_level=`system_change`._
- **WSL Toolkit > Linux-конфигурация > Учётка Linux** (`wsl_linux_account`) — Создать/обновить пользователя Linux, пароль, sudo/wheel group и WSL default user. _kind=`dangerous`, risk_level=`system_change`._
- **WSL Toolkit > Linux-конфигурация > Dev-пакеты** (`wsl_linux_dev_packages`) — Установить Audion WSL Dev packages. Heavy/Desktop пакеты не выбраны. _kind=`dangerous`, risk_level=`system_change`._
- **WSL Toolkit > Linux-конфигурация > Micro baseline** (`wsl_micro_baseline`) — Поставить Audion-настройки micro и keybindings для выбранного Linux-пользователя. _kind=`dangerous`, risk_level=`user_write`._
- **WSL Toolkit > Linux-конфигурация > MC skin** (`wsl_mc_skin`) — Поставить Audion skin для Midnight Commander и при желании сделать активным. _kind=`dangerous`, risk_level=`user_write`._
- **WSL Toolkit > Linux-конфигурация > Neovim base** (`wsl_neovim_base`) — Поставить Audion-профиль Neovim без AI-провайдеров. _kind=`dangerous`, risk_level=`user_write`._
- **WSL Toolkit > Ubuntu Dev Installer Kit > Открыть папку kit** (`ubuntu_dev_open_folder`) — Открыть tools/ubuntu_dev_installer. _kind=`safe`, risk_level=`readonly`._
- **WSL Toolkit > Ubuntu Dev Installer Kit > Открыть README RU** (`ubuntu_dev_open_readme_ru`) — Открыть README RU для project-local Ubuntu kit. _kind=`safe`, risk_level=`readonly`._
- **WSL Toolkit > Ubuntu Dev Installer Kit > Открыть Btrfs guide** (`ubuntu_dev_open_btrfs_guide`) — Открыть Btrfs/Timeshift LiveUSB guide. _kind=`safe`, risk_level=`readonly`._
- **WSL Toolkit > Ubuntu Dev Installer Kit > Открыть installer script** (`ubuntu_dev_open_installer_script`) — Открыть главный Ubuntu dev installer script из project-local kit. _kind=`safe`, risk_level=`readonly`._
- **WSL Toolkit > Ubuntu Dev Installer Kit > Открыть NVMe prep script** (`ubuntu_dev_open_nvme_prep_script`) — Открыть Btrfs/LUKS Ubuntu LiveUSB prep script из project-local kit. _kind=`safe`, risk_level=`readonly`._
- **WSL Toolkit > Ubuntu Dev Installer Kit > Открыть списки пакетов** (`ubuntu_dev_open_packages`) — Открыть папку package-list, которую использует kit. _kind=`safe`, risk_level=`readonly`._
- **WSL Toolkit > Действия с дистрибутивом > Остановить дистрибутив** (`wsl_terminate`) — Остановить выбранный WSL-дистрибутив. _kind=`dangerous`, risk_level=`system_change`._
- **WSL Toolkit > Действия с дистрибутивом > Backup дистрибутива** (`wsl_backup`) — Экспортировать дистрибутив в tar или vhd. _kind=`dangerous`, risk_level=`secret_export`._
- **WSL Toolkit > Действия с дистрибутивом > Клонировать дистрибутив** (`wsl_clone`) — Экспортировать и импортировать под новым именем. _kind=`dangerous`, risk_level=`system_change`._
- **WSL Toolkit > Действия с дистрибутивом > Перенести дистрибутив** (`wsl_move`) — Перенести дистрибутив через export/import. Операция использует временный backup и затем unregister старого имени; сначала проверь target и папку backup. _kind=`dangerous`, risk_level=`destructive`._
- **WSL Toolkit > Действия с дистрибутивом > Удалить дистрибутив** (`wsl_delete`) — Навсегда unregister выбранного WSL-дистрибутива: Windows удалит регистрацию и файловую систему дистрибутива. Перед этим сделай Backup дистрибутива, если нужен откат. _kind=`dangerous`, risk_level=`destructive`._
- **WSL Toolkit > Import и restore > Import VHDX in-place** (`wsl_import_in_place`) — Зарегистрировать существующий ext4.vhdx как WSL-дистрибутив. _kind=`dangerous`, risk_level=`system_change`._
- **WSL Toolkit > Import и restore > Restore из backup** (`wsl_restore_from_backup`) — Импортировать tar/vhd/vhdx backup как WSL-дистрибутив. _kind=`dangerous`, risk_level=`system_change`._
- **WSL Toolkit > Регистрация VHDX пачкой > Зарегистрировать все VHDX** (`wsl_register_all_vhdx`) — Неинтерактивный batch import-in-place. По умолчанию dry run; существующие имена дистрибутивов пропускаются. _kind=`dangerous`, risk_level=`system_change`._
### Виртуализация

- **Виртуализация > Статус виртуализации** (`virt_status`) — Показать hypervisorlaunchtype, состояние компонентов Hyper-V/VMPlatform/WHP/Sandbox/WSL, VBS/Core Isolation и интерпретированный текущий режим. _kind=`safe`, risk_level=`readonly`._
- **Виртуализация > Статус оптимизации** (`virt_optimization_status`) — Только чтение: что тормозит VM/WSL - Core Isolation/VBS, активная схема электропитания, исключения Microsoft Defender для путей WSL/VM, наличие .wslconfig и расположение WSL VHDX. _kind=`safe`, risk_level=`readonly`._
- **Виртуализация > Режим: Hyper-V / WSL2** (`virt_mode_hyperv`) — hypervisorlaunchtype=Auto и включение VirtualMachinePlatform. Заработают Hyper-V/WSL2/Windows Sandbox; сторонние VM - только через WHP или не стартуют. Backup: backup\virtualization. Нужна перезагрузка. _kind=`dangerous`, risk_level=`system_change`._
- **Виртуализация > Режим: Сторонние VM (быстро)** (`virt_mode_thirdparty`) — hypervisorlaunchtype=Off. VMware/VirtualBox на полной скорости; WSL2/Hyper-V/Windows Sandbox перестанут работать до обратного переключения. При включённом VBS/Core Isolation VT-x всё равно может быть занят. Backup: backup\virtualization. Нужна перезагрузка. _kind=`dangerous`, risk_level=`system_change`._
- **Виртуализация > Режим: Сосуществование (WHP)** (`virt_mode_coexist`) — hypervisorlaunchtype=Auto + включение Windows Hypervisor Platform и VirtualMachinePlatform, чтобы современные VMware/VirtualBox работали рядом с Hyper-V/WSL2 (медленнее). Backup: backup\virtualization. Нужна перезагрузка. _kind=`dangerous`, risk_level=`system_change`._
- **Виртуализация > Включить Hyper-V** (`virt_hyperv_enable`) — Включить Microsoft-Hyper-V-All (Диспетчер Hyper-V + платформа) и hypervisorlaunchtype=Auto. Backup: backup\virtualization. Нужна перезагрузка. _kind=`dangerous`, risk_level=`system_change`._
- **Виртуализация > Выключить Hyper-V** (`virt_hyperv_disable`) — Выключить Microsoft-Hyper-V-All. Для полной скорости сторонних VM также примените режим «Сторонние VM» (hypervisorlaunchtype=Off). Backup: backup\virtualization. Нужна перезагрузка. _kind=`dangerous`, risk_level=`system_change`._
- **Виртуализация > Включить Windows Sandbox** (`virt_sandbox_enable`) — Включить Containers-DisposableClientVM (Windows Sandbox). Требует включённый гипервизор (режим Hyper-V/WSL2). Backup: backup\virtualization. Нужна перезагрузка. _kind=`dangerous`, risk_level=`system_change`._
- **Виртуализация > Выключить Windows Sandbox** (`virt_sandbox_disable`) — Выключить Containers-DisposableClientVM (Windows Sandbox). Backup: backup\virtualization. Нужна перезагрузка. _kind=`dangerous`, risk_level=`system_change`._
### Hosts и Bitrix

- **Hosts и Bitrix > Найти текущий endpoint** (`bitrix_detect_endpoint`) — DNS-only lookup игнорирует старые hosts-записи, принимает только локальные/частные IP-адреса, сканирует порты-кандидаты и подставляет IP/ports в поля без изменения hosts. _kind=`safe`, risk_level=`readonly`._
- **Hosts и Bitrix > Статус / DNS / ports** (`bitrix_status`) — Показать hosts override, фактический resolved IP, DNS-ответ, авто-скан портов и TCP-проверку. _kind=`safe`, risk_level=`readonly`._
- **Hosts и Bitrix > Включить override** (`bitrix_enable`) — Применить hosts override для host и IP; найденные/custom порты сохраняются в управляемом комментарии hosts. _kind=`dangerous`, risk_level=`system_change`._
- **Hosts и Bitrix > Выключить override** (`bitrix_disable`) — Побитовый depatch: восстановить точный pre-patch backup hosts, указанный в managed hosts line. _kind=`dangerous`, risk_level=`system_change`._
- **Hosts и Bitrix > Восстановить hosts** (`bitrix_restore`) — Восстановить hosts из последнего pre-patch backup, когда явный depatch по managed-line недоступен. _kind=`dangerous`, risk_level=`system_change`._
### Приложения по умолчанию

- **Приложения по умолчанию > Политика** (`default_apps_policy`) — Запоминает, какими программами открываются ваши файлы, и заставляет Windows возвращать этот набор при каждом входе. _kind=`dangerous`, risk_level=`system_change`._
- **Приложения по умолчанию > Microsoft** (`default_apps_microsoft`) — Убирает или возвращает встроенные приложения Microsoft и удерживает результат после обновлений Windows. _kind=`dangerous`, risk_level=`system_change`._
- **Приложения по умолчанию > Edge** (`default_apps_edge`) — Оставляет Edge на месте, но отучает его перетягивать ссылки и типы файлов у вашего основного браузера. _kind=`dangerous`, risk_level=`system_change`._
- **Приложения по умолчанию > Отслеживание** (`default_apps_watch`) — Отслеживает смену ассоциаций и управляет исключениями Defender для папок Audion. _kind=`dangerous`, risk_level=`system_change`._
- **Приложения по умолчанию > Снимок** (`default_apps_snapshot`) — Сохраняет и сравнивает карту ассоциаций текущего пользователя. _kind=`dangerous`, risk_level=`user_write`._
- **Приложения по умолчанию > Группы** (`default_apps_groups`) — Сохраняет ассоциации по группам — фото, аудио, видео, PDF, браузер — пока нужные программы установлены. _kind=`dangerous`, risk_level=`user_write`._
- **Приложения по умолчанию > Общий отчёт** (`default_apps_overview`) — Прогоняет все проверки этого раздела подряд и печатает единый отчёт. _kind=`safe`, risk_level=`readonly`._
### Hardware

- **Hardware > Driver/Firmware Audit** (`driver_firmware_audit`) — Диагностический отчёт без изменений: проблемные устройства из Диспетчера устройств, BIOS/EC, firmware/UEFI resources и ключевые подписанные драйверы. _kind=`safe`, risk_level=`project_write`._
- **Hardware > Материалы Driver/Firmware Audit > Открыть папку аддона** (`driver_firmware_audit_open_folder`) — Открыть tools/driver_firmware_audit. _kind=`safe`, risk_level=`readonly`._
- **Hardware > Материалы Driver/Firmware Audit > Открыть README** (`driver_firmware_audit_open_readme`) — Открыть README аддона из project-local copy. _kind=`safe`, risk_level=`readonly`._
- **Hardware > Driver Update Blocker > Windows Update driver policy > Проверить защиту драйверов** (`driver_update_status`) — Статус без изменений: Windows Update driver policy, параметры поиска драйверов, device metadata policy, DeviceInstall restrictions и текущие NVIDIA PCI устройства. _kind=`safe`, risk_level=`readonly`._
- **Hardware > Driver Update Blocker > Windows Update driver policy > Блокировать драйверы Windows Update** (`driver_update_block_all`) — Делает backup policy-ключей, ставит ExcludeWUDriversInQualityUpdate=1, выключает поиск драйверов через мастер установки оборудования и загрузку метаданных устройств, затем запускает gpupdate. Рекомендуется перезагрузка. _kind=`dangerous`, risk_level=`system_change`._
- **Hardware > Driver Update Blocker > Windows Update driver policy > Разблокировать драйверы Windows Update** (`driver_update_unblock_all`) — Делает backup policy-ключей, удаляет значения блокировки драйверов Центра обновления Windows, возвращает обычное поведение driver search, затем запускает gpupdate. Рекомендуется перезагрузка. _kind=`dangerous`, risk_level=`system_change`._
- **Hardware > Driver Update Blocker > Windows Update driver policy > Открыть policy backups** (`driver_update_open_policy_backups`) — Открыть backups policy-ключей реестра, которые создаются перед block/unblock операциями. _kind=`safe`, risk_level=`readonly`._
- **Hardware > Driver Update Blocker > HWID-защита драйвера устройства > Проверить текущий lock** (`hwid_driver_status`) — Проверка без изменений: показывает, залочен ли этот HWID и какой драйвер сейчас best-ranked/installed. _kind=`safe`, risk_level=`readonly`._
- **Hardware > Driver Update Blocker > HWID-защита драйвера устройства > 1. Разблокировать перед обновлением** (`hwid_driver_unblock`) — Нажать перед установкой нужного manual/generic драйвера. Удаляет matching HWID locks, сохраняя чужие policy entries. _kind=`dangerous`, risk_level=`system_change`._
- **Hardware > Driver Update Blocker > HWID-защита драйвера устройства > 2. Заблокировать после установки** (`hwid_driver_block`) — Нажать после установки и проверки нужного драйвера. Добавляет этот HWID в DenyDeviceIDs, чтобы Windows Driver Store/WU не подменил его молча. _kind=`dangerous`, risk_level=`system_change`._
- **Hardware > Driver Update Blocker > Аварийный rank repair по HWID > Проверить rank target** (`hwid_driver_rank_status`) — Read-only проверка target: определяет устройство по HWID, показывает current signed driver data и pnputil driver/rank report. _kind=`safe`, risk_level=`readonly`._
- **Hardware > Driver Update Blocker > Аварийный rank repair по HWID > Починить driver rank по HWID** (`hwid_driver_rank_repair`) — Создаёт REG/JSON preflight backup, экспортирует старый package, удаляет bad current INF package, ставит target INF, делает rescan/restart устройства, затем применяет targeted HWID block. Используй только после проверки target. _kind=`dangerous`, risk_level=`system_change`._
- **Hardware > Driver Update Blocker > NVIDIA driver install restrictions > Блокировать NVIDIA driver installs** (`nvidia_driver_block`) — Находит текущие NVIDIA PCI устройства, пишет их Hardware IDs в Device Installation Restrictions и запускает gpupdate. Полезно после установки заведомо хорошего manual/NVCleanstall драйвера. _kind=`dangerous`, risk_level=`system_change`._
- **Hardware > Driver Update Blocker > NVIDIA driver install restrictions > Разблокировать NVIDIA driver installs** (`nvidia_driver_unblock`) — Удаляет NVIDIA PCI IDs из Device Installation Restrictions, сохраняя не-NVIDIA entries в тех же policy lists. _kind=`dangerous`, risk_level=`system_change`._
- **Hardware > Driver Update Blocker > Driver Store backups > Сохранить Driver Store manifest** (`driver_store_manifest`) — Сохраняет отчёты pnputil, systeminfo и Get-WindowsDriver без экспорта driver packages. _kind=`safe`, risk_level=`readonly`._
- **Hardware > Driver Update Blocker > Driver Store backups > Экспортировать установленные драйверы** (`driver_store_export`) — Экспортирует текущие third-party drivers из Driver Store в timestamp backup через Export-WindowsDriver или DISM fallback. _kind=`safe`, risk_level=`project_write`._
- **Hardware > Driver Update Blocker > Driver Store backups > Восстановить экспортированные драйверы** (`driver_store_restore`) — Запускает pnputil /add-driver по выбранному backup без интерактивных prompts. Используй backups с той же машины или очень близкого железа. _kind=`dangerous`, risk_level=`system_change`._
- **Hardware > Driver Update Blocker > Driver Store backups > Открыть driver backups** (`driver_store_open_backups`) — Открыть папку экспортированных driver backups. _kind=`safe`, risk_level=`readonly`._
- **Hardware > Driver Update Blocker > Открыть папку Driver Update Blocker** (`driver_update_open_tool`) — Открыть проектную PowerShell-папку модуля, которую используют GUI и project launchers. _kind=`safe`, risk_level=`readonly`._
- **Hardware > NVIDIA HDMI/DP Audio > Статус NVIDIA audio** (`nvidia_audio_status`) — Статус без изменений: найденные NVIDIA HDMI/DP audio devices, выбранные HDAUDIO Hardware IDs и текущие DeviceInstall policy entries. _kind=`safe`, risk_level=`readonly`._
- **Hardware > NVIDIA HDMI/DP Audio > Экспортировать NVIDIA audio IDs** (`nvidia_audio_export_ids`) — Пишет device details и candidate IDs для policy-block в output-папку оригинальной утилиты. _kind=`safe`, risk_level=`readonly`._
- **Hardware > NVIDIA HDMI/DP Audio > Отключить NVIDIA HDMI/DP audio** (`nvidia_audio_disable`) — Отключает текущие matching NVIDIA HDMI/DP audio devices через Disable-PnpDevice. Обычные audio interfaces не трогает. _kind=`dangerous`, risk_level=`system_change`._
- **Hardware > NVIDIA HDMI/DP Audio > Включить NVIDIA HDMI/DP audio** (`nvidia_audio_enable`) — Снова включает matching NVIDIA HDMI/DP audio devices. Если policy block активен, сначала сними policy. _kind=`dangerous`, risk_level=`system_change`._
- **Hardware > NVIDIA HDMI/DP Audio > Policy-block NVIDIA HDMI/DP audio** (`nvidia_audio_block_policy`) — Делает backup DeviceInstall policy, добавляет только NVIDIA HDAUDIO codec IDs в DenyDeviceIDs, отключает matching devices и запускает PnP rescan. _kind=`dangerous`, risk_level=`system_change`._
- **Hardware > NVIDIA HDMI/DP Audio > Снять policy-block NVIDIA HDMI/DP audio** (`nvidia_audio_unblock_policy`) — Удаляет известные NVIDIA HDAUDIO IDs из DeviceInstall policy, запускает PnP rescan и пытается включить matching devices. _kind=`dangerous`, risk_level=`system_change`._
- **Hardware > NVIDIA HDMI/DP Audio > Открыть NVIDIA audio output** (`nvidia_audio_open_output`) — Открыть output-папку с экспортированными NVIDIA HDMI/DP audio device IDs. _kind=`safe`, risk_level=`readonly`._
- **Hardware > NVIDIA HDMI/DP Audio > Открыть NVIDIA audio backup** (`nvidia_audio_open_backup`) — Открыть DeviceInstall policy backups, созданные перед изменениями NVIDIA audio policy. _kind=`safe`, risk_level=`readonly`._
- **Hardware > NVIDIA HDMI/DP Audio > Открыть папку NVIDIA audio tool** (`nvidia_audio_open_tool`) — Открыть проектную папку NVIDIA HDMI/DP Audio module, которую используют GUI и project launchers. _kind=`safe`, risk_level=`readonly`._
- **Hardware > Накопители / дисковые процедуры > Инвентаризация дисков** (`storage_inventory`) — Сводка без изменений по Get-Disk/Get-Volume: номера дисков, размеры, буквы томов, файловая система и состояние. _kind=`safe`, risk_level=`readonly`._
- **Hardware > Накопители / дисковые процедуры > Детали выбранного диска** (`storage_disk_details`) — Layout диска без изменений и разделы для выбранного номера диска перед ручной работой со storage. _kind=`safe`, risk_level=`readonly`._
- **Hardware > Накопители / дисковые процедуры > Запустить SSD/NVMe wizard** (`storage_ssd_reset_wizard`) — Открыть оригинальный wizard во внешней консоли; destructive-действия всё равно требуют typed confirmations внутри него. _kind=`dangerous`, risk_level=`destructive`._
- **Hardware > Накопители / дисковые процедуры > Открыть папку SSD/NVMe** (`storage_ssd_open_folder`) — Открыть папку SSD/NVMe wizard с README, logs и original scripts; без изменений дисков. _kind=`safe`, risk_level=`readonly`._
- **Hardware > Накопители / дисковые процедуры > Статус WinRE layout** (`storage_winre_status`) — Проверка без изменений: reagentc и layout системного диска, активная WinRE и соседние разделы. _kind=`safe`, risk_level=`readonly`._
- **Hardware > Накопители / дисковые процедуры > Запустить WinRE wizard** (`storage_winre_wizard`) — Отключает WinRE, удаляет раздел восстановления справа от C: и расширяет C: после подтверждения в проекте. _kind=`dangerous`, risk_level=`destructive`._
### OpenSSH KeyKit

- **OpenSSH KeyKit > Проверить связность доступов** (`ssh_keykit_check_links`) — Читает ssh и rclone конфигурацию и показывает каждый путь к ключу, known_hosts и прокси, которого больше нет. _kind=`safe`, risk_level=`readonly`._
- **OpenSSH KeyKit > Экспорт client SSH keys** (`ssh_keykit_export_client`) — Экспортировать .ssh keys/config/known_hosts/authorized_keys текущего пользователя в output\ssh_keykit. _kind=`dangerous`, risk_level=`secret_export`._
- **OpenSSH KeyKit > Экспорт client + server SSH keys** (`ssh_keykit_export_all`) — Экспортировать .ssh текущего пользователя плюс ProgramData\ssh host keys и sshd_config при запуске с правами администратора. _kind=`dangerous`, risk_level=`secret_export`._
- **OpenSSH KeyKit > Импорт client SSH keys** (`ssh_keykit_import_client`) — Отложить текущую .ssh копией .ssh.bak.timestamp, импортировать свежий/выбранный client snapshot из input и починить ACL закрытых ключей. _kind=`dangerous`, risk_level=`user_write`._
- **OpenSSH KeyKit > Импорт client + server SSH keys** (`ssh_keykit_import_all`) — Импортировать client keys плюс server host keys из input, починить ACL, перезапустить sshd и поставить startup type Automatic при запуске с правами администратора. _kind=`dangerous`, risk_level=`system_change`._
- **OpenSSH KeyKit > Открыть папку скриптов KeyKit** (`ssh_keykit_open_folder`) — Открыть tools\ssh_keykit со scripts/wrappers export/import; без изменений ключей. _kind=`safe`, risk_level=`readonly`._
### Бэкап AI CLI

- **Бэкап AI CLI > Бэкап (экспорт)** (`ai_backup_export`) — Атомарно экспортировать Claude и Codex в output\ai_backup, затем проверить manifest и SHA-256. _kind=`dangerous`, risk_level=`secret_export`._
- **Бэкап AI CLI > Восстановить (импорт)** (`ai_backup_import`) — Проверить бэкап в input, по умолчанию показать план, затем заменить только выбранные совпадающие файлы; остальные локальные файлы сохраняются. _kind=`dangerous`, risk_level=`user_write`._
- **Бэкап AI CLI > Объединение памяти** (`ai_backup_merge`) — Проверить бэкап в input и объединить .md-память Claude с текущей, по умолчанию показав план. Совпадения сохраняются, пока не включён Overwrite. _kind=`dangerous`, risk_level=`user_write`._
- **Бэкап AI CLI > Открыть папку инструмента** (`ai_backup_open`) — Открыть tools\ai_backup со скриптом и обёртками. _kind=`safe`, risk_level=`readonly`._
### Сертификаты (экспорт/импорт)

- **Сертификаты (экспорт/импорт) > Статус сертификатов** (`cert_status`) — Список выбранного store: subject, thumbprint, срок действия, закрытый ключ и exportability (помечает TPM/non-exportable). _kind=`safe`, risk_level=`readonly`._
- **Сертификаты (экспорт/импорт) > Экспорт personal ключей в PFX** (`cert_export_pfx`) — Экспорт сертификатов с экспортируемым закрытым ключом из выбранного store в password-protected .pfx в output\certificates. TPM-ключи пропускаются. Файлы СОДЕРЖАТ закрытые ключи. _kind=`dangerous`, risk_level=`secret_export`._
- **Сертификаты (экспорт/импорт) > Экспорт store в SST (публично)** (`cert_export_roots`) — Экспорт публичных сертификатов выбранного store (без закрытых ключей) в .sst с timestamp в output\certificates. _kind=`safe`, risk_level=`project_write`._
- **Сертификаты (экспорт/импорт) > Импорт PFX** (`cert_import_pfx`) — Импортировать выбранный .pfx (с паролем) в целевой store, пометив ключ exportable. Меняет хранилище сертификатов; перезагрузка не нужна. Файл и пароль - в Advanced. _kind=`dangerous`, risk_level=`system_change`._
- **Сертификаты (экспорт/импорт) > Импорт всех PFX из папки** (`cert_import_pfx_folder`) — Импортирует каждый .pfx из certificates.json в то хранилище, откуда он был выгружен, одним паролем. Меняет хранилище сертификатов. _kind=`dangerous`, risk_level=`system_change`._
- **Сертификаты (экспорт/импорт) > Импорт сертификата / CA** (`cert_import_cert`) — Импортировать публичный .cer/.crt/.sst в целевой store (например, доверие корпоративному root CA). Меняет доверие; выбирайте store аккуратно. Файл - в Advanced. _kind=`dangerous`, risk_level=`system_change`._
- **Сертификаты (экспорт/импорт) > Открыть папку экспорта сертификатов** (`cert_open_folder`) — Открыть output\certificates; без изменений сертификатов. _kind=`safe`, risk_level=`readonly`._
### Шрифты пользователя

- **Шрифты пользователя > Показать мои шрифты** (`fonts_status`) — Перечисляет шрифты, установленные для этого пользователя, с пометкой [ OK ] или [MISS], и считает системные. Ничего не меняет. _kind=`safe`, risk_level=`readonly`._
- **Шрифты пользователя > Экспорт моих шрифтов** (`fonts_export`) — Копирует файлы пользовательских шрифтов в output\fonts вместе с картой их зарегистрированных имён. Системные не копируются. _kind=`safe`, risk_level=`project_write`._
- **Шрифты пользователя > Импорт шрифтов** (`fonts_import`) — Ставит собранные шрифты только для этого пользователя: файл в профиль, имя в HKCU, запущенным программам сообщается. Прав администратора не нужно, C:\Windows\Fonts не затрагивается. _kind=`dangerous`, risk_level=`user_write`._
- **Шрифты пользователя > Открыть папку шрифтов** (`fonts_open_folder`) — Открыть output\fonts; ничего не собирает. _kind=`safe`, risk_level=`readonly`._
### Среда оболочки

- **Среда оболочки > Показать файлы оболочки** (`shell_status`) — Перечисляет настройки Windows Terminal и профили PowerShell, которые есть на этой машине, с пометкой [ OK ] или [ -- ]. Ничего не меняет. _kind=`safe`, risk_level=`readonly`._
- **Среда оболочки > Экспорт файлов оболочки** (`shell_export`) — Копирует найденные настройки и профили в output\shell вместе с картой, что есть что. _kind=`safe`, risk_level=`project_write`._
- **Среда оболочки > Импорт файлов оболочки** (`shell_import`) — Кладёт каждый собранный файл туда, где его место на этой машине, сохраняя копию с датой у заменяемого. Совпадающий файл не трогает. _kind=`dangerous`, risk_level=`user_write`._
- **Среда оболочки > Открыть папку среды оболочки** (`shell_open_folder`) — Открыть output\shell; ничего не собирает. _kind=`safe`, risk_level=`readonly`._
### Доступы из конфигурации

- **Доступы из конфигурации > Показать, что названо в конфигурации** (`access_status`) — Перечисляет каждый ключ, known_hosts, сертификат и путь к прокси из конфигурации ssh и rclone с пометкой [ OK ] или [MISS]. Ничего не меняет. _kind=`safe`, risk_level=`readonly`._
- **Доступы из конфигурации > Экспорт файлов доступов** (`access_export`) — Копирует ssh config, rclone.conf и каждый названный ими файл в output\access вместе с картой происхождения. Содержит ЗАКРЫТЫЕ КЛЮЧИ. _kind=`dangerous`, risk_level=`secret_export`._
- **Доступы из конфигурации > Импорт файлов доступов** (`access_import`) — Кладёт привезённые файлы в выбранную папку, переписывает под них конфигурацию ssh и rclone, ограничивает права на ключи и проверяет связность. Заменяет оба файла конфигурации, сохраняя копию с датой. _kind=`dangerous`, risk_level=`user_write`._
### Переезд на новую машину

- **Переезд на новую машину > Показать состав переезда** (`migration_plan`) — Читает config\migration_plan.yaml и перечисляет строки состава: пак, папку и можно ли развернуть без рук. Ничего не меняет. _kind=`safe`, risk_level=`readonly`._
- **Переезд на новую машину > Проверить доступы после переезда** (`migration_verify`) — Тот же разбор путей, что и в паке SSH: каждый ключ, known_hosts и прокси, названные в конфигурации ssh и rclone. _kind=`safe`, risk_level=`readonly`._
- **Переезд на новую машину > Экспорт переезда** (`migration_export`) — Идёт по составу, зовёт паки и собирает всё в output\migration\<машина>_<время> вместе с описью. Содержит ЗАКРЫТЫЕ КЛЮЧИ и пароли Wi-Fi открытым текстом. _kind=`dangerous`, risk_level=`secret_export`._
- **Переезд на новую машину > Импорт переезда** (`migration_import`) — Читает опись из input, отдаёт каждую строку своему паку и заканчивает проверкой доступов. Заменяет SSH-материал этого пользователя и добавляет профили Wi-Fi. _kind=`dangerous`, risk_level=`system_change`._
- **Переезд на новую машину > Открыть папку переезда** (`migration_open_folder`) — Открыть output\migration; ничего не собирает. _kind=`safe`, risk_level=`readonly`._
### Утилиты

- **Утилиты > Документация PDF > Показать план PDF export** (`docs_pdf_plan`) — Dry run: показать Markdown-источники и целевые PDF без записи файлов. _kind=`safe`, risk_level=`readonly`._
- **Утилиты > Документация PDF > Сгенерировать PDF документации** (`docs_pdf_render`) — Сгенерировать PDF для root guides, docs\*.md, GitHub README и optional agent instructions в docs\PDF. Markdown остаётся source of truth. _kind=`safe`, risk_level=`project_write`._
- **Утилиты > Документация PDF > Открыть папку docs PDF** (`docs_pdf_open`) — Открыть docs\PDF. _kind=`safe`, risk_level=`readonly`._
- **Утилиты > Версия ripgrep** (`ripgrep_status`) — Показать версию проектного ripgrep\rg.exe. _kind=`safe`, risk_level=`readonly`._
- **Утилиты > Открыть папку утилиты** (`open_tool_folder`) — Открыть project-local utility folder. _kind=`safe`, risk_level=`readonly`._
### Обслуживание и очистка

- **Обслуживание и очистка > Очистка Codex > Аудит Codex** (`codex_nuke_audit`) — Проверить артефакты Codex Desktop без изменений. _kind=`safe`, risk_level=`readonly`._
- **Обслуживание и очистка > Очистка Codex > Симуляция очистки Codex** (`codex_nuke_dryrun`) — Показать план очистки Codex без изменений системы. _kind=`safe`, risk_level=`readonly`._
- **Обслуживание и очистка > Очистка Codex > Сброс сессии Codex** (`codex_nuke_session_reset`) — Мягкий reset: остановить Codex и очистить sessions/cache, сохранив auth, config и install. _kind=`dangerous`, risk_level=`user_write`._
- **Обслуживание и очистка > Очистка Codex > Полная очистка Codex, сохранить CLI state** (`codex_nuke_keep_cli_state`) — Удалить артефакты Codex Desktop, сохранив ~/.codex для Codex CLI state. Сначала используй аудит/dry-run и проверь scope очистки. _kind=`dangerous`, risk_level=`destructive`._
- **Обслуживание и очистка > Очистка Codex > Полная очистка Codex** (`codex_nuke_full`) — Полное удаление Codex Desktop, включая общий пользовательский state Codex. _kind=`dangerous`, risk_level=`destructive`._
- **Обслуживание и очистка > Очистка Python > Аудит Python** (`python_nuke_audit`) — Проверить Python installs, launchers, caches, переменные среды и PATH entries без изменений. _kind=`safe`, risk_level=`readonly`._
- **Обслуживание и очистка > Очистка Python > Симуляция очистки Python** (`python_nuke_dryrun`) — Показать план очистки Python без изменений системы. _kind=`safe`, risk_level=`readonly`._
- **Обслуживание и очистка > Очистка Python > Полная очистка Python** (`python_nuke_full`) — Удалить распространённые Python installs, launchers, pip cache, переменные среды и PATH entries. Сначала используй аудит/dry-run и проверь, какие installs попали в scope. _kind=`dangerous`, risk_level=`destructive`._
- **Обслуживание и очистка > Очистка Python > Очистка Python без winget uninstall** (`python_nuke_keep_winget`) — Запустить очистку Python, но пропустить winget uninstall pass. Всё равно чистит launchers/cache/env/PATH в выбранном scope; сначала используй аудит/dry-run. _kind=`dangerous`, risk_level=`destructive`._
- **Обслуживание и очистка > Очистить workspace** (`cleanup_workspace`) — Удалить только файлы внутри управляемой папки workspace. _kind=`dangerous`, risk_level=`destructive`._
### Обслуживание

- **Обслуживание > Очистить I/O** (`cleanup_input_output`) — Удалить содержимое управляемых папок input и output. _kind=`dangerous`, risk_level=`destructive`._

<!-- END GENERATED COMMAND CATALOG -->

## Терминал

Правая панель - это основной журнал операций. Она показывает:

- текущий статус;
- прогресс;
- живой stdout/stderr дочерних PowerShell/CMD процессов;
- итоговый статус операции;
- служебные кнопки папок `ROOT`, `INPUT`, `OUTPUT`, `WORK`, `Logs`, `Report`, `Config`.

В Workbench `Сбросить` возвращает проектные `input/output` без удаления,
а `Удалить` очищает текущие `Источник` и `Назначение` после подтверждения.

Внизу терминала есть быстрый command bar:

- выбор `PowerShell` или `CMD`;
- история последних 200 команд;
- pin/unpin любимых команд;
- выбор рабочей папки через picker;
- выбор файла через picker с подстановкой пути файла в команду.

История хранится здесь:

```text
config\terminal_commands.json
```

## WSL

WSL-раздел построен как мастер, а не просто набор старых wrapper-скриптов.

GUI больше не привязан к старым `Audion_WSL_Block_E` / `Audion_WSL_Block_S`: имя дистрибутива, файл образа и папка установки выбираются прямо в форме. Дефолтная managed-зона для новых WSL-артефактов:

```text
X:\WSL на не-системном fixed-диске, если он доступен
C:\WSL только если кроме C: нет других fixed-дисков
```

Базовые операции:

- показать статус WSL2 и Windows features;
- включить WSL2 features в Windows;
- выполнить `wsl --update`;
- вывести online-дистрибутивы;
- установить выбранный дистрибутив;
- установить локальный `.wsl` образ, например `ubuntu-26.04-wsl-amd64.wsl`, или импортировать tar/vhd/vhdx;
- выбрать установку в system default или в заданную папку;
- использовать пины частых дистрибутивов;
- list/status/shutdown установленных дистрибутивов.

Операции с дистрибутивами вынесены отдельно:

- terminate;
- backup с выбором папки;
- clone с папкой установки;
- move с новой папкой;
- delete/unregister;
- import VHDX in-place;
- restore from backup;
- register all VHDX с dry-run по умолчанию.

## Осторожность

Команды с системными изменениями в manifest помечены как `kind: dangerous`, и GUI требует отдельного подтверждения перед запуском. Дополнительный `risk_level` уточняет тип риска: `readonly`, `project_write`, `user_write`, `system_change`, `destructive`, `secret_export`.

Команды не окрашиваются автоматически только потому, что они `kind: dangerous`: это поле отвечает за подтверждение. Мягкие тона кнопок используются точечно, когда рядом есть выбор разной силы действия, например status/repair/reset или backup/export/restore.

Для операций, которым нужны права администратора, запускайте GUI от имени администратора. Иначе backend-скрипты могут штатно отказать.

При обычном запуске весь GUI уже elevated. Если GUI специально запущен с `AUDION_GUI_NO_ELEVATE=1`, часть сервисов всё равно умеет сама запросить UAC для известных admin-действий и вернуть elevated-log в журнал операции.

Интерактивные destructive wizard-утилиты, например `Audion SSD-NVMe Reset Wizard v4`, открываются во внешней консоли, чтобы сохранить их typed confirmations и не прятать prompt-heavy меню внутри GUI-лога. Встроенные инструменты очистки Codex и Python живут в отдельных папках `tools\codex_nuke` и `tools\python_nuke`; GUI показывает их отдельными блоками и вызывает не через интерактивное `Nuke.cmd`, а напрямую через `Invoke-*.ps1` с выбранным режимом.

## Кодировка терминала

GUI-раннер читает вывод дочерних процессов как bytes и декодирует через fallback:

- UTF-16LE/BE для странного Windows/WSL вывода;
- UTF-8;
- Windows OEM code page;
- locale/mbcs;
- cp866/cp1251.

Это важно для русских строк `netsh`, `wsl`, `reagentc`, PowerShell и старых CMD-утилит.

## Проверка

Минимальная проверка после изменений:

```cmd
runtime\python.exe -m py_compile system_core\ui_nicegui\app.py system_core\services\devops_tools.py system_core\core\jobs.py
runtime\python.exe system_core\ui_nicegui\app.py --smoke
runtime\python.exe system_core\doctor.py
```

Проверка GUI-сервера:

```cmd
runtime\python.exe system_core\ui_nicegui\app.py --host 127.0.0.1 --port 8092 --no-browser
```

Откройте:

```text
http://127.0.0.1:8092/
```

## Дополнительная документация

- `USER_GUIDE_RU.md` - полный пользовательский guide по всем разделам и типовым маршрутам.
- `USER_GUIDE_EN.md` - English user guide.
- `docs/AUDION_DEVOPS_TOOLS_RU.md` - архитектура и правила развития текущего проекта.
- `docs/BITRIX_HOSTS_RU.md` - Bitrix endpoint detect, hosts patch/depatch и bitwise restore.
- `docs/NETWORK_CONNECTIVITY_RU.md` - Network Cleaner, Wi-Fi profiles, SMB login, adapters и proxy.
- `docs/BROWSER_BOOKMARKS_MASTER_RU.md` - Chromium Bookmarks/Favicons master export/import через Workbench SOURCE/TARGET.
- `docs/WSL_TOOLKIT_RU.md` - WSL install/import/backup/restore/move/delete.
- `docs/VIRTUALIZATION_SWITCHER_RU.md` - virtualization modes, Hyper-V/WSL2 и VM diagnostics.
- `docs/DEFAULT_APPS_GUARD_RU.md` - короткий ритуал и тонкости Default Apps Guard.
- `docs/ASSOCIATION_DEFENSE_RU.md` - встроенные приложения Microsoft, AppLocker reinstall-block и снимки ассоциаций.
- `docs/HARDWARE_DRIVER_GUARD_RU.md` - hardware, driver, NVIDIA и storage details.
- `docs/STORAGE_DISK_PROCEDURES_RU.md` - WinRE, SSD/NVMe и disk inventory.
- `docs/OPENSSH_KEYKIT_RU.md` - SSH client/server key backup и restore.
- `docs/CERTIFICATE_KEYKIT_RU.md` - certificate/PFX backup и restore.
- `docs/MAINTENANCE_CLEANUP_RU.md` - Codex/Python nuke и workspace cleanup.
- `docs/MANIFEST_REFERENCE_RU.md` - правила manifest/service слоя GUI.
- `docs/GUI_TREE_REFACTOR_RU.md` - правила tree-навигации и layout.
- `AGENTS.md` - инструкция для будущих AI/Code agents.
- `docs/MEMORY.md` - короткая актуальная память для Claude/agent-контекста.
- `docs/SMOKE_TEST_CHECKLIST_RU.md` - smoke checklist.
- `docs/KNOWN_PITFALLS_RU.md` - типовые ловушки GUI-template/Windows.
