"""Read-only executable candidate discovery and byte identity capture."""

from __future__ import annotations

import hashlib
import os
import platform
import shutil
from collections.abc import Iterable, Sequence
from pathlib import Path

from whichproof.models import Candidate, CommandSnapshot, PlatformInfo, Snapshot

WINDOWS_DEFAULT_PATHEXT = (".COM", ".EXE", ".BAT", ".CMD")
HASH_CHUNK_SIZE = 1024 * 1024


class ResolutionError(RuntimeError):
    """Raised when a candidate cannot be captured consistently."""


def executable_suffixes() -> tuple[str, ...]:
    if os.name != "nt":
        return ("",)
    source = os.environ.get("PATHEXT")
    raw_suffixes = source.split(os.pathsep) if source else list(WINDOWS_DEFAULT_PATHEXT)
    suffixes = (suffix.rstrip(".") for suffix in raw_suffixes if suffix)
    return _unique_strings(suffixes, case_insensitive=True)


def executable_names(command: str, suffixes: tuple[str, ...]) -> tuple[str, ...]:
    if suffixes == ("",):
        return (command,)
    names = [f"{command}{suffix}" for suffix in suffixes]
    if any(command.upper().endswith(suffix.upper()) for suffix in suffixes):
        names.insert(0, command)
    return _unique_strings(names, case_insensitive=True)


def capture_snapshot(
    commands: Sequence[str],
    *,
    path_value: str | None = None,
) -> Snapshot:
    command_names = _unique_commands(commands)
    effective_path = os.environ.get("PATH", "") if path_value is None else path_value
    suffixes = executable_suffixes()
    path_entries = list(_path_entries(effective_path))
    _include_implicit_windows_current_directory(
        path_entries,
        command_names,
        effective_path,
    )
    command_snapshots = tuple(
        _capture_command(command, tuple(path_entries), suffixes) for command in command_names
    )
    return Snapshot(
        platform=PlatformInfo(
            system=platform.system(),
            machine=platform.machine(),
            path_separator=os.pathsep,
            executable_suffixes=suffixes,
        ),
        path_entries=tuple(path_entries),
        commands=command_snapshots,
    )


def _unique_commands(commands: Sequence[str]) -> tuple[str, ...]:
    unique: list[str] = []
    seen: set[str] = set()
    for command in commands:
        if not command:
            raise ResolutionError("command names must not be empty")
        if command not in seen:
            seen.add(command)
            unique.append(command)
    if not unique:
        raise ResolutionError("at least one command is required")
    return tuple(unique)


def _path_entries(path_value: str) -> tuple[str, ...]:
    if not path_value:
        return ()
    current_directory = Path.cwd()
    entries = (
        _absolute_path(current_directory if not raw_entry else Path(raw_entry))
        for raw_entry in path_value.split(os.pathsep)
    )
    return _unique_paths(entries)


def _include_implicit_windows_current_directory(
    path_entries: list[str],
    commands: tuple[str, ...],
    path_value: str,
) -> None:
    if os.name != "nt" or not path_value:
        return
    current_directory = _absolute_path(Path.cwd())
    current_key = os.path.normcase(current_directory)
    if any(os.path.normcase(entry) == current_key for entry in path_entries):
        return
    for command in commands:
        directory, _ = os.path.split(command)
        if directory:
            continue
        winner = shutil.which(command, path=path_value)
        if (
            winner is not None
            and os.path.normcase(str(Path(winner).absolute().parent)) == current_key
        ):
            path_entries.insert(0, current_directory)
            return


def _capture_command(
    command: str,
    path_entries: tuple[str, ...],
    suffixes: tuple[str, ...],
) -> CommandSnapshot:
    directory, basename = os.path.split(command)
    if directory:
        explicit_directory = _absolute_path(Path(directory))
        candidates = _candidates_in_directory(explicit_directory, basename, suffixes, None)
    else:
        captured: list[Candidate] = []
        for path_index, path_entry in enumerate(path_entries):
            captured.extend(_candidates_in_directory(path_entry, basename, suffixes, path_index))
        candidates = _unique_candidates(captured)
    return CommandSnapshot(name=command, candidates=tuple(candidates))


def _candidates_in_directory(
    directory: str,
    command: str,
    suffixes: tuple[str, ...],
    path_index: int | None,
) -> list[Candidate]:
    candidates: list[Candidate] = []
    for executable_name in executable_names(command, suffixes):
        candidate_path = Path(directory) / executable_name
        if _is_executable_file(candidate_path):
            candidates.append(_capture_candidate(candidate_path, path_index))
    return candidates


def _is_executable_file(path: Path) -> bool:
    return path.is_file() and os.access(path, os.F_OK | os.X_OK)


def _capture_candidate(path: Path, path_index: int | None) -> Candidate:
    absolute_path = Path(_absolute_path(path))
    try:
        before = absolute_path.stat()
        sha256 = _sha256_file(absolute_path)
        after = absolute_path.stat()
        real_path = absolute_path.resolve(strict=True)
    except OSError as error:
        raise ResolutionError(f"cannot capture executable {absolute_path}: {error}") from error
    before_identity = (before.st_dev, before.st_ino, before.st_size, before.st_mtime_ns)
    after_identity = (after.st_dev, after.st_ino, after.st_size, after.st_mtime_ns)
    if before_identity != after_identity:
        raise ResolutionError(f"executable changed while hashing: {absolute_path}")
    return Candidate(
        path=str(absolute_path),
        real_path=str(real_path),
        path_index=path_index,
        size=after.st_size,
        sha256=sha256,
    )


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(HASH_CHUNK_SIZE), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _absolute_path(path: Path) -> str:
    return os.path.abspath(os.fspath(path))


def _unique_paths(paths: Iterable[str]) -> tuple[str, ...]:
    unique: list[str] = []
    seen: set[str] = set()
    for path in paths:
        key = os.path.normcase(path)
        if key not in seen:
            seen.add(key)
            unique.append(path)
    return tuple(unique)


def _unique_candidates(candidates: Iterable[Candidate]) -> list[Candidate]:
    unique: list[Candidate] = []
    seen: set[str] = set()
    for candidate in candidates:
        key = os.path.normcase(candidate.path)
        if key not in seen:
            seen.add(key)
            unique.append(candidate)
    return unique


def _unique_strings(values: Iterable[str], *, case_insensitive: bool) -> tuple[str, ...]:
    unique: list[str] = []
    seen: set[str] = set()
    for value in values:
        key = value.casefold() if case_insensitive else value
        if key not in seen:
            seen.add(key)
            unique.append(value)
    return tuple(unique)
