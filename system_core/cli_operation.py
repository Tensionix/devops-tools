from __future__ import annotations

import argparse
import json
import sys
from dataclasses import replace
from pathlib import Path
from typing import Any, Iterable

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from system_core.core.jobs import execute_operation
from system_core.core.manifest import CommandNode, Operation, load_manifest, operation_requires_confirmation
from system_core.core.paths import ensure_project_dirs, get_project_paths


def iter_leaf_nodes(nodes: Iterable[CommandNode]) -> Iterable[CommandNode]:
    for node in nodes:
        if node.children:
            yield from iter_leaf_nodes(node.children)
        else:
            yield node


def field_defaults(fields: tuple[dict[str, Any], ...]) -> dict[str, Any]:
    defaults: dict[str, Any] = {}
    for field in fields:
        field_id = str(field.get("id", "")).strip()
        if field_id and "default" in field:
            defaults[field_id] = field["default"]
    return defaults


def find_operation(operation_id: str) -> Operation:
    paths = get_project_paths()
    manifest = load_manifest(paths.config / "tool_manifest.yaml")

    for operation in [*manifest.operations, *manifest.maintenance_operations]:
        if operation.id == operation_id:
            defaults = field_defaults(operation.fields)
            defaults.update(operation.parameters)
            return replace(operation, parameters=defaults)

    for node in iter_leaf_nodes(manifest.operation_groups):
        if node.id == operation_id:
            parameters = field_defaults(node.fields)
            parameters.update(node.parameters)
            return node.to_operation(parameters)

    raise SystemExit(f"Operation was not found in manifest: {operation_id}")


def parse_value(raw: str) -> Any:
    text = raw.strip()
    lowered = text.lower()
    if lowered == "true":
        return True
    if lowered == "false":
        return False
    if lowered == "null":
        return None
    if text.startswith(("[", "{")):
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            return raw
    return raw


def parse_param(raw: str) -> tuple[str, Any]:
    if "=" not in raw:
        raise SystemExit(f"Parameter must use key=value syntax: {raw}")
    key, value = raw.split("=", 1)
    key = key.strip()
    if not key:
        raise SystemExit(f"Parameter key is empty: {raw}")
    return key, parse_value(value)


def build_operation(operation_id: str, raw_params: list[str], raw_json_params: list[str]) -> Operation:
    operation = find_operation(operation_id)
    parameters = dict(operation.parameters)
    for raw in raw_params:
        key, value = parse_param(raw)
        parameters[key] = value
    for raw in raw_json_params:
        key, value = parse_param(raw)
        if isinstance(value, str):
            try:
                value = json.loads(value)
            except json.JSONDecodeError as exc:
                raise SystemExit(f"Invalid JSON parameter {key}: {exc}") from exc
        parameters[key] = value
    return replace(operation, parameters=parameters)


def requires_dangerous_confirmation(operation: Operation) -> bool:
    return operation_requires_confirmation(operation)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run one Audion DevOps Tools manifest operation.")
    parser.add_argument("operation_id", help="Leaf operation id from config/tool_manifest.yaml.")
    parser.add_argument("--param", action="append", default=[], metavar="KEY=VALUE", help="Override operation parameter.")
    parser.add_argument("--json-param", action="append", default=[], metavar="KEY=JSON", help="Override parameter with JSON value.")
    parser.add_argument("--quiet-json", action="store_true", help="Do not print result JSON.")
    parser.add_argument(
        "--yes-i-understand",
        action="store_true",
        help="Confirm that a dangerous operation is intentional.",
    )
    args = parser.parse_args(argv)

    paths = get_project_paths(PROJECT_ROOT)
    ensure_project_dirs(paths)
    operation = build_operation(args.operation_id, args.param, args.json_param)
    if requires_dangerous_confirmation(operation) and not args.yes_i_understand:
        raise SystemExit(f"Dangerous operation requires --yes-i-understand: {operation.id}")

    result = execute_operation(paths, operation, log_callback=print)
    if not args.quiet_json:
        print("")
        print(json.dumps({"ok": result.ok, "message": result.message, "data": result.data}, ensure_ascii=False, indent=2))
    return 0 if result.ok else 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
