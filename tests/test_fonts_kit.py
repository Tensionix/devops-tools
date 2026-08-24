"""User fonts travel; system fonts are not touched.

Windows keeps two sets. The system one comes back with Windows. The per-user one
does not come back at all, and it is the one nobody remembers until a document
opens with the wrong typeface.

The pack is a thin shell over three PowerShell scripts, so what is worth pinning
here is the wiring: which script runs, which folder it is handed, and that the
manifest field is not the kind that the workbench quietly replaces.
"""
from __future__ import annotations

import re
from pathlib import Path
from typing import Any

import pytest

from system_core.core.jobs import JobContext
from system_core.core.manifest import Operation, load_manifest
from system_core.core.paths import get_project_paths
from system_core.services import devops_tools as devops

PROJECT_ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture
def project(tmp_path: Path) -> Path:
    for name in ("config", "input", "output", "logs", "report"):
        (tmp_path / name).mkdir(parents=True, exist_ok=True)
    (tmp_path / "tools" / "fonts_kit").mkdir(parents=True, exist_ok=True)
    (tmp_path / "system_core").mkdir(parents=True, exist_ok=True)
    return tmp_path


@pytest.fixture
def runs(monkeypatch: pytest.MonkeyPatch) -> list[dict[str, Any]]:
    recorded: list[dict[str, Any]] = []

    def fake_run_ps1(context, script, parameters=None, **kwargs):
        recorded.append({"script": Path(str(script)).name, "parameters": dict(parameters or {})})
        return None

    monkeypatch.setattr(devops, "run_ps1", fake_run_ps1)
    return recorded


def run(project: Path, **parameters: Any) -> dict[str, object]:
    operation = Operation(
        id="fonts_probe",
        title="Fonts probe",
        description="",
        service="system_core.services.devops_tools:fonts_kit",
        parameters=dict(parameters),
    )
    context = JobContext(
        paths=get_project_paths(project),
        operation=operation,
        log_file=project / "logs" / "probe.log",
        report_dir=project / "report",
    )
    return devops.fonts_kit(context)


def test_status_only_lists(project: Path, runs) -> None:
    run(project, mode="status")
    assert runs[0]["script"] == "Get-UserFonts.ps1"
    assert runs[0]["parameters"] == {"IncludeSystem": False}
    # Listing must not create the collecting folder: a read-only action that
    # leaves folders behind stops reading as read-only.
    assert not (project / "output" / "fonts").exists()


def test_collecting_goes_to_output(project: Path, runs) -> None:
    result = run(project, mode="export")
    assert runs[0]["script"] == "Export-UserFonts.ps1"
    assert Path(runs[0]["parameters"]["TargetDir"]) == project / "output" / "fonts"
    assert result["folder"] == str(project / "output" / "fonts")


def test_installing_reads_input(project: Path, runs) -> None:
    run(project, mode="import")
    assert runs[0]["script"] == "Import-UserFonts.ps1"
    assert Path(runs[0]["parameters"]["SourceDir"]) == project / "input"


def test_a_named_folder_wins(project: Path, runs) -> None:
    elsewhere = project / "elsewhere"
    run(project, mode="import", fonts_folder=str(elsewhere))
    assert Path(runs[0]["parameters"]["SourceDir"]) == elsewhere


def test_an_unknown_mode_is_refused(project: Path, runs) -> None:
    with pytest.raises(RuntimeError, match="Unknown Fonts mode"):
        run(project, mode="uninstall_everything")


def fonts_pack_node():
    manifest = load_manifest(PROJECT_ROOT / "config" / "tool_manifest.yaml")

    def walk(nodes):
        for node in nodes:
            yield node
            yield from walk(node.children)

    for node in walk(manifest.operation_groups):
        if node.id == "fonts_kit":
            return node
    raise AssertionError("the manifest has no fonts_kit pack")


def test_the_fonts_folder_field_is_not_hijacked_by_the_workbench() -> None:
    field = next(
        item for item in fonts_pack_node().fields if str(item.get("id")) == "fonts_folder"
    )
    assert field.get("workbench_route") is False
    assert str(field.get("default", "")).strip() == ""


WRITING_COMMANDS = re.compile(
    r"\b(New-Item|New-ItemProperty|Set-ItemProperty|Remove-Item|Remove-ItemProperty"
    r"|Copy-Item|Move-Item|Set-Content|Add-Content|Out-File)\b",
    re.IGNORECASE,
)


def test_the_scripts_never_write_to_the_system_font_set() -> None:
    """The one promise of this pack, checked against the scripts themselves.

    Only lines that actually write are examined — the system set is mentioned in
    comments and counted in the listing, and neither of those is a write.
    """
    scripts = PROJECT_ROOT / "tools" / "fonts_kit"
    for name in ("Get-UserFonts.ps1", "Export-UserFonts.ps1", "Import-UserFonts.ps1"):
        text = (scripts / name).read_text(encoding="utf-8")
        code = [line for line in text.splitlines() if not line.strip().startswith("#")]
        for line in code:
            if not WRITING_COMMANDS.search(line):
                continue
            upper = line.upper()
            assert "HKLM" not in upper, f"{name} writes to the machine registry: {line.strip()}"
            assert "WINDIR" not in upper, f"{name} writes into the Windows folder: {line.strip()}"
            assert "C:\\WINDOWS" not in upper, f"{name} writes into C:\\Windows: {line.strip()}"
