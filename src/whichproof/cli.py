"""WhichProof command-line interface."""

from __future__ import annotations

import argparse
import sys
from collections.abc import Sequence
from pathlib import Path

from whichproof import __version__
from whichproof.compare import compare_snapshots
from whichproof.models import Comparison
from whichproof.report import render_capture, render_comparison_json, render_comparison_text
from whichproof.resolver import ResolutionError, capture_snapshot
from whichproof.snapshot_io import SnapshotFormatError, read_snapshot, write_snapshot


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="whichproof",
        description="Capture and verify the executable files visible through PATH.",
    )
    parser.add_argument("--version", action="store_true", help="show the version and exit")
    subparsers = parser.add_subparsers(dest="subcommand")

    capture = subparsers.add_parser("capture", help="write a command-resolution snapshot")
    capture.add_argument("commands", nargs="+", metavar="COMMAND")
    capture.add_argument("--output", required=True, type=Path, metavar="SNAPSHOT")
    capture.add_argument("--path", dest="path_value", metavar="PATH")

    verify = subparsers.add_parser("verify", help="verify a snapshot against this environment")
    verify.add_argument("snapshot", type=Path)
    verify.add_argument("--path", dest="path_value", metavar="PATH")
    _add_format_argument(verify)

    diff = subparsers.add_parser("diff", help="compare two snapshots")
    diff.add_argument("before", type=Path)
    diff.add_argument("after", type=Path)
    _add_format_argument(diff)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    arguments = parser.parse_args(argv)
    if arguments.version:
        print(f"whichproof {__version__}")
        return 0
    if arguments.subcommand is None:
        parser.error("a subcommand is required")
    try:
        return _run(arguments)
    except (OSError, ResolutionError, SnapshotFormatError) as error:
        print(f"whichproof: error: {error}", file=sys.stderr)
        return 2


def _run(arguments: argparse.Namespace) -> int:
    if arguments.subcommand == "capture":
        snapshot = capture_snapshot(arguments.commands, path_value=arguments.path_value)
        write_snapshot(arguments.output, snapshot)
        sys.stdout.write(render_capture(snapshot, arguments.output))
        return 0
    if arguments.subcommand == "verify":
        before = read_snapshot(arguments.snapshot)
        command_names = tuple(command.name for command in before.commands)
        after = capture_snapshot(command_names, path_value=arguments.path_value)
        return _write_comparison(compare_snapshots(before, after), arguments.format)
    if arguments.subcommand == "diff":
        before = read_snapshot(arguments.before)
        after = read_snapshot(arguments.after)
        return _write_comparison(compare_snapshots(before, after), arguments.format)
    raise AssertionError(f"unexpected subcommand: {arguments.subcommand}")


def _write_comparison(comparison: Comparison, output_format: str) -> int:
    if output_format == "json":
        sys.stdout.write(render_comparison_json(comparison))
    else:
        sys.stdout.write(render_comparison_text(comparison))
    return 0 if comparison.equivalent else 1


def _add_format_argument(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--format",
        choices=("text", "json"),
        default="text",
        help="report format (default: text)",
    )
