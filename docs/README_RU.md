# Audion DevOps Tools

Audion DevOps Tools - portable GUI-shell для Windows-набора DevOps утилит Audion.

GUI не заменяет существующие CMD/FZF/PowerShell-слои. Он добавляет управляемую оболочку поверх них: поля, списки, checkbox/radio-группы, picker-кнопки, подтверждения, терминальный журнал и быстрый ручной запуск команд.

Интерфейс намеренно остаётся техническим: кнопки короткие и часто English-heavy, видимые описания компактные, а полный Windows-контекст, риск, откат и официальные RU-термины раскрываются в tooltip. Логические рамки показывают пары и pipeline-сценарии вроде `backup / restore`, `export / import`, `block / unblock`; мягкие тона кнопок различают щадящие, обычные и сильные действия.

Audion DevOps Tools не является клоном Chris Titus WinUtil, generic Windows tuner или debloater. Проект закрывает недостающий тонкий программно-аппаратный слой вокруг Windows, WSL, virtualization, hardware policy, storage, network, default-app policy и secrets. Это рабочая кабина истребителя для контролируемых системных операций: явные параметры, backup, risk labels, подтверждения и logs.

## Возможности

- Desktop GUI на NiceGUI + pywebview.
- Portable Python runtime в `runtime\`.
- Единый WSL Toolkit: WSL2 features/update, online distro install, установка из `.wsl`/tar/vhd, list/status/shutdown, backup/clone/move/delete, import/restore, register all VHDX.
- Virtualization switcher: read-only status/optimization diagnostics, режим Hyper-V/WSL2, быстрые сторонние VM, WHP coexist, Hyper-V/Sandbox toggles с BCD backup и reboot warnings.
- Network Cleaner: диагностика, backup/restore состояния сети, proxy.
- Connectivity / «Подключение и адаптеры»: адаптеры, SMB-вход к Windows file sharing через внешнюю `net use` консоль, sticky Wi-Fi пара, быстрые LAN/Wi-Fi режимы и все Wi-Fi profile-операции (status/connect/export/import).
- Hosts and Bitrix profiles with local endpoint detection, DNS/hosts status, custom/auto-scanned TCP ports, managed hosts metadata and bitwise depatch from backup.
- Default Apps Guard: snapshot/rescan Windows default associations, HKLM policy guard и current/profile/policy comparison.
- Association Defense: встроенные приложения Microsoft (убрать / вернуть / держать удалёнными), AppLocker reinstall-block, Edge/Defender policy guards, снимки ассоциаций (общий и по группам) и отслеживание их смены.
- Hardware / Driver Guard: Windows Update driver policy block, NVIDIA driver install restrictions, Driver Store backup/restore, NVIDIA HDMI/DP Audio control and disk procedures: disk inventory, WinRE, SSD/NVMe wizard launcher.
- Utilities: AI CLI Backup для бэкапа, восстановления и слияния памяти данных Claude Code и Codex, OpenSSH KeyKit и Certificate KeyKit для sensitive key/certificate export/import, «Доступы из конфигурации» и «Переезд на новую машину» для сборки всех доступов в одну папку с описью, Documentation PDF export, Ubuntu Dev Installer materials, bundled ripgrep and quick folder shortcuts.
- Theme catalog в `config\ui_colors.yaml` и переключатель темы в шапке.
- Логические UI-блоки, компактные описания и полные tooltip для сложных Windows/policy/secrets-сценариев.
- Live terminal с декодированием Windows/WSL вывода без кракозябр.

## Официальная основа

Проект старается оборачивать документированные Windows admin/deployment механизмы, а не ломать систему прямой правкой защищённых ключей:

- Default Apps Guard: DISM default app associations + HKLM policy `DefaultAssociationsConfiguration`; снимки ассоциаций текущего пользователя живут в `Association Defense` и только читают реестр.
- Windows Home/Core не считается гарантированным target для Default Apps Guard policy: GUI показывает edition и по умолчанию блокирует apply на неподдержанной редакции.
- WSL Toolkit: официальный `wsl.exe`.
- Wi-Fi profiles: официальный `netsh wlan`.
- Virtualization switcher: `bcdedit`, DISM optional features, `Win32_DeviceGuard` status, power-plan/Defender/.wslconfig diagnostics и WSL VHDX placement.
- Certificate KeyKit: PowerShell PKI cmdlets поверх `Cert:\` stores.
- Hardware / Driver Guard: documented `ExcludeWUDriversInQualityUpdate` policy and Device Installation Restrictions.
- Storage/WinRE/DISM/features inside Hardware: штатные Windows admin tools с backup/status/confirmation вокруг опасных действий.
- OpenSSH KeyKit, Certificate KeyKit PFX backups и Wi-Fi-key backups are sensitive export workflows; generated archives must be stored as secrets.
- `UserChoice` hashes и UCPD не обходятся вручную.

См. Microsoft docs: [ApplicationDefaults Policy CSP](https://learn.microsoft.com/en-us/windows/client-management/mdm/policy-csp-applicationdefaults), [DISM default app associations](https://learn.microsoft.com/en-us/windows-hardware/manufacture/desktop/dism-default-application-association-servicing-command-line-options?view=windows-11), [netsh wlan](https://learn.microsoft.com/en-us/windows-server/administration/windows-commands/netsh-wlan), [WSL basic commands](https://learn.microsoft.com/en-us/windows/wsl/basic-commands).

Hardware scripts are project-local under `system_core\windows_driver_guard` and `system_core\nvidia_audio`; old standalone external folders are not runtime dependencies.

### Default Apps Guard: короткий сценарий

После чистой установки Windows и ручной настройки defaults: `Проверить защиту defaults`, `Перезаписать эталон текущими defaults`, оставить `Remove Suggested=true`, `Включить / починить защиту defaults`, затем sign out/sign in или reboot и снова `Проверить защиту defaults`. Подробный список тонкостей Windows и gotchas: `docs\DEFAULT_APPS_GUARD_RU.md`.

### Bitrix Hosts: короткий сценарий

Текущий default: `portal.itpgrad.ru -> 192.168.0.130`, port `443`. Ритуал: `Detect current endpoint` -> `Status / DNS / ports` -> `Enable override` -> после работы `Disable override`. `Disable override` восстанавливает `hosts` побитово из `backup=hosts_prepatch_....bak`, указанного в managed-комментарии. Подробно: `docs\BITRIX_HOSTS_RU.md`.

## Запуск

```bat
launcher_gui.cmd
```

Обычный запуск запрашивает UAC и поднимает весь GUI от имени администратора. Это удобно для DISM, hosts, сетевых адаптеров, diskpart/WinRE и WSL setup.

Короткие модульные входы:

```bat
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

WSL, Bitrix, Default Apps и Association Defense launchers используют `system_core\cli_operation.py`, то есть идут через тот же manifest/service layer, что и GUI. Cleanup launchers являются корневыми wrappers для встроенных `tools\...\Nuke.cmd` с UAC elevation и typed confirmations.

Read-only/debug запуск без UAC:

```bat
set AUDION_GUI_NO_ELEVATE=1
launcher_gui.cmd
```

## Обслуживание

Создать недостающие рабочие папки:

```bat
init_folders.cmd
```

Деликатная очистка проекта:

```bat
cleanup_project.cmd
```

Cleaner оставляет скрипты, конфиги, документацию, tracked license docs и сами папки. Он удаляет generated/downloaded payloads: `runtime`, `wheelhouse`, `release`, `install\download`, `system_core\powershell`, `system_core\fzf.exe`, logs, reports, input/output/workspace/data contents и Python-кэши.

Проверить план без удаления:

```bat
cleanup_project.cmd /DRYRUN /Y
```

## Проверка

```bat
runtime\python.exe -m py_compile system_core\ui_nicegui\app.py system_core\services\devops_tools.py system_core\core\jobs.py
runtime\python.exe system_core\ui_nicegui\app.py --smoke
runtime\python.exe system_core\doctor.py
```

## Документация

- `README_AUDION_DEVOPS_TOOLS_RU.md`
- `USER_GUIDE_RU.md`
- `USER_GUIDE_EN.md`
- `AGENTS.md`
- `docs\AUDION_DEVOPS_TOOLS_RU.md`
- `docs\BITRIX_HOSTS_RU.md`
- `docs\NETWORK_CONNECTIVITY_RU.md`
- `docs\WSL_TOOLKIT_RU.md`
- `docs\VIRTUALIZATION_SWITCHER_RU.md`
- `docs\DEFAULT_APPS_GUARD_RU.md`
- `docs\ASSOCIATION_DEFENSE_RU.md`
- `docs\HARDWARE_DRIVER_GUARD_RU.md`
- `docs\STORAGE_DISK_PROCEDURES_RU.md`
- `docs\OPENSSH_KEYKIT_RU.md`
- `docs\CERTIFICATE_KEYKIT_RU.md`
- `docs\MAINTENANCE_CLEANUP_RU.md`
- `docs\MANIFEST_REFERENCE_RU.md`
- `docs\GUI_TREE_REFACTOR_RU.md`
- `docs\MEMORY.md`
- `docs\SMOKE_TEST_CHECKLIST_RU.md`
- `docs\KNOWN_PITFALLS_RU.md`
## Канонические названия Workbench

Workbench использует единый публичный словарь Audion Image Tools во всех проектах. Кнопки всегда расположены и называются одинаково: **Источник**, **Добавить файл...**, **Назначение**, **Сбросить**, **Удалить**, **Список**.

`Сбросить` возвращает проектные `input/output` и не удаляет файлы; `Удалить` очищает текущие `Источник` и `Назначение` только после подтверждения. В английском интерфейсе точные названия: **Source**, **Add file...**, **Target**, **Reset**, **Delete**, **List**. Варианты `Цель`, `Очистить`, `Destination` и `Clear` для этих элементов Workbench не используются.
