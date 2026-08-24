# Manifest Reference

`config/tool_manifest.yaml` описывает шаблонные операции для GUI.

Минимальная операция:

```yaml
operations:
  - id: validate_input
    title: "Validate input"
    title_ru: "Проверить input"
    description: "Check input and print inventory."
    description_ru: "Проверить input и вывести инвентаризацию."
    service: "system_core.services.sample_service:validate_input"
    kind: "safe"
    risk_level: "readonly"
```

Поля:

- `id`: стабильный идентификатор.
- `title`: короткая EN-надпись для кнопки.
- `title_ru`: короткая RU-надпись для кнопки.
- `description`: пояснение справа от кнопки.
- `description_ru`: русское пояснение.
- `service`: Python callable в формате `module:function`.
- `kind`: `safe` или `dangerous`.
- `risk_level`: необязательная уточняющая классификация риска. Поддерживаемые значения: `readonly`, `project_write`, `user_write`, `system_change`, `destructive`, `secret_export`.
- `action_group` / `action_group_ru`: логическая рамка вокруг соседних команд. Используйте для пар и pipeline: `backup / restore`, `export / import`, `block / unblock`, `capture / apply`.
- `action_group_tone`: тон рамки. По умолчанию держите `neutral`; цвет рамки нужен редко, когда весь блок имеет один характер.
- `action_tone`: тон акцента конкретной кнопки внутри рамки. Поддерживаемые значения: `friendly`, `medium`, `danger` и алиасы `safe`, `soft`, `normal`, `strong`, `sensitive`, `destructive`. Акцент состоит из слабой заливки и читаемой обводки; это визуальная подсказка, а не замена `kind` и `risk_level`. В парных workflow зелёный `friendly` может означать не абсолютную безопасность, а сторону отмены/разблокировки.
- Кнопки-разделы с `children` не получают `action_tone` в GUI: они остаются стандартными навигационными кнопками. Акцент применяется к leaf-операциям и кнопке `Запустить`.

Правила:

- `title/title_ru` должны быть короткими и помещаться в одну строку.
- Длинный смысл переносите в `description` / `description_ru`. GUI показывает компактную выжимку справа, а полный текст оставляет в tooltip и dangerous-confirmation.
- Leaf-команды в GUI читаются как список: слева короткая кнопка действия, справа короткое решение/контекст, ограничения и подсказка о последствиях. Не превращайте сложные разделы в горсть кнопок без контекста.
- Для системных операций `description_ru` должен отвечать минимум на три вопроса: что изменится, где будет backup/status, нужен ли следующий шаг вроде sign out/reboot.
- `kind: dangerous` требует подтверждения. `risk_level` не заменяет `kind`: он объясняет характер риска даже у операций без destructive-действия.
- Если `action_tone` не задан, GUI берёт акцент из `risk_level`/`kind`. Ручной `action_tone` используйте для смысловых пар и исключений, где кнопка является стороной отмены, восстановления или более мягкого пути внутри одного блока.
- Для реальных проектов без service layer допустимо адаптировать GUI под subprocess-вызов существующего CLI.

## Вложенные Меню

Для больших CLI-проектов используйте `operation_groups`. Дерево может иметь несколько уровней: например `лаунчер -> формат -> профиль -> запуск`.

```yaml
operation_groups:
  - id: convert
    title: "Convert"
    title_ru: "Конвертация"
    children:
      - id: office
        title: "Office"
        title_ru: "Office"
        fields:
          - id: input_formats
            type: "checkboxes"
            label: "Input formats"
            label_ru: "Форматы input"
            default: []
            min_selected: 1
            options:
              - value: "docx"
                label: "DOCX"
              - value: "xlsx"
                label: "XLSX"
              - value: "pptx"
                label: "PPTX"
        children:
          - id: run_convert
            title: "Run"
            title_ru: "Запуск"
            service: "system_core.services.sample_service:run_sample_job"
```

Если задан `operation_groups`, видимый список команд строится из дерева. Важные плоские `operations` нужно продублировать в дереве.

## Fields

`fields` показываются на финальном экране `Запустить` / `Назад`, наследуются дочерними узлами и передаются в `context.operation.parameters`.

Порядок `fields` лучше задавать по смыслу пользовательского решения, а не по порядку CLI-аргументов. Ставьте связанные поля рядом: ключ с моделью, формат с профилем, источник с режимом. Редкие числовые/ручные параметры можно пометить `advanced: true` или вынести ниже через локальные правила рендера.

Команды в `children` должны быть связаны с объектом текущей формы. Если leaf меняет конкретный список, cache или файл, отражайте это в `title_ru/title`: `Ключ в избранное`, `Модель в избранное`, `Сделать инструкцию активной`, `Импортировать файл`. Не используйте безымянные `В избранное`, `Сохранить`, `Применить`, когда рядом несколько `fields` и непонятно, к чему относится действие.

Сервис может вернуть `{"field_updates": {"field_id": "new value"}}`. GUI применит эти значения к текущим `fields`, обновит форму и запишет в журнал `Updated GUI fields: ...`. Используйте это для безопасных detect/rescan-команд, которые должны заполнить форму, но не менять систему напрямую.

Поддерживаемые типы:

- `text`: строка, ссылка, путь или ручной параметр.
- `textarea`, `multiline`: многострочный ввод.
- `password`: строка со скрытым вводом; значение не попадает в журнал операции.
- `folder`: путь к папке с кнопкой системного выбора.
- `file`: путь к файлу с кнопкой системного выбора.
- `path`: legacy/manual путь; для новых GUI предпочитайте `folder` или `file`, если тип пути известен.
- `number`, `int`, `float`: числовой ввод.
- `select`: один вариант из списка `options`.
- `radio`: один вариант из списка `options`, когда вариантов мало и их полезно видеть сразу.
- `checkbox`, `bool`, `boolean`: один флажок, значение `true/false`.
- `checkboxes`: группа флажков, значение - список выбранных `value`.
- `profile_buttons`, `preset_buttons`: набор кнопок, которые меняют значения других `fields`, но не запускают операцию.
- `info_badges`: read-only строка значков из `options_source`; ничего не отправляет в сервис, только показывает текущее состояние системы.
- `smb_login_cache`: специализированный виджет истории SMB-логинов.

## Оформление Поля

`display` меняет подачу поля, не меняя его тип и значение:

- `display: "mode_buttons"` для `radio`: варианты становятся цветными кнопками-тогглами, подсвечивается активный. Цвет берётся из `accent` варианта.
- `display: "safety_buttons"` для `radio`: варианты становятся карточками с `title`, `summary`, `tone` и `icon`; удобно, когда каждый вариант нужно объяснить фразой.
- `display: "chips"` для `checkboxes`: флажки становятся чипами. Чип всегда в одну строку и растёт по своей подписи; переносится на следующую строку чип целиком, подпись внутри не переносится.

Дополнительные ключи оформления:

- `span: "full"` (синоним `width: "wide"`): поле занимает всю строку сетки. Виджеты с описанием и списками растягиваются на всю строку автоматически.
- `hide_hint: true`: не показывать `hint` под полем.
- `group` / `group_ru` у варианта: заголовок группы внутри `checkboxes`; каждая группа рисуется отдельной рамкой.
- `group_accents`: карта `группа -> цвет` на уровне поля. Ключ - непереведённое имя `group`; цвет наследуют рамка группы и её чипы. Если карты нет, берётся `accent` варианта.
- `accent`: цвет одного варианта, в формате `#rrggbb`.
- `searchable: true` для `select`: поле с поиском по списку.
- `show_refresh: false`: убрать кнопку обновления у поля с `options_source`; `refresh_label` / `refresh_label_ru` меняют её подпись.
- `selection_presets` у `checkboxes`: строка кнопок над списком. Пресет задаёт либо `mode` (`all`, `none`, `default`), либо явный список `values` для этого же поля.

Для `checkboxes` используйте:

- `default`: список выбранных значений по умолчанию. Для новых миграций держите `[]`, чтобы пользователь явно выбрал нужное.
- `min_selected`: минимальное количество выбранных пунктов.
- `options`: список вариантов с `value`, `label`, `label_ru`.

Для миграции CLI-проектов удобно делать так: GUI собирает список чекбоксов в `context.operation.parameters`, сервис превращает его в аргумент старого CLI, например `--extensions docx,pptx,xlsx`, и уже CLI фильтрует работу. По умолчанию чекбоксы лучше оставлять пустыми: обычно пользователь хочет обработать что-то конкретное.

## Динамические Options

Для `select`, `radio` и `checkboxes` можно не хранить список вариантов в YAML, а загрузить его из Python provider:

```yaml
fields:
  - id: selected_input_files
    type: "checkboxes"
    label: "Staged input files"
    label_ru: "Файлы в input"
    default: []
    options_source: "system_core.services.sample_service:input_file_options"
    cache_seconds: 20
```

`options_source` использует формат `module:function`. Provider может принимать `root` проекта или не принимать аргументов. Он должен вернуть список:

```python
[
    {"value": "example.docx", "label": "example.docx", "label_ru": "example.docx"},
]
```

GUI кэширует результат на `cache_seconds` секунд и показывает кнопку `Обновить список`. Если provider упал, GUI покажет ошибку как один вариант списка, а не уронит окно.

Если текущее значение `select` не входит в новый список options, GUI должен выбрать первый валидный вариант. Это защищает экран от пустого dropdown после смены cache, языка, WSL-блока, диска или папки.

Для развитых LLM-проектов это заменяет старые ручные файлы со списками моделей. Не держите одновременно `options_source`/cache/favorites/smoke и статический `models.yaml` как равноправные источники. Manifest должен указывать динамический источник, а устойчивые значения вроде лимитов, prompts и env-настроек должны жить отдельно от model ids.

## Профили / Пресеты

`profile_buttons` удобны для типовых наборов галочек и настроек:

```yaml
fields:
  - id: sample_profiles
    type: "profile_buttons"
    label: "Quick presets"
    label_ru: "Быстрые профили"
    presets:
      - id: office
        label: "Office"
        label_ru: "Office"
        values:
          input_formats: ["docx", "pptx", "xlsx"]
          include_metadata: true
      - id: reset
        label: "Reset"
        label_ru: "Сброс"
        values:
          input_formats: []
          include_metadata: false
```

Пресет только меняет `field_values`; пользователь видит результат и сам нажимает `Запустить`.
