"""Command-line entrypoint for ds-cheatsheet."""

from __future__ import annotations

import argparse
import sys

from . import __version__
from .explain import explain
from .loader import CheatSheetLoadError, load_all


def _cmd_tui(_: argparse.Namespace) -> int:
    from .tui.app import CheatSheetApp  # local import: avoid TUI deps for --help

    app = CheatSheetApp()
    app.run()
    return 0


def _cmd_validate(_: argparse.Namespace) -> int:
    try:
        entries = load_all()
    except CheatSheetLoadError as exc:
        print(f"Validation failed: {exc}", file=sys.stderr)
        return 1
    print(f"OK — loaded {len(entries)} commands.")
    return 0


def _cmd_explain(args: argparse.Namespace) -> int:
    command = " ".join(args.command).strip()
    if not command:
        print("Provide a command to explain.", file=sys.stderr)
        return 2

    result = explain(command)
    print(f"Command: {result.command}\n")
    for token in result.tokens:
        print(f"  [{token.kind:>8}] {token.value!s:<24} {token.description}")

    if result.dangerous:
        print("\n!! Dangerous patterns detected:")
        for reason in result.danger_reasons:
            print(f"   - {reason}")

    for note in result.notes:
        print(f"\nNote: {note}")
    return 0


def _cmd_list(args: argparse.Namespace) -> int:
    try:
        entries = load_all()
    except CheatSheetLoadError as exc:
        print(f"Load failed: {exc}", file=sys.stderr)
        return 1

    if args.category:
        entries = [e for e in entries if e.category == args.category]

    for entry in entries:
        flag = " (!) " if entry.dangerous else "     "
        print(f"{flag}[{entry.category:<18}] {entry.title}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="ds-cheatsheet",
        description="Interactive cheat sheet of Linux commands for data scientists.",
    )
    parser.add_argument("--version", action="version", version=f"ds-cheatsheet {__version__}")

    subparsers = parser.add_subparsers(dest="cmd")

    tui = subparsers.add_parser("tui", help="Launch the interactive TUI (default).")
    tui.set_defaults(func=_cmd_tui)

    validate = subparsers.add_parser("validate", help="Validate bundled YAML files.")
    validate.set_defaults(func=_cmd_validate)

    explain_p = subparsers.add_parser("explain", help="Explain a shell command locally.")
    explain_p.add_argument("command", nargs=argparse.REMAINDER)
    explain_p.set_defaults(func=_cmd_explain)

    list_p = subparsers.add_parser("list", help="List loaded commands.")
    list_p.add_argument("--category", help="Filter by category name.")
    list_p.set_defaults(func=_cmd_list)

    parser.set_defaults(func=_cmd_tui)
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
