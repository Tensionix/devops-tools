from __future__ import annotations

import argparse
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml


ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "config" / "tool_manifest.yaml"
README = ROOT / "docs" / "README_AUDION_DEVOPS_TOOLS_RU.md"
GUIDE_RU = ROOT / "docs" / "USER_GUIDE_RU.md"
GUIDE_EN = ROOT / "docs" / "USER_GUIDE_EN.md"

README_BEGIN = "<!-- BEGIN GENERATED COMMAND CATALOG -->"
README_END = "<!-- END GENERATED COMMAND CATALOG -->"
GUIDE_BEGIN = "<!-- BEGIN GENERATED PARAMETER REFERENCE -->"
GUIDE_END = "<!-- END GENERATED PARAMETER REFERENCE -->"


@dataclass(frozen=True)
class CommandDoc:
    node: dict[str, Any]
    path: tuple[dict[str, Any], ...]
    fields: tuple[dict[str, Any], ...]


def _merge_fields(parent: tuple[dict[str, Any], ...], own: list[dict[str, Any]] | None) -> tuple[dict[str, Any], ...]:
    merged = {str(field.get("id")): field for field in parent if field.get("id")}
    for field in own or []:
        if field.get("id"):
            merged[str(field["id"])] = field
    return tuple(merged.values())


def collect_commands(data: dict[str, Any]) -> list[CommandDoc]:
    result: list[CommandDoc] = []

    def walk(nodes: list[dict[str, Any]] | None, path: tuple[dict[str, Any], ...], fields: tuple[dict[str, Any], ...]) -> None:
        for node in nodes or []:
            inherited = _merge_fields(fields, node.get("fields"))
            if node.get("children"):
                walk(node["children"], path + (node,), inherited)
            elif node.get("id") and node.get("service"):
                result.append(CommandDoc(node=node, path=path, fields=inherited))

    walk(data.get("operation_groups"), (), ())
    for section, title_ru, title_en in (
        ("operations", "Прочие операции", "Other operations"),
        ("maintenance_operations", "Обслуживание", "Maintenance"),
    ):
        synthetic = {"title_ru": title_ru, "title": title_en}
        for node in data.get(section) or []:
            result.append(CommandDoc(node=node, path=(synthetic,), fields=tuple(node.get("fields") or [])))
    return result


def text(node: dict[str, Any], key: str, lang: str) -> str:
    localized = node.get(f"{key}_ru") if lang == "ru" else node.get(key)
    fallback = node.get(key) or node.get(f"{key}_ru") or ""
    return str(localized or fallback).strip()


def command_path(command: CommandDoc, lang: str) -> str:
    names = [text(node, "title", lang) for node in command.path]
    names.append(text(command.node, "title", lang))
    return " > ".join(name for name in names if name)


def risk_text(node: dict[str, Any]) -> str:
    kind = str(node.get("kind") or "safe")
    risk = str(node.get("risk_level") or "readonly")
    return f"kind=`{kind}`, risk_level=`{risk}`"


def render_readme(commands: list[CommandDoc]) -> str:
    lines = [
        README_BEGIN,
        "## Полный Каталог Команд",
        "",
        "Этот каталог генерируется из `config\\tool_manifest.yaml`. Он содержит все команды и полный текст, который используется как пользовательская подсказка в GUI. Цвет кнопки не заменяет `kind`, `risk_level`, подтверждение и журнал.",
        "",
    ]
    current = ""
    for command in commands:
        section = text(command.path[0], "title", "ru") if command.path else "Операции"
        if section != current:
            lines.extend([f"### {section}", ""])
            current = section
        title = command_path(command, "ru")
        description = text(command.node, "description", "ru")
        lines.append(f"- **{title}** (`{command.node['id']}`) — {description} _{risk_text(command.node)}._")
    lines.extend(["", README_END])
    return "\n".join(lines)


def format_value(value: Any) -> str:
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, (list, dict)):
        return f"`{yaml.safe_dump(value, allow_unicode=True, default_flow_style=True).strip()}`"
    return f"`{value}`"


def render_guide(commands: list[CommandDoc], lang: str) -> str:
    ru = lang == "ru"
    lines = [
        GUIDE_BEGIN,
        "## Полный Справочник Команд И Параметров" if ru else "## Complete Command And Parameter Reference",
        "",
        (
            "Справочник генерируется из `config\\tool_manifest.yaml`. Он включает весь текст GUI-подсказок, risk-классификацию, наследуемые поля, defaults и варианты выбора. Практические сценарии и объяснение последствий находятся в ручных разделах выше."
            if ru
            else "This reference is generated from `config\\tool_manifest.yaml`. It includes every GUI description, risk classification, inherited field, default and selectable option. Practical workflows and consequence notes remain in the authored sections above."
        ),
        "",
    ]
    for command in commands:
        lines.extend(
            [
                f"### {command_path(command, lang)}",
                "",
                f"- {'Operation id' if not ru else 'Operation id'}: `{command.node['id']}`",
                f"- {'Description' if not ru else 'Описание'}: {text(command.node, 'description', lang)}",
                f"- {'Risk' if not ru else 'Риск'}: {risk_text(command.node)}",
            ]
        )
        if command.fields:
            lines.append(f"- {'Parameters' if not ru else 'Параметры'}:")
            for field in command.fields:
                field_id = field.get("id", "")
                label = text(field, "label", lang) or str(field_id)
                field_type = field.get("type", "text")
                description = text(field, "description", lang)
                details = [f"type=`{field_type}`"]
                if "default" in field:
                    details.append(f"default={format_value(field['default'])}")
                lines.append(f"  - `{field_id}` — **{label}** ({', '.join(details)}). {description}".rstrip())
                options = field.get("options") or []
                if options:
                    rendered = []
                    for option in options:
                        if isinstance(option, dict):
                            rendered.append(f"`{option.get('value')}` — {text(option, 'label', lang) or option.get('value')}")
                        else:
                            rendered.append(f"`{option}`")
                    lines.append(f"    - {'Варианты' if ru else 'Options'}: " + "; ".join(rendered))
        else:
            lines.append(f"- {'Parameters' if not ru else 'Параметры'}: {'none' if not ru else 'нет'}.")
        lines.append("")
    lines.append(GUIDE_END)
    return "\n".join(lines)


def replace_block(source: str, begin: str, end: str, block: str, insert_before: str | None = None) -> str:
    if begin in source and end in source:
        start = source.index(begin)
        finish = source.index(end, start) + len(end)
        return source[:start] + block + source[finish:]
    if insert_before and insert_before in source:
        return source.replace(insert_before, block + "\n\n" + insert_before, 1)
    return source.rstrip() + "\n\n" + block + "\n"


def sync(check: bool) -> int:
    data = yaml.safe_load(MANIFEST.read_text(encoding="utf-8")) or {}
    commands = collect_commands(data)
    targets = {
        README: replace_block(README.read_text(encoding="utf-8"), README_BEGIN, README_END, render_readme(commands), "## Терминал"),
        GUIDE_RU: replace_block(GUIDE_RU.read_text(encoding="utf-8"), GUIDE_BEGIN, GUIDE_END, render_guide(commands, "ru")),
        GUIDE_EN: replace_block(GUIDE_EN.read_text(encoding="utf-8"), GUIDE_BEGIN, GUIDE_END, render_guide(commands, "en")),
    }
    changed = [path for path, content in targets.items() if path.read_text(encoding="utf-8") != content]
    if check:
        for path in changed:
            print(f"[STALE] {path.relative_to(ROOT)}")
        return 1 if changed else 0
    for path, content in targets.items():
        path.write_text(content.rstrip() + "\n", encoding="utf-8")
        print(f"[OK] {path.relative_to(ROOT)}")
    print(f"[OK] Commands documented: {len(commands)}")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Synchronize manifest-derived project documentation.")
    parser.add_argument("--check", action="store_true", help="Fail when generated documentation is stale.")
    args = parser.parse_args()
    return sync(args.check)


if __name__ == "__main__":
    raise SystemExit(main())
