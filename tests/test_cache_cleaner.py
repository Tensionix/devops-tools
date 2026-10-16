"""The cache cleaner clears what its targets name and nothing beside, on a stand of its own.

    runtime\\python.exe tests\\test_cache_cleaner.py

TEMP, LOCALAPPDATA, APPDATA and USERPROFILE point into a scratch folder: the Temp of the stand with
entries old and fresh, the scratch of Claude Code with sessions idle and at work, the media cache of
Adobe. The Windows Temp is only measured here, never cleared: a test run with the rights must not
empty the Temp of the machine.
"""
from __future__ import annotations

import os
import shutil
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from system_core.services.devops_tools import resolve_pwsh  # noqa: E402

SCRIPT = ROOT / "tools" / "cache_cleaner" / "Invoke-CacheCleaner.ps1"
DAY = 24 * 3600


def put(path: Path, size: int = 1024) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(b"x" * size)
    return path


def age(path: Path, seconds: float) -> None:
    """The entry and all under it as written that long ago - the deepest first, as a write would leave them."""
    stamp = time.time() - seconds
    for inner in sorted(path.rglob("*"), key=lambda item: len(item.parts), reverse=True) if path.is_dir() else []:
        os.utime(inner, (stamp, stamp))
    os.utime(path, (stamp, stamp))


class CacheCleanerOnStand(unittest.TestCase):
    def setUp(self) -> None:
        self.stand = Path(tempfile.mkdtemp(prefix="devops_cache_stand_"))
        self.temp = self.stand / "Temp"
        self.local = self.stand / "Local"
        self.roaming = self.stand / "Roaming"
        claude = self.temp / "claude"
        # A project with one session idle two days and one at work now.
        self.idle = claude / "E--TOOLS" / "idle-session"
        put(self.idle / "scratchpad" / "big.bin", 4096)
        age(self.idle, 2 * DAY)
        self.working = claude / "E--TOOLS" / "working-session"
        put(self.working / "scratchpad" / "old.txt")
        age(self.working, 3 * DAY)
        put(self.working / "tasks" / "now.output")
        # A project all of whose sessions sleep: it goes whole.
        self.asleep = claude / "C--Users-Someone"
        put(self.asleep / "session" / "notes.md")
        age(self.asleep, 5 * DAY)
        # The Temp itself: an old leftover and a fresh one.
        self.old_temp = put(self.temp / "old_leftover.tmp")
        age(self.old_temp, 2 * DAY)
        self.fresh_temp = put(self.temp / "fresh.tmp")
        # The media cache of Adobe in its usual place.
        self.media = self.roaming / "Adobe" / "Common" / "Media Cache Files"
        put(self.media / "clip.cfa", 2048)

    def tearDown(self) -> None:
        shutil.rmtree(self.stand, ignore_errors=True)

    def run_cleaner(self, *words: str) -> subprocess.CompletedProcess:
        env = dict(os.environ)
        env.update({"TEMP": str(self.temp), "TMP": str(self.temp), "LOCALAPPDATA": str(self.local),
                    "APPDATA": str(self.roaming), "USERPROFILE": str(self.stand)})
        self.local.mkdir(parents=True, exist_ok=True)
        return subprocess.run([resolve_pwsh(ROOT), "-NoProfile", "-NonInteractive", "-ExecutionPolicy", "Bypass",
                               "-File", str(SCRIPT), *words], env=env, cwd=str(self.stand), capture_output=True,
                              text=True, encoding="utf-8", errors="replace", timeout=180)

    def test_audit_changes_nothing_and_tells_every_target(self) -> None:
        told = self.run_cleaner("-Mode", "Audit")
        self.assertEqual(told.returncode, 0, told.stdout + told.stderr)
        for label in ("Temp older than 24 h", "Windows Temp older than 24 h", "Claude Code sessions idle 24 h", "Adobe Media Cache Files"):
            self.assertIn(label, told.stdout)
        self.assertIn("2 to go", told.stdout)
        for kept in (self.idle, self.working, self.asleep, self.old_temp, self.fresh_temp, self.media / "clip.cfa"):
            self.assertTrue(kept.exists(), kept)

    def test_clean_takes_the_idle_and_leaves_the_working(self) -> None:
        told = self.run_cleaner("-Mode", "Clean", "-Targets", "temp,claude,adobe")
        self.assertEqual(told.returncode, 0, told.stdout + told.stderr)
        self.assertFalse(self.idle.exists())
        self.assertFalse(self.asleep.exists())
        self.assertFalse(self.old_temp.exists())
        self.assertTrue((self.working / "tasks" / "now.output").exists())
        self.assertTrue((self.working / "scratchpad" / "old.txt").exists(), "a session at work keeps all of its files")
        self.assertTrue(self.fresh_temp.exists())
        self.assertTrue((self.temp / "claude").is_dir(), "the scratch folder of Claude Code itself stays")
        self.assertTrue(self.media.is_dir())
        self.assertEqual(list(self.media.iterdir()), [])

    def test_an_unknown_target_is_refused(self) -> None:
        told = self.run_cleaner("-Mode", "Clean", "-Targets", "temp,everything")
        self.assertEqual(told.returncode, 2)
        self.assertTrue(self.old_temp.exists())


if __name__ == "__main__":
    unittest.main(verbosity=1)
