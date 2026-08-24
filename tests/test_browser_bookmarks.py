from __future__ import annotations

from pathlib import Path

from system_core.services.devops_tools import chromium_bookmarks_and_icons_from_html, chromium_bookmarks_from_html


def test_chromium_bookmarks_from_html_preserves_folders_and_urls(tmp_path: Path) -> None:
    source = tmp_path / "bookmarks.html"
    source.write_text(
        """<!DOCTYPE NETSCAPE-Bookmark-file-1>
<DL><p><DT><H3 ADD_DATE="1700000000">Work</H3>
<DL><p><DT><A HREF="https://example.com" ADD_DATE="1700000001">Example</A></DL><p></DL><p>
""",
        encoding="utf-8",
    )

    payload = chromium_bookmarks_from_html(source)

    folder = payload["roots"]["bookmark_bar"]["children"][0]
    assert folder["name"] == "Work"
    assert folder["children"][0]["url"] == "https://example.com"
    assert payload["checksum"]
    assert payload["version"] == 1


def test_html_embedded_icon_is_extracted_without_leaking_into_bookmarks(tmp_path: Path) -> None:
    source = tmp_path / "bookmarks.html"
    source.write_text(
        '<DL><p><DT><H3>Bookmarks bar</H3><DL><p><DT><A HREF="https://example.com/" '
        'ICON="data:image/png;base64,iVBORw0KGgo=">Example</A></DL><p></DL><p>',
        encoding="utf-8",
    )

    payload, icons = chromium_bookmarks_and_icons_from_html(source)
    node = payload["roots"]["bookmark_bar"]["children"][0]

    assert node["url"] == "https://example.com/"
    assert "_audion_icon" not in node
    assert icons["https://example.com/"].startswith(b"\x89PNG")
