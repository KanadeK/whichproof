"""Deterministic comparison of trusted WhichProof snapshots."""

from __future__ import annotations

from whichproof.models import CommandSnapshot, Comparison, Finding, PlatformInfo, Snapshot


def compare_snapshots(before: Snapshot, after: Snapshot) -> Comparison:
    findings: list[Finding] = []
    if before.platform != after.platform:
        findings.append(
            Finding(
                code="WP106",
                severity="error",
                command=None,
                message="search platform or executable suffix rules changed",
                before=_platform_label(before.platform),
                after=_platform_label(after.platform),
            )
        )

    before_commands = {command.name: command for command in before.commands}
    after_commands = {command.name: command for command in after.commands}
    if tuple(before_commands) != tuple(after_commands):
        findings.append(
            Finding(
                code="WP107",
                severity="error",
                command=None,
                message="snapshot command set or order changed",
                before=", ".join(before_commands),
                after=", ".join(after_commands),
            )
        )

    for name in before_commands.keys() & after_commands.keys():
        findings.extend(
            _compare_command(before_commands[name], after_commands[name], before, after)
        )
    findings.sort(key=_finding_order)
    return Comparison(findings=tuple(findings))


def _compare_command(
    before_command: CommandSnapshot,
    after_command: CommandSnapshot,
    before_snapshot: Snapshot,
    after_snapshot: Snapshot,
) -> list[Finding]:
    name = before_command.name
    before_winner = before_command.candidates[0] if before_command.candidates else None
    after_winner = after_command.candidates[0] if after_command.candidates else None
    if before_winner is not None and after_winner is None:
        return [
            Finding(
                code="WP101",
                severity="error",
                command=name,
                message="command no longer resolves",
                before=before_winner.path,
                after=None,
            )
        ]
    if before_winner is None and after_winner is not None:
        return [
            Finding(
                code="WP102",
                severity="error",
                command=name,
                message="previously missing command now resolves",
                before=None,
                after=after_winner.path,
            )
        ]
    if before_winner is None or after_winner is None:
        return []

    findings: list[Finding] = []
    if before_winner.sha256 != after_winner.sha256:
        findings.append(
            Finding(
                code="WP103",
                severity="error",
                command=name,
                message="selected executable bytes changed",
                before=before_winner.sha256,
                after=after_winner.sha256,
            )
        )
    elif not _same_path(
        before_winner.path,
        after_winner.path,
        before_snapshot.platform,
        after_snapshot.platform,
    ):
        findings.append(
            Finding(
                code="WP104",
                severity="info",
                command=name,
                message="selected executable relocated with identical bytes",
                before=before_winner.path,
                after=after_winner.path,
            )
        )

    before_alternates = _alternate_identities(before_command)
    after_alternates = _alternate_identities(after_command)
    if before_alternates != after_alternates:
        findings.append(
            Finding(
                code="WP105",
                severity="error",
                command=name,
                message="non-winning executable candidates changed",
                before=", ".join(before_alternates),
                after=", ".join(after_alternates),
            )
        )
    return findings


def _alternate_identities(command: CommandSnapshot) -> tuple[str, ...]:
    if not command.candidates:
        return ()
    winner_identity = command.candidates[0].sha256
    identities: list[str] = []
    seen = {winner_identity}
    for candidate in command.candidates[1:]:
        if candidate.sha256 not in seen:
            seen.add(candidate.sha256)
            identities.append(candidate.sha256)
    return tuple(identities)


def _same_path(
    before: str,
    after: str,
    before_platform: PlatformInfo,
    after_platform: PlatformInfo,
) -> bool:
    if before_platform.system == after_platform.system == "Windows":
        return before.casefold() == after.casefold()
    return before == after


def _platform_label(platform_info: PlatformInfo) -> str:
    suffixes = ",".join(platform_info.executable_suffixes)
    return (
        f"{platform_info.system}/{platform_info.machine} "
        f"separator={platform_info.path_separator!r} suffixes=[{suffixes}]"
    )


def _finding_order(finding: Finding) -> tuple[int, str, str]:
    code_order = {
        "WP106": 0,
        "WP107": 1,
        "WP101": 2,
        "WP102": 3,
        "WP103": 4,
        "WP104": 5,
        "WP105": 6,
    }
    return code_order[finding.code], finding.command or "", finding.message
