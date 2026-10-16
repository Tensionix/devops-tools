"""Where every operation stands in the window on Avalonia: config/window_layout.yaml taken apart.

The manifest says what an operation is; the layout says where it stands - a section (a large button
under the header), a page of the section (the row under the sections), a card of the page. The
console command hands both to the window (`describe`), and the window knows no section and no
operation by its name.

A card is one of three:

  op      an operation with its form; `guests` are operations whose buttons stand in the same card
          and read the same fields (a status beside the action it checks)
  switch  a switch of the state of the machine: a row of operations, each bringing the machine into
          one state (`is`); the one the machine is in now is lit - the window asks `state --page`. The
          form of the card is the form of the first operation of the row
  pick    a choice of the operation the one run button of the card starts: a row over the form, the
          form follows the operation chosen

Each card may name its `block` (the frame it stands in, with its neighbours of the same name), its
`icon`, its `tone` ("run" - the main action of its block, a filled button; "burn" - it removes) and
`form: none` (the operation runs on its defaults). A page may say `state: true` (it has switches) and
`source: true` (its operations read a file or a folder). Every section and every page has its line
`about` / `about_ru`, and every section has at least two pages - the owner, 15.10.2026: "все разделы
должны иметь подстрочники и внутренние подразделы".

An operation of the manifest that stands nowhere here must be named in `service`, `folders`,
`pending` or `retired` - tests/test_window_layout.py checks it.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

from . import operation_model as model
from .config import load_yaml_or_json
from .manifest import ToolManifest

FILE_NAME = "window_layout.yaml"
LOOKS = ("icon", "block", "block_ru", "tone", "title", "title_ru", "about", "about_ru")


def load(config_folder: Path) -> dict[str, Any]:
    path = config_folder / FILE_NAME
    if not path.is_file():
        return {}
    raw = load_yaml_or_json(path)
    return raw if isinstance(raw, dict) else {}


def card_kind(card: dict[str, Any]) -> str:
    if card.get("switch"):
        return "switch"
    if card.get("pick"):
        return "pick"
    return "op"


def card_entries(card: dict[str, Any]) -> list[dict[str, Any]]:
    """The operations of a card in their order: the row of a switch or a pick, or the host; then the guests."""
    kind = card_kind(card)
    if kind == "op":
        rows = [card]
    else:
        rows = [entry for entry in card.get("options") or [] if isinstance(entry, dict)]
    rows.extend(guest for guest in card.get("guests") or [] if isinstance(guest, dict))
    return rows


def placed(layout: dict[str, Any]) -> list[str]:
    """Every id the layout gives a button to."""
    ids = []
    for section in layout.get("sections") or []:
        for page in section.get("pages") or []:
            for card in page.get("cards") or []:
                ids.extend(str(entry.get("op") or "").strip() for entry in card_entries(card))
    for row in ("service", "folders"):
        ids.extend(str(item.get("op") or "").strip() for item in layout.get(row) or [] if isinstance(item, dict))
    return ids


def folder_operations(layout: dict[str, Any]) -> set[str]:
    """The operations of the working folders of the program: they work on its own input and output."""
    return {str(item.get("op") or "").strip() for item in layout.get("folders") or [] if isinstance(item, dict)}


def _operation(manifest: ToolManifest, entry: dict[str, Any]) -> dict[str, Any] | None:
    node = model.find_node(manifest, str(entry.get("op") or "").strip())
    if node is None:
        return None
    row = model.describe_node(node)
    row["children"] = []
    if str(entry.get("form") or "") == "none":
        row["fields"] = []
    for key in LOOKS:
        if entry.get(key):
            row["place_" + key] = str(entry[key])
    if "is" in entry:
        row["is"] = str(entry["is"])
    row["direct"] = bool(row["runs"]) and not [field for field in row["fields"] if not field.get("route") and not field.get("hidden")]
    return row


def _card(manifest: ToolManifest, card: dict[str, Any]) -> dict[str, Any]:
    kind = card_kind(card)
    main = card_entries(card)[: (len(card.get("options") or []) if kind != "op" else 1)]
    guests = [guest for guest in card.get("guests") or [] if isinstance(guest, dict)]
    told = {
        "kind": kind,
        "id": str(card.get("switch") or card.get("pick") or card.get("op") or ""),
        "state": str(card.get("state") or card.get("switch") or "") if kind == "switch" else "",
        "operations": [row for row in (_operation(manifest, entry) for entry in main) if row is not None],
        "guests": [row for row in (_operation(manifest, entry) for entry in guests) if row is not None],
    }
    for key in LOOKS:
        told[key] = str(card.get(key) or "")
    return told


def describe(layout: dict[str, Any], manifest: ToolManifest) -> dict[str, Any]:
    """The layout with every operation described: what the window draws its sections and pages by."""
    sections = []
    for section in layout.get("sections") or []:
        pages = []
        for page in section.get("pages") or []:
            pages.append({key: page.get(key, "") for key in ("id", "title", "title_ru", "icon", "about", "about_ru")}
                         | {"source": page.get("source") is True, "state": page.get("state") is True,
                            "away": [str(name) for name in page.get("away") or []],
                            "cards": [_card(manifest, card) for card in page.get("cards") or [] if isinstance(card, dict)]})
        sections.append({key: section.get(key, "") for key in ("id", "title", "title_ru", "icon", "about", "about_ru")}
                        | {"pages": pages})
    rows: dict[str, list[dict[str, Any]]] = {"service": [], "folders": []}
    for name, operations in rows.items():
        for entry in layout.get(name) or []:
            row = _operation(manifest, entry) if isinstance(entry, dict) else None
            if row is not None:
                operations.append(row)
    return {"sections": sections, "service": rows["service"], "folders": rows["folders"], "shared": shared(layout),
            "menu": [dict(item) for item in layout.get("menu") or [] if isinstance(item, dict)],
            "pending": dict(layout.get("pending") or {}), "retired": list(layout.get("retired") or [])}


def shared(layout: dict[str, Any]) -> list[str]:
    """The fields whose value is one for the whole window; every other field belongs to its page."""
    return [str(name).strip() for name in layout.get("shared") or [] if str(name).strip()]


def problems(layout: dict[str, Any], manifest: ToolManifest) -> list[str]:
    """What is wrong with the layout, in words; an empty list when nothing is."""
    found: list[str] = []
    known = {model.field_id(field) for node in model.all_nodes(manifest) for field in model.form_fields(node)}
    for name in shared(layout):
        if name not in known:
            found.append(f"`shared` names a field no operation has: {name!r}")
    runs = {node.id for node in model.all_nodes(manifest) if node.service} - set(model.CARD_OPERATIONS)
    stands = placed(layout)
    for name in stands:
        if name not in runs:
            found.append(f"the layout names an operation the manifest does not have: {name!r}")
    seen: set[str] = set()
    for name in stands:
        if name in seen:
            found.append(f"an operation stands in the window twice: {name!r}")
        seen.add(name)
    aside = set(layout.get("pending") or {}) | set(layout.get("retired") or [])
    for name in sorted(aside - runs):
        found.append(f"`pending` or `retired` names an operation the manifest does not have: {name!r}")
    for name in sorted(runs - set(stands) - aside):
        found.append(f"an operation of the manifest stands nowhere in the window: {name!r}")
    for name in sorted(set(stands) & aside):
        found.append(f"an operation both stands in the window and is set aside: {name!r}")
    ids = []
    for section in layout.get("sections") or []:
        where_section = str(section.get("id") or "?")
        ids.append(where_section)
        for key in ("title", "title_ru", "about", "about_ru", "icon"):
            if not str(section.get(key) or "").strip():
                found.append(f"the section {where_section!r} has no {key}")
        pages = section.get("pages") or []
        if len(pages) < 2:
            found.append(f"the section {where_section!r} has fewer than two pages")
        page_ids = []
        for page in pages:
            where = f"{where_section}/{page.get('id')}"
            page_ids.append(str(page.get("id") or ""))
            for key in ("title", "title_ru", "icon"):
                if not str(page.get(key) or "").strip():
                    found.append(f"the page {where} has no {key}")
            if not page.get("cards"):
                found.append(f"the page {where} has no cards")
            # A field set on another page: only a field whose value is one for the whole window can stand away.
            for name in page.get("away") or []:
                if str(name) not in shared(layout):
                    found.append(f"the page {where} puts away {name!r}, which is not a field of the whole window (`shared`)")
            has_switch = False
            for card in page.get("cards") or []:
                kind = card_kind(card)
                if kind == "switch":
                    has_switch = True
                    values = [str(entry.get("is") or "") for entry in card.get("options") or []]
                    if "" in values or len(values) != len(set(values)):
                        found.append(f"the switch {card.get('switch')!r} of {where} names its states badly: {values}")
                if kind != "op" and len(card.get("options") or []) < 2:
                    found.append(f"the {kind} {card.get(kind)!r} of {where} has fewer than two options")
                if kind == "op" and not str(card.get("op") or "").strip():
                    found.append(f"a card of {where} names no operation")
            if has_switch and page.get("state") is not True:
                found.append(f"the page {where} has a switch but no `state: true`")
        if len(page_ids) != len(set(page_ids)):
            found.append(f"the section {where_section!r} names a page twice")
    if len(ids) != len(set(ids)):
        found.append("the layout names a section twice")
    return found
