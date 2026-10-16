"""The form of "Browser Bookmarks Master": the values the former window kept beside the manifest.

The window on NiceGUI drew these operations with a renderer of their own (`render_browser_bookmarks_*`
of `ui_nicegui/app.py`) and kept part of the form in its own state, not in fields of the manifest:
which browsers are ticked, which one is the source of a transfer, where the profile lies, what an
import reads, whether a rollback copy is made. Here those values are fields of the form - named
`bookmark_*`, never written into the manifest - so a window on Avalonia draws them as any other field
and the console command takes them as `--set`. `parameters` builds what the former window handed to
the service (`browser_bookmarks_operation`) from them, with the same refusals.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any, Callable

PARENT = "browser_bookmarks_master"
STATUS = "browser_bookmarks_status"
CLEAR = "browser_bookmarks_clear_favicons"
EXPORT = "browser_bookmarks_export_master"
IMPORT = "browser_bookmarks_import_master"
TRANSFER = "browser_bookmarks_transfer_master"
OPERATIONS = (STATUS, CLEAR, EXPORT, IMPORT, TRANSFER)
BROWSERS_SOURCE = "system_core.services.devops_tools:chromium_browser_options"
NATIVE_SOURCE = "system_core.core.bookmarks_form:native_backup_options"


def _field(field_id: str, kind: str, label: str, label_ru: str, hint: str, hint_ru: str, **extra: Any) -> dict[str, Any]:
    return {"id": field_id, "type": kind, "label": label, "label_ru": label_ru, "hint": hint, "hint_ru": hint_ru,
            "window_value": True, **extra}


BROWSERS = _field(
    "bookmark_browsers", "checkboxes", "Browsers", "Браузеры",
    "The Chromium browsers the operation works on. Status and export take several; an import of a portable profile takes one.",
    "Браузеры Chromium, с которыми работает операция. Статус и экспорт берут несколько; импорт в portable-профиль - один.",
    options_source=BROWSERS_SOURCE, default=["chrome"], group="browsers")
TARGETS = dict(BROWSERS, label="Target browsers", label_ru="Браузеры-приёмники",
               hint="The browsers that receive the bookmarks of the source; the source itself is not among them.",
               hint_ru="Браузеры, которые получат закладки источника; сам источник среди них не стоит.")
SOURCE = _field(
    "bookmark_source", "radio", "Source browser", "Браузер-источник",
    "Transfer: the intermediate master backup is exported from this browser. Portable import: the one browser that receives.",
    "Перенос: из этого браузера снимается промежуточный эталонный backup. Импорт в portable: единственный браузер назначения.",
    options_source=BROWSERS_SOURCE, default="chrome", group="browsers")
LOCATION = _field(
    "bookmark_location", "radio", "Browser location", "Расположение браузера",
    "System mode finds the standard profile itself. Portable needs the exact profile folder, not the folder of the EXE.",
    "Системный режим находит стандартный профиль сам. Portable требует точную папку профиля, а не папку с EXE.",
    default="system", group="browsers",
    options=[{"value": "system", "label": "SYSTEM", "label_ru": "СИСТЕМНЫЙ"},
             {"value": "portable", "label": "PORTABLE", "label_ru": "ПОРТАТИВНЫЙ"}])
IMPORT_KIND = _field(
    "bookmark_import_kind", "radio", "Bookmark source", "Источник закладок",
    "An HTML backup is the main clean import of bookmarks and their icons. A profile backup is the emergency way back.",
    "HTML-бэкап - основной чистый импорт закладок и их значков. Backup профиля - аварийный путь восстановления.",
    default="html", group="source",
    options=[{"value": "html", "label": "HTML BACKUP", "label_ru": "HTML-БЭКАП"},
             {"value": "native", "label": "PROFILE BACKUP", "label_ru": "КОПИЯ ПРОФИЛЯ"}])
HTML_PATH = _field(
    "bookmark_html_path", "file", "HTML file", "HTML-файл",
    "A .html or .htm export of bookmarks. Empty - the newest one in SOURCE.",
    "Экспорт закладок .html или .htm. Пусто - самый новый в ИСТОЧНИКЕ.",
    default="", group="source", extensions=[".html", ".htm"], visible_when={"bookmark_import_kind": "html"})
BACKUP_PATH = _field(
    "bookmark_backup_path", "select", "Profile backup", "Backup профиля",
    "A folder in SOURCE with the files Bookmarks and Favicons. Empty - the newest one.",
    "Папка в ИСТОЧНИКЕ с файлами Bookmarks и Favicons. Пусто - самая новая.",
    default="", group="source", options_source=NATIVE_SOURCE, visible_when={"bookmark_import_kind": "native"})
ROLLBACK = _field(
    "bookmark_rollback", "checkbox", "Create rollback", "Создать страховочную копию",
    "Save the current Bookmarks and Favicons before an import or a cleanup. Untick it when a damaged favicon base is not worth keeping.",
    "Сохранить текущие Bookmarks и Favicons перед импортом или очисткой. Снять, если повреждённую базу значков хранить не нужно.",
    default=True, group="options")

# The fields of the window each operation shows, in the order they stand.
EXTRA_FIELDS = {
    STATUS: (LOCATION, BROWSERS, ROLLBACK),
    CLEAR: (LOCATION, BROWSERS, ROLLBACK),
    EXPORT: (LOCATION, BROWSERS, ROLLBACK),
    IMPORT: (LOCATION, dict(BROWSERS, visible_when={"bookmark_location": "system"}),
             dict(SOURCE, label="Target browser", label_ru="Браузер назначения", visible_when={"bookmark_location": "portable"}),
             IMPORT_KIND, HTML_PATH, BACKUP_PATH, ROLLBACK),
    TRANSFER: (SOURCE, TARGETS, ROLLBACK),
}
# Fields of the manifest the former window did not draw for these operations: the list of
# browsers is drawn as `bookmark_browsers`, and the profile folder only for a portable profile.
HIDDEN_FIELDS = {"browser_profile"}
PROFILE_PATH = "browser_profile_path"


def extra_fields(operation_id: str) -> tuple[dict[str, Any], ...]:
    return EXTRA_FIELDS.get(operation_id, ())


def fields_for(operation_id: str, manifest_fields: tuple[dict[str, Any], ...] | list[dict[str, Any]]) -> list[dict[str, Any]]:
    """The form of a bookmarks operation: the fields of the manifest it shows, then those of the window."""
    shown = []
    for field in manifest_fields:
        key = str(field.get("id") or "")
        if key in HIDDEN_FIELDS:
            continue
        if key == PROFILE_PATH:
            field = dict(field, visible_when={"bookmark_location": "portable"}) if operation_id != TRANSFER else dict(field, hidden=True)
        shown.append(field)
    return [*shown, *[dict(item) for item in extra_fields(operation_id)]]


def native_backup_options(root: Path, values: dict[str, Any]) -> list[dict[str, Any]]:
    """The folders in SOURCE that hold a profile backup, the newest first (`browser_bookmarks_native_backups`)."""
    source = Path(str(values.get("input_path") or Path(root) / "input"))
    found = _native_backups(source)
    return [{"value": str(path), "label": path.name if path != source else f"{path.name} (SOURCE)"} for path in found]


def _native_backups(source: Path) -> list[Path]:
    if not source.exists() or not source.is_dir():
        return []
    required = ("Bookmarks", "Favicons")
    found: list[Path] = []
    if all((source / name).is_file() for name in required):
        found.append(source)
    found.extend(path for path in source.iterdir() if path.is_dir() and all((path / name).is_file() for name in required))
    return sorted(set(found), key=lambda path: path.stat().st_mtime, reverse=True)


def _newest_html(source: Path) -> str:
    if not source.is_dir():
        return ""
    candidates = sorted([*source.glob("*.html"), *source.glob("*.htm")], key=lambda path: path.stat().st_mtime, reverse=True)
    return str(candidates[0]) if candidates else ""


def parameters(node, parent_fields: tuple[dict[str, Any], ...], values: dict[str, Any], source: Path, target: Path,
               field_default: Callable[[dict[str, Any]], Any], is_route: Callable[[dict[str, Any]], bool],
               route_value: Callable[[dict[str, Any]], str], is_badge: Callable[[dict[str, Any]], bool]) -> dict[str, Any]:
    """What `browser_bookmarks_operation` of the former window handed to the service; RuntimeError where it refused."""
    def value(field: dict[str, Any]) -> Any:
        return values.get(field["id"], field.get("default"))

    location = str(value(LOCATION) or "system")
    single = str(value(SOURCE) or "chrome")
    raw_selected = value(BROWSERS)
    selected = [str(item) for item in raw_selected] if isinstance(raw_selected, (list, tuple)) else []
    # What the form of the former window did to the ticks before a run (`normalize_browser_bookmarks_state`).
    if node.id == IMPORT and location == "portable":
        selected = [single]
    elif node.id == TRANSFER:
        selected = [item for item in selected if item != single]
    elif not selected:
        selected = [single]

    selected_values = [item for item in selected if item]
    if not selected_values:
        raise RuntimeError("No browser selected.")
    result = dict(node.parameters)
    for field in parent_fields:
        key = str(field.get("id") or "").strip()
        if not key or key == "browser_profile":
            continue
        if key == PROFILE_PATH and len(selected_values) != 1:
            continue
        if is_badge(field):
            continue
        if is_route(field):
            result[key] = route_value(field)
        else:
            result[key] = values.get(key, field_default(field))
    result["browser_profile"] = selected_values[0]
    result["browser_profiles"] = selected_values
    result["create_rollback_backup"] = bool(value(ROLLBACK))
    result["browser_location_mode"] = location
    if location == "portable":
        if len(selected_values) != 1:
            raise RuntimeError("В portable-режиме выберите ровно один браузер.")
        profile_path = str(values.get(PROFILE_PATH) or "").strip()
        if not profile_path:
            raise RuntimeError("Выберите папку профиля portable-браузера с файлом Bookmarks.")
        result[PROFILE_PATH] = profile_path
    if node.id == IMPORT:
        kind = str(value(IMPORT_KIND) or "html")
        html_path = str(values.get(HTML_PATH["id"]) or "")
        backup_path = str(values.get(BACKUP_PATH["id"]) or "")
        # The former window filled these as the form was drawn: the newest file or folder in SOURCE.
        if kind == "html" and not html_path:
            html_path = _newest_html(source)
        if kind == "native" and not backup_path:
            found = _native_backups(source)
            backup_path = str(found[0]) if found else ""
        result["clear_favicons_before_import"] = False
        result["bookmark_import_kind"] = kind
        result["bookmark_backup_path"] = backup_path
        result["bookmark_html_path"] = html_path
    if node.id == TRANSFER:
        if not single:
            raise RuntimeError("No source browser selected.")
        if single in selected_values:
            raise RuntimeError("Source browser cannot also be a transfer target.")
        result["browser_profile"] = single
        result["source_browser_profile"] = single
        result["target_browser_profiles"] = selected_values
        result["browser_profiles"] = selected_values
        result["clear_favicons_before_import"] = True
    return result
