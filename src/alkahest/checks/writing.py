"""Run locked spelling, prose, and writing-toolchain checks."""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

from .writing_sources import writing_sources

ROOT = Path(__file__).resolve().parents[3]


class WritingError(RuntimeError):
    """Report a failed writing-quality prerequisite or command."""


def executable(name: str) -> str:
    """Resolve one required locked writing command."""
    resolved = shutil.which(name)
    if resolved is None:
        raise WritingError(f"{name} is required for writing checks")
    return resolved


def run(arguments: list[str], *, check: bool = True) -> subprocess.CompletedProcess[str]:
    """Run one writing command in the locked environment."""
    result = subprocess.run(  # noqa: S603 - commands come from closed definitions
        arguments,
        cwd=ROOT,
        text=True,
        check=False,
    )
    if check and result.returncode:
        raise WritingError(f"command failed with status {result.returncode}: {' '.join(arguments)}")
    return result


def version(arguments: list[str]) -> str:
    """Capture one tool version."""
    result = subprocess.run(  # noqa: S603 - commands are resolved below
        arguments,
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode:
        raise WritingError(f"version command failed: {' '.join(arguments)}")
    return (result.stdout + result.stderr).strip()


def check_toolchain() -> None:
    """Verify pinned prose tools are available under an unprivileged identity."""
    if os.geteuid() == 0:
        raise WritingError("writing tools must run as a non-root user")
    expected = {
        "Node": (
            version([executable("node"), "--version"]),
            f"v{os.environ['ALKAHEST_NODE_VERSION']}",
        ),
        "npm": (version([executable("npm"), "--version"]), os.environ["ALKAHEST_NPM_VERSION"]),
        "Vale": (
            version([executable("vale"), "--version"]),
            f"vale version {os.environ['ALKAHEST_VALE_VERSION']}",
        ),
        "CSpell": (
            version([executable("cspell"), "--version"]),
            os.environ["ALKAHEST_CSPELL_VERSION"],
        ),
        "Ace": (
            version([executable("ace-cli"), "--version"]),
            os.environ["ALKAHEST_ACE_VERSION"],
        ),
    }
    for name, (actual, wanted) in expected.items():
        if actual != wanted:
            raise WritingError(f"{name} version is {actual!r}; expected {wanted!r}")
    axe = json.loads(
        Path("/opt/alkahest/writing/node_modules/axe-core/package.json").read_text(encoding="utf-8")
    )["version"]
    if axe != os.environ["ALKAHEST_AXE_CORE_VERSION"]:
        raise WritingError(
            f"axe-core version is {axe!r}; expected {os.environ['ALKAHEST_AXE_CORE_VERSION']!r}"
        )
    print(
        f"Node {expected['Node'][0]}, npm {expected['npm'][0]}, Vale "
        f"{os.environ['ALKAHEST_VALE_VERSION']}, CSpell {expected['CSpell'][0]}, "
        f"axe-core {axe}, and Ace {expected['Ace'][0]} passed offline rootless validation."
    )


def check_spelling(sources: list[str]) -> int:
    """Run CSpell over canonical writing sources."""
    print(f"Writing spelling gate ({len(sources)} canonical sources)")
    return run(
        [
            executable("cspell"),
            "lint",
            "--config",
            "cspell.json",
            "--no-config-search",
            "--root",
            str(ROOT),
            "--no-cache",
            "--no-progress",
            "--no-summary",
            "--no-color",
            "--unique",
            "--validate-directives",
            *sources,
        ],
        check=False,
    ).returncode


def check_prose(sources: list[str]) -> int:
    """Run Vale over canonical writing sources."""
    print(
        f"Writing prose gate ({len(sources)} canonical sources; subjective rules remain warnings)"
    )
    return run(
        [
            executable("vale"),
            "--config=.vale.ini",
            "--no-global",
            "--no-wrap",
            "--output=line",
            *sources,
        ],
        check=False,
    ).returncode


def check_writing(mode: str) -> int:
    """Validate overrides and run the requested writing gates."""
    run([sys.executable, "-m", "alkahest.generators.writing_terminology", "--check"])
    run([sys.executable, "-m", "alkahest.checks.writing_overrides"])
    sources = writing_sources(ROOT)
    if not sources:
        raise WritingError("no canonical writing sources found")
    if mode == "spelling":
        return check_spelling(sources)
    if mode == "prose":
        return check_prose(sources)
    spelling = check_spelling(sources)
    prose = check_prose(sources)
    return spelling or prose


def main(arguments: list[str] | None = None) -> int:
    """Run one writing suite."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=("all", "spelling", "prose", "toolchain"))
    options = parser.parse_args(arguments)
    try:
        if options.mode == "toolchain":
            check_toolchain()
            return 0
        return check_writing(options.mode)
    except (KeyError, OSError, UnicodeError, WritingError) as error:
        print(f"error: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
