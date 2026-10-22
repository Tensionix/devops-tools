from __future__ import annotations

import hashlib
import json
import os
import shutil
import sqlite3
import subprocess
import sys
from urllib.parse import quote
from pathlib import Path
from types import SimpleNamespace
from contextlib import closing

import pytest
import zstandard

from system_core.core import ai_form, operation_model
from system_core.core.manifest import load_manifest
from system_core.services import ai_catalog, ai_native, ai_transfer


ROOT = Path(__file__).resolve().parents[1]
KEEP = "11111111-1111-4111-8111-111111111111"
SKIP = "22222222-2222-4222-8222-222222222222"


def write_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value), encoding="utf-8")


def write_lines(path, values, compressed=False):
    path.parent.mkdir(parents=True, exist_ok=True)
    data = b"".join(ai_catalog.canonical(value) + b"\n" for value in values)
    path.write_bytes(zstandard.ZstdCompressor().compress(data) if compressed else data)


def claude_session(profile, identity, text="fixture conversation"):
    path = profile / "claude/projects/project" / f"{identity}.jsonl"
    write_lines(path, [{"type": "user", "sessionId": identity, "cwd": str(ROOT.parent), "timestamp": "2026-10-21T00:00:00Z",
                        "message": {"role": "user", "content": text}},
                       {"type": "assistant", "sessionId": identity, "message": {"role": "assistant", "content": [{"type": "text", "text": "Fixture reply"}]}}])
    return path


def codex_session(profile, identity, compressed=False, archived=False):
    folder = "archived_sessions" if archived else "sessions/2026/10/21"
    path = profile / "codex" / folder / (f"rollout-2026-10-21T00-00-00-{identity}.jsonl" + (".zst" if compressed else ""))
    write_lines(path, [
        {"timestamp": "2026-10-21T00:00:00.000Z", "type": "session_meta", "payload": {
            "id": identity, "timestamp": "2026-10-21T00:00:00.000Z", "cwd": str(profile), "originator": "codex_cli_rs",
            "cli_version": "0.163.0", "source": "cli", "model_provider": "openai"}},
        {"timestamp": "2026-10-21T00:00:01.000Z", "type": "event_msg", "payload": {"type": "user_message", "message": "Fixture question", "images": [], "local_images": [], "text_elements": []}},
        {"timestamp": "2026-10-21T00:00:01.000Z", "type": "response_item", "payload": {"type": "message", "role": "user", "content": [{"type": "input_text", "text": "Fixture question"}]}},
        {"timestamp": "2026-10-21T00:00:02.000Z", "type": "response_item", "payload": {"type": "message", "role": "assistant", "content": [{"type": "output_text", "text": "Fixture answer"}]}},
        {"timestamp": "2026-10-21T00:00:02.000Z", "type": "event_msg", "payload": {"type": "agent_message", "message": "Fixture answer", "phase": "final_answer"}}
    ], compressed)
    return path


def grok_session(profile, identity):
    folder = profile / "grok/sessions" / quote(str(ROOT.parent), safe="") / identity
    write_json(folder / "summary.json", {"info": {"id": identity, "cwd": str(ROOT.parent)}, "session_summary": "Fixture Grok conversation",
        "created_at": "2026-10-21T00:00:00Z", "updated_at": "2026-10-21T00:00:01Z", "chat_format_version": 1, "num_chat_messages": 2,
        "num_messages": 2, "agent_id": "ag1." + identity.replace("-", ""), "attempt_id": "at1." + identity.replace("-", ""), "current_model_id": "grok-4.7", "next_trace_turn": 0,
        "grok_home": str(profile / "grok"), "agent_name": "grok-build-plan", "sandbox_profile": "off", "reasoning_effort": "high"})
    write_lines(folder / "chat_history.jsonl", [{"type": "user", "content": "Fixture request"}, {"type": "assistant", "content": "Fixture response"}])
    write_lines(folder / "updates.jsonl", [{"timestamp": 1792540800000, "method": "session/update", "params": {
        "sessionId": identity, "update": {"sessionUpdate": kind, "content": {"type": "text", "text": text}}}}
        for kind, text in [("user_message_chunk", "Fixture request"), ("agent_message_chunk", "Fixture response")]])
    return folder


@pytest.fixture
def isolated(tmp_path, monkeypatch):
    def use(profile):
        monkeypatch.setenv("USERPROFILE", str(profile / "user"))
        monkeypatch.setenv("CLAUDE_CONFIG_DIR", str(profile / "claude"))
        monkeypatch.setenv("CODEX_HOME", str(profile / "codex"))
        monkeypatch.setenv("CODEX_SQLITE_HOME", str(profile / "sqlite"))
        monkeypatch.setenv("GROK_HOME", str(profile / "grok"))
        monkeypatch.setenv("APPDATA", str(profile / "roaming"))
        monkeypatch.setenv("LOCALAPPDATA", str(profile / "local"))
        return profile
    use(tmp_path / "source")
    return use


def context(tmp_path, **params):
    project = tmp_path / "project"
    project.mkdir(exist_ok=True)
    messages = []
    paths = SimpleNamespace(root=project, input=project / "input", output=project / "output", backup=project / "backup")
    return SimpleNamespace(paths=paths, operation=SimpleNamespace(parameters=params), log=messages.append,
                           progress=lambda value: None, cancelled=lambda: False, messages=messages)


def export(tmp_path, **params):
    active = context(tmp_path)
    result = ai_transfer.export_backup(active, {"selected_chats": [f"claude:{KEEP}"], "data_categories": [], "dry_run": False, **params})
    return Path(result["path"])


def tree_hash(root):
    return {str(path.relative_to(root)): hashlib.sha256(path.read_bytes()).hexdigest() for path in root.rglob("*") if path.is_file()}


def test_catalog_finds_cli_without_desktop_and_compressed_archives(tmp_path, isolated):
    profile = isolated(tmp_path / "source")
    claude_session(profile, KEEP)
    codex_session(profile, KEEP, compressed=True, archived=True)
    grok_session(profile, KEEP)
    data = ai_catalog.scan()
    assert {chat["key"] for chat in data["chats"]} == {f"claude:{KEEP}", f"codex:{KEEP}", f"grok:{KEEP}"}
    assert next(chat for chat in data["chats"] if chat["app"] == "codex")["archived"]
    assert all(chat["complete"] for chat in data["chats"])
    assert ai_catalog.live_chat_options(values={"chat_provider": "codex"})[0]["value"] == f"codex:{KEEP}"


def test_desktop_and_cli_are_one_chat_and_sidecars_travel_together(tmp_path, isolated):
    profile = isolated(tmp_path / "source")
    main = claude_session(profile, KEEP)
    write_lines(main.with_suffix("") / "subagents/agent.jsonl", [{"type": "assistant", "message": {"content": "Subagent"}}])
    write_json(profile / "roaming/Claude/claude-code-sessions/a/w/local_one.json", {"cliSessionId": KEEP, "title": "Actual Desktop title"})
    data = ai_catalog.scan()
    assert len(data["chats"]) == 1
    chat = data["chats"][0]
    assert set(chat["sources"]) == {"claude", "claude_desktop"}
    assert chat["title"] == "Actual Desktop title"
    assert len(chat["files"]) == 3
    bundle = export(tmp_path)
    assert len(ai_transfer.load_bundle(bundle)["catalog"]["chats"]) == 1


def test_explicit_empty_chat_selection_never_includes_conversations(tmp_path, isolated):
    profile = isolated(tmp_path / "source")
    claude_session(profile, KEEP)
    codex_session(profile, SKIP)
    write_json(profile / "claude/settings.json", {"theme": "fixture"})
    write_json(profile / "claude/.credentials.json", {"secret": "must-not-travel"})
    bundle = export(tmp_path, selected_chats=[], data_categories=["claude:settings"])
    loaded = ai_transfer.load_bundle(bundle)
    assert loaded["catalog"]["chats"] == []
    assert [entry["path"] for entry in loaded["manifest"]["files"]] == ["claude/settings.json"]
    assert "must-not-travel" not in (bundle / "manifest.json").read_text(encoding="utf-8")


def test_selected_chat_travels_without_other_data_and_unselected_metadata(tmp_path, isolated):
    profile = isolated(tmp_path / "source")
    claude_session(profile, KEEP, "selected title")
    claude_session(profile, SKIP, "PRIVATE-UNSELECTED-TITLE")
    bundle = export(tmp_path)
    assert SKIP not in (bundle / "manifest.json").read_text(encoding="utf-8")
    assert "PRIVATE-UNSELECTED-TITLE" not in (bundle / "manifest.json").read_text(encoding="utf-8")
    assert ai_transfer.load_bundle(bundle)["catalog"]["chats"][0]["key"] == f"claude:{KEEP}"


def test_custom_source_and_parent_ai_backup_are_honored(tmp_path, isolated):
    profile = isolated(tmp_path / "source")
    claude_session(profile, KEEP)
    bundle = export(tmp_path, output_path=str(tmp_path / "chosen"))
    assert ai_transfer.bundle_chat_options(tmp_path, {"input_path": str(bundle.parent)})[0]["value"] == f"claude:{KEEP}"


def test_preview_never_creates_profiles_or_publishes_backup(tmp_path, isolated):
    profile = isolated(tmp_path / "source")
    claude_session(profile, KEEP)
    active = context(tmp_path)
    result = ai_transfer.export_backup(active, {"selected_chats": [f"claude:{KEEP}"], "data_categories": [], "dry_run": True})
    assert result["dry_run"] and not active.paths.output.exists()
    bundle = export(tmp_path)
    target = isolated(tmp_path / "target")
    before = tree_hash(bundle)
    result = ai_transfer.import_backup(active, {"input_path": str(bundle), "selected_chats": [f"claude:{KEEP}"], "data_categories": [], "dry_run": True})
    assert result["counts"] == {"ADD": 1}
    assert tree_hash(bundle) == before
    assert not target.exists()


def test_import_preserves_unrelated_and_conflicts_by_default(tmp_path, isolated, monkeypatch):
    source = isolated(tmp_path / "source")
    claude_session(source, KEEP, "incoming")
    bundle = export(tmp_path)
    target = isolated(tmp_path / "target")
    local = claude_session(target, KEEP, "local conflict")
    other = claude_session(target, SKIP, "unrelated")
    before = tree_hash(target)
    monkeypatch.setattr(ai_transfer, "processes_stopped", lambda apps: None)
    result = ai_transfer.import_backup(context(tmp_path), {"input_path": str(bundle), "selected_chats": [f"claude:{KEEP}"], "data_categories": [], "dry_run": False})
    assert result["counts"] == {"CONFLICT": 1}
    assert tree_hash(target) == before
    assert local.exists() and other.exists()


def test_replacement_is_backed_up_and_failure_rolls_back(tmp_path, isolated, monkeypatch):
    source = isolated(tmp_path / "source")
    claude_session(source, KEEP, "incoming")
    write_json(source / "claude/settings.json", {"theme": "incoming"})
    bundle = export(tmp_path, data_categories=["claude:settings"])
    target = isolated(tmp_path / "target")
    claude_session(target, KEEP, "local")
    write_json(target / "claude/settings.json", {"theme": "local"})
    before = tree_hash(target)
    monkeypatch.setattr(ai_transfer, "processes_stopped", lambda apps: None)
    active = context(tmp_path)
    counter = iter([False, True])
    active.cancelled = lambda: next(counter)
    with pytest.raises(RuntimeError, match="cancelled"):
        ai_transfer.import_backup(active, {"input_path": str(bundle), "selected_chats": [f"claude:{KEEP}"], "data_categories": ["claude:settings"],
                                         "dry_run": False, "overwrite_conflicts": True})
    assert tree_hash(target) == before
    journal = next(active.paths.backup.glob("*/journal.json"))
    assert json.loads(journal.read_text(encoding="utf-8"))["status"] == "rolled_back"


@pytest.mark.parametrize("mutation", ["file", "category", "catalog", "traversal", "duplicate"])
def test_tampered_backups_are_rejected_before_profile_write(tmp_path, isolated, mutation):
    source = isolated(tmp_path / "source")
    claude_session(source, KEEP)
    bundle = export(tmp_path)
    manifest_file = bundle / "manifest.json"
    manifest = json.loads(manifest_file.read_text(encoding="utf-8"))
    if mutation == "file":
        (bundle / manifest["files"][0]["path"]).write_text("changed", encoding="utf-8")
    elif mutation == "category":
        manifest["files"][0]["category"] = "settings"
    elif mutation == "catalog":
        manifest["catalog"]["chats"][0]["title"] = "tampered"
    elif mutation == "traversal":
        manifest["files"][0]["path"] = "../escape"
    elif mutation == "duplicate":
        manifest["files"].append(manifest["files"][0])
    manifest_file.write_text(json.dumps(manifest), encoding="utf-8")
    target = isolated(tmp_path / "target")
    with pytest.raises(ValueError):
        ai_transfer.import_backup(context(tmp_path), {"input_path": str(bundle), "selected_chats": [f"claude:{KEEP}"], "data_categories": [], "dry_run": False})
    assert not target.exists()


def test_failed_export_preserves_previous_bundle(tmp_path, isolated, monkeypatch):
    source = isolated(tmp_path / "source")
    claude_session(source, KEEP)
    bundle = export(tmp_path)
    before = tree_hash(bundle)
    def fail(*args):
        raise OSError("fixture write failure")
    monkeypatch.setattr(ai_transfer, "snapshot_file", fail)
    with pytest.raises(OSError):
        export(tmp_path)
    assert tree_hash(bundle) == before


def test_unknown_selection_and_profile_overlap_fail(tmp_path, isolated):
    source = isolated(tmp_path / "source")
    claude_session(source, KEEP)
    with pytest.raises(ValueError, match="Unknown selected chat"):
        export(tmp_path, selected_chats=["codex:missing"])
    with pytest.raises(ValueError, match="overlaps"):
        export(tmp_path, output_path=str(source / "claude"))


def test_new_form_is_explicit_and_legacy_cli_parameters_are_preserved():
    manifest = load_manifest(ROOT / "config/tool_manifest.yaml")
    node = operation_model.find_node(manifest, "ai_backup_export")
    original = operation_model.build_parameters(node, {}, ROOT / "input", ROOT / "output", ROOT)
    assert "transfer_version" not in original
    updated = operation_model.build_parameters(node, {"transfer_version": 3, "selected_chats": [], "data_categories": []}, ROOT / "input", ROOT / "output", ROOT)
    assert updated["selected_chats"] == [] and updated["data_categories"] == [] and updated["dry_run"]
    fields = ai_form.fields_for(node.id, node.fields)
    assert next(field for field in fields if field["id"] == "ai_export__selected_chats")["default"] == []
    with pytest.raises(RuntimeError, match="version"):
        operation_model.build_parameters(node, {"transfer_version": "3"}, ROOT / "input", ROOT / "output", ROOT)
    with pytest.raises(RuntimeError, match="mix"):
        operation_model.build_parameters(node, {"transfer_version": 3, "essentials": False}, ROOT / "input", ROOT / "output", ROOT)


@pytest.mark.skipif(shutil.which("codex") is None, reason="Codex CLI is not installed")
def test_native_codex_lists_and_reads_restored_plain_and_compressed_sessions(tmp_path, isolated):
    profile = isolated(tmp_path / "native")
    profile.mkdir(parents=True, exist_ok=True)
    codex_session(profile, KEEP)
    codex_session(profile, SKIP, compressed=True, archived=True)
    data = ai_catalog.scan()
    ai_native.verify_codex(profile / "codex", profile / "sqlite", profile, data["chats"])
    with ai_native.CodexClient(profile / "codex", profile / "sqlite", profile) as client:
        plain = client.request("thread/read", {"threadId": KEEP, "includeTurns": True})
        archived = client.request("thread/read", {"threadId": SKIP, "includeTurns": True})
    assert plain["thread"]["id"] == KEEP and archived["thread"]["id"] == SKIP
    assert "Fixture answer" in json.dumps(plain) and "Fixture answer" in json.dumps(archived)


@pytest.mark.skipif(shutil.which("grok") is None, reason="Grok CLI is not installed")
def test_native_grok_detects_restored_session(tmp_path, isolated):
    profile = isolated(tmp_path / "native-grok")
    grok_session(profile, KEEP)
    ai_native.verify_grok(profile / "grok", ai_catalog.scan()["chats"], profile)


def test_path_mapping_changes_metadata_and_folder_but_not_messages(tmp_path, isolated, monkeypatch):
    profile = isolated(tmp_path / "source")
    source = claude_session(profile, KEEP, str(ROOT.parent))
    bundle = export(tmp_path)
    target = isolated(tmp_path / "target")
    destination_project = ROOT
    monkeypatch.setattr(ai_transfer, "processes_stopped", lambda apps: None)
    result = ai_transfer.import_backup(context(tmp_path), {"input_path": str(bundle), "selected_chats": [f"claude:{KEEP}"], "data_categories": [],
        "dry_run": False, "path_map": {str(ROOT.parent): str(destination_project)}})
    restored = next((target / "claude/projects").glob("*/*.jsonl"))
    row = json.loads(restored.read_text(encoding="utf-8").splitlines()[0])
    assert row["cwd"] == str(destination_project)
    assert row["message"]["content"] == str(ROOT.parent)
    assert json.loads(source.read_text(encoding="utf-8").splitlines()[0])["cwd"] == str(ROOT.parent)
    assert result["counts"] == {"ADD": 1}


def test_preview_token_rejects_changed_backup_before_writes(tmp_path, isolated):
    source = isolated(tmp_path / "source")
    claude_session(source, KEEP)
    bundle = export(tmp_path)
    target = isolated(tmp_path / "target")
    params = {"input_path": str(bundle), "selected_chats": [f"claude:{KEEP}"], "data_categories": [], "dry_run": True}
    preview = ai_transfer.import_backup(context(tmp_path), params)
    manifest_path = bundle / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["created_utc"] = "2026-10-22T00:00:00Z"
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
    with pytest.raises(ValueError, match="changed"):
        ai_transfer.import_backup(context(tmp_path), dict(params, dry_run=False, ai_plan_token=preview["plan_token"]))
    assert not target.exists()


def test_legacy_without_manifest_requires_explicit_permission(tmp_path, isolated):
    source = isolated(tmp_path / "source")
    claude_session(source, KEEP)
    bundle = export(tmp_path)
    (bundle / "manifest.json").unlink()
    with pytest.raises(ValueError):
        ai_transfer.load_bundle(bundle)
    loaded = ai_transfer.load_bundle(bundle, allow_legacy=True)
    assert loaded["unverified_legacy"] and loaded["catalog"]["chats"][0]["key"] == f"claude:{KEEP}"


def test_native_forms_keep_import_and_export_selection_independent():
    manifest = load_manifest(ROOT / "config/tool_manifest.yaml")
    nodes = [operation_model.find_node(manifest, identity) for identity in sorted(ai_form.OPERATIONS)]
    ids = [{field["id"] for field in ai_form.fields_for(node.id, node.fields) if not field.get("hidden")} for node in nodes]
    assert not ids[0] & ids[1]


@pytest.mark.skipif(shutil.which("codex") is None, reason="Codex CLI is not installed")
def test_native_codex_failure_rolls_back_and_preserves_other_threads(tmp_path, isolated, monkeypatch):
    source = isolated(tmp_path / "source")
    source.mkdir(parents=True)
    codex_session(source, KEEP)
    bundle = export(tmp_path, selected_chats=[f"codex:{KEEP}"])
    target = isolated(tmp_path / "target")
    target.mkdir(parents=True)
    codex_session(target, SKIP)
    ai_native.verify_codex(target / "codex", target / "sqlite", target, ai_catalog.scan()["chats"])
    before = tree_hash(target)
    native = ai_native.verify_codex
    def fail_after_native(*args):
        native(*args)
        raise RuntimeError("fixture native verification failure")
    monkeypatch.setattr(ai_native, "verify_codex", fail_after_native)
    monkeypatch.setattr(ai_transfer, "processes_stopped", lambda apps: None)
    with pytest.raises(RuntimeError, match="fixture"):
        ai_transfer.import_backup(context(tmp_path), {"input_path": str(bundle), "selected_chats": [f"codex:{KEEP}"], "data_categories": [], "dry_run": False})
    assert tree_hash(target) == before


def test_readonly_sqlite_snapshot_reads_wal_without_changing_profile(tmp_path, isolated):
    profile = isolated(tmp_path / "source")
    directory = profile / "sqlite"
    directory.mkdir(parents=True)
    database = directory / "memories_1.sqlite"
    with closing(sqlite3.connect(database)) as live:
        live.execute("PRAGMA journal_mode=WAL")
        live.execute("PRAGMA wal_autocheckpoint=0")
        live.execute("CREATE TABLE facts (value TEXT)")
        live.execute("INSERT INTO facts VALUES ('fixture memory')")
        live.commit()
        before = tree_hash(profile)
        with ai_catalog.readonly_database(database) as reader:
            assert reader.execute("SELECT value FROM facts").fetchone()[0] == "fixture memory"
        assert tree_hash(profile) == before
        bundle = export(tmp_path, selected_chats=[], data_categories=["codex:memory"])
        with closing(sqlite3.connect(bundle / "codex_sqlite/memories_1.sqlite")) as reader:
            assert reader.execute("SELECT value FROM facts").fetchone()[0] == "fixture memory"
        assert tree_hash(profile) == before


def test_recovery_preview_preserves_later_changes_and_explicit_rollback_works(tmp_path, isolated, monkeypatch):
    source = isolated(tmp_path / "source")
    claude_session(source, KEEP)
    bundle = export(tmp_path)
    target = isolated(tmp_path / "target")
    claude_session(target, SKIP, "unrelated")
    before = tree_hash(target)
    monkeypatch.setattr(ai_transfer, "processes_stopped", lambda apps: None)
    active = context(tmp_path)
    result = ai_transfer.import_backup(active, {"input_path": str(bundle), "selected_chats": [f"claude:{KEEP}"], "data_categories": [], "dry_run": False})
    restored = target / "claude/projects/project" / f"{KEEP}.jsonl"
    restored.write_text("later local edit", encoding="utf-8")
    plan = ai_transfer.rollback_import(active, {"journal_path": result["journal"], "dry_run": True})
    assert plan["counts"] == {"CONFLICT": 1}
    with pytest.raises(ValueError, match="changed"):
        ai_transfer.rollback_import(active, {"journal_path": result["journal"], "dry_run": False})
    ai_transfer.rollback_import(active, {"journal_path": result["journal"], "dry_run": False, "overwrite_conflicts": True})
    assert tree_hash(target) == before


def test_inventory_options_cache_is_shared_and_refresh_bypasses_it(tmp_path, isolated, monkeypatch):
    profile = isolated(tmp_path / "source")
    claude_session(profile, KEEP)
    original = ai_catalog.scan
    calls = []
    def counted():
        calls.append(True)
        return original()
    monkeypatch.setattr(ai_catalog, "scan", counted)
    assert len(ai_catalog.scan_options(tmp_path)["chats"]) == 1
    claude_session(profile, SKIP)
    assert len(ai_catalog.scan_options(tmp_path)["chats"]) == 1
    assert len(ai_catalog.scan_options(tmp_path, {"_refresh_options": True})["chats"]) == 2
    assert len(calls) == 2


def test_durable_journal_recovers_after_process_exit(tmp_path, isolated, monkeypatch):
    source = isolated(tmp_path / "source")
    claude_session(source, KEEP, "incoming")
    write_json(source / "claude/settings.json", {"theme": "incoming"})
    bundle = export(tmp_path, data_categories=["claude:settings"])
    target = isolated(tmp_path / "target")
    claude_session(target, KEEP, "original local")
    write_json(target / "claude/settings.json", {"theme": "original local"})
    before = tree_hash(target)
    parameters = {"input_path": str(bundle), "selected_chats": [f"claude:{KEEP}"], "data_categories": ["claude:settings"],
                  "dry_run": False, "overwrite_conflicts": True}
    script = """
import json, os, sys
from pathlib import Path
sys.path.insert(0, str(Path.cwd()))
from tests.test_ai_transfer import context
from system_core.services import ai_transfer
active = context(Path(sys.argv[1]))
counter = {"calls": 0}
def interrupted():
    counter["calls"] += 1
    if counter["calls"] == 2:
        os._exit(91)
    return False
active.cancelled = interrupted
ai_transfer.processes_stopped = lambda apps: None
ai_transfer.import_backup(active, json.loads(sys.argv[2]))
raise SystemExit(2)
"""
    result = subprocess.run([sys.executable, "-X", "utf8", "-c", script, str(tmp_path), json.dumps(parameters)],
                            cwd=ROOT, env=os.environ.copy(), capture_output=True, timeout=30)
    assert result.returncode == 91, result.stderr.decode("utf-8", errors="replace")
    assert tree_hash(target) != before
    active = context(tmp_path)
    journal = next(active.paths.backup.glob("*/journal.json"))
    assert json.loads(journal.read_text(encoding="utf-8"))["status"] == "applying"
    monkeypatch.setattr(ai_transfer, "processes_stopped", lambda apps: None)
    ai_transfer.rollback_import(active, {"journal_path": str(journal), "dry_run": False})
    assert tree_hash(target) == before


def test_essential_preset_leaves_out_only_what_codex_installs_itself():
    assert "codex:plugins" not in ai_catalog.ESSENTIAL
    assert {"claude:plugins", "claude:memory", "codex:memory", "codex:skills", "codex:automations"} <= set(ai_catalog.ESSENTIAL)
    assert "codex:plugins" in ai_catalog.ALL_CATEGORIES
