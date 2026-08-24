"""Where the two KeyKit packs put their files.

Export lands in `output\\<pack>`, import reads `input`, and the service picks
between them from the operation's mode. Two separate mechanisms can take that
choice away before the service ever sees it, and both are invisible in the YAML:

1. A field's manifest `default` is sent as a real parameter by the GUI and the
   CLI, so a folder named there arrives as an explicit user choice.
2. Every field of type `folder` is a workbench route field unless it sets
   `workbench_route: false`, and the GUI then replaces its value with the
   SOURCE/TARGET path from the top panel.

The second one is why an SSH key export landed in `input` on 14 August 2026:
the field was invisible in the form, so nothing on screen showed the substitution.
"""
from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import pytest

from system_core.cli_operation import field_defaults
from system_core.core.manifest import CommandNode, load_manifest
from system_core.services.devops_tools import keykit_default_dir, resolve_user_path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
MANIFEST = PROJECT_ROOT / "config" / "tool_manifest.yaml"

# pack id -> (folder field, subfolder under output)
PACKS = {
    "ssh_keykit": ("ssh_root", "ssh_keykit"),
    "cert_keykit": ("cert_backup_dir", "certificates"),
}


def walk(nodes: tuple[CommandNode, ...]):
    for node in nodes:
        yield node
        yield from walk(node.children)


def keykit_packs() -> dict[str, CommandNode]:
    manifest = load_manifest(MANIFEST)
    found = {
        node.id: node
        for node in walk(tuple(manifest.operation_groups))
        if node.id in PACKS
    }
    missing = set(PACKS) - set(found)
    assert not missing, f"KeyKit packs missing from the manifest: {sorted(missing)}"
    return found


def folder_field(pack: CommandNode, field_id: str) -> dict:
    for field in pack.fields:
        if str(field.get("id")) == field_id:
            return field
    raise AssertionError(f"{pack.id} has no field {field_id}")


@pytest.mark.parametrize("pack_id", sorted(PACKS))
def test_folder_field_opts_out_of_workbench_routing(pack_id: str) -> None:
    field_id, _ = PACKS[pack_id]
    field = folder_field(keykit_packs()[pack_id], field_id)
    assert field.get("workbench_route") is False, (
        f"{field_id} is a folder field, so without workbench_route: false the GUI "
        "replaces it with the SOURCE/TARGET path and both export and import land "
        "in the same folder."
    )


@pytest.mark.parametrize("pack_id", sorted(PACKS))
def test_folder_field_has_no_default(pack_id: str) -> None:
    field_id, _ = PACKS[pack_id]
    field = folder_field(keykit_packs()[pack_id], field_id)
    assert str(field.get("default", "")).strip() == "", (
        f"{field_id} must stay empty by default: a default is sent as a real "
        "parameter and overrides the folder the operation would choose."
    )


def context_at(root: Path) -> SimpleNamespace:
    return SimpleNamespace(
        paths=SimpleNamespace(root=root, input=root / "input", output=root / "output")
    )


@pytest.mark.parametrize(
    ("mode", "expected"),
    [
        ("export_client", "output/ssh_keykit"),
        ("export_all", "output/ssh_keykit"),
        ("check_links", "output/ssh_keykit"),
        ("import_client", "input"),
        ("import_all", "input"),
    ],
)
def test_mode_picks_the_folder(tmp_path: Path, mode: str, expected: str) -> None:
    chosen = keykit_default_dir(context_at(tmp_path), mode, "ssh_keykit")
    assert chosen == tmp_path.joinpath(*expected.split("/"))


@pytest.mark.parametrize("pack_id", sorted(PACKS))
def test_every_operation_lands_where_its_mode_says(tmp_path: Path, pack_id: str) -> None:
    """The whole chain: manifest defaults in, resolved folder out."""
    field_id, subfolder = PACKS[pack_id]
    context = context_at(tmp_path)

    for operation in keykit_packs()[pack_id].children:
        parameters = field_defaults(operation.fields)
        parameters.update(operation.parameters)
        mode = str(parameters.get("mode") or "")
        landed = resolve_user_path(
            context,
            parameters.get(field_id),
            default=keykit_default_dir(context, mode, subfolder),
        )
        expected = tmp_path / "input" if mode.startswith("import") else tmp_path / "output" / subfolder
        assert landed == expected, f"{operation.id} ({mode}) landed in {landed}"


def test_a_named_folder_still_wins(tmp_path: Path) -> None:
    """Filling the field in the form overrides the mode, for both directions."""
    context = context_at(tmp_path)
    elsewhere = tmp_path / "elsewhere"
    for mode in ("export_client", "import_client"):
        landed = resolve_user_path(
            context, str(elsewhere), default=keykit_default_dir(context, mode, "ssh_keykit")
        )
        assert landed == elsewhere
