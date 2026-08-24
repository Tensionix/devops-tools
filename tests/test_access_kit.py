"""Access collected by reference, not by location.

Exporting `.ssh` carries what lives in `.ssh`. It does not carry a key that a
config line points at on another disk — and that is the normal case here: most
of the private keys named by ssh and rclone on this machine live outside the
profile. A migration built only from `.ssh` arrives looking complete and fails
on the first connection.

These tests use a lab setup with fake keys: nothing real is copied anywhere.
"""
from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any

import pytest

from system_core.core.jobs import JobContext
from system_core.core.manifest import Operation
from system_core.core.paths import get_project_paths
from system_core.services import devops_tools as devops


@pytest.fixture
def project(tmp_path: Path) -> Path:
    for name in ("config", "input", "output", "logs", "report", "tools"):
        (tmp_path / name).mkdir(parents=True, exist_ok=True)
    (tmp_path / "tools" / "ssh_keykit").mkdir(parents=True, exist_ok=True)
    (tmp_path / "system_core").mkdir(parents=True, exist_ok=True)
    return tmp_path


def make_context(project: Path, **parameters: Any) -> JobContext:
    operation = Operation(
        id="access_probe",
        title="Access probe",
        description="",
        service="system_core.services.devops_tools:access_kit",
        parameters=dict(parameters),
    )
    return JobContext(
        paths=get_project_paths(project),
        operation=operation,
        log_file=project / "logs" / "probe.log",
        report_dir=project / "report",
    )


@pytest.fixture
def lab(project: Path, monkeypatch: pytest.MonkeyPatch) -> dict[str, Any]:
    """A pretend machine: two configs, a key outside the profile, a dead path."""
    keys = project / "elsewhere" / "keys"
    keys.mkdir(parents=True, exist_ok=True)
    private = keys / "lab_key"
    private.write_text("NOT-A-REAL-KEY", encoding="utf-8")
    (keys / "lab_key.pub").write_text("ssh-ed25519 NOTREAL lab", encoding="utf-8")
    known_hosts = project / "elsewhere" / "known_hosts"
    known_hosts.write_text("example.test ssh-ed25519 NOTREAL", encoding="utf-8")
    gone = keys / "vanished_key"
    proxy = project / "elsewhere" / "proxy.exe"
    proxy.write_text("binary", encoding="utf-8")

    ssh_config = project / "lab_ssh_config"
    ssh_config.write_text(
        "Host lab\n"
        f"  IdentityFile {private}\n"
        f"  UserKnownHostsFile {known_hosts}\n"
        f"  ProxyCommand {proxy} access ssh\n"
        "Host dead\n"
        f"  IdentityFile {gone}\n",
        encoding="utf-8",
    )
    rclone_config = project / "lab_rclone.conf"
    rclone_config.write_text(
        "[labremote]\ntype = sftp\n" f"key_file = {private}\n" f"known_hosts_file = {known_hosts}\n",
        encoding="utf-8",
    )

    rows = [
        {"Source": "ssh", "Scope": "lab", "Setting": "IdentityFile", "Path": str(private), "Raw": str(private), "Exists": "True"},
        {"Source": "ssh", "Scope": "lab", "Setting": "UserKnownHostsFile", "Path": str(known_hosts), "Raw": str(known_hosts), "Exists": "True"},
        {"Source": "ssh", "Scope": "lab", "Setting": "ProxyCommand", "Path": str(proxy), "Raw": str(proxy), "Exists": "True"},
        {"Source": "ssh", "Scope": "dead", "Setting": "IdentityFile", "Path": str(gone), "Raw": str(gone), "Exists": "False"},
        {"Source": "rclone", "Scope": "labremote", "Setting": "key_file", "Path": str(private), "Raw": str(private), "Exists": "True"},
        {"Source": "rclone", "Scope": "labremote", "Setting": "known_hosts_file", "Path": str(known_hosts), "Raw": str(known_hosts), "Exists": "True"},
    ]

    def fake_run_ps1(context, script, parameters=None, **kwargs):
        report = Path(str((parameters or {})["ReportPath"]))
        report.parent.mkdir(parents=True, exist_ok=True)
        with report.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
            writer.writeheader()
            writer.writerows(rows)
        return None

    calls: dict[str, list[Any]] = {"acl": [], "links": []}

    def fake_run_ps_command(context, script, **kwargs):
        calls["acl"].append(script)
        return None

    def fake_ssh_keykit(context):
        calls["links"].append(dict(context.operation.parameters))
        return {}

    monkeypatch.setattr(devops, "run_ps1", fake_run_ps1)
    monkeypatch.setattr(devops, "run_ps_command", fake_run_ps_command)
    monkeypatch.setattr(devops, "ssh_keykit", fake_ssh_keykit)

    return {
        "ssh_config": ssh_config,
        "rclone_config": rclone_config,
        "private": private,
        "known_hosts": known_hosts,
        "proxy": proxy,
        "gone": gone,
        "calls": calls,
    }


def export(project: Path, lab: dict[str, Any], folder: Path) -> dict[str, Any]:
    return devops.access_kit(
        make_context(
            project,
            mode="export",
            ssh_config_path=str(lab["ssh_config"]),
            rclone_config_path=str(lab["rclone_config"]),
            access_folder=str(folder),
        )
    )


# --- rewriting configuration --------------------------------------------------


def test_ssh_style_lines_keep_their_shape() -> None:
    text = "Host lab\n  IdentityFile C:\\old\\key\n  Port 22\n"
    result, count = devops.rewrite_config_paths(
        text, {"C:\\old\\key": "D:\\new\\key"}, devops.SSH_PATH_KEYS
    )
    assert count == 1
    assert "  IdentityFile D:\\new\\key\n" in result
    assert "  Port 22\n" in result


def test_rclone_style_lines_keep_the_equals_sign() -> None:
    text = "[remote]\nkey_file = C:\\old\\key\ntype = sftp\n"
    result, count = devops.rewrite_config_paths(
        text, {"C:\\old\\key": "D:\\new\\key"}, devops.RCLONE_PATH_KEYS
    )
    assert count == 1
    assert "key_file = D:\\new\\key\n" in result
    assert "type = sftp\n" in result


def test_a_path_that_did_not_travel_is_left_alone() -> None:
    """A config is a working file, not a template: only carried paths change."""
    text = "Host lab\n  IdentityFile C:\\somewhere\\else\n"
    result, count = devops.rewrite_config_paths(
        text, {"C:\\old\\key": "D:\\new\\key"}, devops.SSH_PATH_KEYS
    )
    assert count == 0
    assert result == text


def test_comments_are_not_rewritten() -> None:
    text = "# IdentityFile C:\\old\\key\nHost lab\n"
    result, count = devops.rewrite_config_paths(
        text, {"C:\\old\\key": "D:\\new\\key"}, devops.SSH_PATH_KEYS
    )
    assert count == 0
    assert result == text


# --- collecting ---------------------------------------------------------------


def test_export_carries_a_key_that_lives_outside_the_profile(project: Path, lab) -> None:
    folder = project / "output" / "access"
    result = export(project, lab, folder)

    access_map = json.loads((folder / "access_map.json").read_text(encoding="utf-8"))
    carried = {Path(entry["source"]).name for entry in access_map["files"]}
    assert "lab_key" in carried
    assert "known_hosts" in carried
    assert result["files"] == 3  # key, its .pub, known_hosts
    assert result["references"] == 5


def test_the_public_half_travels_with_the_key(project: Path, lab) -> None:
    folder = project / "output" / "access"
    export(project, lab, folder)

    access_map = json.loads((folder / "access_map.json").read_text(encoding="utf-8"))
    companions = [entry for entry in access_map["files"] if entry["setting"] == "companion"]
    assert [Path(entry["source"]).name for entry in companions] == ["lab_key.pub"]


def test_an_executable_is_named_not_carried(project: Path, lab) -> None:
    folder = project / "output" / "access"
    result = export(project, lab, folder)

    access_map = json.loads((folder / "access_map.json").read_text(encoding="utf-8"))
    assert result["by_hand"] == 1
    assert Path(access_map["install_by_hand"][0]["raw"]).name == "proxy.exe"
    stored = {path.name for path in (folder / "files").iterdir()}
    assert not any("proxy" in name for name in stored)


def test_a_path_that_leads_nowhere_is_reported(project: Path, lab) -> None:
    folder = project / "output" / "access"
    result = export(project, lab, folder)

    access_map = json.loads((folder / "access_map.json").read_text(encoding="utf-8"))
    assert result["missing"] == 1
    assert Path(access_map["missing"][0]["raw"]).name == "vanished_key"
    log = (project / "logs" / "probe.log").read_text(encoding="utf-8")
    assert "vanished_key" in log


# --- laying out ---------------------------------------------------------------


def lay_out(project: Path, lab, folder: Path, **extra: Any) -> dict[str, Any]:
    return devops.access_kit(
        make_context(
            project,
            mode="import",
            access_folder=str(folder),
            access_key_root=str(project / "landed"),
            ssh_config_path=str(project / "new_ssh_config"),
            rclone_config_path=str(project / "new_rclone.conf"),
            **extra,
        )
    )


def test_import_points_both_configs_at_the_new_place(project: Path, lab) -> None:
    folder = project / "output" / "access"
    export(project, lab, folder)
    result = lay_out(project, lab, folder)

    landed = project / "landed"
    assert (landed / "lab_key").is_file()
    assert (landed / "lab_key.pub").is_file()
    assert (landed / "known_hosts").is_file()
    assert result["rewritten"] == 4

    ssh_text = (project / "new_ssh_config").read_text(encoding="utf-8")
    rclone_text = (project / "new_rclone.conf").read_text(encoding="utf-8")
    assert f"IdentityFile {landed / 'lab_key'}" in ssh_text
    assert f"key_file = {landed / 'lab_key'}" in rclone_text
    # The host that pointed at a file which was already gone keeps its line: the
    # migration did not carry that key, so it has nothing better to offer.
    assert str(lab["gone"]) in ssh_text


def test_import_keeps_a_copy_of_the_configuration_it_replaces(project: Path, lab) -> None:
    folder = project / "output" / "access"
    export(project, lab, folder)
    existing = project / "new_ssh_config"
    existing.write_text("Host previous\n", encoding="utf-8")

    lay_out(project, lab, folder)

    spares = list(project.glob("new_ssh_config.bak.*"))
    assert len(spares) == 1
    assert spares[0].read_text(encoding="utf-8") == "Host previous\n"


def test_import_can_be_run_twice(project: Path, lab) -> None:
    """Laying the same access out again is what a retried migration is."""
    folder = project / "output" / "access"
    export(project, lab, folder)
    lay_out(project, lab, folder)
    result = lay_out(project, lab, folder)
    assert result["files"] == 3


def test_import_ends_by_checking_the_files_it_just_wrote(project: Path, lab) -> None:
    folder = project / "output" / "access"
    export(project, lab, folder)
    lay_out(project, lab, folder)

    checks = lab["calls"]["links"]
    assert checks, "an import that never checks access cannot say it landed"
    assert checks[-1]["mode"] == "check_links"
    assert checks[-1]["ssh_config_path"] == str(project / "new_ssh_config")
    assert checks[-1]["rclone_config_path"] == str(project / "new_rclone.conf")


def test_import_restricts_the_private_key_only(project: Path, lab) -> None:
    folder = project / "output" / "access"
    export(project, lab, folder)
    lay_out(project, lab, folder)

    script = "\n".join(lab["calls"]["acl"])
    assert "lab_key'" in script
    assert "lab_key.pub" not in script
