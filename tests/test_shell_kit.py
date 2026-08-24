"""Windows Terminal settings and the PowerShell profile.

Neither is stored by any account and both are edited by hand over years, so they
are worth carrying. The subtlety is where they land: Documents can be redirected
(on this machine it is `C:\\Audion\\Documents`), and Windows Terminal exists as a
Store build, a Preview build and an unpackaged one, each with its own folder.

So the collected file is filed under a stable id, and the restore asks *this*
machine where that id belongs. A profile written to a path the machine does not
read is the quietest possible failure.
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
SCRIPTS = PROJECT_ROOT / "tools" / "shell_kit"


@pytest.fixture
def project(tmp_path: Path) -> Path:
    for name in ("config", "input", "output", "logs", "report"):
        (tmp_path / name).mkdir(parents=True, exist_ok=True)
    (tmp_path / "tools" / "shell_kit").mkdir(parents=True, exist_ok=True)
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
        id="shell_probe",
        title="Shell probe",
        description="",
        service="system_core.services.devops_tools:shell_kit",
        parameters=dict(parameters),
    )
    context = JobContext(
        paths=get_project_paths(project),
        operation=operation,
        log_file=project / "logs" / "probe.log",
        report_dir=project / "report",
    )
    return devops.shell_kit(context)


def test_status_only_lists(project: Path, runs) -> None:
    run(project, mode="status")
    assert runs[0]["script"] == "Get-ShellEnvironment.ps1"
    assert not (project / "output" / "shell").exists()


def test_collecting_goes_to_output(project: Path, runs) -> None:
    run(project, mode="export")
    assert runs[0]["script"] == "Export-ShellEnvironment.ps1"
    assert Path(runs[0]["parameters"]["TargetDir"]) == project / "output" / "shell"


def test_restoring_reads_input(project: Path, runs) -> None:
    run(project, mode="import")
    assert runs[0]["script"] == "Import-ShellEnvironment.ps1"
    assert Path(runs[0]["parameters"]["SourceDir"]) == project / "input"


def test_an_unknown_mode_is_refused(project: Path, runs) -> None:
    with pytest.raises(RuntimeError, match="Unknown Shell environment mode"):
        run(project, mode="rewrite_everything")


def test_paths_are_discovered_not_hard_coded() -> None:
    """A redirected Documents folder must not break the pack."""
    text = (SCRIPTS / "ShellPaths.ps1").read_text(encoding="utf-8")
    assert "$PROFILE.CurrentUserAllHosts" in text
    assert 'GetFolderPath("MyDocuments")' in text
    code = [line for line in text.splitlines() if not line.strip().startswith("#")]
    for line in code:
        assert "C:\\Users\\" not in line, f"a profile path is hard-coded: {line.strip()}"


def test_restore_files_by_id_not_by_the_old_path() -> None:
    """The old machine's paths are recorded, but never written to."""
    text = (SCRIPTS / "Import-ShellEnvironment.ps1").read_text(encoding="utf-8")
    code = [line for line in text.splitlines() if not line.strip().startswith("#")]
    destinations = [line for line in code if re.search(r"-Destination", line)]
    assert destinations, "the restore script copies nothing"
    for line in destinations:
        assert "entry.source" not in line, (
            f"the restore writes to the path from the other machine: {line.strip()}"
        )
    assert "$here[$entry.id]" in text, "the restore does not resolve the id on this machine"


def test_restore_keeps_a_copy_of_what_it_replaces() -> None:
    text = (SCRIPTS / "Import-ShellEnvironment.ps1").read_text(encoding="utf-8")
    assert ".bak.$stamp" in text


def shell_pack_node():
    manifest = load_manifest(PROJECT_ROOT / "config" / "tool_manifest.yaml")

    def walk(nodes):
        for node in nodes:
            yield node
            yield from walk(node.children)

    for node in walk(manifest.operation_groups):
        if node.id == "shell_kit":
            return node
    raise AssertionError("the manifest has no shell_kit pack")


def test_the_shell_folder_field_is_not_hijacked_by_the_workbench() -> None:
    field = next(item for item in shell_pack_node().fields if str(item.get("id")) == "shell_folder")
    assert field.get("workbench_route") is False
    assert str(field.get("default", "")).strip() == ""
