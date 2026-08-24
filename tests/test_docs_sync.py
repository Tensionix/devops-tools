from __future__ import annotations

from system_core.docs_sync import sync


def test_manifest_documentation_is_synchronized() -> None:
    assert sync(check=True) == 0
