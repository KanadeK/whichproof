from __future__ import annotations

import hashlib
import os
from pathlib import Path

import pytest

from whichproof import resolver
from whichproof.resolver import (
    ResolutionError,
    capture_snapshot,
    executable_names,
    executable_suffixes,
)


def make_executable(directory: Path, stem: str, content: bytes) -> Path:
    suffix = executable_suffixes()[0]
    path = directory / f"{stem}{suffix}"
    path.write_bytes(content)
    path.chmod(0o755)
    return path


def test_capture_enumerates_shadowed_candidates_in_path_order(tmp_path: Path) -> None:
    first = tmp_path / "first"
    second = tmp_path / "second"
    first.mkdir()
    second.mkdir()
    first_tool = make_executable(first, "demo", b"first")
    second_tool = make_executable(second, "demo", b"second")

    snapshot = capture_snapshot(("demo",), path_value=os.pathsep.join((str(first), str(second))))

    command = snapshot.commands[0]
    assert command.name == "demo"
    assert [candidate.path for candidate in command.candidates] == [
        str(first_tool.absolute()),
        str(second_tool.absolute()),
    ]
    assert [candidate.path_index for candidate in command.candidates] == [0, 1]
    assert command.candidates[0].sha256 == hashlib.sha256(b"first").hexdigest()
    assert command.candidates[0].size == 5


def test_capture_collapses_duplicate_commands_and_path_entries(tmp_path: Path) -> None:
    tools = tmp_path / "tools"
    tools.mkdir()
    make_executable(tools, "demo", b"same")
    path_value = os.pathsep.join((str(tools), str(tools)))

    snapshot = capture_snapshot(("demo", "missing", "demo"), path_value=path_value)

    assert snapshot.path_entries == (str(tools.absolute()),)
    assert [command.name for command in snapshot.commands] == ["demo", "missing"]
    assert snapshot.commands[1].candidates == ()


def test_capture_explicit_path_ignores_search_path(tmp_path: Path) -> None:
    explicit_dir = tmp_path / "explicit"
    shadow_dir = tmp_path / "shadow"
    explicit_dir.mkdir()
    shadow_dir.mkdir()
    explicit = make_executable(explicit_dir, "demo", b"explicit")
    make_executable(shadow_dir, "demo", b"shadow")

    snapshot = capture_snapshot((str(explicit),), path_value=str(shadow_dir))

    assert len(snapshot.commands[0].candidates) == 1
    assert snapshot.commands[0].candidates[0].path == str(explicit.absolute())
    assert snapshot.commands[0].candidates[0].path_index is None


def test_capture_ignores_non_executable_posix_file(tmp_path: Path) -> None:
    tool = tmp_path / "demo"
    tool.write_text("not executable", encoding="utf-8")
    if os.name != "nt":
        tool.chmod(0o644)

    snapshot = capture_snapshot(("demo",), path_value=str(tmp_path))

    assert snapshot.commands[0].candidates == ()


def test_capture_rejects_empty_command() -> None:
    with pytest.raises(ResolutionError, match="must not be empty"):
        capture_snapshot(("",), path_value="")


def test_windows_executable_names_follow_pathext_order() -> None:
    suffixes = (".COM", ".EXE", ".CMD")

    assert executable_names("tool", suffixes) == ("tool.COM", "tool.EXE", "tool.CMD")
    assert executable_names("tool.exe", suffixes) == (
        "tool.exe",
        "tool.exe.COM",
        "tool.exe.EXE",
        "tool.exe.CMD",
    )


def test_posix_executable_names_use_exact_name() -> None:
    assert executable_names("tool", ("",)) == ("tool",)


def test_windows_suffixes_use_default_and_deduplicate_pathext(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    with monkeypatch.context() as context:
        context.setattr(resolver.os, "name", "nt")
        context.setattr(resolver.os, "pathsep", ";")
        context.delenv("PATHEXT", raising=False)
        assert executable_suffixes() == (".COM", ".EXE", ".BAT", ".CMD")

        context.setenv("PATHEXT", ".EXE;.CMD;.exe.")
        assert executable_suffixes() == (".EXE", ".CMD")


def test_windows_implicit_current_directory_is_captured(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class FakePath:
        def __init__(self, value: object) -> None:
            self.value = str(value)

        @classmethod
        def cwd(cls) -> FakePath:
            return cls("C:/cwd")

        def absolute(self) -> FakePath:
            return self

        @property
        def parent(self) -> FakePath:
            return FakePath(self.value.rsplit("/", 1)[0])

        def __str__(self) -> str:
            return self.value

    path_entries = ["C:/tools"]
    with monkeypatch.context() as context:
        context.setattr(resolver.os, "name", "nt")
        context.setattr(resolver, "Path", FakePath)
        context.setattr(resolver, "_absolute_path", lambda path: str(path))
        context.setattr(resolver.shutil, "which", lambda command, path: "C:/cwd/tool")
        resolver._include_implicit_windows_current_directory(
            path_entries,
            ("nested/tool", "tool"),
            "C:/tools",
        )

    assert path_entries == ["C:/cwd", "C:/tools"]


def test_capture_fails_if_executable_changes_while_hashing(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    tools = tmp_path / "tools"
    tools.mkdir()
    executable = make_executable(tools, "demo", b"before")

    def mutate_while_hashing(path: Path) -> str:
        path.write_bytes(b"changed while hashing")
        return hashlib.sha256(b"before").hexdigest()

    monkeypatch.setattr(resolver, "_sha256_file", mutate_while_hashing)

    with pytest.raises(ResolutionError, match="changed while hashing"):
        capture_snapshot(("demo",), path_value=str(tools))

    assert executable.read_bytes() == b"changed while hashing"
