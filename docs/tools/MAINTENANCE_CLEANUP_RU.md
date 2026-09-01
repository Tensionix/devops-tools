# Maintenance And Cleanup

Runbook для Codex Nuke, Python Nuke и очистки workspace.

Полный список GUI-параметров смотри в `USER_GUIDE_RU.md` в блоках `Обслуживание и очистка` и `Справочник параметров -> Maintenance`.

## Главное Правило

Cleanup-команды должны удалять только свой scope. Если непонятно, что попадёт в scope, сначала запускай audit/dry-run/status.

Не используй cleanup как repair, если цель - понять проблему. Сначала диагностика, потом удаление.

## Codex Nuke

`Codex session reset` - мягкий reset:

- остановить Codex processes;
- очистить sessions/cache;
- сохранить auth, config и install.

`Codex NUKE, keep CLI state` удаляет Codex Desktop artifacts, но сохраняет `~\.codex` для Codex CLI state.

`Codex NUKE full` удаляет и desktop artifacts, и общий пользовательский Codex state. Это destructive операция: можно потерять sessions, локальный state и настройки.

Перед реальным nuke:

1. Закрой лишние Codex windows.
2. Убедись, что нужные project files сохранены.
3. Проверь scope в UI.
4. Запусти audit/dry-run, если доступен.
5. Только затем запускай real action.

## Python Nuke

`Python NUKE full` удаляет распространённые Python installs, launchers, Store Python/AppX, pip cache/config, env vars, PATH entries и uninstall registry entries.

`Python NUKE, keep winget` пропускает winget uninstall pass, но остальные cleanup-шаги могут остаться destructive.

Команда не должна трогать project venvs и сам tool folder. После реального nuke лучше reboot перед новой установкой Python.

Проверяй особенно:

- `python.exe` в PATH;
- Python Launcher;
- Store aliases;
- pip/pipx/uv/conda следы;
- user/system env vars.

## Clear Workbench Workspace

`Clear Workbench workspace` удаляет только файлы внутри managed workspace folder проекта.

Это не general-purpose delete. Если операция хочет удалить путь вне workspace, это bug или неверный параметр.

Перед очисткой:

1. Для удаления содержимого нажми `Удалить` в Workbench только после проверки выбранных `Источник` и `Назначение`; `Сбросить` лишь возвращает проектные пути и файлы не удаляет.
2. Проверь log.
3. Не используй абсолютные старые пути с чужих дисков как fallback.

## Smoke

Минимальная проверка:

```text
Codex session reset      -> сохраняет auth/config/install
Codex keep CLI state     -> сохраняет ~/.codex
Codex full nuke          -> требует явное подтверждение
Python nuke dry run      -> перечисляет targets без удаления
Clear workspace          -> target path внутри managed workspace
```
