# Default Apps Guard

Короткий практический гайд для случая: Windows уже установлена, нужные программы уже стоят, defaults выставлены вручную, и хочется запретить Windows снова делать Edge браузером или PDF-читалкой.

## Быстрый Ритуал

1. Запусти `launcher_gui.cmd` обычным способом и подтверди UAC.
2. Открой `ПРИЛОЖЕНИЯ ПО УМОЛЧАНИЮ -> ПОЛИТИКА`.
3. Для важной точки отката заполни `Метка резервной копии`, например `golden-before`, `before-faststone` или `clean-windows-office`.
4. Выбери `Проверить — чем сейчас открываются файлы` и проверь текущую картину: browser, PDF, текст/Office, архивы, картинки, видео, аудио и playlists.
5. Выбери `Экспортировать текущие ассоциации в эталон`.
   Это читает текущие Windows associations и заменяет управляемый эталон `profiles\default_apps\AppAssociations.xml`; timestamp backup сохраняется отдельно.
6. Оставь включённым `Закреплять жёстко`.
   Это hard mode: policy будет возвращать associations при каждом входе пользователя.
7. Выбери `Закрепить сохранённые ассоциации`.
   Команда скопирует XML в `C:\ProgramData\Audion\DefaultApps\AppAssociations.xml`, включит HKLM policy `DefaultAssociationsConfiguration` и выполнит `gpupdate /force`.
8. Сделай sign out/sign in или reboot.
9. После входа снова запусти `Проверить — чем сейчас открываются файлы`.

Смысл: мы не просим Windows быть вежливой. Мы даём ей официальный admin-policy приказ возвращать эталонный набор associations при входе.

Поле `Какие типы файлов отслеживать` стоит прямо в форме, чипами по группам. Оно не меняет эталонный XML и не строит policy; это фильтр для проверки и сравнения current/profile/policy. Обычно его можно не трогать. Если нужна точечная диагностика, используй кнопки-пресеты `Все`, `Снять`, `По умолчанию` и группы `Ссылки`, `Текст`, `Офис`, `Архивы`, `Картинки`, `Видео`, `Аудио`, `Плейлисты`. Свои расширения дописываются в поле `Добавить свои типы`.

## Что Делают Команды

- `Проверить — чем сейчас открываются файлы` - read-only диагностика. Сравнивает current user, эталонный profile XML и active policy XML.
- `Сохранить снимок текущего состояния` - делает backup текущих associations без изменения управляемого эталона.
- `Экспортировать текущие ассоциации в эталон` - заменяет эталонный `AppAssociations.xml` тем, что сейчас назначено в Windows. Это не включает policy, но следующий запуск защиты будет принуждать уже этот эталон.
- `Взять эталон из файла` - заносит выбранный сохранённый снимок или внешний валидный DISM `AppAssociations.xml` в управляемый эталон. XML может быть из этой утилиты, из `DISM /Export-DefaultAppAssociations`, с другой совместимой машины или из deployment baseline.
- `Закрепить сохранённые ассоциации` - включает или чинит HKLM policy по управляемому XML. Требует уже существующий эталон: созданный через перезапись из текущей системы или импортированный внешним XML.
- `Снять закрепление` - снимает policy-слой, но не обещает вернуть Edge/Photos/Media Player.
- `Открыть папку эталона` / `Открыть папку закреплённого набора` / `Открыть папку резервных копий` - открывают рабочие папки модуля без изменения системы.
- `Убрать старые резервные копии` - удаляет только старые безымянные timestamp backups вида `Prefix_YYYY-MM-DD_HH-mm-ss.xml`. Именованные backups, ручные файлы и `.note.txt` заметки сохраняются. По умолчанию работает в dry-run.

Policy-слой - это machine-level значение `HKLM\SOFTWARE\Policies\Microsoft\Windows\System\DefaultAssociationsConfiguration`, которое указывает Windows на активный `AppAssociations.xml` в ProgramData. Оно отвечает за повторное применение default app associations при входе пользователя. Отключение policy-слоя удаляет этот приказ, но не меняет мгновенно текущие ассоциации пользователя.

Для восстановления из собственного backup не нужен `input`: в действии `Взять эталон из файла` есть список `Сохранённый снимок`, который сканирует `backup\default_apps`. Ручной выбор `Файл с другого компьютера` нужен только для файла извне или когда backup лежит не в штатной папке.

## Как Узнать Нужный Backup

У backup есть timestamp, SHA256 в логе и опциональная `Метка резервной копии`. Если поле заполнено, модуль добавляет метку в имя backup-файла и пишет рядом `.note.txt`.

Пример:

```text
AppAssociations_export_2026-05-25_14-30-00_golden-before.xml
AppAssociations_export_2026-05-25_14-30-00_golden-before.xml.note.txt
```

`Метка резервной копии` не влияет на содержимое XML и policy. Это только человеческий ярлык для поиска и понимания, какой снимок был “тот самый”.

## Забавности Windows

- На Windows 11 Home/Core policy `DefaultAssociationsConfiguration` не считается гарантированным путём: Microsoft документирует её для Pro/Enterprise/Education/IoT Enterprise. `Проверить — чем сейчас открываются файлы` покажет edition, а `Закрепить сохранённые ассоциации` по умолчанию остановится на Home/Core, чтобы не создавать ложное чувство защиты.
- Policy обычно реально применяется при новом входе пользователя, не в текущей сессии.
- После чистой установки XML может быть неполным, пока delay-installed apps ещё не зарегистрировались.
- Если приложение обновилось и сменило ProgId, старый XML может перестать попадать в цель. Тогда снова сделай `Экспортировать текущие ассоциации в эталон` и `Закрепить сохранённые ассоциации`.
- Edge, Photos и Media Player могут продолжать уговаривать стать default-приложениями внутри своего UI.
- `Suggested=true` делает association мягкой/однократной. Для защиты от возврата Edge лучше держать включённым `Закреплять жёстко`.
- Browser/PDF associations сильнее защищены через `UserChoice`/UCPD. Поэтому модуль не правит `UserChoice` руками.
- XML с другой машины может не сработать идеально, если там другой набор приложений или ProgId.
- `Снять закрепление` только снимает приказ. Текущее состояние defaults остаётся как есть до следующих пользовательских или системных изменений.

## Официальная Граница

Основной слой модуля построен на документированном Microsoft admin/deployment path:

- DISM default app associations;
- `DefaultAssociationsConfiguration` policy;
- registry path `HKLM\SOFTWARE\Policies\Microsoft\Windows\System`;
- `Suggested` behavior в Windows 11 22H2+;
- применение policy при sign-in.

Снимки ассоциаций текущего пользователя не входят в `ПОЛИТИКУ`: они живут на вкладках `СНИМОК` и `ГРУППЫ`, читают `UserChoice\ProgId` из реестра и только фиксируют состояние. Записывать обратно личный выбор пользователя проект не умеет и не будет — Windows защищает его проверочной суммой.

## Если Это Windows 11 Home

Честный ответ: recurring policy-магия может не работать, потому что Microsoft не документирует `DefaultAssociationsConfiguration` для Home/Core editions.

Что остаётся полезным:

- `Проверить — чем сейчас открываются файлы` - диагностика текущих associations, profile XML, policy XML и Windows edition.
- `Сохранить снимок текущего состояния` - безопасный снимок текущих defaults.
- `Экспортировать текущие ассоциации в эталон` - создание эталонного XML для хранения/переноса.
- `Взять эталон из файла` - загрузка готового XML в managed profile.

Что не обещаем:

- что HKLM policy будет повторно применять defaults при каждом входе;
- что browser/PDF associations удастся удержать через неподдержанную Home/Core policy на 100%;
- что `DISM /Online /Import-DefaultAppAssociations` починит уже существующего пользователя. По документации DISM import применяет default associations при первом входе пользователя, то есть это больше deployment/new-user baseline, чем восстановитель текущего профиля.

В GUI есть expert-чекбокс `Разрешить неподдерживаемую редакцию`. Он позволяет попробовать policy path на Home/Core, но это режим теста, а не документированная гарантия.

## Источники

- <https://learn.microsoft.com/en-us/windows/client-management/mdm/policy-csp-applicationdefaults>
- <https://learn.microsoft.com/en-us/windows-hardware/manufacture/desktop/dism-default-application-association-servicing-command-line-options?view=windows-11>
- <https://learn.microsoft.com/en-us/windows-hardware/manufacture/desktop/export-or-import-default-application-associations?view=windows-11>
