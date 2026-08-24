# Bitrix Hosts: Detect, Patch, Depatch

Этот раздел нужен для on-prem Bitrix, где IP и порт могут переезжать раз в несколько недель или месяцев. Текущий рабочий default:

```text
Host: portal.itpgrad.ru
URL : https://192.168.0.130
IP  : 192.168.0.130
Port: 443
```

## Главное Правило

Windows `hosts` не умеет хранить порт. В `hosts` пишется только:

```text
192.168.0.130    portal.itpgrad.ru
```

Порт хранится только как metadata в комментарии managed-строки:

```text
# AUDION_BITRIX_HOSTS; ports=443; backup=hosts_prepatch_....bak; updated=...
```

Эта metadata нужна DevOps Tools для диагностики, повторной проверки и точного depatch.

## Рабочий Сценарий

1. Открыть `Hosts and Bitrix`.
2. Нажать `Detect current endpoint`.
3. Убедиться, что поля `IP address` и `Custom TCP ports` заполнены локальным адресом и портом.
4. Нажать `Status / DNS / ports`.
5. Если всё выглядит правильно, нажать `Enable override`.
6. После работы нажать `Disable override`, чтобы вернуть exact pre-patch `hosts`.

`Detect current endpoint` не меняет систему. Он делает DNS-only lookup без учёта stale `hosts`, принимает только локальные/private адреса и сканирует порты-кандидаты. Публичный DNS IP выводится в журнал, но в поле `IP address` не подставляется.

Локальными считаются:

- `10.0.0.0/8`;
- `172.16.0.0/12`;
- `192.168.0.0/16`;
- `127.0.0.0/8`;
- `169.254.0.0/16`;
- IPv6 loopback, ULA и link-local.

## Enable Override

`Enable override` делает три вещи:

1. Сохраняет точный pre-patch backup в `backup\hosts\hosts_prepatch_....bak`.
2. Отключает старые активные строки для выбранного host.
3. Добавляет managed-строку `IP -> host` с metadata `ports=...` и `backup=...`.

Backup-файл является источником истины для последующего depatch.

## Disable Override

`Disable override` не редактирует `hosts` построчно. Он:

1. Читает `backup=hosts_prepatch_....bak` из managed-комментария.
2. Проверяет, что backup существует в `backup\hosts`.
3. Сохраняет текущий файл в `hosts_before_disable_....bak`.
4. Копирует pre-patch backup поверх системного `hosts`.

Это побитовый depatch: итоговый `hosts` должен совпасть с исходным backup. Совпадающие дата/время файла после восстановления - хороший бытовой индикатор, что файл не пересобирался вручную.

Если metadata `backup=...` отсутствует или файл backup потерян, `Disable override` должен отказаться от "почти отката". В таком случае используйте `Restore original hosts` или снова включите override новой версией, чтобы создать managed-строку с backup metadata.

## Restore Original Hosts

`Restore original hosts` - аварийный fallback. Он восстанавливает последний доступный `hosts_prepatch_*.bak`, если явный depatch по managed-строке невозможен.

## Что Проверять В Status

`Status / DNS / ports` read-only и должен показывать:

- активные строки `hosts`;
- metadata `ports` и `backup`;
- effective resolution с учётом `hosts`;
- DNS answer без hosts-файла;
- configured DNS servers;
- auto-scan открытых портов;
- итоговую TCP-проверку host/IP и custom/detected ports.

## Smoke

Минимальная проверка поведения:

```text
Detect current endpoint -> fields update only for local/private IP
Enable override          -> pre-patch backup created, managed line has backup=...
Disable override         -> hosts restored byte-for-byte from referenced backup
Status / DNS / ports     -> shows ports + backup metadata
```
