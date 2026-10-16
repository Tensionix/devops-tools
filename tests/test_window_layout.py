"""Every operation of the manifest has its place in the window, or is named as set aside.

    runtime\\python.exe -m pytest -q tests\\test_window_layout.py

config/window_layout.yaml is checked against config/tool_manifest.yaml by the words of
system_core/core/window_layout.py (`problems`): an operation that stands nowhere and is not in `folders`,
`pending` or `retired`, a name the manifest does not have, an operation that stands twice, a section
without its line or with fewer than two pages, a page without cards, a field set away that is not one of
the whole window.
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from system_core.core import window_layout  # noqa: E402
from system_core.core.manifest import load_manifest  # noqa: E402


def test_layout_has_no_problems() -> None:
    manifest = load_manifest(ROOT / "config" / "tool_manifest.yaml")
    layout = window_layout.load(ROOT / "config")
    assert window_layout.problems(layout, manifest) == []
