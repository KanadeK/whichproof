# Contributing

Contributions should preserve the narrow v0.1.0 authority boundary: filesystem executable
resolution only, with no candidate execution or shell-profile loading.

```bash
git clone https://github.com/KanadeK/whichproof.git
cd whichproof
uv sync --locked
uv run python scripts/check.py
```

For behavior changes, add a failing test first, update `docs/SPEC.md` before changing a public CLI
or JSON field, and keep one logical concern per commit. Do not lower coverage, skip a failing test,
add a fallback schema reader, or include real workstation snapshots in fixtures.

Bug reports should include the platform, Python version, WhichProof version, command name, and a
minimal synthetic PATH tree. Redact or replace absolute private paths before posting.
