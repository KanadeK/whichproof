"""Build and prove a synthetic PATH-shadowing example."""

from __future__ import annotations

import argparse
import os
from pathlib import Path

from whichproof.cli import main as whichproof_main
from whichproof.resolver import executable_suffixes


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("artifacts/demo"),
        help="new directory for generated evidence (default: artifacts/demo)",
    )
    return parser


def write_executable(path: Path, content: bytes) -> None:
    path.write_bytes(content)
    path.chmod(0o755)


def main() -> int:
    arguments = build_parser().parse_args()
    output_dir = arguments.output_dir.absolute()
    if output_dir.exists():
        raise RuntimeError(f"demo output already exists: {output_dir}")

    first = output_dir / "path-a"
    second = output_dir / "path-b"
    first.mkdir(parents=True)
    second.mkdir()
    suffix = executable_suffixes()[0]
    first_tool = first / f"demo-tool{suffix}"
    second_tool = second / f"demo-tool{suffix}"
    write_executable(first_tool, b"whichproof synthetic winner v1\n")
    write_executable(second_tool, b"whichproof synthetic alternate v1\n")
    path_value = os.pathsep.join((str(first), str(second)))
    baseline = output_dir / "baseline.json"
    current = output_dir / "current.json"

    _require_exit(
        0,
        whichproof_main(["capture", "demo-tool", "--output", str(baseline), "--path", path_value]),
        "baseline capture",
    )
    _require_exit(
        0,
        whichproof_main(["verify", str(baseline), "--path", path_value]),
        "unchanged verification",
    )

    write_executable(second_tool, b"whichproof synthetic alternate v2\n")
    _require_exit(
        0,
        whichproof_main(["capture", "demo-tool", "--output", str(current), "--path", path_value]),
        "current capture",
    )
    _require_exit(
        1,
        whichproof_main(["diff", str(baseline), str(current)]),
        "expected alternate drift",
    )
    print(f"Evidence: {output_dir}")
    print("WHICHPROOF_DEMO=PASS")
    return 0


def _require_exit(expected: int, actual: int, step: str) -> None:
    if actual != expected:
        raise RuntimeError(f"{step} returned {actual}, expected {expected}")


if __name__ == "__main__":
    raise SystemExit(main())
