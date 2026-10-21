"""An operation of the manifest as data: its fields, their defaults, the parameters of a run.

What a window knows about an operation without it being a matter of looks: the default of a field,
which fields a window draws and which it fills itself (the folders of the workbench), where a list
of options comes from, whether the form may be run, whether a question is asked first, and which
parameters go to the service. While the window on NiceGUI held these rules itself, an operation could
be run "as in the window" only from the window. Here is one copy of them - for the console command
(`system_core/cli.py`) and for the window on Avalonia that calls it.

The rules are carried over from that window (`ui_nicegui/app.py` of 1.10.0) unchanged; that they give
the same parameters for every operation of the manifest is checked by tests/test_cli_door.py against
the record made of that window before it goes (tests/former_window_parameters.json).
"""
from __future__ import annotations

import dataclasses
import importlib
import inspect
import json
from pathlib import Path
from typing import Any

from . import ai_form, bookmarks_form, confirm_notes, smb_logins
from .manifest import CommandNode, Operation, ToolManifest, operation_requires_confirmation

CHECKBOX_GROUP_KINDS = {"checkboxes", "multi_checkbox", "multicheckbox", "multi-select", "multiselect"}
CHECKBOX_KINDS = {"checkbox", "bool", "boolean", "toggle"}
NUMBER_KINDS = {"number", "int", "integer", "float"}
BADGE_KINDS = {"info_badges", "info-badges", "static_badges", "static-badges", "badges"}
SMB_KINDS = {"smb_login_cache", "smb-login-cache"}
LANGUAGES = ("en", "ru")
SMB_SOURCE = "system_core.core.smb_logins:records_options"
DEVOPS_SERVICE = "system_core.services.devops_tools"

# Operations the manifest does not list: the command line under the terminal runs a command typed
# by a person. The former window made it up on the spot; here it has a name.
CARD_OPERATIONS = {
    "terminal_command": Operation(
        id="terminal_command",
        title="Terminal command",
        title_ru="Команда терминала",
        description="Run a command in the shell chosen, from the folder of the program or from the one named.",
        description_ru="Выполнить команду в выбранной оболочке, из папки программы или из названной.",
        service=f"{DEVOPS_SERVICE}:terminal_command",
        fields=(
            {"id": "shell", "type": "select", "label": "Shell", "label_ru": "Оболочка", "default": "pwsh",
             "options": [{"value": "pwsh", "label": "PowerShell"}, {"value": "cmd", "label": "CMD"}]},
            {"id": "command", "type": "text", "label": "Command", "label_ru": "Команда", "default": ""},
            {"id": "cwd", "type": "text", "label": "Working folder", "label_ru": "Рабочая папка", "default": ""},
        ),
    ),
}

# An operation the former window ran with the parameters of the manifest alone, whatever fields it
# inherits: the folder of the rollback copies opens without a form.
DIRECT_OPERATIONS = {"browser_bookmarks_open_local_backup"}


def field_id(field: dict[str, Any]) -> str:
    return str(field.get("id") or field.get("name") or "").strip()


def raw_kind(field: dict[str, Any]) -> str:
    return str(field.get("type", field.get("kind", "text"))).lower()


def is_checkbox_group(field: dict[str, Any]) -> bool:
    return raw_kind(field) in CHECKBOX_GROUP_KINDS


def is_badge_field(field: dict[str, Any]) -> bool:
    return raw_kind(field) in BADGE_KINDS


def is_smb_field(field: dict[str, Any]) -> bool:
    return raw_kind(field) in SMB_KINDS


def safe_language(language: str) -> str:
    return language if language in LANGUAGES else "en"


# The folders of the workbench: the former window filled a path field from its SOURCE or TARGET and
# did not draw it (`is_workbench_route_field`, `workbench_value_for_field`). The same words decide here.
_ROUTE_MARKERS = ("input", "output", "source", "destination", "target", "src", "dst",
                  "исход", "источник", "вход", "выход", "цель", "результ", "приём", "прием")
_PATH_MARKERS = ("path", "folder", "directory", "dir", "пап", "каталог", "путь")
_TARGET_MARKERS = ("output", "destination", "target", "dst", "выход", "цель", "результ", "приём", "прием")


def _haystack(field: dict[str, Any]) -> str:
    label_text = " ".join(str(field.get(item) or "").lower() for item in ("label", "label_ru", "title", "hint", "hint_ru", "placeholder"))
    return f"{field_id(field).lower()} {label_text}"


def is_route_field(field: dict[str, Any]) -> bool:
    if field.get("window_value"):
        return False
    if "workbench_route" in field and not bool(field.get("workbench_route")):
        # Managed system paths (policy folders, backup roots) keep their own value.
        return False
    kind = str(field.get("type", field.get("kind", ""))).lower()
    haystack = _haystack(field)
    return kind in {"path", "folder", "directory"} or (
        any(marker in haystack for marker in _ROUTE_MARKERS) and any(marker in haystack for marker in _PATH_MARKERS))


def route_role(field: dict[str, Any]) -> str:
    """Which folder of the workbench fills a route field: "target" or "source"."""
    return "target" if any(marker in _haystack(field) for marker in _TARGET_MARKERS) else "source"


def option_value(option: Any) -> Any:
    if isinstance(option, dict):
        return option.get("value", option.get("id", option.get("label", "")))
    return option


def option_source(field: dict[str, Any], operation_id: str = "") -> str:
    """Where the options of a field come from when the manifest does not list them: `module:function`."""
    if is_smb_field(field):
        return SMB_SOURCE
    return str(field.get("options_source") or field.get("source") or "").strip()


def resolve_options(source: str, root: Path, values: dict[str, Any]) -> list[Any]:
    """Ask a provider for its list: with the root and the values, with the root, or with nothing - as it takes them."""
    if ":" not in source:
        raise RuntimeError(f"Dynamic option source must use module:function syntax: {source}")
    module_name, function_name = source.split(":", 1)
    provider = getattr(importlib.import_module(module_name), function_name)
    try:
        count = len(inspect.signature(provider).parameters)
    except (TypeError, ValueError):
        count = 1
    if count >= 2:
        options = provider(root, dict(values))
    elif count == 1:
        options = provider(root)
    else:
        options = provider()
    if not isinstance(options, list):
        raise RuntimeError(f"Dynamic option source returned {type(options).__name__}, expected list.")
    return options


# How a live list is asked for when a default needs it; a test or a record puts its own here.
options_provider = None


def live_options(field: dict[str, Any], root: Path | None) -> list[Any]:
    """The options a provider gives a field now; [] when it gives none or fails, as the former window took it."""
    source = option_source(field)
    if not source or is_smb_field(field):
        return []
    if options_provider is not None:
        return list(options_provider(field))
    try:
        return resolve_options(source, root or Path(__file__).resolve().parents[2], {})
    except Exception:  # noqa: BLE001 - the former window put the failure into the list and took no default from it
        return []


def field_default(field: dict[str, Any], root: Path | None = None) -> Any:
    """The value a field has before anyone touched it (`field_default` of the former window).

    A group of ticks takes the ticks its options carry - the options of its provider, when it has
    one, as the former window read them.
    """
    if "default" in field:
        return field["default"]
    options = field.get("options", [])
    if is_checkbox_group(field):
        options = live_options(field, root) or (options if isinstance(options, list) else [])
        return [option.get("value", option.get("id", option.get("label")))
                for option in options if isinstance(option, dict) and option.get("default", False)]
    if isinstance(options, list) and options:
        first = options[0]
        if isinstance(first, dict):
            return first.get("value", first.get("id", ""))
        return first
    return ""


def form_fields(node: CommandNode | Operation) -> list[dict[str, Any]]:
    """The fields of the form of an operation: what the manifest gives it, and for the bookmarks those of the window."""
    if node.id in bookmarks_form.OPERATIONS:
        return bookmarks_form.fields_for(node.id, node.fields)
    if node.id in ai_form.OPERATIONS:
        return ai_form.fields_for(node.id, node.fields)
    return [dict(field) for field in node.fields]


def form_values(node: CommandNode | Operation, values: dict[str, Any], root: Path | None = None) -> dict[str, Any]:
    result = {field_id(field): field_default(field, root) for field in form_fields(node) if field_id(field)}
    result.update(values)
    return result


def matches(condition: Any, values: dict[str, Any]) -> bool:
    """`{key: value | [values]}`: every named field has one of its values."""
    if not isinstance(condition, dict) or not condition:
        return False
    for key, wanted in condition.items():
        accepted = wanted if isinstance(wanted, list) else [wanted]
        if not any(str(values.get(str(key))) == str(item) for item in accepted):
            return False
    return True


def build_parameters(node: CommandNode | Operation, values: dict[str, Any], source: str | Path, target: str | Path,
                     root: Path | None = None, remember: bool = True) -> dict[str, Any]:
    """The parameters of a run, as the former window built them (`operation_from_pending_command`).

    What the manifest sets, then every field: a badge gives nothing, the SMB login its pair (and is
    remembered, as the former window did at the start of a run), a folder of the workbench the
    folder chosen, any other field its value or its default. An operation without fields, and one
    the former window ran directly, gets the parameters of the manifest alone. RuntimeError where
    the former window refused to start.
    """
    source_path, target_path = Path(source), Path(target)

    if node.id in ai_form.OPERATIONS and "transfer_version" in values:
        if type(values["transfer_version"]) is not int or values["transfer_version"] != 3:
            raise RuntimeError("Unsupported AI transfer version; expected integer 3")
        return ai_form.parameters(node, values, source_path, target_path)

    def route_value(field: dict[str, Any]) -> str:
        return str(target_path if route_role(field) == "target" else source_path)

    if node.id in bookmarks_form.OPERATIONS:
        return bookmarks_form.parameters(node, node.fields, values, source_path, target_path,
                                         lambda field: field_default(field, root), is_route_field, route_value, is_badge_field)
    if node.id in DIRECT_OPERATIONS or not node.fields:
        return dict(node.parameters)
    parameters = dict(node.parameters)
    config = (root / "config") if root else None
    for field in node.fields:
        key = field_id(field)
        if not key or is_badge_field(field):
            continue
        if is_smb_field(field):
            told = smb_logins.run_parameters(values.get(key, field_default(field, root)), field_default(field, root), config, remember)
            parameters[key] = told["login"]
            parameters["smb_computer"] = told["smb_computer"]
            parameters["smb_user"] = told["smb_user"]
            continue
        if is_route_field(field):
            parameters[key] = route_value(field)
        else:
            parameters[key] = values.get(key, field_default(field, root))
    if node.id == "ai_backup_rollback":
        parameters["dry_run"] = parameters.pop("rollback_dry_run", True)
        parameters["overwrite_conflicts"] = parameters.pop("rollback_overwrite", False)
    return parameters


def unknown_values(node: CommandNode | Operation, values: dict[str, Any]) -> list[str]:
    """The names of values the operation has no field for: a mistyped name must not vanish quietly."""
    known = {field_id(field) for field in form_fields(node) if field_id(field)}
    return sorted(key for key in values if key not in known)


def refusals(node: CommandNode | Operation, values: dict[str, Any], root: Path | None = None) -> list[str]:
    """Why the form may not run as it stands, in the words of the former window (`validate_pending_fields`)."""
    found = []
    everything = form_values(node, values, root)
    for field in form_fields(node):
        key = field_id(field)
        if is_smb_field(field):
            config = (root / "config") if root else None
            computer, user = smb_logins.effective_login(smb_logins.login_state(everything.get(key), field_default(field, root), config))
            if not computer or not user:
                found.append("SMB: заполните имя компьютера и пользователя.")
            continue
        if not is_checkbox_group(field) or is_route_field(field):
            continue
        wanted = int(field.get("min_selected", 0) or 0)
        chosen = everything.get(key)
        if wanted > 0 and (not isinstance(chosen, list) or len(chosen) < wanted):
            found.append(f"fewer ticks than the field asks for: {key}")
    return found


def wrong_choices(node: CommandNode | Operation, values: dict[str, Any], root: Path | None = None) -> list[str]:
    """Values that are none of the options the manifest lists for their field, as "field=value".

    A window cannot give such a value; a command line can. Only a field with its options written in
    the manifest is judged, and its own default always passes.
    """
    wrong = []
    for field in form_fields(node):
        key = field_id(field)
        options = field.get("options")
        if key not in values or option_source(field) or not isinstance(options, list) or not options:
            continue
        kind = raw_kind(field)
        if kind not in CHECKBOX_GROUP_KINDS and kind not in {"radio", "select", "tabs"}:
            continue
        default = field_default(field, root)
        known = {str(option_value(option)) for option in options}
        given = values[key] if isinstance(values[key], (list, tuple)) else [values[key]]
        allowed = set(default) if isinstance(default, list) else {default}
        wrong.extend(f"{key}={item}" for item in given if str(item) not in known and item not in allowed)
    return wrong


def coerce(field: dict[str, Any], text: str) -> Any:
    """A value of the command line (`--set name=value`) in the shape the field expects."""
    kind = raw_kind(field)
    if kind in CHECKBOX_KINDS:
        lowered = text.strip().lower()
        if lowered in {"1", "true", "yes", "on"}:
            return True
        if lowered in {"0", "false", "no", "off", ""}:
            return False
        raise ValueError("true or false is expected")
    if kind in NUMBER_KINDS:
        number = float(text.replace(",", "."))
        return int(number) if number.is_integer() else number
    if kind in CHECKBOX_GROUP_KINDS:
        return [item.strip() for item in text.split(",") if item.strip()]
    if kind in SMB_KINDS:
        computer, _, user = text.partition("|")
        return {"computer_manual": computer.strip(), "user_manual": user.strip()}
    return text


def all_nodes(manifest: ToolManifest):
    def walk(nodes):
        for node in nodes:
            yield node
            yield from walk(node.children)

    yield from walk(manifest.operation_groups)
    yield from manifest.operations
    yield from manifest.maintenance_operations
    yield from CARD_OPERATIONS.values()


def find_node(manifest: ToolManifest, node_id: str, runs: bool = True) -> CommandNode | Operation | None:
    """A node of the manifest by its id; with `runs` - only one that has a service to run."""
    for node in all_nodes(manifest):
        if node.id == node_id and (node.service or not runs):
            return node
    return None


def question(node: CommandNode | Operation, parameters: dict[str, Any], language: str) -> dict[str, Any]:
    """The question before a run: asked or not, and what it says (`start_operation` of the former window)."""
    operation = node.to_operation(parameters) if isinstance(node, CommandNode) else dataclasses.replace(node, parameters=dict(parameters))
    if not operation_requires_confirmation(operation):
        return {"ask": False}
    said = confirm_notes.words(language)
    return {
        "ask": True,
        "title": said["confirm_title"],
        "operation": operation.display_title(language),
        "description": operation.display_description(language),
        "risk": confirm_notes.risk_level_text(operation.risk_level, language),
        "impact_title": said["confirm_impact_title"],
        "notes": confirm_notes.dangerous_operation_notes(operation, language),
        "note": said["confirm_note"],
        "run": said["confirm_run_dangerous"],
    }


def describe_option(option: Any) -> dict[str, Any]:
    if not isinstance(option, dict):
        return {"value": option, "label": str(option)}
    row = dict(option)
    row["value"] = option_value(option)
    row["label"] = str(option.get("label") or option.get("title") or row["value"])
    return row


def describe_options(field: dict[str, Any], options: list[Any]) -> list[dict[str, Any]]:
    return [describe_option(option) for option in options]


def describe_field(field: dict[str, Any], operation_id: str) -> dict[str, Any]:
    """A field as the manifest wrote it, plus what the window needs to know of it; no provider is asked."""
    row = dict(field)
    row["id"] = field_id(field)
    row["kind"] = raw_kind(field)
    # The block of the form the field stands in: the manifest names it `group` (`section` in older entries).
    row["group"] = str(field.get("group") or field.get("section") or "parameters")
    row["route"] = route_role(field) if is_route_field(field) else ""
    if isinstance(field.get("options"), list):
        row["options"] = describe_options(field, field["options"])
    elif isinstance(field.get("items"), list):
        # The badges of an `info_badges` field are written as `items`: the window reads the options of a field, and
        # without this it drew the name of the field over an empty row (the review of 16.10.2026).
        row["options"] = describe_options(field, field["items"])
    source = option_source(field, operation_id)
    if source:
        row["options_source"] = source
    return row


LOOK_KEYS = ("icon", "block", "block_ru", "tone", "action_group", "action_group_ru", "action_group_tone", "action_tone", "ui_layout")


def describe_node(node: CommandNode | Operation, raw: dict[str, Any] | None = None) -> dict[str, Any]:
    raw = raw if isinstance(raw, dict) else {}
    children = tuple(getattr(node, "children", ()))
    raw_children = {str(item.get("id", "")).strip(): item for item in raw.get("children", []) if isinstance(item, dict)}
    looks = {key: raw[key] for key in LOOK_KEYS if key in raw}
    return {
        "id": node.id, "title": node.title, "title_ru": node.title_ru,
        "description": node.description, "description_ru": node.description_ru,
        "tooltip": raw.get("tooltip", ""), "tooltip_ru": raw.get("tooltip_ru", ""),
        "kind": node.kind, "risk_level": node.risk_level, "runs": bool(node.service),
        "parameters": dict(node.parameters), **looks,
        "fields": [describe_field(field, node.id) for field in form_fields(node) if field_id(field)] if node.service else [],
        "children": [describe_node(child, raw_children.get(child.id)) for child in children],
    }


def share_forms(told: dict[str, Any]) -> dict[str, Any]:
    """The description with every form told once: `forms` - a name and its fields - and the nodes naming theirs.

    The same fields stand under many buttons (the adapters of the network page, the fields of the
    bookmarks); told with every one of them, the answer would repeat itself. A node carries `form` -
    the name of its form, "" when it has none - in place of `fields`:

        fields of a node  = forms[node["form"]]
    """
    forms: dict[str, list[dict[str, Any]]] = {}
    names: dict[str, str] = {}

    def name_of(fields: list[dict[str, Any]], asked_by: str) -> str:
        if not fields:
            return ""
        key = json.dumps(fields, ensure_ascii=False, sort_keys=True, default=str)
        if key not in names:
            name = asked_by
            while name in forms:
                name += "+"
            names[key] = name
            forms[name] = fields
        return names[key]

    def walk(nodes: list[dict[str, Any]]) -> None:
        for node in nodes:
            node["form"] = name_of(node.pop("fields", []), node["id"])
            walk(node.get("children") or [])

    for part in ("nodes", "maintenance", "card_operations"):
        walk(told.get(part) or [])
    layout = told.get("layout") or {}
    places = [place for section in layout.get("sections") or [] for page in section.get("pages") or []
              for card in page.get("cards") or [] for place in [*(card.get("operations") or []), *(card.get("guests") or [])]]
    for place in places + list(layout.get("service") or []) + list(layout.get("folders") or []):
        place["form"] = name_of(place.pop("fields", []), place["id"])
        place.pop("children", None)
    told["forms"] = forms
    return told


def describe(manifest: ToolManifest) -> dict[str, Any]:
    """The manifest taken apart: what a window draws its operations and fields by."""
    def raw_by_id(key: str) -> dict[str, Any]:
        return {str(item.get("id", "")).strip(): item for item in manifest.raw.get(key, []) if isinstance(item, dict)}

    groups, maintenance = raw_by_id("operation_groups"), raw_by_id("maintenance_operations")
    return {
        "tool": dict(manifest.raw.get("tool", {})),
        "nodes": [describe_node(node, groups.get(node.id)) for node in manifest.operation_groups],
        "maintenance": [describe_node(node, maintenance.get(node.id)) for node in manifest.maintenance_operations],
        "card_operations": [describe_node(node) for node in CARD_OPERATIONS.values()],
    }
