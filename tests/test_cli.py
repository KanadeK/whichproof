from __future__ import annotations

import json
import os
from pathlib import Path

import pytest

from whichproof.cli import main
from whichproof.models import Candidate, CommandSnapshot, PlatformInfo, Snapshot
from whichproof.resolver import executable_suffixes
from whichproof.snapshot_io import write_snapshot


def make_executable(directory: Path, stem: str, content: bytes) -> Path:
    path = directory / f"{stem}{executable_suffixes()[0]}"
    path.write_bytes(content)
    path.chmod(0o755)
    return path


def test_capture_verify_and_changed_winner_exit_codes(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    tools = tmp_path / "tools"
    tools.mkdir()
    executable = make_executable(tools, "demo", b"version one")
    snapshot = tmp_path / "baseline.json"

    assert main(["capture", "demo", "--output", str(snapshot), "--path", str(tools)]) == 0
    captured = capsys.readouterr()
    assert "CAPTURED 1 command" in captured.out
    assert "[FOUND] demo" in captured.out
    assert captured.err == ""

    assert main(["verify", str(snapshot), "--path", str(tools)]) == 0
    verified = capsys.readouterr()
    assert verified.out.startswith("EQUIVALENT")
    assert verified.err == ""

    executable.write_bytes(b"version two")
    assert main(["verify", str(snapshot), "--path", str(tools)]) == 1
    drifted = capsys.readouterr()
    assert drifted.out.startswith("DRIFT")
    assert "[ERROR WP103] demo" in drifted.out
    assert drifted.err == ""


def test_capture_records_missing_command_without_failing(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    snapshot = tmp_path / "missing.json"

    exit_code = main(["capture", "not-present", "--output", str(snapshot), "--path", ""])

    captured = capsys.readouterr()
    assert exit_code == 0
    assert "[MISSING] not-present" in captured.out
    assert json.loads(snapshot.read_text(encoding="utf-8"))["commands"][0]["candidates"] == []


def test_diff_json_reports_structured_candidate_drift(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    platform_info = PlatformInfo("Linux", "x86_64", ":", ("",))
    before = Snapshot(
        platform=platform_info,
        path_entries=("/tools",),
        commands=(CommandSnapshot("tool", (Candidate("/a", "/a", 0, 1, "a" * 64),)),),
    )
    after = Snapshot(
        platform=platform_info,
        path_entries=("/tools",),
        commands=(CommandSnapshot("tool", (Candidate("/b", "/b", 0, 1, "b" * 64),)),),
    )
    before_path = tmp_path / "before.json"
    after_path = tmp_path / "after.json"
    write_snapshot(before_path, before)
    write_snapshot(after_path, after)

    exit_code = main(["diff", str(before_path), str(after_path), "--format", "json"])

    captured = capsys.readouterr()
    payload = json.loads(captured.out)
    assert exit_code == 1
    assert payload["equivalent"] is False
    assert payload["findings"][0]["code"] == "WP103"
    assert captured.err == ""


def test_invalid_snapshot_exits_two_without_stdout(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    invalid = tmp_path / "invalid.json"
    invalid.write_text("{", encoding="utf-8")

    exit_code = main(["verify", str(invalid)])

    captured = capsys.readouterr()
    assert exit_code == 2
    assert captured.out == ""
    assert "whichproof: error:" in captured.err
    assert "valid JSON" in captured.err


def test_capture_output_failure_exits_two_without_partial_file(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    output = tmp_path / "missing-parent" / "snapshot.json"

    exit_code = main(["capture", "demo", "--output", str(output), "--path", os.devnull])

    captured = capsys.readouterr()
    assert exit_code == 2
    assert captured.out == ""
    assert "whichproof: error:" in captured.err
    assert not output.exists()


def test_version_is_available(capsys: pytest.CaptureFixture[str]) -> None:
    assert main(["--version"]) == 0

    captured = capsys.readouterr()
    assert captured.out == "whichproof 0.1.0\n"
    assert captured.err == ""
