"""The model of the console command gives every service what the former window gave it.

    runtime\\python.exe tests\\test_model_record.py

Compared with tests/former_window_parameters.json, the record made of the window on NiceGUI before
it goes: for every operation, both languages, with the form untouched and with every field changed;
for the bookmarks, in the seven states of their form. Live lists are the same made-up list the record
used, and the SMB logins go to a file of their own.
"""
from __future__ import annotations

import json
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from system_core.core import bookmarks_form, operation_model as model, smb_logins  # noqa: E402
from system_core.core.manifest import load_manifest  # noqa: E402

RECORD = json.loads((ROOT / "tests" / "former_window_parameters.json").read_text(encoding="utf-8"))
# Operations the window gained after the former window was recorded: no form, the parameters of the manifest alone.
ADDED_AFTER_RECORD = {"cache_cleaner_temp", "cache_cleaner_adobe", "ai_backup_inventory"}
WINDOW_AI_V3 = {"ai_backup_export", "ai_backup_import"}
FORMS_ADDED_AFTER_RECORD = {"ai_backup_rollback"}
# Operations of the former window that are gone since: the export of the documentation into PDF, which ran the
# engine of Audion Office OCR AI beside the project (the owner, 15.10.2026: "remove the dependency and the PDF").
# And the installer of the portable PowerShell: the program has its own, App\AudionPs.exe, since 2.0.0.
REMOVED_AFTER_RECORD = {"docs_pdf_plan", "docs_pdf_render", "docs_pdf_open", "install_portable_powershell"}
# Defaults changed on purpose after the record, field by field: the untouched form gives these instead.
# Everything that takes the pictures, the music and the videos is ticked (the owner, 15.10.2026: "everything
# that takes them over must be ticked ... the rest left unticked, but left as a way to remove it").
# The page of Hosts and Bitrix names no portal of its own: the name and the address are the person's. The portal of
# the record, its address and the pin "Bitrix default" that filled them are gone (the owner, 16.10.2026).
NO_PORTAL = {"host_name": "", "ip_address": ""}
CHANGED_AFTER_RECORD = {
    "default_apps_microsoft": {"apps": ["Photos", "ZuneMusic", "ZuneVideo", "MediaPlayerLegacy", "Paint", "ScreenSketch"]},
    **{node_id: NO_PORTAL for node_id in ("bitrix_detect_endpoint", "bitrix_status", "bitrix_enable", "bitrix_disable", "bitrix_restore")},
}


def recorded_defaults(node_id: str, language: str = "en") -> dict:
    """The untouched form of the record, with the defaults changed since then put in."""
    return {**RECORD[node_id][language]["defaults"], **CHANGED_AFTER_RECORD.get(node_id, {})}


PROBE_OPTIONS = [
    {"value": "probe-a", "label": "Probe A", "label_ru": "Проба А", "default": True},
    {"value": "probe-b", "label": "Probe B", "label_ru": "Проба Б"},
]


def shown(parameters: dict) -> dict:
    text = json.dumps(parameters, ensure_ascii=False, sort_keys=True, default=str)
    return json.loads(text.replace(json.dumps(str(ROOT))[1:-1], "<root>"))


class ModelAgainstRecord(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.manifest = load_manifest(ROOT / "config" / "tool_manifest.yaml")
        model.options_provider = lambda field: list(PROBE_OPTIONS)
        cls.scratch = Path(tempfile.mkdtemp(prefix="devops_model_"))
        smb_logins.cache_path = cls.scratch / "smb_network_logins.json"

    @classmethod
    def tearDownClass(cls) -> None:
        model.options_provider = None
        smb_logins.cache_path = None
        shutil.rmtree(cls.scratch, ignore_errors=True)

    def build(self, node_id: str, values: dict) -> dict:
        node = model.find_node(self.manifest, node_id)
        self.assertIsNotNone(node, node_id)
        return shown(model.build_parameters(node, values, ROOT / "input", ROOT / "output", ROOT))

    def test_every_operation_is_recorded(self) -> None:
        runs = {node.id for node in model.all_nodes(self.manifest) if node.service} - set(model.CARD_OPERATIONS) - ADDED_AFTER_RECORD - FORMS_ADDED_AFTER_RECORD
        recorded = set(RECORD) - {"__bookmarks__"} - REMOVED_AFTER_RECORD
        self.assertEqual(sorted(runs - recorded), [])
        self.assertEqual(sorted(recorded - runs), [])

    def test_parameters_match_the_former_window(self) -> None:
        mismatched = []
        for node_id, entry in RECORD.items():
            if node_id == "__bookmarks__" or node_id in bookmarks_form.OPERATIONS or node_id in model.DIRECT_OPERATIONS or node_id in REMOVED_AFTER_RECORD:
                continue
            for language in ("en", "ru"):
                told = entry[language]
                if self.build(node_id, {}) != recorded_defaults(node_id, language):
                    mismatched.append(f"{node_id} {language} defaults")
                if self.build(node_id, told["values"]) != told["changed"]:
                    mismatched.append(f"{node_id} {language} changed")
        self.assertEqual(mismatched, [])

    def test_direct_operations_take_the_manifest_alone(self) -> None:
        for node_id in sorted(model.DIRECT_OPERATIONS | ADDED_AFTER_RECORD):
            node = model.find_node(self.manifest, node_id)
            self.assertEqual(self.build(node_id, {}), shown(dict(node.parameters)))

    def test_bookmarks_match_the_former_window(self) -> None:
        told = RECORD["__bookmarks__"]
        mismatched = []
        for node_id, states in told["operations"].items():
            for name, expected in states.items():
                story = told["states"][name]
                if node_id == bookmarks_form.TRANSFER and story["single"] in story["selected"]:
                    # The form of the former window took the source out of the targets as it was drawn
                    # (`normalize_browser_bookmarks_state`); the record handed them over as they were, so its
                    # refusal here is one the window never met. The model takes the source out - checked below.
                    continue
                values = {"bookmark_browsers": story["selected"], "bookmark_source": story["single"],
                          "bookmark_location": story["location"], "bookmark_rollback": story.get("rollback", True)}
                if story.get("profile_path"):
                    values["browser_profile_path"] = story["profile_path"]
                if node_id == bookmarks_form.IMPORT:
                    values["bookmark_import_kind"] = story.get("import_kind", "html")
                    values["bookmark_backup_path"] = story.get("backup_path", "")
                    values["bookmark_html_path"] = story.get("html_path", "")
                try:
                    got = {"parameters": self.build(node_id, values)}
                except RuntimeError as error:
                    got = {"refused": f"{error.__class__.__name__}: {error}"}
                if got != expected:
                    mismatched.append(f"{node_id} {name}: {json.dumps(got, ensure_ascii=False)[:300]} != {json.dumps(expected, ensure_ascii=False)[:300]}")
        self.assertEqual(mismatched, [])

    def test_transfer_takes_the_source_out_of_the_targets(self) -> None:
        told = self.build(bookmarks_form.TRANSFER, {"bookmark_browsers": ["chrome", "edge"], "bookmark_source": "chrome"})
        self.assertEqual(told["source_browser_profile"], "chrome")
        self.assertEqual(told["target_browser_profiles"], ["edge"])
        with self.assertRaises(RuntimeError):
            self.build(bookmarks_form.TRANSFER, {"bookmark_browsers": ["chrome"], "bookmark_source": "chrome"})


if __name__ == "__main__":
    unittest.main(verbosity=1)
