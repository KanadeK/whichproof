# WhichProof

> Prove which executable your automation will launch — without launching it.

[简体中文](README.zh-CN.md) · [Specification](docs/SPEC.md) ·
[Repair guide](docs/repair-guide.md) · [Research](docs/research.md)

[![CI](https://github.com/KanadeK/whichproof/actions/workflows/ci.yml/badge.svg)](https://github.com/KanadeK/whichproof/actions/workflows/ci.yml)
[![Python 3.12+](https://img.shields.io/badge/Python-3.12%2B-3776AB)](pyproject.toml)
[![License: MIT](https://img.shields.io/badge/license-MIT-2f6f5e)](LICENSE)

`which` tells you what wins on one machine right now. WhichProof records every executable candidate
visible through PATH, hashes the bytes, and turns that observation into a snapshot another machine
or CI runner can verify.

It does not run `--version`, source a profile, execute a candidate, or upload the snapshot.

## The failure it catches

```text
$ whichproof verify toolchain.json
DRIFT — 1 error(s), 0 info
[ERROR WP103] python: selected executable bytes changed
  before: 6a64...ce31
  after:  0f92...bb18
```

The path can look plausible while a stale shim, package-manager install, virtual environment, or
different CI image puts different bytes first. WhichProof also keeps non-winning candidates visible,
because a later PATH edit can promote one of them.

## Install

Python 3.12 or newer is required. Install the release wheel directly from GitHub:

```bash
python -m pip install "https://github.com/KanadeK/whichproof/releases/download/v0.1.0/whichproof-0.1.0-py3-none-any.whl"
whichproof --version
```

Or install from a clone:

```bash
uv sync --locked
uv run whichproof --version
```

## Capture, commit, verify

Capture the commands your build depends on:

```bash
whichproof capture python git node --output toolchain.json
```

Review and commit `toolchain.json`, then verify it on another workstation or in CI:

```bash
whichproof verify toolchain.json
whichproof verify toolchain.json --format json
```

Compare two existing observations without touching the live environment:

```bash
whichproof diff local.json ci.json
```

Override PATH explicitly when reproducing a runner or service environment:

```powershell
whichproof capture python --output service.json --path 'C:\service\bin;C:\Windows\System32'
```

```bash
whichproof capture python --output service.json --path '/opt/service/bin:/usr/bin'
```

## What the gate means

| Code | Meaning | Fails? |
| --- | --- | --- |
| `WP101` | A previously resolved command is missing | Yes |
| `WP102` | A previously missing command appeared | Yes |
| `WP103` | Selected executable bytes changed | Yes |
| `WP104` | Identical selected bytes moved to a different path | No; reported as information |
| `WP105` | Ordered non-winning byte identities changed | Yes |
| `WP106` | OS, machine, separator, or PATHEXT rules changed | Yes |
| `WP107` | Snapshot command set or order changed | Yes |

Exit codes are stable: `0` means capture succeeded or verification is equivalent, `1` means drift,
and `2` means invalid input or an operational failure. Missing commands do not make `capture` fail;
their absence is the baseline evidence that `verify` protects.

## Real synthetic demo

The demo creates two PATH directories, captures a winner plus an alternate, proves the unchanged
state, mutates only the alternate, and confirms that `WP105` blocks the comparison:

```bash
uv run python scripts/demo.py
```

It leaves reviewable `baseline.json` and `current.json` under `artifacts/demo`.

## Scope and privacy

WhichProof implements a documented filesystem search model for Python 3.12+ PATH/PATHEXT
resolution. It does not claim to resolve shell aliases, functions, built-ins, Windows App Paths,
registry launch policies, or every `CreateProcess`/`ShellExecute` variant. Those are different
authorities and are not silently merged into this one.

Snapshots include absolute PATH entries and executable paths. Treat them as workstation metadata;
review before sharing. File contents are never embedded — only path, resolved path, size, and SHA-256.
There is no network code or telemetry.

## Development and release gate

```bash
uv sync --locked
uv run pytest tests/test_resolver.py
uv run python scripts/check.py
```

The final command runs Ruff, strict mypy, branch coverage at or above 90%, wheel/sdist build,
archive inspection, an isolated wheel install, the passing/drifting demo, and invalid-input behavior.
If it fails, use the [repair guide](docs/repair-guide.md); do not skip a test or lower the gate.

## Why this is a separate tool

The [time-bounded overlap audit](docs/research.md) compares WhichProof with `command -v`,
`shutil.which`, `whichcraft`, shim managers, and the related local projects. The distinguishing
contract is the combination of ordered candidate discovery, byte identity, reusable snapshots,
cross-environment verification, and zero candidate execution.

## License

MIT
