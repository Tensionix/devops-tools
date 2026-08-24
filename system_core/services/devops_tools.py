from __future__ import annotations

import csv
from dataclasses import dataclass, field, replace
from datetime import datetime
from html.parser import HTMLParser
import hashlib
from pathlib import Path
from typing import Any, Callable
import base64
import ipaddress
import json
import os
import re
import shutil
import socket
import subprocess
import sys
import time
import urllib.parse
import urllib.request

from system_core.core.config import load_yaml_or_json
from system_core.core.jobs import JobContext, ProcessResult, decode_process_line, format_command, run_process
from system_core.core.output_decode import decode_process_bytes


PWSH_ARGS = ["-NoLogo", "-NoProfile", "-ExecutionPolicy", "Bypass"]
# Terminal-bar prelude. Redirected stdout makes PowerShell fall back to the OEM code page
# and drop ANSI colour, so both are pinned explicitly before the user's command runs.
POWERSHELL_UTF8_PREAMBLE = (
    "$audionUtf8 = [System.Text.UTF8Encoding]::new($false); "
    "[Console]::InputEncoding = $audionUtf8; "
    "[Console]::OutputEncoding = $audionUtf8; "
    "$OutputEncoding = $audionUtf8; "
    "if (Get-Variable PSStyle -ErrorAction SilentlyContinue) { $PSStyle.OutputRendering = 'ANSI' }; "
)
WSL_DISTRIBUTION_MANIFEST_URL = "https://raw.githubusercontent.com/microsoft/WSL/master/distributions/DistributionInfo.json"
MIN_WSL_EXPORT_BYTES = 1024 * 1024

WSL_DEV_BASELINE_PACKAGES = [
    "ca-certificates",
    "curl",
    "wget",
    "rsync",
    "zstd",
    "git",
    "git-lfs",
    "jq",
    "tree",
    "ripgrep",
    "fd-find",
    "fzf",
    "unzip",
    "zip",
    "7zip",
    "htop",
    "btop",
    "ncdu",
    "mc",
    "far2l",
    "micro",
    "neovim",
    "tmux",
    "shellcheck",
    "tree-sitter-cli",
    "build-essential",
    "gcc",
    "g++",
    "make",
    "cmake",
    "pkg-config",
    "python3",
    "python3-pip",
    "python3-venv",
    "pipx",
    "sudo",
    "openssh-client",
    "rclone",
    "net-tools",
    "nmap",
    "traceroute",
]

WSL_MEDIA_CLI_PACKAGES = [
    "ffmpeg",
    "mediainfo",
    "imagemagick",
    "sox",
    "flac",
    "vorbis-tools",
    "opus-tools",
    "libimage-exiftool-perl",
    "mkvtoolnix",
    "handbrake-cli",
    "x264",
    "x265",
    "aom-tools",
    "svt-av1",
    "atomicparsley",
    "hashdeep",
    "normalize-audio",
    "shntool",
]

WSL_LAB_PACKAGES = [
    "podman",
    "distrobox",
    "fuse-overlayfs",
    "slirp4netns",
]

WSL_SYNC_EXTRA_PACKAGES = [
    "syncthing",
    "wireguard-tools",
]

WSL_APT_MIRRORS: dict[str, tuple[str, str]] = {
    "keep": ("", ""),
    "https_archive": ("https://archive.ubuntu.com/ubuntu", "https://security.ubuntu.com/ubuntu"),
    "https_azure": ("https://azure.archive.ubuntu.com/ubuntu", "https://security.ubuntu.com/ubuntu"),
    "https_kernel": ("https://mirrors.edge.kernel.org/ubuntu", "https://security.ubuntu.com/ubuntu"),
    "https_yandex": ("https://mirror.yandex.ru/ubuntu", "https://security.ubuntu.com/ubuntu"),
}


def bundle_root(context: JobContext | Path | str) -> Path:
    if isinstance(context, JobContext):
        return context.paths.root.parent
    root = Path(context).resolve()
    return root.parent


def tool_dir(context: JobContext | Path | str, name: str) -> Path:
    path = bundle_root(context) / name
    if not path.exists():
        raise RuntimeError(f"Tool folder was not found: {path}")
    return path


def project_tool_dir(context: JobContext, name: str) -> Path:
    raw = str(name).strip().replace("\\", "/")
    if not raw:
        raise RuntimeError("Project tool folder name is empty.")
    relative = Path(raw)
    if relative.is_absolute() or ".." in relative.parts:
        raise RuntimeError(f"Unsafe project tool folder name: {name}")
    tools_root = (context.paths.root / "tools").resolve()
    path = (tools_root / relative).resolve()
    if path != tools_root and tools_root not in path.parents:
        raise RuntimeError(f"Project tool folder escaped tools root: {path}")
    if not path.exists():
        raise RuntimeError(f"Project tool folder was not found: {path}")
    return path


def open_path(context: JobContext, path: Path) -> None:
    if path.exists() and path.is_file():
        target = path
        context.log(f"Opening file: {target}")
    else:
        ensure_directory(path, label="Folder")
        target = path
        context.log(f"Opening folder: {target}")
    if os.name == "nt":
        os.startfile(str(target))  # type: ignore[attr-defined]
    else:
        subprocess.Popen(["xdg-open", str(target)])
    context.progress(1.0)


def ensure_directory(path: Path, *, label: str = "Folder") -> None:
    try:
        path.mkdir(parents=True, exist_ok=True)
    except OSError as exc:
        raise RuntimeError(f"{label} is not available or cannot be created: {path}") from exc


def resolve_pwsh(root: Path | str | None = None) -> str:
    project_root = Path(root).resolve() if root else Path(__file__).resolve().parents[2]
    candidates = [
        project_root / "system_core" / "powershell" / "pwsh.exe",
        shutil.which("pwsh.exe"),
        shutil.which("powershell.exe"),
    ]
    for candidate in candidates:
        if not candidate:
            continue
        path = Path(candidate) if not isinstance(candidate, Path) else candidate
        if path.exists():
            return str(path)
    raise RuntimeError("PowerShell was not found: portable pwsh.exe, pwsh.exe, powershell.exe.")


def resolve_windows_powershell() -> str:
    if os.name != "nt":
        return resolve_pwsh()
    system_root = Path(os.environ.get("SystemRoot", r"C:\Windows"))
    candidates = [
        system_root / "Sysnative" / "WindowsPowerShell" / "v1.0" / "powershell.exe",
        system_root / "System32" / "WindowsPowerShell" / "v1.0" / "powershell.exe",
        shutil.which("powershell.exe"),
    ]
    for candidate in candidates:
        if not candidate:
            continue
        path = Path(candidate) if not isinstance(candidate, Path) else candidate
        if path.exists():
            return str(path)
    raise RuntimeError("Windows PowerShell was not found: powershell.exe.")


def powershell_command(root: Path | str, *tail: str, windows_powershell: bool = False) -> list[str]:
    exe = resolve_windows_powershell() if windows_powershell else resolve_pwsh(root)
    return [exe, *PWSH_ARGS, *tail]


def parameter_args(parameters: dict[str, Any]) -> list[str]:
    args: list[str] = []
    for key, value in parameters.items():
        if value is None:
            continue
        name = str(key).strip()
        if not name:
            continue
        if isinstance(value, bool):
            if value:
                args.append(f"-{name}")
            continue
        if isinstance(value, (list, tuple)):
            if not value:
                continue
            args.append(f"-{name}")
            args.extend(str(item) for item in value if item is not None)
            continue
        text = str(value)
        if text == "":
            continue
        args.extend([f"-{name}", text])
    return args


def is_windows_admin() -> bool:
    if os.name != "nt":
        return True
    try:
        import ctypes

        return bool(ctypes.windll.shell32.IsUserAnAdmin())
    except Exception:
        return False


def _ps_invocation_arg(arg: str) -> str:
    if re.fullmatch(r"-[A-Za-z][A-Za-z0-9_]*", arg):
        return arg
    return ps_quote(arg)


def _read_elevated_log(context: JobContext, log_path: Path) -> None:
    if not log_path.exists():
        context.log(f"[UAC] Elevated log was not created: {log_path}")
        return
    context.log(f"[UAC] Elevated log: {log_path}")
    raw = log_path.read_bytes()
    for raw_line in raw.splitlines():
        line = decode_process_line(raw_line).strip("\r\n")
        if line:
            context.log(line)


def run_elevated_ps_command(
    context: JobContext,
    command_text: str,
    *,
    cwd: Path | None = None,
    progress_seconds: float = 300.0,
    input_text: str | None = None,
    windows_powershell: bool = False,
) -> ProcessResult:
    if os.name != "nt":
        return run_ps_command(context, command_text, cwd=cwd, progress_seconds=progress_seconds, input_text=input_text)

    working_dir = cwd or context.paths.root
    context.report_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    payload = context.report_dir / f"elevated_payload_{stamp}.ps1"
    wrapper = context.report_dir / f"elevated_wrapper_{stamp}.ps1"
    launcher = context.report_dir / f"elevated_launcher_{stamp}.ps1"
    log_path = context.report_dir / f"elevated_output_{stamp}.log"
    exit_path = context.report_dir / f"elevated_exit_{stamp}.txt"
    input_path = context.report_dir / f"elevated_input_{stamp}.txt" if input_text is not None else None
    pwsh = resolve_windows_powershell() if windows_powershell else resolve_pwsh(context.paths.root)

    temp_files = [payload, wrapper, launcher, exit_path]
    if input_path is not None:
        temp_files.append(input_path)

    try:
        payload.write_text(command_text, encoding="utf-8")
        if input_path is not None:
            input_path.write_text(input_text, encoding="utf-8")
        wrapper.write_text(
            "\n".join(
                [
                    "$ErrorActionPreference = 'Continue'",
                    "$OutputEncoding = [System.Text.UTF8Encoding]::new($false)",
                    "try { [Console]::OutputEncoding = $OutputEncoding } catch { }",
                    f"$logPath = {ps_quote(log_path)}",
                    f"$exitPath = {ps_quote(exit_path)}",
                    f"$payload = {ps_quote(payload)}",
                    f"$inputPath = {ps_quote(input_path) if input_path is not None else '$null'}",
                    f"Set-Location -LiteralPath {ps_quote(working_dir)}",
                    "\"=== Elevated PowerShell started: $(Get-Date -Format o) ===\" | Out-File -FilePath $logPath -Encoding utf8",
                    "$stdin = $null",
                    "try {",
                    "  if ($inputPath) {",
                    "    $stdin = [System.IO.StreamReader]::new($inputPath, [System.Text.UTF8Encoding]::new($false))",
                    "    [Console]::SetIn($stdin)",
                    "  }",
                    "  & $payload *>&1 | Tee-Object -FilePath $logPath -Append",
                    "  $code = if ($global:LASTEXITCODE -is [int]) { $global:LASTEXITCODE } else { 0 }",
                    "} catch {",
                    "  $_ | Out-String | Tee-Object -FilePath $logPath -Append",
                    "  $code = 1",
                    "} finally {",
                    "  if ($stdin) { $stdin.Dispose() }",
                    "}",
                    "\"__AUDION_EXIT_CODE=$code\" | Out-File -FilePath $logPath -Encoding utf8 -Append",
                    "$code | Out-File -FilePath $exitPath -Encoding ascii",
                    "exit $code",
                    "",
                ]
            ),
            encoding="utf-8",
        )
        launcher.write_text(
            "\n".join(
                [
                    "$ErrorActionPreference = 'Stop'",
                    f"$exe = {ps_quote(pwsh)}",
                    f"$wrapper = {ps_quote(wrapper)}",
                    f"$cwd = {ps_quote(working_dir)}",
                    "$args = @('-NoLogo', '-NoProfile', '-ExecutionPolicy', 'Bypass', '-File', $wrapper)",
                    "Write-Host '[UAC] Requesting Administrator rights...'",
                    "$process = Start-Process -FilePath $exe -ArgumentList $args -WorkingDirectory $cwd -Verb RunAs -Wait -PassThru",
                    "exit $process.ExitCode",
                    "",
                ]
            ),
            encoding="utf-8",
        )

        context.log("[UAC] This action needs Administrator rights; Windows may show a UAC prompt.")
        result = run_process(
            context,
            powershell_command(context.paths.root, "-File", str(launcher), windows_powershell=windows_powershell),
            cwd=working_dir,
            check=False,
            progress_seconds=progress_seconds,
        )
        _read_elevated_log(context, log_path)
        exit_code = result.exit_code
        if exit_path.exists():
            try:
                exit_code = int(exit_path.read_text(encoding="ascii", errors="ignore").strip())
            except ValueError:
                pass
        if exit_code != 0:
            raise RuntimeError(f"Elevated command failed with exit code {exit_code}.")
        return ProcessResult(exit_code=exit_code, lines=())
    finally:
        for path in temp_files:
            try:
                if path.exists():
                    path.unlink()
            except OSError as exc:
                context.log(f"[UAC] Could not remove temporary file {path}: {exc}")


def run_ps1(
    context: JobContext,
    script: Path,
    parameters: dict[str, Any] | None = None,
    *,
    cwd: Path | None = None,
    check: bool = True,
    progress_seconds: float = 600.0,
    elevated: bool = False,
    input_text: str | None = None,
    windows_powershell: bool = False,
) -> ProcessResult:
    if not script.exists():
        raise RuntimeError(f"PowerShell script was not found: {script}")
    args = parameter_args(parameters or {})
    if elevated and os.name == "nt" and not is_windows_admin():
        invocation = " ".join([ps_quote(script), *(_ps_invocation_arg(arg) for arg in args)])
        return run_elevated_ps_command(
            context,
            f"& {invocation}",
            cwd=cwd or script.parent,
            progress_seconds=progress_seconds,
            input_text=input_text,
            windows_powershell=windows_powershell,
        )
    command = powershell_command(context.paths.root, "-File", str(script), *args, windows_powershell=windows_powershell)
    return run_process(context, command, cwd=cwd or script.parent, input_text=input_text, check=check, progress_seconds=progress_seconds)


def run_ps_command(
    context: JobContext,
    command_text: str,
    *,
    cwd: Path | None = None,
    check: bool = True,
    progress_seconds: float = 120.0,
    elevated: bool = False,
    input_text: str | None = None,
    windows_powershell: bool = False,
) -> ProcessResult:
    if elevated and os.name == "nt" and not is_windows_admin():
        return run_elevated_ps_command(
            context,
            command_text,
            cwd=cwd,
            progress_seconds=progress_seconds,
            input_text=input_text,
            windows_powershell=windows_powershell,
        )
    command = powershell_command(context.paths.root, "-Command", command_text, windows_powershell=windows_powershell)
    return run_process(context, command, cwd=cwd or context.paths.root, input_text=input_text, check=check, progress_seconds=progress_seconds)


def run_cmd_file(
    context: JobContext,
    script: Path,
    args: list[str] | None = None,
    *,
    cwd: Path | None = None,
    check: bool = True,
    progress_seconds: float = 600.0,
) -> ProcessResult:
    if not script.exists():
        raise RuntimeError(f"CMD script was not found: {script}")
    command = ["cmd.exe", "/d", "/c", "call", str(script), *(args or [])]
    return run_process(context, command, cwd=cwd or script.parent, check=check, progress_seconds=progress_seconds)


def _run_capture(command: list[str], *, cwd: Path | None = None, timeout: float = 8.0, check: bool = True) -> str:
    result = subprocess.run(
        command,
        cwd=str(cwd) if cwd else None,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        timeout=timeout,
        check=False,
    )
    text = decode_process_bytes(result.stdout).replace("\x00", "").strip()
    if check and result.returncode != 0:
        first_line = next((line.strip() for line in text.splitlines() if line.strip()), "")
        detail = f": {first_line}" if first_line else ""
        raise RuntimeError(f"{format_command(command)} failed with exit code {result.returncode}{detail}")
    return text


def _json_capture(root: Path, command_text: str, *, timeout: float = 8.0) -> Any:
    try:
        text = _run_capture(powershell_command(root, "-Command", command_text), cwd=root, timeout=timeout)
        if not text:
            return None
        return json.loads(text)
    except Exception:
        return None


def _option(value: Any, label: str, label_ru: str | None = None) -> dict[str, str]:
    item = {"value": str(value), "label": label}
    if label_ru:
        item["label_ru"] = label_ru
    return item


def _package_options(packages: list[str]) -> list[dict[str, str]]:
    return [_option(package, package, package) for package in packages]


def wsl_dev_baseline_package_options(root: Path | str | None = None) -> list[dict[str, str]]:
    return _package_options(WSL_DEV_BASELINE_PACKAGES)


def wsl_media_cli_package_options(root: Path | str | None = None) -> list[dict[str, str]]:
    return _package_options(WSL_MEDIA_CLI_PACKAGES)


def wsl_sync_package_options(root: Path | str | None = None) -> list[dict[str, str]]:
    return _package_options(WSL_SYNC_EXTRA_PACKAGES)


def wsl_lab_package_options(root: Path | str | None = None) -> list[dict[str, str]]:
    return _package_options(WSL_LAB_PACKAGES)


def resolve_user_path(context: JobContext, value: Any, *, default: Path | None = None) -> Path:
    text = str(value or "").strip().strip('"')
    if not text:
        return default or context.paths.root
    path = Path(os.path.expandvars(text)).expanduser()
    if not path.is_absolute():
        path = context.paths.root / path
    return path


def ps_quote(value: Any) -> str:
    return "'" + str(value or "").replace("'", "''") + "'"


def ps_array(values: list[Any]) -> str:
    return "@(" + ", ".join(ps_quote(value) for value in values) + ")"


DEFAULT_APP_GUARD_IDENTIFIERS = [
    "http",
    "https",
    ".pdf",
    ".jpg",
    ".jpeg",
    ".png",
    ".webp",
    ".gif",
    ".mp4",
    ".mkv",
    ".mp3",
    ".flac",
    ".wav",
]


def normalize_string_list(value: Any) -> list[str]:
    if isinstance(value, (list, tuple, set)):
        raw_items = value
    else:
        raw_items = re.split(r"[,;\s]+", str(value or ""))
    result: list[str] = []
    for item in raw_items:
        text = str(item or "").strip()
        if text and text not in result:
            result.append(text)
    return result


def integer_parameter(value: Any, default: int, *, minimum: int | None = None, maximum: int | None = None) -> int:
    try:
        result = int(float(str(value).strip()))
    except (TypeError, ValueError):
        result = default
    if minimum is not None:
        result = max(minimum, result)
    if maximum is not None:
        result = min(maximum, result)
    return result


def normalize_port_list(value: Any, default: list[int]) -> list[int]:
    result: list[int] = []
    for item in normalize_string_list(value):
        try:
            port = int(item)
        except ValueError:
            continue
        if 1 <= port <= 65535 and port not in result:
            result.append(port)
    return result or list(default)


def ps_int_array(values: list[int]) -> str:
    return "@(" + ", ".join(str(int(value)) for value in values) + ")"


def normalize_endpoint_and_ports(value: str, ports: list[int]) -> tuple[str, list[int]]:
    text = str(value or "").strip()
    if not text:
        return "", ports
    probe = text if "://" in text else f"//{text}"
    try:
        parsed = urllib.parse.urlsplit(probe)
    except ValueError:
        return text, ports
    host = parsed.hostname or text
    try:
        port = parsed.port
    except ValueError:
        port = None
    if port and 1 <= port <= 65535 and port not in ports:
        ports = [*ports, port]
    return host.strip("[]"), ports


def is_local_network_ip(value: str) -> bool:
    try:
        address = ipaddress.ip_address(str(value).strip())
    except ValueError:
        return False
    local_networks = (
        ipaddress.ip_network("10.0.0.0/8"),
        ipaddress.ip_network("172.16.0.0/12"),
        ipaddress.ip_network("192.168.0.0/16"),
        ipaddress.ip_network("127.0.0.0/8"),
        ipaddress.ip_network("169.254.0.0/16"),
        ipaddress.ip_network("::1/128"),
        ipaddress.ip_network("fc00::/7"),
        ipaddress.ip_network("fe80::/10"),
    )
    return any(address in network for network in local_networks)


def tcp_port_is_open(host: str, port: int, timeout: float = 2.5) -> bool:
    try:
        with socket.create_connection((host, int(port)), timeout=timeout):
            return True
    except OSError:
        return False


def default_apps_guard_script(context: JobContext, name: str) -> Path:
    script = context.paths.system_core / "windows_default_apps_guard" / name
    if not script.exists():
        raise RuntimeError(f"Default Apps Guard script was not found: {script}")
    return script


def default_apps_program_data_dir() -> Path:
    if os.name == "nt":
        base = Path(os.environ.get("ProgramData", r"C:\ProgramData"))
    else:
        base = Path("/var/lib")
    return base / "Audion" / "DefaultApps"


def default_apps_guard_paths(context: JobContext) -> dict[str, Path]:
    root = context.paths.root
    return {
        "backup_dir": root / "backup" / "default_apps",
        "profile_dir": root / "profiles" / "default_apps",
        "profile_xml": root / "profiles" / "default_apps" / "AppAssociations.xml",
        "policy_dir": default_apps_program_data_dir(),
    }


def default_apps_backup_xml_options(root: Path | str | None = None) -> list[dict[str, str]]:
    project_root = Path(root).resolve() if root else Path(__file__).resolve().parents[2]
    backup_dir = project_root / "backup" / "default_apps"
    options: list[dict[str, str]] = [
        _option("", "Select a backup XML...", "Выбрать backup XML...")
    ]
    if not backup_dir.exists():
        return [*options, _option("", "No Default Apps Guard backups found", "Backup Default Apps Guard не найдены")]

    files = sorted(
        (path for path in backup_dir.glob("*.xml") if path.is_file()),
        key=lambda path: path.stat().st_mtime if path.exists() else 0,
        reverse=True,
    )
    if not files:
        return [*options, _option("", "No XML backups found", "XML backup не найдены")]

    for path in files[:200]:
        stamp = ""
        try:
            stamp = datetime.fromtimestamp(path.stat().st_mtime).strftime("%Y-%m-%d %H:%M:%S")
        except Exception:
            pass
        label_note = ""
        kind_note = ""
        note_path = Path(f"{path}.note.txt")
        if note_path.exists():
            try:
                for line in note_path.read_text(encoding="utf-8", errors="replace").splitlines():
                    if line.startswith("Label:"):
                        label_note = line.split(":", 1)[1].strip()
                    elif line.startswith("Kind:"):
                        kind_note = line.split(":", 1)[1].strip()
            except OSError:
                pass
        parts = [item for item in (stamp, label_note, kind_note, path.name) if item]
        label = " | ".join(parts)
        options.append(_option(path, label, label))
    return options


def _system_drive_root() -> Path:
    raw = os.environ.get("SystemDrive", "C:").strip().rstrip("\\/")
    if not re.fullmatch(r"[A-Za-z]:", raw):
        raw = "C:"
    return Path(raw + "\\")


def _path_drive_root(path: Path | str) -> Path | None:
    drive = Path(path).resolve().drive
    if not re.fullmatch(r"[A-Za-z]:", drive):
        return None
    return Path(drive.upper() + "\\")


def _windows_fixed_drive_roots() -> list[Path]:
    if os.name != "nt":
        return []
    try:
        import ctypes

        kernel32 = ctypes.windll.kernel32
        bitmask = int(kernel32.GetLogicalDrives())
        fixed_roots: list[Path] = []
        for index in range(26):
            if not (bitmask & (1 << index)):
                continue
            letter = chr(ord("A") + index)
            root_text = f"{letter}:\\"
            # DRIVE_FIXED: local disk, not removable/network/CD-ROM/RAM disk.
            if int(kernel32.GetDriveTypeW(root_text)) == 3:
                fixed_roots.append(Path(root_text))
        return fixed_roots
    except Exception:
        return []


def _drive_free_bytes(root: Path) -> int:
    if os.name != "nt":
        return 0
    try:
        import ctypes

        free = ctypes.c_ulonglong(0)
        ctypes.windll.kernel32.GetDiskFreeSpaceExW(str(root), ctypes.byref(free), None, None)
        return int(free.value)
    except Exception:
        return 0


def wsl_workspace_root(context: JobContext | Path | str) -> Path:
    project_root = context.paths.root if isinstance(context, JobContext) else Path(context).resolve()
    system_root = _system_drive_root()
    system_drive = system_root.drive.lower()
    fixed_roots = _windows_fixed_drive_roots()
    non_system_roots = [root for root in fixed_roots if root.drive.lower() != system_drive]

    for root in non_system_roots:
        existing = root / "WSL"
        if existing.exists():
            return existing

    project_drive_root = _path_drive_root(project_root)
    if project_drive_root and any(root.drive.lower() == project_drive_root.drive.lower() for root in non_system_roots):
        return project_drive_root / "WSL"

    if non_system_roots:
        return max(non_system_roots, key=_drive_free_bytes) / "WSL"

    return system_root / "WSL"


def wsl_candidate_roots(root: Path | str | None = None) -> list[Path]:
    project_root = Path(root).resolve() if root else Path(__file__).resolve().parents[2]
    parent = project_root.parent
    roots = [wsl_workspace_root(project_root), parent / "WSL"]
    roots.extend(block / "WSL" for block in sorted(parent.glob("Audion_WSL_Block_*")))
    result: list[Path] = []
    seen: set[str] = set()
    for item in roots:
        key = str(item).lower()
        if key in seen:
            continue
        seen.add(key)
        result.append(item)
    return result


def ensure_wsl_workspace(context: JobContext) -> Path:
    root = wsl_workspace_root(context)
    for child in ("Backup", "Images", "Logs", "VHDX"):
        (root / child).mkdir(parents=True, exist_ok=True)
    return root


def safe_wsl_file_part(value: str) -> str:
    text = re.sub(r"[^A-Za-z0-9._-]+", "_", value.strip())
    return text.strip("._") or "distro"


def assert_wsl_export_ready(context: JobContext, export_file: Path, *, unregister_guard: bool = False) -> int:
    message = "WSL export file was not created or looks too small"
    if unregister_guard:
        message += "; unregister blocked"
    message += "."
    if not export_file.exists():
        raise RuntimeError(message)
    size = export_file.stat().st_size
    if size < MIN_WSL_EXPORT_BYTES:
        raise RuntimeError(message)
    context.log(f"WSL export preflight passed: {export_file} ({size} bytes)")
    return size


def infer_wsl_image_name(path: Path) -> str:
    text = path.name.lower()
    match = re.search(r"ubuntu[-_](\d{2}\.\d{2})", text)
    if match:
        return f"Ubuntu-{match.group(1)}"
    if "ubuntu" in text:
        return "Ubuntu"
    return path.stem


def timestamp() -> str:
    return datetime.now().strftime("%Y%m%d-%H%M%S")


def wsl_distro_options(root: Path | str | None = None) -> list[dict[str, str]]:
    try:
        text = _run_capture(["wsl.exe", "--list", "--quiet"], timeout=8.0)
    except Exception as exc:
        detail = str(exc).strip() or exc.__class__.__name__
        label = f"WSL is not available: {detail}"
        label_ru = f"WSL недоступна: {detail}"
        return [_option("", label, label_ru)]
    names = [line.strip() for line in text.splitlines() if line.strip()]
    if not names:
        return [_option("", "No WSL distributions found", "WSL-дистрибутивы не найдены")]
    return [_option(name, name, name) for name in names]


def wsl_online_distro_options(root: Path | str | None = None) -> list[dict[str, str]]:
    fallback = [
        "Ubuntu",
        "Ubuntu-26.04",
        "Ubuntu-24.04",
        "Ubuntu-22.04",
        "Debian",
        "kali-linux",
        "archlinux",
        "FedoraLinux-44",
        "FedoraLinux-43",
        "openSUSE-Tumbleweed",
        "openSUSE-Leap-16.0",
        "AlmaLinux-10",
    ]
    names: list[str] = []

    def add_name(candidate: str) -> None:
        name = candidate.strip().split()[0] if candidate.strip() else ""
        if not re.fullmatch(r"[A-Za-z0-9._-]+", name):
            return
        if name.upper() in {"NAME", "FRIENDLY"}:
            return
        if name not in names:
            names.append(name)

    try:
        text = _run_capture(["wsl.exe", "--list", "--online", "--quiet"], timeout=12.0)
        for line in text.splitlines():
            add_name(line)
    except Exception:
        names = []
    if not names:
        try:
            text = _run_capture(["wsl.exe", "--list", "--online"], timeout=12.0)
        except Exception as exc:
            text = ""
            names.extend(wsl_distribution_manifest_names())
            if not names:
                msg = f"WSL online list and manifest fetch failed: {exc.__class__.__name__}"
                return [_option(item, item, item) for item in fallback] + [_option("", msg, msg)]
        for raw in text.splitlines():
            line = raw.strip()
            if not line or line.lower().startswith(("the following", "name", "-")):
                continue
            add_name(line)
    if not names:
        names = wsl_distribution_manifest_names()
    if not names:
        names = fallback
    return [_option(name, name, name) for name in names]


def wsl_distribution_manifest_names(timeout: float = 8.0) -> list[str]:
    try:
        request = urllib.request.Request(WSL_DISTRIBUTION_MANIFEST_URL, headers={"User-Agent": "Audion-DevOps-Tools"})
        with urllib.request.urlopen(request, timeout=timeout) as response:
            data = json.loads(response.read().decode("utf-8", errors="replace"))
    except Exception:
        return []

    names: list[str] = []

    def add(value: Any) -> None:
        name = str(value or "").strip()
        if not re.fullmatch(r"[A-Za-z0-9._-]+", name):
            return
        if name not in names:
            names.append(name)

    modern = data.get("ModernDistributions", {})
    if isinstance(modern, dict):
        for distro_group in modern.values():
            if not isinstance(distro_group, list):
                continue
            for item in distro_group:
                if isinstance(item, dict):
                    add(item.get("Name"))

    legacy = data.get("Distributions", [])
    if isinstance(legacy, list):
        for item in legacy:
            if isinstance(item, dict):
                add(item.get("Name"))

    return names


def wsl_backup_file_options(root: Path | str | None = None) -> list[dict[str, str]]:
    files: list[Path] = []
    for wsl_root in wsl_candidate_roots(root):
        backup_root = wsl_root / "Backup"
        if backup_root.exists():
            files.extend(path for path in backup_root.rglob("*") if path.suffix.lower() in {".tar", ".vhd", ".vhdx", ".wsl"})
    if not files:
        return [_option("", "No WSL backup files found", "Файлы backup WSL не найдены")]
    files = sorted(files, key=lambda path: path.stat().st_mtime if path.exists() else 0, reverse=True)
    return [_option(path, str(path), str(path)) for path in files[:200]]


def vhdx_file_options(root: Path | str | None = None) -> list[dict[str, str]]:
    files: list[Path] = []
    for wsl_root in wsl_candidate_roots(root):
        if wsl_root.exists():
            files.extend(path for path in wsl_root.rglob("*.vhdx") if path.is_file())
    if not files:
        return [_option("", "No VHDX files found in WSL workspaces", "VHDX в WSL workspace не найдены")]
    files = sorted(files, key=lambda path: path.stat().st_mtime if path.exists() else 0, reverse=True)
    return [_option(path, str(path), str(path)) for path in files[:200]]


def _path_key(path: Path) -> str:
    return str(path.resolve()).lower()


def wsl_registered_vhdx_paths(root: Path | str | None = None) -> dict[str, str]:
    project_root = Path(root).resolve() if root else Path(__file__).resolve().parents[2]
    data = _json_capture(
        project_root,
        r"""
$rows = @(Get-ChildItem -LiteralPath 'HKCU:\Software\Microsoft\Windows\CurrentVersion\Lxss' -ErrorAction SilentlyContinue | ForEach-Object {
  $item = Get-ItemProperty -LiteralPath $_.PSPath -ErrorAction SilentlyContinue
  if ($item.DistributionName -and $item.BasePath) {
    [pscustomobject]@{ Name = [string]$item.DistributionName; BasePath = [string]$item.BasePath }
  }
})
$rows | ConvertTo-Json -Compress
""",
    )
    if data is None:
        return {}
    rows = data if isinstance(data, list) else [data]
    result: dict[str, str] = {}
    for row in rows:
        if not isinstance(row, dict):
            continue
        name = str(row.get("Name") or "").strip()
        base_text = str(row.get("BasePath") or "").strip()
        if not name or not base_text:
            continue
        base = Path(os.path.expandvars(base_text)).expanduser()
        vhdx = base if base.suffix.lower() in {".vhd", ".vhdx"} else base / "ext4.vhdx"
        result[_path_key(vhdx)] = name
    return result


def disk_options(root: Path | str | None = None) -> list[dict[str, str]]:
    project_root = Path(root).resolve() if root else Path(__file__).resolve().parents[2]
    data = _json_capture(
        project_root,
        (
            "$rows = Get-Disk | Sort-Object Number | ForEach-Object { "
            "[pscustomobject]@{Number=$_.Number; FriendlyName=$_.FriendlyName; BusType=[string]$_.BusType; "
            "SizeGB=[math]::Round($_.Size/1GB,1); PartitionStyle=[string]$_.PartitionStyle; "
            "Health=[string]$_.HealthStatus; IsSystem=[bool]$_.IsSystem; IsBoot=[bool]$_.IsBoot} }; "
            "$rows | ConvertTo-Json -Compress"
        ),
    )
    if data is None:
        return [_option("", "Get-Disk failed or PowerShell is unavailable", "Get-Disk не выполнен")]
    rows = data if isinstance(data, list) else [data]
    options: list[dict[str, str]] = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        number = row.get("Number", "")
        flags = []
        if row.get("IsSystem"):
            flags.append("System")
        if row.get("IsBoot"):
            flags.append("Boot")
        suffix = f" [{' / '.join(flags)}]" if flags else ""
        label = (
            f"Disk {number}: {row.get('FriendlyName', '')} | {row.get('BusType', '')} | "
            f"{row.get('SizeGB', '')} GB | {row.get('PartitionStyle', '')} | {row.get('Health', '')}{suffix}"
        )
        options.append(_option(number, label, label))
    return options or [_option("", "No disks returned by Get-Disk", "Get-Disk не вернул диски")]


def network_adapter_options(root: Path | str | None = None) -> list[dict[str, str]]:
    project_root = Path(root).resolve() if root else Path(__file__).resolve().parents[2]
    data = _json_capture(
        project_root,
        (
            "$rows = Get-NetAdapter | Sort-Object Name | ForEach-Object { "
            "[pscustomobject]@{Name=$_.Name; Status=[string]$_.Status; LinkSpeed=[string]$_.LinkSpeed; "
            "MacAddress=$_.MacAddress; InterfaceDescription=$_.InterfaceDescription} }; "
            "$rows | ConvertTo-Json -Compress"
        ),
    )
    if data is None:
        return [_option("", "Get-NetAdapter failed or PowerShell is unavailable", "Get-NetAdapter не выполнен")]
    rows = data if isinstance(data, list) else [data]
    options: list[dict[str, str]] = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        name = str(row.get("Name", "")).strip()
        if not name:
            continue
        label = f"{name} | {row.get('Status', '')} | {row.get('LinkSpeed', '')} | {row.get('InterfaceDescription', '')}"
        options.append(_option(name, label, label))
    return options or [_option("", "No adapters returned by Get-NetAdapter", "Get-NetAdapter не вернул адаптеры")]


def wifi_adapter_options(root: Path | str | None = None) -> list[dict[str, str]]:
    project_root = Path(root).resolve() if root else Path(__file__).resolve().parents[2]
    data = _json_capture(
        project_root,
        (
            "$rows = Get-NetAdapter | Where-Object { $_.NdisPhysicalMedium -match 'Wireless|Native802_11' -or "
            "$_.InterfaceDescription -match 'Wireless|Wi-Fi|WiFi|802.11|WLAN' -or $_.Name -match 'Wi-Fi|WiFi|WLAN|Wireless' } | "
            "Sort-Object Name | ForEach-Object { [pscustomobject]@{Name=$_.Name; Status=[string]$_.Status; "
            "LinkSpeed=[string]$_.LinkSpeed; InterfaceDescription=$_.InterfaceDescription} }; "
            "$rows | ConvertTo-Json -Compress"
        ),
    )
    if data is None:
        return network_adapter_options(project_root)
    rows = data if isinstance(data, list) else [data]
    options: list[dict[str, str]] = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        name = str(row.get("Name", "")).strip()
        if not name:
            continue
        label = f"{name} | {row.get('Status', '')} | {row.get('LinkSpeed', '')} | {row.get('InterfaceDescription', '')}"
        options.append(_option(name, label, label))
    return options or network_adapter_options(project_root)


def wifi_profile_options(root: Path | str | None = None) -> list[dict[str, str]]:
    try:
        text = _run_capture(["netsh.exe", "wlan", "show", "profiles"], timeout=8.0)
    except Exception as exc:
        msg = f"netsh wlan failed: {exc.__class__.__name__}"
        return [_option("", msg, msg)]
    profiles: list[str] = []
    for line in text.splitlines():
        if ":" not in line:
            continue
        name = line.split(":", 1)[1].strip()
        if name and name not in profiles:
            profiles.append(name)
    if not profiles:
        return [_option("", "No Wi-Fi profiles found", "Wi-Fi профили не найдены")]
    return [_option(name, name, name) for name in profiles]


def network_backup_snapshot_paths(root: Path | str | None = None) -> list[Path]:
    project_root = Path(root).resolve() if root else Path(__file__).resolve().parents[2]
    backup_root = project_root / "backup"
    if not backup_root.exists():
        return []
    snapshots = [path for path in backup_root.iterdir() if path.is_dir() and path.name.startswith("network_backup_")]
    return sorted(snapshots, key=lambda path: path.stat().st_mtime if path.exists() else 0, reverse=True)


def network_backup_snapshot_options(root: Path | str | None = None) -> list[dict[str, str]]:
    snapshots = network_backup_snapshot_paths(root)
    if not snapshots:
        return [_option("", "No Network Cleaner backups found", "Backup Network Cleaner не найдены")]
    options: list[dict[str, str]] = []
    for path in snapshots[:100]:
        stamp = ""
        try:
            stamp = datetime.fromtimestamp(path.stat().st_mtime).strftime("%Y-%m-%d %H:%M:%S")
        except Exception:
            stamp = ""
        label = f"{stamp} | {path.name}" if stamp else path.name
        options.append(_option(path, label, label))
    return options


def runtime_status(context: JobContext) -> dict[str, object]:
    context.log(f"Audion DevOps Tools root: {context.paths.root}")
    context.log(f"Bundle root: {bundle_root(context)}")
    portable = context.paths.system_core / "powershell" / "pwsh.exe"
    context.log(f"Portable PowerShell: {portable}")
    context.log(f"Portable PowerShell exists: {portable.exists()}")
    resolved = resolve_pwsh(context.paths.root)
    context.log(f"Resolved PowerShell: {resolved}")
    run_process(context, [resolved, "--version"], cwd=context.paths.root, check=False, progress_seconds=10)
    context.progress(1.0)
    return {"resolved": resolved, "portable_exists": portable.exists()}


def _windows_long_paths_value() -> str:
    if os.name != "nt":
        return "not_windows"
    try:
        import winreg

        key_path = r"SYSTEM\CurrentControlSet\Control\FileSystem"
        with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, key_path) as key:
            value, _kind = winreg.QueryValueEx(key, "LongPathsEnabled")
        return "ON" if int(value) == 1 else "OFF"
    except FileNotFoundError:
        return "OFF"
    except Exception as exc:
        return f"unknown ({exc.__class__.__name__})"


def _git_config_value(scope: str) -> str:
    git = shutil.which("git.exe") or shutil.which("git")
    if not git:
        return "git not found"
    result = subprocess.run(
        [git, "config", f"--{scope}", "--get", "core.longpaths"],
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )
    value = result.stdout.strip()
    if result.returncode == 0 and value:
        return value
    if result.returncode == 1:
        return "not set"
    detail = (result.stderr or result.stdout).strip()
    return f"error ({detail or result.returncode})"


def windows_long_paths(context: JobContext) -> dict[str, object]:
    mode = str(context.operation.parameters.get("mode") or "status").strip().lower()
    if mode == "enable_windows":
        context.log("Enabling Win32 long paths for longPathAware applications.")
        context.log("This sets HKLM LongPathsEnabled=1; individual apps still need longPathAware support.")
        script = """
$ErrorActionPreference = 'Stop'
$path = 'HKLM:\\SYSTEM\\CurrentControlSet\\Control\\FileSystem'
New-ItemProperty -Path $path -Name 'LongPathsEnabled' -Value 1 -PropertyType DWORD -Force | Out-Null
$value = (Get-ItemProperty -Path $path -Name 'LongPathsEnabled').LongPathsEnabled
Write-Host "Windows LongPathsEnabled: $value"
"""
        run_ps_command(context, script, progress_seconds=60.0, elevated=True)
    elif mode == "enable_git":
        git = shutil.which("git.exe") or shutil.which("git")
        if not git:
            raise RuntimeError("git was not found in PATH.")
        context.log("Enabling Git for Windows long paths for the current user.")
        run_process(context, [git, "config", "--global", "core.longpaths", "true"], cwd=context.paths.root, progress_seconds=20.0)
    elif mode != "status":
        raise RuntimeError(f"Unsupported Windows long paths mode: {mode}")

    windows_value = _windows_long_paths_value()
    git_global = _git_config_value("global")
    git_system = _git_config_value("system")
    context.log(f"Windows LongPathsEnabled: {windows_value}")
    context.log(f"Git global core.longpaths: {git_global}")
    context.log(f"Git system core.longpaths: {git_system}")
    context.log("Note: Windows long paths require both LongPathsEnabled=1 and longPathAware support in the application.")
    context.progress(1.0)
    return {
        "mode": mode,
        "windows_long_paths": windows_value,
        "git_global_core_longpaths": git_global,
        "git_system_core_longpaths": git_system,
    }


def install_portable_powershell(context: JobContext) -> dict[str, object]:
    script = context.paths.root / "install" / "Install-Portable-PowerShell.cmd"
    run_cmd_file(context, script, ["/NOPAUSE"], cwd=context.paths.root, progress_seconds=180.0)
    return {"script": str(script)}


def preflight_status(context: JobContext) -> dict[str, object]:
    script = context.paths.system_core / "scripts" / "Preflight-Status.ps1"
    run_ps1(context, script, cwd=context.paths.root, progress_seconds=90.0, check=False)
    return {"status": "preflight"}


def network_cleaner(context: JobContext) -> dict[str, object]:
    mode = str(context.operation.parameters.get("mode", "Status")).strip() or "Status"
    script = project_tool_dir(context, "network_cleaner") / "system_core" / "Audion_Network_Cleaner.ps1"
    context.log(f"Network Cleaner mode: {mode}")
    elevated = mode.lower() not in {"openbackup", "help"}
    run_ps1(context, script, {"Mode": mode}, cwd=script.parents[1], progress_seconds=900.0, elevated=elevated)
    return {"mode": mode}


def windows_proxy_tool(context: JobContext) -> dict[str, object]:
    action = str(context.operation.parameters.get("action") or "Status").strip() or "Status"
    allowed = {"Status", "DisableUserProxy", "ResetWinHttp"}
    if action not in allowed:
        raise RuntimeError(f"Unsupported Windows proxy action: {action}")
    script = project_tool_dir(context, "disable_windows_proxy") / "system_core" / "proxy" / "Proxy-Tool.ps1"
    context.log(f"Windows Proxy Tool action: {action}")
    elevated = action == "ResetWinHttp"
    run_ps1(context, script, {"Action": action}, cwd=script.parent, progress_seconds=180.0, elevated=elevated)
    return {"action": action}


def network_restore(context: JobContext) -> dict[str, object]:
    params = context.operation.parameters
    restore_mode = str(params.get("restore_mode") or "latest").strip().lower()
    script = project_tool_dir(context, "network_cleaner") / "system_core" / "Audion_Network_Cleaner.ps1"

    if restore_mode == "selected":
        selected = resolve_user_path(context, params.get("network_restore_snapshot"), default=script.parents[1] / "backup")
        snapshots = network_backup_snapshot_paths(context.paths.root)
        selected_resolved = selected.resolve()
        index = next((idx + 1 for idx, path in enumerate(snapshots) if path.resolve() == selected_resolved), 0)
        if index <= 0:
            raise RuntimeError(f"Selected Network Cleaner backup is not in the current snapshot list: {selected}")
        context.log(f"Network restore snapshot: {selected}")
        input_text = f"{index}\nRESTORE\n"
        mode = "RestoreSelect"
    else:
        context.log("Network restore snapshot: latest")
        input_text = "RESTORE\n"
        mode = "RestoreLatest"

    context.log("Network restore will create a fresh pre-restore backup first.")
    run_ps1(context, script, {"Mode": mode}, cwd=script.parents[1], progress_seconds=900.0, elevated=True, input_text=input_text)
    return {"mode": mode}


def network_wifi_status(context: JobContext) -> dict[str, object]:
    params = context.operation.parameters
    profile = str(params.get("wifi_profile_override") or params.get("wifi_profile") or "").strip()
    adapter = str(params.get("wifi_adapter") or "").strip()
    context.log("Wi-Fi interfaces and profiles")
    run_process(context, ["netsh.exe", "wlan", "show", "interfaces"], cwd=context.paths.root, check=False, progress_seconds=20.0)
    profiles_command = ["netsh.exe", "wlan", "show", "profiles"]
    if adapter:
        # The group pickers are shared, so honour them here instead of always
        # dumping every adapter and every profile.
        profiles_command.append(f"interface={adapter}")
        context.log(f"Wi-Fi adapter: {adapter}")
    run_process(context, profiles_command, cwd=context.paths.root, check=False, progress_seconds=20.0)
    if profile:
        context.log(f"Wi-Fi profile details: {profile}")
        # No key=clear here: the status view must never print a Wi-Fi password.
        run_process(
            context,
            ["netsh.exe", "wlan", "show", "profile", f"name={profile}"],
            cwd=context.paths.root,
            check=False,
            progress_seconds=20.0,
        )
    return {"status": "wifi", "profile": profile, "adapter": adapter}


def wifi_connect(context: JobContext) -> dict[str, object]:
    params = context.operation.parameters
    profile = str(params.get("wifi_profile_override") or params.get("wifi_profile") or "").strip()
    if not profile:
        raise RuntimeError("Wi-Fi profile is empty.")
    adapter = str(params.get("wifi_adapter") or "").strip()
    command = ["netsh.exe", "wlan", "connect", f"name={profile}"]
    if adapter:
        command.append(f"interface={adapter}")
    run_process(context, command, cwd=context.paths.root, progress_seconds=40.0)
    return {"profile": profile, "adapter": adapter}


def wifi_profile_connection_mode(context: JobContext) -> dict[str, object]:
    params = context.operation.parameters
    profile = str(params.get("wifi_profile_override") or params.get("wifi_profile") or "").strip()
    mode = str(params.get("connection_mode") or "auto").strip().lower()
    if not profile:
        raise RuntimeError("Wi-Fi profile is empty.")
    if mode not in {"auto", "manual"}:
        raise RuntimeError(f"Unsupported Wi-Fi connection mode: {mode}")
    context.log(f"Wi-Fi profile: {profile}")
    context.log(f"Connection mode: {mode}")
    run_process(
        context,
        ["netsh.exe", "wlan", "set", "profileparameter", f"name={profile}", f"connectionmode={mode}"],
        cwd=context.paths.root,
        progress_seconds=40.0,
    )
    return {"profile": profile, "connection_mode": mode}


def wifi_sticky_pair(context: JobContext) -> dict[str, object]:
    params = context.operation.parameters
    target = str(params.get("auto_wifi_profile_override") or params.get("auto_wifi_profile") or "").strip()
    other = str(params.get("manual_wifi_profile_override") or params.get("manual_wifi_profile") or "").strip()
    adapter = str(params.get("wifi_adapter") or "").strip()
    connect_target = bool(params.get("connect_auto_profile", True))
    if not target:
        raise RuntimeError("Auto Wi-Fi profile is empty.")
    if not other:
        raise RuntimeError("Manual Wi-Fi profile is empty.")
    if target == other:
        raise RuntimeError("Auto and manual Wi-Fi profiles must be different.")
    context.log(f"Auto Wi-Fi profile: {target}")
    context.log(f"Manual Wi-Fi profile: {other}")
    if adapter:
        context.log(f"Wi-Fi adapter: {adapter}")
    lines = [
        "$ErrorActionPreference = 'Stop'",
        f"$target = {ps_quote(target)}",
        f"$other = {ps_quote(other)}",
        f"$adapter = {ps_quote(adapter)}",
        f"$connectTarget = ${str(connect_target).lower()}",
        "if ($connectTarget) {",
        "  $connectArgs = @('wlan', 'connect', \"name=$target\")",
        "  if ($adapter) { $connectArgs += \"interface=$adapter\" }",
        "  & netsh.exe @connectArgs",
        "  if ($LASTEXITCODE -ne 0) { throw \"netsh wlan connect failed with exit code $LASTEXITCODE\" }",
        "}",
        "$pairs = @(@($target, 'auto'), @($other, 'manual'))",
        "foreach ($pair in $pairs) {",
        "  $profile = [string]$pair[0]",
        "  $mode = [string]$pair[1]",
        "  Write-Host \"Setting Wi-Fi profile '$profile' connectionmode=$mode\"",
        "  & netsh.exe wlan set profileparameter \"name=$profile\" \"connectionmode=$mode\"",
        "  if ($LASTEXITCODE -ne 0) { throw \"netsh wlan set profileparameter failed for '$profile' with exit code $LASTEXITCODE\" }",
        "}",
        "Write-Host ''",
        "& netsh.exe wlan show interfaces",
    ]
    run_ps_command(context, "\n".join(lines), progress_seconds=80.0)
    return {"auto_profile": target, "manual_profile": other, "adapter": adapter, "connect": connect_target}


def smb_network_login(context: JobContext) -> dict[str, object]:
    params = context.operation.parameters
    login = params.get("smb_login")
    login_data = login if isinstance(login, dict) else {}
    computer = str(params.get("smb_computer") or login_data.get("computer_manual") or login_data.get("computer") or "").strip().strip("\\/")
    user_input = str(params.get("smb_user") or login_data.get("user_manual") or login_data.get("user") or "").strip()
    open_explorer = bool(params.get("smb_open_explorer", True))

    if not computer:
        raise RuntimeError("SMB computer name is empty.")
    if not user_input:
        raise RuntimeError("SMB user name is empty.")
    if re.search(r'[<>:"/\\|?*]', computer):
        raise RuntimeError(f"SMB computer name contains unsupported characters: {computer}")
    if "\\" in user_input or "@" in user_input:
        display_user = user_input
    else:
        display_user = f"{computer}\\{user_input}"

    context.report_dir.mkdir(parents=True, exist_ok=True)
    script = context.report_dir / "smb_network_login.ps1"
    script.write_text(
        "\n".join(
            [
                "$ErrorActionPreference = 'Continue'",
                "$PSNativeCommandUseErrorActionPreference = $false",
                f"$Computer = {ps_quote(computer)}",
                f"$UserInput = {ps_quote(user_input)}",
                f"$OpenExplorer = ${str(open_explorer).lower()}",
                "$User = if ($UserInput -match '\\\\|@') { $UserInput } else { \"$Computer\\$UserInput\" }",
                "$Target = \"\\\\$Computer\\IPC$\"",
                "Write-Host '=== Audion SMB network login ==='",
                "Write-Host ('Computer : ' + $Computer)",
                "Write-Host ('Target   : ' + $Target)",
                "Write-Host ('User     : ' + $User)",
                "Write-Host ''",
                "Write-Host 'Type the Windows account password when net use asks for it.'",
                "Write-Host 'The password is entered in this console and is not stored by DevOps Tools.'",
                "Write-Host ''",
                "& net.exe use $Target /delete /y *> $null",
                "& net.exe use $Target /user:$User * /persistent:yes",
                "$Code = if ($LASTEXITCODE -is [int]) { $LASTEXITCODE } else { 0 }",
                "Write-Host ''",
                "if ($Code -eq 0) {",
                "  Write-Host 'SMB session is ready.'",
                "  Write-Host ''",
                "  & net.exe view (\"\\\\\" + $Computer)",
                "  if ($OpenExplorer) { Start-Process explorer.exe (\"\\\\\" + $Computer) }",
                "} else {",
                "  Write-Host ('net use failed with exit code: ' + $Code)",
                "  Write-Host 'Common codes: 53 path/name not found, 5 access denied, 86 wrong password, 1219 existing session with another user.'",
                "}",
                "Write-Host ''",
                "Read-Host 'Press Enter to close this window'",
                "exit $Code",
                "",
            ]
        ),
        encoding="utf-8",
    )

    pwsh = resolve_pwsh(context.paths.root)
    context.log("Launching external SMB login console.")
    context.log(f"SMB target: \\\\{computer}\\IPC$")
    context.log(f"SMB user: {display_user}")
    context.log("Password prompt stays in the external console; DevOps Tools does not receive or store it.")
    if os.name == "nt":
        subprocess.Popen(
            ["cmd.exe", "/d", "/c", "start", "", pwsh, *PWSH_ARGS, "-File", str(script)],
            cwd=str(context.paths.root),
        )
    else:
        subprocess.Popen([pwsh, *PWSH_ARGS, "-File", str(script)], cwd=str(context.paths.root))
    context.progress(1.0)
    return {"computer": computer, "user": display_user, "script": str(script)}


def wifi_export_profiles(context: JobContext) -> dict[str, object]:
    params = context.operation.parameters
    target = resolve_user_path(context, params.get("target_folder"), default=context.paths.output / "wifi_profiles")
    target.mkdir(parents=True, exist_ok=True)
    include_keys = bool(params.get("include_keys", False))
    # The profile and adapter pickers are shared by the whole Wi-Fi group, so an
    # export honours them when they are set and exports everything when they are not.
    profile = str(params.get("wifi_profile_override") or params.get("wifi_profile") or "").strip()
    adapter = str(params.get("wifi_adapter") or "").strip()
    command = ["netsh.exe", "wlan", "export", "profile", f"folder={target}"]
    if profile:
        command.append(f"name={profile}")
        context.log(f"Wi-Fi export profile: {profile}")
    else:
        context.log("Wi-Fi export scope: all profiles")
    if adapter:
        command.append(f"interface={adapter}")
        context.log(f"Wi-Fi export adapter: {adapter}")
    if include_keys:
        command.append("key=clear")
        context.log("WARNING: Wi-Fi keys will be exported in clear text inside XML files.")
    run_process(context, command, cwd=context.paths.root, progress_seconds=60.0)
    return {"target": str(target), "include_keys": include_keys, "profile": profile, "adapter": adapter}


def wifi_import_profiles(context: JobContext) -> dict[str, object]:
    params = context.operation.parameters
    source_kind = str(params.get("source_kind") or "file").strip().lower()
    if source_kind == "folder":
        source = resolve_user_path(context, params.get("import_profile_folder"), default=context.paths.input)
        if not source.exists() or not source.is_dir():
            raise RuntimeError(f"Wi-Fi profile folder was not found: {source}")
        files = sorted(path for path in source.glob("*.xml") if path.is_file())
    else:
        source = resolve_user_path(context, params.get("import_profile_xml"), default=context.paths.input)
        if not source.exists() or not source.is_file():
            raise RuntimeError(f"Wi-Fi profile XML was not found: {source}")
        files = [source]
    if not files:
        raise RuntimeError(f"No Wi-Fi profile XML files found: {source}")

    scope = str(params.get("import_user_scope") or "current").strip().lower()
    if scope not in {"current", "all"}:
        scope = "current"
    adapter = str(params.get("wifi_adapter") or "").strip()
    context.log(f"Wi-Fi import source: {source}")
    context.log(f"Wi-Fi import user scope: {scope}")
    if adapter:
        context.log(f"Wi-Fi import adapter: {adapter}")

    elevated = scope == "all"
    lines = [
        "$ErrorActionPreference = 'Stop'",
        f"$profiles = {ps_array([str(path) for path in files])}",
        f"$scope = {ps_quote(scope)}",
        f"$adapter = {ps_quote(adapter)}",
        "$imported = 0",
        "foreach ($profile in $profiles) {",
        "  Write-Host \"Importing Wi-Fi profile: $profile\"",
        "  $args = @('wlan', 'add', 'profile', \"filename=$profile\", \"user=$scope\")",
        "  if ($adapter) { $args += \"interface=$adapter\" }",
        "  & netsh.exe @args",
        "  if ($LASTEXITCODE -ne 0) { throw \"netsh wlan add profile failed with exit code $LASTEXITCODE\" }",
        "  $imported += 1",
        "}",
        "Write-Host \"Imported Wi-Fi profile XML files: $imported\"",
    ]
    run_ps_command(context, "\n".join(lines), progress_seconds=max(60.0, 10.0 * len(files)), elevated=elevated)
    return {"source": str(source), "count": len(files), "scope": scope}


def network_adapter_action(context: JobContext) -> dict[str, object]:
    params = context.operation.parameters
    adapter = str(params.get("adapter") or "").strip()
    action = str(params.get("adapter_action") or "restart").strip().lower()
    if not adapter:
        raise RuntimeError("Adapter is empty.")
    allowed_actions = {"enable", "disable", "restart"}
    if action not in allowed_actions:
        raise RuntimeError(f"Unsupported adapter action: {action}. Allowed: {', '.join(sorted(allowed_actions))}.")
    script = f"""
$ErrorActionPreference = 'Stop'
$adapter = {ps_quote(adapter)}
Write-Host "Adapter: $adapter"
switch ('{action}') {{
  'enable' {{ Enable-NetAdapter -Name $adapter -Confirm:$false }}
  'disable' {{ Disable-NetAdapter -Name $adapter -Confirm:$false }}
  'restart' {{
    Disable-NetAdapter -Name $adapter -Confirm:$false
    Start-Sleep -Seconds 2
    Enable-NetAdapter -Name $adapter -Confirm:$false
  }}
  default {{ throw 'Unsupported adapter action: {action}' }}
}}
Get-NetAdapter -Name $adapter | Format-List Name,Status,LinkSpeed,InterfaceDescription | Out-String -Width 220
"""
    run_ps_command(context, script, progress_seconds=80.0, elevated=True)
    return {"adapter": adapter, "action": action}


def lan_wifi_switch(context: JobContext) -> dict[str, object]:
    params = context.operation.parameters
    mode = str(params.get("switch_mode") or "wifi_only").strip().lower()
    lan_adapter = str(params.get("lan_adapter") or "").strip()
    wifi_adapter = str(params.get("wifi_adapter") or "").strip()
    wifi_profile = str(params.get("wifi_profile_override") or params.get("wifi_profile") or "").strip()
    if not lan_adapter and not wifi_adapter:
        raise RuntimeError("Select at least one LAN or Wi-Fi adapter.")
    lines = [
        "$ErrorActionPreference = 'Stop'",
        f"$lan = {ps_quote(lan_adapter)}",
        f"$wifi = {ps_quote(wifi_adapter)}",
        f"$profile = {ps_quote(wifi_profile)}",
        "Write-Host \"LAN adapter: $lan\"",
        "Write-Host \"Wi-Fi adapter: $wifi\"",
        "Write-Host \"Wi-Fi profile: $profile\"",
    ]
    if mode == "lan_only":
        lines.extend([
            "if ($lan) { Enable-NetAdapter -Name $lan -Confirm:$false }",
            "if ($wifi) { Disable-NetAdapter -Name $wifi -Confirm:$false }",
        ])
    elif mode == "wifi_only":
        lines.extend([
            "if ($lan) { Disable-NetAdapter -Name $lan -Confirm:$false }",
            "if ($wifi) { Enable-NetAdapter -Name $wifi -Confirm:$false }",
            "Start-Sleep -Seconds 2",
            "if ($profile) { if ($wifi) { netsh wlan connect name=\"$profile\" interface=\"$wifi\" } else { netsh wlan connect name=\"$profile\" } }",
        ])
    elif mode == "both_on":
        lines.extend([
            "if ($lan) { Enable-NetAdapter -Name $lan -Confirm:$false }",
            "if ($wifi) { Enable-NetAdapter -Name $wifi -Confirm:$false }",
            "Start-Sleep -Seconds 2",
            "if ($profile) { if ($wifi) { netsh wlan connect name=\"$profile\" interface=\"$wifi\" } else { netsh wlan connect name=\"$profile\" } }",
        ])
    elif mode == "cycle_wifi":
        lines.extend([
            "if (-not $wifi) { throw 'Wi-Fi adapter is required for cycle_wifi.' }",
            "Disable-NetAdapter -Name $wifi -Confirm:$false",
            "Start-Sleep -Seconds 3",
            "Enable-NetAdapter -Name $wifi -Confirm:$false",
            "Start-Sleep -Seconds 3",
            "if ($profile) { netsh wlan connect name=\"$profile\" interface=\"$wifi\" }",
        ])
    else:
        raise RuntimeError(f"Unsupported switch mode: {mode}")
    lines.extend([
        "Write-Host ''",
        "Get-NetAdapter | Sort-Object Name | Format-Table Name,Status,LinkSpeed,InterfaceDescription -AutoSize | Out-String -Width 220",
    ])
    run_ps_command(context, "\n".join(lines), progress_seconds=120.0, elevated=True)
    return {"mode": mode, "lan": lan_adapter, "wifi": wifi_adapter, "profile": wifi_profile}


def wsl_toolkit(context: JobContext) -> dict[str, object]:
    params = context.operation.parameters
    action = str(params.get("action", "list")).strip() or "list"
    name = str(params.get("wsl_name_override") or params.get("wsl_name") or "").strip()
    context.log(f"WSL action: {action}")
    if name:
        context.log(f"WSL distro: {name}")

    if action == "list":
        result = run_process(context, ["wsl.exe", "--list", "--verbose"], cwd=context.paths.root, check=False, progress_seconds=30.0)
        if result.exit_code != 0:
            context.log("WSL is not ready yet. Install/enable WSL first, reboot if requested, or install a local .wsl image.")
    elif action == "status":
        result = run_process(context, ["wsl.exe", "--status"], cwd=context.paths.root, check=False, progress_seconds=30.0)
        if result.exit_code != 0:
            context.log("WSL is not ready yet. Install/enable WSL first, reboot if requested, or install a local .wsl image.")
    elif action == "shutdown":
        run_process(context, ["wsl.exe", "--shutdown"], cwd=context.paths.root, progress_seconds=60.0)
    elif action == "terminate":
        if not name:
            raise RuntimeError("WSL distro name is empty.")
        run_process(context, ["wsl.exe", "--terminate", name], cwd=context.paths.root, progress_seconds=60.0)
    elif action == "backup":
        if not name:
            raise RuntimeError("WSL distro name is empty.")
        wsl_root = ensure_wsl_workspace(context)
        backup_dir = resolve_user_path(context, params.get("backup_dir"), default=wsl_root / "Backup")
        backup_dir.mkdir(parents=True, exist_ok=True)
        fmt = str(params.get("format") or "tar").strip().lower()
        ext = "vhdx" if fmt == "vhd" else "tar"
        out_dir = backup_dir / safe_wsl_file_part(name)
        out_dir.mkdir(parents=True, exist_ok=True)
        out_file = out_dir / f"{safe_wsl_file_part(name)}_{timestamp()}.{ext}"
        run_process(context, ["wsl.exe", "--terminate", name], cwd=context.paths.root, check=False, progress_seconds=20.0)
        if fmt == "vhd":
            context.log("Shutting down WSL before VHD export to release the backing disk.")
            run_process(context, ["wsl.exe", "--shutdown"], cwd=context.paths.root, check=False, progress_seconds=20.0)
        command = ["wsl.exe", "--export", name, str(out_file)]
        if fmt == "vhd":
            command.append("--vhd")
        run_process(context, command, cwd=context.paths.root, progress_seconds=1800.0)
        assert_wsl_export_ready(context, out_file)
        context.log(f"Backup created: {out_file}")
    elif action == "clone":
        if not name:
            raise RuntimeError("WSL distro name is empty.")
        new_name = str(params.get("new_name") or "").strip()
        if not new_name:
            raise RuntimeError("New distro name is empty.")
        location = resolve_user_path(context, params.get("location"), default=wsl_workspace_root(context) / "VHDX" / safe_wsl_file_part(new_name))
        location.mkdir(parents=True, exist_ok=True)
        backup_dir = resolve_user_path(context, params.get("backup_dir"), default=ensure_wsl_workspace(context) / "Backup" / "_temp")
        backup_dir.mkdir(parents=True, exist_ok=True)
        tmp_tar = backup_dir / f"{safe_wsl_file_part(name)}_{timestamp()}.tar"
        run_process(context, ["wsl.exe", "--terminate", name], cwd=context.paths.root, check=False, progress_seconds=20.0)
        run_process(context, ["wsl.exe", "--export", name, str(tmp_tar)], cwd=context.paths.root, progress_seconds=1800.0)
        assert_wsl_export_ready(context, tmp_tar)
        run_process(context, ["wsl.exe", "--import", new_name, str(location), str(tmp_tar), "--version", "2"], cwd=context.paths.root, progress_seconds=1800.0)
        context.log(f"Cloned '{name}' -> '{new_name}'")
        context.log(f"Install location: {location}")
    elif action == "move":
        if not name:
            raise RuntimeError("WSL distro name is empty.")
        location = resolve_user_path(context, params.get("location"), default=wsl_workspace_root(context) / "VHDX" / safe_wsl_file_part(name))
        location.mkdir(parents=True, exist_ok=True)
        backup_dir = resolve_user_path(context, params.get("backup_dir"), default=ensure_wsl_workspace(context) / "Backup" / "_temp")
        backup_dir.mkdir(parents=True, exist_ok=True)
        tmp_tar = backup_dir / f"{safe_wsl_file_part(name)}_{timestamp()}.tar"
        run_process(context, ["wsl.exe", "--terminate", name], cwd=context.paths.root, check=False, progress_seconds=20.0)
        run_process(context, ["wsl.exe", "--export", name, str(tmp_tar)], cwd=context.paths.root, progress_seconds=1800.0)
        assert_wsl_export_ready(context, tmp_tar, unregister_guard=True)
        run_process(context, ["wsl.exe", "--unregister", name], cwd=context.paths.root, progress_seconds=120.0)
        run_process(context, ["wsl.exe", "--import", name, str(location), str(tmp_tar), "--version", "2"], cwd=context.paths.root, progress_seconds=1800.0)
        context.log(f"Moved '{name}' to: {location}")
    elif action == "delete":
        if not name:
            raise RuntimeError("WSL distro name is empty.")
        run_process(context, ["wsl.exe", "--terminate", name], cwd=context.paths.root, check=False, progress_seconds=20.0)
        run_process(context, ["wsl.exe", "--unregister", name], cwd=context.paths.root, progress_seconds=120.0)
    elif action == "importinplace":
        if not name:
            raise RuntimeError("WSL distro name is empty.")
        vhdx = resolve_user_path(context, params.get("vhdx_path_manual") or params.get("vhdx_path"), default=wsl_workspace_root(context) / "VHDX")
        if not vhdx.exists():
            raise RuntimeError(f"VHDX file was not found: {vhdx}")
        run_process(context, ["wsl.exe", "--shutdown"], cwd=context.paths.root, check=False, progress_seconds=30.0)
        run_process(context, ["wsl.exe", "--import-in-place", name, str(vhdx)], cwd=context.paths.root, progress_seconds=300.0)
    elif action == "restorefrombackup":
        if not name:
            raise RuntimeError("WSL distro name is empty.")
        location = resolve_user_path(context, params.get("location"), default=wsl_workspace_root(context) / "VHDX" / safe_wsl_file_part(name))
        backup_file = resolve_user_path(context, params.get("backup_file_manual") or params.get("backup_file"), default=wsl_workspace_root(context) / "Backup")
        if not backup_file.exists():
            raise RuntimeError(f"Backup file was not found: {backup_file}")
        location.mkdir(parents=True, exist_ok=True)
        ext = backup_file.suffix.lower()
        command = ["wsl.exe", "--import", name, str(location), str(backup_file)]
        if ext in {".vhd", ".vhdx"}:
            command.append("--vhd")
        else:
            command.extend(["--version", "2"])
        run_process(context, ["wsl.exe", "--shutdown"], cwd=context.paths.root, check=False, progress_seconds=30.0)
        run_process(context, command, cwd=context.paths.root, progress_seconds=1800.0)
    else:
        raise RuntimeError(f"Unsupported WSL action: {action}")
    return {"action": action, "name": name}


def wsl_system_status(context: JobContext) -> dict[str, object]:
    script = r"""
$ErrorActionPreference = 'Continue'
Write-Host "=== Windows WSL features ==="
$isAdmin = ([Security.Principal.WindowsPrincipal] [Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
Write-Host "Administrator: $isAdmin"
if ($isAdmin) {
  $features = @('Microsoft-Windows-Subsystem-Linux', 'VirtualMachinePlatform')
  $featureRows = foreach ($feature in $features) {
    try {
      Get-WindowsOptionalFeature -Online -FeatureName $feature |
        Select-Object FeatureName, State
    } catch {
      [pscustomobject]@{ FeatureName = $feature; State = "ERROR: $($_.Exception.Message)" }
    }
  }
  $featureRows | Format-Table FeatureName,State -AutoSize | Out-String -Width 180
} else {
  Write-Host "Windows optional feature state requires Administrator rights; skipping feature table."
}
Write-Host "=== WSL status ==="
& wsl.exe --status
if ($LASTEXITCODE -ne 0) { Write-Host "WSL status exit code: $LASTEXITCODE" }
Write-Host ""
Write-Host "=== Installed distributions ==="
& wsl.exe --list --verbose
if ($LASTEXITCODE -ne 0) { Write-Host "WSL list exit code: $LASTEXITCODE" }
exit 0
"""
    run_ps_command(context, script, check=False, progress_seconds=60.0)
    return {"status": "wsl_system"}


def wsl_enable_features(context: JobContext) -> dict[str, object]:
    script = r"""
$ErrorActionPreference = 'Stop'
Write-Host "Enabling Windows Subsystem for Linux..."
dism.exe /online /enable-feature /featurename:Microsoft-Windows-Subsystem-Linux /all /norestart
Write-Host ""
Write-Host "Enabling VirtualMachinePlatform..."
dism.exe /online /enable-feature /featurename:VirtualMachinePlatform /all /norestart
Write-Host ""
Write-Host "Setting WSL default version to 2..."
wsl --set-default-version 2
Write-Host ""
Write-Host "Done. A Windows reboot can still be required before first distro install."
"""
    run_ps_command(context, script, progress_seconds=300.0, elevated=True)
    return {"enabled": True}


def wsl_update(context: JobContext) -> dict[str, object]:
    run_process(context, ["wsl.exe", "--update"], cwd=context.paths.root, progress_seconds=300.0)
    return {"updated": True}


def wsl_list_online(context: JobContext) -> dict[str, object]:
    result = run_process(context, ["wsl.exe", "--list", "--online"], cwd=context.paths.root, check=False, progress_seconds=60.0)
    if result.exit_code != 0:
        context.log("WSL online catalog is not available from this Windows state yet.")
        context.log("Run 'Install WSL2 in Windows' with Administrator rights, reboot if requested, or install a local .wsl image from the WSL module.")
    return {"online": result.exit_code == 0, "exit_code": result.exit_code}


def wsl_default_install_location(context: JobContext, distro: str) -> Path:
    return wsl_workspace_root(context) / "VHDX" / safe_wsl_file_part(distro)


def wsl_selected_distro(context: JobContext) -> str:
    params = context.operation.parameters
    name = str(params.get("wsl_name_override") or params.get("wsl_name") or "").strip()
    if not name:
        raise RuntimeError("WSL distro name is empty.")
    return name


def linux_user_or_default(context: JobContext) -> str:
    return str(context.operation.parameters.get("linux_username") or "").strip()


def validate_linux_username(username: str) -> None:
    if not re.fullmatch(r"[a-z_][a-z0-9_-]{0,31}", username):
        raise RuntimeError("Linux username must match: [a-z_][a-z0-9_-]{0,31}")


def read_wsl_asset(*parts: str) -> str:
    path = Path(__file__).resolve().parents[1] / "wsl_assets" / Path(*parts)
    if not path.exists():
        raise RuntimeError(f"WSL asset was not found: {path}")
    return path.read_text(encoding="utf-8")


def run_wsl_script(
    context: JobContext,
    distro: str,
    script: str,
    *,
    user: str | None = "root",
    check: bool = True,
    progress_seconds: float = 600.0,
) -> ProcessResult:
    command = ["wsl.exe", "-d", distro]
    if user:
        command.extend(["--user", user])
    command.extend(["--", "bash", "-s"])
    if not script.endswith("\n"):
        script += "\n"
    return run_process(
        context,
        command,
        cwd=context.paths.root,
        input_text=script,
        check=check,
        progress_seconds=progress_seconds,
    )


def bash_single_quote(value: str) -> str:
    return "'" + value.replace("'", "'\"'\"'") + "'"


def bash_array(values: list[str]) -> str:
    return " ".join(bash_single_quote(value) for value in values)


def parse_package_text(raw: Any) -> list[str]:
    items: list[str] = []
    for token in re.split(r"[\s,;]+", str(raw or "")):
        name = token.strip()
        if not name:
            continue
        if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9+_.-]*", name):
            raise RuntimeError(f"Unsupported package name: {name}")
        if name not in items:
            items.append(name)
    return items


def wsl_apt_network_settings(params: dict[str, Any]) -> dict[str, object]:
    mirror_mode = str(params.get("wsl_apt_mirror") or "https_archive").strip().lower()
    custom_mirror = str(params.get("wsl_apt_custom_mirror") or "").strip().rstrip("/")
    custom_security = str(params.get("wsl_apt_custom_security_mirror") or "").strip().rstrip("/")

    if mirror_mode == "custom":
        if not custom_mirror:
            raise RuntimeError("Custom apt mirror is selected, but mirror URL is empty.")
        for url in [custom_mirror, custom_security]:
            if url and not re.fullmatch(r"https?://[A-Za-z0-9._~:/?#\[\]@!$&'()*+,;=%-]+", url):
                raise RuntimeError(f"Unsupported apt mirror URL: {url}")
        mirror = custom_mirror
        security = custom_security or custom_mirror
    else:
        if mirror_mode not in WSL_APT_MIRRORS:
            raise RuntimeError(f"Unsupported apt mirror mode: {mirror_mode}")
        mirror, security = WSL_APT_MIRRORS[mirror_mode]

    return {
        "mirror_mode": mirror_mode,
        "mirror": mirror,
        "security_mirror": security,
        "force_ipv4": bool(params.get("wsl_apt_force_ipv4", True)),
        "network_repair": bool(params.get("wsl_apt_network_repair", True)),
        "retries": integer_parameter(params.get("wsl_apt_retries"), 4, minimum=0, maximum=10),
        "timeout": integer_parameter(params.get("wsl_apt_timeout"), 20, minimum=5, maximum=120),
    }


def wsl_apt_prelude(settings: dict[str, object]) -> str:
    return f"""
apt_force_ipv4={bash_single_quote(str(settings["force_ipv4"]).lower())}
apt_network_repair={bash_single_quote(str(settings["network_repair"]).lower())}
apt_retries={bash_single_quote(str(settings["retries"]))}
apt_timeout={bash_single_quote(str(settings["timeout"]))}
apt_mirror={bash_single_quote(str(settings["mirror"]))}
apt_security_mirror={bash_single_quote(str(settings["security_mirror"]))}

apt_opts=(
  -o "Acquire::Retries=$apt_retries"
  -o "Acquire::http::Timeout=$apt_timeout"
  -o "Acquire::https::Timeout=$apt_timeout"
)
if [ "$apt_force_ipv4" = "true" ]; then
  apt_opts+=(-o "Acquire::ForceIPv4=true")
fi

configure_apt_network() {{
  [ "$apt_network_repair" = "true" ] || return 0
  if [ "$apt_force_ipv4" = "true" ]; then
    cat > /etc/apt/apt.conf.d/99audion-wsl-network <<EOF
Acquire::ForceIPv4 "true";
Acquire::Retries "$apt_retries";
Acquire::http::Timeout "$apt_timeout";
Acquire::https::Timeout "$apt_timeout";
EOF
    echo "[i] Wrote /etc/apt/apt.conf.d/99audion-wsl-network"
  fi
  [ -n "$apt_mirror" ] || return 0
  ts="$(date +%Y%m%d-%H%M%S)"
  backup_dir="/var/backups/audion-apt/$ts"
  mkdir -p "$backup_dir"
  for stale in /etc/apt/sources.list.audion-bak.* /etc/apt/sources.list.d/*.audion-bak.*; do
    [ -e "$stale" ] || continue
    stale_name="$(printf '%s' "$stale" | sed 's#[/:]#_#g')"
    mv "$stale" "$backup_dir/$stale_name"
    echo "[i] Moved stale apt source backup out of active source dir: $stale"
  done
  for source_file in /etc/apt/sources.list /etc/apt/sources.list.d/*.list /etc/apt/sources.list.d/*.sources; do
    [ -f "$source_file" ] || continue
    backup_name="$(printf '%s' "$source_file" | sed 's#[/:]#_#g')"
    cp -a "$source_file" "$backup_dir/$backup_name"
    sed -i -E \\
      -e "s#https?://([A-Za-z0-9.-]+\\.)?(archive|ports)\\.ubuntu\\.com/ubuntu/?#$apt_mirror#g" \\
      -e "s#https?://security\\.ubuntu\\.com/ubuntu/?#$apt_security_mirror#g" \\
      "$source_file"
    echo "[i] Checked apt source: $source_file"
  done
  echo "[i] Apt mirror mode: $apt_mirror"
  echo "[i] Apt security mirror: $apt_security_mirror"
}}

apt_update_strict() {{
  local log_file
  log_file="$(mktemp)"
  local rc=0
  apt-get "${{apt_opts[@]}}" update 2>&1 | tee "$log_file" || rc=$?
  if grep -Eqi 'Failed to fetch|Some index files failed|Unable to fetch|Could not connect|Network is unreachable|Connection timed out|Temporary failure resolving' "$log_file"; then
    rc=100
  fi
  rm -f "$log_file"
  return "$rc"
}}

apt_install_resilient() {{
  export DEBIAN_FRONTEND=noninteractive
  apt-get "${{apt_opts[@]}}" install "$@"
}}
"""


def wsl_install_distro(context: JobContext) -> dict[str, object]:
    params = context.operation.parameters
    distro = str(params.get("install_distro_override") or params.get("install_distro") or "").strip()
    if not distro:
        raise RuntimeError("WSL distribution is empty.")
    name = str(params.get("install_name") or "").strip()
    if name and not re.fullmatch(r"[A-Za-z0-9._-]+", name):
        raise RuntimeError("WSL instance name may contain only letters, digits, dot, underscore and dash.")
    location_mode = str(params.get("install_location_mode") or "system").strip().lower()
    location_raw = str(params.get("install_location") or "").strip()
    command = ["wsl.exe", "--install", "-d", distro]
    if name:
        command.extend(["--name", name])
    location = ""
    if location_mode == "custom":
        target = resolve_user_path(context, location_raw, default=wsl_default_install_location(context, name or distro))
        target.mkdir(parents=True, exist_ok=True)
        location = str(target)
        command.extend(["--location", location])
    if bool(params.get("no_launch", True)):
        command.append("--no-launch")
    context.log(f"Installing WSL distribution: {distro}")
    if name:
        context.log(f"Instance name: {name}")
    context.log(f"Install mode: {location_mode}")
    if location:
        context.log(f"Install location: {location}")
    run_process(context, command, cwd=context.paths.root, progress_seconds=1800.0)
    return {"distro": distro, "name": name, "mode": location_mode, "location": location}


def wsl_install_from_file(context: JobContext) -> dict[str, object]:
    params = context.operation.parameters
    source = resolve_user_path(context, params.get("install_image_file"), default=wsl_workspace_root(context) / "Images")
    if not source.exists() or not source.is_file():
        raise RuntimeError(f"WSL image file was not found: {source}")
    name = str(params.get("install_name") or infer_wsl_image_name(source)).strip()
    if not name:
        raise RuntimeError("WSL distribution name is empty.")
    location = resolve_user_path(context, params.get("install_location"), default=wsl_default_install_location(context, name))
    location.mkdir(parents=True, exist_ok=True)
    suffixes = [item.lower() for item in source.suffixes]
    context.log(f"Installing WSL distribution from file: {source}")
    context.log(f"Distro name: {name}")
    context.log(f"Install location: {location}")
    if source.suffix.lower() == ".wsl":
        command = ["wsl.exe", "--install", "--from-file", str(source), "--name", name, "--location", str(location)]
        if bool(params.get("no_launch", True)):
            command.append("--no-launch")
    elif source.suffix.lower() in {".vhd", ".vhdx"}:
        command = ["wsl.exe", "--import", name, str(location), str(source), "--vhd"]
    elif source.suffix.lower() == ".tar" or suffixes[-2:] in [[".tar", ".gz"], [".tar", ".xz"]]:
        command = ["wsl.exe", "--import", name, str(location), str(source), "--version", "2"]
    else:
        raise RuntimeError("Unsupported WSL image type. Use .wsl, .tar, .tar.gz, .vhd or .vhdx.")
    run_process(context, command, cwd=context.paths.root, progress_seconds=1800.0)
    return {"source": str(source), "name": name, "location": str(location)}


def wsl_linux_account(context: JobContext) -> dict[str, object]:
    params = context.operation.parameters
    distro = wsl_selected_distro(context)
    username = str(params.get("linux_username") or "").strip()
    if not username:
        raise RuntimeError("Linux username is empty.")
    validate_linux_username(username)
    password = str(params.get("linux_password") or "")
    set_password = bool(params.get("linux_set_password", True)) and bool(password)
    add_sudo = bool(params.get("linux_add_sudo", True))
    set_default = bool(params.get("linux_set_default_user", True))
    shell = str(params.get("linux_shell") or "/bin/bash").strip() or "/bin/bash"
    if not shell.startswith("/"):
        raise RuntimeError("Linux shell must be an absolute path, for example /bin/bash.")

    password_b64 = base64.b64encode(password.encode("utf-8")).decode("ascii")
    script = f"""#!/usr/bin/env bash
set -euo pipefail
username={bash_single_quote(username)}
shell_path={bash_single_quote(shell)}
password_b64={bash_single_quote(password_b64)}

if ! getent passwd "$username" >/dev/null; then
  echo "[i] Creating user: $username"
  useradd -m -s "$shell_path" "$username"
else
  echo "[i] User already exists: $username"
  usermod -s "$shell_path" "$username" || true
fi

if {str(add_sudo).lower()}; then
  if getent group sudo >/dev/null 2>&1; then
    usermod -aG sudo "$username"
    echo "[i] Added to sudo group: $username"
  elif getent group wheel >/dev/null 2>&1; then
    usermod -aG wheel "$username"
    echo "[i] Added to wheel group: $username"
  else
    echo "[warn] Neither sudo nor wheel group was found."
  fi
fi

if {str(set_password).lower()}; then
  password="$(printf '%s' "$password_b64" | base64 -d)"
  printf '%s:%s\\n' "$username" "$password" | chpasswd
  unset password password_b64
  echo "[i] Password updated for: $username"
else
  echo "[i] Password step skipped."
fi

if {str(set_default).lower()}; then
  ts="$(date +%Y%m%d-%H%M%S)"
  if [ -f /etc/wsl.conf ]; then
    cp -a /etc/wsl.conf "/etc/wsl.conf.bak.$ts"
    skip_user_section=false
    while IFS= read -r line || [ -n "$line" ]; do
      case "$line" in
        "[user]")
          skip_user_section=true
          continue
          ;;
        "["*"]")
          skip_user_section=false
          ;;
      esac
      if ! $skip_user_section; then
        printf '%s\\n' "$line"
      fi
    done < /etc/wsl.conf > /tmp/audion-wsl.conf
  else
    : > /tmp/audion-wsl.conf
  fi
  printf '\\n[user]\\ndefault=%s\\n' "$username" >> /tmp/audion-wsl.conf
  install -m 0644 /tmp/audion-wsl.conf /etc/wsl.conf
  rm -f /tmp/audion-wsl.conf
  echo "[i] /etc/wsl.conf default user set to: $username"
fi

echo "[OK] Linux account bootstrap finished."
"""
    context.log(f"WSL account bootstrap distro: {distro}")
    context.log(f"Linux username: {username}")
    run_wsl_script(context, distro, script, user="root", progress_seconds=120.0)
    if set_default:
        context.log("Terminating distro so WSL can reload /etc/wsl.conf...")
        run_process(context, ["wsl.exe", "--terminate", distro], cwd=context.paths.root, check=False, progress_seconds=20.0)
    return {"distro": distro, "username": username, "default_user": set_default}


def wsl_linux_apt_update(context: JobContext) -> dict[str, object]:
    params = context.operation.parameters
    distro = wsl_selected_distro(context)
    upgrade_mode = str(params.get("wsl_apt_upgrade") or "none").strip().lower()
    if upgrade_mode not in {"none", "upgrade", "full-upgrade"}:
        raise RuntimeError(f"Unsupported package upgrade mode: {upgrade_mode}")
    apt_settings = wsl_apt_network_settings(params)
    script = f"""#!/usr/bin/env bash
set -euo pipefail
upgrade_mode={bash_single_quote(upgrade_mode)}
{wsl_apt_prelude(apt_settings)}
if command -v apt-get >/dev/null 2>&1; then
  pm=apt
elif command -v dnf >/dev/null 2>&1; then
  pm=dnf
else
  echo "[error] Supported package manager was not found. Expected apt-get or dnf."
  exit 2
fi
echo "[i] Package manager: $pm"
case "$pm" in
  apt)
    export DEBIAN_FRONTEND=noninteractive
    configure_apt_network
    apt_update_strict
    case "$upgrade_mode" in
      none) ;;
      upgrade) apt-get "${{apt_opts[@]}}" upgrade -y ;;
      full-upgrade) apt-get "${{apt_opts[@]}}" full-upgrade -y ;;
    esac
    ;;
  dnf)
    dnf makecache -y
    case "$upgrade_mode" in
      none) ;;
      upgrade) dnf upgrade -y ;;
      full-upgrade) dnf distro-sync -y ;;
    esac
    ;;
esac
echo "[OK] Package update finished."
"""
    context.log(f"WSL package update distro: {distro}")
    context.log(f"Upgrade mode: {upgrade_mode}")
    context.log(f"APT mirror mode: {apt_settings['mirror_mode']}")
    context.log(f"APT ForceIPv4: {apt_settings['force_ipv4']}")
    run_wsl_script(context, distro, script, user="root", progress_seconds=1200.0)
    return {"distro": distro, "upgrade": upgrade_mode}


def wsl_linux_dev_packages(context: JobContext) -> dict[str, object]:
    params = context.operation.parameters
    distro = wsl_selected_distro(context)

    packages: list[str] = []

    def add_many(items: list[str]) -> None:
        for item in items:
            if item not in packages:
                packages.append(item)

    package_group_keys = [
        "wsl_packages_baseline",
        "wsl_packages_media_cli",
        "wsl_packages_sync",
        "wsl_packages_lab",
    ]
    if any(key in params for key in package_group_keys):
        for key in package_group_keys:
            selected = params.get(key, [])
            if isinstance(selected, list):
                add_many([str(item) for item in selected])
            elif selected:
                add_many([str(selected)])
    else:
        profiles = params.get("wsl_package_profiles", ["dev_baseline"])
        if not isinstance(profiles, list):
            profiles = [str(profiles)]
        if "dev_baseline" in profiles:
            add_many(WSL_DEV_BASELINE_PACKAGES)
        if "media_cli" in profiles:
            add_many(WSL_MEDIA_CLI_PACKAGES)
        if "lab_containers" in profiles:
            add_many(WSL_LAB_PACKAGES)
        if "sync_extra" in profiles:
            add_many(WSL_SYNC_EXTRA_PACKAGES)
    add_many(parse_package_text(params.get("wsl_optional_packages")))
    flatpak_flathub = bool(params.get("wsl_flatpak_flathub", False))
    if flatpak_flathub:
        add_many(["flatpak"])

    if not packages:
        raise RuntimeError("No WSL packages selected.")

    update_first = bool(params.get("wsl_apt_update_first", True))
    install_recommends = bool(params.get("wsl_install_recommends", False))
    selinux_permissive = bool(params.get("wsl_selinux_permissive", False))
    apt_settings = wsl_apt_network_settings(params)
    apt_recommends_arg = "" if install_recommends else "--no-install-recommends"
    script = f"""#!/usr/bin/env bash
set -euo pipefail
{wsl_apt_prelude(apt_settings)}
if command -v apt-get >/dev/null 2>&1; then
  pm=apt
elif command -v dnf >/dev/null 2>&1; then
  pm=dnf
else
  echo "[error] Supported package manager was not found. Expected apt-get or dnf."
  exit 2
fi
echo "[i] Package manager: $pm"

sleep_selinux() {{
  echo "[i] SELinux permissive requested."
  if command -v getenforce >/dev/null 2>&1; then
    current="$(getenforce 2>/dev/null || true)"
    echo "[i] SELinux runtime: ${{current:-unknown}}"
    if [ "$current" = "Enforcing" ] && command -v setenforce >/dev/null 2>&1; then
      setenforce 0 || echo "[warn] setenforce 0 failed; continuing."
    fi
  else
    echo "[i] getenforce not found; runtime SELinux check skipped."
  fi
  if [ -f /etc/selinux/config ]; then
    ts="$(date +%Y%m%d-%H%M%S)"
    cp -a /etc/selinux/config "/etc/selinux/config.bak.$ts"
    if grep -q '^SELINUX=' /etc/selinux/config; then
      sed -i 's/^SELINUX=.*/SELINUX=permissive/' /etc/selinux/config
    else
      printf '\\nSELINUX=permissive\\n' >> /etc/selinux/config
    fi
    echo "[i] /etc/selinux/config: SELINUX=permissive"
  else
    echo "[i] /etc/selinux/config not found; persistent SELinux change skipped."
  fi
}}

if {str(selinux_permissive).lower()}; then
  if [ "$pm" = "dnf" ]; then
    sleep_selinux
  else
    echo "[i] SELinux permissive requested, skipped for package manager: $pm"
  fi
fi

if {str(update_first).lower()}; then
  case "$pm" in
    apt)
      export DEBIAN_FRONTEND=noninteractive
      configure_apt_network
      apt_update_strict
      ;;
    dnf)
      dnf makecache -y
      ;;
  esac
fi
requested=({bash_array(packages)})
installable=()
skipped=()
declare -A seen=()

map_package() {{
  local pkg="$1"
  if [ "$pm" = "dnf" ]; then
    case "$pkg" in
      wget)
        printf '%s\\n' "wget2-wget"
        return 0
        ;;
      shellcheck)
        printf '%s\\n' "ShellCheck"
        return 0
        ;;
      ffmpeg)
        printf '%s\\n' "ffmpeg-free"
        return 0
        ;;
      aom-tools)
        printf '%s\\n' "aom"
        return 0
        ;;
      normalize-audio)
        printf '%s\\n' "normalize"
        return 0
        ;;
      build-essential|python3-venv)
        return 0
        ;;
      g++)
        printf '%s\\n' "gcc-c++"
        return 0
        ;;
      pkg-config)
        printf '%s\\n' "pkgconf-pkg-config"
        return 0
        ;;
      7zip|p7zip-full)
        printf '%s\\n' "7zip"
        return 0
        ;;
      openssh-client)
        printf '%s\\n' "openssh-clients"
        return 0
        ;;
      imagemagick)
        printf '%s\\n' "ImageMagick"
        return 0
        ;;
      exiftool|libimage-exiftool-perl)
        printf '%s\\n' "perl-Image-ExifTool"
        return 0
        ;;
      handbrake-cli)
        printf '%s\\n' "HandBrake-cli"
        return 0
        ;;
      atomicparsley)
        printf '%s\\n' "AtomicParsley"
        return 0
        ;;
    esac
  fi
  printf '%s\\n' "$pkg"
}}

package_exists() {{
  local pkg="$1"
  case "$pm" in
    apt)
      local candidate
      candidate="$(apt-cache policy "$pkg" 2>/dev/null | awk -F: '/^[[:space:]]*Candidate:/ {{ gsub(/^[[:space:]]+|[[:space:]]+$/, "", $2); print $2; exit }}')"
      [ -n "$candidate" ] && [ "$candidate" != "(none)" ]
      ;;
    dnf)
      rpm -q "$pkg" >/dev/null 2>&1 || dnf -q repoquery --available --installed --qf '%{{name}}' "$pkg" 2>/dev/null | grep -Fxq "$pkg"
      ;;
  esac
}}

for pkg in "${{requested[@]}}"; do
  mapped_any=false
  while IFS= read -r mapped; do
    [ -n "$mapped" ] || continue
    mapped_any=true
    if [ -n "${{seen[$mapped]:-}}" ]; then
      continue
    fi
    seen["$mapped"]=1
    if package_exists "$mapped"; then
      installable+=("$mapped")
    else
      skipped+=("$pkg -> $mapped")
    fi
  done < <(map_package "$pkg")
  if ! $mapped_any; then
    skipped+=("$pkg")
  fi
done
if [ "${{#skipped[@]}}" -gt 0 ]; then
  printf '[skip] package not found: %s\\n' "${{skipped[@]}}"
fi
if [ "${{#installable[@]}}" -eq 0 ]; then
  echo "[warn] No installable packages after package-manager filtering."
  exit 0
fi
echo "[i] Installing ${{#installable[@]}} packages..."
case "$pm" in
  apt)
    export DEBIAN_FRONTEND=noninteractive
    apt_install_resilient -y {apt_recommends_arg} "${{installable[@]}}"
    ;;
  dnf)
    dnf install -y "${{installable[@]}}"
    ;;
esac
if command -v fdfind >/dev/null 2>&1 && ! command -v fd >/dev/null 2>&1; then
  install -d -m 0755 /usr/local/bin
  ln -sf "$(command -v fdfind)" /usr/local/bin/fd
  echo "[i] Created /usr/local/bin/fd -> fdfind"
fi
if {str(flatpak_flathub).lower()}; then
  if command -v flatpak >/dev/null 2>&1; then
    flatpak remote-add --if-not-exists --system flathub https://dl.flathub.org/repo/flathub.flatpakrepo
    echo "[i] Flatpak remotes:"
    flatpak remotes --system || true
  else
    echo "[warn] Flatpak requested, but flatpak command is unavailable after package install."
  fi
fi
echo "[OK] WSL Dev packages installed."
"""
    context.log(f"WSL Dev packages distro: {distro}")
    context.log(f"Requested package count: {len(packages)}")
    context.log(f"SELinux permissive: {selinux_permissive}")
    context.log(f"Flatpak + Flathub: {flatpak_flathub}")
    context.log(f"APT mirror mode: {apt_settings['mirror_mode']}")
    context.log(f"APT ForceIPv4: {apt_settings['force_ipv4']}")
    run_wsl_script(context, distro, script, user="root", progress_seconds=1800.0)
    return {
        "distro": distro,
        "packages": len(packages),
        "selinux_permissive": selinux_permissive,
        "flatpak_flathub": flatpak_flathub,
    }


def wsl_micro_baseline(context: JobContext) -> dict[str, object]:
    distro = wsl_selected_distro(context)
    user = linux_user_or_default(context) or None
    script = read_wsl_asset("micro", "audion-micro-baseline.sh")
    context.log(f"Installing micro baseline in WSL distro: {distro}")
    context.log(f"Linux user: {user or '(WSL default)'}")
    run_wsl_script(context, distro, script, user=user, progress_seconds=120.0)
    return {"distro": distro, "user": user or ""}


def wsl_mc_skin(context: JobContext) -> dict[str, object]:
    params = context.operation.parameters
    distro = wsl_selected_distro(context)
    user = linux_user_or_default(context) or None
    skin = str(params.get("mc_skin") or "electricblue256").strip().lower()
    if skin not in {"audion256", "electricblue256"}:
        raise RuntimeError(f"Unsupported MC skin: {skin}")
    skin_text = read_wsl_asset("mc", f"{skin}.ini")
    skin_b64 = base64.b64encode(skin_text.encode("utf-8")).decode("ascii")
    apply_skin = bool(params.get("mc_apply_skin", True))
    script = f"""#!/usr/bin/env bash
set -euo pipefail
skin={bash_single_quote(skin)}
skin_b64={bash_single_quote(skin_b64)}
skin_dir="$HOME/.local/share/mc/skins"
config_dir="$HOME/.config/mc"
mkdir -p "$skin_dir" "$config_dir"
target="$skin_dir/${{skin}}.ini"
if [ -f "$target" ]; then
  cp -a "$target" "$target.bak.$(date +%Y%m%d-%H%M%S)"
fi
printf '%s' "$skin_b64" | base64 -d > "$target"
echo "[i] MC skin installed: $target"
if {str(apply_skin).lower()}; then
  ini="$config_dir/ini"
  if [ -f "$ini" ]; then
    cp -a "$ini" "$ini.bak.$(date +%Y%m%d-%H%M%S)"
    if grep -q '^skin=' "$ini"; then
      sed -i "s/^skin=.*/skin=$skin/" "$ini"
    else
      printf '\\n[Midnight-Commander]\\nskin=%s\\n' "$skin" >> "$ini"
    fi
  else
    printf '[Midnight-Commander]\\nskin=%s\\n' "$skin" > "$ini"
  fi
  echo "[i] MC config points to skin: $skin"
fi
echo "[OK] MC skin setup finished."
"""
    context.log(f"Installing MC skin in WSL distro: {distro}")
    context.log(f"Linux user: {user or '(WSL default)'}")
    context.log(f"MC skin: {skin}")
    run_wsl_script(context, distro, script, user=user, progress_seconds=120.0)
    return {"distro": distro, "user": user or "", "skin": skin}


def wsl_neovim_base(context: JobContext) -> dict[str, object]:
    params = context.operation.parameters
    distro = wsl_selected_distro(context)
    user = linux_user_or_default(context) or None
    appname = str(params.get("nvim_appname") or "audion-ide").strip()
    if not re.fullmatch(r"[A-Za-z0-9._-]+", appname):
        raise RuntimeError("Neovim appname may contain only letters, digits, dot, underscore and dash.")
    profile = str(params.get("nvim_profile") or "lite").strip().lower()
    if profile not in {"lite", "lazyvim"}:
        raise RuntimeError("Neovim profile must be 'lite' or 'lazyvim'.")
    script = (
        "export AUDION_NVIM_APPNAME="
        + bash_single_quote(appname)
        + "\nexport AUDION_NVIM_PROFILE="
        + bash_single_quote(profile)
        + "\n"
        + read_wsl_asset("neovim", "audion-nvim-base.sh")
    )
    context.log(f"Installing Neovim base profile in WSL distro: {distro}")
    context.log(f"Linux user: {user or '(WSL default)'}")
    context.log(f"NVIM_APPNAME: {appname}")
    context.log(f"Neovim profile: {profile}")
    run_wsl_script(context, distro, script, user=user, progress_seconds=1800.0)
    return {"distro": distro, "user": user or "", "appname": appname, "profile": profile}


def wsl_register_all_vhdx(context: JobContext) -> dict[str, object]:
    params = context.operation.parameters
    wsl_root = ensure_wsl_workspace(context)
    root = resolve_user_path(context, params.get("register_root"), default=wsl_root / "VHDX")
    if not root.exists():
        raise RuntimeError(f"VHDX root was not found: {root}")
    filter_name = str(params.get("filter") or "ext4.vhdx").strip() or "ext4.vhdx"
    dry_run = bool(params.get("dry_run", True))
    files = sorted(path for path in root.rglob(filter_name) if path.is_file())
    context.log(f"Register-all root: {root}")
    context.log(f"Filter: {filter_name}")
    context.log(f"Dry run: {dry_run}")
    if not files:
        context.log("No VHDX files found.")
        return {"root": str(root), "count": 0, "dry_run": dry_run}
    existing_text = _run_capture(["wsl.exe", "--list", "--quiet"], timeout=8.0)
    existing = {line.strip().lower() for line in existing_text.splitlines() if line.strip()}
    registered_vhdx = wsl_registered_vhdx_paths(context.paths.root)
    if not dry_run:
        run_process(context, ["wsl.exe", "--shutdown"], cwd=context.paths.root, check=False, progress_seconds=20.0)
    registered = 0
    skipped = 0
    for path in files:
        name = path.parent.name
        command = ["wsl.exe", "--import-in-place", name, str(path)]
        if name.lower() in existing:
            context.log(f"SKIP existing distro name: {name} -> {path}")
            skipped += 1
            continue
        registered_name = registered_vhdx.get(_path_key(path))
        if registered_name:
            context.log(f"SKIP VHDX already registered as {registered_name}: {path}")
            skipped += 1
            continue
        context.log(f"{'DRYRUN ' if dry_run else ''}{format_command(command)}")
        if not dry_run:
            run_process(context, command, cwd=context.paths.root, progress_seconds=120.0)
            existing.add(name.lower())
            registered_vhdx[_path_key(path)] = name
        registered += 1
    return {"root": str(root), "count": len(files), "registered": registered, "skipped": skipped, "dry_run": dry_run}


_VIRTUALIZATION_STATUS_PS = r"""
$ErrorActionPreference = 'Continue'
$PSNativeCommandUseErrorActionPreference = $false

$isAdmin = ([Security.Principal.WindowsPrincipal] [Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
Write-Host "Administrator: $isAdmin"
Write-Host ''

Write-Host '=== Hypervisor launch type (bcdedit) ==='
$hltLine = (& bcdedit /enum '{current}' 2>$null | Select-String -Pattern 'hypervisorlaunchtype')
if ($hltLine) {
  $hlt = ($hltLine.Line.Trim() -split '\s+')[-1]
} else {
  $hlt = 'Auto'
  Write-Host '(hypervisorlaunchtype not explicitly set; default is Auto on Hyper-V-capable systems)'
}
Write-Host "hypervisorlaunchtype: $hlt"
Write-Host ''

Write-Host '=== Optional features ==='
if ($isAdmin) {
  $features = @(
    'Microsoft-Hyper-V-All',
    'VirtualMachinePlatform',
    'HypervisorPlatform',
    'Microsoft-Windows-Subsystem-Linux',
    'Containers-DisposableClientVM'
  )
  $rows = foreach ($f in $features) {
    try {
      Get-WindowsOptionalFeature -Online -FeatureName $f -ErrorAction Stop | Select-Object FeatureName, State
    } catch {
      [pscustomobject]@{ FeatureName = $f; State = 'NotPresent/Unknown' }
    }
  }
  $rows | Format-Table FeatureName, State -AutoSize | Out-String -Width 200
} else {
  Write-Host 'Feature table needs Administrator rights; skipped.'
}
Write-Host ''

Write-Host '=== Virtualization-based security (VBS / Core Isolation) ==='
try {
  $dg = Get-CimInstance -Namespace 'root\Microsoft\Windows\DeviceGuard' -ClassName Win32_DeviceGuard -ErrorAction Stop
  $running = @($dg.SecurityServicesRunning)
  $vbs = switch ($dg.VirtualizationBasedSecurityStatus) { 0 { 'Off' } 1 { 'Configured' } 2 { 'Running' } default { 'Unknown' } }
  Write-Host "VBS status: $vbs"
  Write-Host ("HVCI (Memory Integrity) running: " + $(if ($running -contains 2) { 'Yes' } else { 'No' }))
  Write-Host ("Credential Guard running: " + $(if ($running -contains 1) { 'Yes' } else { 'No' }))
} catch {
  Write-Host "VBS query failed: $($_.Exception.Message)"
}
Write-Host ''

Write-Host '=== Interpreted mode ==='
if ($hlt -ieq 'Off') {
  Write-Host 'Mode: THIRD-PARTY FAST. Hyper-V/WSL2/Sandbox are OFF; VMware/VirtualBox run at full speed.'
  Write-Host 'Note: if VBS/Core Isolation is Running, the hypervisor may still hold VT-x. Disable Core Isolation for true full speed.'
} else {
  Write-Host 'Mode: HYPER-V / WSL2. The Windows hypervisor owns VT-x; third-party VMs run only via Windows Hypervisor Platform (slower) or fail.'
}
exit 0
"""


_VIRTUALIZATION_OPTIMIZATION_PS = r"""
$ErrorActionPreference = 'Continue'

Write-Host '=== Core Isolation / VBS (VM speed) ==='
try {
  $dg = Get-CimInstance -Namespace 'root\Microsoft\Windows\DeviceGuard' -ClassName Win32_DeviceGuard -ErrorAction Stop
  $running = @($dg.SecurityServicesRunning)
  if ($running -contains 2) {
    Write-Host 'HVCI (Memory Integrity): ON -> adds VM overhead. Turn OFF for max third-party VM speed (security tradeoff).'
  } else {
    Write-Host 'HVCI (Memory Integrity): OFF -> good for VM speed.'
  }
  Write-Host ("Credential Guard: " + $(if ($running -contains 1) { 'ON -> holds VT-x' } else { 'OFF' }))
} catch {
  Write-Host "VBS query failed: $($_.Exception.Message)"
}
Write-Host ''

Write-Host '=== Active power plan ==='
& powercfg /getactivescheme
Write-Host 'Tip: use High performance / Ultimate for heavy virtualization.'
Write-Host ''

Write-Host '=== Defender real-time exclusions ==='
try {
  $ex = (Get-MpPreference).ExclusionPath
  if ($ex) {
    foreach ($p in $ex) { Write-Host ("  " + $p) }
  } else {
    Write-Host '  (none) -> consider excluding WSL VHDX and VM disk folders for IO speed (security tradeoff).'
  }
} catch {
  Write-Host '  Get-MpPreference unavailable (no Defender or insufficient rights).'
}
Write-Host ''

Write-Host '=== .wslconfig ==='
$cfg = Join-Path $env:USERPROFILE '.wslconfig'
if (Test-Path -LiteralPath $cfg) {
  Write-Host ("Found: " + $cfg)
  Get-Content -LiteralPath $cfg | ForEach-Object { Write-Host ("  " + $_) }
} else {
  Write-Host '  Not found -> create %UserProfile%\.wslconfig to cap RAM/CPU and enable sparseVhd / nestedVirtualization.'
}
exit 0
"""


def virtualization_switch(context: JobContext) -> dict[str, object]:
    params = context.operation.parameters
    mode = str(params.get("mode") or "status").strip().lower()

    if mode == "status":
        run_ps_command(context, _VIRTUALIZATION_STATUS_PS, check=False, progress_seconds=60.0)
        return {"mode": mode}

    if mode == "optimization_status":
        run_ps_command(context, _VIRTUALIZATION_OPTIMIZATION_PS, check=False, progress_seconds=90.0)
        try:
            vhdx = wsl_registered_vhdx_paths(context.paths.root)
        except Exception as exc:
            context.log(f"WSL VHDX lookup failed: {exc.__class__.__name__}: {exc}")
            vhdx = {}
        context.log("")
        context.log("=== WSL VHDX placement ===")
        if vhdx:
            for path, name in vhdx.items():
                context.log(f"{name}: {path}")
            context.log("Tip: keep VHDX on a fast NVMe drive; a slow/system drive throttles WSL IO.")
        else:
            context.log("No registered WSL VHDX paths found.")
        return {"mode": mode}

    backup_dir = context.paths.backup / "virtualization"
    backup_dir.mkdir(parents=True, exist_ok=True)

    steps: list[str] = []
    if mode == "mode_hyperv":
        context.log("Switching to Hyper-V / WSL2 mode (hypervisor ON).")
        steps += [
            "& bcdedit /set hypervisorlaunchtype Auto | Out-Host",
            "dism.exe /online /enable-feature /featurename:VirtualMachinePlatform /all /norestart",
        ]
    elif mode == "mode_thirdparty":
        context.log("Switching to third-party fast mode (hypervisor OFF). WSL2/Hyper-V/Sandbox will stop until you switch back.")
        steps += [
            "& bcdedit /set hypervisorlaunchtype Off | Out-Host",
        ]
    elif mode == "mode_coexist":
        context.log("Enabling coexistence: Windows Hypervisor Platform ON, hypervisor ON (third-party VMs run alongside Hyper-V, slower).")
        steps += [
            "& bcdedit /set hypervisorlaunchtype Auto | Out-Host",
            "dism.exe /online /enable-feature /featurename:HypervisorPlatform /all /norestart",
            "dism.exe /online /enable-feature /featurename:VirtualMachinePlatform /all /norestart",
        ]
    elif mode == "hyperv_enable":
        context.log("Enabling Hyper-V (Microsoft-Hyper-V-All).")
        steps += [
            "dism.exe /online /enable-feature /featurename:Microsoft-Hyper-V-All /all /norestart",
            "& bcdedit /set hypervisorlaunchtype Auto | Out-Host",
        ]
    elif mode == "hyperv_disable":
        context.log("Disabling Hyper-V (Microsoft-Hyper-V-All).")
        steps += [
            "dism.exe /online /disable-feature /featurename:Microsoft-Hyper-V-All /norestart",
        ]
    elif mode == "sandbox_enable":
        context.log("Enabling Windows Sandbox (Containers-DisposableClientVM).")
        steps += [
            "dism.exe /online /enable-feature /featurename:Containers-DisposableClientVM /all /norestart",
        ]
    elif mode == "sandbox_disable":
        context.log("Disabling Windows Sandbox (Containers-DisposableClientVM).")
        steps += [
            "dism.exe /online /disable-feature /featurename:Containers-DisposableClientVM /norestart",
        ]
    else:
        raise RuntimeError(f"Unsupported virtualization mode: {mode}")

    script = "\n".join(
        [
            "$ErrorActionPreference = 'Stop'",
            "$PSNativeCommandUseErrorActionPreference = $false",
            f"$BackupDir = {ps_quote(backup_dir)}",
            "New-Item -ItemType Directory -Force -Path $BackupDir | Out-Null",
            "$Stamp = Get-Date -Format 'yyyyMMdd_HHmmss'",
            f"$BcdBackup = Join-Path $BackupDir ('bcd_before_{mode}_' + $Stamp + '.bcd')",
            "& bcdedit /export $BcdBackup | Out-Host",
            "Write-Host ('BCD backup: ' + $BcdBackup)",
            "Write-Host ''",
            *steps,
            "Write-Host ''",
            "Write-Host 'Done. A reboot is REQUIRED before the new virtualization mode is active.'",
        ]
    )
    run_ps_command(context, script, progress_seconds=300.0, elevated=True)
    return {"mode": mode, "reboot_required": True, "backup_dir": str(backup_dir)}


def bitrix_dns_only_ips(context: JobContext, host_name: str) -> list[str]:
    script = f"""
$ErrorActionPreference = 'Continue'
$TargetHost = {ps_quote(host_name)}
$Ips = @()
Write-Host '=== DNS-only Bitrix endpoint lookup ==='
Write-Host ('Host name: ' + $TargetHost)
$ResolveCommand = Get-Command Resolve-DnsName -ErrorAction SilentlyContinue
if ($ResolveCommand) {{
  foreach ($RecordType in @('A', 'AAAA')) {{
    try {{
      $ResolveParams = @{{
        Name = $TargetHost
        Type = $RecordType
        ErrorAction = 'Stop'
      }}
      if ($ResolveCommand.Parameters.ContainsKey('DnsOnly')) {{ $ResolveParams['DnsOnly'] = $true }}
      if ($ResolveCommand.Parameters.ContainsKey('NoHostsFile')) {{ $ResolveParams['NoHostsFile'] = $true }}
      $Records = Resolve-DnsName @ResolveParams |
        Where-Object {{ $_.IPAddress }} |
        Select-Object -ExpandProperty IPAddress -Unique
      foreach ($Record in $Records) {{
        $Ips += [string]$Record
      }}
    }} catch {{
      Write-Host ($RecordType + ': ERROR: ' + $_.Exception.Message)
    }}
  }}
}} else {{
  Write-Host 'Resolve-DnsName is not available; falling back to nslookup.'
  $Raw = & nslookup.exe $TargetHost 2>$null
  foreach ($Line in $Raw) {{
    foreach ($Match in [regex]::Matches($Line, '(?<![0-9A-Fa-f:.])(?:\\d{{1,3}}\\.){{3}}\\d{{1,3}}(?![0-9A-Fa-f:.])')) {{
      $Ips += [string]$Match.Value
    }}
  }}
}}
$Ips = @($Ips | Where-Object {{ $_ }} | Sort-Object -Unique)
if ($Ips) {{
  Write-Host 'DNS-only IPs:'
  $Ips | ForEach-Object {{ Write-Host ('  ' + $_) }}
}} else {{
  Write-Host 'DNS-only IPs: none'
}}
Write-Host ('__AUDION_DNS_IPS_JSON=' + (($Ips | ConvertTo-Json -Compress)))
"""
    result = run_ps_command(context, script, check=False, progress_seconds=20.0)
    for line in reversed(result.lines):
        if line.startswith("__AUDION_DNS_IPS_JSON="):
            raw = line.split("=", 1)[1].strip()
            if not raw:
                return []
            try:
                parsed = json.loads(raw)
            except json.JSONDecodeError:
                return []
            if isinstance(parsed, str):
                return [parsed]
            if isinstance(parsed, list):
                return [str(item) for item in parsed if str(item).strip()]
    return []


def bitrix_detect_endpoint(context: JobContext, host_name: str, ports: list[int], scan_candidates: list[int]) -> dict[str, object]:
    dns_ips = bitrix_dns_only_ips(context, host_name)
    local_ips = [ip for ip in dns_ips if is_local_network_ip(ip)]
    public_ips = [ip for ip in dns_ips if ip not in local_ips]
    updates: dict[str, Any] = {}
    selected_ip = local_ips[0] if local_ips else ""

    context.log("=== Bitrix endpoint decision ===")
    if local_ips:
        context.log("Local/private DNS IP candidates: " + ", ".join(local_ips))
        updates["ip_address"] = selected_ip
    elif public_ips:
        context.log("DNS returned only public IPs; GUI fields will not be changed.")
        context.log("Public DNS IP candidates: " + ", ".join(public_ips))
    else:
        context.log("No DNS IP candidates found; GUI fields will not be changed.")

    detected_ports: list[int] = []
    if selected_ip:
        scan_ports = list(dict.fromkeys([*scan_candidates, *ports]))
        context.log("Scanning local Bitrix IP ports: " + ", ".join(str(port) for port in scan_ports))
        for port in scan_ports:
            if tcp_port_is_open(selected_ip, port):
                detected_ports.append(port)
                context.log(f"  {selected_ip}:{port} -> OPEN")
            else:
                context.log(f"  {selected_ip}:{port} -> closed/timeout")

    if detected_ports:
        updates["bitrix_ports"] = ",".join(str(port) for port in detected_ports)
        context.log("Detected local Bitrix ports: " + updates["bitrix_ports"])
    elif selected_ip:
        context.log("No open candidate ports detected; keeping current custom ports field.")

    if updates:
        updates["host_name"] = host_name
    return {
        "mode": "detect",
        "host": host_name,
        "dns_ips": dns_ips,
        "local_ips": local_ips,
        "public_ips": public_ips,
        "selected_ip": selected_ip,
        "detected_ports": detected_ports,
        "field_updates": updates,
    }


def bitrix_hosts_status(
    context: JobContext,
    host_name: str,
    ip_address: str,
    manual_ports: list[int],
    scan_candidates: list[int],
    auto_scan_ports: bool,
) -> None:
    manual_port_array = ps_int_array(manual_ports)
    scan_port_array = ps_int_array(scan_candidates)
    auto_scan_literal = "$true" if auto_scan_ports else "$false"
    script = f"""
$ErrorActionPreference = 'Continue'
$TargetHost = {ps_quote(host_name)}
$TargetIp = {ps_quote(ip_address)}
$ManualPorts = {manual_port_array}
$ScanCandidates = {scan_port_array}
$AutoScanPorts = {auto_scan_literal}
$TargetIpLabel = if ($TargetIp) {{ $TargetIp }} else {{ '(empty)' }}
$ManualPortLabel = if ($ManualPorts) {{ $ManualPorts -join ', ' }} else {{ '(none)' }}
$ScanPortLabel = if ($ScanCandidates) {{ $ScanCandidates -join ', ' }} else {{ '(none)' }}
$AutoScanLabel = if ($AutoScanPorts) {{ 'enabled' }} else {{ 'disabled' }}
$HostsPath = Join-Path $env:SystemRoot 'System32\\drivers\\etc\\hosts'
$ManagedMarker = 'AUDION_BITRIX_HOSTS'

Write-Host '=== Bitrix host status ==='
Write-Host ('Host name: ' + $TargetHost)
Write-Host ('Preset/target IP: ' + $TargetIpLabel)
Write-Host ('Custom TCP ports: ' + $ManualPortLabel)
Write-Host ('Auto-scan: ' + $AutoScanLabel + '; candidates: ' + $ScanPortLabel)
Write-Host ('Hosts file: ' + $HostsPath)
Write-Host ''

Write-Host '=== hosts file active entries ==='
if (-not (Test-Path -LiteralPath $HostsPath)) {{
  Write-Host 'hosts file was not found.'
}} else {{
  $LineNumber = 0
  $HostRows = foreach ($Line in Get-Content -LiteralPath $HostsPath -ErrorAction SilentlyContinue) {{
    $LineNumber++
    $Clean = ($Line -split '#', 2)[0].Trim()
    if (-not $Clean) {{ continue }}
    $Parts = $Clean -split '\\s+'
    if ($Parts.Count -lt 2) {{ continue }}
    $EntryIp = $Parts[0]
    $Names = @($Parts | Select-Object -Skip 1)
    $NameMatch = $Names | Where-Object {{ $_ -ieq $TargetHost }}
    $IpMatch = $TargetIp -and ($EntryIp -eq $TargetIp)
    if ($NameMatch -or $IpMatch) {{
      $Comment = ''
      $MetaPorts = ''
      $MetaBackup = ''
      $Managed = 'no'
      if ($Line -match '#(.*)$') {{
        $Comment = $Matches[1].Trim()
        if ($Comment -like ('*' + $ManagedMarker + '*')) {{ $Managed = 'yes' }}
        if ($Comment -match 'ports=([^;\\s]+)') {{ $MetaPorts = $Matches[1] }}
        if ($Comment -match 'backup=([^;\\s]+)') {{ $MetaBackup = $Matches[1] }}
      }}
      [pscustomobject]@{{
        Line = $LineNumber
        IP = $EntryIp
        Names = ($Names -join ', ')
        Ports = $MetaPorts
        Backup = $MetaBackup
        Managed = $Managed
        Raw = $Line
      }}
    }}
  }}
  if ($HostRows) {{
    $HostRows | Format-Table Line,IP,Names,Ports,Backup,Managed -AutoSize | Out-String -Width 220
    Write-Host 'Raw matching lines:'
    $HostRows | ForEach-Object {{ Write-Host ('  ' + $_.Raw) }}
  }} else {{
    Write-Host 'No active hosts entries matched the selected host/IP.'
  }}
}}
Write-Host ''

Write-Host '=== effective system resolution (hosts-aware) ==='
try {{
  $Effective = [System.Net.Dns]::GetHostAddresses($TargetHost) |
    ForEach-Object {{ $_.IPAddressToString }} |
    Sort-Object -Unique
  if ($Effective) {{
    $Effective | ForEach-Object {{ Write-Host ('  ' + $_) }}
  }} else {{
    Write-Host '  no addresses returned.'
  }}
}} catch {{
  Write-Host ('  ERROR: ' + $_.Exception.Message)
}}
Write-Host ''

function Test-AudionTcpPort {{
  param(
    [Parameter(Mandatory = $true)][string]$ComputerName,
    [Parameter(Mandatory = $true)][int]$Port,
    [int]$TimeoutMs = 3500
  )
  $Client = [System.Net.Sockets.TcpClient]::new()
  try {{
    $Async = $Client.BeginConnect($ComputerName, $Port, $null, $null)
    $Connected = $Async.AsyncWaitHandle.WaitOne($TimeoutMs, $false)
    if ($Connected) {{
      try {{
        $Client.EndConnect($Async)
        return $true
      }} catch {{
        return $false
      }}
    }}
    return $false
  }} catch {{
    return $false
  }} finally {{
    try {{ $Client.Close() }} catch {{ }}
  }}
}}

$TcpTargets = @()
if ($TargetHost) {{
  $TcpTargets += [pscustomobject]@{{ Label = 'host (hosts-aware)'; ComputerName = $TargetHost }}
}}
if ($TargetIp) {{
  $TcpTargets += [pscustomobject]@{{ Label = 'preset/target IP'; ComputerName = $TargetIp }}
}}

$DetectedPorts = [System.Collections.Generic.List[int]]::new()
if ($AutoScanPorts -and $ScanCandidates -and $TcpTargets) {{
  Write-Host '=== TCP port auto scan ==='
  foreach ($TcpTarget in $TcpTargets) {{
    Write-Host ($TcpTarget.Label + ': ' + $TcpTarget.ComputerName)
    foreach ($CandidatePort in $ScanCandidates) {{
      $Open = Test-AudionTcpPort -ComputerName $TcpTarget.ComputerName -Port ([int]$CandidatePort)
      if ($Open) {{
        if (-not $DetectedPorts.Contains([int]$CandidatePort)) {{ [void]$DetectedPorts.Add([int]$CandidatePort) }}
        Write-Host ('  ' + $TcpTarget.ComputerName + ':' + $CandidatePort + ' -> OPEN')
      }}
    }}
  }}
  if ($DetectedPorts.Count -eq 0) {{
    Write-Host '  no open candidate ports detected.'
  }}
  Write-Host ''
}}

$EffectivePorts = @($ManualPorts + $DetectedPorts.ToArray() | Sort-Object -Unique)
$EffectivePortLabel = if ($EffectivePorts) {{ $EffectivePorts -join ', ' }} else {{ '(none)' }}
Write-Host '=== TCP port checks ==='
Write-Host ('Effective TCP ports: ' + $EffectivePortLabel)
if (-not $EffectivePorts) {{
  Write-Host 'No TCP ports selected or detected.'
}} else {{
  foreach ($TcpTarget in $TcpTargets) {{
    Write-Host ($TcpTarget.Label + ': ' + $TcpTarget.ComputerName)
    foreach ($Port in $EffectivePorts) {{
      $Open = Test-AudionTcpPort -ComputerName $TcpTarget.ComputerName -Port ([int]$Port)
      $State = if ($Open) {{ 'OPEN' }} else {{ 'closed/timeout' }}
      Write-Host ('  ' + $TcpTarget.ComputerName + ':' + $Port + ' -> ' + $State)
    }}
  }}
}}
Write-Host ''

Write-Host '=== DNS answer without hosts file ==='
$ResolveCommand = Get-Command Resolve-DnsName -ErrorAction SilentlyContinue
if ($ResolveCommand) {{
  foreach ($RecordType in @('A', 'AAAA')) {{
    try {{
      $ResolveParams = @{{
        Name = $TargetHost
        Type = $RecordType
        ErrorAction = 'Stop'
      }}
      if ($ResolveCommand.Parameters.ContainsKey('DnsOnly')) {{ $ResolveParams['DnsOnly'] = $true }}
      if ($ResolveCommand.Parameters.ContainsKey('NoHostsFile')) {{ $ResolveParams['NoHostsFile'] = $true }}
      $Records = Resolve-DnsName @ResolveParams |
        Where-Object {{ $_.IPAddress }} |
        Select-Object -ExpandProperty IPAddress -Unique
      if ($Records) {{
        Write-Host ($RecordType + ':')
        $Records | Sort-Object -Unique | ForEach-Object {{ Write-Host ('  ' + $_) }}
      }} else {{
        Write-Host ($RecordType + ': no records.')
      }}
    }} catch {{
      Write-Host ($RecordType + ': ERROR: ' + $_.Exception.Message)
    }}
  }}
}} else {{
  Write-Host 'Resolve-DnsName is not available; falling back to nslookup.'
  & nslookup.exe $TargetHost 2>$null
}}
Write-Host ''

Write-Host '=== configured DNS servers ==='
try {{
  Get-DnsClientServerAddress -AddressFamily IPv4 -ErrorAction Stop |
    Where-Object {{ $_.ServerAddresses }} |
    Select-Object InterfaceAlias,ServerAddresses |
    Format-Table -AutoSize | Out-String -Width 220
}} catch {{
  Write-Host ('  ERROR: ' + $_.Exception.Message)
}}
"""
    context.log("Bitrix Hosts mode: status")
    run_ps_command(context, script, progress_seconds=60.0)


def bitrix_hosts_apply(
    context: JobContext,
    mode: str,
    host_name: str,
    ip_address: str,
    manual_ports: list[int],
    scan_candidates: list[int],
    auto_scan_ports: bool,
) -> None:
    backup_dir = context.paths.backup / "hosts"
    manual_port_array = ps_int_array(manual_ports)
    scan_port_array = ps_int_array(scan_candidates)
    auto_scan_literal = "$true" if auto_scan_ports else "$false"
    script = f"""
$ErrorActionPreference = 'Stop'
$Mode = {ps_quote(mode.lower())}
$TargetHost = {ps_quote(host_name)}
$TargetIp = {ps_quote(ip_address)}
$ManualPorts = {manual_port_array}
$ScanCandidates = {scan_port_array}
$AutoScanPorts = {auto_scan_literal}
$HostsPath = Join-Path $env:SystemRoot 'System32\\drivers\\etc\\hosts'
$BackupDir = {ps_quote(backup_dir)}
$ManagedMarker = 'AUDION_BITRIX_HOSTS'

function Test-AudionTcpPort {{
  param(
    [Parameter(Mandatory = $true)][string]$ComputerName,
    [Parameter(Mandatory = $true)][int]$Port,
    [int]$TimeoutMs = 2500
  )
  $Client = [System.Net.Sockets.TcpClient]::new()
  try {{
    $Async = $Client.BeginConnect($ComputerName, $Port, $null, $null)
    $Connected = $Async.AsyncWaitHandle.WaitOne($TimeoutMs, $false)
    if ($Connected) {{
      try {{
        $Client.EndConnect($Async)
        return $true
      }} catch {{
        return $false
      }}
    }}
    return $false
  }} catch {{
    return $false
  }} finally {{
    try {{ $Client.Close() }} catch {{ }}
  }}
}}

function Backup-AudionHosts {{
  param([string]$Kind = 'snapshot')
  New-Item -ItemType Directory -Force -Path $BackupDir | Out-Null
  $Stamp = Get-Date -Format 'yyyyMMdd-HHmmss-fff'
  $SafeKind = if ($Kind -match '^[A-Za-z0-9_-]+$') {{ $Kind }} else {{ 'snapshot' }}
  $BackupPath = Join-Path $BackupDir ('hosts_' + $SafeKind + '_' + $Stamp + '.bak')
  if (Test-Path -LiteralPath $HostsPath) {{
    Copy-Item -LiteralPath $HostsPath -Destination $BackupPath -Force
  }} else {{
    '' | Out-File -FilePath $BackupPath -Encoding utf8
  }}
  Write-Host ('Backup: ' + $BackupPath)
  return $BackupPath
}}

function Get-AudionManagedBackupName {{
  param([AllowEmptyString()][string[]]$Lines)
  foreach ($Line in $Lines) {{
    if (-not (Test-AudionHostsLineTarget -Line $Line)) {{ continue }}
    if ($Line -notlike ('*' + $ManagedMarker + '*')) {{ continue }}
    if ($Line -match 'backup=([^;\\s]+)') {{ return $Matches[1] }}
  }}
  return ''
}}

function Test-AudionHostsLineTarget {{
  param([AllowEmptyString()][string]$Line)
  $Clean = ($Line -split '#', 2)[0].Trim()
  if (-not $Clean) {{ return $false }}
  $Parts = $Clean -split '\\s+'
  if ($Parts.Count -lt 2) {{ return $false }}
  $Names = @($Parts | Select-Object -Skip 1)
  foreach ($Name in $Names) {{
    if ($Name -ieq $TargetHost) {{ return $true }}
  }}
  return $false
}}

function Get-AudionDetectedPorts {{
  $Detected = [System.Collections.Generic.List[int]]::new()
  if (-not $AutoScanPorts -or -not $ScanCandidates) {{ return @() }}
  $Targets = @()
  if ($TargetHost) {{ $Targets += $TargetHost }}
  if ($TargetIp) {{ $Targets += $TargetIp }}
  foreach ($Target in $Targets) {{
    foreach ($CandidatePort in $ScanCandidates) {{
      if (Test-AudionTcpPort -ComputerName $Target -Port ([int]$CandidatePort)) {{
        if (-not $Detected.Contains([int]$CandidatePort)) {{ [void]$Detected.Add([int]$CandidatePort) }}
      }}
    }}
  }}
  return @($Detected.ToArray() | Sort-Object -Unique)
}}

function Write-AudionHostsLines {{
  param([AllowEmptyString()][string[]]$Lines)
  $Text = ($Lines -join [Environment]::NewLine) + [Environment]::NewLine
  [System.IO.File]::WriteAllText($HostsPath, $Text, [System.Text.UTF8Encoding]::new($false))
}}

Write-Host ('Mode: ' + $Mode)
Write-Host ('Host name: ' + $TargetHost)
Write-Host ('Preset/target IP: ' + $(if ($TargetIp) {{ $TargetIp }} else {{ '(empty)' }}))
Write-Host ('Custom TCP ports: ' + $(if ($ManualPorts) {{ $ManualPorts -join ', ' }} else {{ '(none)' }}))
Write-Host ('Auto-scan ports: ' + $(if ($AutoScanPorts) {{ 'enabled' }} else {{ 'disabled' }}))
Write-Host ('Hosts file: ' + $HostsPath)

if ($Mode -eq 'restore') {{
  if (-not (Test-Path -LiteralPath $BackupDir)) {{ throw ('No hosts backup folder found: ' + $BackupDir) }}
  $Latest = Get-ChildItem -LiteralPath $BackupDir -Filter 'hosts_prepatch_*.bak' -File |
    Sort-Object LastWriteTime -Descending |
    Select-Object -First 1
  if (-not $Latest) {{
    $Latest = Get-ChildItem -LiteralPath $BackupDir -Filter 'hosts_*.bak' -File |
      Sort-Object LastWriteTime -Descending |
      Select-Object -First 1
  }}
  if (-not $Latest) {{ throw ('No hosts backups found in: ' + $BackupDir) }}
  Backup-AudionHosts -Kind 'before_restore' | Out-Null
  Copy-Item -LiteralPath $Latest.FullName -Destination $HostsPath -Force
  Write-Host ('Restored hosts from: ' + $Latest.FullName)
  return
}}

if (-not $TargetHost) {{ throw 'Host name is empty.' }}
$Lines = if (Test-Path -LiteralPath $HostsPath) {{
  @([System.IO.File]::ReadAllLines($HostsPath))
}} else {{
  @()
}}

if ($Mode -eq 'disable') {{
  if (-not (Test-Path -LiteralPath $BackupDir)) {{ throw ('No hosts backup folder found: ' + $BackupDir) }}
  $BackupName = Get-AudionManagedBackupName -Lines $Lines
  if (-not $BackupName) {{
    throw 'Exact pre-patch backup metadata was not found in the managed hosts line. Refusing to rewrite hosts; use Restore original hosts or re-enable override with the new version first.'
  }}
  if ($BackupName -notmatch '^hosts_[A-Za-z0-9_-]+_\\d{{8}}-\\d{{6}}-\\d{{3}}\\.bak$') {{
    throw ('Unsafe hosts backup metadata: ' + $BackupName)
  }}
  $BackupPath = Join-Path $BackupDir $BackupName
  if (-not (Test-Path -LiteralPath $BackupPath)) {{
    throw ('Exact pre-patch hosts backup was not found: ' + $BackupPath)
  }}
  Backup-AudionHosts -Kind 'before_disable' | Out-Null
  Copy-Item -LiteralPath $BackupPath -Destination $HostsPath -Force
  Write-Host ('Bitwise depatch restored hosts from: ' + $BackupPath)
  return
}}

$PrePatchBackup = Backup-AudionHosts -Kind 'prepatch'
$PrePatchBackupName = Split-Path -Leaf $PrePatchBackup

$NewLines = [System.Collections.Generic.List[string]]::new()
foreach ($Line in $Lines) {{
  if (Test-AudionHostsLineTarget -Line $Line) {{
    if ($Line.TrimStart().StartsWith('#')) {{
      [void]$NewLines.Add($Line)
    }} else {{
      [void]$NewLines.Add(('# ' + $ManagedMarker + ' disabled=' + (Get-Date -Format s) + ' original=' + $Line))
    }}
  }} else {{
    [void]$NewLines.Add($Line)
  }}
}}

if ($Mode -ne 'enable') {{
  throw ('Unsupported Bitrix hosts mode: ' + $Mode)
}}
if (-not $TargetIp) {{ throw 'IP address is empty; enable override needs an IP.' }}

$DetectedPorts = Get-AudionDetectedPorts
$EffectivePorts = @($ManualPorts + $DetectedPorts | Sort-Object -Unique)
$PortLabel = if ($EffectivePorts) {{ $EffectivePorts -join ',' }} else {{ 'none' }}
if ($DetectedPorts) {{
  Write-Host ('Detected open ports: ' + ($DetectedPorts -join ', '))
}} else {{
  Write-Host 'Detected open ports: none'
}}
Write-Host ('Ports saved in hosts metadata: ' + $PortLabel)

if ($NewLines.Count -gt 0 -and $NewLines[$NewLines.Count - 1].Trim()) {{
  [void]$NewLines.Add('')
}}
$Comment = '# ' + $ManagedMarker + '; ports=' + $PortLabel + '; backup=' + $PrePatchBackupName + '; updated=' + (Get-Date -Format s)
[void]$NewLines.Add(($TargetIp + "`t" + $TargetHost + "`t" + $Comment))
Write-AudionHostsLines -Lines $NewLines.ToArray()
Write-Host ('Enabled hosts override: ' + $TargetIp + ' -> ' + $TargetHost)
Write-Host ('Pre-patch hosts backup for exact depatch: ' + $PrePatchBackup)
"""
    context.log(f"Bitrix Hosts mode: {mode}")
    run_ps_command(context, script, progress_seconds=120.0, elevated=mode.lower() != "status")


def bitrix_hosts(context: JobContext) -> dict[str, object]:
    params = context.operation.parameters
    mode = str(params.get("mode", "status")).strip() or "status"
    host_name = str(params.get("host_name", "portal.itpgrad.ru")).strip() or "portal.itpgrad.ru"
    ip_address = str(params.get("ip_address", "")).strip()
    custom_ports = normalize_port_list(params.get("bitrix_ports"), [443, 80])
    host_name, custom_ports = normalize_endpoint_and_ports(host_name, custom_ports)
    ip_address, custom_ports = normalize_endpoint_and_ports(ip_address, custom_ports)
    scan_candidates = normalize_port_list(params.get("bitrix_port_scan_candidates"), [80, 443, 8080, 8443, 8890, 8891, 8892])
    auto_scan_ports = bool(params.get("bitrix_auto_scan_ports", True))
    if mode.lower() == "detect":
        return bitrix_detect_endpoint(context, host_name, custom_ports, scan_candidates)
    if mode.lower() == "status":
        bitrix_hosts_status(context, host_name, ip_address, custom_ports, scan_candidates, auto_scan_ports)
        return {"mode": mode, "host": host_name, "ip": ip_address, "ports": custom_ports, "auto_scan_ports": auto_scan_ports}
    bitrix_hosts_apply(context, mode, host_name, ip_address, custom_ports, scan_candidates, auto_scan_ports)
    return {"mode": mode, "host": host_name, "ip": ip_address, "ports": custom_ports, "auto_scan_ports": auto_scan_ports}


DEFAULT_APPS_POLICY_ACTIONS: dict[str, str] = {
    "status": "status",
    "snapshot": "snapshot_current",
    "export": "export_profile",
    "import": "import_profile",
    "apply": "apply_policy",
    "remove": "remove_policy",
    "cleanup": "cleanup_backups",
    "open_profiles": "open_profile_folder",
    "open_policy": "open_policy_folder",
    "open_backups": "open_backup_folder",
}


def default_apps_guard(context: JobContext) -> dict[str, object]:
    params = context.operation.parameters
    mode = str(params.get("mode", "status")).strip().lower() or "status"
    if mode == "policy_control":
        action = str(params.get("policy_action") or "status").strip().lower()
        resolved = DEFAULT_APPS_POLICY_ACTIONS.get(action)
        if resolved is None:
            raise RuntimeError(f"Unknown default apps policy action: {action}")
        context.log(f"Policy action: {action}")
        mode = resolved
    defaults = default_apps_guard_paths(context)

    backup_dir = resolve_user_path(context, params.get("backup_dir"), default=defaults["backup_dir"])
    profile_xml = resolve_user_path(context, params.get("profile_xml"), default=defaults["profile_xml"])
    policy_dir = resolve_user_path(context, params.get("program_data_dir"), default=defaults["policy_dir"])
    identifiers = normalize_string_list(params.get("check_identifiers")) or list(DEFAULT_APP_GUARD_IDENTIFIERS)
    identifiers = normalize_string_list([*identifiers, *normalize_string_list(params.get("extra_identifiers"))])
    strip_suggested = bool(params.get("strip_suggested", True))
    include_dism_inventory = bool(params.get("include_dism_inventory", False))
    remove_policy_xml = bool(params.get("remove_policy_xml", False))
    allow_unsupported_policy_edition = bool(params.get("allow_unsupported_policy_edition", False))
    backup_label = str(params.get("backup_label") or "").strip()
    backup_retention_days = integer_parameter(params.get("backup_retention_days"), 30, minimum=1, maximum=3650)
    cleanup_dry_run = bool(params.get("cleanup_dry_run", True))

    context.log(f"Default Apps Guard mode: {mode}")
    context.log(f"Policy dir: {policy_dir}")
    context.log(f"Profile XML: {profile_xml}")
    context.log(f"Backup dir: {backup_dir}")
    if backup_label:
        context.log(f"Backup label: {backup_label}")

    ensure_directory(backup_dir, label="Default Apps Guard backup folder")
    ensure_directory(profile_xml.parent, label="Default Apps Guard profile folder")

    if mode == "status":
        script = default_apps_guard_script(context, "Check-DefaultAppAssociations.ps1")
        run_ps1(
            context,
            script,
            {
                "PolicyDir": str(policy_dir),
                "ProfileXml": str(profile_xml),
                "BackupDir": str(backup_dir),
                "Identifiers": ",".join(identifiers),
                "IncludeDismInventory": include_dism_inventory,
            },
            cwd=script.parent,
            progress_seconds=120.0,
        )
        return {"mode": mode, "profile_xml": str(profile_xml), "policy_dir": str(policy_dir)}

    if mode in {"export_profile", "snapshot_current"}:
        script = default_apps_guard_script(context, "Export-DefaultAppAssociations.ps1")
        run_ps1(
            context,
            script,
            {
                "ProfileXml": str(profile_xml),
                "BackupDir": str(backup_dir),
                "BackupLabel": backup_label,
                "StripSuggested": strip_suggested,
                "BackupOnly": mode == "snapshot_current",
            },
            cwd=script.parent,
            elevated=True,
            progress_seconds=180.0,
        )
        return {"mode": mode, "profile_xml": str(profile_xml), "backup_dir": str(backup_dir)}

    if mode == "import_profile":
        import_profile_xml_raw = str(params.get("import_profile_xml") or "").strip()
        import_backup_xml_raw = str(params.get("import_backup_xml") or "").strip()
        source_xml_raw = import_profile_xml_raw or import_backup_xml_raw
        if not source_xml_raw:
            raise RuntimeError("Import source XML is empty. Select Backup XML or choose External XML.")
        import_profile_xml = resolve_user_path(context, source_xml_raw)
        script = default_apps_guard_script(context, "Import-DefaultAppProfile.ps1")
        run_ps1(
            context,
            script,
            {
                "SourceXml": str(import_profile_xml),
                "ProfileXml": str(profile_xml),
                "BackupDir": str(backup_dir),
                "StripSuggested": strip_suggested,
            },
            cwd=script.parent,
            progress_seconds=120.0,
        )
        return {"mode": mode, "source_xml": str(import_profile_xml), "profile_xml": str(profile_xml)}

    if mode == "apply_policy":
        context.log("Using the project elevation layer; no extra UAC appears when the GUI is already elevated.")
        script = default_apps_guard_script(context, "Apply-DefaultAppPolicy.ps1")
        run_ps1(
            context,
            script,
            {
                "SourceXml": str(profile_xml),
                "PolicyDir": str(policy_dir),
                "BackupDir": str(backup_dir),
                "BackupLabel": backup_label,
                "StripSuggested": strip_suggested,
                "AllowUnsupportedPolicyEdition": allow_unsupported_policy_edition,
            },
            cwd=script.parent,
            elevated=True,
            progress_seconds=240.0,
        )
        return {"mode": mode, "profile_xml": str(profile_xml), "policy_dir": str(policy_dir)}

    if mode == "remove_policy":
        context.log("Using the project elevation layer; no extra UAC appears when the GUI is already elevated.")
        script = default_apps_guard_script(context, "Remove-DefaultAppPolicy.ps1")
        run_ps1(
            context,
            script,
            {
                "PolicyDir": str(policy_dir),
                "BackupDir": str(backup_dir),
                "BackupLabel": backup_label,
                "RemovePolicyXml": remove_policy_xml,
            },
            cwd=script.parent,
            elevated=True,
            progress_seconds=180.0,
        )
        return {"mode": mode, "policy_dir": str(policy_dir), "backup_dir": str(backup_dir)}

    if mode == "cleanup_backups":
        script = default_apps_guard_script(context, "Cleanup-DefaultAppsBackups.ps1")
        run_ps1(
            context,
            script,
            {"BackupDir": str(backup_dir), "RetentionDays": backup_retention_days, "DryRun": cleanup_dry_run},
            cwd=script.parent,
            progress_seconds=120.0,
        )
        return {"mode": mode, "backup_dir": str(backup_dir), "retention_days": backup_retention_days}

    if mode in {"open_backup_folder", "open_profile_folder", "open_policy_folder"}:
        if mode == "open_backup_folder":
            path = backup_dir
        elif mode == "open_profile_folder":
            path = profile_xml.parent
        else:
            path = policy_dir
        path.mkdir(parents=True, exist_ok=True)
        context.log(f"Opening folder: {path}")
        if os.name == "nt":
            subprocess.Popen(["explorer.exe", str(path)])
        else:
            subprocess.Popen(["xdg-open", str(path)])
        context.progress(1.0)
        return {"mode": mode, "folder": str(path)}

    raise RuntimeError(f"Unknown Default Apps Guard mode: {mode}")


def association_defense_root(context: JobContext | Path | str) -> Path:
    if isinstance(context, JobContext):
        return context.paths.system_core / "association_defense"
    root = Path(context).resolve()
    return root / "system_core" / "association_defense"


def association_defense_script(context: JobContext, name: str) -> Path:
    script = association_defense_root(context) / name
    if not script.exists():
        raise RuntimeError(f"Association Defense script was not found: {script}")
    return script


MICROSOFT_APP_KEYS: tuple[str, ...] = (
    "ZuneMusic",
    "ZuneVideo",
    "Photos",
    "Clipchamp",
    "SoundRecorder",
    "Camera",
    "Paint",
    "ScreenSketch",
    "GamingApp",
    "XboxGamingOverlay",
    "XboxSpeechToTextOverlay",
    "XboxIdentityProvider",
    "SolitaireCollection",
    "YourPhone",
    "People",
    "Teams",
    "OutlookForWindows",
    "BingNews",
    "BingWeather",
    "Getstarted",
    "FeedbackHub",
    "WindowsMaps",
    "Copilot",
    "StickyNotes",
    "Todos",
    "OneNote",
    "Whiteboard",
    "PowerAutomateDesktop",
    "QuickAssist",
    "DevHome",
    "Family",
)

# AppLocker publisher rules are only written for the packaged apps the
# reinstall-block brick knows about.
APPLOCKER_APP_KEYS: tuple[str, ...] = ("Photos", "ZuneVideo", "ZuneMusic", "Clipchamp")

MICROSOFT_APP_DEFAULT_KEYS: tuple[str, ...] = ("ZuneMusic", "ZuneVideo")


def normalize_microsoft_app_keys(raw: Any, *, default: tuple[str, ...] = MICROSOFT_APP_DEFAULT_KEYS) -> list[str]:
    """Map GUI/CLI app selection onto catalog keys of Microsoft-Apps.ps1."""
    aliases = {key.casefold(): key for key in MICROSOFT_APP_KEYS}
    aliases.update(
        {
            "media player": "ZuneMusic",
            "zune": "ZuneMusic",
            "films": "ZuneVideo",
            "films&tv": "ZuneVideo",
            "microsoft.zunemusic": "ZuneMusic",
            "microsoft.zunevideo": "ZuneVideo",
            "microsoft.windows.photos": "Photos",
            "clipchamp.clipchamp": "Clipchamp",
            "microsoft.windowscamera": "Camera",
        }
    )
    if raw is None or raw == "":
        items: list[Any] = list(default)
    elif isinstance(raw, (list, tuple, set)):
        items = list(raw)
    else:
        text = str(raw).strip()
        items = [item.strip() for item in re.split(r"[,;|]+", text) if item.strip()] if text else list(default)

    selected: list[str] = []
    for item in items:
        value = str(item).strip()
        if not value:
            continue
        if value.casefold() == "all":
            return list(MICROSOFT_APP_KEYS)
        canonical = aliases.get(value.casefold())
        if canonical is None:
            raise RuntimeError(f"Unknown Microsoft app: {value}")
        if canonical not in selected:
            selected.append(canonical)
    return selected or list(default)


def microsoft_apps(context: JobContext) -> dict[str, object]:
    """In-box Microsoft apps: remove, restore, re-provision, lock, re-arm."""
    params = context.operation.parameters
    action = str(params.get("apps_action") or "status").strip().lower()
    dry_run = bool(params.get("dry_run", True))
    root = association_defense_root(context)
    selected = normalize_microsoft_app_keys(params.get("apps"))
    target = ",".join(selected)
    applocker_selected = [key for key in selected if key in APPLOCKER_APP_KEYS]

    def invoke(
        script_name: str,
        script_params: dict[str, Any],
        *,
        elevated: bool = False,
        progress_seconds: float = 180.0,
        check: bool = True,
    ) -> ProcessResult:
        script = association_defense_script(context, script_name)
        return run_ps1(
            context,
            script,
            script_params,
            cwd=root,
            check=check,
            progress_seconds=progress_seconds,
            elevated=elevated,
            windows_powershell=True,
        )

    context.log(f"Microsoft apps action: {action}")
    context.log(f"Selected apps: {target}")

    if action == "status":
        invoke("Microsoft-Apps.ps1", {"Status": True, "Target": target}, progress_seconds=300.0)
        invoke("Appx-Rearm.ps1", {"Status": True}, progress_seconds=120.0)
        if applocker_selected:
            invoke(
                "AppX-ReinstallBlock.ps1",
                {"Status": True, "Target": ",".join(applocker_selected)},
                progress_seconds=180.0,
                check=False,
            )
        return {"action": action, "apps": selected}

    if action == "remove":
        invoke(
            "Microsoft-Apps.ps1",
            {"Remove": True, "Target": target, "DryRun": dry_run},
            elevated=not dry_run,
            progress_seconds=900.0,
        )
        return {"action": action, "apps": selected, "dry_run": dry_run}

    if action == "restore":
        invoke("Microsoft-Apps.ps1", {"Restore": True, "Target": target}, elevated=True, progress_seconds=900.0)
        return {"action": action, "apps": selected}

    if action == "provision":
        invoke(
            "Microsoft-Apps.ps1",
            {"Provision": True, "Target": target, "DryRun": dry_run},
            elevated=not dry_run,
            progress_seconds=600.0,
        )
        return {"action": action, "apps": selected, "dry_run": dry_run}

    if action == "keep_removed":
        # Remove first, then let the scheduled task re-apply after feature updates.
        invoke(
            "Microsoft-Apps.ps1",
            {"Remove": True, "Target": target, "DryRun": dry_run},
            elevated=not dry_run,
            progress_seconds=900.0,
        )
        if applocker_selected:
            result = invoke(
                "AppX-ReinstallBlock.ps1",
                {"Enable": True, "Target": ",".join(applocker_selected), "DryRun": dry_run},
                elevated=not dry_run,
                progress_seconds=300.0,
                check=False,
            )
            if result.exit_code == 4:
                context.log("AppLocker rules are incomplete: at least one app is already absent, so its publisher identity could not be captured.")
            elif result.exit_code == 3:
                context.log("AppLocker is not available on this Windows edition; the scheduled re-apply is the remaining protection.")
            elif result.exit_code != 0:
                context.log(f"AppLocker reinstall-block returned exit code {result.exit_code}; continuing with the scheduled re-apply.")
        if dry_run:
            context.log("Dry run: the scheduled re-apply task was not registered.")
            return {"action": action, "apps": selected, "dry_run": True, "rearm": "skipped"}
        invoke("Appx-Rearm.ps1", {"Enable": True, "Target": target}, elevated=True, progress_seconds=240.0)
        return {"action": action, "apps": selected, "dry_run": False, "rearm": "enabled"}

    if action == "allow_back":
        invoke("Appx-Rearm.ps1", {"Disable": True}, elevated=True, progress_seconds=180.0)
        invoke("AppX-ReinstallBlock.ps1", {"Disable": True, "Target": "All"}, elevated=True, progress_seconds=300.0, check=False)
        context.log("Locks removed. Apps are not reinstalled; run Restore for that.")
        return {"action": action}

    if action == "rearm_check":
        invoke("Appx-Rearm.ps1", {"RunCheck": True}, elevated=True, progress_seconds=600.0)
        return {"action": action}

    if action == "open_logs":
        path = Path(os.environ.get("ProgramData", r"C:\ProgramData")) / "Audion" / "AppxGuard"
        path.mkdir(parents=True, exist_ok=True)
        open_path(context, path)
        return {"action": action, "folder": str(path)}

    raise RuntimeError(f"Unknown Microsoft apps action: {action}")


EDGE_WATCHED_IDENTIFIERS: tuple[str, ...] = (
    "http",
    "https",
    ".htm",
    ".html",
    ".pdf",
    ".svg",
    ".webp",
    ".xml",
)

EDGE_PROGID_PREFIXES: tuple[str, ...] = ("MSEdge", "AppXq0fevzme")


def _user_choice_prog_id(identifier: str) -> str:
    if os.name != "nt":
        return ""
    try:
        import winreg
    except ImportError:  # pragma: no cover - non-Windows
        return ""
    if identifier.startswith("."):
        path = rf"Software\Microsoft\Windows\CurrentVersion\Explorer\FileExts\{identifier}\UserChoice"
    else:
        path = rf"Software\Microsoft\Windows\Shell\Associations\UrlAssociations\{identifier}\UserChoice"
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, path) as key:
            value, _ = winreg.QueryValueEx(key, "ProgId")
            return str(value)
    except OSError:
        return ""


def edge_association_badges(root: Path | str | None = None) -> list[dict[str, str]]:
    """Badge row: which link/file types Microsoft Edge currently owns."""
    badges: list[dict[str, str]] = []
    owned = 0
    for identifier in EDGE_WATCHED_IDENTIFIERS:
        prog_id = _user_choice_prog_id(identifier)
        if not prog_id:
            badges.append({"label": identifier, "summary": "не задано", "summary_ru": "не задано", "tone": "neutral"})
            continue
        is_edge = any(prog_id.startswith(prefix) for prefix in EDGE_PROGID_PREFIXES)
        if is_edge:
            owned += 1
        badges.append(
            {
                "label": identifier,
                "summary": prog_id,
                "summary_ru": prog_id,
                "tone": "danger" if is_edge else "friendly",
                "hint": f"{identifier} -> {prog_id}",
                "hint_ru": f"{identifier} сейчас открывает {prog_id}." + (" Это Microsoft Edge." if is_edge else ""),
            }
        )
    summary_label = "Edge держит: " + (str(owned) if owned else "ничего")
    badges.insert(
        0,
        {
            "label": summary_label,
            "label_ru": summary_label,
            "tone": "danger" if owned else "friendly",
            "hint_ru": "Жёлтым отмечены типы, которые сейчас открывает Edge. Обновите список после смены браузера в Windows.",
        },
    )
    return badges


def edge_calm(context: JobContext) -> dict[str, object]:
    """Microsoft Edge calm-down policies; WebView2 stays protected."""
    params = context.operation.parameters
    action = str(params.get("edge_action") or "status").strip().lower()
    level_raw = str(params.get("edge_level") or "calm").strip().lower()
    level = "Quiet" if level_raw in {"quiet", "тихо", "hard"} else "Calm"
    dry_run = bool(params.get("dry_run", True))
    root = association_defense_root(context)

    def invoke(script_params: dict[str, Any], *, elevated: bool, progress_seconds: float) -> ProcessResult:
        script = association_defense_script(context, "Edge-Debloat.ps1")
        return run_ps1(
            context,
            script,
            script_params,
            cwd=root,
            progress_seconds=progress_seconds,
            elevated=elevated,
            windows_powershell=True,
        )

    context.log(f"Edge action: {action} (level: {level})")

    if action == "status":
        invoke({"Status": True, "Level": level}, elevated=False, progress_seconds=180.0)
        return {"action": action, "level": level}

    if action == "apply":
        invoke({"Enable": True, "Level": level, "DryRun": dry_run}, elevated=not dry_run, progress_seconds=240.0)
        return {"action": action, "level": level, "dry_run": dry_run}

    if action == "revert":
        invoke({"Disable": True, "DryRun": dry_run}, elevated=not dry_run, progress_seconds=240.0)
        return {"action": action, "dry_run": dry_run}

    if action == "webview2":
        invoke({"RepairWebView2": True, "DryRun": dry_run}, elevated=not dry_run, progress_seconds=600.0)
        return {"action": action, "dry_run": dry_run}

    raise RuntimeError(f"Unknown Edge action: {action}")


def association_defense(context: JobContext) -> dict[str, object]:
    """Expert tab: association snapshots, Defender exclusions and Drift Watch."""
    params = context.operation.parameters
    mode = str(params.get("mode") or "overview_control").strip().lower()
    root = association_defense_root(context)

    dry_run = bool(params.get("dry_run", False))
    snapshot_name = str(params.get("snapshot_name") or "Microsoft Snapshot").strip()
    snapshot_machine = str(params.get("snapshot_machine") or os.environ.get("COMPUTERNAME") or "").strip()
    group_name = str(params.get("group_name") or "").strip()
    group_custom_name = str(params.get("group_custom_name") or "").strip()
    group_ext = str(params.get("group_ext") or "").strip()

    def invoke(
        script_name: str,
        script_params: dict[str, Any],
        *,
        elevated: bool = False,
        progress_seconds: float = 180.0,
        check: bool = True,
    ) -> ProcessResult:
        script = association_defense_script(context, script_name)
        return run_ps1(
            context,
            script,
            script_params,
            cwd=root,
            check=check,
            progress_seconds=progress_seconds,
            elevated=elevated,
            windows_powershell=True,
        )

    def normalize_guards(raw: Any) -> list[str]:
        allowed = ("Defender", "Drift")
        aliases = {item.casefold(): item for item in allowed}
        aliases.update({"driftwatch": "Drift", "drift watch": "Drift"})
        if raw is None or raw == "":
            items: list[Any] = list(allowed)
        elif isinstance(raw, (list, tuple, set)):
            items = list(raw)
        else:
            text = str(raw).strip()
            items = [item.strip() for item in re.split(r"[,;|]+", text) if item.strip()] if text else list(allowed)
        selected: list[str] = []
        for item in items:
            value = str(item).strip()
            if not value:
                continue
            if value.casefold() == "all":
                return list(allowed)
            canonical = aliases.get(value.casefold())
            if canonical is None:
                raise RuntimeError(f"Unknown watch target: {value}")
            if canonical not in selected:
                selected.append(canonical)
        return selected or list(allowed)

    context.log(f"Association defense mode: {mode}")
    context.log(f"Association defense root: {root}")

    if mode == "overview_control":
        action = str(params.get("overview_action") or "status_all").strip().lower()
        if action == "status_all":
            invoke("Defense.ps1", {"Status": True}, progress_seconds=420.0)
            return {"mode": mode, "action": action}
        if action == "open_folder":
            open_path(context, root)
            return {"mode": mode, "action": action, "folder": str(root)}
        if action == "open_snapshots":
            path = root / "snapshots"
            open_path(context, path)
            return {"mode": mode, "action": action, "folder": str(path)}
        raise RuntimeError(f"Unknown overview action: {action}")

    if mode == "guards_control":
        action = str(params.get("guard_action") or "status").strip().lower()
        selected = normalize_guards(params.get("guard_targets"))
        script_by_guard = {"Defender": "Defender-Exclusions.ps1", "Drift": "Drift-Watch.ps1"}
        param_by_action = {"status": {"Status": True}, "enable": {"Enable": True}, "disable": {"Disable": True}}
        context.log(f"Watch action: {action}")
        context.log(f"Selected: {', '.join(selected)}")

        if action == "run_check":
            if "Drift" not in selected:
                raise RuntimeError("Run-check applies to Drift Watch only. Select Drift or choose Status/Enable/Disable.")
            invoke("Drift-Watch.ps1", {"RunCheck": True}, progress_seconds=180.0)
            return {"mode": mode, "action": action, "guards": ["Drift"]}

        if action not in param_by_action:
            raise RuntimeError(f"Unknown watch action: {action}")
        for guard in selected:
            invoke(
                script_by_guard[guard],
                param_by_action[action],
                elevated=action in {"enable", "disable"},
                progress_seconds=240.0 if guard == "Defender" else 180.0,
            )
        return {"mode": mode, "action": action, "guards": selected}

    if mode == "snapshot_control":
        action = str(params.get("snapshot_action") or "status").strip().lower()
        if action == "open_snapshots":
            path = root / "snapshots"
            open_path(context, path)
            return {"mode": mode, "action": action, "folder": str(path)}
        snapshot_actions: dict[str, tuple[dict[str, Any], bool, float]] = {
            "status": ({"Status": True, "Name": snapshot_name, "Machine": snapshot_machine}, False, 180.0),
            "capture": ({"Enable": True, "Name": snapshot_name, "Machine": snapshot_machine, "DryRun": dry_run}, not dry_run, 240.0),
        }
        if action not in snapshot_actions:
            raise RuntimeError(f"Unknown snapshot action: {action}")
        script_params, elevated, progress_seconds = snapshot_actions[action]
        invoke("Golden-Snapshot.ps1", script_params, elevated=elevated, progress_seconds=progress_seconds)
        return {"mode": mode, "action": action, "snapshot": snapshot_name, "dry_run": dry_run}

    if mode == "groups_control":
        action = str(params.get("group_action") or "status").strip().lower()
        selected_group = (group_custom_name if group_name.casefold() == "custom" else group_name).strip()
        if action == "commit" and not selected_group:
            raise RuntimeError("Group name is empty.")
        group_actions: dict[str, tuple[dict[str, Any], bool, float]] = {
            "status": ({"Status": True, "Name": snapshot_name, "Machine": snapshot_machine}, False, 180.0),
            "compose": ({"Compose": True, "Name": snapshot_name, "Machine": snapshot_machine, "DryRun": dry_run}, not dry_run, 180.0),
            "commit": (
                {
                    "Commit": selected_group,
                    "Ext": group_ext,
                    "Name": snapshot_name,
                    "Machine": snapshot_machine,
                    "DryRun": dry_run,
                },
                not dry_run,
                240.0,
            ),
        }
        if action not in group_actions:
            raise RuntimeError(f"Unknown group snapshot action: {action}")
        script_params, elevated, progress_seconds = group_actions[action]
        invoke("Group-Snapshot.ps1", script_params, elevated=elevated, progress_seconds=progress_seconds)
        return {"mode": mode, "action": action, "group": selected_group, "dry_run": dry_run}

    raise RuntimeError(f"Unknown Association Defense mode: {mode}")


def driver_update_blocker_root(context: JobContext | Path | str) -> Path:
    if isinstance(context, JobContext):
        return context.paths.system_core / "windows_driver_guard"
    root = Path(context).resolve()
    return root / "system_core" / "windows_driver_guard"


def driver_update_blocker_script(context: JobContext, name: str) -> Path:
    script = driver_update_blocker_root(context) / name
    if not script.exists():
        raise RuntimeError(f"Driver Update Blocker script was not found: {script}")
    return script


def driver_backup_options(root: Path | str | None = None) -> list[dict[str, str]]:
    project_root = Path(root).resolve() if root else Path(__file__).resolve().parents[2]
    backup_root = project_root / "backup" / "driver_guard" / "driver_store"
    options: list[dict[str, str]] = [
        {
            "value": "",
            "label": "Newest available driver backup",
            "label_ru": "Самый свежий backup драйверов",
        }
    ]
    if not backup_root.exists():
        return options
    backups = [
        item
        for item in backup_root.iterdir()
        if item.is_dir() and (item / "drivers").is_dir()
    ]
    backups.sort(key=lambda item: item.stat().st_mtime, reverse=True)
    for item in backups:
        stamp = datetime.fromtimestamp(item.stat().st_mtime).strftime("%Y-%m-%d %H:%M")
        inf_count = len(list((item / "drivers").rglob("*.inf")))
        label = f"{stamp} | {inf_count} INF | {item.name}"
        options.append({"value": str(item), "label": label, "label_ru": label})
    return options


def driver_update_blocker(context: JobContext) -> dict[str, object]:
    params = context.operation.parameters
    mode = str(params.get("mode", "")).strip().lower()
    root = driver_update_blocker_root(context)

    script_by_mode = {
        "status": "Show-Driver-Block-Status.ps1",
        "block_all": "Block-All-WU-Driver-Updates.ps1",
        "unblock_all": "Unblock-All-WU-Driver-Updates.ps1",
        "status_hwid": "Set-HardwareId-DriverInstallRestriction.ps1",
        "block_hwid": "Set-HardwareId-DriverInstallRestriction.ps1",
        "unblock_hwid": "Set-HardwareId-DriverInstallRestriction.ps1",
        "repair_rank_hwid_status": "Repair-DriverRank-ByHardwareId.ps1",
        "repair_rank_hwid": "Repair-DriverRank-ByHardwareId.ps1",
        "block_nvidia": "Block-NVIDIA-Driver-Updates.ps1",
        "unblock_nvidia": "Unblock-NVIDIA-Driver-Updates.ps1",
        "backup_manifest": "Backup-DriverStore-Manifest.ps1",
        "export_drivers": "Export-Installed-Drivers.ps1",
        "restore_drivers": "Restore-Exported-Drivers.ps1",
    }

    if mode in script_by_mode:
        script = driver_update_blocker_script(context, script_by_mode[mode])
        script_params: dict[str, Any] = {}
        elevated = mode not in {"status", "status_hwid", "repair_rank_hwid_status", "backup_manifest"}
        progress_seconds = 300.0

        if mode == "block_nvidia":
            script_params["IncludeCompatibleIds"] = bool(params.get("include_compatible_ids", False))
            script_params["Retroactive"] = bool(params.get("nvidia_retroactive", False))
            elevated = True
        elif mode in {"status_hwid", "block_hwid", "unblock_hwid"}:
            hardware_ids = str(params.get("target_hardware_ids") or params.get("hardware_id_list") or "").strip()
            device_instance_id = str(params.get("target_device_instance_id") or "").strip()
            if hardware_ids:
                script_params["HardwareIdList"] = hardware_ids
            elif mode != "status_hwid":
                raise RuntimeError("Hardware IDs are required for this HWID driver restriction action.")
            if device_instance_id:
                script_params["DeviceInstanceId"] = device_instance_id
            if mode == "status_hwid":
                script_params["Status"] = True
                progress_seconds = 120.0
            else:
                script_params["Retroactive"] = bool(params.get("hwid_retroactive", False))
                script_params["KeepGlobalWindowsUpdateDriverBlock"] = bool(params.get("hwid_keep_global_wu_block", False))
                if mode == "unblock_hwid":
                    script_params["Unblock"] = True
                elevated = True
                progress_seconds = 180.0
        elif mode in {"repair_rank_hwid", "repair_rank_hwid_status"}:
            hardware_ids = str(params.get("target_hardware_ids") or params.get("hardware_id_list") or "").strip()
            if not hardware_ids:
                raise RuntimeError("Hardware IDs are required for HWID driver rank repair.")
            script_params["HardwareIdList"] = hardware_ids
            optional_text_params = {
                "DeviceInstanceId": str(params.get("target_device_instance_id") or "").strip(),
                "BadVersion": str(params.get("bad_driver_version") or "").strip(),
                "TargetVersion": str(params.get("target_driver_version") or "").strip(),
                "TargetInfPath": str(params.get("target_inf_path") or "").strip(),
                "TargetInfNamePattern": str(params.get("target_inf_name_pattern") or "").strip(),
                "DriverClass": str(params.get("driver_rank_class") or "").strip(),
            }
            for key, value in optional_text_params.items():
                if value:
                    script_params[key] = value
            if bool(params.get("skip_current_version_check", False)):
                script_params["SkipCurrentVersionCheck"] = True
            if bool(params.get("allow_version_only_target_inf_fallback", False)):
                script_params["AllowVersionOnlyTargetInfFallback"] = True
            if bool(params.get("hwid_keep_global_wu_block", False)):
                script_params["KeepGlobalWindowsUpdateDriverBlock"] = True
            if bool(params.get("no_policy_block_after_repair", False)):
                script_params["NoPolicyBlock"] = True
            if mode == "repair_rank_hwid_status":
                script_params["Status"] = True
                elevated = False
                progress_seconds = 180.0
            else:
                elevated = True
                progress_seconds = 1200.0
        elif mode == "backup_manifest":
            progress_seconds = 120.0
        elif mode == "export_drivers":
            progress_seconds = 900.0
            elevated = True
        elif mode == "restore_drivers":
            backup_path = str(params.get("driver_backup_path") or params.get("driver_backup_select") or "").strip()
            if backup_path:
                script_params["BackupPath"] = backup_path
            script_params["NoPrompt"] = True
            progress_seconds = 900.0
            elevated = True

        run_ps1(context, script, script_params, cwd=script.parent, progress_seconds=progress_seconds, elevated=elevated)
        return {"mode": mode, "script": str(script)}

    if mode in {"open_tool_folder", "open_policy_backups", "open_driver_backups", "open_reg_fallback"}:
        if mode == "open_policy_backups":
            path = context.paths.backup / "driver_guard" / "policy"
        elif mode == "open_driver_backups":
            path = context.paths.backup / "driver_guard" / "driver_store"
        elif mode == "open_reg_fallback":
            path = context.paths.output / "driver_guard" / "reg_fallback"
        else:
            path = root
        open_path(context, path)
        return {"mode": mode, "folder": str(path)}

    raise RuntimeError(f"Unknown Driver Update Blocker mode: {mode}")


def driver_firmware_audit(context: JobContext) -> dict[str, object]:
    params = context.operation.parameters
    script = context.paths.system_core / "diagnostics" / "Invoke-WindowsDriverFirmwareAudit.ps1"
    if not script.exists():
        raise RuntimeError(f"Windows Driver/Firmware Audit script was not found: {script}")

    output_dir = resolve_user_path(context, params.get("output_dir"), default=context.paths.logs)
    output_dir.mkdir(parents=True, exist_ok=True)

    script_params: dict[str, Any] = {
        "OutputDir": str(output_dir),
        "OpenReport": bool(params.get("open_report")),
        "Json": bool(params.get("json")),
        "Csv": bool(params.get("csv")),
    }
    context.log("Windows Driver/Firmware Audit is read-only.")
    run_ps1(context, script, script_params, cwd=context.paths.root, progress_seconds=120.0, elevated=False)
    return {"script": str(script), "output_dir": str(output_dir)}


def keykit_default_dir(context: JobContext, mode: str, subfolder: str) -> Path:
    """Export writes to `output\\<subfolder>`, import reads from `input`.

    The same two doors every other pack uses: a tool that invents its own folder
    makes the user remember where each one hides its result.

    Both KeyKit packs route through here, and both depend on the manifest field
    staying empty by default and opting out of workbench routing. The GUI and the
    CLI send a field's manifest default as a real parameter, and the GUI replaces
    the value of any `folder` field with the SOURCE/TARGET path from the top
    panel unless the field carries `workbench_route: false`. Either one silently
    overrides the choice made here — on 14 August 2026 the second one sent an SSH
    key export into `input`.
    """
    return context.paths.input if mode.startswith("import") else context.paths.output / subfolder


def ssh_keykit(context: JobContext) -> dict[str, object]:
    params = context.operation.parameters
    mode = str(params.get("mode") or "export_client").strip().lower()
    tool_root = project_tool_dir(context, "ssh_keykit")

    if mode == "open_tool_folder":
        open_path(context, tool_root)
        return {"folder": str(tool_root)}

    default_root = keykit_default_dir(context, mode, "ssh_keykit")
    root_dir = resolve_user_path(context, params.get("ssh_root"), default=default_root)
    root_dir.mkdir(parents=True, exist_ok=True)
    profile_name = str(params.get("profile_name") or os.environ.get("COMPUTERNAME") or "").strip()
    user_name = str(params.get("user_name") or os.environ.get("USERNAME") or "").strip()
    snapshot = str(params.get("snapshot") or "").strip()

    script_params: dict[str, Any] = {
        "RootDir": str(root_dir),
        "ProfileName": profile_name,
        "UserName": user_name,
    }

    if mode == "check_links":
        # Access breaks quietly: keys and configuration files all stay in
        # place, only the paths inside them stop matching reality. Nothing is
        # copied or changed here, so the root/profile/user arguments the other
        # modes need would only be noise.
        script = tool_root / "Test-SSHAccessLinks.ps1"
        script_params = {}
        for key, value in (
            ("SshConfig", params.get("ssh_config_path")),
            ("RcloneConfig", params.get("rclone_config_path")),
            ("ReportPath", params.get("links_report_path")),
        ):
            text_value = str(value or "").strip()
            if text_value:
                script_params[key] = str(resolve_user_path(context, text_value))
        # Default is on: a check that reports breakage and still exits clean
        # teaches the operator to ignore it.
        stop_on_broken = params.get("fail_on_broken")
        script_params["FailOnBroken"] = True if stop_on_broken is None else bool(stop_on_broken)
    elif mode in {"export_client", "export_all"}:
        script = tool_root / "Export-OpenSSHKeys.ps1"
        script_params["IncludeServerKeys"] = mode == "export_all"
    elif mode in {"import_client", "import_all"}:
        script = tool_root / "Import-OpenSSHKeys.ps1"
        script_params["ImportServerKeys"] = mode == "import_all"
        if snapshot:
            script_params["Snapshot"] = snapshot
    else:
        raise RuntimeError(f"Unknown SSH KeyKit mode: {mode}")

    elevated = mode in {"export_all", "import_all"}
    context.log(f"SSH KeyKit mode: {mode}")
    if mode != "check_links":
        context.log(f"SSH KeyKit root: {root_dir}")
    run_ps1(context, script, script_params, cwd=tool_root, progress_seconds=180.0, elevated=elevated)
    return {"mode": mode, "root_dir": str(root_dir), "script": str(script)}


def ai_backup(context: JobContext) -> dict[str, object]:
    """Back up / restore Claude Code and Codex CLI data through Workbench I/O.

    Export writes to output\\ai_backup, import reads from input - the same two
    doors every pack uses, so no path field is needed. -Yes is forced on import
    so the GUI does not stall on the script's confirmation prompt.
    """
    params = context.operation.parameters
    mode = str(params.get("mode") or "export").strip().lower()
    if mode not in {"export", "import", "merge", "open_tool_folder"}:
        raise RuntimeError(f"Unknown AI Backup mode: {mode}")
    tool_root = project_tool_dir(context, "ai_backup")

    if mode == "open_tool_folder":
        open_path(context, tool_root)
        return {"folder": str(tool_root)}

    # Import and Merge both read a backup staged in input; Export writes to output.
    reads_input = mode in ("import", "merge")
    io_dir = context.paths.input if reads_input else context.paths.output / "ai_backup"
    io_dir.mkdir(parents=True, exist_ok=True)
    # "Move only the essentials" shapes both export and restore. Authentication
    # is intentionally independent because those files are password-equivalent.
    essentials = bool(params.get("essentials", True))

    ps_mode = {"import": "Import", "merge": "Merge"}.get(mode, "Export")
    script = tool_root / "AI-Backup.ps1"
    script_params: dict[str, Any] = {
        "Mode": ps_mode,
        "Path": str(io_dir),
    }
    # -Full only shapes an export/restore copy; it means nothing to a memory merge.
    if not essentials and mode != "merge":
        script_params["Full"] = True
    if bool(params.get("include_auth", False)) and mode != "merge":
        script_params["IncludeAuth"] = True
    if bool(params.get("dry_run", False)) and mode in ("import", "merge"):
        script_params["DryRun"] = True
    if bool(params.get("allow_foreign_paths", False)) and mode == "import":
        script_params["AllowForeignPaths"] = True
    if bool(params.get("allow_legacy", False)) and mode in ("import", "merge"):
        script_params["AllowLegacy"] = True
    if mode == "import":
        script_params["Yes"] = True
    # Merge keeps local files on name clashes unless the "Overwrite" box is ticked.
    if mode == "merge" and bool(params.get("overwrite", False)):
        script_params["Overwrite"] = True

    context.log(f"AI Backup mode: {mode}")
    context.log(f"AI Backup I/O: {io_dir}")
    run_ps1(context, script, script_params, cwd=tool_root, progress_seconds=600.0)
    return {"mode": mode, "path": str(io_dir), "script": str(script)}


_CERT_VALID_STORES = {
    "CurrentUser\\My",
    "LocalMachine\\My",
    "CurrentUser\\Root",
    "LocalMachine\\Root",
    "CurrentUser\\CA",
    "LocalMachine\\CA",
}


def _cert_store_or_default(value: Any, default: str) -> str:
    store = str(value or "").strip().replace("/", "\\")
    return store if store in _CERT_VALID_STORES else default


def certificate_keykit(context: JobContext) -> dict[str, object]:
    params = context.operation.parameters
    mode = str(params.get("mode") or "status").strip().lower()

    # Import names its own file, so for import `input` only decides which folder
    # is prepared and logged.
    default_cert_dir = keykit_default_dir(context, mode, "certificates")
    backup_dir = resolve_user_path(
        context,
        params.get("cert_backup_dir"),
        default=default_cert_dir,
    )
    backup_dir.mkdir(parents=True, exist_ok=True)

    if mode == "open_folder":
        open_path(context, backup_dir)
        return {"folder": str(backup_dir)}

    store = _cert_store_or_default(params.get("cert_store"), "CurrentUser\\My")
    import_store = _cert_store_or_default(params.get("import_store"), store)
    password = str(params.get("pfx_password") or "")
    import_file = str(params.get("import_file") or "").strip()

    context.log(f"Certificate KeyKit mode: {mode}")
    context.log(f"Store: {store}")
    context.log(f"Backup dir: {backup_dir}")

    if mode == "status":
        script = f"""
$ErrorActionPreference = 'Continue'
$Store = {ps_quote(store)}
Write-Host ('=== Certificates in Cert:\\' + $Store + ' ===')
$items = @(Get-ChildItem -Path ('Cert:\\' + $Store) -ErrorAction SilentlyContinue)
if (-not $items) {{ Write-Host '(empty or not accessible from this context)'; exit 0 }}
foreach ($c in $items) {{
  $exportable = 'n/a (no private key)'
  if ($c.HasPrivateKey) {{
    $exportable = 'Unknown'
    try {{
      $rsa = [System.Security.Cryptography.X509Certificates.RSACertificateExtensions]::GetRSAPrivateKey($c)
      if ($rsa -and $rsa.Key -and ($rsa.Key.PSObject.Properties.Name -contains 'ExportPolicy')) {{
        if ($rsa.Key.ExportPolicy -band [System.Security.Cryptography.CngExportPolicies]::AllowExport) {{
          $exportable = 'Yes'
        }} else {{
          $exportable = 'No (TPM / non-exportable)'
        }}
      }}
    }} catch {{ $exportable = 'Unknown' }}
  }}
  Write-Host ('-' * 60)
  Write-Host ('Subject    : ' + $c.Subject)
  Write-Host ('Thumbprint : ' + $c.Thumbprint)
  Write-Host ('Expires    : ' + $c.NotAfter)
  Write-Host ('PrivateKey : ' + $c.HasPrivateKey)
  Write-Host ('Exportable : ' + $exportable)
}}
Write-Host ('-' * 60)
Write-Host ('Total: ' + $items.Count)
exit 0
"""
        run_ps_command(context, script, check=False, progress_seconds=60.0, elevated=store.startswith("LocalMachine"))
        return {"mode": mode, "store": store}

    if mode == "export_pfx":
        if not password:
            raise RuntimeError("PFX password is empty. Set 'PFX password' before exporting private keys.")
        context.log("Exporting exportable private-key certificates to password-protected .pfx files.")
        context.log("TPM-bound / non-exportable keys are reported as SKIP; they cannot survive reinstall as PFX.")
        script = f"""
$ErrorActionPreference = 'Continue'
$Store = {ps_quote(store)}
$BackupDir = {ps_quote(backup_dir)}
$PasswordText = [Console]::In.ReadLine()
if ([string]::IsNullOrEmpty($PasswordText)) {{ throw 'PFX password was not supplied through stdin.' }}
$Password = ConvertTo-SecureString -String $PasswordText -Force -AsPlainText
$ok = 0; $fail = 0
$carried = @()
foreach ($c in @(Get-ChildItem -Path ('Cert:\\' + $Store) -ErrorAction SilentlyContinue | Where-Object {{ $_.HasPrivateKey }})) {{
  $out = Join-Path $BackupDir ($c.Thumbprint + '.pfx')
  try {{
    Export-PfxCertificate -Cert $c.PSPath -FilePath $out -Password $Password -ChainOption BuildChain -ErrorAction Stop | Out-Null
    Write-Host ('OK   ' + $c.Thumbprint + '  ' + $c.Subject)
    $carried += [pscustomobject]@{{
      thumbprint = $c.Thumbprint
      subject    = $c.Subject
      store      = $Store
      file       = ($c.Thumbprint + '.pfx')
      expires    = $c.NotAfter.ToString('yyyy-MM-dd')
    }}
    $ok++
  }} catch {{
    Write-Host ('SKIP ' + $c.Thumbprint + '  ' + $c.Subject + '  -> ' + $_.Exception.Message)
    $fail++
  }}
}}
# The store each certificate came from is written down here. Without it an
# unattended import has to guess where a .pfx belongs, and a certificate in the
# wrong store is a certificate that silently does nothing.
$map = [pscustomobject]@{{
  format       = 1
  created      = (Get-Date).ToString('yyyy-MM-dd HH:mm:ss')
  machine      = $env:COMPUTERNAME
  certificates = $carried
}}
$mapPath = Join-Path $BackupDir 'certificates.json'
$map | ConvertTo-Json -Depth 5 | Set-Content -LiteralPath $mapPath -Encoding UTF8
Write-Host ''
Write-Host ('Exported: ' + $ok + ', skipped/non-exportable: ' + $fail)
Write-Host ('Map written: ' + $mapPath)
Write-Host ('Export folder (CONTAINS PRIVATE KEYS): ' + $BackupDir)
exit 0
"""
        run_ps_command(context, script, check=False, progress_seconds=300.0, elevated=store.startswith("LocalMachine"), input_text=password + "\n")
        return {"mode": mode, "store": store, "backup_dir": str(backup_dir)}

    if mode == "export_roots":
        context.log("Exporting selected store's public certificates to an .sst bundle (no private keys).")
        script = f"""
$ErrorActionPreference = 'Stop'
$Store = {ps_quote(store)}
$BackupDir = {ps_quote(backup_dir)}
$Stamp = Get-Date -Format 'yyyyMMdd_HHmmss'
$out = Join-Path $BackupDir (($Store -replace '\\\\','_') + '_' + $Stamp + '.sst')
$items = @(Get-ChildItem -Path ('Cert:\\' + $Store) -ErrorAction Stop)
if (-not $items) {{ Write-Host 'Store is empty; nothing exported.'; exit 0 }}
$items | Export-Certificate -FilePath $out -Type SST | Out-Null
Write-Host ('Exported ' + $items.Count + ' public certs to: ' + $out)
exit 0
"""
        run_ps_command(context, script, check=False, progress_seconds=120.0, elevated=store.startswith("LocalMachine"))
        return {"mode": mode, "store": store, "backup_dir": str(backup_dir)}

    if mode == "import_pfx":
        if not import_file:
            raise RuntimeError("Import file is empty. Select a .pfx file in Advanced.")
        if not password:
            raise RuntimeError("PFX password is empty. Set 'PFX password' to import a .pfx.")
        context.log(f"Importing PFX into Cert:\\{import_store} (private key marked exportable).")
        script = f"""
$ErrorActionPreference = 'Stop'
$ImportStore = {ps_quote(import_store)}
$ImportFile = {ps_quote(import_file)}
$PasswordText = [Console]::In.ReadLine()
if ([string]::IsNullOrEmpty($PasswordText)) {{ throw 'PFX password was not supplied through stdin.' }}
$Password = ConvertTo-SecureString -String $PasswordText -Force -AsPlainText
Import-PfxCertificate -FilePath $ImportFile -CertStoreLocation ('Cert:\\' + $ImportStore) -Password $Password -Exportable |
  Format-List Subject, Thumbprint | Out-String | Write-Host
Write-Host ('Imported PFX into Cert:\\' + $ImportStore)
exit 0
"""
        run_ps_command(context, script, progress_seconds=120.0, elevated=import_store.startswith("LocalMachine"), input_text=password + "\n")
        return {"mode": mode, "import_store": import_store, "import_file": import_file}

    if mode == "import_pfx_folder":
        # A whole folder at once. It works because collecting encrypts every
        # .pfx with the same password from the form, and because the export
        # wrote down which store each certificate came from.
        if not password:
            raise RuntimeError("PFX password is empty. Set 'PFX password' to import certificates.")
        map_file = backup_dir / "certificates.json"
        if not map_file.is_file():
            raise RuntimeError(
                f"Certificate map was not found: {map_file}. "
                "Import one file at a time, or collect the certificates again."
            )
        certificate_map = json.loads(map_file.read_text(encoding="utf-8"))
        if int(certificate_map.get("format", 0)) != 1:
            raise RuntimeError(f"Certificate map format {certificate_map.get('format')!r} is not supported.")
        entries = certificate_map.get("certificates") or []
        if not entries:
            context.log("The certificate map lists nothing; nothing to import.")
            return {"mode": mode, "imported": 0, "skipped": 0}

        imported = 0
        skipped = 0
        for entry in entries:
            file_name = str(entry.get("file") or "")
            source = backup_dir / file_name
            target_store = _cert_store_or_default(entry.get("store"), import_store)
            if not source.is_file():
                context.log(f"SKIP {file_name}: not in {backup_dir}")
                skipped += 1
                continue
            context.log(f"Importing {file_name} into Cert:\\{target_store} — {entry.get('subject', '')}")
            script = f"""
$ErrorActionPreference = 'Stop'
$ImportStore = {ps_quote(target_store)}
$ImportFile = {ps_quote(str(source))}
$PasswordText = [Console]::In.ReadLine()
if ([string]::IsNullOrEmpty($PasswordText)) {{ throw 'PFX password was not supplied through stdin.' }}
$Password = ConvertTo-SecureString -String $PasswordText -Force -AsPlainText
Import-PfxCertificate -FilePath $ImportFile -CertStoreLocation ('Cert:\\' + $ImportStore) -Password $Password -Exportable |
  Format-List Subject, Thumbprint | Out-String | Write-Host
exit 0
"""
            try:
                run_ps_command(
                    context,
                    script,
                    progress_seconds=120.0,
                    elevated=target_store.startswith("LocalMachine"),
                    input_text=password + "\n",
                )
                imported += 1
            except Exception as exc:
                # One certificate refusing is not a reason to leave the rest of
                # the folder unimported; the failures are counted and named.
                context.log(f"ERROR: {file_name} was not imported: {exc}")
                skipped += 1

        context.log(f"Imported: {imported}. Skipped or failed: {skipped}.")
        if imported == 0 and skipped:
            raise RuntimeError("No certificate was imported; see the log above.")
        return {"mode": mode, "imported": imported, "skipped": skipped}

    if mode == "import_cert":
        if not import_file:
            raise RuntimeError("Import file is empty. Select a .cer/.crt/.sst file in Advanced.")
        context.log(f"Importing public certificate/CA into Cert:\\{import_store}.")
        script = f"""
$ErrorActionPreference = 'Stop'
$ImportStore = {ps_quote(import_store)}
$ImportFile = {ps_quote(import_file)}
Import-Certificate -FilePath $ImportFile -CertStoreLocation ('Cert:\\' + $ImportStore) |
  Format-List Subject, Thumbprint | Out-String | Write-Host
Write-Host ('Imported certificate(s) into Cert:\\' + $ImportStore)
exit 0
"""
        run_ps_command(context, script, progress_seconds=120.0, elevated=import_store.startswith("LocalMachine"))
        return {"mode": mode, "import_store": import_store, "import_file": import_file}

    raise RuntimeError(f"Unknown Certificate KeyKit mode: {mode}")


# --- Fonts installed for this user --------------------------------------------
#
# Windows keeps two font sets: the system one in C:\Windows\Fonts under HKLM,
# which comes back with Windows, and the per-user one in the profile under HKCU,
# which does not come back at all. This pack only ever reads and writes the
# second: a per-user install needs no elevation and cannot damage the set the
# system owns.


def fonts_kit(context: JobContext) -> dict[str, object]:
    params = context.operation.parameters
    mode = str(params.get("mode") or "status").strip().lower()
    tool_root = project_tool_dir(context, "fonts_kit")

    if mode == "status":
        run_ps1(
            context,
            tool_root / "Get-UserFonts.ps1",
            {"IncludeSystem": bool(params.get("include_system", False))},
            cwd=tool_root,
            progress_seconds=60.0,
        )
        return {"mode": mode}

    default_folder = (
        context.paths.input if mode.startswith("import") else context.paths.output / "fonts"
    )
    folder = resolve_user_path(context, params.get("fonts_folder"), default=default_folder)

    if mode == "open_folder":
        open_path(context, folder)
        return {"folder": str(folder)}

    folder.mkdir(parents=True, exist_ok=True)
    if mode == "export":
        run_ps1(
            context,
            tool_root / "Export-UserFonts.ps1",
            {"TargetDir": str(folder)},
            cwd=tool_root,
            progress_seconds=300.0,
        )
        return {"mode": mode, "folder": str(folder)}

    if mode == "import":
        run_ps1(
            context,
            tool_root / "Import-UserFonts.ps1",
            {"SourceDir": str(folder)},
            cwd=tool_root,
            progress_seconds=300.0,
        )
        return {"mode": mode, "folder": str(folder)}

    raise RuntimeError(f"Unknown Fonts mode: {mode}")


# --- Shell environment --------------------------------------------------------
#
# The two files that make a terminal feel like yours: the Windows Terminal
# settings and the PowerShell profile. Neither is stored by any account, and
# both are edited by hand over years.


def shell_kit(context: JobContext) -> dict[str, object]:
    params = context.operation.parameters
    mode = str(params.get("mode") or "status").strip().lower()
    tool_root = project_tool_dir(context, "shell_kit")

    if mode == "status":
        run_ps1(
            context,
            tool_root / "Get-ShellEnvironment.ps1",
            {},
            cwd=tool_root,
            progress_seconds=60.0,
        )
        return {"mode": mode}

    default_folder = (
        context.paths.input if mode.startswith("import") else context.paths.output / "shell"
    )
    folder = resolve_user_path(context, params.get("shell_folder"), default=default_folder)

    if mode == "open_folder":
        open_path(context, folder)
        return {"folder": str(folder)}

    folder.mkdir(parents=True, exist_ok=True)
    if mode == "export":
        run_ps1(
            context,
            tool_root / "Export-ShellEnvironment.ps1",
            {"TargetDir": str(folder)},
            cwd=tool_root,
            progress_seconds=120.0,
        )
        return {"mode": mode, "folder": str(folder)}

    if mode == "import":
        run_ps1(
            context,
            tool_root / "Import-ShellEnvironment.ps1",
            {"SourceDir": str(folder)},
            cwd=tool_root,
            progress_seconds=120.0,
        )
        return {"mode": mode, "folder": str(folder)}

    raise RuntimeError(f"Unknown Shell environment mode: {mode}")


# --- Access named by configuration --------------------------------------------
#
# Exporting `.ssh` carries the keys that live in `.ssh`. It does not carry the
# key a config line points at on another disk, and that is not a rare setup: on
# this machine three of the four private keys named by ssh and rclone live
# outside the profile entirely. Such a migration arrives looking complete and
# fails on the first connection.
#
# So this pack collects by reference instead of by location: it runs the same
# link check the SSH pack runs, and copies every file that configuration names,
# wherever it lives. On the new machine it puts those files under one root and
# rewrites the configuration to match — which is why the check reports the raw
# spelling of each path as well as the resolved one.

ACCESS_MAP_FILE = "access_map.json"
ACCESS_FORMAT = 1
SSH_PATH_KEYS = ("identityfile", "userknownhostsfile", "certificatefile")
RCLONE_PATH_KEYS = ("key_file", "known_hosts_file", "pubkey_file", "service_account_file")


def default_ssh_config_path() -> Path:
    return Path(os.environ.get("USERPROFILE", "")) / ".ssh" / "config"


def default_rclone_config_path() -> Path:
    return Path(os.environ.get("APPDATA", "")) / "rclone" / "rclone.conf"


def read_access_report(path: Path) -> list[dict[str, str]]:
    if not path.is_file():
        raise RuntimeError(f"Access report was not written: {path}")
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return [
            {str(key): str(value or "") for key, value in row.items()}
            for row in csv.DictReader(handle)
        ]


def access_stored_name(source: Path, scope: str) -> str:
    """A flat, collision-proof name for a file that came from anywhere.

    Two remotes can both name `known_hosts` from different folders, so the
    original folder decides the prefix.
    """
    digest = hashlib.sha256(str(source).lower().encode("utf-8")).hexdigest()[:8]
    stem = re.sub(r"[^A-Za-z0-9._-]+", "_", source.name) or "file"
    return f"{digest}_{stem}"


def rewrite_config_paths(text: str, mapping: dict[str, str], keys: tuple[str, ...]) -> tuple[str, int]:
    """Point configuration lines at the files as they now lie.

    Only lines that name a path are touched, and only when the value is one the
    migration actually carried: a config is a working file, not a template, and
    a blind search-and-replace in one is how a working host turns into a broken
    one.
    """
    rewritten = 0
    lines = text.splitlines(keepends=True)
    for index, line in enumerate(lines):
        stripped = line.strip()
        if not stripped or stripped.startswith(("#", ";")):
            continue
        for key in keys:
            head = stripped[: len(key)].lower()
            if head != key.lower():
                continue
            remainder = stripped[len(key) :]
            separator = "=" if remainder.lstrip().startswith("=") else ""
            value = remainder.lstrip()[1:].strip() if separator else remainder.strip()
            replacement = mapping.get(value.strip('"'))
            if not replacement:
                continue
            ending = line[len(line.rstrip("\r\n")) :]
            indent = line[: len(line) - len(line.lstrip())]
            joiner = " = " if separator else " "
            lines[index] = f"{indent}{stripped[: len(key)]}{joiner}{replacement}{ending}"
            rewritten += 1
            break
    return "".join(lines), rewritten


def access_kit(context: JobContext) -> dict[str, object]:
    params = context.operation.parameters
    mode = str(params.get("mode") or "status").strip().lower()
    tool_root = project_tool_dir(context, "ssh_keykit")

    ssh_config = resolve_user_path(context, params.get("ssh_config_path"), default=default_ssh_config_path())
    rclone_config = resolve_user_path(
        context, params.get("rclone_config_path"), default=default_rclone_config_path()
    )

    if mode == "status":
        call_migration_pack(
            context,
            ssh_keykit,
            {
                "mode": "check_links",
                "fail_on_broken": False,
                "ssh_config_path": params.get("ssh_config_path"),
                "rclone_config_path": params.get("rclone_config_path"),
            },
        )
        return {"mode": mode}

    default_folder = (
        context.paths.input if mode.startswith("import") else context.paths.output / "access"
    )
    folder = resolve_user_path(context, params.get("access_folder"), default=default_folder)

    if mode == "export":
        folder.mkdir(parents=True, exist_ok=True)
        files_dir = folder / "files"
        configs_dir = folder / "config"
        files_dir.mkdir(parents=True, exist_ok=True)
        configs_dir.mkdir(parents=True, exist_ok=True)
        report = folder / "links.csv"

        script_params: dict[str, Any] = {"ReportPath": str(report), "FailOnBroken": False}
        if str(params.get("ssh_config_path") or "").strip():
            script_params["SshConfig"] = str(ssh_config)
        if str(params.get("rclone_config_path") or "").strip():
            script_params["RcloneConfig"] = str(rclone_config)
        run_ps1(
            context,
            tool_root / "Test-SSHAccessLinks.ps1",
            script_params,
            cwd=tool_root,
            progress_seconds=120.0,
        )

        configs: list[dict[str, Any]] = []
        for kind, source in (("ssh", ssh_config), ("rclone", rclone_config)):
            if not source.is_file():
                context.log(f"No {kind} configuration at {source}; nothing to carry for it.")
                continue
            stored = configs_dir / (f"{kind}_config" if kind == "ssh" else "rclone.conf")
            shutil.copy2(source, stored)
            configs.append(
                {"kind": kind, "source": str(source), "file": str(stored.relative_to(folder)).replace("\\", "/")}
            )

        carried: list[dict[str, Any]] = []
        by_hand: list[dict[str, Any]] = []
        missing: list[dict[str, Any]] = []
        for row in read_access_report(report):
            entry = {
                "source": row.get("Path", ""),
                "raw": row.get("Raw", "") or row.get("Path", ""),
                "config": row.get("Source", ""),
                "scope": row.get("Scope", ""),
                "setting": row.get("Setting", ""),
            }
            if str(row.get("Exists", "")).strip().lower() not in {"true", "1", "yes"}:
                missing.append(entry)
                continue
            if row.get("Setting", "").lower() == "proxycommand":
                # An executable is installed on the new machine, not carried in a
                # migration folder: naming it is the useful part.
                by_hand.append(entry)
                continue
            source_path = Path(entry["source"])
            stored = files_dir / access_stored_name(source_path, entry["scope"])
            shutil.copy2(source_path, stored)
            entry["file"] = str(stored.relative_to(folder)).replace("\\", "/")
            carried.append(entry)

            # Configuration names the private key; the public half sits beside it
            # unmentioned and is missed by anything that collects by reference.
            companion = Path(str(source_path) + ".pub")
            if companion.is_file() and not any(item["source"] == str(companion) for item in carried):
                stored_pub = files_dir / access_stored_name(companion, entry["scope"])
                shutil.copy2(companion, stored_pub)
                carried.append(
                    {
                        "source": str(companion),
                        "raw": str(companion),
                        "config": entry["config"],
                        "scope": entry["scope"],
                        "setting": "companion",
                        "file": str(stored_pub.relative_to(folder)).replace("\\", "/"),
                    }
                )

        access_map = {
            "format": ACCESS_FORMAT,
            "created": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "machine": os.environ.get("COMPUTERNAME", ""),
            "configs": configs,
            "files": carried,
            "install_by_hand": by_hand,
            "missing": missing,
        }
        (folder / ACCESS_MAP_FILE).write_text(
            json.dumps(access_map, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        # One file can be named by several hosts and remotes, so references and
        # files are different numbers and both are worth seeing.
        unique_files = {entry["source"] for entry in carried}
        context.log(f"Configurations carried: {len(configs)}")
        context.log(f"Files carried: {len(unique_files)} ({len(carried)} reference(s))")
        for entry in by_hand:
            context.log(f"Install on the new machine by hand: {entry['raw']} ({entry['scope']})")
        for entry in missing:
            context.log(f"WARNING: named but not on disk, nothing to carry: {entry['raw']} ({entry['scope']})")
        return {
            "mode": mode,
            "folder": str(folder),
            "files": len(unique_files),
            "references": len(carried),
            "configs": len(configs),
            "by_hand": len(by_hand),
            "missing": len(missing),
        }

    if mode == "import":
        map_file = folder / ACCESS_MAP_FILE
        if not map_file.is_file():
            raise RuntimeError(f"Access map was not found: {map_file}")
        access_map = json.loads(map_file.read_text(encoding="utf-8"))
        if int(access_map.get("format", 0)) != ACCESS_FORMAT:
            raise RuntimeError(f"Access map format {access_map.get('format')!r} is not supported.")

        key_root = resolve_user_path(
            context,
            params.get("access_key_root"),
            default=Path(os.environ.get("USERPROFILE", "")) / ".ssh" / "linked",
        )
        key_root.mkdir(parents=True, exist_ok=True)
        context.log(f"Files from the migration go to: {key_root}")

        mapping: dict[str, str] = {}
        # One file can be named by several hosts and remotes, so the same file
        # arrives more than once. Counting the references as files would report
        # more than actually landed.
        placed: dict[str, Path] = {}
        for entry in access_map.get("files", []):
            stored = folder / str(entry.get("file", ""))
            if not stored.is_file():
                context.log(f"WARNING: missing in the migration folder: {entry.get('file')}")
                continue
            target = key_root / Path(str(entry.get("source", stored.name))).name
            if target.exists():
                # A previous layout locked this file down to the owner alone, so
                # copying straight over it fails. Laying the same access out twice
                # has to work: that is what a retried migration is.
                try:
                    target.chmod(0o600)
                except OSError:
                    pass
                target.unlink()
            shutil.copy2(stored, target)
            placed[str(target)] = target
            mapping[str(entry.get("raw", ""))] = str(target)
            mapping[str(entry.get("source", ""))] = str(target)

        rewritten_total = 0
        for entry in access_map.get("configs", []):
            stored = folder / str(entry.get("file", ""))
            if not stored.is_file():
                context.log(f"WARNING: missing in the migration folder: {entry.get('file')}")
                continue
            kind = str(entry.get("kind"))
            destination = ssh_config if kind == "ssh" else rclone_config
            keys = SSH_PATH_KEYS if kind == "ssh" else RCLONE_PATH_KEYS
            text, rewritten = rewrite_config_paths(
                stored.read_text(encoding="utf-8"), mapping, keys
            )
            rewritten_total += rewritten
            destination.parent.mkdir(parents=True, exist_ok=True)
            if destination.is_file():
                # The file being replaced is a working configuration; a copy of
                # it is the difference between a mistake and a lost afternoon.
                spare = destination.with_name(f"{destination.name}.bak.{timestamp()}")
                shutil.copy2(destination, spare)
                context.log(f"Previous {kind} configuration kept as: {spare}")
            destination.write_text(text, encoding="utf-8")
            context.log(f"{kind} configuration written: {destination} ({rewritten} path(s) rewritten)")

        if placed:
            # Windows OpenSSH refuses a private key that other accounts can read.
            quoted = ps_array(
                [str(path) for path in placed.values() if path.suffix.lower() != ".pub"]
            )
            run_ps_command(
                context,
                f"""
$ErrorActionPreference = 'Continue'
$user = "$env:USERDOMAIN\\$env:USERNAME"
foreach ($file in {quoted}) {{
  & icacls $file /inheritance:r | Out-Null
  & icacls $file /grant:r "$user:(F)" "SYSTEM:(F)" "Administrators:(F)" | Out-Null
  Write-Host ('ACL set: ' + $file)
}}
exit 0
""",
                check=False,
                progress_seconds=120.0,
            )

        for entry in access_map.get("install_by_hand", []):
            context.log(f"Still needed on this machine: {entry.get('raw')} ({entry.get('scope')})")

        context.log("")
        context.log("Checking access links after the rewrite:")
        call_migration_pack(
            context,
            ssh_keykit,
            {
                "mode": "check_links",
                "fail_on_broken": False,
                # The check has to read the same two files this run just wrote,
                # not whatever the current user's default configuration is.
                "ssh_config_path": str(ssh_config),
                "rclone_config_path": str(rclone_config),
            },
        )
        return {
            "mode": mode,
            "folder": str(folder),
            "files": len(placed),
            "rewritten": rewritten_total,
            "key_root": str(key_root),
        }

    raise RuntimeError(f"Unknown Access mode: {mode}")


# --- Migration: one trip instead of a folder-by-folder checklist --------------
#
# Every pack here already exports and imports its own piece. What was missing is
# the order: which pieces make up a move, where they land together, and how the
# new machine knows the move is complete. That order used to live in the
# operator's head, which is where migrations lose a piece.

MIGRATION_PLAN_FILE = "migration_plan.yaml"
MIGRATION_INVENTORY = "migration.json"
MIGRATION_FORMAT = 1


@dataclass(frozen=True)
class MigrationPack:
    """How one pack is asked to work into a migration folder.

    Packs name their folder parameter differently — `ssh_root`, `target_folder`,
    `cert_backup_dir` — so migration cannot simply hand over a path. A pack that
    exports unattended but cannot import that way declares no import service,
    and the plan has to say `import: manual` for it.
    """

    export_service: Callable[[JobContext], dict[str, object]]
    export_folder_param: str
    import_service: Callable[[JobContext], dict[str, object]] | None = None
    import_folder_param: str = ""
    import_defaults: dict[str, Any] = field(default_factory=dict)
    # Parameters a pack may take from the migration form itself. Named one by
    # one on purpose: handing a pack everything the migration was given is how
    # a folder meant for the migration ends up steering a pack.
    passthrough: tuple[str, ...] = ()


MIGRATION_PACKS: dict[str, MigrationPack] = {
    "ssh_keykit": MigrationPack(
        export_service=ssh_keykit,
        export_folder_param="ssh_root",
        import_service=ssh_keykit,
        import_folder_param="ssh_root",
    ),
    "certificate_keykit": MigrationPack(
        export_service=certificate_keykit,
        export_folder_param="cert_backup_dir",
        import_service=certificate_keykit,
        import_folder_param="cert_backup_dir",
        # A .pfx is encrypted with a password, and a password does not belong in
        # a plan file: it is asked for in the form, once per run.
        passthrough=("pfx_password",),
    ),
    "wifi_profiles": MigrationPack(
        export_service=wifi_export_profiles,
        export_folder_param="target_folder",
        import_service=wifi_import_profiles,
        import_folder_param="import_profile_folder",
        import_defaults={"source_kind": "folder"},
    ),
    "access_links": MigrationPack(
        export_service=access_kit,
        export_folder_param="access_folder",
        import_service=access_kit,
        import_folder_param="access_folder",
        passthrough=("ssh_config_path", "rclone_config_path", "access_key_root"),
    ),
    "user_fonts": MigrationPack(
        export_service=fonts_kit,
        export_folder_param="fonts_folder",
        import_service=fonts_kit,
        import_folder_param="fonts_folder",
    ),
    "shell_environment": MigrationPack(
        export_service=shell_kit,
        export_folder_param="shell_folder",
        import_service=shell_kit,
        import_folder_param="shell_folder",
    ),
}


@dataclass(frozen=True)
class MigrationItem:
    item_id: str
    title: str
    title_ru: str
    pack: str
    folder: str
    secret: bool
    export_mode: str
    export_params: dict[str, Any]
    import_mode: str
    import_params: dict[str, Any]
    manual: bool
    manual_reason: str
    manual_reason_ru: str


def migration_plan_file(context: JobContext) -> Path:
    return context.paths.config / MIGRATION_PLAN_FILE


def migration_output_root(context: JobContext) -> Path:
    return context.paths.output / "migration"


def _migration_folder_name(value: str, item_id: str) -> str:
    """A plan file names folders, so it must not be able to name a path."""
    folder = str(value or item_id).strip()
    if not folder or folder in {".", ".."}:
        raise RuntimeError(f"Migration plan item {item_id!r} has an empty folder name.")
    if any(mark in folder for mark in ("\\", "/", ":")) or Path(folder).is_absolute():
        raise RuntimeError(
            f"Migration plan item {item_id!r} names a path, not a folder: {folder!r}"
        )
    return folder


def _migration_side(raw: Any, item_id: str, side: str) -> tuple[str, dict[str, Any], bool]:
    """Read the `export:`/`import:` half of a plan item."""
    if isinstance(raw, str) and raw.strip().lower() == "manual":
        return "", {}, True
    if not isinstance(raw, dict):
        raise RuntimeError(
            f"Migration plan item {item_id!r} has no {side} section (a mapping, or 'manual')."
        )
    parameters = {str(key): value for key, value in raw.items() if str(key) != "mode"}
    mode = str(raw.get("mode") or "").strip()
    if not mode:
        raise RuntimeError(f"Migration plan item {item_id!r} has no {side} mode.")
    return mode, parameters, False


def load_migration_plan(context: JobContext) -> list[MigrationItem]:
    plan_file = migration_plan_file(context)
    if not plan_file.exists():
        raise RuntimeError(f"Migration plan was not found: {plan_file}")

    data = load_yaml_or_json(plan_file)
    raw_items = data.get("items")
    if not isinstance(raw_items, list) or not raw_items:
        raise RuntimeError(f"Migration plan has no items: {plan_file}")

    items: list[MigrationItem] = []
    seen: set[str] = set()
    for raw in raw_items:
        if not isinstance(raw, dict):
            raise RuntimeError(f"Migration plan item is not a mapping: {raw!r}")
        item_id = str(raw.get("id") or "").strip()
        if not item_id:
            raise RuntimeError("Migration plan has an item without an id.")
        if item_id in seen:
            raise RuntimeError(f"Migration plan repeats item id: {item_id}")
        seen.add(item_id)

        pack_name = str(raw.get("pack") or "").strip()
        pack = MIGRATION_PACKS.get(pack_name)
        if pack is None:
            known = ", ".join(sorted(MIGRATION_PACKS))
            raise RuntimeError(
                f"Migration plan item {item_id!r} names an unknown pack: {pack_name!r}. "
                f"Known packs: {known}."
            )

        export_mode, export_params, export_manual = _migration_side(
            raw.get("export"), item_id, "export"
        )
        if export_manual:
            raise RuntimeError(
                f"Migration plan item {item_id!r} cannot be manual on export: "
                "an item that cannot be collected has no place in a migration."
            )
        import_mode, import_params, manual = _migration_side(
            raw.get("import"), item_id, "import"
        )
        if not manual and pack.import_service is None:
            raise RuntimeError(
                f"Migration plan item {item_id!r} asks pack {pack_name!r} to import, "
                "but that pack has no unattended import. Use 'import: manual'."
            )

        items.append(
            MigrationItem(
                item_id=item_id,
                title=str(raw.get("title") or item_id),
                title_ru=str(raw.get("title_ru") or raw.get("title") or item_id),
                pack=pack_name,
                folder=_migration_folder_name(raw.get("folder"), item_id),
                secret=bool(raw.get("secret", False)),
                export_mode=export_mode,
                export_params=export_params,
                import_mode=import_mode,
                import_params=import_params,
                manual=manual,
                manual_reason=str(raw.get("manual_reason") or ""),
                manual_reason_ru=str(raw.get("manual_reason_ru") or ""),
            )
        )
    return items


def call_migration_pack(
    context: JobContext,
    service: Callable[[JobContext], dict[str, object]],
    parameters: dict[str, Any],
) -> dict[str, object]:
    """Run a pack with our parameters, keeping one journal for the whole trip.

    The sub-context keeps the same log file and report folder, so a migration
    reads as a single run rather than as several unrelated operations.
    """
    operation = replace(context.operation, parameters=dict(parameters))
    return service(replace(context, operation=operation)) or {}


def migration_folder_summary(path: Path) -> dict[str, int]:
    files = 0
    total = 0
    if path.exists():
        for item in path.rglob("*"):
            if item.is_file():
                files += 1
                total += item.stat().st_size
    return {"files": files, "bytes": total}


def describe_migration_plan(context: JobContext, items: list[MigrationItem]) -> None:
    context.log(f"Migration plan: {migration_plan_file(context)}")
    context.log(f"Items: {len(items)}")
    for item in items:
        route = "manual" if item.manual else f"automatic ({item.import_mode})"
        secret = "secret" if item.secret else "public"
        context.log(
            f"  {item.item_id:<14} {item.pack:<20} -> {item.folder:<14} {secret:<7} import: {route}"
        )
        if item.manual and item.manual_reason:
            context.log(f"        {item.manual_reason}")


def find_migration_folder(context: JobContext, explicit: Any) -> Path:
    """Where a migration to import is lying.

    Import reads `input` — the same door every other pack uses — and accepts
    either the migration folder itself or a folder holding several of them.
    """
    root = resolve_user_path(context, explicit, default=context.paths.input)
    if (root / MIGRATION_INVENTORY).is_file():
        return root
    if not root.is_dir():
        raise RuntimeError(f"Migration folder was not found: {root}")

    candidates = sorted(
        (path for path in root.iterdir() if (path / MIGRATION_INVENTORY).is_file()),
        key=lambda path: (path / MIGRATION_INVENTORY).stat().st_mtime,
        reverse=True,
    )
    if not candidates:
        raise RuntimeError(
            f"No migration found in {root}: expected {MIGRATION_INVENTORY} there "
            "or in one of its subfolders."
        )
    if len(candidates) > 1:
        context.log(f"Migrations found: {len(candidates)}. Taking the newest one.")
    return candidates[0]


def migration_kit(context: JobContext) -> dict[str, object]:
    params = context.operation.parameters
    mode = str(params.get("mode") or "plan").strip().lower()

    if mode == "open_folder":
        folder = migration_output_root(context)
        open_path(context, folder)
        return {"folder": str(folder)}

    if mode == "verify":
        # The same check the SSH pack runs: after a move, access is what proves
        # the move landed.
        call_migration_pack(context, ssh_keykit, {"mode": "check_links"})
        return {"mode": mode}

    items = load_migration_plan(context)

    if mode == "plan":
        describe_migration_plan(context, items)
        context.log(f"Export would collect into: {migration_output_root(context)}")
        context.log(f"Import would read from:    {context.paths.input}")
        return {"mode": mode, "items": [item.item_id for item in items]}

    if mode == "export":
        machine = str(params.get("profile_name") or os.environ.get("COMPUTERNAME") or "machine").strip()
        user = str(params.get("user_name") or os.environ.get("USERNAME") or "").strip()
        target = migration_output_root(context) / f"{machine}_{timestamp()}"
        target.mkdir(parents=True, exist_ok=True)
        context.log(f"Collecting migration into: {target}")

        collected: list[dict[str, Any]] = []
        failures: list[str] = []
        for index, item in enumerate(items, start=1):
            pack = MIGRATION_PACKS[item.pack]
            folder = target / item.folder
            folder.mkdir(parents=True, exist_ok=True)
            context.log(f"[{index}/{len(items)}] {item.item_id}: {item.title}")
            parameters = {
                **{key: params[key] for key in pack.passthrough if key in params},
                **item.export_params,
                "mode": item.export_mode,
                pack.export_folder_param: str(folder),
            }
            entry: dict[str, Any] = {
                "id": item.item_id,
                "title": item.title,
                "title_ru": item.title_ru,
                "pack": item.pack,
                "folder": item.folder,
                "secret": item.secret,
                "import": "manual" if item.manual else item.import_mode,
                "import_params": item.import_params,
                "manual_reason": item.manual_reason,
                "manual_reason_ru": item.manual_reason_ru,
            }
            try:
                call_migration_pack(context, pack.export_service, parameters)
                entry["collected"] = True
            except Exception as exc:
                # One piece failing is not a reason to abandon the rest: a
                # partial migration with a named gap beats no migration at all.
                context.log(f"ERROR: {item.item_id} was not collected: {exc}")
                entry["collected"] = False
                entry["error"] = str(exc)
                failures.append(item.item_id)
            entry.update(migration_folder_summary(folder))
            collected.append(entry)

        inventory = {
            "format": MIGRATION_FORMAT,
            "created": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "machine": machine,
            "user": user,
            "items": collected,
        }
        (target / MIGRATION_INVENTORY).write_text(
            json.dumps(inventory, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        total_files = sum(int(entry.get("files", 0)) for entry in collected)
        context.log(f"Inventory written: {target / MIGRATION_INVENTORY}")
        context.log(f"Collected items: {len(collected) - len(failures)}/{len(collected)}, files: {total_files}")
        if failures:
            raise RuntimeError(
                "Migration collected with gaps: " + ", ".join(failures) + ". See the log above."
            )
        return {"mode": mode, "folder": str(target), "items": len(collected), "files": total_files}

    if mode == "import":
        source = find_migration_folder(context, params.get("migration_folder"))
        inventory_file = source / MIGRATION_INVENTORY
        context.log(f"Migration: {source}")
        inventory = json.loads(inventory_file.read_text(encoding="utf-8"))
        if int(inventory.get("format", 0)) != MIGRATION_FORMAT:
            raise RuntimeError(
                f"Migration format {inventory.get('format')!r} is not supported by this version."
            )
        context.log(
            f"Collected on {inventory.get('machine')} at {inventory.get('created')} "
            f"by {inventory.get('user')}"
        )

        entries = inventory.get("items")
        if not isinstance(entries, list) or not entries:
            raise RuntimeError(f"Migration inventory lists no items: {inventory_file}")

        restored: list[str] = []
        manual: list[str] = []
        failures: list[str] = []
        for index, entry in enumerate(entries, start=1):
            item_id = str(entry.get("id") or f"item{index}")
            folder = source / str(entry.get("folder") or item_id)
            title = str(entry.get("title") or item_id)
            context.log(f"[{index}/{len(entries)}] {item_id}: {title}")

            if not entry.get("collected", True):
                context.log(f"  skipped: it was not collected on {inventory.get('machine')}")
                failures.append(item_id)
                continue
            if str(entry.get("import")) == "manual":
                reason = str(entry.get("manual_reason") or "")
                context.log(f"  by hand: {reason or 'this pack has no unattended import'}")
                context.log(f"  files are here: {folder}")
                manual.append(item_id)
                continue

            pack = MIGRATION_PACKS.get(str(entry.get("pack")))
            if pack is None or pack.import_service is None:
                context.log(f"  ERROR: unknown pack {entry.get('pack')!r}, nothing was imported")
                failures.append(item_id)
                continue

            parameters = {
                **pack.import_defaults,
                **{key: params[key] for key in pack.passthrough if key in params},
                **(entry.get("import_params") or {}),
                "mode": str(entry.get("import")),
                pack.import_folder_param: str(folder),
            }
            try:
                call_migration_pack(context, pack.import_service, parameters)
                restored.append(item_id)
            except Exception as exc:
                context.log(f"  ERROR: {exc}")
                failures.append(item_id)

        context.log("")
        context.log(f"Restored: {len(restored)}. By hand: {len(manual)}. Failed: {len(failures)}.")
        for item_id in manual:
            context.log(f"  by hand: {item_id}")

        # A migration is finished when access answers, not when files are copied.
        context.log("")
        context.log("Checking access links after the move:")
        call_migration_pack(
            context, ssh_keykit, {"mode": "check_links", "fail_on_broken": False}
        )

        if failures:
            raise RuntimeError("Migration finished with failures: " + ", ".join(failures))
        return {
            "mode": mode,
            "source": str(source),
            "restored": restored,
            "manual": manual,
        }

    raise RuntimeError(f"Unknown Migration mode: {mode}")


def nvidia_audio_tool_root(context: JobContext | Path | str) -> Path:
    if isinstance(context, JobContext):
        return context.paths.system_core / "nvidia_audio"
    root = Path(context).resolve()
    return root / "system_core" / "nvidia_audio"


def nvidia_audio_script(context: JobContext, name: str) -> Path:
    script = nvidia_audio_tool_root(context) / name
    if not script.exists():
        raise RuntimeError(f"NVIDIA HDMI/DP Audio script was not found: {script}")
    return script


def nvidia_hdmi_dp_audio(context: JobContext) -> dict[str, object]:
    params = context.operation.parameters
    mode = str(params.get("mode", "")).strip().lower()
    root = nvidia_audio_tool_root(context)

    script_by_mode = {
        "status": "Status-NvidiaHdmiDpAudio.ps1",
        "export_ids": "Export-NvidiaHdmiDpAudioDeviceIds.ps1",
        "disable": "Disable-NvidiaHdmiDpAudio.ps1",
        "enable": "Enable-NvidiaHdmiDpAudio.ps1",
        "block_policy": "Block-NvidiaHdmiDpAudioPolicy.ps1",
        "unblock_policy": "Unblock-NvidiaHdmiDpAudioPolicy.ps1",
    }
    if mode in script_by_mode:
        script = nvidia_audio_script(context, script_by_mode[mode])
        elevated = mode in {"disable", "enable", "block_policy", "unblock_policy"}
        run_ps1(context, script, {}, cwd=script.parent, progress_seconds=300.0, elevated=elevated)
        return {"mode": mode, "script": str(script)}

    if mode in {"open_tool_folder", "open_backup", "open_output", "open_state"}:
        if mode == "open_backup":
            path = context.paths.backup / "nvidia_audio"
        elif mode == "open_output":
            path = context.paths.output / "nvidia_audio"
        elif mode == "open_state":
            path = context.paths.root / "data" / "nvidia_audio"
        else:
            path = root
        open_path(context, path)
        return {"mode": mode, "folder": str(path)}

    raise RuntimeError(f"Unknown NVIDIA HDMI/DP Audio mode: {mode}")


CHROMIUM_REQUIRED_FILES = ("Bookmarks", "Favicons")
CHROMIUM_OPTIONAL_FILES = ("Favicons-journal", "Favicons-wal", "Favicons-shm")
CHROMIUM_BOOKMARK_FILES = (*CHROMIUM_REQUIRED_FILES, *CHROMIUM_OPTIONAL_FILES)
CHROMIUM_FAVICON_FILES = ("Favicons", *CHROMIUM_OPTIONAL_FILES)

CHROMIUM_BROWSER_PROFILES: dict[str, dict[str, object]] = {
    "chrome": {
        "label": "Google Chrome",
        "process": {"nt": "chrome.exe", "posix": "chrome"},
        "profiles": {
            "nt": r"%LOCALAPPDATA%\Google\Chrome\User Data\Default",
            "posix": "~/.config/google-chrome/Default",
        },
    },
    "edge": {
        "label": "Microsoft Edge",
        "process": {"nt": "msedge.exe", "posix": "msedge"},
        "profiles": {
            "nt": r"%LOCALAPPDATA%\Microsoft\Edge\User Data\Default",
            "posix": "~/.config/microsoft-edge/Default",
        },
    },
    "brave": {
        "label": "Brave Browser",
        "process": {"nt": "brave.exe", "posix": "brave"},
        "profiles": {
            "nt": r"%LOCALAPPDATA%\BraveSoftware\Brave-Browser\User Data\Default",
            "posix": "~/.config/BraveSoftware/Brave-Browser/Default",
        },
    },
    "vivaldi": {
        "label": "Vivaldi",
        "process": {"nt": "vivaldi.exe", "posix": "vivaldi"},
        "profiles": {
            "nt": r"%LOCALAPPDATA%\Vivaldi\User Data\Default",
            "posix": "~/.config/vivaldi/Default",
        },
    },
    "yandex": {
        "label": "Yandex Browser",
        "process": {"nt": "browser.exe", "posix": "yandex-browser"},
        "profiles": {
            "nt": r"%LOCALAPPDATA%\Yandex\YandexBrowser\User Data\Default",
            "posix": "~/.config/yandex-browser/Default",
        },
    },
    "opera": {
        "label": "Opera Stable",
        "process": {"nt": "opera.exe", "posix": "opera"},
        "profiles": {
            "nt": r"%APPDATA%\Opera Software\Opera Stable\Default",
            "posix": "~/.config/opera/Default",
        },
    },
}


def chromium_browser_options(root: Path | str | None = None) -> list[dict[str, str]]:
    return [
        {
            "value": key,
            "label": str(definition["label"]),
            "label_ru": str(definition["label"]),
        }
        for key, definition in CHROMIUM_BROWSER_PROFILES.items()
    ]


def _split_chromium_browser_keys(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, (list, tuple, set)):
        raw_items = value
    else:
        raw_items = re.split(r"[\r\n,;|]+", str(value))
    keys: list[str] = []
    seen: set[str] = set()
    for item in raw_items:
        key = str(item or "").strip().lower()
        if not key or key in seen:
            continue
        _chromium_browser_definition(key)
        keys.append(key)
        seen.add(key)
    return keys


def _selected_chromium_browser_keys(params: dict[str, Any]) -> list[str]:
    keys = _split_chromium_browser_keys(params.get("browser_profiles"))
    if keys:
        return keys
    key, _definition = _chromium_browser_definition(params.get("browser_profile"))
    return [key]


def _transfer_chromium_browser_keys(params: dict[str, Any]) -> tuple[str, list[str]]:
    source_key, _definition = _chromium_browser_definition(params.get("source_browser_profile") or params.get("browser_profile"))
    target_keys = _split_chromium_browser_keys(params.get("target_browser_profiles"))
    if not target_keys:
        target_keys = _split_chromium_browser_keys(params.get("browser_profiles"))
    if not target_keys:
        target_keys = [key for key in CHROMIUM_BROWSER_PROFILES if key != source_key]
    target_keys = [key for key in target_keys if key != source_key]
    if not target_keys:
        raise RuntimeError("Transfer requires at least one target browser different from the source browser.")
    return source_key, target_keys


def _platform_key() -> str:
    return "nt" if os.name == "nt" else "posix"


def _chromium_browser_definition(browser_key: Any) -> tuple[str, dict[str, object]]:
    key = str(browser_key or "chrome").strip().lower()
    if key not in CHROMIUM_BROWSER_PROFILES:
        allowed = ", ".join(sorted(CHROMIUM_BROWSER_PROFILES))
        raise RuntimeError(f"Unsupported Chromium browser profile: {key or '<empty>'}. Expected: {allowed}")
    return key, CHROMIUM_BROWSER_PROFILES[key]


def _chromium_definition_value(definition: dict[str, object], section: str) -> str:
    values = definition.get(section)
    if not isinstance(values, dict):
        return ""
    return str(values.get(_platform_key()) or values.get("posix") or "")


def _resolve_browser_profile_path(context: JobContext, params: dict[str, Any], definition: dict[str, object]) -> Path:
    override = str(params.get("browser_profile_path") or "").strip()
    if override:
        return resolve_user_path(context, override)
    template = _chromium_definition_value(definition, "profiles")
    if not template:
        raise RuntimeError("Browser profile path template is empty.")
    return Path(os.path.expandvars(template)).expanduser()


def _browser_process_name(definition: dict[str, object]) -> str:
    process = _chromium_definition_value(definition, "process")
    if not process:
        raise RuntimeError("Browser process name is empty.")
    return process


def _safe_bookmarks_backup_name(value: str) -> str:
    clean = re.sub(r"[^A-Za-z0-9._-]+", "_", value.strip())
    clean = clean.strip("._-")
    return clean or "browser"


def _normalize_backup_version_number(value: Any) -> int | None:
    text = str(value or "").strip().lower()
    if not text or text in {"auto", "next"}:
        return None
    match = re.search(r"(\d+)", text)
    if not match:
        raise RuntimeError(f"Backup version must be a number, vNN, or auto. Got: {value}")
    number = int(match.group(1))
    if number < 1:
        raise RuntimeError("Backup version must be 1 or greater.")
    return number


def _format_backup_version_suffix(number: int) -> str:
    return f"v{number:02d}"


def _next_versioned_chromium_backup_dir(
    target_root: Path,
    *,
    date_prefix: str,
    backup_label: str,
    browser_key: str,
    version_value: Any,
) -> tuple[Path, str, int]:
    base = _safe_bookmarks_backup_name(backup_label) if str(backup_label or "").strip() else f"{_safe_bookmarks_backup_name(browser_key)}_bookmarks_master"
    start = _normalize_backup_version_number(version_value) or 1
    version = start
    while version < 100000:
        suffix = _format_backup_version_suffix(version)
        candidate = target_root / f"{date_prefix}_{base}_{suffix}"
        if not candidate.exists():
            return candidate, suffix, version
        version += 1
    raise RuntimeError(f"Could not find a free backup version under: {target_root}")


def _browser_process_running(process_name: str) -> bool:
    if not process_name:
        return False
    try:
        if os.name == "nt":
            result = subprocess.run(
                ["tasklist.exe", "/FI", f"IMAGENAME eq {process_name}", "/NH"],
                stdin=subprocess.DEVNULL,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                check=False,
            )
            text = decode_process_bytes(result.stdout).lower()
            return process_name.lower() in text and "no tasks" not in text and "нет задач" not in text
        result = subprocess.run(
            ["pgrep", "-x", process_name],
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            check=False,
        )
        return result.returncode == 0
    except Exception:
        return False


def _close_browser_process(context: JobContext, process_name: str, *, enabled: bool) -> None:
    if not enabled:
        context.log("Browser process close skipped by option.")
        return
    if not _browser_process_running(process_name):
        context.log(f"Browser process is not running: {process_name}")
        return
    context.log(f"Closing browser process before file operation: {process_name}")
    if os.name == "nt":
        run_process(context, ["taskkill.exe", "/IM", process_name], check=False, progress_seconds=10.0)
    else:
        run_process(context, ["pkill", "-x", process_name], check=False, progress_seconds=10.0)
    deadline = time.monotonic() + 8.0
    while time.monotonic() < deadline:
        if not _browser_process_running(process_name):
            context.log(f"Browser process closed: {process_name}")
            return
        time.sleep(0.25)
    if _browser_process_running(process_name):
        context.log(f"Browser process did not close gracefully; forcing close: {process_name}")
        if os.name == "nt":
            run_process(context, ["taskkill.exe", "/F", "/IM", process_name], check=False, progress_seconds=10.0)
        else:
            run_process(context, ["pkill", "-KILL", "-x", process_name], check=False, progress_seconds=10.0)
        time.sleep(1.0)
    if _browser_process_running(process_name):
        raise RuntimeError(f"Browser process is still running after forced close attempt: {process_name}")


def _chromium_file_snapshot(folder: Path) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    for file_name in CHROMIUM_BOOKMARK_FILES:
        path = folder / file_name
        exists = path.exists()
        rows.append(
            {
                "name": file_name,
                "path": str(path),
                "exists": exists,
                "size": path.stat().st_size if exists and path.is_file() else None,
                "modified": datetime.fromtimestamp(path.stat().st_mtime).isoformat(timespec="seconds") if exists and path.is_file() else None,
            }
        )
    return rows


def _missing_chromium_files(folder: Path) -> list[str]:
    return [name for name in CHROMIUM_REQUIRED_FILES if not (folder / name).is_file()]


def _assert_chromium_files(folder: Path, label: str) -> None:
    missing = _missing_chromium_files(folder)
    if missing:
        raise RuntimeError(f"{label} is missing required Chromium bookmark files: {', '.join(missing)}. Folder: {folder}")


def _chromium_profile_skip_reason(profile: Path, label: str, *, require_files: bool) -> str:
    if not profile.exists():
        return f"{label} folder was not found: {profile}"
    if require_files:
        missing = _missing_chromium_files(profile)
        if missing:
            return f"{label} is missing required Chromium bookmark files: {', '.join(missing)}. Folder: {profile}"
    return ""


def _skip_chromium_browser(context: JobContext, browser_key: str, definition: dict[str, object], profile: Path, reason: str) -> dict[str, object]:
    context.log(f"SKIP: {definition['label']} ({browser_key}) - {reason}")
    return {
        "browser": browser_key,
        "browser_label": str(definition["label"]),
        "profile": str(profile),
        "reason": reason,
    }


def _find_latest_chromium_backup(source_root: Path) -> Path:
    if all((source_root / name).is_file() for name in CHROMIUM_REQUIRED_FILES):
        return source_root
    if not source_root.exists():
        raise RuntimeError(f"Backup source folder was not found: {source_root}")
    candidates = [
        path
        for path in source_root.iterdir()
        if path.is_dir() and all((path / name).is_file() for name in CHROMIUM_REQUIRED_FILES)
    ]
    if not candidates:
        raise RuntimeError(f"No Chromium bookmark backup folder with Bookmarks/Favicons was found in: {source_root}")
    candidates.sort(key=lambda path: path.stat().st_mtime, reverse=True)
    return candidates[0]


def _chromium_time(timestamp: str | None = None) -> str:
    if timestamp and str(timestamp).isdigit():
        return str((int(timestamp) + 11644473600) * 1_000_000)
    return str(int((time.time() + 11644473600) * 1_000_000))


class _NetscapeBookmarksParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.root: list[dict[str, Any]] = []
        self.stack: list[list[dict[str, Any]]] = [self.root]
        self.pending_folder: dict[str, Any] | None = None
        self.capture: str | None = None
        self.attrs: dict[str, str] = {}
        self.text: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        tag = tag.lower()
        if tag in {"h3", "a"}:
            self.capture = tag
            self.attrs = {str(k).lower(): str(v or "") for k, v in attrs}
            self.text = []
        elif tag == "dl" and self.pending_folder is not None:
            self.stack.append(self.pending_folder["children"])
            self.pending_folder = None

    def handle_data(self, data: str) -> None:
        if self.capture:
            self.text.append(data)

    def handle_endtag(self, tag: str) -> None:
        tag = tag.lower()
        if tag == "h3" and self.capture == "h3":
            folder = {
                "type": "folder",
                "name": "".join(self.text).strip() or "Folder",
                "date_added": _chromium_time(self.attrs.get("add_date")),
                "date_modified": "0",
                "children": [],
            }
            self.stack[-1].append(folder)
            self.pending_folder = folder
            self.capture = None
        elif tag == "a" and self.capture == "a":
            href = self.attrs.get("href", "").strip()
            if href:
                self.stack[-1].append({
                    "type": "url",
                    "name": "".join(self.text).strip() or href,
                    "url": href,
                    "date_added": _chromium_time(self.attrs.get("add_date")),
                    "_audion_icon": self.attrs.get("icon", ""),
                })
            self.capture = None
        elif tag == "dl" and len(self.stack) > 1:
            self.stack.pop()


def _assign_chromium_bookmark_ids(nodes: list[dict[str, Any]], next_id: list[int]) -> None:
    for node in nodes:
        node["id"] = str(next_id[0])
        next_id[0] += 1
        if node.get("type") == "folder":
            _assign_chromium_bookmark_ids(node.get("children", []), next_id)


def _chromium_bookmark_checksum(roots: dict[str, dict[str, Any]]) -> str:
    digest = hashlib.md5()

    def visit(node: dict[str, Any]) -> None:
        for key in ("id", "name", "type"):
            digest.update(str(node.get(key, "")).encode("utf-8"))
        if node.get("type") == "url":
            digest.update(str(node.get("url", "")).encode("utf-8"))
        for child in node.get("children", []):
            visit(child)

    for name in ("bookmark_bar", "other", "synced"):
        visit(roots[name])
    return digest.hexdigest()


def chromium_bookmarks_and_icons_from_html(html_path: Path) -> tuple[dict[str, Any], dict[str, bytes]]:
    if not html_path.is_file() or html_path.suffix.lower() not in {".html", ".htm"}:
        raise RuntimeError(f"HTML bookmarks file was not found: {html_path}")
    parser = _NetscapeBookmarksParser()
    parser.feed(html_path.read_text(encoding="utf-8-sig", errors="replace"))
    if not parser.root:
        raise RuntimeError(f"No bookmarks were found in HTML file: {html_path}")
    if len(parser.root) == 1 and parser.root[0].get("type") == "folder":
        root_name = str(parser.root[0].get("name") or "").strip().casefold()
        if root_name in {"панель закладок", "bookmarks bar", "bookmark bar", "favorites bar"}:
            parser.root = list(parser.root[0].get("children", []))
    roots = {
        "bookmark_bar": {"children": parser.root, "date_added": _chromium_time(), "date_modified": "0", "id": "1", "name": "Bookmarks bar", "type": "folder"},
        "other": {"children": [], "date_added": _chromium_time(), "date_modified": "0", "id": "2", "name": "Other bookmarks", "type": "folder"},
        "synced": {"children": [], "date_added": _chromium_time(), "date_modified": "0", "id": "3", "name": "Mobile bookmarks", "type": "folder"},
    }
    _assign_chromium_bookmark_ids(parser.root, [4])
    icons: dict[str, bytes] = {}

    def collect(nodes: list[dict[str, Any]]) -> None:
        for node in nodes:
            icon_value = str(node.pop("_audion_icon", "") or "")
            if node.get("type") == "url" and icon_value.startswith("data:") and "," in icon_value:
                header, encoded = icon_value.split(",", 1)
                if ";base64" in header.lower():
                    try:
                        icons[str(node.get("url") or "")] = base64.b64decode(encoded, validate=True)
                    except (ValueError, TypeError):
                        pass
            collect(node.get("children", []))

    collect(parser.root)
    return {"checksum": _chromium_bookmark_checksum(roots), "roots": roots, "version": 1}, icons


def chromium_bookmarks_from_html(html_path: Path) -> dict[str, Any]:
    payload, _icons = chromium_bookmarks_and_icons_from_html(html_path)
    return payload


def _image_dimensions(data: bytes) -> tuple[int, int]:
    if len(data) >= 24 and data.startswith(b"\x89PNG\r\n\x1a\n"):
        return int.from_bytes(data[16:20], "big"), int.from_bytes(data[20:24], "big")
    return 0, 0


def _merge_html_icons_into_favicons(context: JobContext, profile: Path, icons: dict[str, bytes], *, clean: bool = True) -> int:
    import sqlite3

    database = profile / "Favicons"
    if not database.is_file() or not icons:
        context.log(f"HTML favicon merge skipped: database={database.is_file()} icons={len(icons)}")
        return 0
    temp = profile / f".Favicons.audion-html-{os.getpid()}"
    shutil.copy2(database, temp)
    merged = 0
    try:
        connection = sqlite3.connect(temp)
        try:
            connection.execute("PRAGMA journal_mode=DELETE")
            if clean:
                connection.execute("DELETE FROM icon_mapping")
                connection.execute("DELETE FROM favicon_bitmaps")
                connection.execute("DELETE FROM favicons")
            for page_url, image_data in icons.items():
                icon_url = f"audion-html://{hashlib.sha256(image_data).hexdigest()}"
                row = connection.execute("SELECT id FROM favicons WHERE url=?", (icon_url,)).fetchone()
                if row:
                    icon_id = int(row[0])
                else:
                    cursor = connection.execute("INSERT INTO favicons(url, icon_type) VALUES(?, 1)", (icon_url,))
                    icon_id = int(cursor.lastrowid)
                width, height = _image_dimensions(image_data)
                connection.execute("DELETE FROM favicon_bitmaps WHERE icon_id=?", (icon_id,))
                connection.execute(
                    "INSERT INTO favicon_bitmaps(icon_id,last_updated,image_data,width,height,last_requested) VALUES(?,?,?,?,?,?)",
                    (icon_id, int(_chromium_time()), sqlite3.Binary(image_data), width, height, int(_chromium_time())),
                )
                connection.execute("DELETE FROM icon_mapping WHERE page_url=?", (page_url,))
                connection.execute("INSERT INTO icon_mapping(page_url,icon_id,page_url_type) VALUES(?,?,0)", (page_url, icon_id))
                merged += 1
            result = connection.execute("PRAGMA quick_check").fetchone()
            if not result or str(result[0]).lower() != "ok":
                raise RuntimeError(f"Generated Favicons quick_check failed: {result}")
            connection.commit()
        finally:
            connection.close()
        os.replace(temp, database)
        for sidecar_name in ("Favicons-journal", "Favicons-wal", "Favicons-shm"):
            sidecar = profile / sidecar_name
            if sidecar.exists():
                sidecar.unlink()
    finally:
        if temp.exists():
            temp.unlink()
    context.log(f"{'Rebuilt' if clean else 'Merged'} {merged} embedded HTML favicons in: {database}")
    return merged


def _assert_sqlite_quick_check(path: Path, label: str) -> None:
    import sqlite3

    try:
        uri = path.resolve().as_uri() + "?mode=ro"
        with sqlite3.connect(uri, uri=True) as connection:
            row = connection.execute("PRAGMA quick_check").fetchone()
    except sqlite3.DatabaseError as exc:
        raise RuntimeError(f"{label} SQLite check failed: {path} ({exc})") from exc
    if not row or str(row[0]).lower() != "ok":
        raise RuntimeError(f"{label} SQLite quick_check is not OK: {path} ({row[0] if row else 'empty result'})")


def _copy_file_atomic(src: Path, dst: Path) -> int:
    tmp = dst.with_name(f".{dst.name}.audion-tmp-{os.getpid()}")
    try:
        if tmp.exists():
            tmp.unlink()
        shutil.copy2(src, tmp)
        try:
            with tmp.open("r+b") as handle:
                os.fsync(handle.fileno())
        except OSError:
            pass
        os.replace(tmp, dst)
        return dst.stat().st_size
    finally:
        try:
            if tmp.exists():
                tmp.unlink()
        except OSError:
            pass


def _copy_chromium_file_set(context: JobContext, source: Path, target: Path, *, overwrite: bool) -> list[dict[str, object]]:
    copied: list[dict[str, object]] = []
    target.mkdir(parents=True, exist_ok=True)
    for file_name in CHROMIUM_REQUIRED_FILES:
        src = source / file_name
        if not src.is_file():
            raise RuntimeError(f"Required source file was not found: {src}")
    target_favicons = target / "Favicons"
    for file_name in CHROMIUM_BOOKMARK_FILES:
        src = source / file_name
        dst = target / file_name
        if not src.is_file():
            context.log(f"Skipped optional Chromium file because it is absent: {src}")
            continue
        if dst.exists() and not overwrite:
            raise RuntimeError(f"Target file already exists: {dst}")
        if file_name == "Favicons":
            _assert_sqlite_quick_check(src, "Source Favicons")
        size = _copy_file_atomic(src, dst)
        context.log(f"Copied {file_name}: {src} -> {dst} ({size} bytes)")
        copied.append({"name": file_name, "source": str(src), "target": str(dst), "size": size})
    if target_favicons.is_file():
        _assert_sqlite_quick_check(target_favicons, "Target Favicons")
    return copied


def _write_chromium_backup_manifest(path: Path, payload: dict[str, object]) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _local_browser_bookmark_backup_root(context: JobContext) -> Path:
    path = context.paths.backup / "browser_bookmarks"
    path.mkdir(parents=True, exist_ok=True)
    return path


def _clear_chromium_favicons(context: JobContext, profile: Path) -> list[str]:
    deleted: list[str] = []
    for file_name in CHROMIUM_FAVICON_FILES:
        path = profile / file_name
        if path.exists():
            path.unlink()
            deleted.append(str(path))
            context.log(f"Deleted: {path}")
        else:
            context.log(f"Already absent: {path}")
    return deleted


def _browser_bookmarks_status(context: JobContext, params: dict[str, Any], browser_key: str, definition: dict[str, object]) -> dict[str, object]:
    profile = _resolve_browser_profile_path(context, params, definition)
    source_root = resolve_user_path(context, params.get("backup_source_path"), default=context.paths.input)
    target_root = resolve_user_path(context, params.get("backup_target_path"), default=context.paths.output)
    process_name = _browser_process_name(definition)
    context.log(f"Browser: {definition['label']} ({browser_key})")
    context.log(f"Process: {process_name}")
    context.log(f"Process running: {_browser_process_running(process_name)}")
    context.log(f"Profile: {profile}")
    context.log(f"Backup source: {source_root}")
    context.log(f"Backup target: {target_root}")
    context.log("")
    context.log("=== Profile files ===")
    for row in _chromium_file_snapshot(profile):
        context.log(f"{row['name']}: exists={row['exists']} size={row['size']} modified={row['modified']}")
    latest = None
    try:
        latest_path = _find_latest_chromium_backup(source_root)
        latest = str(latest_path)
        context.log("")
        context.log(f"Latest importable backup from source: {latest_path}")
    except RuntimeError as exc:
        context.log("")
        context.log(f"Latest importable backup from source: {exc}")
    return {
        "mode": "status",
        "browser": browser_key,
        "profile": str(profile),
        "backup_source": str(source_root),
        "backup_target": str(target_root),
        "latest_source_backup": latest,
    }


def _import_chromium_backup_into_browser(
    context: JobContext,
    params: dict[str, Any],
    source_dir: Path,
    browser_key: str,
    definition: dict[str, object],
    *,
    stamp: str,
    close_process: bool,
    pre_import_label: str,
    ignore_profile_override: bool = False,
) -> dict[str, object]:
    profile_params = dict(params)
    if ignore_profile_override:
        profile_params.pop("browser_profile_path", None)
    profile = _resolve_browser_profile_path(context, profile_params, definition)
    process_name = _browser_process_name(definition)
    _close_browser_process(context, process_name, enabled=close_process)
    profile.mkdir(parents=True, exist_ok=True)
    pre_import_dir, pre_import_version_suffix, pre_import_version_number = _next_versioned_chromium_backup_dir(
        _local_browser_bookmark_backup_root(context),
        date_prefix=stamp,
        backup_label=pre_import_label,
        browser_key=browser_key,
        version_value=params.get("backup_version"),
    )
    existing_files = [name for name in CHROMIUM_BOOKMARK_FILES if (profile / name).is_file()]
    create_rollback = bool(params.get("create_rollback_backup", True))
    if existing_files and create_rollback:
        pre_import_dir.mkdir(parents=True, exist_ok=True)
        for file_name in existing_files:
            shutil.copy2(profile / file_name, pre_import_dir / file_name)
            context.log(f"Pre-import backup: {profile / file_name} -> {pre_import_dir / file_name}")
        _write_chromium_backup_manifest(
            pre_import_dir / "audion_browser_bookmarks_manifest.json",
            {
                "kind": "Audion Chromium Bookmarks Master",
                "mode": "pre_import_backup",
                "created_at": datetime.now().isoformat(timespec="seconds"),
                "date_prefix": stamp,
                "version": pre_import_version_number,
                "version_suffix": pre_import_version_suffix,
                "browser": browser_key,
                "browser_label": definition["label"],
                "profile": str(profile),
                "source_dir": str(source_dir),
                "backup_dir": str(pre_import_dir),
                "files": _chromium_file_snapshot(pre_import_dir),
            },
        )
    else:
        context.log("Pre-import rollback was skipped or no existing Chromium bookmark files were found.")
    context.log("Clearing local Favicons cache before import.")
    _clear_chromium_favicons(context, profile)
    copied = _copy_chromium_file_set(context, source_dir, profile, overwrite=True)
    context.log(f"Imported Chromium bookmark master from: {source_dir}")
    context.log("Next step: start the browser manually and enable bookmark sync only after checking the local state.")
    return {
        "browser": browser_key,
        "source_dir": str(source_dir),
        "profile": str(profile),
        "pre_import_backup": str(pre_import_dir) if existing_files and create_rollback else "",
        "files": copied,
    }


def _import_chromium_html_into_browser(
    context: JobContext,
    params: dict[str, Any],
    html_path: Path,
    browser_key: str,
    definition: dict[str, object],
    *,
    stamp: str,
    close_process: bool,
) -> dict[str, object]:
    profile = _resolve_browser_profile_path(context, params, definition)
    _close_browser_process(context, _browser_process_name(definition), enabled=close_process)
    profile.mkdir(parents=True, exist_ok=True)
    pre_import_dir, suffix, version = _next_versioned_chromium_backup_dir(
        _local_browser_bookmark_backup_root(context), date_prefix=stamp,
        backup_label=f"pre_import_{browser_key}", browser_key=browser_key,
        version_value=params.get("backup_version"),
    )
    existing_files = [name for name in CHROMIUM_BOOKMARK_FILES if (profile / name).is_file()]
    create_rollback = bool(params.get("create_rollback_backup", True))
    if existing_files and create_rollback:
        pre_import_dir.mkdir(parents=True, exist_ok=True)
        for name in existing_files:
            shutil.copy2(profile / name, pre_import_dir / name)
        _write_chromium_backup_manifest(pre_import_dir / "audion_browser_bookmarks_manifest.json", {
            "kind": "Audion Chromium Bookmarks Master", "mode": "pre_import_html_backup",
            "created_at": datetime.now().isoformat(timespec="seconds"), "version": version,
            "version_suffix": suffix, "browser": browser_key, "profile": str(profile),
            "source_html": str(html_path), "files": _chromium_file_snapshot(pre_import_dir),
        })
    payload, embedded_icons = chromium_bookmarks_and_icons_from_html(html_path)
    temp_json = profile / f".Bookmarks.audion-html-{os.getpid()}"
    try:
        temp_json.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        json.loads(temp_json.read_text(encoding="utf-8"))
        context.log("Replacing Bookmarks and rebuilding Favicons from embedded HTML ICON data.")
        os.replace(temp_json, profile / "Bookmarks")
        merged_icons = _merge_html_icons_into_favicons(context, profile, embedded_icons)
    finally:
        if temp_json.exists():
            temp_json.unlink()
    context.log(f"Imported HTML bookmarks: {html_path} -> {profile / 'Bookmarks'}")
    return {"browser": browser_key, "source_html": str(html_path), "profile": str(profile),
            "pre_import_backup": str(pre_import_dir) if existing_files and create_rollback else "",
            "bookmarks": len(payload["roots"]["bookmark_bar"]["children"]), "favicons_merged": merged_icons}


def browser_bookmarks_master(context: JobContext) -> dict[str, object]:
    params = context.operation.parameters
    mode = str(params.get("mode", "status")).strip().lower()
    browser_keys = _selected_chromium_browser_keys(params)
    close_process = bool(params.get("close_browser_process", True))
    stamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")

    if mode == "status":
        results = []
        for index, browser_key in enumerate(browser_keys, start=1):
            _key, definition = _chromium_browser_definition(browser_key)
            if len(browser_keys) > 1:
                context.log(f"=== Browser status [{index}/{len(browser_keys)}] ===")
            results.append(_browser_bookmarks_status(context, params, browser_key, definition))
            if index < len(browser_keys):
                context.log("")
        return {"mode": "status", "browsers": browser_keys, "results": results}

    if mode == "open_local_backup":
        path = _local_browser_bookmark_backup_root(context)
        open_path(context, path)
        return {"mode": mode, "folder": str(path)}

    if mode == "clear_favicons":
        results = []
        skipped = []
        for index, browser_key in enumerate(browser_keys, start=1):
            _key, definition = _chromium_browser_definition(browser_key)
            profile = _resolve_browser_profile_path(context, params, definition)
            process_name = _browser_process_name(definition)
            if len(browser_keys) > 1:
                context.log(f"=== Clear Favicons [{index}/{len(browser_keys)}]: {definition['label']} ===")
            skip_reason = _chromium_profile_skip_reason(profile, "Browser profile", require_files=False)
            if skip_reason:
                skipped.append(_skip_chromium_browser(context, browser_key, definition, profile, skip_reason))
                continue
            _close_browser_process(context, process_name, enabled=close_process)
            existing_files = [name for name in CHROMIUM_BOOKMARK_FILES if (profile / name).is_file()]
            rollback_dir = ""
            if existing_files and bool(params.get("create_rollback_backup", True)):
                backup_dir, suffix, version = _next_versioned_chromium_backup_dir(
                    _local_browser_bookmark_backup_root(context), date_prefix=stamp,
                    backup_label=f"pre_favicons_clear_{browser_key}", browser_key=browser_key,
                    version_value=params.get("backup_version"),
                )
                backup_dir.mkdir(parents=True, exist_ok=True)
                for name in existing_files:
                    shutil.copy2(profile / name, backup_dir / name)
                _write_chromium_backup_manifest(backup_dir / "audion_browser_bookmarks_manifest.json", {
                    "kind": "Audion Chromium Bookmarks Master", "mode": "pre_favicons_clear",
                    "created_at": datetime.now().isoformat(timespec="seconds"), "version": version,
                    "version_suffix": suffix, "browser": browser_key, "profile": str(profile),
                    "files": _chromium_file_snapshot(backup_dir),
                })
                rollback_dir = str(backup_dir)
                context.log(f"Favicons rollback backup: {backup_dir}")
            deleted = _clear_chromium_favicons(context, profile)
            results.append({"browser": browser_key, "profile": str(profile), "rollback_backup": rollback_dir, "deleted": deleted})
        return {"mode": mode, "browsers": browser_keys, "results": results, "skipped": skipped}

    if mode == "export_master":
        target_root = resolve_user_path(context, params.get("backup_target_path"), default=context.paths.output)
        backup_label = str(params.get("backup_label") or "").strip()
        backup_version = params.get("backup_version")
        results = []
        skipped = []
        for index, browser_key in enumerate(browser_keys, start=1):
            _key, definition = _chromium_browser_definition(browser_key)
            profile = _resolve_browser_profile_path(context, params, definition)
            process_name = _browser_process_name(definition)
            effective_backup_label = f"{backup_label}_{browser_key}" if backup_label and len(browser_keys) > 1 else backup_label
            if len(browser_keys) > 1:
                context.log(f"=== Export master [{index}/{len(browser_keys)}]: {definition['label']} ===")
            skip_reason = _chromium_profile_skip_reason(profile, "Browser profile", require_files=True)
            if skip_reason:
                skipped.append(_skip_chromium_browser(context, browser_key, definition, profile, skip_reason))
                continue
            _close_browser_process(context, process_name, enabled=close_process)
            backup_dir, version_suffix, version_number = _next_versioned_chromium_backup_dir(
                target_root,
                date_prefix=stamp,
                backup_label=effective_backup_label,
                browser_key=browser_key,
                version_value=backup_version,
            )
            copied = _copy_chromium_file_set(context, profile, backup_dir, overwrite=False)
            manifest = {
                "kind": "Audion Chromium Bookmarks Master",
                "mode": "export_master",
                "created_at": datetime.now().isoformat(timespec="seconds"),
                "date_prefix": stamp,
                "version": version_number,
                "version_suffix": version_suffix,
                "backup_label": effective_backup_label,
                "requested_backup_label": backup_label,
                "browser": browser_key,
                "browser_label": definition["label"],
                "process": process_name,
                "profile": str(profile),
                "backup_dir": str(backup_dir),
                "files": copied,
            }
            _write_chromium_backup_manifest(backup_dir / "audion_browser_bookmarks_manifest.json", manifest)
            context.log(f"Exported Chromium bookmark master backup: {backup_dir}")
            results.append({"browser": browser_key, "backup_dir": str(backup_dir), "files": copied})
        return {"mode": mode, "browsers": browser_keys, "results": results, "skipped": skipped}

    if mode == "import_master":
        source_root = resolve_user_path(context, params.get("backup_source_path"), default=context.paths.input)
        source_kind = str(params.get("bookmark_import_kind") or "native").strip().lower()
        html_value = str(params.get("bookmark_html_path") or "").strip()
        selected_native = str(params.get("bookmark_backup_path") or "").strip()
        html_path = resolve_user_path(context, html_value, default=source_root) if html_value else None
        source_dir = resolve_user_path(context, selected_native, default=source_root) if selected_native else None
        if source_kind == "html":
            if html_path is None:
                raise RuntimeError("Choose an HTML bookmarks file before import.")
            chromium_bookmarks_from_html(html_path)
        else:
            source_dir = source_dir if source_dir and all((source_dir / name).is_file() for name in CHROMIUM_REQUIRED_FILES) else _find_latest_chromium_backup(source_root)
            _assert_chromium_files(source_dir, "Backup source")
        results = []
        skipped = []
        for index, browser_key in enumerate(browser_keys, start=1):
            _key, definition = _chromium_browser_definition(browser_key)
            profile = _resolve_browser_profile_path(context, params, definition)
            if len(browser_keys) > 1:
                context.log(f"=== Import master [{index}/{len(browser_keys)}]: {definition['label']} ===")
            skip_reason = _chromium_profile_skip_reason(profile, "Browser profile", require_files=False)
            if skip_reason:
                skipped.append(_skip_chromium_browser(context, browser_key, definition, profile, skip_reason))
                continue
            results.append(
                _import_chromium_html_into_browser(context, params, html_path, browser_key, definition, stamp=stamp, close_process=close_process)
                if source_kind == "html" and html_path is not None else _import_chromium_backup_into_browser(
                    context,
                    params,
                    source_dir,
                    browser_key,
                    definition,
                    stamp=stamp,
                    close_process=close_process,
                    pre_import_label=f"pre_import_{browser_key}",
                )
            )
        return {"mode": mode, "browsers": browser_keys, "source_kind": source_kind,
                "source": str(html_path if source_kind == "html" else source_dir), "results": results, "skipped": skipped}

    if mode == "transfer_master":
        source_key, target_keys = _transfer_chromium_browser_keys(params)
        _key, source_definition = _chromium_browser_definition(source_key)
        source_profile = _resolve_browser_profile_path(context, params, source_definition)
        source_process_name = _browser_process_name(source_definition)
        backup_label = str(params.get("backup_label") or "").strip() or "bookmarks_master"
        transfer_label = f"{backup_label}_transfer_from_{source_key}"

        context.log("=== Transfer step 1/2: export source browser into project-local backup ===")
        context.log(f"Source browser: {source_definition['label']} ({source_key})")
        context.log(f"Targets: {', '.join(target_keys)}")
        skipped = []
        source_skip_reason = _chromium_profile_skip_reason(source_profile, "Source browser profile", require_files=True)
        if source_skip_reason:
            skipped.append(_skip_chromium_browser(context, source_key, source_definition, source_profile, source_skip_reason))
            return {
                "mode": mode,
                "source_browser": source_key,
                "target_browsers": target_keys,
                "transfer_backup": "",
                "exported_files": [],
                "results": [],
                "skipped": skipped,
            }

        target_entries: list[tuple[str, dict[str, object]]] = []
        target_params = dict(params)
        target_params.pop("browser_profile_path", None)
        for browser_key in target_keys:
            _target_key, definition = _chromium_browser_definition(browser_key)
            target_profile = _resolve_browser_profile_path(context, target_params, definition)
            skip_reason = _chromium_profile_skip_reason(target_profile, "Target browser profile", require_files=False)
            if skip_reason:
                skipped.append(_skip_chromium_browser(context, browser_key, definition, target_profile, skip_reason))
                continue
            target_entries.append((browser_key, definition))
        if not target_entries:
            context.log("No available target browser profiles were found for transfer.")
            return {
                "mode": mode,
                "source_browser": source_key,
                "target_browsers": target_keys,
                "transfer_backup": "",
                "exported_files": [],
                "results": [],
                "skipped": skipped,
            }

        _close_browser_process(context, source_process_name, enabled=close_process)
        transfer_dir, transfer_version_suffix, transfer_version_number = _next_versioned_chromium_backup_dir(
            _local_browser_bookmark_backup_root(context),
            date_prefix=stamp,
            backup_label=transfer_label,
            browser_key=source_key,
            version_value=params.get("backup_version"),
        )
        exported_files = _copy_chromium_file_set(context, source_profile, transfer_dir, overwrite=False)
        _write_chromium_backup_manifest(
            transfer_dir / "audion_browser_bookmarks_manifest.json",
            {
                "kind": "Audion Chromium Bookmarks Master",
                "mode": "transfer_master_export",
                "created_at": datetime.now().isoformat(timespec="seconds"),
                "date_prefix": stamp,
                "version": transfer_version_number,
                "version_suffix": transfer_version_suffix,
                "backup_label": transfer_label,
                "source_browser": source_key,
                "source_browser_label": source_definition["label"],
                "source_process": source_process_name,
                "source_profile": str(source_profile),
                "target_browsers": target_keys,
                "backup_dir": str(transfer_dir),
                "files": exported_files,
            },
        )
        context.log(f"Intermediate transfer backup: {transfer_dir}")

        context.log("")
        context.log("=== Transfer step 2/2: import backup into target browsers ===")
        results = []
        for index, (browser_key, definition) in enumerate(target_entries, start=1):
            context.log(f"=== Transfer import [{index}/{len(target_entries)}]: {definition['label']} ===")
            results.append(
                _import_chromium_backup_into_browser(
                    context,
                    params,
                    transfer_dir,
                    browser_key,
                    definition,
                    stamp=stamp,
                    close_process=close_process,
                    pre_import_label=f"pre_transfer_{browser_key}",
                    ignore_profile_override=True,
                )
            )
            if index < len(target_entries):
                context.log("")
        return {
            "mode": mode,
            "source_browser": source_key,
            "target_browsers": target_keys,
            "transfer_backup": str(transfer_dir),
            "exported_files": exported_files,
            "results": results,
            "skipped": skipped,
        }

    raise RuntimeError(f"Unknown Browser Bookmarks Master mode: {mode}")


NUKE_TOOL_DEFINITIONS: dict[str, dict[str, object]] = {
    "codex": {
        "folder": "codex_nuke",
        "script": "Invoke-CodexNuke.ps1",
        "label": "Codex Nuke",
        "modes": {"Audit", "DryRun", "Nuke", "SessionReset"},
        "switches": {"KeepCaches", "SkipReboot", "KeepCliState", "SkipStoreReset"},
    },
    "python": {
        "folder": "python_nuke",
        "script": "Invoke-PythonNuke.ps1",
        "label": "Python Nuke",
        "modes": {"Audit", "DryRun", "Nuke"},
        "switches": {"KeepWinget", "KeepProjectVenvs"},
    },
}


def _nuke_log_path(context: JobContext, tool_key: str, mode: str) -> Path:
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_dir = context.paths.logs / "nuke" / tool_key
    log_dir.mkdir(parents=True, exist_ok=True)
    return log_dir / f"{tool_key}_{mode.lower()}_{stamp}.log"


def _run_integrated_nuke_tool(context: JobContext, parameters: dict[str, Any]) -> dict[str, object]:
    tool_key = str(parameters.get("tool", "")).strip().lower()
    definition = NUKE_TOOL_DEFINITIONS.get(tool_key)
    if definition is None:
        raise RuntimeError(f"Unknown integrated nuke tool: {tool_key}")

    mode = str(parameters.get("mode", "Audit")).strip()
    allowed_modes = definition["modes"]
    if not isinstance(allowed_modes, set) or mode not in allowed_modes:
        allowed_text = ", ".join(sorted(str(item) for item in allowed_modes))
        raise RuntimeError(f"Unsupported {definition['label']} mode: {mode}. Expected: {allowed_text}")

    tool_root = project_tool_dir(context, str(definition["folder"]))
    script = tool_root / str(definition["script"])
    log_path = _nuke_log_path(context, tool_key, mode)
    script_parameters: dict[str, Any] = {
        "Mode": mode,
        "LogPath": str(log_path),
    }
    switches = definition["switches"]
    if isinstance(switches, set):
        for switch_name in sorted(switches):
            if bool(parameters.get(switch_name, False)):
                script_parameters[switch_name] = True

    elevated = mode == "Nuke"
    context.log(f"[NUKE] {definition['label']}: {mode}")
    context.log(f"[NUKE] Transcript: {log_path}")
    result = run_ps1(
        context,
        script,
        script_parameters,
        cwd=script.parent,
        progress_seconds=900.0,
        elevated=elevated,
        check=False,
    )
    if result.exit_code == 255:
        raise RuntimeError(f"{definition['label']} failed with a fatal exit code; see log: {log_path}")
    if mode == "Nuke" and result.exit_code != 0:
        raise RuntimeError(f"{definition['label']} finished with exit code {result.exit_code}; see log: {log_path}")
    return {
        "tool": tool_key,
        "mode": mode,
        "script": str(script),
        "log_path": str(log_path),
        "exit_code": result.exit_code,
    }


def integrated_nuke_tool(context: JobContext) -> dict[str, object]:
    return _run_integrated_nuke_tool(context, dict(context.operation.parameters))


def python_nuke(context: JobContext) -> dict[str, object]:
    parameters = dict(context.operation.parameters)
    parameters.update({"tool": "python", "mode": "Nuke"})
    return _run_integrated_nuke_tool(context, parameters)


def storage_inventory(context: JobContext) -> dict[str, object]:
    script = r"""
$ErrorActionPreference = 'Continue'
$isAdmin = ([Security.Principal.WindowsPrincipal] [Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
Write-Host "Administrator: $isAdmin"
Write-Host ""
Write-Host "=== Get-Disk ==="
Get-Disk | Sort-Object Number | Format-Table Number,FriendlyName,BusType,Size,PartitionStyle,HealthStatus,IsSystem,IsBoot,IsOffline,IsReadOnly -AutoSize | Out-String -Width 240
Write-Host "=== Get-Volume ==="
Get-Volume | Sort-Object DriveLetter | Format-Table DriveLetter,FileSystemLabel,FileSystem,HealthStatus,SizeRemaining,Size -AutoSize | Out-String -Width 240
"""
    run_ps_command(context, script, progress_seconds=60.0)
    return {"inventory": "disk_volume"}


def disk_details(context: JobContext) -> dict[str, object]:
    raw_disk_number = str(context.operation.parameters.get("disk_number", "")).strip()
    if raw_disk_number == "":
        raise RuntimeError("Disk number is empty.")
    try:
        disk_number = int(raw_disk_number)
    except ValueError as exc:
        raise RuntimeError(f"Disk number must be an integer: {raw_disk_number}") from exc
    if disk_number < 0:
        raise RuntimeError(f"Disk number must be zero or greater: {disk_number}")
    script = f"""
$ErrorActionPreference = 'Stop'
$diskNumber = {disk_number}
Write-Host "=== Disk $diskNumber ==="
Get-Disk -Number $diskNumber | Format-List * | Out-String -Width 240
Write-Host "=== Partitions ==="
Get-Partition -DiskNumber $diskNumber | Sort-Object Offset | Format-Table PartitionNumber,DriveLetter,Type,GptType,Size,Offset -AutoSize | Out-String -Width 240
"""
    run_ps_command(context, script, progress_seconds=60.0)
    return {"disk_number": disk_number}


def winre_status(context: JobContext) -> dict[str, object]:
    script = r"""
$ErrorActionPreference = 'Continue'
Write-Host "=== reagentc /info ==="
reagentc /info
Write-Host ""
Write-Host "=== OS partition layout ==="
$systemDrive = $env:SystemDrive.TrimEnd(':')
$osPartition = Get-Partition -DriveLetter $systemDrive
if ($osPartition) {
  Get-Partition -DiskNumber $osPartition.DiskNumber | Sort-Object Offset | Format-Table PartitionNumber,DriveLetter,Type,GptType,Size,Offset -AutoSize | Out-String -Width 240
} else {
  Write-Host "OS partition was not detected."
}
"""
    run_ps_command(context, script, progress_seconds=60.0)
    return {"status": "winre"}


def run_winre_wizard(context: JobContext) -> dict[str, object]:
    confirm = str(context.operation.parameters.get("winre_typed_confirm") or "").strip()
    if confirm != "YES":
        raise RuntimeError("WinRE extend is destructive. Type YES in the confirmation field to run it.")
    script = project_tool_dir(context, "winre_extend") / "Remove-WinRE-And-Extend-System.ps1"
    run_ps1(
        context,
        script,
        {"NoPause": True, "YesIUnderstand": True},
        cwd=script.parent,
        progress_seconds=600.0,
        elevated=True,
    )
    return {"script": str(script)}


def launch_external_cmd(context: JobContext, script: Path) -> None:
    if not script.exists():
        raise RuntimeError(f"CMD script was not found: {script}")
    context.log(f"Launching external console: {script}")
    subprocess.Popen(["cmd.exe", "/d", "/c", "start", "", str(script)], cwd=str(script.parent))
    context.progress(1.0)


def run_ssd_reset_wizard(context: JobContext) -> dict[str, object]:
    script = project_tool_dir(context, "ssd_nvme_reset_wizard") / "Run-Audion-SSD-NVMe-Reset-Wizard.cmd"
    launch_external_cmd(context, script)
    return {"script": str(script)}


def terminal_command(context: JobContext) -> dict[str, object]:
    params = context.operation.parameters
    command_text = str(params.get("command") or "").strip()
    if not command_text:
        raise RuntimeError("Command is empty.")
    shell = str(params.get("shell") or "pwsh").strip().lower()
    cwd = resolve_user_path(context, params.get("cwd"), default=context.paths.root)
    if cwd.is_file():
        cwd = cwd.parent
    if not cwd.exists():
        raise RuntimeError(f"Working directory was not found: {cwd}")
    context.log(f"Terminal shell: {shell}")
    context.log(f"Terminal cwd: {cwd}")
    # The terminal bar runs arbitrary third-party tools, so the child console must speak UTF-8.
    # Without this the child writes in the OEM code page and drops everything outside it
    # (arrows, check marks, block characters) before we ever get the bytes.
    if shell == "cmd":
        command = ["cmd.exe", "/d", "/c", f"chcp 65001>nul & {command_text}"]
    else:
        command = powershell_command(context.paths.root, "-Command", POWERSHELL_UTF8_PREAMBLE + command_text)
    result = run_process(context, command, cwd=cwd, check=False, progress_seconds=300.0)
    if result.exit_code != 0:
        raise RuntimeError(f"Terminal command failed with exit code {result.exit_code}.")
    return {"shell": shell, "cwd": str(cwd), "exit_code": result.exit_code}


def ripgrep_status(context: JobContext) -> dict[str, object]:
    folder = context.paths.root / "ripgrep"
    exe = folder / ("rg.exe" if os.name == "nt" else "rg")
    if not exe.exists():
        raise RuntimeError(f"Project ripgrep executable was not found: {exe}")
    context.log(f"Project ripgrep folder: {folder}")
    result = run_process(context, [str(exe), "--version"], cwd=folder, check=True, progress_seconds=10.0)
    version = next((line.strip() for line in result.lines if line.strip()), "")
    if not version.lower().startswith("ripgrep "):
        raise RuntimeError(f"Unexpected ripgrep version output: {version or '<empty>'}")
    context.log(f"Resolved ripgrep version: {version}")
    return {"rg": str(exe), "version": version}


def docs_pdf_export(context: JobContext) -> dict[str, object]:
    params = context.operation.parameters
    mode = str(params.get("mode", "render")).strip().lower()
    pdf_root = context.paths.root / "docs" / "PDF"
    if mode == "open_folder":
        open_path(context, pdf_root)
        return {"folder": str(pdf_root)}

    if mode not in {"render", "plan"}:
        raise RuntimeError(f"Unsupported docs PDF mode: {mode}")

    script = context.paths.system_core / "docs_pdf.py"
    if not script.exists():
        raise RuntimeError(f"Docs PDF wrapper was not found: {script}")
    python_exe = context.paths.root / "runtime" / "python.exe"
    python_cmd = str(python_exe if python_exe.exists() else Path(sys.executable))
    theme = str(params.get("docs_pdf_theme", "both")).strip() or "both"
    command = [python_cmd, str(script), "--theme", theme]
    if mode == "plan":
        command.append("--dry-run")
    if not bool(params.get("docs_pdf_include_agent_instructions", True)):
        command.append("--no-agent-instructions")

    context.log(f"Docs PDF mode: {mode}")
    context.log(f"Docs PDF root: {pdf_root}")
    context.log(f"Docs PDF theme: {theme}")
    result = run_process(context, command, cwd=context.paths.root, check=True, progress_seconds=900.0)
    return {"mode": mode, "pdf_root": str(pdf_root), "exit_code": result.exit_code}


def open_tool_folder(context: JobContext) -> dict[str, object]:
    name = str(context.operation.parameters.get("folder", "")).strip()
    if not name:
        raise RuntimeError("Folder name is empty.")
    if name == "WSL":
        path = ensure_wsl_workspace(context)
    elif name.lower() == "ripgrep":
        path = context.paths.root / "ripgrep"
        path.mkdir(parents=True, exist_ok=True)
    elif name.lower().startswith("tools/"):
        path = project_tool_dir(context, name[6:])
    else:
        raise RuntimeError(f"Only project-local tool folders can be opened from the GUI: {name}")
    context.log(f"Opening folder: {path}")
    if os.name == "nt":
        subprocess.Popen(["explorer.exe", str(path)])
    else:
        subprocess.Popen(["xdg-open", str(path)])
    context.progress(1.0)
    return {"folder": str(path)}


def open_project_path(context: JobContext) -> dict[str, object]:
    raw = str(context.operation.parameters.get("path", "")).strip().replace("\\", "/")
    if not raw:
        raise RuntimeError("Project path is empty.")
    relative = Path(raw)
    if relative.is_absolute() or ".." in relative.parts:
        raise RuntimeError(f"Unsafe project path: {raw}")
    path = (context.paths.root / relative).resolve()
    root = context.paths.root.resolve()
    if path != root and root not in path.parents:
        raise RuntimeError(f"Project path escaped root: {path}")
    open_path(context, path)
    return {"path": str(path)}
