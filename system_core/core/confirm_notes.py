"""What the question before a dangerous operation says: its notes, its risk line, its words.

The window on NiceGUI built these texts itself (`dangerous_operation_notes`, `risk_level_text` and the
`confirm_*` labels of `ui_nicegui/app.py`); they are carried over here word for word, so that the
console command tells a window on Avalonia the same question. Whether a question is asked at all is
`manifest.operation_requires_confirmation` - the rule the former window asked too.
"""
from __future__ import annotations

from .manifest import Operation

RISK_LEVEL_LABELS = {
    "readonly": {
        "ru": "Уровень риска: только чтение/диагностика.",
        "en": "Risk level: read-only diagnostics.",
    },
    "project_write": {
        "ru": "Уровень риска: запись в папку проекта.",
        "en": "Risk level: writes inside the project folder.",
    },
    "user_write": {
        "ru": "Уровень риска: изменение профиля пользователя.",
        "en": "Risk level: changes the user profile.",
    },
    "system_change": {
        "ru": "Уровень риска: изменение системного состояния Windows (политики, компоненты, гипервизор и т.п.).",
        "en": "Risk level: changes Windows system state (policies, features, hypervisor, etc.).",
    },
    "destructive": {
        "ru": "Уровень риска: destructive-действие с удалением, unregister или перезаписью.",
        "en": "Risk level: destructive delete, unregister, or overwrite action.",
    },
    "secret_export": {
        "ru": "Уровень риска: экспорт чувствительных данных.",
        "en": "Risk level: exports sensitive data.",
    },
}

WORDS = {
    "ru": {
        "confirm_title": "Подтвердите действие",
        "confirm_note": "Действие может изменить систему или рабочую область; при необходимости появится UAC-запрос.",
        "confirm_impact_title": "Что произойдёт",
        "confirm_irreversible_note": "Если это разрушительная операция, откат возможен только из backup или вручную.",
        "confirm_parameters_note": "Перед запуском проверьте выбранные поля и путь назначения.",
        "confirm_run_dangerous": "Понимаю, запустить",
    },
    "en": {
        "confirm_title": "Confirm action",
        "confirm_note": "This action may change the system or workspace; a UAC prompt may appear when needed.",
        "confirm_impact_title": "What will happen",
        "confirm_irreversible_note": "If this is a destructive operation, rollback is only possible from backup or manually.",
        "confirm_parameters_note": "Review selected fields and destination paths before starting.",
        "confirm_run_dangerous": "I understand, run",
    },
}


def words(language: str) -> dict[str, str]:
    return dict(WORDS.get(language, WORDS["en"]))


def risk_level_text(risk_level: str, language: str) -> str:
    value = str(risk_level or "").strip()
    if not value:
        return ""
    labels = RISK_LEVEL_LABELS.get(value)
    if labels:
        return labels.get(language, labels["en"])
    return f"Risk level: {value}"


def dangerous_operation_notes(operation: Operation, language: str) -> list[str]:
    op_id = operation.id.lower()
    text = " ".join(
        [
            op_id,
            operation.title.lower(),
            operation.title_ru.lower(),
            operation.description.lower(),
            operation.description_ru.lower(),
        ]
    )
    ru = language == "ru"
    notes: list[str] = []

    def add(ru_text: str, en_text: str) -> None:
        note = ru_text if ru else en_text
        if note not in notes:
            notes.append(note)

    if any(token in text for token in ("format", "diskpart", "ssd", "nvme", "winre", "partition", "раздел", "формат")):
        add(
            "Может изменить разметку диска, WinRE или состояние накопителя; ошибка выбора диска может привести к потере данных.",
            "May change disk layout, WinRE, or drive state; choosing the wrong disk can cause data loss.",
        )
        add(
            "Интерактивные storage-wizard действия продолжают требовать собственные текстовые подтверждения.",
            "Interactive storage wizard actions still require their own typed confirmations.",
        )

    if "network_nuclear" in op_id or "nuclear" in text or "тоталь" in text:
        add(
            "Будут глубоко сброшены сетевые стеки и маршруты; сеть может временно пропасть до переподключения или reboot.",
            "Network stacks and routes will be deeply reset; connectivity can disappear until reconnect or reboot.",
        )
    elif "network_standard" in op_id:
        add(
            "Будут сброшены Winsock, TCP/IP, WinHTTP proxy, DNS и ARP; активные соединения могут оборваться.",
            "Winsock, TCP/IP, WinHTTP proxy, DNS, and ARP will be reset; active connections can drop.",
        )

    if "network_restore" in op_id:
        add(
            "Текущее сетевое состояние будет заменено данными из выбранного backup-снимка.",
            "Current network state will be replaced with data from the selected backup snapshot.",
        )
    if "proxy" in op_id:
        add(
            "Будут изменены proxy-настройки Windows; приложения могут потерять доступ к сети через корпоративный или ручной proxy.",
            "Windows proxy settings will be changed; apps may lose network access through corporate or manual proxy.",
        )
    if "adapter" in op_id or "lan_wifi" in op_id:
        add(
            "Сетевые адаптеры могут быть выключены или перезапущены; текущие подключения могут оборваться.",
            "Network adapters may be disabled or restarted; current connections may drop.",
        )
    if "wifi_import" in op_id:
        add(
            "Wi-Fi XML будет добавлен в Windows как сохранённый профиль; существующий профиль с тем же именем может быть заменён Windows.",
            "The Wi-Fi XML will be added to Windows as a saved profile; Windows may replace an existing profile with the same name.",
        )
    if "wifi_export" in op_id or "wifi_keys" in op_id:
        add(
            "Wi-Fi ключи могут быть сохранены открытым текстом, если включён соответствующий параметр.",
            "Wi-Fi keys may be saved as clear text if the matching option is enabled.",
        )

    if "wsl_delete" in op_id or "unregister" in text:
        add(
            "WSL unregister удалит выбранный дистрибутив и его Linux-файловую систему из Windows.",
            "WSL unregister will remove the selected distribution and its Linux filesystem from Windows.",
        )
    if "wsl_move" in op_id:
        add(
            "Дистрибутив будет перенесён через export/import; при сбое нужен backup/export для восстановления.",
            "The distribution will be moved through export/import; recovery after failure requires a backup/export.",
        )
    if "wsl_restore" in op_id or "wsl_import" in op_id or "wsl_install" in op_id:
        add(
            "Будет создана или зарегистрирована WSL-инстанция из выбранного образа; проверьте имя и папку установки.",
            "A WSL instance will be created or registered from the selected image; verify name and install folder.",
        )
    if "wsl_register_all" in op_id:
        add(
            "Пакетная регистрация может добавить несколько VHDX как WSL-дистрибутивы; если dry-run снят, изменения будут реальными.",
            "Batch registration can add multiple VHDX files as WSL distributions; if dry-run is off, changes are real.",
        )
    if "wsl_shutdown" in op_id or "wsl_terminate" in op_id:
        add(
            "Запущенные Linux-процессы в выбранном WSL-контексте будут остановлены.",
            "Running Linux processes in the selected WSL context will be stopped.",
        )
    if "wsl_enable" in op_id:
        add(
            "Будут включены Windows optional features для WSL2/Virtual Machine Platform; может потребоваться reboot.",
            "Windows optional features for WSL2/Virtual Machine Platform will be enabled; reboot may be required.",
        )
    if "wsl_linux" in op_id or "neovim" in op_id:
        add(
            "Команда изменит выбранный Linux-дистрибутив: пакеты, пользователя, пароль, sudo/wheel или конфиги.",
            "The command will modify the selected Linux distribution: packages, user, password, sudo/wheel, or configs.",
        )

    if "hosts" in text or "bitrix" in op_id:
        add(
            "Будет изменён файл Windows hosts; DNS-резолвинг для выбранных имён может поменяться сразу.",
            "The Windows hosts file will be changed; DNS resolution for selected names may change immediately.",
        )
    if "python_nuke" in op_id:
        add(
            "Будут удаляться Python installs/launchers/cache и PATH-записи; часть Python-инструментов перестанет запускаться.",
            "Python installs/launchers/cache and PATH entries will be removed; some Python tools may stop launching.",
        )
    if "codex_nuke" in op_id:
        add(
            "Codex Desktop, sandbox-пользователи, firewall rules, cache/state и registry-артефакты могут быть удалены; для CLI state выбирай вариант keep CLI state.",
            "Codex Desktop, sandbox users, firewall rules, cache/state, and registry artifacts may be removed; choose keep CLI state to preserve CLI state.",
        )
    if "cleanup_input_output" in op_id:
        add(
            "Содержимое управляемых папок input и output будет удалено; сами папки останутся.",
            "Contents of managed input and output folders will be deleted; the folders stay.",
        )
    if "cleanup_workspace" in op_id:
        add(
            "Содержимое управляемой папки workspace будет удалено; внешние исторические инструменты не трогаются.",
            "Contents of the managed workspace folder will be deleted; external historical tools are not touched.",
        )

    said = words(language)
    add(said["confirm_parameters_note"], said["confirm_parameters_note"])
    add(said["confirm_irreversible_note"], said["confirm_irreversible_note"])
    return notes
