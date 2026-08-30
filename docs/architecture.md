# Architecture

WhichProof has one authority path:

```text
CLI input / snapshot JSON
        -> boundary validation
        -> resolver or snapshot model
        -> comparer
        -> deterministic text/JSON rendering
```

- `models.py` owns the snapshot and finding types.
- `resolver.py` owns platform search rules and hashing. It never spawns a process.
- `snapshot_io.py` is the only JSON boundary and performs strict shape validation plus atomic writes.
- `compare.py` owns all drift classifications and the equivalence verdict.
- `cli.py` maps argparse commands to those modules and maps domain outcomes to exit codes.

There is no secondary schema, legacy reader, plugin system, configuration file, or shell adapter in v0.1.0. A snapshot's first candidate is the single authoritative winner.

## Rollback

The release is a standalone CLI with no migrations or persistent service. Roll back by installing the previous tagged wheel. Snapshots remain data files and are never mutated by `verify` or `diff`.

