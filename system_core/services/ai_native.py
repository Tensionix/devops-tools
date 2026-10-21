from __future__ import annotations

import json
import os
import queue
import shutil
import subprocess
import threading
import time
from pathlib import Path
from typing import Any

from system_core.core.jobs import hidden_subprocess_kwargs


CODEX_VERSIONS = {"0.163.0"}
GROK_VERSIONS = {"1.0.62"}


def executable(name: str) -> str:
    found = shutil.which(name)
    if not found:
        raise RuntimeError(f"{name} is required to verify restored sessions")
    return found


def native_version(name: str) -> str:
    result = subprocess.run([executable(name), "--version"], capture_output=True, timeout=10, **hidden_subprocess_kwargs())
    if result.returncode:
        raise RuntimeError(f"Cannot determine {name} version")
    parts = result.stdout.decode("utf-8", errors="replace").strip().split()
    if len(parts) < 2:
        raise RuntimeError(f"Unknown {name} version")
    return parts[1]


def require_version(app: str) -> str:
    version = native_version(app)
    supported = CODEX_VERSIONS if app == "codex" else GROK_VERSIONS
    if version not in supported:
        raise RuntimeError(f"{app} {version}: restoration adapter is not verified for this version")
    return version


class CodexClient:
    def __init__(self, home: Path, sqlite_home: Path, cwd: Path):
        self.home, self.sqlite_home, self.cwd = home, sqlite_home, cwd
        self.process = None
        self.lines: queue.Queue = queue.Queue()
        self.serial = 0

    def __enter__(self):
        env = os.environ.copy()
        env.update(CODEX_HOME=str(self.home), CODEX_SQLITE_HOME=str(self.sqlite_home))
        command = [executable("codex"), "app-server", "--stdio", "-c", "sqlite_home=" + json.dumps(str(self.sqlite_home)),
                   "-c", "analytics.enabled=false", "-c", "otel.exporter=\"none\""]
        self.process = subprocess.Popen(command, cwd=self.cwd, env=env, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                                        stderr=subprocess.DEVNULL, **hidden_subprocess_kwargs())
        def read_lines():
            for line in self.process.stdout:
                try:
                    self.lines.put(json.loads(line))
                except ValueError:
                    continue
            self.lines.put(None)
        self.reader = threading.Thread(target=read_lines, daemon=True)
        self.reader.start()
        try:
            self.request("initialize", {"clientInfo": {"name": "audion_devops_tools", "title": "Audion DevOps Tools", "version": "2.1.0"},
                                        "capabilities": {"experimentalApi": True}})
            self.write({"method": "initialized"})
        except BaseException:
            self.__exit__(None, None, None)
            raise
        return self

    def write(self, value):
        self.process.stdin.write((json.dumps(value) + "\n").encode("utf-8"))
        self.process.stdin.flush()

    def request(self, method: str, params: dict, timeout: float = 30) -> dict[str, Any]:
        self.serial += 1
        identity = self.serial
        self.write({"id": identity, "method": method, "params": params})
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            try:
                reply = self.lines.get(timeout=max(0.01, deadline - time.monotonic()))
            except queue.Empty:
                break
            if reply is None:
                raise RuntimeError(f"Codex app-server exited during {method}")
            if reply.get("id") != identity:
                continue
            if "error" in reply:
                raise RuntimeError(f"Codex app-server rejected {method}: {reply['error'].get('code', 'unknown')}")
            return reply.get("result") or {}
        raise RuntimeError(f"Codex app-server timeout: {method}")

    def list_threads(self, archived: bool = False):
        cursor = None
        answer = []
        for page in range(1000):
            result = self.request("thread/list", {"limit": 100, "cursor": cursor, "archived": archived,
                "sourceKinds": ["cli", "vscode", "exec", "appServer", "unknown"], "useStateDbOnly": False})
            answer.extend(result.get("data") or [])
            cursor = result.get("nextCursor")
            if cursor is None:
                return answer
        raise RuntimeError("Codex thread listing did not finish")

    def __exit__(self, *unused):
        if self.process:
            try:
                self.process.stdin.close()
                self.process.wait(timeout=3)
            except (OSError, subprocess.TimeoutExpired):
                self.process.kill()
                self.process.wait(timeout=5)
            self.process.stdout.close()


def verify_codex(home: Path, sqlite_home: Path, cwd: Path, chats: list[dict]) -> None:
    require_version("codex")
    with CodexClient(home, sqlite_home, cwd) as client:
        listed = {item["id"]: item for archived in (False, True) for item in client.list_threads(archived)}
        for chat in chats:
            if chat["id"] not in listed:
                raise RuntimeError(f"Restored Codex thread is not visible: {chat['id']}")
            result = client.request("thread/read", {"threadId": chat["id"], "includeTurns": False})
            thread = result.get("thread") or {}
            if thread.get("id") != chat["id"]:
                raise RuntimeError(f"Codex cannot read restored thread: {chat['id']}")
            turns = client.request("thread/turns/list", {"threadId": chat["id"], "limit": 1, "itemsView": "full"})
            if not turns.get("data"):
                raise RuntimeError(f"Codex cannot read restored conversation: {chat['id']}")
            if chat.get("title"):
                if chat.get("archived"):
                    client.request("thread/unarchive", {"threadId": chat["id"]})
                client.request("thread/name/set", {"threadId": chat["id"], "name": chat["title"]})
                if chat.get("archived"):
                    client.request("thread/archive", {"threadId": chat["id"]})


def verify_grok(home: Path, chats: list[dict], cwd: Path) -> None:
    require_version("grok")
    env = os.environ.copy()
    env["GROK_HOME"] = str(home)
    for chat in chats:
        working = Path(chat.get("cwd") or cwd)
        result = subprocess.run([executable("grok"), "export", chat["id"]], env=env, cwd=working if working.is_dir() else cwd,
                                capture_output=True, timeout=30, **hidden_subprocess_kwargs())
        if result.returncode or not result.stdout.strip():
            raise RuntimeError(f"Grok cannot read restored session: {chat['id']}")
