# WSL Toolkit

Практический runbook для WSL-раздела Audion DevOps Tools: установка, импорт, перенос, backup/restore, VHDX-регистрация и Linux bootstrap.

Полный список GUI-параметров смотри в `USER_GUIDE_RU.md` в блоке `Справочник параметров -> WSL Toolkit`.

## Главное Правило

WSL Toolkit работает через штатный `wsl.exe` и project-local service layer. Не смешивай ручные `wsl --import`, `wsl --unregister`, копирование VHDX и кнопки GUI в одном сценарии без свежего статуса.

Перед опасными действиями:

1. Запусти `System WSL2 status` или `WSL status`.
2. Убедись, что выбран правильный дистрибутив.
3. Сделай `Backup distro`, если дистрибутив содержит рабочие ключи, конфиги или код.
4. Для VHD backup дождись shutdown WSL; это защищает от `ERROR_SHARING_VIOLATION`.
5. После move/restore/delete перечитай статус, а не доверяй старому списку.

## Базовая Установка

Обычный порядок для новой машины:

1. `System WSL2 status`.
2. `Enable WSL2 features`, если компоненты не включены.
3. Reboot.
4. `Update WSL2`.
5. `Installable distros`.
6. `Install distro`.
7. `Installed distros`.
8. `WSL status`.

Параметр `Install location mode` важен: custom location нужен, если VHDX должен лежать не в профиле пользователя, например на быстром диске `S:\WSL\VHDX`.

`No launch` полезен для автоматизированной установки: дистрибутив ставится, но первый interactive launch не открывается сразу.

## Установка Из Образа

`Install from image file` нужен для `.wsl`, `.tar`, `.tar.gz`, `.vhd` или `.vhdx`.

Проверяй:

- `Image file` - реальный образ, а не папка рядом с ним.
- `Distro name` - уникальное имя WSL-дистрибутива.
- `Install location` - папка, где будет жить импортированный дистрибутив.
- `Import type` - обычный import или VHDX in-place, если образ должен остаться рабочим диском.

VHDX in-place не стоит использовать на случайных downloaded файлах без понимания происхождения. Это рабочий диск WSL, а не архив.

## Linux Configuration

Этот блок меняет уже существующий Linux-дистрибутив:

- `Package update` - apt update/upgrade и repair-сценарии.
- `Account bootstrap` - создание пользователя, sudo/wheel и default WSL user.
- `Dev packages` - установка выбранных групп dev-пакетов.
- `MC skin` - Midnight Commander skin.
- `Neovim base` - базовая конфигурация Neovim.

Для apt-сценариев модуль умеет обходить типичные проблемы DNS/proxy внутри WSL, но это не замена диагностике сети Windows. Если apt не видит интернет, сначала проверь `Network Cleaner` и `Connectivity`.

## Backup / Clone / Move / Delete

`Backup distro` экспортирует выбранный дистрибутив в tar или VHD. Такой backup может содержать SSH keys, tokens, browser cookies, git credentials, `.npmrc`, `.pypirc`, cloud configs и рабочий код. Храни его как secret.

`Clone distro` делает новый дистрибутив через export/import. Используй для ветки экспериментов, а не для "быстрого копирования папки".

`Move distro` тоже идёт через export/import. Это destructive-операция: старое место может быть unregister/remove после успешного переноса. Делай backup и проверяй новый launch до удаления старого состояния.

`Delete distro` выполняет unregister. Это необратимо для выбранного WSL instance, если нет отдельного backup.

## Restore И VHDX Batch

`Restore from backup` поднимает дистрибутив из ранее созданного tar/VHD backup.

`Import VHDX in-place` регистрирует VHDX как WSL-дистрибутив без распаковки. Это удобно для переносимых VHDX, но опасно тем, что файл сразу становится рабочим диском.

`Register all VHDX` сканирует выбранную папку и регистрирует пачку VHDX. Используй только на понятной структуре, иначе получишь лишние WSL entries с неочевидными именами.

## Где Лежат Данные

Типовые рабочие места:

```text
backup\wsl
output\wsl
S:\WSL\VHDX
```

Точные пути зависят от выбранных параметров и текущего profile/config проекта.

## Smoke

Минимальная проверка после изменения WSL Toolkit:

```text
System WSL2 status      -> read-only status без ошибок
Installed distros       -> список дистрибутивов
Backup distro           -> backup created, log содержит путь
Restore from backup     -> новый distro name появляется в WSL status
Move distro             -> старый/новый путь понятны в log
Delete distro           -> требует осознанного target, после unregister не числится
```

