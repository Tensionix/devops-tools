"""The console command of Audion DevOps Tools.

A button of the window and the command line run the same thing: an operation of the manifest, by the
same runner (`execute_operation`), with the parameters the former window built (`core/operation_model.py`).

  devops_cli.cmd describe
  devops_cli.cmd run --operation dns_status
  devops_cli.cmd run --operation network_wifi_connect --set wifi_profile=Home --set wifi_adapter=Wi-Fi
  devops_cli.cmd check --operation network_standard_repair
  devops_cli.cmd options --operation network_wifi_connect --field wifi_adapter
  devops_cli.cmd state --page link
  devops_cli.cmd smb --forget "PC<TAB>user"
  devops_cli.cmd version

The output of `run`: a plain line is a line of the operation's log; a line that starts with
`::devops::` is a service line and carries JSON - the start, the share of the work done, the one live
line under the log (`activity`), the end. The outcome goes to the file of `--result`. A console gets
the lines in the colours the services write them in; a caller that reads them by a pipe gets the
text without the colour codes, or with them when it asks (`--colours`) - the window does, and paints
them; with `--colours` every process the operation starts is framed by a line of its own.

`describe`, `check`, `options`, `state` and `smb` answer with one line of JSON.

Outcomes and exit codes: `done` 0; `failed` 1; `stopped` 130; a wrong call - 2, and nothing is run.
The gate of the engine (exit code 3 of a script: an edition, a policy, a tool that is missing) is a
failure the log names in its last lines.

Paths: a relative `--source` or `--target` is counted from the project folder; a relative
`--params`, `--result` or `--cancel-file` - from the folder of the caller. The folders of the program
itself (`folders` of the layout: "Clear I/O") always work on `input` and `output` of the program.

Stopping: the caller creates the file of `--cancel-file`. The operation sees it at its next safe point
and stops by itself.

A password is never an argument: the window hands the values of a form in the file of `--params`,
which the window removes after the run, and the log shows such values replaced.
"""
from __future__ import annotations

import argparse
import dataclasses
import json
import os
import sys
import time
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from system_core.core import operation_model as model  # noqa: E402
from system_core.core import smb_logins, window_layout  # noqa: E402
from system_core.core.ansi import strip_ansi  # noqa: E402
from system_core.core.jobs import execute_operation, redact_parameters  # noqa: E402
from system_core.core.manifest import Operation, load_manifest  # noqa: E402
from system_core.core.paths import ensure_project_dirs, get_project_paths  # noqa: E402

CONTROL = "::devops::"
EXIT_OK, EXIT_FAILED, EXIT_USAGE, EXIT_STOPPED = 0, 1, 2, 130
CANCELLED = "Operation cancelled by user."

_nobody_listens = False


def say(line: str) -> None:
    global _nobody_listens
    if _nobody_listens:
        return
    try:
        print(line, flush=True)
    except (OSError, ValueError):
        _nobody_listens = True


def control(payload: dict[str, Any]) -> None:
    say(CONTROL + json.dumps(payload, ensure_ascii=False, default=str))


_colours = False


def tell(line: str) -> None:
    """A line of the operation's log: with its colour codes for a console or a caller that paints them."""
    say(str(line) if _colours or sys.stdout.isatty() else strip_ansi(str(line)))


def usage_error(message: str) -> int:
    try:
        print("[ERR] " + message, file=sys.stderr, flush=True)
    except (OSError, ValueError):
        pass
    return EXIT_USAGE


def project(root: str | None):
    paths = get_project_paths(Path(root).resolve() if root else ROOT)
    manifest = paths.config / "tool_manifest.yaml"
    if not manifest.is_file():
        raise ValueError(f"not a project folder, no manifest: {manifest}")
    try:
        return paths, load_manifest(manifest)
    except Exception as error:  # noqa: BLE001 - whatever the manifest stumbles over, nothing was run
        raise ValueError(f"the manifest does not read: {manifest}: {error}") from error


def project_version(paths) -> str:
    try:
        return str(json.loads((paths.config / "version.json").read_text(encoding="utf-8")).get("version", ""))
    except (OSError, ValueError):
        return ""


def language_of(args: argparse.Namespace, paths) -> str:
    """The language named by the caller; without it - the one chosen in the window, English when none was."""
    if args.language:
        return model.safe_language(args.language)
    try:
        chosen = json.loads((paths.config / "window_settings.json").read_text(encoding="utf-8-sig")).get("Lang", "")
    except (OSError, ValueError, AttributeError):
        chosen = ""
    return model.safe_language(str(chosen))


def command_describe(args: argparse.Namespace) -> int:
    paths, manifest = project(args.root)
    payload = model.describe(manifest)
    payload["version"] = project_version(paths)
    payload["language"] = language_of(args, paths)
    payload["layout"] = window_layout.describe(window_layout.load(paths.config), manifest)
    payload["paths"] = {"root": str(paths.root), "input": str(paths.input), "output": str(paths.output),
                        "backup": str(paths.backup), "logs": str(paths.logs), "report": str(paths.report),
                        "config": str(paths.config), "workspace": str(paths.workspace)}
    say(json.dumps(model.share_forms(payload), ensure_ascii=False, default=str))
    return EXIT_OK


def read_values(args: argparse.Namespace, node) -> dict[str, Any]:
    """The values of the fields: the file of `--params`, over it every `--set name=value`."""
    values: dict[str, Any] = {}
    if args.params:
        loaded = json.loads(Path(args.params).read_text(encoding="utf-8-sig"))
        if not isinstance(loaded, dict):
            raise ValueError("--params: a JSON object \"field name: value\" is expected")
        values.update(loaded)
    fields = {model.field_id(field): field for field in model.form_fields(node) if model.field_id(field)}
    for item in args.set or []:
        name, separator, text = item.partition("=")
        name = name.strip()
        if not separator or not name:
            raise ValueError(f"--set: name=value is expected, got {item!r}")
        if name not in fields:
            raise ValueError(f"--set: the operation has no field {name!r}")
        try:
            values[name] = model.coerce(fields[name], text)
        except ValueError as error:
            raise ValueError(f"--set {name}: {error}") from error
    return values


def write_result(path: str, payload: dict[str, Any]) -> str:
    if not path:
        return ""
    try:
        target = Path(path)
        target.parent.mkdir(parents=True, exist_ok=True)
        draft = target.with_name(target.name + ".tmp")
        draft.write_text(json.dumps(payload, ensure_ascii=False, indent=1, default=str), encoding="utf-8")
        draft.replace(target)
        return ""
    except OSError as error:
        return str(error)


def workbench_path(text: str, fallback: Path, root: Path) -> Path:
    """Source or Target as named by the caller; a relative one is counted from the project folder."""
    if not text:
        return fallback
    cleaned = text.strip().strip('"').strip()
    if '"' in cleaned:
        raise ValueError(f"a quotation mark inside a path - was the path quoted with a backslash at its end? {text!r}")
    path = Path(os.path.expandvars(cleaned)).expanduser()
    return path if path.is_absolute() else root / path


def own_file(text: str) -> str:
    return str(Path(text).expanduser().resolve()) if text else ""


def with_parameters(node, parameters: dict[str, Any]) -> Operation:
    return node.to_operation(parameters) if hasattr(node, "to_operation") else dataclasses.replace(node, parameters=parameters)


def prepared(args: argparse.Namespace):
    """The node, its values and its folders as a run and a check take them; a wrong call raises ValueError."""
    paths, manifest = project(args.root)
    node = model.find_node(manifest, args.operation)
    if node is None:
        raise ValueError(f"the manifest has no operation {args.operation!r}")
    args.params = own_file(args.params)
    values = read_values(args, node)
    layout = window_layout.load(paths.config)
    if args.operation in window_layout.folder_operations(layout):
        # The folders of the program itself: whatever the window shows as SOURCE and TARGET.
        source, target = paths.input, paths.output
    else:
        source = workbench_path(args.source, paths.input, paths.root)
        target = workbench_path(args.target, paths.output, paths.root)
    unknown = model.unknown_values(node, values)
    if unknown:
        raise ValueError("the operation has no fields: " + ", ".join(unknown))
    wrong = model.wrong_choices(node, values, paths.root)
    if wrong:
        raise ValueError("not one of the options of the field: " + ", ".join(wrong))
    refused = model.refusals(node, values, paths.root)
    if refused:
        raise ValueError("; ".join(refused))
    return paths, node, values, source, target


def command_check(args: argparse.Namespace) -> int:
    """Whether the form may run, and the question the window asks first."""
    try:
        paths, node, values, source, target = prepared(args)
        language = language_of(args, paths)
        os.chdir(ROOT)
        parameters = model.build_parameters(node, values, source, target, paths.root, remember=False)
    except (OSError, ValueError, RuntimeError) as error:
        say(json.dumps({"operation": args.operation, "ok": False, "error": str(error)}, ensure_ascii=False))
        return EXIT_OK
    told = {"operation": node.id, "ok": True, "parameters": redact_parameters(parameters)}
    told.update(model.question(node, parameters, language))
    say(json.dumps(told, ensure_ascii=False, default=str))
    return EXIT_OK


def command_run(args: argparse.Namespace) -> int:
    global _colours
    _colours = bool(args.colours)
    args.result, args.cancel_file = own_file(args.result), own_file(args.cancel_file)
    try:
        paths, node, values, source, target = prepared(args)
    except (OSError, ValueError) as error:
        return usage_error(str(error))
    language = language_of(args, paths)
    ensure_project_dirs(paths)
    os.chdir(ROOT)
    try:
        parameters = model.build_parameters(node, values, source, target, paths.root)
    except RuntimeError as error:
        # What the former window refused at the button: no browser ticked, a portable profile without its folder.
        return usage_error(str(error))
    cancel_file = Path(args.cancel_file) if args.cancel_file else None
    operation = with_parameters(node, parameters)
    run_paths = dataclasses.replace(paths, input=source, output=target)

    control({"started": {"operation": operation.id, "source": str(source), "target": str(target)}})
    began = time.monotonic()
    result = execute_operation(run_paths, operation, tell,
                               lambda value: control({"progress": round(float(value), 4)}),
                               (lambda: cancel_file.exists()) if cancel_file is not None else None,
                               (lambda text: control({"activity": strip_ansi(str(text))})) if args.colours else None,
                               language if args.colours else "")
    stopped = (not result.ok) and CANCELLED in result.message and cancel_file is not None and cancel_file.exists()
    outcome = "stopped" if stopped else "done" if result.ok else "failed"
    seconds = round(time.monotonic() - began, 1)
    trouble = write_result(args.result, {"operation": operation.id, "outcome": outcome, "ok": result.ok,
                                         "message": result.message, "data": result.data,
                                         "source": str(source), "target": str(target), "seconds": seconds})
    if trouble:
        say(f"[WARN] The outcome could not be written to {args.result}: {trouble}")
    control({"finished": {"outcome": outcome, "message": result.message, "seconds": seconds}})
    return EXIT_STOPPED if stopped else EXIT_OK if result.ok else EXIT_FAILED


def command_options(args: argparse.Namespace) -> int:
    paths, manifest = project(args.root)
    node = model.find_node(manifest, args.operation, runs=False)
    if node is None:
        return usage_error(f"the manifest has no node {args.operation!r}")
    field = next((item for item in model.form_fields(node) if model.field_id(item) == args.field), None)
    if field is None:
        return usage_error(f"the node {node.id!r} has no field {args.field!r}")
    args.params = own_file(args.params)
    try:
        values = model.form_values(node, read_values(args, node), paths.root)
        values["input_path"] = str(workbench_path(args.source, paths.input, paths.root))
        values["output_path"] = str(workbench_path(args.target, paths.output, paths.root))
    except (OSError, ValueError) as error:
        return usage_error(str(error))
    source = model.option_source(field, node.id)
    if not source:
        options = field.get("options", [])
        listed = model.describe_options(field, options) if isinstance(options, list) else []
        say(json.dumps({"field": args.field, "source": "", "options": listed}, ensure_ascii=False, default=str))
        return EXIT_OK
    os.chdir(ROOT)
    try:
        options = model.resolve_options(source, paths.root, values)
    except Exception as error:  # noqa: BLE001 - the reason is the answer: a window shows it in place of the list
        say(json.dumps({"field": args.field, "source": source, "options": [],
                        "error": f"{error.__class__.__name__}: {error}"}, ensure_ascii=False))
        return EXIT_FAILED
    say(json.dumps({"field": args.field, "source": source, "options": model.describe_options(field, options)},
                   ensure_ascii=False, default=str))
    return EXIT_OK


def command_state(args: argparse.Namespace) -> int:
    """What the machine is in, for the switches of a page: one JSON, nothing in the log."""
    paths, _manifest = project(args.root)
    os.chdir(ROOT)
    from system_core.services import machine_state

    try:
        told = machine_state.page_state(args.page, paths.root)
    except Exception as error:  # noqa: BLE001 - the window shows the reason and lights nothing
        say(json.dumps({"page": args.page, "error": f"{error.__class__.__name__}: {error}"}, ensure_ascii=False))
        return EXIT_FAILED
    say(json.dumps({"page": args.page, **told}, ensure_ascii=False, default=str))
    return EXIT_OK


def command_smb(args: argparse.Namespace) -> int:
    """The remembered SMB pairs: save one, forget one, forget them all."""
    paths, _manifest = project(args.root)
    config = paths.config
    if args.forget:
        done = smb_logins.delete(args.forget, config)
    elif args.clear:
        smb_logins.clear(config)
        done = True
    elif args.save:
        computer, _, user = args.save.partition("|")
        done = bool(smb_logins.upsert(computer, user, config))
    else:
        done = True
    say(json.dumps({"ok": done, "records": smb_logins.records_options(paths.root)}, ensure_ascii=False))
    return EXIT_OK


def command_version(args: argparse.Namespace) -> int:
    paths, _manifest = project(args.root)
    say(project_version(paths))
    return EXIT_OK


def add_workbench_arguments(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--source", default="", help="Source: where the operation reads from; input by default")
    parser.add_argument("--target", default="", help="Target: where exports go; output by default")


def add_form_arguments(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--params", default="", help="A JSON file with the values of the fields by their names")
    parser.add_argument("--set", action="append", metavar="NAME=VALUE", help="The value of one field; may be repeated")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="devops_cli", description="Audion DevOps Tools: the console command.")
    parser.add_argument("--root", default="", help="The project folder, when it is not the one the command lies in")
    parser.add_argument("--language", default="", choices=["", "en", "ru"],
                        help="The language of the interface; by default the one the window was left in")
    commands = parser.add_subparsers(dest="command")

    commands.add_parser("describe", help="The manifest and the layout as JSON").set_defaults(func=command_describe)

    run = commands.add_parser("run", help="Run an operation of the manifest")
    run.add_argument("--operation", required=True, help="The id of the operation")
    add_workbench_arguments(run)
    add_form_arguments(run)
    run.add_argument("--result", default="", help="Where to write the outcome of the operation (JSON)")
    run.add_argument("--cancel-file", default="", help="The stop signal: once the file appears, the operation stops")
    run.add_argument("--colours", action="store_true",
                     help="Leave the colour codes in the lines, frame every process and send the live line: for a caller that paints them")
    run.set_defaults(func=command_run)

    check = commands.add_parser("check", help="Whether a form may run, and the question asked before it")
    check.add_argument("--operation", required=True, help="The id of the operation")
    add_workbench_arguments(check)
    add_form_arguments(check)
    check.set_defaults(func=command_check)

    options = commands.add_parser("options", help="The list of options of one field, asked of its provider")
    options.add_argument("--operation", required=True, help="The id of the node that carries the field")
    options.add_argument("--field", required=True, help="The id of the field")
    add_workbench_arguments(options)
    add_form_arguments(options)
    options.set_defaults(func=command_options)

    state = commands.add_parser("state", help="The state of the machine for the switches of a page")
    state.add_argument("--page", required=True, help="The id of the page of the layout")
    state.set_defaults(func=command_state)

    smb = commands.add_parser("smb", help="The remembered SMB pairs")
    smb.add_argument("--save", default="", metavar="COMPUTER|USER", help="Remember a pair")
    smb.add_argument("--forget", default="", metavar="KEY", help="Forget the pair of this key")
    smb.add_argument("--clear", action="store_true", help="Forget every pair")
    smb.set_defaults(func=command_smb)

    commands.add_parser("version", help="The version number").set_defaults(func=command_version)
    return parser


def main(argv: list[str] | None = None) -> int:
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8")
        except (AttributeError, ValueError):
            pass
    parser = build_parser()
    try:
        args = parser.parse_args(argv)
    except SystemExit as stop:
        return EXIT_USAGE if stop.code not in (0, None) else EXIT_OK
    if not getattr(args, "func", None):
        parser.print_help()
        return EXIT_USAGE
    try:
        return int(args.func(args))
    except (OSError, ValueError) as error:
        return usage_error(f"{error.__class__.__name__}: {error}")


if __name__ == "__main__":
    raise SystemExit(main())
