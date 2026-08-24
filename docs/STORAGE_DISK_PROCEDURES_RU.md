# Storage / Disk Procedures

Runbook для disk inventory, SSD/NVMe wizard launcher и WinRE extend.

Полный список GUI-параметров смотри в `USER_GUIDE_RU.md` в блоках `Storage / Disk Procedures` и `Справочник параметров -> Hardware -> Накопители`.

## Главное Правило

Дисковые операции не прощают невнимательность к target. Перед любым destructive-шагом нужно видеть:

- номер диска;
- layout partitions;
- где находится `C:`;
- где находится recovery partition;
- есть ли свежий backup важных данных.

Если target не очевиден, остановись на inventory.

## Inventory

`Disk inventory` и `Selected disk details` read-only. Они нужны до любого wizard:

1. Запусти inventory.
2. Проверь размер, bus/media type, partition style.
3. Открой details для выбранного диска.
4. Сохрани log, если дальше будет destructive сценарий.

## SSD/NVMe Reset Wizard

`SSD/NVMe Reset Wizard v4` открывает оригинальный wizard во внешней консоли.

Сам wizard требует собственные typed confirmations для destructive-действий. GUI только запускает его из проекта и пишет context/log.

Не запускай reset wizard, если:

- диск выбран на глаз;
- на диске нет backup;
- непонятно, какой namespace/device будет затронут;
- параллельно открыты disk management tools, которые могут держать state.

## WinRE Extend

`Run WinRE extend wizard` нужен для сценария: отключить WinRE, удалить recovery partition справа от `C:` и расширить `C:` после подтверждения.

Это destructive операция. Ошибка target может удалить не тот раздел.

Перед запуском:

1. `reagentc /info` или status из проекта.
2. Disk inventory.
3. Убедиться, что recovery partition именно справа от `C:`.
4. Backup важных данных.
5. Проверить BitLocker/recovery key status, если используется.

После успешного сценария:

1. Проверить размер `C:`.
2. Проверить `reagentc /info`.
3. При необходимости заново включить WinRE.
4. Сохранить log.

## Smoke

Минимальная проверка:

```text
Disk inventory          -> read-only list, без изменений
Selected disk details   -> details совпадают с выбранным disk id
SSD/NVMe wizard launch  -> открывает внешнюю консоль, destructive внутри wizard
WinRE wizard            -> требует явные подтверждения, log содержит target/layout
```

