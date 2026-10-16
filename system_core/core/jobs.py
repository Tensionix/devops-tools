from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable
import importlib
import json
import os
import re
import subprocess
import time
import traceback

from .logging_utils import append_log, timestamp
from .manifest import Operation
from .paths import ProjectPaths
from .ansi import strip_ansi
from .output_decode import decode_process_bytes


LogCallback = Callable[[str], None]
ProgressCallback = Callable[[float], None]
CancelCallback = Callable[[], bool]
ActivityCallback = Callable[[str], None]


@dataclass
class JobContext:
    paths: ProjectPaths
    operation: Operation
    log_file: Path
    report_dir: Path
    log_callback: LogCallback | None = None
    progress_callback: ProgressCallback | None = None
    cancel_callback: CancelCallback | None = None
    # The window on Avalonia asks for two things the console and the former window did not get:
    # the live line of a long step (`activity_callback`) and a frame line round every process the
    # operation starts (`frames` - the language of the frame, "" for none). The log file of the
    # operation is written as it always was.
    activity_callback: ActivityCallback | None = None
    frames: str = ""
    processes_started: int = 0

    def log(self, message: str) -> None:
        append_log(self.log_file, message)
        if self.log_callback:
            self.log_callback(message)

    def log_apart(self, written: str, shown: str) -> None:
        """One line to the log file, another to the one who listens."""
        append_log(self.log_file, written)
        if self.log_callback:
            self.log_callback(shown)

    def activity(self, text: str) -> None:
        if self.activity_callback:
            self.activity_callback(text)

    def progress(self, value: float) -> None:
        if self.progress_callback:
            self.progress_callback(max(0.0, min(1.0, float(value))))

    def cancelled(self) -> bool:
        return bool(self.cancel_callback and self.cancel_callback())


@dataclass
class JobResult:
    ok: bool
    message: str
    data: dict[str, Any]


@dataclass(frozen=True)
class ProcessResult:
    exit_code: int
    lines: tuple[str, ...]


SENSITIVE_PARAMETER_PARTS = (
    "password",
    "passwd",
    "passphrase",
    "secret",
    "token",
    "apikey",
    "api_key",
    "access_key",
    "private_key",
    "credential",
)


def redact_parameters(value: Any) -> Any:
    if isinstance(value, dict):
        result: dict[str, Any] = {}
        for key, item in value.items():
            key_text = str(key)
            lowered = key_text.lower()
            if any(part in lowered for part in SENSITIVE_PARAMETER_PARTS):
                result[key_text] = "***REDACTED***" if item not in {"", None} else item
                continue
            result[key_text] = redact_parameters(item)
        return result
    if isinstance(value, list):
        return [redact_parameters(item) for item in value]
    if isinstance(value, tuple):
        return tuple(redact_parameters(item) for item in value)
    return value


def utf8_subprocess_env(extra: dict[str, str] | None = None) -> dict[str, str]:
    env = os.environ.copy()
    if extra:
        env.update(extra)
    env["PYTHONUTF8"] = "1"
    env["PYTHONIOENCODING"] = "utf-8"
    env["PYTHONUNBUFFERED"] = "1"
    env.pop("NO_COLOR", None)
    env["CLICOLOR"] = "1"
    env["CLICOLOR_FORCE"] = "1"
    env["FORCE_COLOR"] = "1"
    env["AUDION_GUI_TERMINAL"] = "1"
    return env


def unbuffer_python_command(command: list[str]) -> list[str]:
    if not command:
        return command
    executable = Path(command[0]).name.lower()
    if executable not in python_executable_names():
        return command
    if any(item == "-u" for item in command[1:3]):
        return command
    return [command[0], "-u", *command[1:]]


def python_executable_names() -> set[str]:
    return {"python", "python.exe", "python3", "python3.exe", "py", "py.exe", "pythonw.exe"}


def is_python_command(command: list[str]) -> bool:
    if not command:
        return False
    return Path(command[0]).name.lower() in python_executable_names()


def hidden_subprocess_startupinfo() -> subprocess.STARTUPINFO | None:
    if os.name != "nt" or not hasattr(subprocess, "STARTUPINFO"):
        return None
    startupinfo = subprocess.STARTUPINFO()
    startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
    startupinfo.wShowWindow = 0
    return startupinfo


def hidden_subprocess_creationflags() -> int:
    if os.name == "nt" and hasattr(subprocess, "CREATE_NO_WINDOW"):
        return int(subprocess.CREATE_NO_WINDOW)
    return 0


def hidden_subprocess_kwargs() -> dict[str, Any]:
    return {
        "startupinfo": hidden_subprocess_startupinfo(),
        "creationflags": hidden_subprocess_creationflags(),
    }


def format_command(command: list[str]) -> str:
    return " ".join(f'"{item}"' if " " in item else item for item in command)


# The frame round a process: one line in the colour of a heading where the console shows two
# ([CWD] and [CMD]), and the exit code in the colour of how it ended - green, amber for the gate of
# exit code 3, red for any other. The codes are ANSI: the window paints them in its own tones.
FRAME_WORDS = {"ru": "процесс", "en": "process"}
_BOLD_CYAN, _GREEN, _AMBER, _RED, _RESET = "\x1b[1;36m", "\x1b[32m", "\x1b[33m", "\x1b[31m", "\x1b[0m"
_SHELL_FLAGS = {"-noprofile", "-nologo", "-noninteractive", "-executionpolicy", "bypass", "-file", "-command", "/d", "/c", "call"}


def frame_line(number: int, command: list[str], language: str) -> str:
    """`── process 2 · AudionPs.exe · Audion_Network_Cleaner.ps1 -Mode StandardRepair ──`"""
    program = Path(command[0]).name if command else "?"
    rest = []
    for item in command[1:]:
        if not rest and item.lower() in _SHELL_FLAGS:
            continue
        text = Path(item).name if not rest and ("\\" in item or "/" in item) and Path(item).suffix else item
        rest.append(f'"{text}"' if " " in text else text)
    told = " ".join(rest)
    if len(told) > 160:
        told = told[:157] + "..."
    word = FRAME_WORDS.get(language, FRAME_WORDS["en"])
    return f"{_BOLD_CYAN}── {word} {number} · {program}" + (f" · {told}" if told else "") + f" ──{_RESET}"


def exit_line(exit_code: int) -> str:
    colour = _GREEN if exit_code == 0 else _AMBER if exit_code == 3 else _RED
    return f"{colour}[EXIT {exit_code}]{_RESET}"


# A line a tool rewrites in place to show how far it is - and nothing else: DISM "[====  45.0% ====]",
# wsl.exe "Downloading: Ubuntu [=====      ] 37.0%", a bare "45%". Such a line goes to the live line
# of the window when the window listens. A line that says something and ends in a share
# ("free 45%") is no progress and stays in the log.
PROGRESS_LINE = re.compile(
    r"^\s*(?:"
    r"\[[=\s]*\d{1,3}(?:[.,]\d+)?\s?%[=\s]*\]"
    r"|(?:[^\[\]%]{0,60}[:\s])?\[[=#>\s.-]*\]\s*\d{1,3}(?:[.,]\d+)?\s?%"
    r"|\d{1,3}(?:[.,]\d+)?\s?%"
    r")\s*$")


def decode_process_line(raw_line: bytes) -> str:
    return decode_process_bytes(raw_line)


SPINNER_FRAME_CHARS = set("-\\|/ \t")


def _is_spinner_only_line(line: str) -> bool:
    stripped = line.strip()
    return bool(stripped) and all(char in SPINNER_FRAME_CHARS for char in line)


def decoded_process_lines(raw_line: bytes | str) -> list[str]:
    text = str(raw_line) if isinstance(raw_line, str) else decode_process_bytes(raw_line)
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    lines: list[str] = []
    for part in text.split("\n"):
        line = part.rstrip()
        if not line or _is_spinner_only_line(line):
            continue
        lines.append(line)
    return lines


def run_process(
    context: JobContext,
    command: list[str],
    *,
    cwd: Path | None = None,
    extra_env: dict[str, str] | None = None,
    input_text: str | None = None,
    check: bool = True,
    progress_seconds: float = 600.0,
) -> ProcessResult:
    """Run a child process hidden, stream stdout/stderr into the GUI log."""
    if not command:
        raise ValueError("Command is empty.")

    command = unbuffer_python_command(command)
    working_dir = cwd or context.paths.root
    if context.frames:
        context.processes_started += 1
        append_log(context.log_file, f"[CWD] {working_dir}")
        context.log_apart(f"[CMD] {format_command(command)}", frame_line(context.processes_started, command, context.frames))
    else:
        context.log(f"[CWD] {working_dir}")
        context.log(f"[CMD] {format_command(command)}")

    use_python_text_stream = is_python_command(command)
    process_kwargs: dict[str, Any] = {
        "cwd": str(working_dir),
        "stdin": subprocess.PIPE if input_text is not None else subprocess.DEVNULL,
        "stdout": subprocess.PIPE,
        "stderr": subprocess.STDOUT,
        "env": utf8_subprocess_env(extra_env),
        **hidden_subprocess_kwargs(),
    }
    if use_python_text_stream:
        process_kwargs.update({"bufsize": 1, "text": True, "encoding": "utf-8", "errors": "replace"})

    process = subprocess.Popen(command, **process_kwargs)
    if input_text is not None:
        assert process.stdin is not None
        if use_python_text_stream:
            process.stdin.write(input_text)
        else:
            process.stdin.write(input_text.encode("utf-8", errors="replace"))
        process.stdin.close()

    lines: list[str] = []
    start = time.monotonic()
    last_progress = start

    assert process.stdout is not None
    for raw_line in process.stdout:
        if context.cancelled():
            context.log("[CANCEL] Terminating child process...")
            process.terminate()
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()
            raise RuntimeError("Operation cancelled by user.")

        output_lines = [str(raw_line).rstrip("\r\n")] if use_python_text_stream else decoded_process_lines(bytes(raw_line))
        for line in output_lines:
            if not line:
                continue
            lines.append(strip_ansi(line))
            if context.activity_callback is not None and PROGRESS_LINE.match(strip_ansi(line)):
                append_log(context.log_file, line)
                context.activity(strip_ansi(line).strip())
                continue
            context.log(line)

        now = time.monotonic()
        if now - last_progress >= 0.5:
            elapsed = max(0.0, now - start)
            context.progress(min(0.95, 0.08 + elapsed / max(1.0, float(progress_seconds))))
            last_progress = now

    exit_code = process.wait()
    if context.frames:
        context.log_apart(f"[EXIT] {exit_code}", exit_line(exit_code))
    else:
        context.log(f"[EXIT] {exit_code}")
    if check and exit_code != 0:
        if exit_code == 3:
            raise RuntimeError("Command stopped at a prerequisite, Windows edition, policy, or tool availability gate (exit code 3). Review the last command output lines above.")
        raise RuntimeError(f"Command failed with exit code {exit_code}.")
    return ProcessResult(exit_code=exit_code, lines=tuple(lines))


def _load_callable(service: str) -> Callable[[JobContext], Any]:
    module_name, function_name = service.split(":", 1)
    module = importlib.import_module(module_name)
    return getattr(module, function_name)


def execute_operation(
    paths: ProjectPaths,
    operation: Operation,
    log_callback: LogCallback | None = None,
    progress_callback: ProgressCallback | None = None,
    cancel_callback: CancelCallback | None = None,
    activity_callback: ActivityCallback | None = None,
    frames: str = "",
) -> JobResult:
    run_stamp = timestamp().replace(":", "-")
    log_file = paths.logs / f"{run_stamp}_{operation.id}.log"
    report_dir = paths.report / f"{run_stamp}_{operation.id}"
    report_dir.mkdir(parents=True, exist_ok=True)
    context = JobContext(paths, operation, log_file, report_dir, log_callback, progress_callback, cancel_callback,
                         activity_callback, frames)

    try:
        context.log(f"Starting operation: {operation.id}")
        if operation.parameters:
            safe_parameters = redact_parameters(operation.parameters)
            context.log(f"Parameters: {json.dumps(safe_parameters, ensure_ascii=False, sort_keys=True)}")
        context.progress(0.0)
        result = _load_callable(operation.service)(context)
        context.progress(1.0)
        context.log(f"Finished operation: {operation.id}")

        if isinstance(result, dict):
            return JobResult(True, "Operation finished.", result)
        return JobResult(True, str(result or "Operation finished."), {})

    except RuntimeError as exc:
        context.log(f"ERROR: {exc}")
        return JobResult(False, f"{exc.__class__.__name__}: {exc}", {})
    except Exception as exc:
        context.log(traceback.format_exc())
        return JobResult(False, f"{exc.__class__.__name__}: {exc}", {})
