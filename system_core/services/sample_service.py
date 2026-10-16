from __future__ import annotations

from pathlib import Path
import os
import shutil

from system_core.core.jobs import JobContext


def _is_inside(child: Path, parent: Path) -> bool:
    """True iff `child` (after resolve) is inside `parent` (after resolve).

    Uses os.path.commonpath which is stricter than `parent in child.parents`
    when `child == parent` and works correctly across symlinks because both
    sides are already resolved.
    """
    try:
        child_resolved = str(child.resolve())
        parent_resolved = str(parent.resolve())
    except OSError:
        return False
    try:
        common = os.path.commonpath([child_resolved, parent_resolved])
    except ValueError:
        # Different drives on Windows, etc.
        return False
    return common == parent_resolved


def _clean_managed_folder(context: JobContext, folder: Path, label: str) -> dict[str, object]:
    root = context.paths.root.resolve()
    if folder.is_symlink():
        raise RuntimeError(f"{label} is a symbolic link. Cleanup blocked for safety.")

    folder.mkdir(parents=True, exist_ok=True)
    folder_resolved = folder.resolve()
    if not _is_inside(folder_resolved, root):
        raise RuntimeError(f"{label} path is outside project root. Cleanup blocked.")

    removed = 0
    skipped: list[str] = []
    for item in folder.iterdir():
        if item.name == ".gitkeep":
            continue
        try:
            if item.is_symlink():
                item.unlink()
            elif item.is_dir():
                if not _is_inside(item, folder_resolved):
                    skipped.append(f"{item.name} (escapes {label})")
                    continue
                shutil.rmtree(item)
            else:
                item.unlink()
            removed += 1
            context.log(f"Removed from {label}: {item.name}")
        except OSError as exc:
            skipped.append(f"{item.name} ({exc})")

    return {"folder": label, "removed_items": removed, "skipped_items": skipped}


def cleanup_input_output(context: JobContext) -> dict[str, object]:
    context.log("Cleaning managed input/output folders.")
    input_result = _clean_managed_folder(context, context.paths.input, "input")
    context.progress(0.5)
    if context.cancelled():
        context.log("Input/output cleanup cancelled by user after input cleanup.")
        return {"cancelled": True, "input": input_result}

    output_result = _clean_managed_folder(context, context.paths.output, "output")
    context.progress(1.0)
    total_removed = int(input_result["removed_items"]) + int(output_result["removed_items"])
    total_skipped = len(input_result["skipped_items"]) + len(output_result["skipped_items"])
    context.log(f"Input/output cleanup complete. Removed: {total_removed}, skipped: {total_skipped}")
    return {"input": input_result, "output": output_result, "removed_items": total_removed, "skipped_items": total_skipped}


def cleanup_workspace(context: JobContext) -> dict[str, object]:
    """Delete only files inside the managed workspace folder.

    Safety rules:
    - workspace must resolve to a path inside the project root.
    - Symlinks inside workspace are unlinked, never traversed. shutil.rmtree
      with follow_symlinks=False is not enough on Windows because Path.rmtree
      via shutil treats junctions inconsistently — we handle symlinks first
      and explicitly.
    - Non-symlink subdirectories are checked again before removal: their
      resolved path must still be inside workspace. This catches the case
      where workspace itself contains a directory whose resolve() escapes
      (e.g. a junction or reparse point set up between the outer check and
      iteration).
    """
    workspace = context.paths.workspace
    root = context.paths.root.resolve()

    # Reject workspaces that are themselves symlinks pointing outside root.
    if workspace.is_symlink():
        raise RuntimeError("Workspace is a symbolic link. Cleanup blocked for safety.")

    workspace_resolved = workspace.resolve()
    if not _is_inside(workspace_resolved, root):
        raise RuntimeError("Workspace path is outside project root. Cleanup blocked.")

    workspace.mkdir(parents=True, exist_ok=True)

    removed = 0
    skipped: list[str] = []

    for item in workspace.iterdir():
        if item.name == ".gitkeep":
            continue

        # Symlinks: unlink the link itself, do NOT follow.
        if item.is_symlink():
            try:
                item.unlink()
                removed += 1
                context.log(f"Removed symlink: {item.name}")
            except OSError as exc:
                skipped.append(f"{item.name} (symlink, {exc})")
            continue

        # Re-verify directory containment before recursive delete.
        if item.is_dir():
            if not _is_inside(item, workspace_resolved):
                skipped.append(f"{item.name} (escapes workspace after resolve)")
                context.log(f"Skipped (escapes workspace): {item.name}")
                continue
            shutil.rmtree(item)
            removed += 1
            continue

        # Regular file.
        item.unlink()
        removed += 1

    context.log(f"Workspace cleanup complete. Removed: {removed}, skipped: {len(skipped)}")
    if skipped:
        context.log("Skipped items: " + ", ".join(skipped))
    context.progress(1.0)
    return {"removed_items": removed, "skipped_items": skipped}
