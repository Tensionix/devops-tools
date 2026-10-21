from __future__ import annotations

from copy import deepcopy
from pathlib import Path

import pytest

from system_core.core import operation_model, window_layout
from system_core.core.manifest import load_manifest


ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(scope="module")
def manifest():
    return load_manifest(ROOT / "config/tool_manifest.yaml")


def ai_page(layout):
    section = next(section for section in layout["sections"] if section["id"] == "transfer")
    return next(page for page in section["pages"] if page["id"] == "ai")


def test_ai_uses_two_persistent_modes_with_import_utilities(manifest):
    layout = window_layout.load(ROOT / "config")
    page = ai_page(window_layout.describe(layout, manifest))
    transfer = page["cards"][0]
    assert transfer["kind"] == "pick"
    assert transfer["view"] == "tabs"
    assert [operation["id"] for operation in transfer["operations"]] == ["ai_backup_export", "ai_backup_import"]
    assert {operation["id"] for operation in transfer["guests"]} == {"ai_backup_inventory", "ai_backup_open"}
    assert {card["id"]: card["when_picked"] for card in page["cards"][1:]} == {
        "ai_backup_rollback": "ai_backup_import", "ai_backup_merge": "ai_backup_import"}


@pytest.mark.parametrize("operation, mode", [("ai_backup_export", "export"), ("ai_backup_import", "import")])
def test_ai_filters_are_three_full_width_rows_and_lists_keep_their_groups(manifest, operation, mode):
    node = operation_model.find_node(manifest, operation)
    fields = {field["id"]: operation_model.describe_field(field, operation) for field in operation_model.form_fields(node)}
    prefix = f"ai_{mode}__"
    filters = [fields[prefix + name] for name in ("chat_provider", "chat_project", "chat_archive")]
    assert all(field["full_width"] and field["group"] == "ai_filters" for field in filters)
    assert fields[prefix + "chat_project"]["view"] == "dropdown"
    ordered = ["ai_summary", "chat_provider", "selected_chats", "data_categories", "ai_selection"]
    assert [fields[prefix + name]["group_order"] for name in ordered] == [1, 2, 3, 4, 5]
    assert fields[prefix + "ai_presets"]["group"] == fields[prefix + "data_categories"]["group"] == "ai_data"
    assert fields[prefix + "ai_summary"]["label"] == fields[prefix + "ai_summary"]["label_ru"] == ""
    assert fields[prefix + "selected_chats"]["preserve_selection"] is True
    assert fields[prefix + "ai_selection"]["view"] == "summary"


def test_tab_dependencies_are_validated(manifest):
    layout = window_layout.load(ROOT / "config")
    ai_page(layout)["cards"][1]["when_picked"] = "unknown"
    assert any("unknown tab" in problem for problem in window_layout.problems(layout, manifest))


def test_only_one_tabbed_pick_is_allowed_per_page(manifest):
    layout = window_layout.load(ROOT / "config")
    page = ai_page(layout)
    page["cards"].append(deepcopy(page["cards"][0]))
    assert any("more than one tabbed pick" in problem for problem in window_layout.problems(layout, manifest))


def test_tabbed_view_requires_a_pick(manifest):
    layout = window_layout.load(ROOT / "config")
    ai_page(layout)["cards"][1]["view"] = "tabs"
    assert any("is not a pick" in problem for problem in window_layout.problems(layout, manifest))
