"""Every Russian text of the window has its English pair in Source\\config\\i18n.json.

    runtime\\python.exe tests\\test_window_i18n.py

The window speaks Russian in its code and its markup and asks the dictionary for the other
language (Lang.T, Lang.F, Lang.Walk). A text without a pair shows in Russian in the English
window: the texts handed to Lang.T and Lang.F, and the texts, tips and captions of the markup.
"""
from __future__ import annotations

import json
import re
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "Source"
CYRILLIC = re.compile("[А-Яа-яЁё]")
CALLED = re.compile(r'Lang\.[TF]\("((?:[^"\\]|\\.)*)"')
MARKED = re.compile(r'(?:Text|ToolTip\.Tip|Content|Watermark|PlaceholderText)="([^"]*)"')


def code_texts():
    for folder in (SOURCE, SOURCE / "Core", SOURCE / "Views"):
        for path in sorted(folder.glob("*.cs")):
            for match in CALLED.finditer(path.read_text(encoding="utf-8")):
                yield path.name, match.group(1).replace('\\"', '"').replace("\\n", "\n").replace("\\\\", "\\")
    for path in sorted(SOURCE.glob("*.axaml")):
        for match in MARKED.finditer(path.read_text(encoding="utf-8")):
            yield path.name, match.group(1).replace("&#10;", "\n").replace("&quot;", '"').replace("&amp;", "&")


class WindowDictionary(unittest.TestCase):
    def test_every_russian_text_has_an_english_pair(self) -> None:
        words = json.loads((SOURCE / "config" / "i18n.json").read_text(encoding="utf-8"))
        missing = sorted({f"{name}: {text}" for name, text in code_texts() if CYRILLIC.search(text) and text not in words})
        self.assertEqual(missing, [])

    def test_every_text_of_the_window_has_a_pair(self) -> None:
        # Source\Tools\check_i18n.py reads every Russian string of the window - a status line, a button made
        # in code, a tooltip of a form - not only the texts handed to Lang.T and Lang.F.
        sys.path.insert(0, str(SOURCE / "Tools"))
        try:
            import check_i18n
        finally:
            sys.path.pop(0)
        self.assertEqual(check_i18n.problems(), [])

    def test_every_pair_has_its_english(self) -> None:
        words = json.loads((SOURCE / "config" / "i18n.json").read_text(encoding="utf-8"))
        empty = sorted(key for key, value in words.items() if not (isinstance(value, dict) and str(value.get("en") or "").strip()))
        self.assertEqual(empty, [])


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    unittest.main(verbosity=1)
