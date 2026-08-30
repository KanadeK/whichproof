"""Strict JSON boundary and atomic snapshot persistence."""

from __future__ import annotations

import json
import os
import re
import tempfile
from pathlib import Path
from typing import TypeGuard

from whichproof.models import (
    SNAPSHOT_SCHEMA,
    Candidate,
    CommandSnapshot,
    PlatformInfo,
    Snapshot,
)

SHA256_PATTERN = re.compile(r"[0-9a-f]{64}\Z")


class SnapshotFormatError(ValueError):
    """Raised when external snapshot data violates schema v1."""


def dumps_snapshot(snapshot: Snapshot) -> str:
    payload = {
        "schema": SNAPSHOT_SCHEMA,
        "platform": {
            "system": snapshot.platform.system,
            "machine": snapshot.platform.machine,
            "path_separator": snapshot.platform.path_separator,
            "executable_suffixes": list(snapshot.platform.executable_suffixes),
        },
        "path_entries": list(snapshot.path_entries),
        "commands": [
            {
                "name": command.name,
                "candidates": [
                    {
                        "path": candidate.path,
                        "real_path": candidate.real_path,
                        "path_index": candidate.path_index,
                        "size": candidate.size,
                        "sha256": candidate.sha256,
                    }
                    for candidate in command.candidates
                ],
            }
            for command in snapshot.commands
        ],
    }
    return json.dumps(payload, ensure_ascii=False, indent=2) + "\n"


def write_snapshot(path: Path, snapshot: Snapshot) -> None:
    content = dumps_snapshot(snapshot)
    temporary_path: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            newline="\n",
            dir=path.parent,
            prefix=f".{path.name}.",
            suffix=".tmp",
            delete=False,
        ) as temporary:
            temporary.write(content)
            temporary_path = Path(temporary.name)
        os.replace(temporary_path, path)
        temporary_path = None
    finally:
        if temporary_path is not None:
            temporary_path.unlink(missing_ok=True)


def read_snapshot(path: Path) -> Snapshot:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, UnicodeDecodeError) as error:
        raise SnapshotFormatError(f"{path} is not valid JSON: {error}") from error
    return _parse_snapshot(payload)


def _parse_snapshot(value: object) -> Snapshot:
    payload = _expect_object(
        value,
        "snapshot",
        {"schema", "platform", "path_entries", "commands"},
    )
    schema = _expect_string(payload["schema"], "schema")
    if schema != SNAPSHOT_SCHEMA:
        raise SnapshotFormatError(f"unsupported schema: {schema!r}")

    platform_payload = _expect_object(
        payload["platform"],
        "platform",
        {"system", "machine", "path_separator", "executable_suffixes"},
    )
    suffixes = _expect_string_list(
        platform_payload["executable_suffixes"], "platform.executable_suffixes"
    )
    platform_info = PlatformInfo(
        system=_expect_string(platform_payload["system"], "platform.system"),
        machine=_expect_string(platform_payload["machine"], "platform.machine"),
        path_separator=_expect_string(
            platform_payload["path_separator"], "platform.path_separator"
        ),
        executable_suffixes=suffixes,
    )

    path_entries = _expect_string_list(payload["path_entries"], "path_entries")
    commands_payload = _expect_list(payload["commands"], "commands")
    commands: list[CommandSnapshot] = []
    names: set[str] = set()
    for command_index, command_value in enumerate(commands_payload):
        context = f"commands[{command_index}]"
        command_payload = _expect_object(command_value, context, {"name", "candidates"})
        name = _expect_string(command_payload["name"], f"{context}.name")
        if not name:
            raise SnapshotFormatError(f"{context}.name must not be empty")
        if name in names:
            raise SnapshotFormatError(f"duplicate command name: {name!r}")
        names.add(name)
        candidates_payload = _expect_list(command_payload["candidates"], f"{context}.candidates")
        candidates: list[Candidate] = []
        candidate_paths: set[str] = set()
        for candidate_index, candidate_value in enumerate(candidates_payload):
            candidate_context = f"{context}.candidates[{candidate_index}]"
            candidate_payload = _expect_object(
                candidate_value,
                candidate_context,
                {"path", "real_path", "path_index", "size", "sha256"},
            )
            candidate = _parse_candidate(candidate_payload, candidate_context, len(path_entries))
            if candidate.path in candidate_paths:
                raise SnapshotFormatError(f"duplicate candidate path: {candidate.path!r}")
            candidate_paths.add(candidate.path)
            candidates.append(candidate)
        commands.append(CommandSnapshot(name=name, candidates=tuple(candidates)))

    return Snapshot(
        platform=platform_info,
        path_entries=path_entries,
        commands=tuple(commands),
    )


def _parse_candidate(payload: dict[str, object], context: str, path_count: int) -> Candidate:
    path_index_value = payload["path_index"]
    if path_index_value is None:
        path_index = None
    elif _is_int(path_index_value):
        if not 0 <= path_index_value < path_count:
            raise SnapshotFormatError(f"{context}.path_index is outside path_entries")
        path_index = path_index_value
    else:
        raise SnapshotFormatError(f"{context}.path_index is outside path_entries")
    size_value = payload["size"]
    if not _is_int(size_value):
        raise SnapshotFormatError(f"{context}.size must be a non-negative integer")
    if size_value < 0:
        raise SnapshotFormatError(f"{context}.size must be a non-negative integer")
    sha256 = _expect_string(payload["sha256"], f"{context}.sha256")
    if SHA256_PATTERN.fullmatch(sha256) is None:
        raise SnapshotFormatError(f"{context}.sha256 must be 64 lowercase hex characters")
    return Candidate(
        path=_expect_string(payload["path"], f"{context}.path"),
        real_path=_expect_string(payload["real_path"], f"{context}.real_path"),
        path_index=path_index,
        size=size_value,
        sha256=sha256,
    )


def _expect_object(value: object, context: str, fields: set[str]) -> dict[str, object]:
    if not isinstance(value, dict) or not all(isinstance(key, str) for key in value):
        raise SnapshotFormatError(f"{context} must be an object")
    actual_fields = set(value)
    if actual_fields != fields:
        unexpected = sorted(actual_fields - fields)
        missing = sorted(fields - actual_fields)
        if unexpected:
            raise SnapshotFormatError(f"{context} has unexpected field: {unexpected[0]}")
        raise SnapshotFormatError(f"{context} is missing field: {missing[0]}")
    return value


def _expect_list(value: object, context: str) -> list[object]:
    if not isinstance(value, list):
        raise SnapshotFormatError(f"{context} must be an array")
    return value


def _expect_string(value: object, context: str) -> str:
    if not isinstance(value, str):
        raise SnapshotFormatError(f"{context} must be a string")
    return value


def _expect_string_list(value: object, context: str) -> tuple[str, ...]:
    values = _expect_list(value, context)
    strings: list[str] = []
    for index, item in enumerate(values):
        strings.append(_expect_string(item, f"{context}[{index}]"))
    return tuple(strings)


def _is_int(value: object) -> TypeGuard[int]:
    return isinstance(value, int) and not isinstance(value, bool)
