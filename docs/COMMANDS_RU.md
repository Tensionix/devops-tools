# Audion DevOps Tools — справочник команд

[English](COMMANDS_EN.md) · [О программе](README_RU.md) · [Руководство](USER_GUIDE_RU.md)

**Содержание**

- [Среда выполнения и оболочка > Предварительный снимок](#среда-выполнения-и-оболочка--предварительный-снимок)
- [Среда выполнения и оболочка > Статус PowerShell](#среда-выполнения-и-оболочка--статус-powershell)
- [Среда выполнения и оболочка > Проверить Windows Long Paths](#среда-выполнения-и-оболочка--проверить-windows-long-paths)
- [Среда выполнения и оболочка > Включить Windows Long Paths](#среда-выполнения-и-оболочка--включить-windows-long-paths)
- [Среда выполнения и оболочка > Включить Git Long Paths](#среда-выполнения-и-оболочка--включить-git-long-paths)
- [Среда выполнения и оболочка > Установить портативный PowerShell](#среда-выполнения-и-оболочка--установить-портативный-powershell)
- [Browser Bookmarks Master > Статус](#browser-bookmarks-master--статус)
- [Browser Bookmarks Master > Очистить локальный Favicons cache](#browser-bookmarks-master--очистить-локальный-favicons-cache)
- [Browser Bookmarks Master > Экспорт эталона в Workbench TARGET](#browser-bookmarks-master--экспорт-эталона-в-workbench-target)
- [Browser Bookmarks Master > Импорт эталона из Workbench SOURCE](#browser-bookmarks-master--импорт-эталона-из-workbench-source)
- [Browser Bookmarks Master > Перенести эталон между браузерами](#browser-bookmarks-master--перенести-эталон-между-браузерами)
- [Browser Bookmarks Master > Открыть локальные safety backups](#browser-bookmarks-master--открыть-локальные-safety-backups)
- [Очистка сети > Снимок статуса](#очистка-сети--снимок-статуса)
- [Очистка сети > Полный backup сети](#очистка-сети--полный-backup-сети)
- [Очистка сети > Полный backup + Wi-Fi ключи](#очистка-сети--полный-backup--wi-fi-ключи)
- [Очистка сети > Восстановить backup сети > Восстановить последний backup](#очистка-сети--восстановить-backup-сети--восстановить-последний-backup)
- [Очистка сети > Восстановить backup сети > Восстановить выбранный backup](#очистка-сети--восстановить-backup-сети--восстановить-выбранный-backup)
- [Очистка сети > Профили ремонта > Легкий ремонт](#очистка-сети--профили-ремонта--легкий-ремонт)
- [Очистка сети > Профили ремонта > Стандартный ремонт](#очистка-сети--профили-ремонта--стандартный-ремонт)
- [Очистка сети > Профили ремонта > Жёсткий ремонт](#очистка-сети--профили-ремонта--жёсткий-ремонт)
- [Очистка сети > Прокси > Статус прокси](#очистка-сети--прокси--статус-прокси)
- [Очистка сети > Прокси > Отключить прокси пользователя](#очистка-сети--прокси--отключить-прокси-пользователя)
- [Очистка сети > Прокси > Сбросить WinHTTP proxy](#очистка-сети--прокси--сбросить-winhttp-proxy)
- [Очистка сети > Открыть backup](#очистка-сети--открыть-backup)
- [Подключение и адаптеры > Wi-Fi профили > Статус Wi-Fi](#подключение-и-адаптеры--wi-fi-профили--статус-wi-fi)
- [Подключение и адаптеры > Wi-Fi профили > Подключить профиль](#подключение-и-адаптеры--wi-fi-профили--подключить-профиль)
- [Подключение и адаптеры > Wi-Fi профили > Автоподключение профиля](#подключение-и-адаптеры--wi-fi-профили--автоподключение-профиля)
- [Подключение и адаптеры > Wi-Fi профили > Экспорт профилей](#подключение-и-адаптеры--wi-fi-профили--экспорт-профилей)
- [Подключение и адаптеры > Wi-Fi профили > Импорт профилей > Импорт XML файла](#подключение-и-адаптеры--wi-fi-профили--импорт-профилей--импорт-xml-файла)
- [Подключение и адаптеры > Wi-Fi профили > Импорт профилей > Импорт папки XML](#подключение-и-адаптеры--wi-fi-профили--импорт-профилей--импорт-папки-xml)
- [Подключение и адаптеры > SMB вход в сеть](#подключение-и-адаптеры--smb-вход-в-сеть)
- [Подключение и адаптеры > Действие адаптера](#подключение-и-адаптеры--действие-адаптера)
- [Подключение и адаптеры > LAN/Wi-Fi переключатель](#подключение-и-адаптеры--lanwi-fi-переключатель)
- [Подключение и адаптеры > Wi-Fi sticky-пара](#подключение-и-адаптеры--wi-fi-sticky-пара)
- [WSL Toolkit > Базовые и установка > Статус WSL2 в системе](#wsl-toolkit--базовые-и-установка--статус-wsl2-в-системе)
- [WSL Toolkit > Базовые и установка > Установить WSL2 в Windows](#wsl-toolkit--базовые-и-установка--установить-wsl2-в-windows)
- [WSL Toolkit > Базовые и установка > Обновить WSL2](#wsl-toolkit--базовые-и-установка--обновить-wsl2)
- [WSL Toolkit > Базовые и установка > Список для установки](#wsl-toolkit--базовые-и-установка--список-для-установки)
- [WSL Toolkit > Базовые и установка > Установить дистрибутив](#wsl-toolkit--базовые-и-установка--установить-дистрибутив)
- [WSL Toolkit > Базовые и установка > Установить из файла образа](#wsl-toolkit--базовые-и-установка--установить-из-файла-образа)
- [WSL Toolkit > Базовые и установка > Список установленных](#wsl-toolkit--базовые-и-установка--список-установленных)
- [WSL Toolkit > Базовые и установка > Статус WSL](#wsl-toolkit--базовые-и-установка--статус-wsl)
- [WSL Toolkit > Базовые и установка > Shutdown WSL](#wsl-toolkit--базовые-и-установка--shutdown-wsl)
- [WSL Toolkit > Linux-конфигурация > Package update](#wsl-toolkit--linux-конфигурация--package-update)
- [WSL Toolkit > Linux-конфигурация > Учётка Linux](#wsl-toolkit--linux-конфигурация--учётка-linux)
- [WSL Toolkit > Linux-конфигурация > Dev-пакеты](#wsl-toolkit--linux-конфигурация--dev-пакеты)
- [WSL Toolkit > Linux-конфигурация > Micro baseline](#wsl-toolkit--linux-конфигурация--micro-baseline)
- [WSL Toolkit > Linux-конфигурация > MC skin](#wsl-toolkit--linux-конфигурация--mc-skin)
- [WSL Toolkit > Linux-конфигурация > Neovim base](#wsl-toolkit--linux-конфигурация--neovim-base)
- [WSL Toolkit > Ubuntu Dev Installer Kit > Открыть папку kit](#wsl-toolkit--ubuntu-dev-installer-kit--открыть-папку-kit)
- [WSL Toolkit > Ubuntu Dev Installer Kit > Открыть README RU](#wsl-toolkit--ubuntu-dev-installer-kit--открыть-readme-ru)
- [WSL Toolkit > Ubuntu Dev Installer Kit > Открыть Btrfs guide](#wsl-toolkit--ubuntu-dev-installer-kit--открыть-btrfs-guide)
- [WSL Toolkit > Ubuntu Dev Installer Kit > Открыть installer script](#wsl-toolkit--ubuntu-dev-installer-kit--открыть-installer-script)
- [WSL Toolkit > Ubuntu Dev Installer Kit > Открыть NVMe prep script](#wsl-toolkit--ubuntu-dev-installer-kit--открыть-nvme-prep-script)
- [WSL Toolkit > Ubuntu Dev Installer Kit > Открыть списки пакетов](#wsl-toolkit--ubuntu-dev-installer-kit--открыть-списки-пакетов)
- [WSL Toolkit > Действия с дистрибутивом > Остановить дистрибутив](#wsl-toolkit--действия-с-дистрибутивом--остановить-дистрибутив)
- [WSL Toolkit > Действия с дистрибутивом > Backup дистрибутива](#wsl-toolkit--действия-с-дистрибутивом--backup-дистрибутива)
- [WSL Toolkit > Действия с дистрибутивом > Клонировать дистрибутив](#wsl-toolkit--действия-с-дистрибутивом--клонировать-дистрибутив)
- [WSL Toolkit > Действия с дистрибутивом > Перенести дистрибутив](#wsl-toolkit--действия-с-дистрибутивом--перенести-дистрибутив)
- [WSL Toolkit > Действия с дистрибутивом > Удалить дистрибутив](#wsl-toolkit--действия-с-дистрибутивом--удалить-дистрибутив)
- [WSL Toolkit > Import и restore > Import VHDX in-place](#wsl-toolkit--import-и-restore--import-vhdx-in-place)
- [WSL Toolkit > Import и restore > Restore из backup](#wsl-toolkit--import-и-restore--restore-из-backup)
- [WSL Toolkit > Регистрация VHDX пачкой > Зарегистрировать все VHDX](#wsl-toolkit--регистрация-vhdx-пачкой--зарегистрировать-все-vhdx)
- [Виртуализация > Статус виртуализации](#виртуализация--статус-виртуализации)
- [Виртуализация > Статус оптимизации](#виртуализация--статус-оптимизации)
- [Виртуализация > Режим: Hyper-V / WSL2](#виртуализация--режим-hyper-v--wsl2)
- [Виртуализация > Режим: Сторонние VM (быстро)](#виртуализация--режим-сторонние-vm-быстро)
- [Виртуализация > Режим: Сосуществование (WHP)](#виртуализация--режим-сосуществование-whp)
- [Виртуализация > Включить Hyper-V](#виртуализация--включить-hyper-v)
- [Виртуализация > Выключить Hyper-V](#виртуализация--выключить-hyper-v)
- [Виртуализация > Включить Windows Sandbox](#виртуализация--включить-windows-sandbox)
- [Виртуализация > Выключить Windows Sandbox](#виртуализация--выключить-windows-sandbox)
- [Hosts и Bitrix > Найти текущий endpoint](#hosts-и-bitrix--найти-текущий-endpoint)
- [Hosts и Bitrix > Статус / DNS / ports](#hosts-и-bitrix--статус--dns--ports)
- [Hosts и Bitrix > Включить override](#hosts-и-bitrix--включить-override)
- [Hosts и Bitrix > Выключить override](#hosts-и-bitrix--выключить-override)
- [Hosts и Bitrix > Восстановить hosts](#hosts-и-bitrix--восстановить-hosts)
- [Приложения по умолчанию > Политика](#приложения-по-умолчанию--политика)
- [Приложения по умолчанию > Microsoft](#приложения-по-умолчанию--microsoft)
- [Приложения по умолчанию > Edge](#приложения-по-умолчанию--edge)
- [Приложения по умолчанию > Отслеживание](#приложения-по-умолчанию--отслеживание)
- [Приложения по умолчанию > Снимок](#приложения-по-умолчанию--снимок)
- [Приложения по умолчанию > Группы](#приложения-по-умолчанию--группы)
- [Приложения по умолчанию > Общий отчёт](#приложения-по-умолчанию--общий-отчёт)
- [Hardware > Driver/Firmware Audit](#hardware--driverfirmware-audit)
- [Hardware > Материалы Driver/Firmware Audit > Открыть папку аддона](#hardware--материалы-driverfirmware-audit--открыть-папку-аддона)
- [Hardware > Материалы Driver/Firmware Audit > Открыть README](#hardware--материалы-driverfirmware-audit--открыть-readme)
- [Hardware > Driver Update Blocker > Windows Update driver policy > Проверить защиту драйверов](#hardware--driver-update-blocker--windows-update-driver-policy--проверить-защиту-драйверов)
- [Hardware > Driver Update Blocker > Windows Update driver policy > Блокировать драйверы Windows Update](#hardware--driver-update-blocker--windows-update-driver-policy--блокировать-драйверы-windows-update)
- [Hardware > Driver Update Blocker > Windows Update driver policy > Разблокировать драйверы Windows Update](#hardware--driver-update-blocker--windows-update-driver-policy--разблокировать-драйверы-windows-update)
- [Hardware > Driver Update Blocker > Windows Update driver policy > Открыть policy backups](#hardware--driver-update-blocker--windows-update-driver-policy--открыть-policy-backups)
- [Hardware > Driver Update Blocker > HWID-защита драйвера устройства > Проверить текущий lock](#hardware--driver-update-blocker--hwid-защита-драйвера-устройства--проверить-текущий-lock)
- [Hardware > Driver Update Blocker > HWID-защита драйвера устройства > 1. Разблокировать перед обновлением](#hardware--driver-update-blocker--hwid-защита-драйвера-устройства--1-разблокировать-перед-обновлением)
- [Hardware > Driver Update Blocker > HWID-защита драйвера устройства > 2. Заблокировать после установки](#hardware--driver-update-blocker--hwid-защита-драйвера-устройства--2-заблокировать-после-установки)
- [Hardware > Driver Update Blocker > Аварийный rank repair по HWID > Проверить rank target](#hardware--driver-update-blocker--аварийный-rank-repair-по-hwid--проверить-rank-target)
- [Hardware > Driver Update Blocker > Аварийный rank repair по HWID > Починить driver rank по HWID](#hardware--driver-update-blocker--аварийный-rank-repair-по-hwid--починить-driver-rank-по-hwid)
- [Hardware > Driver Update Blocker > NVIDIA driver install restrictions > Блокировать NVIDIA driver installs](#hardware--driver-update-blocker--nvidia-driver-install-restrictions--блокировать-nvidia-driver-installs)
- [Hardware > Driver Update Blocker > NVIDIA driver install restrictions > Разблокировать NVIDIA driver installs](#hardware--driver-update-blocker--nvidia-driver-install-restrictions--разблокировать-nvidia-driver-installs)
- [Hardware > Driver Update Blocker > Driver Store backups > Сохранить Driver Store manifest](#hardware--driver-update-blocker--driver-store-backups--сохранить-driver-store-manifest)
- [Hardware > Driver Update Blocker > Driver Store backups > Экспортировать установленные драйверы](#hardware--driver-update-blocker--driver-store-backups--экспортировать-установленные-драйверы)
- [Hardware > Driver Update Blocker > Driver Store backups > Восстановить экспортированные драйверы](#hardware--driver-update-blocker--driver-store-backups--восстановить-экспортированные-драйверы)
- [Hardware > Driver Update Blocker > Driver Store backups > Открыть driver backups](#hardware--driver-update-blocker--driver-store-backups--открыть-driver-backups)
- [Hardware > Driver Update Blocker > Открыть папку Driver Update Blocker](#hardware--driver-update-blocker--открыть-папку-driver-update-blocker)
- [Hardware > NVIDIA HDMI/DP Audio > Статус NVIDIA audio](#hardware--nvidia-hdmidp-audio--статус-nvidia-audio)
- [Hardware > NVIDIA HDMI/DP Audio > Экспортировать NVIDIA audio IDs](#hardware--nvidia-hdmidp-audio--экспортировать-nvidia-audio-ids)
- [Hardware > NVIDIA HDMI/DP Audio > Отключить NVIDIA HDMI/DP audio](#hardware--nvidia-hdmidp-audio--отключить-nvidia-hdmidp-audio)
- [Hardware > NVIDIA HDMI/DP Audio > Включить NVIDIA HDMI/DP audio](#hardware--nvidia-hdmidp-audio--включить-nvidia-hdmidp-audio)
- [Hardware > NVIDIA HDMI/DP Audio > Policy-block NVIDIA HDMI/DP audio](#hardware--nvidia-hdmidp-audio--policy-block-nvidia-hdmidp-audio)
- [Hardware > NVIDIA HDMI/DP Audio > Снять policy-block NVIDIA HDMI/DP audio](#hardware--nvidia-hdmidp-audio--снять-policy-block-nvidia-hdmidp-audio)
- [Hardware > NVIDIA HDMI/DP Audio > Открыть NVIDIA audio output](#hardware--nvidia-hdmidp-audio--открыть-nvidia-audio-output)
- [Hardware > NVIDIA HDMI/DP Audio > Открыть NVIDIA audio backup](#hardware--nvidia-hdmidp-audio--открыть-nvidia-audio-backup)
- [Hardware > NVIDIA HDMI/DP Audio > Открыть папку NVIDIA audio tool](#hardware--nvidia-hdmidp-audio--открыть-папку-nvidia-audio-tool)
- [Hardware > Накопители / дисковые процедуры > Инвентаризация дисков](#hardware--накопители--дисковые-процедуры--инвентаризация-дисков)
- [Hardware > Накопители / дисковые процедуры > Детали выбранного диска](#hardware--накопители--дисковые-процедуры--детали-выбранного-диска)
- [Hardware > Накопители / дисковые процедуры > Запустить SSD/NVMe wizard](#hardware--накопители--дисковые-процедуры--запустить-ssdnvme-wizard)
- [Hardware > Накопители / дисковые процедуры > Открыть папку SSD/NVMe](#hardware--накопители--дисковые-процедуры--открыть-папку-ssdnvme)
- [Hardware > Накопители / дисковые процедуры > Статус WinRE layout](#hardware--накопители--дисковые-процедуры--статус-winre-layout)
- [Hardware > Накопители / дисковые процедуры > Запустить WinRE wizard](#hardware--накопители--дисковые-процедуры--запустить-winre-wizard)
- [OpenSSH KeyKit > Проверить связность доступов](#openssh-keykit--проверить-связность-доступов)
- [OpenSSH KeyKit > Экспорт client SSH keys](#openssh-keykit--экспорт-client-ssh-keys)
- [OpenSSH KeyKit > Экспорт client + server SSH keys](#openssh-keykit--экспорт-client--server-ssh-keys)
- [OpenSSH KeyKit > Импорт client SSH keys](#openssh-keykit--импорт-client-ssh-keys)
- [OpenSSH KeyKit > Импорт client + server SSH keys](#openssh-keykit--импорт-client--server-ssh-keys)
- [OpenSSH KeyKit > Открыть папку скриптов KeyKit](#openssh-keykit--открыть-папку-скриптов-keykit)
- [Бэкап AI CLI > Бэкап (экспорт)](#бэкап-ai-cli--бэкап-экспорт)
- [Бэкап AI CLI > Восстановить (импорт)](#бэкап-ai-cli--восстановить-импорт)
- [Бэкап AI CLI > Объединение памяти](#бэкап-ai-cli--объединение-памяти)
- [Бэкап AI CLI > Открыть папку инструмента](#бэкап-ai-cli--открыть-папку-инструмента)
- [Сертификаты (экспорт/импорт) > Статус сертификатов](#сертификаты-экспортимпорт--статус-сертификатов)
- [Сертификаты (экспорт/импорт) > Экспорт personal ключей в PFX](#сертификаты-экспортимпорт--экспорт-personal-ключей-в-pfx)
- [Сертификаты (экспорт/импорт) > Экспорт store в SST (публично)](#сертификаты-экспортимпорт--экспорт-store-в-sst-публично)
- [Сертификаты (экспорт/импорт) > Импорт PFX](#сертификаты-экспортимпорт--импорт-pfx)
- [Сертификаты (экспорт/импорт) > Импорт всех PFX из папки](#сертификаты-экспортимпорт--импорт-всех-pfx-из-папки)
- [Сертификаты (экспорт/импорт) > Импорт сертификата / CA](#сертификаты-экспортимпорт--импорт-сертификата--ca)
- [Сертификаты (экспорт/импорт) > Открыть папку экспорта сертификатов](#сертификаты-экспортимпорт--открыть-папку-экспорта-сертификатов)
- [Шрифты пользователя > Показать мои шрифты](#шрифты-пользователя--показать-мои-шрифты)
- [Шрифты пользователя > Экспорт моих шрифтов](#шрифты-пользователя--экспорт-моих-шрифтов)
- [Шрифты пользователя > Импорт шрифтов](#шрифты-пользователя--импорт-шрифтов)
- [Шрифты пользователя > Открыть папку шрифтов](#шрифты-пользователя--открыть-папку-шрифтов)
- [Среда оболочки > Показать файлы оболочки](#среда-оболочки--показать-файлы-оболочки)
- [Среда оболочки > Экспорт файлов оболочки](#среда-оболочки--экспорт-файлов-оболочки)
- [Среда оболочки > Импорт файлов оболочки](#среда-оболочки--импорт-файлов-оболочки)
- [Среда оболочки > Открыть папку среды оболочки](#среда-оболочки--открыть-папку-среды-оболочки)
- [Доступы из конфигурации > Показать, что названо в конфигурации](#доступы-из-конфигурации--показать-что-названо-в-конфигурации)
- [Доступы из конфигурации > Экспорт файлов доступов](#доступы-из-конфигурации--экспорт-файлов-доступов)
- [Доступы из конфигурации > Импорт файлов доступов](#доступы-из-конфигурации--импорт-файлов-доступов)
- [Переезд на новую машину > Показать состав переезда](#переезд-на-новую-машину--показать-состав-переезда)
- [Переезд на новую машину > Проверить доступы после переезда](#переезд-на-новую-машину--проверить-доступы-после-переезда)
- [Переезд на новую машину > Экспорт переезда](#переезд-на-новую-машину--экспорт-переезда)
- [Переезд на новую машину > Импорт переезда](#переезд-на-новую-машину--импорт-переезда)
- [Переезд на новую машину > Открыть папку переезда](#переезд-на-новую-машину--открыть-папку-переезда)
- [Утилиты > Документация PDF > Показать план PDF export](#утилиты--документация-pdf--показать-план-pdf-export)
- [Утилиты > Документация PDF > Сгенерировать PDF документации](#утилиты--документация-pdf--сгенерировать-pdf-документации)
- [Утилиты > Документация PDF > Открыть папку docs PDF](#утилиты--документация-pdf--открыть-папку-docs-pdf)
- [Утилиты > Версия ripgrep](#утилиты--версия-ripgrep)
- [Утилиты > Открыть папку утилиты](#утилиты--открыть-папку-утилиты)
- [Обслуживание и очистка > Очистка Codex > Аудит Codex](#обслуживание-и-очистка--очистка-codex--аудит-codex)
- [Обслуживание и очистка > Очистка Codex > Симуляция очистки Codex](#обслуживание-и-очистка--очистка-codex--симуляция-очистки-codex)
- [Обслуживание и очистка > Очистка Codex > Сброс сессии Codex](#обслуживание-и-очистка--очистка-codex--сброс-сессии-codex)
- [Обслуживание и очистка > Очистка Codex > Полная очистка Codex, сохранить CLI state](#обслуживание-и-очистка--очистка-codex--полная-очистка-codex-сохранить-cli-state)
- [Обслуживание и очистка > Очистка Codex > Полная очистка Codex](#обслуживание-и-очистка--очистка-codex--полная-очистка-codex)
- [Обслуживание и очистка > Очистка Python > Аудит Python](#обслуживание-и-очистка--очистка-python--аудит-python)
- [Обслуживание и очистка > Очистка Python > Симуляция очистки Python](#обслуживание-и-очистка--очистка-python--симуляция-очистки-python)
- [Обслуживание и очистка > Очистка Python > Полная очистка Python](#обслуживание-и-очистка--очистка-python--полная-очистка-python)
- [Обслуживание и очистка > Очистка Python > Очистка Python без winget uninstall](#обслуживание-и-очистка--очистка-python--очистка-python-без-winget-uninstall)
- [Обслуживание и очистка > Очистить workspace](#обслуживание-и-очистка--очистить-workspace)
- [Обслуживание > Очистить I/O](#обслуживание--очистить-io)

Полный перечень операций с параметрами. Читается по необходимости: когда нужно
знать точное имя операции, её поля или что она делает в системе.


Справочник генерируется из `config\tool_manifest.yaml`. Он включает весь текст GUI-подсказок, risk-классификацию, наследуемые поля, defaults и варианты выбора. Практические сценарии и объяснение последствий — в [руководстве](USER_GUIDE_RU.md).

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
