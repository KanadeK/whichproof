# Research and overlap audit

Research was time-boxed on 2026-08-30 against the local 366-directory workspace inventory and representative public GitHub projects.

## Rejected candidate

A PDF fake-redaction auditor was rejected because Free Law Project already ships [x-ray](https://github.com/freelawproject/x-ray), which detects text covered by rectangle-like redactions. That would be highly similar, not differentiated.

## Closest public tools

| Project or interface | What it does | Why WhichProof is not a clone |
| --- | --- | --- |
| POSIX [`command -v`](https://pubs.opengroup.org/onlinepubs/9799919799.2024edition/utilities/command.html) | Reports what the current shell would invoke now | No candidate-byte manifest, cross-machine comparison, or reusable CI gate |
| Python [`shutil.which`](https://docs.python.org/3/library/shutil.html#shutil.which) | Returns the first executable matching one search | WhichProof records every candidate plus its byte identity and verifies a prior snapshot |
| [`whichcraft`](https://github.com/cookiecutter/whichcraft) | Backports cross-platform `shutil.which` behavior | Compatibility library, not evidence capture or drift analysis |
| [`shimexe`](https://github.com/loonghao/shimexe) | Creates and manages executable shims | Mutates command routing; WhichProof is read-only and audits existing routing |
| `soldr` usage described by [`clud`](https://github.com/zackees/clud/blob/main/docs/DESIGN_DECISIONS.md) | Pins Rust toolchain launchers to avoid PATH shims | Rust-specific launcher policy, not generic command resolution evidence |

Microsoft documents several Windows launch/search mechanisms, and POSIX defines its own PATH search. WhichProof deliberately promises only its documented shell-neutral Python 3.12+ resolution model; it does not merge these mechanisms into a misleading universal resolver. See [CreateProcess search behavior](https://learn.microsoft.com/en-us/windows/win32/api/processthreadsapi/nf-processthreadsapi-createprocessw) and the [POSIX PATH definition](https://pubs.opengroup.org/onlinepubs/7908799/xbd/envvar.html).

## Local overlap check

- `envseismograph` compares broad, user-supplied environment snapshots; it does not discover executable candidates or hash the winner.
- `argvproof` executes a trusted witness through real shells to prove argument quoting; WhichProof never executes the audited command and studies executable selection instead.
- `cmdwitness` compares observable behavior of two explicit command versions; WhichProof determines which file a bare name would select before execution.
- `path-passport` audits filename portability and repair plans; it does not model PATH command resolution.

No local repository or prior-discussion memory entry matched the combination of ordered candidate enumeration, winner byte identity, reusable snapshots, and non-executing cross-environment verification.

