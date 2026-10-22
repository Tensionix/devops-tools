from __future__ import annotations

import hashlib
import io
import json
import os
import re
import shutil
import sqlite3
import stat
import tempfile
import time
import tomllib
from contextlib import closing, contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterator
from urllib.parse import unquote


UUID = re.compile(r"[0-9a-fA-F]{8}(?:-[0-9a-fA-F]{4}){3}-[0-9a-fA-F]{12}")
APPS = {"claude": "Claude Code", "claude_desktop": "Claude Desktop", "codex": "Codex", "grok": "Grok CLI", "chatgpt": "ChatGPT Desktop"}
CATEGORIES = {
    "memory": ("Memory", "Память"), "settings": ("Settings", "Настройки"),
    "instructions": ("Instructions and rules", "Инструкции и правила"),
    "skills": ("Skills", "Навыки"), "plugins": ("Plugins", "Плагины"),
    "automations": ("Automation", "Автоматизации"), "extras": ("Additional profile data", "Дополнительные данные профиля"),
    "cache": ("Non-conversation cache", "Кэш без переписок"),
}
# The plugins of Codex stay out of Essential: Codex installs them itself, hundreds of megabytes a transfer does not need.
ESSENTIAL = [f"{app}:{category}" for app in ("claude", "codex", "grok") for category in CATEGORIES
             if category not in {"extras", "cache"} and f"{app}:{category}" != "codex:plugins"]
ALL_CATEGORIES = [f"{app}:{category}" for app in ("claude", "codex", "grok") for category in CATEGORIES]
PROFILE_ITEMS = {
    "claude": {"memory": ["projects/*/memory"], "settings": ["settings.json", "settings.local.json"],
               "instructions": ["CLAUDE.md", "rules", "agents"], "skills": ["skills"], "plugins": ["plugins"],
               "automations": [], "extras": ["commands"], "cache": []},
    "codex": {"memory": ["memories"], "settings": ["config.toml"], "instructions": ["AGENTS.md", "rules"],
              "skills": ["skills"], "plugins": ["plugins"], "automations": ["automations"], "extras": ["prompts"], "cache": ["models_cache.json"]},
    "grok": {"memory": ["memory", "memory-v2"], "settings": ["config.toml"], "instructions": ["GROK.md", "rules", "agents"],
             "skills": ["skills"], "plugins": ["installed-plugins"], "automations": ["workflows"], "extras": ["commands"], "cache": []},
}


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def digest(path: Path) -> str:
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def canonical(value: Any) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")


def read_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(value, dict):
        raise ValueError(f"Expected a JSON object: {path.name}")
    return value


def linked(path: Path) -> bool:
    info = path.lstat()
    return path.is_symlink() or bool(getattr(info, "st_file_attributes", 0) & stat.FILE_ATTRIBUTE_REPARSE_POINT)


def safe_path(root: Path, relative: str, *, existing: bool = False) -> Path:
    parts = relative.replace("\\", "/").split("/")
    if not parts or any(not part or part in (".", "..") or ":" in part or part.endswith((".", " ")) for part in parts):
        raise ValueError(f"Unsafe relative path: {relative}")
    if any(re.fullmatch(r"(?i)(con|prn|aux|nul|com[1-9]|lpt[1-9])(?:\..*)?", part) for part in parts):
        raise ValueError(f"Reserved path: {relative}")
    current = root.absolute()
    for ancestor in [current, *current.parents]:
        if ancestor.exists() and linked(ancestor):
            raise ValueError(f"Reparse point: {ancestor}")
    for part in parts:
        current = current / part
        if current.exists() and linked(current):
            raise ValueError(f"Reparse point: {current}")
    if existing and not current.is_file():
        raise ValueError(f"Missing file: {relative}")
    return current


def walk_files(root: Path, warnings: list[str]) -> Iterator[Path]:
    if not root.exists():
        return
    if linked(root):
        warnings.append(f"Reparse point skipped: {root}")
        return
    if root.is_file():
        yield root
        return
    def on_error(error: OSError) -> None:
        warnings.append(f"{type(error).__name__}: {error.filename}")
    for folder, directories, filenames in os.walk(root, followlinks=False, onerror=on_error):
        base = Path(folder)
        remaining = []
        for name in directories:
            if linked(base / name):
                warnings.append(f"Reparse point skipped: {base / name}")
            elif name not in {".git", "node_modules", "__pycache__"}:
                remaining.append(name)
        directories[:] = remaining
        for name in filenames:
            path = base / name
            try:
                if linked(path) or path.suffix.lower() in {".lock", ".sock"} or name.endswith(("-wal", "-shm", "-journal")):
                    continue
                yield path
            except OSError as error:
                on_error(error)


def roots() -> dict[str, Any]:
    user = Path(os.environ.get("USERPROFILE") or Path.home())
    local = Path(os.environ.get("LOCALAPPDATA") or user / "AppData/Local")
    roaming = Path(os.environ.get("APPDATA") or user / "AppData/Roaming")
    codex = Path(os.path.expandvars(os.environ.get("CODEX_HOME") or str(user / ".codex"))).expanduser().absolute()
    sqlite_home = os.environ.get("CODEX_SQLITE_HOME") or str(codex)
    try:
        sqlite_home = tomllib.loads((codex / "config.toml").read_text(encoding="utf-8-sig")).get("sqlite_home") or sqlite_home
    except (OSError, ValueError):
        pass
    packages = local / "Packages"
    claude_packages = sorted(packages.glob("Claude_*")) if packages.is_dir() else []
    desktop = [roaming / "Claude/claude-code-sessions"]
    desktop.extend(package / "LocalCache/Roaming/Claude/claude-code-sessions" for package in claude_packages)
    desktop.extend(package / "LocalState/Claude/claude-code-sessions" for package in claude_packages)
    chatgpt = [roaming / "ChatGPT", local / "OpenAI/ChatGPT"]
    chatgpt.extend(sorted(packages.glob("OpenAI.ChatGPT_*")) if packages.is_dir() else [])
    chatgpt.extend(sorted(packages.glob("OpenAI.Codex_*")) if packages.is_dir() else [])
    return {"claude": Path(os.path.expandvars(os.environ.get("CLAUDE_CONFIG_DIR") or str(user / ".claude"))).expanduser().absolute(),
            "codex": codex, "codex_sqlite": Path(os.path.expandvars(str(sqlite_home))).expanduser().absolute(),
            "grok": Path(os.path.expandvars(os.environ.get("GROK_HOME") or str(user / ".grok"))).expanduser().absolute(),
            "desktop": list(dict.fromkeys(desktop)), "chatgpt": chatgpt,
            "claude_installed": bool(shutil.which("claude-desktop.exe") or any((local / "Microsoft/WindowsApps" / name).exists() for name in ["claude-desktop.exe"]))}


@contextmanager
def transcript(path: Path):
    if path.name.endswith(".zst"):
        import zstandard
        with path.open("rb") as raw:
            with zstandard.ZstdDecompressor().stream_reader(raw) as reader:
                with io.TextIOWrapper(reader, encoding="utf-8-sig") as text:
                    yield text
    else:
        with path.open(encoding="utf-8-sig") as text:
            yield text


def stamp(value: Any, fallback: float = 0) -> float:
    try:
        if isinstance(value, (int, float)):
            return float(value) / 1000 if value > 100000000000 else float(value)
        return datetime.fromisoformat(str(value).replace("Z", "+00:00")).timestamp()
    except (ValueError, TypeError, OverflowError):
        return fallback


def message_text(value: Any) -> str:
    if isinstance(value, str):
        return " ".join(value.split())[:140]
    if isinstance(value, list):
        return message_text(" ".join(str(item.get("text", "")) for item in value if isinstance(item, dict)))
    return ""


def session_metadata(path: Path, app: str) -> dict[str, Any]:
    info: dict[str, Any] = {}
    recognized = False
    with transcript(path) as stream:
        for number, line in enumerate(stream):
            if number >= 256:
                break
            try:
                row = json.loads(line)
            except ValueError:
                continue
            if not isinstance(row, dict):
                continue
            kind = row.get("type")
            if app == "codex" and kind == "session_meta":
                payload = row.get("payload") or {}
                def parent_of(value):
                    if not isinstance(value, dict):
                        return None
                    for key, member in value.items():
                        if key in {"parent_thread_id", "parentThreadId"} and isinstance(member, str):
                            return member
                        if isinstance(member, dict) and (found := parent_of(member)):
                            return found
                    return None
                info.update({"id": payload.get("id"), "cwd": payload.get("cwd", ""), "created": stamp(payload.get("timestamp")),
                             "source": payload.get("source", "cli"), "parent": parent_of(payload) or payload.get("forked_from_id")})
                recognized = True
            elif app == "claude" and kind in {"user", "assistant", "summary", "custom-title", "system"}:
                recognized = True
                info.setdefault("id", row.get("sessionId"))
                info.setdefault("cwd", row.get("cwd", ""))
                info.setdefault("created", stamp(row.get("timestamp")))
                if row.get("customTitle"):
                    info["title"] = message_text(row["customTitle"])
                if row.get("isSidechain"):
                    info["subagent"] = True
            if not info.get("title"):
                if kind == "user":
                    info["title"] = message_text((row.get("message") or {}).get("content"))
                elif kind == "event_msg" and (row.get("payload") or {}).get("type") == "user_message":
                    info["title"] = message_text(row["payload"].get("message"))
                elif kind == "response_item" and (row.get("payload") or {}).get("role") == "user":
                    info["title"] = message_text(row["payload"].get("content"))
            if app == "codex" and info.get("id") and info.get("title"):
                break
    info["recognized"] = recognized
    return info


def codex_index(profile: dict[str, Any], warnings: list[str]) -> dict[str, dict[str, Any]]:
    entries: dict[str, dict[str, Any]] = {}
    for database in sorted(profile["codex_sqlite"].glob("state_*.sqlite"), reverse=True):
        try:
            if linked(database):
                continue
            with readonly_database(database) as connection:
                connection.row_factory = sqlite3.Row
                columns = {row[1] for row in connection.execute("PRAGMA table_info(threads)")}
                wanted = [name for name in ("id", "title", "name", "cwd", "archived", "source", "created_at", "updated_at") if name in columns]
                if "id" not in wanted:
                    warnings.append(f"Unsupported Codex index: {database.name}")
                    continue
                for row in connection.execute("SELECT " + ",".join(wanted) + " FROM threads"):
                    entries.setdefault(row["id"], dict(row))
        except (OSError, sqlite3.Error):
            warnings.append(f"Cannot read Codex index: {database.name}")
    return entries


@contextmanager
def readonly_database(database: Path):
    with tempfile.TemporaryDirectory(prefix="audion-ai-sqlite-") as temporary:
        target = Path(temporary) / "snapshot.sqlite"
        for attempt in range(3):
            sources = [database, database.with_name(database.name + "-wal")]
            before = [(source.stat().st_size, source.stat().st_mtime_ns) if source.exists() else None for source in sources]
            for source, metadata in zip(sources, before):
                destination = target if source == database else target.with_name(target.name + "-wal")
                if metadata is None:
                    destination.unlink(missing_ok=True)
                else:
                    if linked(source):
                        raise ValueError("Reparse point in SQLite state")
                    shutil.copy2(source, destination)
            after = [(source.stat().st_size, source.stat().st_mtime_ns) if source.exists() else None for source in sources]
            if before == after:
                break
        else:
            raise OSError("SQLite changed while taking a read-only snapshot")
        with closing(sqlite3.connect(target, timeout=2)) as connection:
            yield connection


def file_record(path: Path, root: Path, prefix: str, app: str, category: str, chat: str = "") -> dict[str, Any]:
    relative = path.relative_to(root).as_posix()
    safe_path(root, relative, existing=True)
    metadata = path.stat()
    return {"path": prefix + "/" + relative, "root": prefix, "relative": relative, "app": app, "category": category,
            "chat": chat, "size": metadata.st_size, "mtime_ns": metadata.st_mtime_ns, "source": str(path)}


def scan() -> dict[str, Any]:
    profile = roots()
    warnings: list[str] = []
    files: dict[str, dict[str, Any]] = {}
    chats: dict[str, dict[str, Any]] = {}
    source_warnings: dict[str, list[str]] = {app: [] for app in APPS}
    codex_children = []

    def add(path: Path, root: Path, prefix: str, app: str, category: str, key: str = "") -> str:
        entry = file_record(path, root, prefix, app, category, key)
        previous = files.get(entry["path"])
        if previous and previous["source"] != entry["source"]:
            if digest(Path(previous["source"])) != digest(path):
                raise ValueError(f"Conflicting profile files: {entry['path']}")
        files[entry["path"]] = entry
        return entry["path"]

    for app in ("claude", "codex", "grok"):
        root = profile[app]
        problems = source_warnings[app]
        try:
            if app == "claude":
                candidates = sorted((root / "projects").glob("*/*.jsonl"))
            elif app == "codex":
                candidates = [path for folder in ("sessions", "archived_sessions") for path in walk_files(root / folder, problems)
                              if path.name.endswith((".jsonl", ".jsonl.zst"))]
            else:
                candidates = sorted((root / "sessions").glob("*/*/summary.json"))
            index = codex_index(profile, problems) if app == "codex" else {}
            for path in candidates:
                try:
                    if linked(path):
                        raise ValueError("Reparse point")
                    if app == "grok":
                        data = read_json(path)
                        detail = data.get("info") or {}
                        info = {"id": detail.get("id") or path.parent.name, "cwd": detail.get("cwd") or unquote(path.parent.parent.name),
                                "title": message_text(data.get("session_summary") or data.get("title")),
                                "created": stamp(data.get("created_at")), "recognized": data.get("chat_format_version") in (1, 2)}
                        if not info["title"] and (path.parent / "chat_history.jsonl").is_file():
                            with (path.parent / "chat_history.jsonl").open(encoding="utf-8") as history:
                                for number, line in enumerate(history):
                                    if number > 64:
                                        break
                                    row = json.loads(line)
                                    if row.get("role") == "user" or row.get("type") == "user":
                                        info["title"] = message_text(row.get("content"))
                                        break
                    else:
                        info = session_metadata(path, app)
                    found = UUID.search(path.name if app != "grok" else path.parent.name)
                    identity = str(info.get("id") or (found.group(0) if found else ""))
                    if not UUID.fullmatch(identity):
                        raise ValueError("Unknown session identity")
                    saved = index.get(identity, {})
                    source_kind = info.get("source") or saved.get("source")
                    if info.get("subagent") or (app == "codex" and (isinstance(source_kind, dict) or str(source_kind).lower().startswith("subagent"))):
                        if app == "codex" and info.get("parent"):
                            codex_children.append((path, identity, info["parent"]))
                        continue
                    key = f"{app}:{identity}"
                    archived = "archived_sessions" in path.relative_to(root).parts
                    title = message_text(saved.get("name") or saved.get("title") or info.get("title"))
                    chat = {"key": key, "app": app, "id": identity, "title": title, "cwd": str(info.get("cwd") or saved.get("cwd") or ""),
                            "created": stamp(saved.get("created_at"), float(info.get("created") or path.stat().st_mtime)),
                            "updated": stamp(saved.get("updated_at"), path.stat().st_mtime), "archived": archived,
                            "files": [], "sources": [app], "complete": bool(info.get("recognized")),
                            "restore": "native" if info.get("recognized") else "unsupported", "warnings": []}
                    if not info.get("recognized"):
                        chat["warnings"].append("Unrecognized session format; archive only")
                    if app == "grok":
                        pieces = list(walk_files(path.parent, problems))
                        if not all(any(piece.name == name for piece in pieces) for name in ("updates.jsonl", "chat_history.jsonl")):
                            chat["complete"] = False
                            chat["restore"] = "unsupported"
                            chat["warnings"].append("Grok replay stream or conversation history is missing; archive only")
                    else:
                        pieces = [path]
                        if app == "claude":
                            pieces.extend(walk_files(path.with_suffix(""), problems))
                    chat["files"] = [add(piece, root, app, app, "chat", key) for piece in pieces]
                    previous = chats.get(key)
                    if previous:
                        previous["files"].extend(name for name in chat["files"] if name not in previous["files"])
                        previous["archived"] = previous["archived"] and archived
                        previous["warnings"].append("Multiple files share this session identity")
                        main_files = [name for name in previous["files"] if name.endswith((".jsonl", ".jsonl.zst")) and
                                      (app == "codex" or len(name.split("/")) == 4)]
                        if {digest(Path(files[name]["source"])) for name in main_files} != {digest(path)}:
                            previous.update(complete=False, restore="unsupported")
                    else:
                        chats[key] = chat
                except (OSError, ValueError, RuntimeError) as error:
                    problems.append(f"{type(error).__name__}: {path}")
            for category, patterns in PROFILE_ITEMS[app].items():
                for pattern in patterns:
                    for item in root.glob(pattern):
                        for path in walk_files(item, problems):
                            add(path, root, app, app, category)
            auth = root / (".credentials.json" if app == "claude" else "auth.json")
            if auth.is_file():
                add(auth, root, app, app, "auth")
            if app == "codex":
                for name in ("memories_1.sqlite", "goals_1.sqlite"):
                    path = profile["codex_sqlite"] / name
                    if path.is_file():
                        add(path, profile["codex_sqlite"], "codex_sqlite", app, "memory")
        except (OSError, ValueError) as error:
            problems.append(f"{type(error).__name__}: {root}")

    for unused in range(len(codex_children) + 1):
        progress = False
        for path, identity, parent in list(codex_children):
            chat = chats.get(f"codex:{parent}") or next((item for item in chats.values() if parent in item.get("dependencies", [])), None)
            if chat:
                chat.setdefault("dependencies", []).append(identity)
                chat["files"].append(add(path, profile["codex"], "codex", "codex", "chat", chat["key"]))
                codex_children.remove((path, identity, parent))
                progress = True
        if not progress:
            break
    if codex_children:
        source_warnings["codex"].append(f"Orphan subagent sessions excluded: {len(codex_children)}")

    for desktop_root in profile["desktop"]:
        problems = source_warnings["claude_desktop"]
        for path in walk_files(desktop_root, problems):
            if not path.name.startswith("local_") or path.suffix != ".json":
                continue
            try:
                data = read_json(path)
                identity = str(data.get("cliSessionId") or "")
                key = f"claude:{identity}" if UUID.fullmatch(identity) else f"claude_desktop:{path.stem}"
                chat = chats.setdefault(key, {"key": key, "app": "claude_desktop", "id": identity or path.stem,
                    "title": "", "cwd": str(data.get("cwd") or ""), "created": stamp(data.get("createdAt")),
                    "updated": stamp(data.get("lastActivityAt"), path.stat().st_mtime), "archived": bool(data.get("isArchived")),
                    "sources": [], "files": [], "complete": False, "restore": "unsupported", "warnings": ["Desktop transcript is unavailable"]})
                if "claude_desktop" not in chat["sources"]:
                    chat["sources"].append("claude_desktop")
                if data.get("title"):
                    chat["title"] = message_text(data["title"])
                if "isArchived" in data:
                    chat["archived"] = bool(data["isArchived"])
                chat["updated"] = max(chat["updated"], stamp(data.get("lastActivityAt")))
                name = add(path, desktop_root, "claude_app/claude-code-sessions", "claude_desktop", "chat", key)
                if name not in chat["files"]:
                    chat["files"].append(name)
            except (OSError, ValueError):
                problems.append(f"Unreadable Desktop entry: {path}")

    categories = []
    for app in ("claude", "codex", "grok"):
        for category in CATEGORIES:
            entries = [entry for entry in files.values() if entry["app"] == app and entry["category"] == category]
            categories.append({"key": f"{app}:{category}", "app": app, "category": category,
                               "count": len(entries), "size": sum(entry["size"] for entry in entries)})
    sources = []
    for app in APPS:
        problems = source_warnings[app]
        if app == "claude_desktop":
            found_roots = [path for path in profile["desktop"] if path.exists()]
            exists = bool(found_roots or profile["claude_installed"])
            location = " | ".join(str(path) for path in found_roots or profile["desktop"][:1])
        elif app == "chatgpt":
            found_roots = [path for path in profile["chatgpt"] if path.exists()]
            exists = bool(found_roots or shutil.which("ChatGPT.exe"))
            location = " | ".join(str(path) for path in found_roots or profile["chatgpt"][:1])
        else:
            exists = profile[app].exists()
            location = str(profile[app])
        relevant = [chat for chat in chats.values() if app in chat["sources"]]
        entries = [entry for entry in files.values() if entry["app"] == app]
        state = "partial" if problems else "found" if exists else "missing"
        note = ""
        if app in {"chatgpt", "claude_desktop"} and exists and not relevant:
            state = "unsupported"
            note = "Local profile detected; cloud chat history has no supported local import format"
        sources.append({"app": app, "state": state, "root": location, "chats": len(relevant),
                        "archived": sum(chat["archived"] for chat in relevant), "size": sum(entry["size"] for entry in entries),
                        "warnings": problems, "note": note})
        warnings.extend(problems)
    for chat in chats.values():
        chat["size"] = sum(files[name]["size"] for name in chat["files"])
    return {"scanned_utc": utc_now(), "sources": sources, "chats": sorted(chats.values(), key=lambda chat: chat["updated"], reverse=True),
            "categories": categories, "files": list(files.values()), "warnings": warnings,
            "roots": {key: str(profile[key]) for key in ("claude", "codex", "codex_sqlite", "grok")}}


def scan_options(root=None, values=None):
    project = Path(root or Path(__file__).resolve().parents[2])
    directory = safe_path(project, "._runtime/ai_catalog")
    directory.mkdir(parents=True, exist_ok=True)
    identity = hashlib.sha256(canonical({key: os.environ.get(key, "") for key in
        ("USERPROFILE", "CLAUDE_CONFIG_DIR", "CODEX_HOME", "CODEX_SQLITE_HOME", "GROK_HOME", "APPDATA", "LOCALAPPDATA")})).hexdigest()[:24]
    target = safe_path(directory, identity + ".json")
    lock = safe_path(directory, identity + ".lock")
    started = time.monotonic()
    while True:
        try:
            handle = os.open(lock, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
            os.close(handle)
            break
        except FileExistsError:
            if lock.stat().st_mtime < time.time() - 90:
                lock.unlink(missing_ok=True)
            elif time.monotonic() - started > 45:
                raise RuntimeError("AI inventory is busy; try refreshing again")
            else:
                time.sleep(0.05)
    try:
        if not (values or {}).get("_refresh_options") and target.is_file() and time.time() - target.stat().st_mtime < 20:
            try:
                return read_json(target)
            except (OSError, ValueError):
                pass
        data = scan()
        temporary = safe_path(directory, target.name + ".tmp")
        temporary.write_bytes(canonical(data))
        temporary.replace(target)
        return data
    finally:
        lock.unlink(missing_ok=True)


def option(value: str, label: str, label_ru: str, **extra: Any) -> dict[str, Any]:
    return {"value": value, "label": label, "label_ru": label_ru, **extra}


def inventory_options(root=None, values=None):
    catalog = scan_options(root, values)
    states = {"found": ("found", "найдено"), "missing": ("not found", "не найдено"),
              "partial": ("partially available", "частично доступно"), "unsupported": ("local profile; format unsupported", "профиль найден; формат не поддержан")}
    answer = []
    for source in catalog["sources"]:
        english, russian = states[source["state"]]
        label = APPS[source["app"]]
        tip = source["root"] + "\n" + catalog["scanned_utc"]
        if source["note"]:
            tip += "\n" + source["note"]
        tip += "\n" + "\n".join(source["warnings"][:5])
        tip_ru = tip.replace("Local profile detected; cloud chat history has no supported local import format",
                             "Приложение или профиль найдены. Поддерживаемого локального формата переноса облачных чатов нет.")
        answer.append(option(source["app"], f"{label}: {english} · {source['chats']} chats · {source['size']/1048576:.1f} MB",
            f"{label}: {russian} · чатов {source['chats']} · {source['size']/1048576:.1f} МБ", hint=tip, hint_ru=tip,
            tone="warn" if source["state"] in {"partial", "unsupported"} else "plain"))
        answer[-1]["hint_ru"] = tip_ru
    return answer


def chat_options(catalog: dict[str, Any], values: dict[str, Any]) -> list[dict[str, Any]]:
    answer = []
    for chat in catalog["chats"]:
        if values.get("chat_provider", "all") not in ("all", chat["app"]) and values.get("chat_provider") not in chat["sources"]:
            continue
        if values.get("chat_project", "all") not in ("all", chat["cwd"]):
            continue
        if values.get("chat_archive") == "active" and chat["archived"] or values.get("chat_archive") == "archived" and not chat["archived"]:
            continue
        when = datetime.fromtimestamp(chat["updated"]).strftime("%d.%m.%Y") if chat.get("updated") else ""
        title = chat["title"] or f"Untitled · {chat['id'][:8]}"
        title_ru = chat["title"] or f"Без названия · {chat['id'][:8]}"
        label = f"{APPS[chat['app']]} · {title} · {when} · {chat['size']/1048576:.1f} MB"
        label_ru = f"{APPS[chat['app']]} · {title_ru} · {when} · {chat['size']/1048576:.1f} МБ"
        if chat["cwd"]:
            project = Path(chat["cwd"]).name or chat["cwd"]
            label += " · " + project
            label_ru += " · " + project
        if chat["archived"]:
            label += " · archived"
            label_ru += " · архив"
        if not chat["complete"]:
            label += " · incomplete"
            label_ru += " · неполный"
        hint = "\n".join([chat["cwd"], chat["key"], *chat["files"], *chat.get("warnings", [])])
        answer.append(option(chat["key"], label, label_ru, hint=hint, hint_ru=hint, group=chat["cwd"], default=False))
    return answer or [option("", "No matching local chats. Refresh or change filters.", "Локальные чаты не найдены. Обновите список или измените фильтры.")]


def live_chat_options(root=None, values=None):
    return chat_options(scan_options(root, values), values or {})


def category_options(root=None, values=None):
    return categories_as_options(scan_options(root, values))


def categories_as_options(catalog):
    return [option(item["key"], f"{APPS[item['app']]} · {CATEGORIES[item['category']][0]} · {item['count']} files · {item['size']/1048576:.1f} MB",
        f"{APPS[item['app']]} · {CATEGORIES[item['category']][1]} · файлов {item['count']} · {item['size']/1048576:.1f} МБ",
        hint="No data" if not item["count"] else "", hint_ru="Данные не найдены" if not item["count"] else "") for item in catalog["categories"]]


def project_options(root=None, values=None):
    return [option("all", "All projects", "Все проекты")] + [option(name, name or "No project", name or "Без проекта")
        for name in sorted({chat["cwd"] for chat in scan_options(root, values)["chats"]})]
