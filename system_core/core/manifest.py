from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from .config import load_yaml_or_json


@dataclass(frozen=True)
class Operation:
    id: str
    title: str
    description: str
    service: str
    kind: str = "safe"
    risk_level: str = ""
    title_ru: str = ""
    description_ru: str = ""
    parameters: dict[str, Any] = field(default_factory=dict)
    fields: tuple[dict[str, Any], ...] = ()

    def display_title(self, language: str) -> str:
        if language == "ru" and self.title_ru:
            return self.title_ru
        return self.title

    def display_description(self, language: str) -> str:
        if language == "ru" and self.description_ru:
            return self.description_ru
        return self.description


@dataclass(frozen=True)
class CommandNode:
    id: str
    title: str
    description: str = ""
    service: str = ""
    kind: str = "safe"
    risk_level: str = ""
    ui_layout: str = ""
    surface: str = ""
    section: str = ""
    action_group: str = ""
    action_group_ru: str = ""
    action_group_tone: str = ""
    action_tone: str = ""
    title_ru: str = ""
    description_ru: str = ""
    parameters: dict[str, Any] = field(default_factory=dict)
    fields: tuple[dict[str, Any], ...] = ()
    children: tuple["CommandNode", ...] = ()

    def display_title(self, language: str) -> str:
        if language == "ru" and self.title_ru:
            return self.title_ru
        return self.title

    def display_description(self, language: str) -> str:
        if language == "ru" and self.description_ru:
            return self.description_ru
        return self.description

    def to_operation(self, parameters: dict[str, Any] | None = None) -> Operation:
        return Operation(
            id=self.id,
            title=self.title,
            description=self.description,
            service=self.service,
            kind=self.kind,
            risk_level=self.risk_level,
            title_ru=self.title_ru,
            description_ru=self.description_ru,
            parameters=dict(parameters if parameters is not None else self.parameters),
            fields=self.fields,
        )


@dataclass(frozen=True)
class ToolManifest:
    raw: dict[str, Any]
    operations: list[Operation]
    maintenance_operations: list[Operation]
    operation_groups: list[CommandNode]


def _truthy_parameter(value: Any, *, default: bool = False) -> bool:
    if value is None:
        return default
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return bool(value)
    text = str(value).strip().lower()
    if not text:
        return default
    if text in {"1", "true", "yes", "y", "on"}:
        return True
    if text in {"0", "false", "no", "n", "off"}:
        return False
    return default


def operation_requires_confirmation(operation: Operation) -> bool:
    if str(operation.kind).strip().lower() != "dangerous":
        return False

    params = operation.parameters
    mode = str(params.get("mode") or "").strip().lower()
    dry_run = _truthy_parameter(params.get("dry_run"), default=False)

    if mode == "apps_control":
        action = str(params.get("apps_action") or "status").strip().lower()
        if action in {"status", "open_logs"}:
            return False
        if action in {"remove", "keep_removed", "provision"}:
            return not dry_run
        return True

    if mode == "edge_control":
        action = str(params.get("edge_action") or "status").strip().lower()
        if action == "status":
            return False
        return not dry_run

    if mode == "policy_control":
        action = str(params.get("policy_action") or "status").strip().lower()
        if action in {"status", "open_profiles", "open_policy", "open_backups"}:
            return False
        if action == "cleanup":
            return not _truthy_parameter(params.get("cleanup_dry_run"), default=True)
        return True

    if mode == "guards_control":
        action = str(params.get("guard_action") or "status").strip().lower()
        return action in {"enable", "disable"}

    if mode == "snapshot_control":
        action = str(params.get("snapshot_action") or "status").strip().lower()
        if action in {"status", "open_snapshots"}:
            return False
        if action == "capture":
            return not dry_run
        return True

    if mode == "groups_control":
        action = str(params.get("group_action") or "status").strip().lower()
        if action == "status":
            return False
        if action in {"commit", "compose"}:
            return not dry_run
        return True

    return True


def _extract_i18n(item: dict[str, Any], key: str) -> dict[str, Any]:
    value = item.get(f"{key}_i18n", {})
    return value if isinstance(value, dict) else {}


def _extract_parameters(item: dict[str, Any]) -> dict[str, Any]:
    value = item.get("parameters", item.get("params", {}))
    return dict(value) if isinstance(value, dict) else {}


def _extract_fields(item: dict[str, Any]) -> tuple[dict[str, Any], ...]:
    value = item.get("fields", [])
    if not isinstance(value, list):
        return ()
    return tuple(dict(field) for field in value if isinstance(field, dict))


def _parse_operation(item: dict[str, Any]) -> Operation:
    title_i18n = _extract_i18n(item, "title")
    description_i18n = _extract_i18n(item, "description")
    return Operation(
        id=str(item.get("id", "")).strip(),
        title=str(item.get("title", title_i18n.get("en", ""))).strip(),
        description=str(item.get("description", description_i18n.get("en", ""))).strip(),
        service=str(item.get("service", "")).strip(),
        kind=str(item.get("kind", "safe")).strip() or "safe",
        risk_level=str(item.get("risk_level", "")).strip(),
        title_ru=str(item.get("title_ru", title_i18n.get("ru", ""))).strip(),
        description_ru=str(item.get("description_ru", description_i18n.get("ru", ""))).strip(),
        parameters=_extract_parameters(item),
        fields=_extract_fields(item),
    )


def _parse_command_node(
    item: dict[str, Any],
    inherited_parameters: dict[str, Any] | None = None,
    inherited_fields: tuple[dict[str, Any], ...] = (),
    inherited_surface: str = "",
    inherited_section: str = "",
) -> CommandNode:
    title_i18n = _extract_i18n(item, "title")
    description_i18n = _extract_i18n(item, "description")
    parameters = dict(inherited_parameters or {})
    parameters.update(_extract_parameters(item))
    fields = (*inherited_fields, *_extract_fields(item))
    surface = str(item.get("surface", inherited_surface)).strip()
    section = str(
        item.get(
            "command_section",
            item.get("ui_section", item.get("section", inherited_section)),
        )
    ).strip()
    children_raw = item.get("children", [])
    children = tuple(
        _parse_command_node(child, parameters, fields, surface, section)
        for child in children_raw
        if isinstance(child, dict)
    )
    return CommandNode(
        id=str(item.get("id", "")).strip(),
        title=str(item.get("title", title_i18n.get("en", ""))).strip(),
        description=str(item.get("description", description_i18n.get("en", ""))).strip(),
        service=str(item.get("service", "")).strip(),
        kind=str(item.get("kind", "safe")).strip() or "safe",
        risk_level=str(item.get("risk_level", "")).strip(),
        ui_layout=str(item.get("ui_layout", item.get("layout", ""))).strip(),
        surface=surface,
        section=section,
        action_group=str(item.get("action_group", item.get("command_group", ""))).strip(),
        action_group_ru=str(item.get("action_group_ru", item.get("command_group_ru", ""))).strip(),
        action_group_tone=str(item.get("action_group_tone", item.get("group_tone", ""))).strip(),
        action_tone=str(item.get("action_tone", item.get("button_tone", ""))).strip(),
        title_ru=str(item.get("title_ru", title_i18n.get("ru", ""))).strip(),
        description_ru=str(item.get("description_ru", description_i18n.get("ru", ""))).strip(),
        parameters=parameters,
        fields=fields,
        children=children,
    )


def load_manifest(path: Path) -> ToolManifest:
    raw = load_yaml_or_json(path)
    operations = [_parse_operation(item) for item in raw.get("operations", [])]
    maintenance = [_parse_operation(item) for item in raw.get("maintenance_operations", [])]
    operation_groups = [
        _parse_command_node(item)
        for item in raw.get("operation_groups", [])
        if isinstance(item, dict)
    ]

    for operation in [*operations, *maintenance]:
        if not operation.id:
            raise ValueError("Operation id is empty.")
        if ":" not in operation.service:
            raise ValueError(f"Operation service must use module:function syntax: {operation.id}")

    def validate_node(node: CommandNode) -> None:
        if not node.id:
            raise ValueError("Command node id is empty.")
        if node.children:
            for child in node.children:
                validate_node(child)
            return
        if ":" not in node.service:
            raise ValueError(f"Leaf command service must use module:function syntax: {node.id}")

    for group in operation_groups:
        validate_node(group)

    return ToolManifest(
        raw=raw,
        operations=operations,
        maintenance_operations=maintenance,
        operation_groups=operation_groups,
    )
