"""The SMB logins the program remembers: pairs "computer - user", never a password.

Carried over from the window on NiceGUI (`smb_*` of `ui_nicegui/app.py`) unchanged, so that the
console command and a window on Avalonia read and write the same file the former window did:
config/smb_network_logins.json, at most a hundred pairs, the newest first. The password is typed
into the external `net use` console and is seen neither here nor in any log.

The value of the field `smb_login` is a dict:
    record_key       the pair picked from the cache ("" - none)
    computer, user   the pair the field shows
    computer_manual, user_manual   what was typed over it
    cleared          "true" once the cache was cleared: the default of the manifest is not taken
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

PAIR_SEPARATOR = "\t"
LIMIT = 100
FILE_NAME = "smb_network_logins.json"

# The file the pairs are kept in; a test or a record points it elsewhere.
cache_path: Path | None = None


def _path(config: Path | None = None) -> Path:
    if cache_path is not None:
        return cache_path
    if config is None:
        config = Path(__file__).resolve().parents[2] / "config"
    return config / FILE_NAME


def clean_computer(value: Any) -> str:
    return str(value or "").strip().strip("\\/")


def clean_user(value: Any) -> str:
    return str(value or "").strip()


def record_key(computer: Any, user: Any) -> str:
    return f"{clean_computer(computer)}{PAIR_SEPARATOR}{clean_user(user)}"


def _identity(record: dict[str, str]) -> str:
    return clean_computer(record.get("computer", "")).casefold() + PAIR_SEPARATOR + clean_user(record.get("user", "")).casefold()


def record_from_key(key: Any) -> dict[str, str] | None:
    text = str(key or "")
    if PAIR_SEPARATOR not in text:
        return None
    computer, user = text.split(PAIR_SEPARATOR, 1)
    computer = clean_computer(computer)
    user = clean_user(user)
    if not computer or not user:
        return None
    return {"computer": computer, "user": user}


def load_records(config: Path | None = None) -> list[dict[str, str]]:
    path = _path(config)
    if not path.exists():
        return []
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return []
    records_raw = raw.get("records", raw) if isinstance(raw, dict) else raw
    if not isinstance(records_raw, list):
        return []
    records: list[dict[str, str]] = []
    seen: set[str] = set()
    for item in records_raw:
        if not isinstance(item, dict):
            continue
        record = {"computer": clean_computer(item.get("computer")), "user": clean_user(item.get("user"))}
        if not record["computer"] or not record["user"]:
            continue
        identity = _identity(record)
        if identity in seen:
            continue
        seen.add(identity)
        records.append(record)
        if len(records) >= LIMIT:
            break
    return records


def save_records(records: list[dict[str, str]], config: Path | None = None) -> None:
    path = _path(config)
    clean: list[dict[str, str]] = []
    seen: set[str] = set()
    for item in records:
        record = {"computer": clean_computer(item.get("computer")), "user": clean_user(item.get("user"))}
        if not record["computer"] or not record["user"]:
            continue
        identity = _identity(record)
        if identity in seen:
            continue
        seen.add(identity)
        clean.append(record)
        if len(clean) >= LIMIT:
            break
    if not clean:
        try:
            path.unlink()
        except FileNotFoundError:
            pass
        except OSError:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(json.dumps({"records": []}, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({"records": clean}, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def upsert(computer: Any, user: Any, config: Path | None = None) -> str:
    record = {"computer": clean_computer(computer), "user": clean_user(user)}
    if not record["computer"] or not record["user"]:
        return ""
    identity = _identity(record)
    records = [item for item in load_records(config) if _identity(item) != identity]
    save_records([record, *records], config)
    return record_key(record["computer"], record["user"])


def delete(key: Any, config: Path | None = None) -> bool:
    record = record_from_key(key)
    if not record:
        return False
    identity = _identity(record)
    current = load_records(config)
    records = [item for item in current if _identity(item) != identity]
    if len(records) == len(current):
        return False
    save_records(records, config)
    return True


def clear(config: Path | None = None) -> None:
    save_records([], config)


def default_login(field_default: Any) -> dict[str, str]:
    if isinstance(field_default, dict):
        return {"computer": clean_computer(field_default.get("computer")), "user": clean_user(field_default.get("user"))}
    return {"computer": "", "user": ""}


def login_state(raw: Any, field_default: Any, config: Path | None = None) -> dict[str, str]:
    """The value of the field as the former window read it (`smb_login_state`)."""
    default = default_login(field_default)
    value = raw if isinstance(raw, dict) else {}
    records = load_records(config)
    selected_key = str(value.get("record_key") or "")
    selected = next((record for record in records if record_key(record["computer"], record["user"]) == selected_key), None)
    computer_manual = clean_computer(value.get("computer_manual"))
    user_manual = clean_user(value.get("user_manual"))
    use_default = str(value.get("cleared") or "").lower() != "true"
    computer = clean_computer(value.get("computer")) or (selected["computer"] if selected else "") or (default["computer"] if use_default else "")
    user = clean_user(value.get("user")) or (selected["user"] if selected else "") or (default["user"] if use_default else "")
    if selected is None and selected_key:
        selected_key = ""
    return {
        "record_key": selected_key,
        "computer": computer,
        "user": user,
        "computer_manual": computer_manual,
        "user_manual": user_manual,
        "cleared": "true" if not use_default else "",
    }


def effective_login(value: dict[str, str]) -> tuple[str, str]:
    computer = clean_computer(value.get("computer_manual")) or clean_computer(value.get("computer"))
    user = clean_user(value.get("user_manual")) or clean_user(value.get("user"))
    return computer, user


def run_parameters(raw: Any, field_default: Any, config: Path | None = None, remember: bool = True) -> dict[str, Any]:
    """What the former window put into the parameters at the start of a run, and the pair it remembered then.

    `remember` False - a question before the run: the pair is not written down yet.
    """
    login = login_state(raw, field_default, config)
    computer, user = effective_login(login)
    if computer and user:
        login["record_key"] = upsert(computer, user, config) if remember else record_key(computer, user)
        login["computer"] = computer
        login["user"] = user
        login["computer_manual"] = ""
        login["user_manual"] = ""
        login["cleared"] = ""
    return {"login": login, "smb_computer": computer, "smb_user": user}


def records_options(root: Path) -> list[dict[str, Any]]:
    """The remembered pairs as options of a list, the newest first."""
    rows = []
    for record in load_records(Path(root) / "config"):
        key = record_key(record["computer"], record["user"])
        rows.append({"value": key, "label": f"{record['computer']} | {record['user']}",
                     "computer": record["computer"], "user": record["user"]})
    return rows
