"""What the window on Avalonia hands the console command gives every service what the former window gave it.

    runtime\\python.exe tests\\test_window_values.py

The window writes down what it hands the command for every operation with the form untouched
(`AudionDevOpsTools.exe --self-test --values-to <file>`). The command takes those values as it takes
them from the file of `--params`; the model turns them into the parameters of the run, and these are
compared with the untouched form of tests/former_window_parameters.json. The file is the one named by
DEVOPS_WINDOW_VALUES, or the one the window left by the build writes (App, then Source\\bin); with no
window built the test is skipped.
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from system_core.core import bookmarks_form, operation_model as model, smb_logins, window_layout  # noqa: E402
from system_core.core.manifest import load_manifest  # noqa: E402
from tests.test_model_record import ADDED_AFTER_RECORD, PROBE_OPTIONS, RECORD, recorded_defaults, shown  # noqa: E402

WINDOWS = [
    ROOT / "App" / "AudionDevOpsTools.exe",
    ROOT / "Source" / "bin" / "Release" / "net10.0" / "AudionDevOpsTools.exe",
    ROOT / "Source" / "bin" / "Debug" / "net10.0" / "AudionDevOpsTools.exe",
]


def window_values(scratch: Path) -> dict | None:
    named = os.environ.get("DEVOPS_WINDOW_VALUES", "").strip()
    if named:
        return json.loads(Path(named).read_text(encoding="utf-8-sig"))
    window = next((path for path in WINDOWS if path.is_file()), None)
    if window is None:
        return None
    told = scratch / "window_values.json"
    subprocess.run([str(window), "--self-test", "--to", str(scratch / "self_test.txt"), "--values-to", str(told)],
                   cwd=str(ROOT), timeout=300, check=False)
    return json.loads(told.read_text(encoding="utf-8-sig")) if told.is_file() else {}


class WindowAgainstRecord(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.manifest = load_manifest(ROOT / "config" / "tool_manifest.yaml")
        model.options_provider = lambda field: list(PROBE_OPTIONS)
        cls.scratch = Path(tempfile.mkdtemp(prefix="devops_window_"))
        smb_logins.cache_path = cls.scratch / "smb_network_logins.json"
        cls.sent = window_values(cls.scratch)
        if cls.sent is None:
            cls.tearDownClass()
            raise unittest.SkipTest("no window is built: App\\AudionDevOpsTools.exe, Source\\bin")

    @classmethod
    def tearDownClass(cls) -> None:
        model.options_provider = None
        smb_logins.cache_path = None
        shutil.rmtree(cls.scratch, ignore_errors=True)

    def node(self, node_id: str):
        node = model.find_node(self.manifest, node_id)
        self.assertIsNotNone(node, node_id)
        return node

    def test_the_window_tells_of_every_operation_it_shows(self) -> None:
        layout = window_layout.load(ROOT / "config")
        shown_ops = set(window_layout.placed(layout)) | set(window_layout.folder_operations(layout))
        self.assertEqual(sorted(shown_ops - set(self.sent)), [])
        self.assertEqual(sorted(set(self.sent) - shown_ops), [])

    def test_the_command_takes_what_the_window_sends(self) -> None:
        wrong = []
        for node_id, values in self.sent.items():
            node = self.node(node_id)
            unknown = model.unknown_values(node, values)
            if unknown:
                wrong.append(f"{node_id}: no such fields {unknown}")
            choices = model.wrong_choices(node, values, ROOT)
            if choices:
                wrong.append(f"{node_id}: not of the options {choices}")
            if model.refusals(node, values, ROOT) != model.refusals(node, {}, ROOT):
                wrong.append(f"{node_id}: refused otherwise than the untouched form")
        self.assertEqual(wrong, [])

    def built(self, node, values: dict) -> dict:
        try:
            return shown(model.build_parameters(node, values, ROOT / "input", ROOT / "output", ROOT))
        except RuntimeError as error:
            return {"refused": str(error)}

    @staticmethod
    def arrived(node, values: dict) -> dict:
        """The values once the lists the page asks for have come: a group of ticks of a live list that
        names no default of its own ticks the defaults of the list as it arrives (`Form.Offer` of the
        window). The window wrote its values down without asking for a list, so the arrival is the
        made-up list of the record."""
        values = dict(values)
        for field in model.form_fields(node):
            key = model.field_id(field)
            if model.is_checkbox_group(field) and model.option_source(field) and "default" not in field and values.get(key) == []:
                ticked = [option["value"] for option in PROBE_OPTIONS if option.get("default")]
                if ticked:
                    values[key] = ticked
        return values

    def test_parameters_match_the_former_window(self) -> None:
        mismatched = []
        for node_id, values in self.sent.items():
            if node_id in model.CARD_OPERATIONS:
                continue
            node = self.node(node_id)
            got = self.built(node, self.arrived(node, values))
            # The bookmarks were recorded in states of their form, not untouched: the untouched form is the
            # one of the model, itself compared with those states in tests/test_model_record.py. An operation
            # the former window ran directly took the parameters of the manifest alone.
            expected = self.built(node, {}) if node_id in bookmarks_form.OPERATIONS else recorded_defaults(node_id) if node_id in RECORD else None
            if node_id in model.DIRECT_OPERATIONS or node_id in ADDED_AFTER_RECORD:
                expected = shown(dict(node.parameters))
            if got != expected:
                mismatched.append(f"{node_id}: {json.dumps(got, ensure_ascii=False)[:240]} != {json.dumps(expected, ensure_ascii=False)[:240]}")
        self.assertEqual(mismatched, [])


if __name__ == "__main__":
    unittest.main(verbosity=1)
