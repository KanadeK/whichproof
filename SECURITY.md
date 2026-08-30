# Security policy

## Supported version

Security fixes are provided for the latest tagged release.

## Reporting

Do not open a public issue for a vulnerability that could expose local paths or executable data.
Use GitHub's private security advisory flow for `KanadeK/whichproof`.

## Trust boundary

- WhichProof reads executable metadata and bytes for SHA-256; it never executes candidates.
- Snapshot JSON is untrusted input and is strictly validated before comparison.
- Snapshot output contains absolute PATH entries and file paths. It may be sensitive even though it
  contains no file bytes, environment values beyond PATH/PATHEXT-derived data, or command output.
- WhichProof has no runtime dependency, network request, telemetry, privilege elevation, PATH
  mutation, or automatic repair.

Do not run WhichProof against files you are not authorized to read. A passing comparison proves
the documented byte-identity contract only; it is not a malware or code-signing verdict.
