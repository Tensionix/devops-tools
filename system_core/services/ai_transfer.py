from __future__ import annotations

import copy
import hashlib
import json
import os
import shutil
import sqlite3
import subprocess
import tempfile
import uuid
from collections import Counter
from contextlib import closing
from pathlib import Path
from typing import Any
from urllib.parse import quote

from system_core.services import ai_catalog as catalog
from system_core.services import ai_native


inventory_options = catalog.inventory_options
category_options = catalog.category_options
project_options = catalog.project_options


def normalized(values, mode):
    prefix = f"ai_{mode}__"
    return {**(values or {}), **{key[len(prefix):]: value for key, value in (values or {}).items() if key.startswith(prefix)}}


def live_chat_options(root=None, values=None):
    return catalog.live_chat_options(root, normalized(values, "export"))


def category_of(relative: str) -> tuple[str, str]:
    parts = relative.replace("\\", "/").split("/")
    app = parts[0]
    rest = "/".join(parts[1:])
    if app == "claude_app" and rest.startswith("claude-code-sessions/") and parts[-1].startswith("local_") and rest.endswith(".json"):
        return "claude_desktop", "chat"
    if app == "codex_sqlite" and rest in {"memories_1.sqlite", "goals_1.sqlite"}:
        return "codex", "memory"
    if app not in catalog.PROFILE_ITEMS:
        raise ValueError(f"Unsupported bundle component: {relative}")
    if rest == (".credentials.json" if app == "claude" else "auth.json"):
        return app, "auth"
    if app == "claude" and len(parts) >= 4 and parts[1] == "projects":
        identity = parts[3].removesuffix(".jsonl")
        if catalog.UUID.fullmatch(identity):
            return app, "chat"
    if app == "codex" and parts[1] in {"sessions", "archived_sessions"} and relative.endswith((".jsonl", ".jsonl.zst")):
        return app, "chat"
    if app == "grok" and len(parts) >= 5 and parts[1] == "sessions" and catalog.UUID.fullmatch(parts[3]):
        return app, "chat"
    for category, patterns in catalog.PROFILE_ITEMS[app].items():
        for pattern in patterns:
            if pattern == "projects/*/memory":
                if len(parts) >= 5 and parts[1] == "projects" and parts[3] == "memory":
                    return app, category
            elif rest == pattern or rest.startswith(pattern + "/"):
                return app, category
    raise ValueError(f"Unsupported profile data: {relative}")


def pick_bundle(source: Path, allow_legacy: bool = False) -> Path:
    if (source / "manifest.json").is_file():
        return source
    if (source / "ai_backup/manifest.json").is_file():
        return source / "ai_backup"
    if allow_legacy:
        candidates = [path for path in (source, source / "ai_backup") if any((path / app).is_dir() for app in ("claude", "codex", "grok", "claude_app"))]
        if len(candidates) == 1:
            return candidates[0]
        if len(candidates) > 1:
            raise ValueError("More than one legacy backup found; select its exact folder")
    raise ValueError("No AI backup found in SOURCE / В ИСТОЧНИКЕ нет бэкапа AI")


def load_bundle(source: Path, allow_legacy: bool = False) -> dict[str, Any]:
    root = pick_bundle(source, allow_legacy)
    manifest_file = catalog.safe_path(root, "manifest.json")
    unverified = not manifest_file.is_file()
    if unverified:
        if not allow_legacy:
            raise ValueError("Legacy backup requires explicit permission")
        warnings = []
        entries = [{"path": path.relative_to(root).as_posix(), "size": path.stat().st_size, "sha256": catalog.digest(path)} for path in catalog.walk_files(root, warnings)]
        if warnings:
            raise ValueError("Legacy backup contains inaccessible files or reparse points")
        manifest = {"schema_version": 1, "files": entries, "source": {}}
    else:
        manifest = catalog.read_json(manifest_file)
    schema = manifest.get("schema_version")
    if schema not in (1, 2, 3):
        raise ValueError(f"Unsupported AI backup schema: {schema}")
    entries = manifest.get("files")
    if not isinstance(entries, list) or not entries:
        raise ValueError("Backup has no file inventory")
    seen = set()
    for entry in entries:
        if not isinstance(entry, dict) or not isinstance(entry.get("path"), str):
            raise ValueError("Invalid manifest entry")
        name = entry["path"]
        normalized = name.replace("\\", "/").casefold()
        if normalized in seen:
            raise ValueError(f"Duplicate bundle path: {name}")
        seen.add(normalized)
        path = catalog.safe_path(root, name, existing=True)
        if not isinstance(entry.get("sha256"), str) or len(entry["sha256"]) != 64 or path.stat().st_size != entry.get("size") or catalog.digest(path) != entry["sha256"]:
            raise ValueError(f"Backup integrity check failed: {name}")
        if schema == 3:
            app, category = category_of(name)
            if entry.get("app") != app or entry.get("category") != category:
                raise ValueError(f"Incorrect file ownership: {name}")
    if schema == 3:
        data = manifest.get("catalog")
        if not isinstance(data, dict) or hashlib.sha256(catalog.canonical(data)).hexdigest() != manifest.get("catalog_sha256"):
            raise ValueError("Backup catalog integrity check failed")
        file_map = {entry["path"]: entry for entry in entries}
        warnings = []
        actual_files = {path.relative_to(root).as_posix() for path in catalog.walk_files(root, warnings)}
        if warnings or actual_files != set(file_map) | {"manifest.json"}:
            raise ValueError("Backup contains unlisted files or inaccessible paths")
        keys = set()
        owned = set()
        for chat in data.get("chats", []):
            key = chat.get("key")
            if not isinstance(key, str) or key in keys or key != f"{chat.get('app')}:{chat.get('id')}":
                raise ValueError("Invalid chat identity in catalog")
            keys.add(key)
            if not isinstance(chat.get("files"), list) or not chat["files"]:
                raise ValueError("Chat has no files")
            for name in chat["files"]:
                entry = file_map.get(name)
                if not entry or entry.get("category") != "chat" or entry.get("chat") != key or name in owned:
                    raise ValueError("Chat dependency does not match the file inventory")
                owned.add(name)
                parts = name.split("/")
                if entry["app"] == "claude" and parts[3].removesuffix(".jsonl") != chat["id"]:
                    raise ValueError("Claude chat identity does not match its files")
                if entry["app"] == "grok" and parts[3] != chat["id"]:
                    raise ValueError("Grok chat identity does not match its files")
                if entry["app"] == "codex":
                    meta = catalog.session_metadata(root / name, "codex")
                    family = {chat["id"], *chat.get("dependencies", [])}
                    if meta.get("id") != chat["id"] and (meta.get("id") not in family or meta.get("parent") not in family):
                        raise ValueError("Codex chat identity does not match its files")
                if entry["app"] == "claude_desktop":
                    desktop = catalog.read_json(root / name)
                    if chat["app"] == "claude" and desktop.get("cliSessionId") != chat["id"]:
                        raise ValueError("Desktop transcript identity does not match")
        if {entry["path"] for entry in entries if entry["category"] == "chat"} != owned:
            raise ValueError("Orphan chat files in backup")
        expected_categories = {(entry["app"], entry["category"]) for entry in entries if entry["category"] not in {"chat", "auth"}}
        if {(item["app"], item["category"]) for item in data.get("categories", [])} != expected_categories:
            raise ValueError("Category catalog does not match files")
        for item in data["categories"]:
            members = [entry for entry in entries if (entry["app"], entry["category"]) == (item["app"], item["category"])]
            if item.get("key") != f"{item['app']}:{item['category']}" or item.get("count") != len(members) or item.get("size") != sum(entry["size"] for entry in members):
                raise ValueError("Incorrect category inventory")
    else:
        data = legacy_catalog(root, manifest)
    return {"root": root, "manifest": manifest, "catalog": data, "unverified_legacy": unverified,
            "fingerprint": hashlib.sha256(catalog.canonical(manifest)).hexdigest() if unverified else catalog.digest(manifest_file)}


def legacy_catalog(root: Path, manifest: dict) -> dict:
    chats = {}
    usable = []
    warnings = ["Legacy backup: only supported files can be restored; shared live state databases are excluded"]
    for original in manifest["files"]:
        entry = dict(original)
        try:
            app, category = category_of(entry["path"])
        except ValueError:
            continue
        entry.update(app=app, category=category, chat="")
        if category == "chat":
            path = root / entry["path"]
            if app == "claude_desktop":
                info = catalog.read_json(path)
                identity = info.get("cliSessionId") or path.stem
                primary = "claude" if catalog.UUID.fullmatch(str(identity)) else "claude_desktop"
                key = f"{primary}:{identity}"
                meta = {"title": info.get("title", ""), "cwd": info.get("cwd", "")}
            elif app == "claude":
                identity = entry["path"].split("/")[3].removesuffix(".jsonl")
                key = f"claude:{identity}"
                meta = catalog.session_metadata(path, app) if path.name.endswith(".jsonl") else {}
            elif app == "codex":
                meta = catalog.session_metadata(path, app)
                found = catalog.UUID.search(path.name)
                identity = meta.get("id") or (found.group(0) if found else "")
                key = f"codex:{identity}"
            else:
                continue
            chat = chats.setdefault(key, {"key": key, "id": str(identity), "app": key.split(":")[0], "title": "", "cwd": "",
                "created": 0, "updated": 0, "archived": "archived_sessions" in path.parts, "sources": [], "files": [], "size": 0,
                "complete": False, "restore": "unsupported", "warnings": []})
            if meta.get("title"):
                chat["title"] = catalog.message_text(meta["title"])
            chat["cwd"] = str(meta.get("cwd") or chat["cwd"])
            if app not in chat["sources"]:
                chat["sources"].append(app)
            if meta.get("recognized"):
                chat.update(complete=True, restore="native")
            chat["files"].append(entry["path"])
            chat["size"] += entry["size"]
            entry["chat"] = key
        usable.append(entry)
    categories = []
    for app, category in sorted({(entry["app"], entry["category"]) for entry in usable if entry["category"] not in {"chat", "auth"}}):
        entries = [entry for entry in usable if (entry["app"], entry["category"]) == (app, category)]
        categories.append({"key": f"{app}:{category}", "app": app, "category": category, "count": len(entries), "size": sum(entry["size"] for entry in entries)})
    manifest["compatible_files"] = usable
    return {"chats": list(chats.values()), "categories": categories, "sources": [], "warnings": warnings}


def bundle_source(root, values):
    return Path((values or {}).get("input_path") or Path(root or Path(__file__).resolve().parents[2]) / "input")


def bundle_for_options(root, values):
    values = normalized(values, "import")
    return load_bundle(bundle_source(root, values), bool(values.get("allow_legacy", False)))


def bundle_chat_options(root=None, values=None):
    return catalog.chat_options(bundle_for_options(root, values)["catalog"], normalized(values, "import"))


def bundle_category_options(root=None, values=None):
    return catalog.categories_as_options(bundle_for_options(root, values)["catalog"])


def bundle_project_options(root=None, values=None):
    data = bundle_for_options(root, values)["catalog"]
    return [catalog.option("all", "All projects", "Все проекты")] + [catalog.option(name, name or "No project", name or "Без проекта") for name in sorted({chat["cwd"] for chat in data["chats"]})]


def bundle_summary_options(root=None, values=None):
    loaded = bundle_for_options(root, values)
    manifest = loaded["manifest"]
    english = "Legacy backup; original integrity unavailable" if loaded["unverified_legacy"] else "Verified backup"
    russian = "Старый бэкап; исходная целостность неизвестна" if loaded["unverified_legacy"] else "Бэкап проверен"
    return [catalog.option("backup", f"{english} · schema {manifest['schema_version']} · {len(loaded['catalog']['chats'])} chats",
        f"{russian} · формат {manifest['schema_version']} · чатов {len(loaded['catalog']['chats'])}",
        hint=str(loaded["root"]) + "\n" + str(manifest.get("created_utc", "")), hint_ru=str(loaded["root"]) + "\n" + str(manifest.get("created_utc", ""))),
        *[catalog.option("", warning, warning, tone="warn") for warning in loaded["catalog"].get("warnings", [])[:3]]]


def selection(data: dict, params: dict) -> tuple[list[dict], list[dict]]:
    keys = params.get("selected_chats", [])
    categories = params.get("data_categories", catalog.ESSENTIAL)
    if not isinstance(keys, list) or not all(isinstance(key, str) for key in keys) or not isinstance(categories, list):
        raise ValueError("Chat and category selections must be lists")
    available = {chat["key"] for chat in data["chats"]}
    if set(keys) - available:
        raise ValueError("Unknown selected chat; refresh the inventory")
    if set(categories) - set(catalog.ALL_CATEGORIES):
        raise ValueError("Unknown selected data category")
    entries = [entry for entry in data["files"] if entry.get("chat") in keys or (
        entry["category"] not in {"chat", "auth"} and f"{entry['app']}:{entry['category']}" in categories) or
        entry["category"] == "auth" and params.get("include_auth", False)]
    return [chat for chat in data["chats"] if chat["key"] in keys], entries


def selection_options(root=None, values=None):
    data = catalog.scan_options(root, values)
    return selection_badges(data, normalized(values, "export"))


def bundle_selection_options(root=None, values=None):
    loaded = bundle_for_options(root, values)
    data = dict(loaded["catalog"], files=loaded["manifest"].get("compatible_files", loaded["manifest"]["files"]))
    return selection_badges(data, normalized(values, "import"))


def selection_badges(data, values):
    chats, files = selection(data, values)
    categories = {(entry["app"], entry["category"]) for entry in files if entry["category"] not in {"chat", "auth"}}
    size = sum(entry["size"] for entry in files)
    return [catalog.option("selection", f"Selected: {len(chats)} chats, {len(categories)} categories · {size/1048576:.1f} MB",
        f"Выбрано: чатов {len(chats)}, категорий {len(categories)} · {size/1048576:.1f} МБ")]


def snapshot_file(source: Path, target: Path):
    target.parent.mkdir(parents=True, exist_ok=True)
    if source.suffix.lower() in {".sqlite", ".sqlite3", ".db", ".db3"}:
        with source.open("rb") as stream:
            sqlite_header = stream.read(16) == b"SQLite format 3\x00"
        if sqlite_header:
            with catalog.readonly_database(source) as live:
                with closing(sqlite3.connect(target)) as saved:
                    live.backup(saved)
                    if saved.execute("PRAGMA integrity_check").fetchone()[0] != "ok":
                        raise ValueError("SQLite snapshot integrity check failed")
            return
    before = source.stat()
    shutil.copy2(source, target)
    after = source.stat()
    if (before.st_size, before.st_mtime_ns) != (after.st_size, after.st_mtime_ns) or catalog.digest(source) != catalog.digest(target):
        raise ValueError(f"Source changed during export: {source.name}")


def assert_outside_profiles(target: Path, profile: dict):
    destination = target.resolve()
    for root in [profile[name] for name in ("claude", "codex", "codex_sqlite", "grok")] + profile["desktop"]:
        resolved = root.resolve()
        if destination == resolved or destination.is_relative_to(resolved) or resolved.is_relative_to(destination):
            raise ValueError("Backup path overlaps an AI profile")


def plan_report(context, name: str, value: dict) -> str:
    folder = Path(getattr(context, "report_dir", context.paths.root / "report"))
    folder.mkdir(parents=True, exist_ok=True)
    path = catalog.safe_path(folder, name)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding="utf-8")
    context.log(f"AI plan: {path}")
    return str(path)


def export_backup(context, params):
    data = catalog.scan()
    chats, entries = selection(data, params)
    if not entries:
        raise ValueError("Nothing selected or available / Нет выбранных доступных данных")
    target = Path(params.get("output_path") or context.paths.output) / "ai_backup"
    assert_outside_profiles(target, catalog.roots())
    catalog.safe_path(target.parent, target.name)
    context.log(f"AI export: chats={len(chats)}, files={len(entries)}, bytes={sum(entry['size'] for entry in entries)}")
    token = hashlib.sha256(catalog.canonical({"target": str(target), "files": [(entry["path"], entry["size"], entry["mtime_ns"]) for entry in entries]})).hexdigest()
    if params.get("dry_run", True):
        result = {"dry_run": True, "chats": len(chats), "files": len(entries), "path": str(target), "warnings": data["warnings"],
                  "plan_token": token, "field_updates": {"ai_export__ai_plan_token": token},
                  "entries": [{key: entry[key] for key in ("path", "app", "category", "size")} for entry in entries]}
        result["plan_file"] = plan_report(context, "ai_export_plan.json", result)
        return result
    if params.get("ai_plan_token") and params["ai_plan_token"] != token:
        raise ValueError("Selected data changed; run the export preview again")
    target.parent.mkdir(parents=True, exist_ok=True)
    stage = Path(tempfile.mkdtemp(prefix=".ai_backup-stage-", dir=target.parent))
    previous = target.with_name(".ai_backup-previous-" + uuid.uuid4().hex)
    try:
        written = []
        for number, entry in enumerate(entries):
            if context.cancelled():
                raise RuntimeError("Operation cancelled by user.")
            source = Path(entry["source"])
            if (source.stat().st_size, source.stat().st_mtime_ns) != (entry["size"], entry["mtime_ns"]) and source.suffix not in {".sqlite", ".db"}:
                raise ValueError("Selected data changed; refresh the inventory")
            destination = catalog.safe_path(stage, entry["path"])
            snapshot_file(source, destination)
            saved = {key: entry[key] for key in ("path", "app", "category", "chat")}
            saved.update(size=destination.stat().st_size, sha256=catalog.digest(destination))
            written.append(saved)
            context.progress((number + 1) / len(entries))
        selected_categories = []
        for app, category in sorted({(entry["app"], entry["category"]) for entry in written if entry["category"] not in {"chat", "auth"}}):
            pieces = [entry for entry in written if (entry["app"], entry["category"]) == (app, category)]
            selected_categories.append({"key": f"{app}:{category}", "app": app, "category": category,
                                        "count": len(pieces), "size": sum(piece["size"] for piece in pieces)})
        saved_catalog = {"chats": chats, "categories": selected_categories, "sources": data["sources"], "warnings": data["warnings"]}
        manifest = {"schema_version": 3, "bundle_id": str(uuid.uuid4()), "created_utc": catalog.utc_now(),
                    "source": data["roots"], "files": written, "catalog": saved_catalog,
                    "catalog_sha256": hashlib.sha256(catalog.canonical(saved_catalog)).hexdigest(),
                    "includes_auth": any(entry["category"] == "auth" for entry in written)}
        (stage / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
        load_bundle(stage)
        if target.exists():
            target.rename(previous)
        try:
            stage.rename(target)
        except BaseException:
            if previous.exists():
                previous.rename(target)
            raise
        if previous.exists():
            shutil.rmtree(previous)
        return {"dry_run": False, "path": str(target), "chats": len(chats), "files": len(written), "schema_version": 3,
                "warnings": data["warnings"]}
    finally:
        if stage.exists():
            shutil.rmtree(stage)


def destination_for(entry: dict, profile: dict) -> Path:
    relative = entry.get("restore_path", entry["path"])
    if relative.startswith("claude_app/claude-code-sessions/"):
        candidates = [root for root in profile["desktop"] if root.exists()]
        root = max(candidates, key=lambda path: path.stat().st_mtime) if candidates else profile["desktop"][0]
        name = relative.split("claude_app/claude-code-sessions/", 1)[1]
        parts = name.split("/")
        if len(parts) >= 3 and root.is_dir() and not (root / parts[0] / parts[1]).is_dir():
            workspaces = [workspace for account in root.iterdir() if account.is_dir() and not catalog.linked(account)
                          for workspace in account.iterdir() if workspace.is_dir() and not catalog.linked(workspace)]
            if len(workspaces) == 1:
                name = workspaces[0].relative_to(root).as_posix() + "/" + "/".join(parts[2:])
            elif len(workspaces) > 1:
                raise ValueError("Desktop has multiple workspaces; the saved workspace cannot be matched safely")
        return catalog.safe_path(root, name)
    prefix, name = relative.split("/", 1)
    if prefix not in {"claude", "codex", "codex_sqlite", "grok"}:
        raise ValueError("Unknown import destination")
    return catalog.safe_path(profile[prefix], name)


def processes_stopped(apps: set[str]):
    if os.name != "nt":
        return
    result = subprocess.run(["tasklist.exe", "/FO", "CSV", "/NH"], capture_output=True, timeout=10,
                            **ai_native.hidden_subprocess_kwargs())
    if result.returncode:
        raise RuntimeError("Cannot verify running AI applications")
    import csv
    names = {row[0].lower() for row in csv.reader(result.stdout.decode("utf-8", errors="replace").splitlines()) if row}
    patterns = {"claude": {"claude.exe", "claude-desktop.exe"}, "claude_desktop": {"claude.exe", "claude-desktop.exe"},
                "codex": {"codex.exe", "chatgpt.exe"}, "grok": {"grok.exe"}}
    if any(names & patterns.get(app, set()) for app in apps):
        raise RuntimeError("Close the affected AI applications before importing / Закройте затрагиваемые AI-приложения перед импортом")


def prepare_mapping(entries, chats, root, mapping, stage):
    if not mapping:
        return entries, chats
    known = {chat["key"]: chat for chat in chats}
    folders = {}
    for chat in chats:
        if chat["cwd"] in mapping:
            for name in chat["files"]:
                parts = name.split("/")
                if len(parts) > 3 and parts[0] == "claude" and parts[1] == "projects":
                    folders[parts[2]] = catalog.re.sub(r"[^a-zA-Z0-9]", "-", mapping[chat["cwd"]])
    prepared = []
    for entry in entries:
        selected = dict(entry)
        parts = entry["path"].split("/")
        if len(parts) > 3 and parts[:2] == ["claude", "projects"] and parts[2] in folders:
            parts[2] = folders[parts[2]]
        if entry.get("chat") in known:
            chat = known[entry["chat"]]
            if chat["app"] == "grok" and chat["cwd"] in mapping:
                parts[2] = quote(mapping[chat["cwd"]], safe="")
        selected["restore_path"] = "/".join(parts)
        if entry["category"] == "chat" and entry["path"].endswith((".json", ".jsonl", ".jsonl.zst")):
            source = catalog.safe_path(root, entry["path"], existing=True)
            target = catalog.safe_path(stage, entry["path"])
            target.parent.mkdir(parents=True, exist_ok=True)
            def map_row(row):
                if not isinstance(row, dict):
                    return row
                containers = [row]
                if row.get("type") in {"session_meta", "turn_context"} and isinstance(row.get("payload"), dict):
                    containers.append(row["payload"])
                if isinstance(row.get("info"), dict):
                    containers.append(row["info"])
                for container in containers:
                    for key in ("cwd", "working_directory", "projectPath"):
                        if isinstance(container.get(key), str) and container[key] in mapping:
                            container[key] = mapping[container[key]]
                return row
            if source.name.endswith(".json"):
                target.write_bytes(catalog.canonical(map_row(catalog.read_json(source))))
            else:
                with catalog.transcript(source) as stream:
                    with target.open("wb") as raw:
                        if source.name.endswith(".zst"):
                            import zstandard
                            with zstandard.ZstdCompressor().stream_writer(raw, closefd=False) as destination:
                                for line in stream:
                                    destination.write(catalog.canonical(map_row(json.loads(line))) + b"\n")
                        else:
                            for line in stream:
                                raw.write(catalog.canonical(map_row(json.loads(line))) + b"\n")
            selected.update(source_sha256=entry["sha256"], sha256=catalog.digest(target), prepared_source=str(target))
        prepared.append(selected)
    restored = copy.deepcopy(chats)
    for chat in restored:
        chat["cwd"] = mapping.get(chat["cwd"], chat["cwd"])
    return prepared, restored


def import_backup(context, params):
    with tempfile.TemporaryDirectory(prefix=".ai-import-preview-", dir=context.paths.root) as stage:
        return import_loaded(context, params, Path(stage))


def import_loaded(context, params, stage):
    loaded = load_bundle(Path(params.get("input_path") or context.paths.input), bool(params.get("allow_legacy", False)))
    manifest, data, root = loaded["manifest"], loaded["catalog"], loaded["root"]
    data = dict(data, files=manifest.get("compatible_files", manifest["files"]))
    chats, entries = selection(data, params)
    if not entries:
        raise ValueError("Nothing selected or available / Нет выбранных доступных данных")
    for chat in chats:
        if not chat["complete"] or chat["restore"] != "native":
            raise ValueError(f"Chat format cannot be restored: {chat['key']}; files can be exported as an archive")
    profile = catalog.roots()
    path_map = params.get("path_map") or {}
    if isinstance(path_map, str):
        path_map = json.loads(path_map)
    if not isinstance(path_map, dict) or not all(isinstance(key, str) and isinstance(value, str) for key, value in path_map.items()):
        raise ValueError("Path mapping must be a JSON object of strings")
    if any(not Path(value).is_absolute() for value in path_map.values()):
        raise ValueError("Mapped project paths must be absolute")
    entries, chats = prepare_mapping(entries, chats, root, path_map, stage)
    planned = []
    local_catalog = catalog.scan()
    local_chats = {chat["key"]: chat for chat in local_catalog["chats"]}
    blocked = set()
    for chat in chats:
        previous = local_chats.get(chat["key"])
        if previous:
            existing_hashes = sorted(catalog.digest(Path(entry["source"])) for entry in local_catalog["files"] if entry.get("chat") == chat["key"])
            incoming_hashes = sorted(entry["sha256"] for entry in entries if entry.get("chat") == chat["key"])
            if existing_hashes != incoming_hashes and not params.get("overwrite_conflicts"):
                blocked.add(chat["key"])
    for entry in entries:
        destination = destination_for(entry, profile)
        state = "ADD"
        if entry.get("chat") in blocked:
            state = "CONFLICT"
        elif destination.exists():
            state = "SAME" if catalog.digest(destination) == entry["sha256"] else "REPLACE" if params.get("overwrite_conflicts") else "CONFLICT"
        planned.append({"entry": entry, "destination": destination, "state": state})
    counts = dict(Counter(item["state"] for item in planned))
    for state, count in counts.items():
        context.log(f"AI import {state}: {count}")
    for item in planned[:80]:
        context.log(f"{item['state']:8} {item['entry']['path']} -> {item['destination']}")
    foreign = []
    original_roots = manifest.get("source") or {}
    for item in planned:
        app = item["entry"]["app"]
        same_root = str(original_roots.get(app, "")).casefold() == str(profile.get(app, "")).casefold()
        if item["entry"]["category"] in {"settings", "instructions"} and not same_root:
            text = (root / item["entry"]["path"]).read_text(encoding="utf-8-sig", errors="replace")
            if catalog.re.search(r"(?:[A-Za-z]:\\|\\\\[^\\]+\\)", text):
                foreign.append(item["entry"]["path"])
    foreign_chats = [chat["key"] for chat in chats if chat["cwd"] and not Path(chat["cwd"]).is_dir() and chat["cwd"] not in path_map.values()]
    token = hashlib.sha256(catalog.canonical({"bundle": loaded["fingerprint"], "selection": params.get("selected_chats", []),
        "categories": params.get("data_categories", catalog.ESSENTIAL), "auth": params.get("include_auth", False),
        "overwrite": params.get("overwrite_conflicts", False), "mapping": path_map,
        "plan": [(item["entry"]["path"], item["entry"]["sha256"], str(item["destination"]), item["state"]) for item in planned]})).hexdigest()
    if params.get("dry_run", True):
        result = {"dry_run": True, "counts": counts, "plan": [{"path": item["entry"]["path"], "destination": str(item["destination"]), "state": item["state"]} for item in planned],
                "fingerprint": loaded["fingerprint"], "plan_token": token, "field_updates": {"ai_import__ai_plan_token": token},
                "foreign_path_files": foreign, "foreign_chat_paths": foreign_chats, "warnings": data.get("warnings", [])}
        result["plan_file"] = plan_report(context, "ai_import_plan.json", result)
        return result
    if params.get("ai_plan_token") and params["ai_plan_token"] != token:
        raise ValueError("Backup, destination or selection changed; run the preview again")
    changes = [item for item in planned if item["state"] in {"ADD", "REPLACE"}]
    if not changes:
        return {"dry_run": False, "counts": counts, "native_verified": [], "warnings": data.get("warnings", [])}
    if (foreign or foreign_chats) and not params.get("allow_foreign_paths"):
        raise ValueError("Saved configuration contains absolute paths; review the preview and explicitly allow them")
    changing_chats = [chat for chat in chats if chat["key"] not in blocked and any(item["entry"].get("chat") == chat["key"] for item in changes)]
    for app in {chat["app"] for chat in changing_chats} & {"codex", "grok"}:
        ai_native.require_version(app)
    grok_chats = [chat for chat in changing_chats if chat["app"] == "grok"]
    if grok_chats:
        validation_home = stage / "verify-grok"
        for item in planned:
            entry = item["entry"]
            if entry.get("chat") not in {chat["key"] for chat in grok_chats}:
                continue
            relative = entry.get("restore_path", entry["path"]).split("grok/", 1)[1]
            destination = catalog.safe_path(validation_home, relative)
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(Path(entry.get("prepared_source", root / entry["path"])), destination)
        ai_native.verify_grok(validation_home, grok_chats, context.paths.root)
    processes_stopped({item["entry"]["app"] for item in changes})
    if not loaded["unverified_legacy"] and catalog.digest(root / "manifest.json") != loaded["fingerprint"]:
        raise ValueError("Backup changed after planning")
    restore_root = context.paths.backup / ("ai_import_" + uuid.uuid4().hex)
    restore_root.mkdir(parents=True)
    journal = {"schema_version": 1, "operation": "ai_transfer_import", "status": "prepared", "files": [], "created_directories": []}
    journal_path = restore_root / "journal.json"

    def save_journal():
        temporary = journal_path.with_name(".journal-" + uuid.uuid4().hex + ".tmp")
        try:
            with temporary.open("w", encoding="utf-8") as stream:
                json.dump(journal, stream, ensure_ascii=False, indent=2)
                stream.flush()
                os.fsync(stream.fileno())
            temporary.replace(journal_path)
        finally:
            temporary.unlink(missing_ok=True)

    def remember(path: Path):
        if any(item["destination"] == str(path) for item in journal["files"]):
            return
        saved = restore_root / f"file-{len(journal['files']):06d}"
        exists = path.exists()
        if exists:
            shutil.copy2(path, saved)
        journal["files"].append({"destination": str(path), "saved": saved.name if exists else None, "existed": exists,
                                 "saved_sha256": catalog.digest(saved) if exists else None})
        save_journal()

    native_roots = [profile["codex"] / name for name in (".tmp", ".sandbox", "skills/.system")]
    native_files_before = set()
    native_directories_before = set()
    need_codex = any(chat["app"] == "codex" for chat in changing_chats)
    native_started = False

    def native_paths():
        files = set(profile["codex_sqlite"].glob("*.sqlite*"))
        directories = {profile["codex_sqlite"]} if profile["codex_sqlite"].is_dir() else set()
        for folder in native_roots:
            if folder.is_dir():
                if catalog.linked(folder):
                    raise ValueError("Reparse point in native Codex state")
                directories.add(folder)
                for parent in folder.parents:
                    if parent == profile["codex"] or parent.is_relative_to(profile["codex"]):
                        directories.add(parent)
                for path in folder.rglob("*"):
                    if catalog.linked(path):
                        raise ValueError("Reparse point in native Codex state")
                    (directories if path.is_dir() else files).add(path)
        return files, directories

    def record_native_changes():
        if not native_started:
            return
        files, directories = native_paths()
        known_destinations = {item["destination"] for item in journal["files"]}
        for path in files - native_files_before:
            if str(path) not in known_destinations:
                journal["files"].append({"destination": str(path), "saved": None, "existed": False})
        for path in sorted(directories - native_directories_before, key=lambda value: len(value.parts)):
            if str(path) not in journal["created_directories"]:
                journal["created_directories"].append(str(path))
        save_journal()

    try:
        for item in changes:
            remember(item["destination"])
        if need_codex:
            native_files_before, native_directories_before = native_paths()
            for path in sorted(native_files_before):
                remember(path)
            bases = {"state_5.sqlite", "logs_2.sqlite", "queue_1.sqlite", "memories_1.sqlite", "goals_1.sqlite"}
            names = {base + suffix for base in bases for suffix in ("", "-wal", "-shm")}
            names.update(path.name for path in profile["codex_sqlite"].glob("*.sqlite*"))
            for name in sorted(names):
                remember(catalog.safe_path(profile["codex_sqlite"], name))
            remember(catalog.safe_path(profile["codex"], "session_index.jsonl"))
            remember(catalog.safe_path(profile["codex"], "installation_id"))
        journal["status"] = "applying"
        save_journal()
        for item in changes:
            if context.cancelled():
                raise RuntimeError("Operation cancelled by user.")
            entry, destination = item["entry"], item["destination"]
            source = catalog.safe_path(root, entry["path"], existing=True)
            if catalog.digest(source) != entry.get("source_sha256", entry["sha256"]):
                raise ValueError("Backup file changed after planning")
            source = Path(entry.get("prepared_source", source))
            missing = [parent for parent in destination.parents if not parent.exists()]
            for directory in reversed(missing):
                if str(directory) not in journal["created_directories"]:
                    journal["created_directories"].append(str(directory))
            save_journal()
            destination.parent.mkdir(parents=True, exist_ok=True)
            staged = destination.with_name(".ai-" + uuid.uuid4().hex[:12] + ".tmp")
            try:
                shutil.copy2(source, staged)
                if catalog.digest(staged) != entry["sha256"]:
                    raise ValueError("Backup changed while copying")
                catalog.safe_path(destination.parent, destination.name)
                staged.replace(destination)
            finally:
                staged.unlink(missing_ok=True)
        if need_codex:
            native_started = True
            ai_native.verify_codex(profile["codex"], profile["codex_sqlite"], context.paths.root,
                                   [chat for chat in changing_chats if chat["app"] == "codex"])
        record_native_changes()
        if context.cancelled():
            raise RuntimeError("Operation cancelled by user.")
        for item in journal["files"]:
            destination = Path(item["destination"])
            item["applied_sha256"] = catalog.digest(destination) if destination.is_file() else None
        journal["status"] = "complete"
        save_journal()
    except BaseException:
        record_native_changes()
        failures = []
        for item in reversed(journal["files"]):
            destination = Path(item["destination"])
            try:
                if item["existed"]:
                    shutil.copy2(restore_root / item["saved"], destination)
                else:
                    destination.unlink(missing_ok=True)
            except OSError:
                failures.append(str(destination))
        for name in reversed(journal["created_directories"]):
            try:
                Path(name).rmdir()
            except OSError:
                continue
        journal.update(status="rollback_incomplete" if failures else "rolled_back", rollback_errors=failures)
        save_journal()
        context.log(f"AI import rollback: {journal['status']}; journal: {journal_path}")
        raise
    return {"dry_run": False, "counts": counts, "journal": str(journal_path),
            "native_verified": [chat["key"] for chat in changing_chats if chat["app"] in {"codex", "grok"}],
            "restored_chats": [chat["key"] for chat in changing_chats], "warnings": data.get("warnings", [])}


def rollback_import(context, params):
    text = str(params.get("journal_path") or "").strip()
    if not text:
        raise ValueError("Select backup/ai_import_.../journal.json / Выберите журнал импорта")
    path = Path(text).absolute()
    backup_root = context.paths.backup.absolute()
    if not path.is_relative_to(backup_root):
        raise ValueError("The journal must be inside this program's backup folder")
    path = catalog.safe_path(backup_root, path.relative_to(backup_root).as_posix(), existing=True)
    journal = catalog.read_json(path)
    if journal.get("schema_version") != 1 or journal.get("operation") != "ai_transfer_import" or not isinstance(journal.get("files"), list):
        raise ValueError("Unsupported import journal")
    profile = catalog.roots()
    allowed = [profile[key].absolute() for key in ("claude", "codex", "codex_sqlite", "grok")] + profile["desktop"]

    def checked_destination(value):
        destination = Path(value).absolute()
        for root in sorted(allowed, key=lambda item: len(item.parts), reverse=True):
            if destination.is_relative_to(root) and destination != root:
                return catalog.safe_path(root, destination.relative_to(root).as_posix())
        raise ValueError("Journal destination is outside the current AI profiles")

    plan = []
    for item in journal["files"]:
        destination = checked_destination(item["destination"])
        if item.get("existed"):
            saved = catalog.safe_path(path.parent, str(item.get("saved") or ""), existing=True)
            if not item.get("saved_sha256") or catalog.digest(saved) != item["saved_sha256"]:
                raise ValueError("Recovery copy integrity check failed")
        else:
            saved = None
        state = "RESTORE" if saved else "REMOVE"
        if "applied_sha256" in item:
            current = catalog.digest(destination) if destination.is_file() else None
            if current != item["applied_sha256"] and not params.get("overwrite_conflicts", False):
                state = "CONFLICT"
        plan.append((destination, saved, state))
    directories = [checked_destination(value) for value in journal.get("created_directories", [])
                   if any(Path(value).absolute().is_relative_to(root) and Path(value).absolute() != root for root in allowed)]
    counts = dict(Counter(state for destination, saved, state in plan))
    if params.get("dry_run", True):
        result = {"dry_run": True, "counts": counts, "journal": str(path), "plan": [{"destination": str(destination), "state": state} for destination, saved, state in plan]}
        result["plan_file"] = plan_report(context, "ai_rollback_plan.json", result)
        return result
    if counts.get("CONFLICT"):
        raise ValueError("Local files changed since import; review conflicts before rolling back")
    processes_stopped({"claude", "claude_desktop", "codex", "grok"})
    for destination, saved, state in reversed(plan):
        checked_destination(str(destination))
        if saved:
            destination.parent.mkdir(parents=True, exist_ok=True)
            temporary = destination.with_name(".ai-rollback-" + uuid.uuid4().hex[:10])
            try:
                shutil.copy2(saved, temporary)
                temporary.replace(destination)
            finally:
                temporary.unlink(missing_ok=True)
        else:
            destination.unlink(missing_ok=True)
    for directory in sorted(directories, key=lambda item: len(item.parts), reverse=True):
        try:
            directory.rmdir()
        except OSError:
            continue
    journal["status"] = "rolled_back"
    path.write_text(json.dumps(journal, ensure_ascii=False, indent=2), encoding="utf-8")
    return {"dry_run": False, "counts": counts, "journal": str(path), "status": "rolled_back"}


def run(context):
    params = dict(context.operation.parameters)
    mode = params.get("mode", "export")
    if mode == "inventory":
        data = catalog.scan()
        for source in data["sources"]:
            context.log(f"{catalog.APPS[source['app']]}: {source['state']}; chats={source['chats']}; archived={source['archived']}; profile={source['root']}")
        for category in data["categories"]:
            if category["count"]:
                context.log(f"{category['key']}: files={category['count']}; bytes={category['size']}")
        return {key: value for key, value in data.items() if key not in {"files", "roots"}}
    if mode == "export":
        return export_backup(context, params)
    if mode == "import":
        return import_backup(context, params)
    if mode == "rollback":
        params["dry_run"] = params.get("rollback_dry_run", params.get("dry_run", True))
        params["overwrite_conflicts"] = params.get("rollback_overwrite", params.get("overwrite_conflicts", False))
        return rollback_import(context, params)
    raise ValueError(f"Unsupported AI transfer mode: {mode}")
