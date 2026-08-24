from __future__ import annotations

from pathlib import Path
import sys

import pytest

from system_core.core.jobs import JobContext, redact_parameters, run_process
from system_core.core.manifest import Operation
from system_core.core.paths import ensure_project_dirs, get_project_paths


def _context(tmp_path: Path) -> JobContext:
    paths = get_project_paths(tmp_path)
    ensure_project_dirs(paths)
    return JobContext(
        paths=paths,
        operation=Operation(
            id="test",
            title="Test",
            description="",
            service="pkg.module:test",
        ),
        log_file=paths.logs / "test.log",
        report_dir=paths.report,
    )


def test_run_process_streams_output(tmp_path: Path) -> None:
    context = _context(tmp_path)

    result = run_process(
        context,
        [sys.executable, "-c", "print('hello from child')"],
    )

    assert result.exit_code == 0
    assert result.lines == ("hello from child",)
    assert "hello from child" in context.log_file.read_text(encoding="utf-8")


def test_run_process_raises_on_nonzero_exit(tmp_path: Path) -> None:
    context = _context(tmp_path)

    with pytest.raises(RuntimeError, match="exit code 7"):
        run_process(context, [sys.executable, "-c", "raise SystemExit(7)"])


def test_redact_parameters_masks_sensitive_values() -> None:
    safe = redact_parameters(
        {
            "linux_username": "audion",
            "linux_password": "secret-pass",
            "nested": {"api_key": "abc123", "plain": "visible"},
        }
    )

    assert safe["linux_username"] == "audion"
    assert safe["linux_password"] == "***REDACTED***"
    assert safe["nested"]["api_key"] == "***REDACTED***"
    assert safe["nested"]["plain"] == "visible"
