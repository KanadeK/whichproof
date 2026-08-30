# WhichProof contributor rules

## Product boundary

WhichProof audits filesystem executable resolution. It never executes a discovered command,
loads a shell profile, or claims to resolve shell aliases, functions, or built-ins.

## Stack and commands

- Python 3.12+ with no runtime dependencies.
- Sync: `uv sync --locked`
- Focused tests: `uv run pytest tests/test_<area>.py`
- Full gate: `uv run python scripts/check.py`
- Build: `uv build`

## Conventions

- Validate CLI arguments and snapshot JSON only at their boundaries.
- Keep resolution, comparison, serialization, and CLI orchestration in separate modules.
- JSON output is a public schema. Preserve field meanings and deterministic ordering.
- Exit `0` for an equivalent verification, `1` for observed drift, and `2` for invalid input or runtime failure.
- Do not add a runtime dependency when the standard library is sufficient.
- Stage exact paths; never use `git add .` or `git add -A`.

## Example style

```python
def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()
```

