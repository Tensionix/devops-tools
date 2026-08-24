AI CLI Backup — проверяемый перенос Claude Code и Codex
=======================================================

Инструмент создаёт переносимый bundle с папками claude\, codex\,
codex_sqlite\ и файлом manifest.json. Manifest содержит состав, размеры,
категории и SHA-256 всех данных. Экспорт сначала собирается во временной
папке, проверяется и только затем атомарно заменяет предыдущий бэкап.

КАК РАБОТАЕТ GUI
----------------
  Backup (export)  — пишет новый bundle в output\ai_backup.
  Restore (import) — проверяет bundle, положенный прямо в input, и импортирует
                     выбранные категории. Dry run включён по умолчанию.
  Merge memory     — проверяет bundle и объединяет только .md-память Claude.

Для импорта содержимое input должно начинаться с manifest.json, claude\,
codex\ и/или codex_sqlite\. Не кладите весь bundle ещё одним уровнем
input\ai_backup\, иначе GUI не увидит manifest.

РЕЖИМЫ
------
Essential:
  Claude — settings, CLAUDE.md, skills, plugins, projects\*\memory и
           пользовательский .claude.json.
  Codex  — config.toml, AGENTS.md, memories, rules, automations, skills,
           plugins, согласованные snapshots memories_1.sqlite и
           goals_1.sqlite.

Full дополнительно включает историю сессий, кэш и прочее содержимое профилей.
SQLite-файлы Codex сохраняются через SQLite Backup API, а не отрывом main-файла
от активных WAL/SHM.

Авторизация всегда отдельна и по умолчанию выключена:
  Claude — .credentials.json;
  Codex  — auth.json, когда используется файловое хранилище.
Bundle с авторизацией эквивалентен паролю. installation_id не переносится.

ПУТИ ПРОФИЛЕЙ
-------------
Инструмент учитывает CLAUDE_CONFIG_DIR, CODEX_HOME, CODEX_SQLITE_HOME и
sqlite_home из Codex config.toml. При переносе на другой компьютер manifest
показывает конфиги с абсолютными путями. Реальный импорт таких конфигов требует
явного разрешения Allow foreign paths / -AllowForeignPaths после Dry run.

ИМПОРТ
------
Перед любой записью проверяются структура, размеры, SHA-256 и отсутствие
незаявленных файлов. Essential-импорт игнорирует историю даже из Full-bundle.
Full-импорт добавляет категорию full. Авторизация импортируется только с
Include auth. Совпадающие файлы заменяются, остальные локальные файлы не
удаляются. Claude и Codex должны быть закрыты.

Старые бэкапы прежней версии AI-Backup.ps1 не имеют manifest.json. Они не
являются «старым форматом памяти», но их целостность доказать нельзя. Для них
нужно явное -AllowLegacy; новые бэкапы этого флага не требуют.

ВРУЧНУЮ
-------
  wrappers\backup.cmd  -Path "D:\AI" [-Full] [-IncludeAuth] [-DryRun]
  wrappers\restore.cmd -Path "D:\AI" [-Full] [-IncludeAuth] [-DryRun]
                       [-AllowForeignPaths] [-AllowLegacy] [-Yes]
  wrappers\merge.cmd   -Path "D:\AI" [-Overwrite] [-DryRun] [-AllowLegacy]

Те же команды можно передать напрямую AI-Backup.ps1 с -Mode Export, Import
или Merge. CMD-обёртки используют тот же project-local PowerShell resolver,
что GUI, и возвращают настоящий exit code скрипта.

Dry run ничего не записывает. Успех реального экспорта означает, что готовый
bundle уже перечитан и все SHA-256 совпали.
