# Network Cleaner И Connectivity

Runbook для диагностики сети, backup/restore, proxy, Wi-Fi профилей, SMB-входа, адаптеров и быстрых LAN/Wi-Fi режимов.

Полный список GUI-параметров смотри в `USER_GUIDE_RU.md` в блоках `Network Cleaner` и `Подключение и адаптеры`.

## Граница Разделов

`Network Cleaner` - это repair/backup/restore слой для состояния сети Windows.

`Connectivity` - это текущая маршрутизация подключения: Wi-Fi profiles, SMB session login, adapters, LAN/Wi-Fi switch и sticky pair.

Если сеть сломана системно, начинай с `Network Cleaner`. Если нужно переключить текущий адаптер или профиль, иди в `Connectivity`.

## Network Cleaner: Безопасный Порядок

1. `Status snapshot`.
2. `Backup network state`.
3. Если нужны Wi-Fi пароли, отдельно `Backup with Wi-Fi keys`.
4. Только после backup запускай repair.
5. После repair снова `Status snapshot`.

`Backup with Wi-Fi keys` экспортирует Wi-Fi XML с `key=clear`. Это secret-output: файл может содержать пароль сети открытым текстом.

## Restore

`Restore latest` и `Restore selected` восстанавливают состояние из snapshot.

Перед rollback проект делает свежий снимок текущего состояния, чтобы даже "сломанная" текущая конфигурация не потерялась.

Restore может затронуть:

- IP/DNS/routes;
- WinHTTP/WinINet proxy;
- firewall export/import;
- Winsock/network registry exports;
- `hosts`;
- Wi-Fi profiles.

После restore проверь статус, DNS и фактическое подключение. Не запускай несколько restore подряд без чтения log.

## Repair Profiles

`Light repair` - самый мягкий:

- DNS flush/register;
- ARP cache clear;
- NetBIOS refresh;
- DHCP renew только для connected DHCP interfaces.

`Standard repair` глубже: Winsock/TCP/IP/proxy/network reset сценарии.

`Nuclear repair` - крайний режим. Используй только после backup и понимания, что текущий сетевой стек уже проще собрать заново.

## Proxy

Proxy-команды разделены:

- user proxy;
- WinHTTP proxy.

Это разные слои Windows. Отключение одного не гарантирует отключение второго. После изменения proxy проверь и browser/app поведение, и CLI-сценарии.

## Wi-Fi Profiles

`Wi-Fi status` показывает adapters и сохранённые profiles.

`Connect profile` подключает выбранный saved profile, опционально через выбранный Wi-Fi adapter.

`Profile autoconnect` меняет `connectionmode=auto/manual`. Это удобно для пары "домашний профиль auto, мобильный hotspot manual".

`Export profiles` сохраняет XML. Clear-text keys включаются только отдельным checkbox.

`Import profiles` добавляет XML обратно через `netsh wlan`.

## SMB / Windows File Sharing

`SMB вход в сеть` открывает внешнюю консоль для входа к компьютеру с общими папками Windows через `net use`.

Что важно:

- это не создание share, не настройка ACL и не включение SMB-сервера;
- цель операции - создать пользовательский SMB-сеанс к существующему компьютеру вида `\\COMPUTER`;
- пароль вводится только во внешней консоли `net use` и не попадает в GUI, logs или cache;
- GUI хранит только пару `computer / user` в `config\smb_network_logins.json`;
- после успешного входа команда показывает `net view \\COMPUTER` и, если включён checkbox, открывает Explorer на `\\COMPUTER`;
- если Windows уже держит SMB-сеанс к тому же компьютеру под другим пользователем, возможна ошибка `1219`; сначала закрой старый сеанс через Windows Credential Manager, `net use` или перезагрузку.

Типовой сценарий:

1. Выбрать сохранённую пару или вписать `COMPUTER-NAME` и `User Name`.
2. Нажать `SMB вход в сеть`.
3. В открывшейся консоли ввести пароль Windows-учётки.
4. После сообщения `SMB session is ready` работать с `\\COMPUTER` в Explorer.

## Adapter И LAN/Wi-Fi Modes

`Adapter action` включает/выключает выбранный сетевой адаптер. Это может оборвать текущую сессию.

`LAN/Wi-Fi switch`:

- LAN only;
- Wi-Fi only;
- both on;
- cycle Wi-Fi.

`Wi-Fi sticky pair` делает один профиль auto-connect, а второй manual. Это не repair, а управление приоритетом подключения.

## Где Лежат Данные

Типовые места:

```text
backup\network
backup\wifi
config\smb_network_logins.json
report\smb_network_login.ps1
logs
```

Wi-Fi XML с clear keys не должен уходить в публичные репозитории, issue, screenshots или shared folders. SMB cache не содержит паролей, но всё равно раскрывает имена компьютеров и пользователей.

## Smoke

Минимальная проверка:

```text
Status snapshot       -> пишет snapshot/log, сеть не меняет
Backup network state  -> создаёт manifest и exports
Backup Wi-Fi keys     -> явно помечен как sensitive
Restore selected      -> выбирает snapshot из dropdown
Wi-Fi status          -> показывает adapters/profiles
Export profiles       -> XML создан в выбранной папке
SMB вход в сеть        -> открывает внешнюю консоль, пароль не виден в GUI/log
Adapter action        -> target adapter виден в log
```
