from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
PDF_ROOT = PROJECT_ROOT / "docs" / "PDF"
DEFAULT_ENGINE_PATH = Path(
    r"E:\TOOLS\Audion Office OCR AI\Audion Office OCR AI\system_core\dev_markdown_pdf_engine.py"
)

ROOT_GUIDES = [
    "README_AUDION_DEVOPS_TOOLS_RU.md",
    "USER_GUIDE_RU.md",
    "USER_GUIDE_EN.md",
]

AGENT_INSTRUCTIONS = [
    "AGENTS.md",
    "CLAUDE.md",
]

THEME_OUTPUTS = {
    "both": ["dark", "light-sand"],
    "dark": ["dark"],
    "light-sand": ["light-sand"],
}


@dataclass(frozen=True)
class RenderGroup:
    label: str
    sources: list[Path]
    out_dir: Path
    base_root: Path


def tools_root() -> Path:
    try:
        return PROJECT_ROOT.parents[1]
    except IndexError:
        return PROJECT_ROOT.parent


def engine_candidates() -> list[Path]:
    env_path = os.environ.get("AUDION_MARKDOWN_PDF_ENGINE", "").strip()
    candidates: list[Path] = []
    if env_path:
        candidates.append(Path(env_path))
    root = tools_root()
    candidates.extend(
        [
            DEFAULT_ENGINE_PATH,
            root / "Audion Office OCR AI" / "Audion Office OCR AI" / "system_core" / "dev_markdown_pdf_engine.py",
            root / "Audion Office OCR AI" / "system_core" / "dev_markdown_pdf_engine.py",
            Path(r"E:\TOOLS\Audion Office OCR AI\Audion Office OCR AI\system_core\dev_markdown_pdf_engine.py"),
            Path(r"E:\TOOLS\Audion Office OCR AI\system_core\dev_markdown_pdf_engine.py"),
            Path(r"S:\TOOLS\Audion Office OCR AI\Audion Office OCR AI\system_core\dev_markdown_pdf_engine.py"),
            Path(r"S:\TOOLS\Audion Office OCR AI\system_core\dev_markdown_pdf_engine.py"),
        ]
    )
    unique: list[Path] = []
    seen: set[str] = set()
    for candidate in candidates:
        key = str(candidate).lower()
        if key not in seen:
            seen.add(key)
            unique.append(candidate)
    return unique


def resolve_engine(explicit: str = "") -> Path:
    candidates = [Path(explicit)] if explicit else engine_candidates()
    for candidate in candidates:
        if candidate.exists():
            return candidate.resolve()
    attempted = "\n".join(f"  - {candidate}" for candidate in candidates)
    raise RuntimeError(
        "Markdown PDF engine was not found. Set AUDION_MARKDOWN_PDF_ENGINE "
        "or pass --engine.\nAttempted:\n" + attempted
    )


def python_for_engine(engine: Path) -> Path:
    office_root = engine.parents[1]
    runtime_python = office_root / "runtime" / "python.exe"
    if runtime_python.exists():
        return runtime_python
    return Path(sys.executable)


def existing_files(relative_paths: list[str]) -> list[Path]:
    files: list[Path] = []
    for rel in relative_paths:
        path = PROJECT_ROOT / rel
        if path.exists() and path.is_file():
            files.append(path.resolve())
    return files


def build_groups(include_agent_instructions: bool) -> list[RenderGroup]:
    groups: list[RenderGroup] = []
    root_sources = existing_files(ROOT_GUIDES)
    if include_agent_instructions:
        root_sources.extend(existing_files(AGENT_INSTRUCTIONS))
    if root_sources:
        groups.append(
            RenderGroup(
                label="root guides",
                sources=root_sources,
                out_dir=PDF_ROOT,
                base_root=PROJECT_ROOT,
            )
        )

    docs_dir = PROJECT_ROOT / "docs"
    if docs_dir.exists():
        groups.append(
            RenderGroup(
                label="docs runbooks",
                sources=[docs_dir.resolve()],
                out_dir=PDF_ROOT,
                base_root=docs_dir.resolve(),
            )
        )

    github_dir = PROJECT_ROOT / "GitHub"
    if github_dir.exists():
        groups.append(
            RenderGroup(
                label="GitHub readmes",
                sources=[github_dir.resolve()],
                out_dir=PDF_ROOT / "GitHub",
                base_root=github_dir.resolve(),
            )
        )

    return groups


def expected_manifest(groups: list[RenderGroup], theme: str) -> list[dict[str, str]]:
    themes = THEME_OUTPUTS[theme]
    items: list[dict[str, str]] = []
    for group in groups:
        expanded: list[Path] = []
        for source in group.sources:
            if source.is_file() and source.suffix.lower() in {".md", ".markdown"}:
                expanded.append(source)
            elif source.is_dir():
                for path in sorted(source.rglob("*"), key=lambda item: str(item).lower()):
                    if path.is_file() and path.suffix.lower() in {".md", ".markdown"}:
                        if PDF_ROOT in path.resolve().parents:
                            continue
                        expanded.append(path.resolve())
        for source in expanded:
            try:
                rel = source.relative_to(group.base_root)
            except ValueError:
                rel = Path(source.name)
            for item_theme in themes:
                output = group.out_dir / rel.parent / f"{source.stem}.{item_theme}.pdf"
                items.append(
                    {
                        "group": group.label,
                        "theme": item_theme,
                        "source": str(source.relative_to(PROJECT_ROOT)),
                        "output": str(output.relative_to(PROJECT_ROOT)),
                    }
                )
    return items


def run_streamed(command: list[str], cwd: Path) -> int:
    process = subprocess.Popen(
        command,
        cwd=str(cwd),
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    assert process.stdout is not None
    for line in process.stdout:
        print(line, end="", flush=True)
    return process.wait()


def run_engine_group(engine: Path, group: RenderGroup, args: argparse.Namespace) -> int:
    python_exe = python_for_engine(engine)
    command = [
        str(python_exe),
        str(engine),
        "--theme",
        args.theme,
        "--output-mode",
        "mirror-output",
        "--out-dir",
        str(group.out_dir),
        "--base-root",
        str(group.base_root),
    ]
    if args.dry_run:
        command.append("--dry-run")
    for source in group.sources:
        command.extend(["--source", str(source)])

    print("----------------------------------------------------------------------")
    print(f"[GROUP] {group.label}")
    print(f"[ENGINE] {engine}")
    print(f"[PYTHON] {python_exe}")
    print(f"[OUT]    {group.out_dir}")
    print()
    return run_streamed(command, cwd=PROJECT_ROOT)


def write_local_manifest(groups: list[RenderGroup], theme: str) -> Path:
    PDF_ROOT.mkdir(parents=True, exist_ok=True)
    manifest_path = PDF_ROOT / "manifest.json"
    payload = {
        "engine": "Audion Office OCR AI dev_markdown_pdf_engine.py",
        "output_root": str(PDF_ROOT.relative_to(PROJECT_ROOT)),
        "items": expected_manifest(groups, theme),
    }
    manifest_path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return manifest_path


def print_dry_run_plan(groups: list[RenderGroup], theme: str, explicit_engine: str) -> None:
    items = expected_manifest(groups, theme)
    print("----------------------------------------------------------------------")
    print("[PLAN] Markdown PDF conversion")
    for item in items:
        print(f"[{item['theme']}] {item['source']} -> {item['output']}")
    print()
    print(f"[PLAN] Sources: {len({item['source'] for item in items})}")
    print(f"[PLAN] PDFs:    {len(items)}")
    try:
        engine = resolve_engine(explicit_engine)
    except RuntimeError:
        print("[INFO] Render engine is not installed; dry-run remains available.")
        print("[INFO] A real export will require --engine or AUDION_MARKDOWN_PDF_ENGINE.")
    else:
        print(f"[PLAN] Engine:  {engine}")


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Render Audion DevOps Tools Markdown guides into docs/PDF.",
    )
    parser.add_argument(
        "--theme",
        choices=sorted(THEME_OUTPUTS),
        default="both",
        help="Theme to render. Default: both.",
    )
    parser.add_argument(
        "--engine",
        default="",
        help="Explicit path to dev_markdown_pdf_engine.py.",
    )
    parser.add_argument(
        "--no-agent-instructions",
        action="store_true",
        help="Skip AGENTS.md and CLAUDE.md.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print conversion plan without writing PDFs.",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(sys.argv[1:] if argv is None else argv)
    groups = build_groups(include_agent_instructions=not args.no_agent_instructions)

    if not groups:
        print("[INFO] No Markdown groups found.")
        return 0

    print("======================================================================")
    print("AUDION DEVOPS TOOLS - DOCS PDF EXPORT")
    print("======================================================================")
    print(f"Project : {PROJECT_ROOT}")
    print(f"PDF root: {PDF_ROOT}")
    print(f"Theme   : {args.theme}")
    print(f"Dry run : {args.dry_run}")
    print()

    if args.dry_run:
        print_dry_run_plan(groups, args.theme, args.engine)
        print("[OK] Docs PDF dry-run finished. Nothing was written.")
        return 0

    try:
        engine = resolve_engine(args.engine)
    except RuntimeError as exc:
        print(f"[ERROR] {exc}")
        return 2

    failures = 0
    for group in groups:
        code = run_engine_group(engine, group, args)
        if code != 0:
            print(f"[ERROR] Group failed with exit code {code}: {group.label}")
            failures += 1
            break

    if failures:
        return 1

    if not args.dry_run:
        manifest = write_local_manifest(groups, args.theme)
        print()
        print(f"[OK] Local PDF manifest: {manifest}")
    print("[OK] Docs PDF export finished.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
