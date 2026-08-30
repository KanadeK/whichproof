from __future__ import annotations

import json
from collections.abc import Callable
from pathlib import Path

import pytest

from whichproof.models import Candidate, CommandSnapshot, PlatformInfo, Snapshot
from whichproof.snapshot_io import (
    SnapshotFormatError,
    dumps_snapshot,
    read_snapshot,
    write_snapshot,
)


def sample_snapshot() -> Snapshot:
    return Snapshot(
        platform=PlatformInfo(
            system="Windows",
            machine="AMD64",
            path_separator=";",
            executable_suffixes=(".COM", ".EXE"),
        ),
        path_entries=("C:/tools", "C:/Windows/System32"),
        commands=(
            CommandSnapshot(
                name="tool",
                candidates=(
                    Candidate(
                        path="C:/tools/tool.exe",
                        real_path="C:/tools/tool.exe",
                        path_index=0,
                        size=4,
                        sha256="a" * 64,
                    ),
                ),
            ),
            CommandSnapshot(name="missing", candidates=()),
        ),
    )


def test_snapshot_round_trips_deterministically(tmp_path: Path) -> None:
    snapshot = sample_snapshot()
    output = tmp_path / "snapshot.json"

    write_snapshot(output, snapshot)

    assert read_snapshot(output) == snapshot
    assert output.read_text(encoding="utf-8") == dumps_snapshot(snapshot)
    assert output.read_bytes().endswith(b"\n")


def test_write_snapshot_replaces_existing_file(tmp_path: Path) -> None:
    output = tmp_path / "snapshot.json"
    output.write_text("old", encoding="utf-8")

    write_snapshot(output, sample_snapshot())

    assert json.loads(output.read_text(encoding="utf-8"))["schema"] == "whichproof.snapshot.v1"
    assert not list(tmp_path.glob("*.tmp"))


@pytest.mark.parametrize(
    "mutate, message",
    [
        (lambda payload: payload.update(schema="whichproof.snapshot.v2"), "unsupported schema"),
        (lambda payload: payload.update(extra=True), "unexpected field"),
        (lambda payload: payload.update(path_entries="C:/tools"), "path_entries"),
        (lambda payload: payload["commands"][0].update(candidates=None), "candidates"),
        (lambda payload: payload["commands"][0]["candidates"][0].update(size=-1), "size"),
        (lambda payload: payload["commands"][0]["candidates"][0].update(sha256="bad"), "sha256"),
    ],
)
def test_snapshot_rejects_invalid_external_json(
    tmp_path: Path,
    mutate: Callable[[dict[str, object]], None],
    message: str,
) -> None:
    payload = json.loads(dumps_snapshot(sample_snapshot()))
    mutate(payload)
    path = tmp_path / "invalid.json"
    path.write_text(json.dumps(payload), encoding="utf-8")

    with pytest.raises(SnapshotFormatError, match=message):
        read_snapshot(path)


def test_snapshot_rejects_invalid_json(tmp_path: Path) -> None:
    path = tmp_path / "invalid.json"
    path.write_text("{", encoding="utf-8")

    with pytest.raises(SnapshotFormatError, match="valid JSON"):
        read_snapshot(path)
