# Synthetic example data

`scripts/demo.py` creates two PATH directories containing the same command name with different bytes.
It captures both candidates, proves the unchanged snapshot, changes only the non-winning candidate,
and proves that `WP105 CANDIDATES_CHANGED` blocks the comparison.

Run from a checkout:

```bash
uv run python scripts/demo.py
```

The script writes `baseline.json` and `current.json` under `artifacts/demo`. The files contain only
synthetic paths and executable bytes created by the script. Remove that generated directory before
running the demo again.
