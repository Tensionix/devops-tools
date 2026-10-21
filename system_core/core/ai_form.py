from __future__ import annotations

from copy import deepcopy

from system_core.services.ai_catalog import ALL_CATEGORIES, ESSENTIAL


OPERATIONS = {"ai_backup_export", "ai_backup_import"}
SOURCE = "system_core.services.ai_transfer:"


def fields_for(operation: str, original: list[dict]) -> list[dict]:
    importing = operation == "ai_backup_import"
    hidden = [dict(field, hidden=True, default=deepcopy(field.get("default", []))) for field in original]
    common = [dict(field) for field in original if field["id"] in {"include_auth", "dry_run", "allow_foreign_paths", "allow_legacy"}]
    modern = [
        {"id": "transfer_version", "type": "number", "default": 3, "hidden": True},
        {"id": "ai_plan_token", "type": "text", "default": "", "hidden": True,
         "depends_on": ["selected_chats", "data_categories", "include_auth", "overwrite_conflicts", "path_map"]},
        {"id": "ai_summary", "type": "info_badges", "label": "Backup" if importing else "Local sources",
         "label_ru": "Бэкап" if importing else "Локальные источники", "options_source": SOURCE + ("bundle_summary_options" if importing else "inventory_options"), "cache_seconds": 20},
        {"id": "chat_provider", "type": "radio", "label": "Application", "label_ru": "Приложение", "default": "all",
         "options": [{"value": key, "label": "All" if key == "all" else text, "label_ru": "Все" if key == "all" else text} for key, text in [("all", "All"), ("claude", "Claude Code"), ("claude_desktop", "Claude Desktop"), ("codex", "Codex"), ("grok", "Grok CLI")]]},
        {"id": "chat_project", "type": "select", "label": "Project", "label_ru": "Проект", "default": "all", "view": "dropdown",
         "options_source": SOURCE + ("bundle_project_options" if importing else "project_options"), "cache_seconds": 20},
        {"id": "chat_archive", "type": "radio", "label": "History", "label_ru": "История", "default": "all",
         "options": [{"value": "all", "label": "All", "label_ru": "Вся"}, {"value": "active", "label": "Active", "label_ru": "Активная"}, {"value": "archived", "label": "Archived", "label_ru": "Архив"}]},
        {"id": "selected_chats", "type": "multiselect", "display": "ai_chats", "preserve_selection": True, "default": [],
         "label": "Chats in the backup" if importing else "Local chats", "label_ru": "Чаты в бэкапе" if importing else "Локальные чаты",
         "options_source": SOURCE + ("bundle_chat_options" if importing else "live_chat_options"), "depends_on": ["chat_provider", "chat_project", "chat_archive"], "cache_seconds": 20,
         "hint": "Chats are selected independently of the data preset. Filters preserve hidden selections.",
         "hint_ru": "Выбор чатов не зависит от пресета данных. Фильтры сохраняют скрытые отметки."},
        {"id": "ai_presets", "type": "profile_buttons", "presets": [
            {"id": "essential", "label": "Essential", "label_ru": "Необходимое", "values": {"data_categories": ESSENTIAL}},
            {"id": "full", "label": "All supported data", "label_ru": "Все поддержанные данные", "values": {"data_categories": ALL_CATEGORIES}}]},
        {"id": "data_categories", "type": "multiselect", "display": "ai_categories", "default": ESSENTIAL,
         "label": "Other data", "label_ru": "Остальные данные", "options_source": SOURCE + ("bundle_category_options" if importing else "category_options"), "cache_seconds": 20},
        *common,
        {"id": "overwrite_conflicts", "type": "checkbox", "default": False, "label": "Replace conflicting local data", "label_ru": "Заменять конфликтующие локальные данные", "visible_when": {"transfer_version": 3}} if importing else
        {"id": "dry_run", "type": "checkbox", "default": True, "label": "Preview export", "label_ru": "Показать план экспорта"},
        {"id": "path_map", "type": "textarea", "default": "{}", "advanced": True, "label": "Project path mapping (JSON)", "label_ru": "Сопоставление папок проектов (JSON)", "hidden": not importing},
        {"id": "ai_selection", "type": "info_badges", "options_source": SOURCE + ("bundle_selection_options" if importing else "selection_options"),
         "depends_on": ["selected_chats", "data_categories", "include_auth"], "cache_seconds": 0},
    ]
    prefix = "ai_import__" if importing else "ai_export__"
    for field in modern:
        if field["id"] != "transfer_version":
            field["id"] = prefix + field["id"]
        if "depends_on" in field:
            field["depends_on"] = [prefix + name for name in field["depends_on"]]
        for preset in field.get("presets", []):
            preset["values"] = {prefix + key: value for key, value in preset.get("values", {}).items()}
        if importing and field.get("options_source"):
            field.setdefault("depends_on", []).append(prefix + "allow_legacy")
    return hidden + modern


def parameters(node, values, source, target):
    from system_core.services.ai_catalog import ESSENTIAL
    if values.get("essentials") is False or values.get("export_chats") or values.get("import_chats"):
        raise RuntimeError("Do not mix legacy chat/profile selection with transfer_version 3")
    values = normalized(values, "import" if node.id == "ai_backup_import" else "export")
    return {"mode": node.parameters.get("mode", "export"), "transfer_version": 3,
            "selected_chats": values.get("selected_chats", []), "data_categories": values.get("data_categories", ESSENTIAL),
            "include_auth": bool(values.get("include_auth", False)), "dry_run": bool(values.get("dry_run", True)),
            "overwrite_conflicts": bool(values.get("overwrite_conflicts", False)),
            "allow_foreign_paths": bool(values.get("allow_foreign_paths", False)), "allow_legacy": bool(values.get("allow_legacy", False)),
            "path_map": values.get("path_map", "{}"), "ai_plan_token": values.get("ai_plan_token", ""), "input_path": str(source), "output_path": str(target)}


def normalized(values, mode):
    prefix = f"ai_{mode}__"
    return {**values, **{key[len(prefix):]: value for key, value in values.items() if key.startswith(prefix)}}
