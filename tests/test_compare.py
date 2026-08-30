from __future__ import annotations

from dataclasses import replace

from whichproof.compare import compare_snapshots
from whichproof.models import Candidate, CommandSnapshot, PlatformInfo, Snapshot


def candidate(path: str, digest: str, path_index: int = 0) -> Candidate:
    return Candidate(
        path=path,
        real_path=path,
        path_index=path_index,
        size=10,
        sha256=digest * 64,
    )


def snapshot(
    commands: tuple[CommandSnapshot, ...],
    *,
    platform_info: PlatformInfo | None = None,
) -> Snapshot:
    return Snapshot(
        platform=platform_info
        or PlatformInfo(
            system="Linux",
            machine="x86_64",
            path_separator=":",
            executable_suffixes=("",),
        ),
        path_entries=("/first", "/second"),
        commands=commands,
    )


def command(name: str, *candidates: Candidate) -> CommandSnapshot:
    return CommandSnapshot(name=name, candidates=candidates)


def finding_codes(before: Snapshot, after: Snapshot) -> list[str]:
    return [finding.code for finding in compare_snapshots(before, after).findings]


def test_identical_snapshots_are_equivalent() -> None:
    before = snapshot((command("tool", candidate("/first/tool", "a")),))

    comparison = compare_snapshots(before, before)

    assert comparison.equivalent
    assert comparison.findings == ()


def test_missing_and_appeared_winners_are_reported() -> None:
    missing = snapshot((command("tool"),))
    present = snapshot((command("tool", candidate("/first/tool", "a")),))

    assert finding_codes(present, missing) == ["WP101"]
    assert finding_codes(missing, present) == ["WP102"]
    assert not compare_snapshots(present, missing).equivalent


def test_changed_winner_bytes_fail_verification() -> None:
    before = snapshot((command("tool", candidate("/first/tool", "a")),))
    after = snapshot((command("tool", candidate("/first/tool", "b")),))

    comparison = compare_snapshots(before, after)

    assert finding_codes(before, after) == ["WP103"]
    assert not comparison.equivalent
    assert comparison.findings[0].severity == "error"


def test_byte_identical_relocation_is_informational() -> None:
    before = snapshot((command("tool", candidate("/old/tool", "a")),))
    after = snapshot((command("tool", candidate("/new/tool", "a")),))

    comparison = compare_snapshots(before, after)

    assert finding_codes(before, after) == ["WP104"]
    assert comparison.equivalent
    assert comparison.findings[0].severity == "info"


def test_alternate_candidate_identity_or_order_drift_fails() -> None:
    winner = candidate("/first/tool", "a")
    before = snapshot((command("tool", winner, candidate("/second/tool", "b", 1)),))
    replaced = snapshot((command("tool", winner, candidate("/second/tool", "c", 1)),))
    reordered = snapshot(
        (
            command(
                "tool",
                winner,
                candidate("/second/c", "c", 1),
                candidate("/second/b", "b", 1),
            ),
        )
    )

    assert finding_codes(before, replaced) == ["WP105"]
    assert finding_codes(before, reordered) == ["WP105"]


def test_duplicate_byte_identical_alternate_is_not_drift() -> None:
    before = snapshot((command("tool", candidate("/first/tool", "a")),))
    after = snapshot(
        (
            command(
                "tool",
                candidate("/moved/tool", "a"),
                candidate("/second/tool", "a", 1),
            ),
        )
    )

    comparison = compare_snapshots(before, after)

    assert finding_codes(before, after) == ["WP104"]
    assert comparison.equivalent


def test_platform_and_command_set_drift_are_reported_first() -> None:
    before = snapshot((command("old"),))
    windows = replace(
        before.platform,
        system="Windows",
        path_separator=";",
        executable_suffixes=(".EXE",),
    )
    after = snapshot((command("new"),), platform_info=windows)

    comparison = compare_snapshots(before, after)

    assert finding_codes(before, after) == ["WP106", "WP107"]
    assert not comparison.equivalent
