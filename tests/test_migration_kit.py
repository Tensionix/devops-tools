"""Migration: the plan, the collecting, the unpacking.

Nothing here touches real keys. The packs are replaced by stand-ins that write a
marker file and record how they were called, so the tests are about the frame
itself: does it refuse a plan it cannot honour, does it put each piece in its own
folder, does the inventory describe the trip, and does the new machine get every
piece handed back to the pack that made it.

The one thing a migration must never do is finish quietly while a piece stayed
behind — most of these tests are about that.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from system_core.core.jobs import JobContext
from system_core.core.manifest import Operation
from system_core.core.paths import get_project_paths
from system_core.services import devops_tools as devops

PLAN_HEADER = "version: 1\nitems:\n"

SSH_LIKE = """\
  - id: ssh_access
    title: "SSH keys"
    title_ru: "Ключи SSH"
    pack: test_pack
    folder: ssh_access
    secret: true
    export:
      mode: export_client
    import:
      mode: import_client
"""

MANUAL_ITEM = """\
  - id: certificates
    title: "Certificates"
    title_ru: "Сертификаты"
    pack: manual_pack
    folder: certificates
    secret: true
    export:
      mode: export_pfx
    import: manual
    manual_reason: "Every .pfx asks for its own password."
"""


@pytest.fixture
def project(tmp_path: Path) -> Path:
    for name in ("config", "input", "output", "logs", "report"):
        (tmp_path / name).mkdir(parents=True, exist_ok=True)
    (tmp_path / "system_core").mkdir(parents=True, exist_ok=True)
    return tmp_path


def write_plan(project: Path, body: str) -> Path:
    plan = project / "config" / "migration_plan.yaml"
    plan.write_text(PLAN_HEADER + body, encoding="utf-8")
    return plan


def make_context(project: Path, **parameters: Any) -> JobContext:
    operation = Operation(
        id="migration_probe",
        title="Migration probe",
        description="",
        service="system_core.services.devops_tools:migration_kit",
        parameters=dict(parameters),
    )
    return JobContext(
        paths=get_project_paths(project),
        operation=operation,
        log_file=project / "logs" / "probe.log",
        report_dir=project / "report",
    )


@pytest.fixture
def packs(monkeypatch: pytest.MonkeyPatch) -> dict[str, list[dict[str, Any]]]:
    """Stand-in packs: they record the call and leave one file behind."""
    calls: dict[str, list[dict[str, Any]]] = {"export": [], "import": [], "links": []}

    def exporter(context: JobContext) -> dict[str, object]:
        parameters = dict(context.operation.parameters)
        calls["export"].append(parameters)
        folder = Path(str(parameters["probe_folder"]))
        folder.mkdir(parents=True, exist_ok=True)
        (folder / "carried.txt").write_text("carried", encoding="utf-8")
        return {"folder": str(folder)}

    def importer(context: JobContext) -> dict[str, object]:
        calls["import"].append(dict(context.operation.parameters))
        return {}

    def failing(context: JobContext) -> dict[str, object]:
        calls["export"].append(dict(context.operation.parameters))
        raise RuntimeError("this pack refuses to travel")

    def links(context: JobContext) -> dict[str, object]:
        calls["links"].append(dict(context.operation.parameters))
        return {}

    monkeypatch.setitem(
        devops.MIGRATION_PACKS,
        "test_pack",
        devops.MigrationPack(
            export_service=exporter,
            export_folder_param="probe_folder",
            import_service=importer,
            import_folder_param="probe_folder",
            import_defaults={"source_kind": "folder"},
        ),
    )
    monkeypatch.setitem(
        devops.MIGRATION_PACKS,
        "manual_pack",
        devops.MigrationPack(
            export_service=exporter,
            export_folder_param="probe_folder",
            import_service=None,
            passthrough=("pfx_password",),
        ),
    )
    monkeypatch.setitem(
        devops.MIGRATION_PACKS,
        "broken_pack",
        devops.MigrationPack(export_service=failing, export_folder_param="probe_folder"),
    )
    # The access check at the end of an import is the real SSH pack; here it only
    # has to be observed, not run.
    monkeypatch.setattr(devops, "ssh_keykit", links)
    return calls


# --- the plan refuses what it cannot honour -----------------------------------


def test_plan_lists_every_item(project: Path, packs) -> None:
    write_plan(project, SSH_LIKE + MANUAL_ITEM)
    items = devops.load_migration_plan(make_context(project))
    assert [item.item_id for item in items] == ["ssh_access", "certificates"]
    assert items[0].manual is False
    assert items[1].manual is True


def test_an_unknown_pack_is_refused(project: Path, packs) -> None:
    write_plan(
        project,
        """\
  - id: mystery
    pack: no_such_pack
    export:
      mode: export
    import:
      mode: import
""",
    )
    with pytest.raises(RuntimeError, match="unknown pack"):
        devops.load_migration_plan(make_context(project))


def test_a_folder_that_is_a_path_is_refused(project: Path, packs) -> None:
    write_plan(
        project,
        """\
  - id: ssh_access
    pack: test_pack
    folder: "..\\\\elsewhere"
    export:
      mode: export_client
    import:
      mode: import_client
""",
    )
    with pytest.raises(RuntimeError, match="names a path"):
        devops.load_migration_plan(make_context(project))


def test_a_repeated_id_is_refused(project: Path, packs) -> None:
    write_plan(project, SSH_LIKE + SSH_LIKE)
    with pytest.raises(RuntimeError, match="repeats item id"):
        devops.load_migration_plan(make_context(project))


def test_promising_an_import_a_pack_cannot_do_is_refused(project: Path, packs) -> None:
    write_plan(
        project,
        """\
  - id: certificates
    pack: manual_pack
    export:
      mode: export_pfx
    import:
      mode: import_pfx
""",
    )
    with pytest.raises(RuntimeError, match="no unattended import"):
        devops.load_migration_plan(make_context(project))


def test_an_item_that_cannot_be_collected_is_refused(project: Path, packs) -> None:
    write_plan(
        project,
        """\
  - id: ssh_access
    pack: test_pack
    export: manual
    import:
      mode: import_client
""",
    )
    with pytest.raises(RuntimeError, match="cannot be manual on export"):
        devops.load_migration_plan(make_context(project))


# --- collecting ---------------------------------------------------------------


def test_export_puts_each_item_in_its_own_folder(project: Path, packs) -> None:
    write_plan(project, SSH_LIKE + MANUAL_ITEM)
    result = devops.migration_kit(make_context(project, mode="export", profile_name="TESTBOX"))

    folder = Path(str(result["folder"]))
    assert folder.parent == project / "output" / "migration"
    assert folder.name.startswith("TESTBOX_")
    assert (folder / "ssh_access" / "carried.txt").is_file()
    assert (folder / "certificates" / "carried.txt").is_file()
    assert [call["mode"] for call in packs["export"]] == ["export_client", "export_pfx"]


def test_export_writes_an_inventory(project: Path, packs) -> None:
    write_plan(project, SSH_LIKE + MANUAL_ITEM)
    result = devops.migration_kit(make_context(project, mode="export", profile_name="TESTBOX"))

    inventory = json.loads(
        (Path(str(result["folder"])) / "migration.json").read_text(encoding="utf-8")
    )
    assert inventory["machine"] == "TESTBOX"
    assert inventory["format"] == devops.MIGRATION_FORMAT
    entries = {entry["id"]: entry for entry in inventory["items"]}
    assert entries["ssh_access"]["import"] == "import_client"
    assert entries["ssh_access"]["files"] == 1
    assert entries["certificates"]["import"] == "manual"
    assert entries["certificates"]["manual_reason"]


def test_the_form_password_reaches_only_the_pack_that_asked(project: Path, packs) -> None:
    write_plan(project, SSH_LIKE + MANUAL_ITEM)
    devops.migration_kit(make_context(project, mode="export", pfx_password="secret"))

    by_mode = {call["mode"]: call for call in packs["export"]}
    assert by_mode["export_pfx"]["pfx_password"] == "secret"
    assert "pfx_password" not in by_mode["export_client"]


def test_a_pack_that_fails_is_named_and_the_rest_still_travel(project: Path, packs) -> None:
    write_plan(
        project,
        SSH_LIKE
        + """\
  - id: broken
    pack: broken_pack
    export:
      mode: export
    import: manual
""",
    )
    context = make_context(project, mode="export")
    with pytest.raises(RuntimeError, match="collected with gaps"):
        devops.migration_kit(context)

    migrations = sorted((project / "output" / "migration").iterdir())
    inventory = json.loads((migrations[-1] / "migration.json").read_text(encoding="utf-8"))
    entries = {entry["id"]: entry for entry in inventory["items"]}
    assert entries["ssh_access"]["collected"] is True
    assert entries["broken"]["collected"] is False
    assert "refuses to travel" in entries["broken"]["error"]


# --- unpacking ----------------------------------------------------------------


def collect_into_input(project: Path, body: str, *, nested: bool = True) -> Path:
    """Collect a migration, then move it where an import would look for it."""
    write_plan(project, body)
    result = devops.migration_kit(make_context(project, mode="export", profile_name="OLDBOX"))
    folder = Path(str(result["folder"]))
    destination = project / "input" / (folder.name if nested else "")
    if nested:
        folder.rename(destination)
        return destination
    for child in folder.iterdir():
        child.rename(project / "input" / child.name)
    return project / "input"


def test_import_hands_each_item_back_to_its_pack(project: Path, packs) -> None:
    collect_into_input(project, SSH_LIKE)
    packs["export"].clear()

    result = devops.migration_kit(make_context(project, mode="import"))

    assert result["restored"] == ["ssh_access"]
    assert len(packs["import"]) == 1
    call = packs["import"][0]
    assert call["mode"] == "import_client"
    assert call["source_kind"] == "folder"  # the pack's own default came along
    assert Path(str(call["probe_folder"])).name == "ssh_access"


def test_import_finds_a_migration_lying_directly_in_input(project: Path, packs) -> None:
    collect_into_input(project, SSH_LIKE, nested=False)
    result = devops.migration_kit(make_context(project, mode="import"))
    assert result["restored"] == ["ssh_access"]


def test_manual_items_are_named_not_skipped_silently(project: Path, packs) -> None:
    collect_into_input(project, SSH_LIKE + MANUAL_ITEM)
    result = devops.migration_kit(make_context(project, mode="import"))

    assert result["restored"] == ["ssh_access"]
    assert result["manual"] == ["certificates"]
    log = (project / "logs" / "probe.log").read_text(encoding="utf-8")
    assert "Every .pfx asks for its own password." in log


def test_import_ends_with_the_access_check(project: Path, packs) -> None:
    collect_into_input(project, SSH_LIKE)
    devops.migration_kit(make_context(project, mode="import"))

    assert packs["links"], "an import that never checks access cannot say it landed"
    assert packs["links"][0]["mode"] == "check_links"
    # Broken links must be reported, not turned into a failed import: the files
    # did arrive, and the operator needs the list, not an exception.
    assert packs["links"][0]["fail_on_broken"] is False


def test_import_refuses_an_inventory_from_a_newer_format(project: Path, packs) -> None:
    folder = collect_into_input(project, SSH_LIKE)
    inventory_file = folder / "migration.json"
    inventory = json.loads(inventory_file.read_text(encoding="utf-8"))
    inventory["format"] = devops.MIGRATION_FORMAT + 1
    inventory_file.write_text(json.dumps(inventory), encoding="utf-8")

    with pytest.raises(RuntimeError, match="not supported"):
        devops.migration_kit(make_context(project, mode="import"))


def test_import_without_a_migration_says_where_it_looked(project: Path, packs) -> None:
    write_plan(project, SSH_LIKE)
    with pytest.raises(RuntimeError, match="No migration found"):
        devops.migration_kit(make_context(project, mode="import"))


# --- the real manifest --------------------------------------------------------

PROJECT_ROOT = Path(__file__).resolve().parents[1]


def migration_pack_node():
    from system_core.core.manifest import load_manifest

    manifest = load_manifest(PROJECT_ROOT / "config" / "tool_manifest.yaml")

    def walk(nodes):
        for node in nodes:
            yield node
            yield from walk(node.children)

    for node in walk(manifest.operation_groups):
        if node.id == "migration_kit":
            return node
    raise AssertionError("the manifest has no migration_kit pack")


def test_the_shipped_plan_loads(project: Path) -> None:
    """The plan that ships with the program must name packs that exist."""
    shipped = (PROJECT_ROOT / "config" / "migration_plan.yaml").read_text(encoding="utf-8")
    (project / "config" / "migration_plan.yaml").write_text(shipped, encoding="utf-8")
    items = devops.load_migration_plan(make_context(project))
    assert items, "the shipped migration plan is empty"


def test_the_migration_folder_field_is_not_hijacked_by_the_workbench() -> None:
    field = next(
        item for item in migration_pack_node().fields if str(item.get("id")) == "migration_folder"
    )
    assert field.get("workbench_route") is False, (
        "a folder field without workbench_route: false is replaced by the "
        "SOURCE/TARGET path, and collecting and unpacking end up in one folder"
    )
    assert str(field.get("default", "")).strip() == "", (
        "a default is sent as a real parameter and overrides the folder the "
        "operation would choose"
    )


def test_every_migration_operation_is_wired_to_the_service() -> None:
    children = {node.id: node for node in migration_pack_node().children}
    assert set(children) == {
        "migration_plan",
        "migration_verify",
        "migration_export",
        "migration_import",
        "migration_open_folder",
    }
    for node in children.values():
        assert node.service.endswith(":migration_kit")
    assert children["migration_export"].risk_level == "secret_export"
    assert children["migration_import"].risk_level == "system_change"
    assert children["migration_plan"].kind == "safe"
