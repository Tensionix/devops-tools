from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable
import importlib
import json
import locale
import os
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


@dataclass
class JobContext:
    paths: ProjectPaths
    operation: Operation
    log_file: Path
    report_dir: Path
    log_callback: LogCallback | None = None
    progress_callback: ProgressCallback | None = None
    cancel_callback: CancelCallback | None = None

    def log(self, message: str) -> None:
        append_log(self.log_file, message)
        if self.log_callback:
            self.log_callback(message)

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


def windows_oem_encoding() -> str | None:
    if os.name != "nt":
        return None
    try:
        import ctypes

        code_page = int(ctypes.windll.kernel32.GetOEMCP())
    except Exception:
        return None
    return f"cp{code_page}" if code_page else None


def output_decodings() -> list[str]:
    candidates = [
        "utf-8",
        windows_oem_encoding(),
        locale.getencoding() if hasattr(locale, "getencoding") else locale.getpreferredencoding(False),
        "mbcs" if os.name == "nt" else None,
        "cp866" if os.name == "nt" else None,
        "cp1251" if os.name == "nt" else None,
    ]
    seen: set[str] = set()
    result: list[str] = []
    for item in candidates:
        if not item:
            continue
        key = item.lower()
        if key in seen:
            continue
        seen.add(key)
        result.append(item)
    return result


def _decode_utf16ish(raw_line: bytes, encoding: str) -> str | None:
    data = raw_line
    if encoding == "utf-16-le" and data.startswith(b"\x00") and len(data) > 1:
        data = data[1:]
    elif encoding == "utf-16-be" and data.endswith(b"\x00") and len(data) > 1:
        data = data[:-1]
    if len(data) % 2:
        data = data + b"\x00" if encoding == "utf-16-le" else b"\x00" + data
    try:
        return data.decode(encoding)
    except UnicodeDecodeError:
        try:
            return data.decode(encoding, errors="replace")
        except Exception:
            return None


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


def legacy_decode_process_line(raw_line: bytes) -> str:
    if not raw_line.strip(b"\x00\r\n"):
        return ""
    if len(raw_line) >= 3 and raw_line[0] == 0 and raw_line[1] != 0:
        raw_line = raw_line[1:]
    if len(raw_line) >= 4:
        pairs = max(1, len(raw_line) // 2)
        odd_utf16_markers = sum(1 for index in range(1, len(raw_line), 2) if raw_line[index] in {0, 3, 4})
        even_utf16_markers = sum(1 for index in range(0, len(raw_line), 2) if raw_line[index] in {0, 3, 4})
        if odd_utf16_markers / pairs > 0.35:
            decoded = _decode_utf16ish(raw_line, "utf-16-le")
            if decoded is not None:
                return decoded
        if even_utf16_markers / pairs > 0.35:
            decoded = _decode_utf16ish(raw_line, "utf-16-be")
            if decoded is not None:
                return decoded
    for encoding in output_decodings():
        try:
            return raw_line.decode(encoding)
        except (LookupError, UnicodeDecodeError):
            continue
    return raw_line.decode("utf-8", errors="replace")


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
            context.log(line)

        now = time.monotonic()
        if now - last_progress >= 0.5:
            elapsed = max(0.0, now - start)
            context.progress(min(0.95, 0.08 + elapsed / max(1.0, float(progress_seconds))))
            last_progress = now

    exit_code = process.wait()
    context.log(f"[EXIT] {exit_code}")
    if check and exit_code != 0:
        if exit_code == 3:
            raise RuntimeError("Command stopped at a prerequisite, Windows edition, policy, or tool availability gate (exit code 3). Review the last command output lines above.")
        raise RuntimeError(f"Command failed with exit code {exit_code}.")
    return ProcessResult(exit_code=exit_code, lines=tuple(lines))


def resolve_project_path(context: JobContext, raw_path: str) -> Path:
    path_text = raw_path.strip().strip('"')
    if not path_text:
        raise RuntimeError("Path field is empty.")
    path = Path(os.path.expandvars(path_text)).expanduser()
    if not path.is_absolute():
        path = context.paths.root / path
    return path


def run_cmd_script(
    context: JobContext,
    script: str,
    args: list[str] | None = None,
    *,
    check: bool = True,
) -> ProcessResult:
    script_path = resolve_project_path(context, script)
    if not script_path.exists():
        raise RuntimeError(f"Script was not found: {script_path}")
    command = ["cmd.exe", "/d", "/c", "call", str(script_path), *(args or [])]
    return run_process(context, command, cwd=context.paths.root, check=check)


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
) -> JobResult:
    run_stamp = timestamp().replace(":", "-")
    log_file = paths.logs / f"{run_stamp}_{operation.id}.log"
    report_dir = paths.report / f"{run_stamp}_{operation.id}"
    report_dir.mkdir(parents=True, exist_ok=True)
    context = JobContext(paths, operation, log_file, report_dir, log_callback, progress_callback, cancel_callback)

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
