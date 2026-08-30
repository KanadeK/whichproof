"""Human and machine rendering for capture and comparison outcomes."""

from __future__ import annotations

import json
from pathlib import Path

from whichproof.models import Comparison, Finding, Snapshot


def render_capture(snapshot: Snapshot, output: Path) -> str:
    command_word = "command" if len(snapshot.commands) == 1 else "commands"
    lines = [f"CAPTURED {len(snapshot.commands)} {command_word} -> {output}"]
    for command in snapshot.commands:
        if not command.candidates:
            lines.append(f"[MISSING] {command.name}")
            continue
        winner = command.candidates[0]
        lines.append(
            f"[FOUND] {command.name} -> {winner.path} "
            f"sha256={winner.sha256[:12]} candidates={len(command.candidates)}"
        )
    return "\n".join(lines) + "\n"


def render_comparison_text(comparison: Comparison) -> str:
    errors = sum(finding.severity == "error" for finding in comparison.findings)
    infos = sum(finding.severity == "info" for finding in comparison.findings)
    status = "EQUIVALENT" if comparison.equivalent else "DRIFT"
    lines = [f"{status} — {errors} error(s), {infos} info"]
    for finding in comparison.findings:
        command = f" {finding.command}" if finding.command is not None else ""
        lines.append(f"[{finding.severity.upper()} {finding.code}]{command}: {finding.message}")
        lines.append(f"  before: {_display_value(finding.before)}")
        lines.append(f"  after:  {_display_value(finding.after)}")
    return "\n".join(lines) + "\n"


def render_comparison_json(comparison: Comparison) -> str:
    errors = sum(finding.severity == "error" for finding in comparison.findings)
    infos = sum(finding.severity == "info" for finding in comparison.findings)
    payload = {
        "equivalent": comparison.equivalent,
        "summary": {"errors": errors, "info": infos},
        "findings": [_finding_payload(finding) for finding in comparison.findings],
    }
    return json.dumps(payload, ensure_ascii=False, indent=2) + "\n"


def _finding_payload(finding: Finding) -> dict[str, str | None]:
    return {
        "code": finding.code,
        "severity": finding.severity,
        "command": finding.command,
        "message": finding.message,
        "before": finding.before,
        "after": finding.after,
    }


def _display_value(value: str | None) -> str:
    return "<none>" if value is None or value == "" else value
