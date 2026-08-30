"""Trusted domain models for WhichProof snapshots and findings."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

SNAPSHOT_SCHEMA = "whichproof.snapshot.v1"


@dataclass(frozen=True, slots=True)
class PlatformInfo:
    system: str
    machine: str
    path_separator: str
    executable_suffixes: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class Candidate:
    path: str
    real_path: str
    path_index: int | None
    size: int
    sha256: str


@dataclass(frozen=True, slots=True)
class CommandSnapshot:
    name: str
    candidates: tuple[Candidate, ...]


@dataclass(frozen=True, slots=True)
class Snapshot:
    platform: PlatformInfo
    path_entries: tuple[str, ...]
    commands: tuple[CommandSnapshot, ...]


@dataclass(frozen=True, slots=True)
class Finding:
    code: str
    severity: Literal["error", "info"]
    command: str | None
    message: str
    before: str | None
    after: str | None


@dataclass(frozen=True, slots=True)
class Comparison:
    findings: tuple[Finding, ...]

    @property
    def equivalent(self) -> bool:
        return not any(finding.severity == "error" for finding in self.findings)
