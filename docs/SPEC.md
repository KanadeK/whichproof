# Spec: WhichProof v0.1.0

## Assumptions

1. The first release audits the filesystem search model used by Python 3.12+ `shutil.which`, not every shell's aliases, functions, built-ins, App Paths, or registry behavior.
2. A snapshot is intentionally local and may expose absolute PATH entries. WhichProof never uploads it.
3. Cross-machine equivalence means the same command resolves to the same file bytes. Absolute relocation alone is reported but does not fail verification.
4. The autonomous delivery request authorizes writing the specification and proceeding without an intermediate approval pause; discoveries that change the public contract must update this file first.

## Objective

Build a local-first CLI for developers and CI maintainers who need evidence for the question:
"Will this bare command launch the same executable here?"

WhichProof captures every executable candidate visible through a supplied PATH, records the selected candidate's byte identity, and later verifies or compares snapshots without executing any candidate.

## Public CLI contract

```text
whichproof capture COMMAND [COMMAND ...] --output SNAPSHOT [--path PATH]
whichproof verify SNAPSHOT [--path PATH] [--format text|json]
whichproof diff BASE CURRENT [--format text|json]
whichproof --version
```

- `capture` writes schema `whichproof.snapshot.v1` as UTF-8 JSON and replaces an existing output atomically.
- `verify` captures the commands named by the baseline under the current or supplied PATH, then compares them.
- `diff` compares two untrusted snapshot files after strict schema validation.
- Human text goes to stdout. Boundary/runtime errors go to stderr.
- Exit `0`: capture succeeded or compared snapshots are equivalent.
- Exit `1`: one or more commands drifted.
- Exit `2`: usage, input, filesystem, hashing, or output failure.

## Snapshot v1 contract

Top level:

- `schema`: exact string `whichproof.snapshot.v1`.
- `platform`: `system`, `machine`, `path_separator`, and ordered `executable_suffixes`.
- `path_entries`: ordered absolute path strings used for resolution.
- `commands`: ordered by the caller's first occurrence.

Each command contains `name` and ordered `candidates`. Each candidate contains:

- `path`: absolute lexical path discovered in the search.
- `real_path`: absolute resolved path.
- `path_index`: zero-based index of the PATH entry that first exposed it, or `null` for an explicit path.
- `size`: file size in bytes.
- `sha256`: lowercase SHA-256 of file bytes.

The first candidate is authoritative. Duplicate commands and duplicate candidate paths are collapsed while preserving first-seen order. Unknown fields are rejected so v1 cannot silently acquire ambiguous meaning.

## Drift rules

- `WP101 MISSING`: a formerly resolved command has no current winner.
- `WP102 APPEARED`: a formerly missing command now resolves.
- `WP103 WINNER_CHANGED`: winner bytes differ. This fails verification.
- `WP104 RELOCATED`: winner bytes match but its path differs. Informational; does not fail.
- `WP105 CANDIDATES_CHANGED`: non-winning candidate byte identities or order differ. This fails because future PATH edits can change the winner.
- `WP106 PLATFORM_CHANGED`: search platform or executable suffix rules differ. This fails.

No report includes file contents, environment variables other than PATH-derived entries and PATHEXT-derived suffixes, or command output.

## Project structure

```text
src/whichproof/       domain models, resolver, comparison, JSON I/O, CLI
tests/                unit and integration tests
examples/             synthetic PATH trees and checked-in evidence
docs/                 specification, architecture, research, repair guide
scripts/check.py      single release-equivalent local gate
.github/workflows/    Windows/Linux CI and tag release build
tasks/                implementation plan and status
```

## Code style

- Typed Python, Ruff formatting, strict mypy.
- Dataclasses carry trusted internal state; JSON parsing constructs them once at the boundary.
- Errors are explicit `WhichProofError` values; no broad catches or silent defaults.

## Testing strategy

- Unit tests: PATH/PATHEXT enumeration, executable filtering, hashing, deduplication, schema rejection, and each drift code.
- Integration tests: all CLI commands, stdout/stderr separation, exit `0/1/2`, atomic output replacement, and a synthetic shadowing scenario.
- CI: Python 3.12 and 3.13 on Ubuntu and Windows.
- Release gate: Ruff, formatting, strict mypy, pytest with at least 90% branch coverage, wheel/sdist build, archive inspection, isolated wheel install, passing demo, failing drift demo, and invalid-input behavior.

## Boundaries

- Always: preserve deterministic ordering; hash bytes without executing them; validate external JSON once; use exact test and packaging commands.
- Ask first: breaking schema/CLI changes after v0.1.0, network features, or execution of discovered commands.
- Never: load shell profiles, execute candidates, upload snapshots, hide drift, include fallback schema readers, or commit secrets/build caches.

## Success criteria

1. A synthetic PATH with two same-name executables captures both in resolution order and selects the first.
2. `verify` passes after relocation of byte-identical winners, but fails on changed winner bytes, missing/appeared commands, candidate-set drift, or platform-rule drift.
3. Malformed or unsupported snapshots fail with exit `2` and no partial output.
4. Full release gate and both CI operating systems pass.
5. Wheel and sdist install cleanly; GitHub has a public `v0.1.0` Release with checksums and an anonymous install/usage verification.
6. The authenticated Gmail account receives the public URL and exact acceptance commands only after remote verification.

## Open questions

None for v0.1.0. Shell-aware resolution and registry/App Paths are explicit non-goals, not deferred compatibility promises.

