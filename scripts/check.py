"""One release-equivalent local gate for WhichProof."""

from __future__ import annotations

import hashlib
import os
import subprocess
import sys
import tarfile
import tempfile
import venv
import zipfile
from collections.abc import Sequence
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DIST = ROOT / "dist"
TEMP_ROOT = ROOT / ".tmp"


def run(
    args: Sequence[str],
    *,
    cwd: Path = ROOT,
    check: bool = True,
    capture: bool = False,
) -> subprocess.CompletedProcess[str]:
    print(f"+ {subprocess.list2cmdline(args)}")
    return subprocess.run(
        args,
        cwd=cwd,
        check=check,
        capture_output=capture,
        text=True,
    )


def require(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def inspect_archives(wheel: Path, sdist: Path) -> None:
    with zipfile.ZipFile(wheel) as archive:
        wheel_names = set(archive.namelist())
    required_wheel_files = {
        "whichproof/cli.py",
        "whichproof/compare.py",
        "whichproof/resolver.py",
        "whichproof/snapshot_io.py",
    }
    require(required_wheel_files <= wheel_names, "wheel is missing runtime modules")

    with tarfile.open(sdist, "r:gz") as archive:
        source_names = {Path(name).as_posix() for name in archive.getnames()}
    required_suffixes = {
        "README.md",
        "LICENSE",
        "docs/SPEC.md",
        "docs/repair-guide.md",
        "examples/README.md",
        "scripts/demo.py",
        "tests/test_cli.py",
    }
    for suffix in required_suffixes:
        require(
            any(name.endswith(suffix) for name in source_names),
            f"sdist is missing {suffix}",
        )
    forbidden_parts = ("/.tmp/", "/artifacts/", "/.venv/", "/.uv-cache/")
    require(
        not any(any(part in f"/{name}" for part in forbidden_parts) for name in source_names),
        "sdist contains local build or evidence data",
    )


def installed_gate(wheel: Path) -> None:
    TEMP_ROOT.mkdir(exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="release-", dir=TEMP_ROOT) as directory:
        root = Path(directory)
        environment = root / "venv"
        venv.EnvBuilder(with_pip=True).create(environment)
        scripts = environment / ("Scripts" if os.name == "nt" else "bin")
        python = scripts / ("python.exe" if os.name == "nt" else "python")
        whichproof = scripts / ("whichproof.exe" if os.name == "nt" else "whichproof")
        run((str(python), "-m", "pip", "install", "--no-deps", str(wheel)))

        version = run((str(whichproof), "--version"), capture=True)
        require(version.stdout == "whichproof 0.1.0\n", "installed CLI version is wrong")

        demo = run(
            (
                str(python),
                str(ROOT / "scripts" / "demo.py"),
                "--output-dir",
                str(root / "demo"),
            ),
            capture=True,
        )
        require("WHICHPROOF_DEMO=PASS" in demo.stdout, "installed demo did not pass")
        require("WP105" in demo.stdout, "installed demo did not prove alternate drift")

        invalid = root / "invalid.json"
        invalid.write_text("{", encoding="utf-8")
        rejected = run(
            (str(whichproof), "verify", str(invalid)),
            check=False,
            capture=True,
        )
        require(rejected.returncode == 2, "invalid snapshot returned the wrong exit code")
        require("valid JSON" in rejected.stderr, "invalid snapshot error was not actionable")


def write_checksums(artifacts: Sequence[Path]) -> None:
    lines: list[str] = []
    for artifact in sorted(artifacts, key=lambda path: path.name):
        digest = hashlib.sha256(artifact.read_bytes()).hexdigest()
        lines.append(f"{digest}  {artifact.name}")
    (DIST / "SHA256SUMS").write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")


def main() -> int:
    run((sys.executable, "-m", "ruff", "check", "."))
    run((sys.executable, "-m", "ruff", "format", "--check", "."))
    run((sys.executable, "-m", "mypy", "src", "scripts"))
    run((sys.executable, "-m", "coverage", "erase"))
    run((sys.executable, "-m", "coverage", "run", "-m", "pytest"))
    run((sys.executable, "-m", "coverage", "report"))

    if DIST.exists():
        import shutil

        shutil.rmtree(DIST)
    run((sys.executable, "-m", "build", "--no-isolation", "--outdir", str(DIST)))
    wheels = list(DIST.glob("whichproof-*.whl"))
    sdists = list(DIST.glob("whichproof-*.tar.gz"))
    require(len(wheels) == 1, "expected exactly one wheel")
    require(len(sdists) == 1, "expected exactly one source distribution")
    inspect_archives(wheels[0], sdists[0])
    installed_gate(wheels[0])
    write_checksums((wheels[0], sdists[0]))
    print("WHICHPROOF_RELEASE_GATE=PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
