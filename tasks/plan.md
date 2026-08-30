# Implementation plan: WhichProof v0.1.0

## Architecture decisions

- Use Python 3.12+ and the standard library at runtime so the audit tool adds no executable-resolution dependency of its own.
- Treat CLI and snapshot schema as contract-first public interfaces.
- Implement one capture model consumed by both `verify` and `diff`; no duplicate live-compare path.

## Phase 1: contract and capture

- [x] Define typed snapshot model and strict JSON boundary.
- [x] Implement platform-aware ordered candidate capture and hashing.

### Checkpoint

- [x] Focused tests prove missing, explicit-path, duplicate-PATH, POSIX, and Windows suffix cases.

## Phase 2: comparison and CLI

- [x] Implement all seven drift classifications and equivalence policy.
- [x] Add `capture`, `verify`, `diff`, version, output formats, and exit mapping.

### Checkpoint

- [x] End-to-end synthetic shadowing flow exits `0`, then `1` after drift; invalid JSON exits `2`.

## Phase 3: delivery

- [x] Add examples, repair guide, README, contributing/security policy, and changelog.
- [x] Add cross-platform CI, tag release workflow, deterministic package checks, and local gate.
- [x] Review all axes, fix findings, commit exact paths, tag, publish, verify, and notify.

## Risks and mitigations

| Risk | Impact | Mitigation |
| --- | --- | --- |
| Shell-specific behavior is mistaken for filesystem resolution | False claims | Explicitly exclude aliases/functions/built-ins and never load profiles |
| Cross-host absolute paths create false failures | Unusable verification | Decide equivalence primarily by winner bytes; report relocation without failing |
| A candidate changes while hashing | Incorrect evidence | Compare size and stat identity before/after hashing and fail fast on mutation |
| Snapshot paths disclose workstation layout | Privacy surprise | No network, explicit documentation, no file contents or other environment values |
