from __future__ import annotations

import hashlib
import json
import os
import sqlite3
import subprocess
import sys
from contextlib import closing
from pathlib import Path
from typing import Any

import pytest

from system_core.core.jobs import JobContext
from system_core.core.manifest import Operation, load_manifest
from system_core.core.paths import get_project_paths
from system_core.services import devops_tools as devops


PROJECT_ROOT = Path(__file__).resolve().parents[1]
TOOL_ROOT = PROJECT_ROOT / "tools" / "ai_backup"
SCRIPT = TOOL_ROOT / "AI-Backup.ps1"
PWSH = PROJECT_ROOT / "system_core" / "powershell" / "pwsh.exe"
PYTHON = PROJECT_ROOT / "runtime" / "python.exe"


def make_profile(root: Path) -> dict[str, Path]:
    user = root / "user"
    claude = root / "claude-home"
    codex = root / "codex-home"
    sqlite_home = root / "codex-sqlite"
    for directory in (user, claude, codex, sqlite_home):
        directory.mkdir(parents=True, exist_ok=True)

    (claude / "projects" / "sample" / "memory").mkdir(parents=True)
    (claude / "projects" / "sample" / "memory" / "fact.md").write_text("portable fact\n", encoding="utf-8")
    (claude / "projects" / "sample" / "memory" / "second.md").write_text("second fact\n", encoding="utf-8")
    (claude / "projects" / "sample" / "memory" / "MEMORY.md").write_text(
        "- [fact](fact.md)\n- [second](second.md)\n", encoding="utf-8"
    )
    (claude / "settings.json").write_text('{"theme":"dark"}\n', encoding="utf-8")
    (claude / ".credentials.json").write_text('{"secret":"claude"}\n', encoding="utf-8")
    (claude / "sessions").mkdir()
    (claude / "sessions" / "old.jsonl").write_text("session\n", encoding="utf-8")
    (user / ".claude.json").write_text('{"projects":{}}\n', encoding="utf-8")

    (codex / "memories").mkdir()
    (codex / "memories" / "memory_summary.md").write_text("summary\n", encoding="utf-8")
    (codex / "config.toml").write_text('model = "test"\n', encoding="utf-8")
    (codex / "auth.json").write_text('{"secret":"codex"}\n', encoding="utf-8")
    (codex / "installation_id").write_text("machine-specific\n", encoding="utf-8")
    (codex / "sessions").mkdir()
    (codex / "sessions" / "old.jsonl").write_text("session\n", encoding="utf-8")

    database = sqlite_home / "memories_1.sqlite"
    with closing(sqlite3.connect(database)) as connection:
        connection.execute("PRAGMA journal_mode=WAL")
        connection.execute("CREATE TABLE memory (value TEXT)")
        connection.execute("INSERT INTO memory VALUES ('from-wal')")
        connection.commit()
    with closing(sqlite3.connect(sqlite_home / "goals_1.sqlite")) as connection:
        connection.execute("CREATE TABLE goal (value TEXT)")
        connection.execute("INSERT INTO goal VALUES ('goal')")
        connection.commit()

    return {"user": user, "claude": claude, "codex": codex, "sqlite": sqlite_home}


def tool_env(profile: dict[str, Path]) -> dict[str, str]:
    env = os.environ.copy()
    env.update(
        {
            "USERPROFILE": str(profile["user"]),
            "CLAUDE_CONFIG_DIR": str(profile["claude"]),
            "CODEX_HOME": str(profile["codex"]),
            "CODEX_SQLITE_HOME": str(profile["sqlite"]),
            "AUDION_GUI_PYTHON": str(PYTHON),
            "AUDION_NO_PAUSE": "1",
        }
    )
    return env


def run_tool(profile: dict[str, Path], mode: str, bundle: Path, *flags: str) -> subprocess.CompletedProcess[str]:
    if not PWSH.is_file() or not PYTHON.is_file():
        pytest.skip("project-local PowerShell/Python runtime is unavailable")
    command = [
        str(PWSH),
        "-NoProfile",
        "-ExecutionPolicy",
        "Bypass",
        "-File",
        str(SCRIPT),
        "-Mode",
        mode,
        "-Path",
        str(bundle),
        *flags,
    ]
    return subprocess.run(command, env=tool_env(profile), text=True, capture_output=True, encoding="utf-8")


def manifest_files(bundle: Path) -> dict[str, dict[str, Any]]:
    payload = json.loads((bundle / "manifest.json").read_text(encoding="utf-8"))
    return {entry["path"]: entry for entry in payload["files"]}


def test_essential_export_is_fresh_verified_and_excludes_auth(tmp_path: Path) -> None:
    profile = make_profile(tmp_path / "source")
    bundle = tmp_path / "bundle"

    live = sqlite3.connect(profile["sqlite"] / "memories_1.sqlite")
    live.execute("PRAGMA wal_autocheckpoint=0")
    live.execute("INSERT INTO memory VALUES ('committed-while-open')")
    live.commit()
    try:
        first = run_tool(profile, "Export", bundle)
    finally:
        live.close()
    assert first.returncode == 0, first.stdout + first.stderr
    files = manifest_files(bundle)
    assert "claude/projects/sample/memory/fact.md" in files
    assert "codex/memories/memory_summary.md" in files
    assert "codex_sqlite/memories_1.sqlite" in files
    assert "claude/.credentials.json" not in files
    assert "codex/auth.json" not in files
    assert "claude/sessions/old.jsonl" not in files
    assert "codex/sessions/old.jsonl" not in files
    assert "codex/installation_id" not in files

    for relative, entry in files.items():
        digest = hashlib.sha256((bundle / Path(relative)).read_bytes()).hexdigest()
        assert digest == entry["sha256"]
    with closing(sqlite3.connect(bundle / "codex_sqlite" / "memories_1.sqlite")) as connection:
        assert connection.execute("SELECT value FROM memory ORDER BY rowid").fetchall() == [
            ("from-wal",),
            ("committed-while-open",),
        ]

    stale = bundle / "claude" / "stale.txt"
    stale.write_text("must disappear", encoding="utf-8")
    second = run_tool(profile, "Export", bundle)
    assert second.returncode == 0, second.stdout + second.stderr
    assert not stale.exists()


def test_full_bundle_respects_restore_scope_and_auth_opt_in(tmp_path: Path) -> None:
    source = make_profile(tmp_path / "source")
    bundle = tmp_path / "bundle"
    exported = run_tool(source, "Export", bundle, "-Full", "-IncludeAuth")
    assert exported.returncode == 0, exported.stdout + exported.stderr
    files = manifest_files(bundle)
    assert "claude/sessions/old.jsonl" in files
    assert "codex/sessions/old.jsonl" in files
    assert files["codex/auth.json"]["category"] == "auth"

    target = make_profile(tmp_path / "target")
    (target["claude"] / "settings.json").write_text('{"theme":"target"}\n', encoding="utf-8")
    with closing(sqlite3.connect(target["sqlite"] / "memories_1.sqlite")) as connection:
        connection.execute("UPDATE memory SET value = 'target'")
        connection.commit()
    for path in (
        target["claude"] / "sessions" / "old.jsonl",
        target["codex"] / "sessions" / "old.jsonl",
        target["claude"] / ".credentials.json",
        target["codex"] / "auth.json",
    ):
        path.unlink()

    essential = run_tool(target, "Import", bundle, "-Yes", "-AllowRunningApps")
    assert essential.returncode == 0, essential.stdout + essential.stderr
    assert not (target["claude"] / "sessions" / "old.jsonl").exists()
    assert not (target["codex"] / "sessions" / "old.jsonl").exists()
    assert not (target["claude"] / ".credentials.json").exists()
    assert not (target["codex"] / "auth.json").exists()
    assert (target["claude"] / "settings.json").read_text(encoding="utf-8") == '{"theme":"dark"}\n'
    with closing(sqlite3.connect(target["sqlite"] / "memories_1.sqlite")) as connection:
        assert connection.execute("SELECT value FROM memory").fetchone() == ("from-wal",)

    full = run_tool(target, "Import", bundle, "-Full", "-IncludeAuth", "-Yes", "-AllowRunningApps")
    assert full.returncode == 0, full.stdout + full.stderr
    assert (target["claude"] / "sessions" / "old.jsonl").read_text(encoding="utf-8") == "session\n"
    assert (target["codex"] / "sessions" / "old.jsonl").read_text(encoding="utf-8") == "session\n"
    assert (target["claude"] / ".credentials.json").is_file()
    assert (target["codex"] / "auth.json").is_file()


def test_corrupt_bundle_is_rejected_before_profile_write(tmp_path: Path) -> None:
    source = make_profile(tmp_path / "source")
    bundle = tmp_path / "bundle"
    assert run_tool(source, "Export", bundle).returncode == 0
    (bundle / "claude" / "settings.json").write_text("tampered\n", encoding="utf-8")

    target = make_profile(tmp_path / "target")
    marker = target["claude"] / "settings.json"
    before = marker.read_bytes()
    result = run_tool(target, "Import", bundle, "-Yes", "-AllowRunningApps")
    assert result.returncode != 0
    assert "SHA-256" in result.stdout + result.stderr or "Размер не совпал" in result.stdout + result.stderr
    assert marker.read_bytes() == before


def test_manifest_cannot_relabel_auth_as_essential(tmp_path: Path) -> None:
    source = make_profile(tmp_path / "source")
    bundle = tmp_path / "bundle"
    assert run_tool(source, "Export", bundle, "-IncludeAuth").returncode == 0
    manifest_path = bundle / "manifest.json"
    payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    auth = next(entry for entry in payload["files"] if entry["path"] == "codex/auth.json")
    auth["category"] = "essential"
    manifest_path.write_text(json.dumps(payload), encoding="utf-8")

    target = make_profile(tmp_path / "target")
    before = (target["codex"] / "auth.json").read_bytes()
    result = run_tool(target, "Import", bundle, "-Yes", "-AllowRunningApps")
    assert result.returncode != 0
    assert "manifest" in result.stdout + result.stderr
    assert (target["codex"] / "auth.json").read_bytes() == before


def test_bundle_cannot_overlap_a_live_profile(tmp_path: Path) -> None:
    profile = make_profile(tmp_path / "profile")
    inside = run_tool(profile, "Export", profile["codex"] / "backup")
    assert inside.returncode != 0
    assert "пересекаться" in (inside.stdout + inside.stderr)
    assert not (profile["codex"] / "backup").exists()

    parent = run_tool(profile, "Export", profile["codex"].parent)
    assert parent.returncode != 0
    assert "пересекаться" in (parent.stdout + parent.stderr)


def test_foreign_absolute_paths_require_explicit_permission(tmp_path: Path) -> None:
    source = make_profile(tmp_path / "source")
    (source["codex"] / "config.toml").write_text('model = "test"\nnotes = "X:\\\\OldPC\\\\notes"\n', encoding="utf-8")
    bundle = tmp_path / "bundle"
    assert run_tool(source, "Export", bundle).returncode == 0

    target = make_profile(tmp_path / "target")
    blocked = run_tool(target, "Import", bundle, "-Yes", "-AllowRunningApps")
    assert blocked.returncode != 0
    assert "-AllowForeignPaths" in blocked.stdout + blocked.stderr

    preview = run_tool(target, "Import", bundle, "-DryRun")
    assert preview.returncode == 0, preview.stdout + preview.stderr
    assert "Dry run" in preview.stdout
    assert "OldPC" not in (target["codex"] / "config.toml").read_text(encoding="utf-8")


def test_claude_merge_preserves_conflicts_until_overwrite_is_explicit(tmp_path: Path) -> None:
    source = make_profile(tmp_path / "source")
    bundle = tmp_path / "bundle"
    assert run_tool(source, "Export", bundle).returncode == 0

    target = make_profile(tmp_path / "target")
    memory = target["claude"] / "projects" / "sample" / "memory"
    (memory / "fact.md").write_text("local fact\n", encoding="utf-8")
    (memory / "second.md").unlink()

    merged = run_tool(target, "Merge", bundle, "-AllowRunningApps")
    assert merged.returncode == 0, merged.stdout + merged.stderr
    assert (memory / "fact.md").read_text(encoding="utf-8") == "local fact\n"
    assert (memory / "second.md").read_text(encoding="utf-8") == "second fact\n"

    overwritten = run_tool(target, "Merge", bundle, "-Overwrite", "-AllowRunningApps")
    assert overwritten.returncode == 0, overwritten.stdout + overwritten.stderr
    assert (memory / "fact.md").read_text(encoding="utf-8") == "portable fact\n"


@pytest.fixture
def service_project(tmp_path: Path) -> Path:
    for name in ("config", "input", "output", "logs", "report"):
        (tmp_path / name).mkdir(parents=True, exist_ok=True)
    (tmp_path / "tools" / "ai_backup").mkdir(parents=True)
    return tmp_path


def run_service(project: Path, monkeypatch: pytest.MonkeyPatch, **parameters: Any) -> dict[str, Any]:
    recorded: dict[str, Any] = {}

    def fake_run_ps1(context, script, parameters=None, **kwargs):
        recorded.update(parameters or {})

    monkeypatch.setattr(devops, "run_ps1", fake_run_ps1)
    operation = Operation(
        id="ai_backup_probe",
        title="AI backup probe",
        description="",
        service="system_core.services.devops_tools:ai_backup",
        parameters=parameters,
    )
    context = JobContext(
        paths=get_project_paths(project),
        operation=operation,
        log_file=project / "logs" / "probe.log",
        report_dir=project / "report",
    )
    devops.ai_backup(context)
    return recorded


def test_gui_service_maps_the_same_restore_controls_as_cli(service_project: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    parameters = run_service(
        service_project,
        monkeypatch,
        mode="import",
        essentials=False,
        include_auth=True,
        dry_run=True,
        allow_foreign_paths=True,
        allow_legacy=True,
    )
    assert parameters == {
        "Mode": "Import",
        "Path": str(service_project / "input"),
        "Full": True,
        "IncludeAuth": True,
        "DryRun": True,
        "AllowForeignPaths": True,
        "AllowLegacy": True,
        "Yes": True,
    }


def test_gui_service_rejects_unknown_mode(service_project: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    with pytest.raises(RuntimeError, match="Unknown AI Backup mode"):
        run_service(service_project, monkeypatch, mode="guess")


def test_manifest_scopes_fields_to_the_relevant_operation() -> None:
    manifest = load_manifest(PROJECT_ROOT / "config" / "tool_manifest.yaml")

    def walk(nodes):
        for node in nodes:
            yield node
            yield from walk(node.children)

    nodes = {node.id: node for node in walk(manifest.operation_groups)}
    export_fields = {field["id"] for field in nodes["ai_backup_export"].fields}
    import_fields = {field["id"] for field in nodes["ai_backup_import"].fields}
    merge_fields = {field["id"] for field in nodes["ai_backup_merge"].fields}
    assert export_fields == {"essentials", "include_auth"}
    assert import_fields == {"essentials", "include_auth", "dry_run", "allow_foreign_paths", "allow_legacy"}
    assert merge_fields == {"overwrite", "dry_run", "allow_legacy"}


def test_wrappers_use_project_powershell_and_propagate_exit_code() -> None:
    for name in ("backup.cmd", "restore.cmd", "merge.cmd"):
        text = (TOOL_ROOT / "wrappers" / name).read_text(encoding="utf-8")
        assert "%PROJECT%\\system_core\\powershell\\pwsh.exe" in text
        assert "S:\\Audion" not in text
        assert "E:\\Audion" not in text
        assert "exit /b %EXIT_CODE%" in text


@pytest.mark.skipif(sys.platform != "win32", reason="CMD wrapper is Windows-only")
def test_backup_wrapper_returns_the_script_failure(tmp_path: Path) -> None:
    env = os.environ.copy()
    env.update(
        {
            "USERPROFILE": str(tmp_path / "user"),
            "CLAUDE_CONFIG_DIR": str(tmp_path / "missing-claude"),
            "CODEX_HOME": str(tmp_path / "missing-codex"),
            "CODEX_SQLITE_HOME": str(tmp_path / "missing-sqlite"),
            "AUDION_NO_PAUSE": "1",
        }
    )
    wrapper = TOOL_ROOT / "wrappers" / "backup.cmd"
    command = subprocess.list2cmdline([str(wrapper), "-Path", str(tmp_path / "bundle")])
    result = subprocess.run(["cmd.exe", "/d", "/s", "/c", command], env=env, capture_output=True)
    assert result.returncode != 0


@pytest.mark.skipif(sys.platform != "win32", reason="Windows PowerShell is Windows-only")
def test_script_parses_in_windows_powershell_51() -> None:
    executable = Path(os.environ.get("SystemRoot", r"C:\Windows")) / "System32" / "WindowsPowerShell" / "v1.0" / "powershell.exe"
    command = (
        "$null=$tokens=$errors=$null;"
        f"[System.Management.Automation.Language.Parser]::ParseFile('{SCRIPT}',[ref]$tokens,[ref]$errors)|Out-Null;"
        "if($errors.Count){$errors|ForEach-Object{$_.ToString()};exit 1}"
    )
    result = subprocess.run([str(executable), "-NoProfile", "-Command", command], capture_output=True)
    output = (result.stdout + result.stderr).decode("utf-8", errors="replace")
    assert result.returncode == 0, output
