# Audion Network Cleaner v2 — TimeMachine edition

Цель проекта: **мягкое ядерное оружие с машиной времени**.

Обычные режимы не должны добивать Windows. Перед любой ремонтной процедурой скрипт создаёт снимок состояния сети внутри папки проекта:

```text
backup\network_backup_YYYYMMDD_HHMMSS_<Reason>\
```

Точки восстановления Windows не используются. Всё хранится внутри проекта.

## Главное отличие v2

Добавлены режимы отката:

```cmd
Run_TimeMachine_Restore_Latest.cmd
```

Восстановить последний снимок.

```cmd
Run_TimeMachine_Restore_Select.cmd
```

Выбрать снимок вручную.

Перед откатом скрипт сначала делает новый снимок текущего сломанного состояния, чтобы не потерять даже его.

## Что сохраняется в backup

- `ipconfig /all`
- `route print`
- `netsh -c interface dump`
- IPv4/IPv6/DNS/routes/interface snapshots
- WinHTTP proxy status
- Winsock catalog
- firewall export `.wfw`
- Wi-Fi profiles без ключей по умолчанию
- опционально Wi-Fi profiles с ключами в открытом виде
- registry exports:
  - TCP/IP parameters and interfaces
  - TCP/IP v6 parameters and interfaces
  - Winsock2 parameters
  - NetBT parameters and interfaces
  - NetworkList profiles/signatures
  - HKCU Internet Settings
  - WinHTTP/Internet Settings connections
- binary copy of `hosts`
- SHA256 hashes for copied `hosts`
- `restore_manifest.json`
- full run logs

## Важная честность про «побайтово»

Для обычных файлов, например `hosts`, используется бинарное копирование и SHA256-проверка.

Но живой сетевой стек Windows, registry hives, драйверная база, Winsock catalog и network adapter database не являются одним обычным файлом, который можно гарантированно вернуть побайтово из-под работающей Windows. Поэтому TimeMachine Restore делает максимально практичный откат:

- импортирует сохранённые `.reg`
- восстанавливает `hosts`
- импортирует firewall `.wfw`
- прогоняет сохранённый `netsh interface dump`
- добавляет обратно Wi-Fi profiles
- обновляет DNS registration/cache

Это не замена полному offline-образу диска, но это максимально контролируемый откат внутри portable-проекта без System Restore.

## Режимы

### Только диагностика

```cmd
Run_Status.cmd
```

Показывает текущее состояние сети и создаёт снимок.

### Только бэкап

```cmd
Run_Backup.cmd
```

Создаёт снимок без ремонта.

### Бэкап с Wi-Fi ключами

```cmd
Run_Backup_With_WiFi_Keys_SENSITIVE.cmd
```

Экспортирует Wi-Fi profiles с `key=clear`. Это удобно для полного восстановления профилей, но XML-файлы могут содержать Wi-Fi пароли в открытом виде. Хранить осторожно.

### Мягкий ремонт

```cmd
Run_Light_Repair.cmd
```

Делает:

```text
ipconfig /flushdns
ipconfig /registerdns
netsh interface ip delete arpcache
nbtstat -R
nbtstat -RR
targeted ipconfig /renew for connected DHCP interfaces
```

Не делает:

```text
route -f
netsh int ip reset
netsh winsock reset
firewall reset
Wi-Fi profile deletion
event log cleanup
```

### Стандартный ремонт

```cmd
Run_Standard_Repair.cmd
```

Делает:

```text
netsh winsock reset
netsh int ip reset
netsh winhttp reset proxy
ipconfig /flushdns
ipconfig /registerdns
netsh interface ip delete arpcache
```

После него лучше перезагрузиться.

### Nuclear Repair

```cmd
Run_Nuclear_Repair_DANGEROUS.cmd
```

Требует ввод `NUCLEAR`.

Делает Standard Repair + `route -f`.

`netcfg -d` запускается только после отдельного ввода `NETCFG-D`.

### TimeMachine Restore

```cmd
Run_TimeMachine_Restore_Latest.cmd
```

или

```cmd
Run_TimeMachine_Restore_Select.cmd
```

Требует ввод `RESTORE`.

Перед восстановлением делает свежий снимок текущего состояния.

### Godzilla Strike

```cmd
Run_Godzilla_Strike_FINAL_DANGEROUS.cmd
```

Это финальный выжигающий режим, когда Windows всё равно под снос или сеть уже не жалко.

Требует ввод `GODZILLA`.

Делает жёсткий набор сбросов:

```text
netsh winsock reset catalog
netsh int ip reset
netsh int ipv4 reset
netsh int ipv6 reset
netsh winhttp reset proxy
ipconfig /flushdns
ipconfig /registerdns
ipconfig /release
route -f
netsh interface ip delete arpcache
```

Дополнительные разрушительные действия требуют отдельных подтверждений:

```text
FIREWALL-RESET        -> netsh advfirewall reset
DELETE-WIFI-PROFILES  -> netsh wlan delete profile name=*
NETCFG-D              -> netcfg -d
RENEW                 -> ipconfig /renew
```

## Что принципиально не делаем автоматически

- не чистим Event Logs
- не трогаем `hosts` в repair-режимах
- не удаляем Wi-Fi profiles без отдельного подтверждения
- не сбрасываем firewall без отдельного подтверждения
- не запускаем `netcfg -d` без отдельного подтверждения
- не используем System Restore
- не пишем бэкапы вне папки проекта

## Рекомендуемая схема применения

Сначала:

```cmd
Run_Status.cmd
```

Если проблема лёгкая:

```cmd
Run_Light_Repair.cmd
```

Если не помогло:

```cmd
Run_Standard_Repair.cmd
```

Если стало хуже:

```cmd
Run_TimeMachine_Restore_Select.cmd
```

Если Windows всё равно под переустановку:

```cmd
Run_Godzilla_Strike_FINAL_DANGEROUS.cmd
```
