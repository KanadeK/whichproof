# Repair guide

WhichProof reports observation drift; it does not rewrite PATH or install tools. Fix the owning
environment, capture a new snapshot only after reviewing the intended change, and keep the old
snapshot in version history.

| Code | Investigate | Typical repair |
| --- | --- | --- |
| `WP101` | PATH entry removed, tool uninstalled, activation step skipped | Restore the required install/activation or update the build to an explicit executable path |
| `WP102` | New global tool, virtual environment, shim, or current-directory candidate | Remove the unintended candidate or review and capture the newly required tool |
| `WP103` | Package-manager upgrade, stale shim target, replaced runner image | Verify the file origin and intended version, then either restore it or approve a reviewed snapshot update |
| `WP104` | Same bytes installed elsewhere | Usually no repair; review path disclosure and deployment conventions |
| `WP105` | A shadow candidate was added, removed, or reordered | Remove stale duplicates or make PATH ordering explicit before they become the winner |
| `WP106` | Different OS/architecture/PATHEXT policy | Keep separate reviewed baselines for genuinely different runner classes |
| `WP107` | Baselines were generated for different command portfolios | Regenerate from the agreed command list; do not merge unrelated snapshots |

## Operational failures

- `whichproof: error: ... is not valid JSON`: restore the committed snapshot or recapture it. Do not hand-edit hashes.
- `executable changed while hashing`: stop the installer/build that is replacing the file, then retry. The partial observation is rejected.
- `Permission denied` while hashing: run under the same account as the automation or grant read access to that executable; WhichProof does not elevate.
- Output parent missing: create the intended parent explicitly, then rerun. WhichProof does not guess directories.
- `uv` cache error on Windows: use a repository-local cache, for example `uv --cache-dir .uv-cache sync --locked`.
- PyPI/OSV network failure: keep the local functional gate; run `uv audit --locked` in network-enabled CI rather than silently marking the audit passed.

## Deliberate contract changes

When a tool upgrade is intended:

1. Capture a candidate snapshot to a new file.
2. Run `whichproof diff committed.json candidate.json`.
3. Confirm the exact command and hash changes against the package-manager or runner-image change.
4. Replace the committed snapshot in the same reviewed change that upgrades the tool.
5. Let CI run `whichproof verify` on the new baseline.
