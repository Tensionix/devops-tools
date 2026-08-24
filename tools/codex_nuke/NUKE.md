**Ограничения, которые честно надо признать:**
- Если Codex обновится и переименуется (например, новый `OpenAI.Codex2`) — скрипт его не подхватит. Лечится: задать `-PackageNamePattern` (по умолчанию `OpenAI\.Codex`).
- Если файл в профиле залочен антивирусом — нужен ребут. MoveFileEx-fallback решает, но требует перезагрузки.
- TrustedInstaller-ключи иногда требуют именно остановки сервиса (как у нас WSearch/StateRepository). Это уже встроено.
- На сервере без `Get-AppxPackage` (Server Core без AppX) часть веток просто no-op.
- `Remove-AppxProvisionedPackage` требует Windows образа онлайн — на нестандартных SKU может не работать.