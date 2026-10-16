"""What state the machine is in, for the switches of the window: one answer per page, nothing in a log.

A switch of the window is a row of operations, each bringing the machine into one state: the cable or
a Wi-Fi network, a resolver of names, a mode of the hypervisor, a lock on drivers. The window lights
the one the machine is in now; this module says which, read from the same places the operations
"Status" read - the registry, the hosts file, bcdedit, the optional features and the devices of
Windows - but without printing, and fast: the registry and the network tables are read directly, and
what only PowerShell knows is asked in one call per page.

    page_state("link", root) -> {"switches": {"internet": {"is": "main", "detail": "Wi-Fi · Home-5G · 192.168.0.1"}}}

`is` is "" when the state is none of the switch (another network, a resolver of one's own) or could not
be read; `detail` says what was seen; `pending` names the state that comes after a restart, when it is
not the one in force; `note` is a word of trouble (no rights, no device).
"""
from __future__ import annotations

import ctypes
import json
import os
import re
import subprocess
from ctypes import wintypes
from pathlib import Path
from typing import Any

try:
    import winreg
except ImportError:  # pragma: no cover - the program is for Windows
    winreg = None  # type: ignore[assignment]

PROVIDERS = {
    "cloudflare": {"1.1.1.1", "1.0.0.1"},
    "google": {"8.8.8.8", "8.8.4.4"},
    "quad9": {"9.9.9.9", "149.112.112.112"},
    "yandex": {"77.88.8.8", "77.88.8.1"},
    "adguard": {"94.140.14.14", "94.140.15.15"},
}
HOSTS_MARKER = "AUDION_BITRIX_HOSTS"
IF_TYPE_ETHERNET, IF_TYPE_WIFI = 6, 71
NVIDIA_DISPLAY = re.compile(r"(?i)^PCI\\VEN_10DE")
NVIDIA_AUDIO = re.compile(r"(?i)^HDAUDIO\\FUNC_01&VEN_10DE")


def _hidden() -> dict[str, Any]:
    if os.name != "nt":
        return {}
    info = subprocess.STARTUPINFO()
    info.dwFlags |= subprocess.STARTF_USESHOWWINDOW
    info.wShowWindow = 0
    return {"startupinfo": info, "creationflags": getattr(subprocess, "CREATE_NO_WINDOW", 0)}


def _run(command: list[str], timeout: float = 20.0) -> tuple[int, str]:
    from system_core.core.output_decode import decode_process_bytes

    try:
        done = subprocess.run(command, capture_output=True, timeout=timeout, stdin=subprocess.DEVNULL, **_hidden())
    except (OSError, subprocess.TimeoutExpired) as error:
        return -1, str(error)
    return done.returncode, decode_process_bytes(done.stdout or b"") + decode_process_bytes(done.stderr or b"")


def _reg_value(root: Any, path: str, name: str) -> Any:
    if winreg is None:
        return None
    try:
        with winreg.OpenKey(root, path) as key:
            return winreg.QueryValueEx(key, name)[0]
    except OSError:
        return None


def _reg_values(root: Any, path: str) -> list[Any]:
    if winreg is None:
        return []
    values = []
    try:
        with winreg.OpenKey(root, path) as key:
            index = 0
            while True:
                try:
                    values.append(winreg.EnumValue(key, index)[1])
                except OSError:
                    break
                index += 1
    except OSError:
        return []
    return values


# --- the interface the internet goes through -------------------------------------------------------

class _GUID(ctypes.Structure):
    _fields_ = [("Data1", wintypes.DWORD), ("Data2", wintypes.WORD), ("Data3", wintypes.WORD), ("Data4", ctypes.c_ubyte * 8)]

    def text(self) -> str:
        tail = bytes(self.Data4)
        return "{%08X-%04X-%04X-%s-%s}" % (self.Data1, self.Data2, self.Data3, tail[:2].hex().upper(), tail[2:].hex().upper())


def best_interface() -> dict[str, Any]:
    """The interface Windows would send 8.8.8.8 through: its index, kind, GUID and alias; {} when none."""
    if os.name != "nt":
        return {}
    iphlpapi = ctypes.windll.iphlpapi
    index = wintypes.DWORD()
    destination = int.from_bytes(bytes([8, 8, 8, 8]), "little")
    if iphlpapi.GetBestInterface(wintypes.DWORD(destination), ctypes.byref(index)) != 0:
        return {}
    luid = ctypes.c_uint64()
    if iphlpapi.ConvertInterfaceIndexToLuid(index, ctypes.byref(luid)) != 0:
        return {"index": index.value}
    guid = _GUID()
    iphlpapi.ConvertInterfaceLuidToGuid(ctypes.byref(luid), ctypes.byref(guid))
    alias = ctypes.create_unicode_buffer(257)
    iphlpapi.ConvertInterfaceLuidToAlias(ctypes.byref(luid), alias, 257)
    return {"index": index.value, "type": (luid.value >> 48) & 0xFFFF, "guid": guid.text(), "alias": alias.value}


def _tcpip(guid: str, name: str) -> str:
    if winreg is None or not guid:
        return ""
    value = _reg_value(winreg.HKEY_LOCAL_MACHINE, rf"SYSTEM\CurrentControlSet\Services\Tcpip\Parameters\Interfaces\{guid}", name)
    if isinstance(value, list):
        return " ".join(str(item) for item in value if item)
    return str(value or "").strip()


def _gateway(guid: str) -> str:
    for name in ("DefaultGateway", "DhcpDefaultGateway"):
        text = _tcpip(guid, name)
        if text:
            return text.replace(",", " ").split()[0]
    return ""


def _ssid() -> str:
    code, text = _run(["netsh.exe", "wlan", "show", "interfaces"], 10.0)
    if code != 0:
        return ""
    for line in text.splitlines():
        found = re.match(r"^\s*SSID\s*:\s*(.+?)\s*$", line)
        if found:
            return found.group(1)
    return ""


def _wifi_slots(root: Path) -> dict[str, str]:
    path = Path(root) / "data" / "wifi" / "slots.json"
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    return {key: str(value.get("ssid") or "") for key, value in data.items() if isinstance(value, dict)}


def internet(root: Path) -> dict[str, Any]:
    face = best_interface()
    if not face.get("type"):
        return {"is": "", "detail": "", "note": "offline"}
    gateway = _gateway(face.get("guid", ""))
    if face["type"] == IF_TYPE_ETHERNET:
        return {"is": "cable", "detail": " · ".join(part for part in (face.get("alias", ""), gateway) if part)}
    if face["type"] == IF_TYPE_WIFI:
        ssid = _ssid()
        slots = _wifi_slots(root)
        state = next((slot for slot, name in slots.items() if name and name == ssid), "")
        return {"is": state, "detail": " · ".join(part for part in (face.get("alias", ""), ssid, gateway) if part)}
    return {"is": "", "detail": face.get("alias", "")}


def resolver(root: Path) -> dict[str, Any]:
    face = best_interface()
    guid = face.get("guid", "")
    if not guid:
        return {"is": "", "detail": "", "note": "offline"}
    static = [item for item in _tcpip(guid, "NameServer").replace(",", " ").split() if item]
    if not static:
        dhcp = _tcpip(guid, "DhcpNameServer")
        return {"is": "auto", "detail": " · ".join(part for part in (face.get("alias", ""), dhcp) if part)}
    servers = set(static)
    detail = " · ".join([face.get("alias", ""), ", ".join(static)])
    if servers == {_gateway(guid)}:
        return {"is": "router", "detail": detail}
    for name, addresses in PROVIDERS.items():
        if servers <= addresses:
            return {"is": name, "detail": detail}
    return {"is": "", "detail": detail}


def hosts_override(root: Path) -> dict[str, Any]:
    path = Path(os.environ.get("SystemRoot", r"C:\Windows")) / "System32" / "drivers" / "etc" / "hosts"
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except OSError as error:
        return {"is": "", "detail": "", "note": str(error)}
    for line in text.splitlines():
        if HOSTS_MARKER in line and line.strip() and not line.lstrip().startswith("#"):
            return {"is": "on", "detail": " ".join(line.split("#", 1)[0].split())}
    return {"is": "off", "detail": ""}


def wu_drivers(root: Path) -> dict[str, Any]:
    if winreg is None:
        return {"is": ""}
    value = _reg_value(winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Policies\Microsoft\Windows\WindowsUpdate", "ExcludeWUDriversInQualityUpdate")
    return {"is": "blocked" if value == 1 else "allowed", "detail": "ExcludeWUDriversInQualityUpdate = " + ("1" if value == 1 else "-")}


def _deny_ids() -> list[str]:
    if winreg is None:
        return []
    base = r"SOFTWARE\Policies\Microsoft\Windows\DeviceInstall\Restrictions"
    if _reg_value(winreg.HKEY_LOCAL_MACHINE, base, "DenyDeviceIDs") != 1:
        return []
    return [str(item) for item in _reg_values(winreg.HKEY_LOCAL_MACHINE, base + r"\DenyDeviceIDs")]


def nvidia_install(root: Path) -> dict[str, Any]:
    ids = [item for item in _deny_ids() if NVIDIA_DISPLAY.match(item)]
    return {"is": "blocked" if ids else "allowed", "detail": f"DenyDeviceIDs: {len(ids)}" if ids else ""}


def nvidia_audio_policy(root: Path) -> dict[str, Any]:
    ids = [item for item in _deny_ids() if NVIDIA_AUDIO.match(item)]
    return {"is": "banned" if ids else "none", "detail": f"DenyDeviceIDs: {len(ids)}" if ids else ""}


# --- what only PowerShell knows: one call per page -----------------------------------------------------

def _powershell(root: Path, script: str) -> Any:
    from system_core.services.devops_tools import resolve_pwsh

    code, text = _run([resolve_pwsh(root), "-NoProfile", "-NonInteractive", "-ExecutionPolicy", "Bypass", "-Command", script], 30.0)
    start = text.find("{")
    if code != 0 or start < 0:
        raise RuntimeError(text.strip()[-300:] or f"exit code {code}")
    return json.loads(text[start:])


FEATURES_SCRIPT = (
    "$ErrorActionPreference='Stop';"
    "$names='Microsoft-Hyper-V-All','VirtualMachinePlatform','HypervisorPlatform','Containers-DisposableClientVM';"
    "$f=@{}; foreach($n in $names){ $x=Get-CimInstance Win32_OptionalFeature -Filter (\"Name='\"+$n+\"'\") -ErrorAction SilentlyContinue;"
    " $f[$n]= if($x){[int]$x.InstallState}else{3} };"
    "$present=[bool](Get-CimInstance Win32_ComputerSystem).HypervisorPresent;"
    "@{features=$f; present=$present} | ConvertTo-Json -Compress"
)


def _bcd_launch_type() -> str:
    code, text = _run(["bcdedit.exe", "/enum", "{current}"], 10.0)
    if code != 0:
        return "?"
    found = re.search(r"(?im)^\s*hypervisorlaunchtype\s+(\w+)", text)
    return found.group(1).lower() if found else "auto"


def hyperv_page(root: Path) -> dict[str, Any]:
    try:
        told = _powershell(root, FEATURES_SCRIPT)
    except Exception as error:  # noqa: BLE001 - the window shows the word and lights nothing
        note = str(error)
        return {"hypervisor": {"is": "", "note": note}, "hyperv_feature": {"is": "", "note": note},
                "sandbox_feature": {"is": "", "note": note}}
    features = told.get("features") or {}
    launch = _bcd_launch_type()

    def enabled(name: str) -> bool:
        return int(features.get(name, 2)) == 1

    def feature(name: str) -> dict[str, Any]:
        state = int(features.get(name, 3))
        if state == 3:
            return {"is": "", "note": "absent"}
        return {"is": "on" if state == 1 else "off", "detail": name}

    if launch == "?":
        mode = {"is": "", "note": "rights"}
    else:
        configured = "thirdparty" if launch == "off" else "coexist" if enabled("HypervisorPlatform") else "hyperv"
        mode = {"is": configured, "detail": f"hypervisorlaunchtype {launch} · HypervisorPresent {bool(told.get('present'))}"}
        running = bool(told.get("present"))
        if (configured == "thirdparty") == running:
            # bcdedit says one thing and the hypervisor running says another: the change waits for a restart.
            mode["pending"] = configured
            mode["is"] = "hyperv" if running else "thirdparty"
    return {"hypervisor": mode, "hyperv_feature": feature("Microsoft-Hyper-V-All"), "sandbox_feature": feature("Containers-DisposableClientVM")}


AUDIO_SCRIPT = (
    "$ErrorActionPreference='Stop';"
    "$d=@(Get-CimInstance Win32_PnPEntity -Filter \"DeviceID LIKE 'HDAUDIO\\\\FUNC_01&VEN_10DE%'\" -ErrorAction SilentlyContinue);"
    "@{count=$d.Count; disabled=@($d | Where-Object { $_.ConfigManagerErrorCode -eq 22 }).Count; names=@($d | ForEach-Object { $_.Name })} | ConvertTo-Json -Compress"
)


def nvidia_page(root: Path) -> dict[str, Any]:
    told = {"nvidia_install": nvidia_install(root), "nvidia_audio_policy": nvidia_audio_policy(root)}
    try:
        audio = _powershell(root, AUDIO_SCRIPT)
        count, disabled = int(audio.get("count") or 0), int(audio.get("disabled") or 0)
        if not count:
            told["nvidia_audio_device"] = {"is": "", "note": "no_device"}
        else:
            names = audio.get("names") or []
            told["nvidia_audio_device"] = {"is": "off" if disabled == count else "on",
                                           "detail": " · ".join(str(name) for name in (names if isinstance(names, list) else [names]))}
    except Exception as error:  # noqa: BLE001
        told["nvidia_audio_device"] = {"is": "", "note": str(error)}
    return told


PAGES = {
    "link": lambda root: {"internet": internet(root)},
    "dns": lambda root: {"resolver": resolver(root)},
    "hosts": lambda root: {"hosts_override": hosts_override(root)},
    "wu": lambda root: {"wu_drivers": wu_drivers(root)},
    "nvidia": nvidia_page,
    "hyperv": hyperv_page,
}


def page_state(page: str, root: Path) -> dict[str, Any]:
    """The state of the switches of one page of the layout; a page without switches has none."""
    reader = PAGES.get(page)
    if reader is None:
        return {"switches": {}}
    return {"switches": reader(Path(root))}
