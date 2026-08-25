"""Run the complete provider-neutral publishing validation pipeline."""

from __future__ import annotations

import shlex
import sys
from pathlib import Path

from .process import run_process

ROOT = Path(__file__).resolve().parents[2]

# Keep policy here instead of provider YAML so the exact sequence runs locally.
# Bootstrap is the sole networked stage; every later tool boundary is offline.
COMMANDS = (
    "alkahest quality",
    "alkahest doctor",
    "alkahest report toolchain",
    "alkahest check writing-toolchain writing glyph-coverage",
    "alkahest test accessibility-browser writing-quality author-guide",
    "alkahest check",
    "alkahest test",
    "alkahest generate rights-report",
    "alkahest check rights-report",
    "alkahest package companion-bundles",
    "alkahest check companion-bundles",
    "alkahest render complete",
    "alkahest check preview",
    "alkahest generate covers",
    "alkahest check cover-artifacts",
    "python3 -m alkahest.checks.reproducibility --repeat quick",
    "alkahest check golden-pages",
    "alkahest check accessibility epub-accessibility publication pdf-profiles",
)


def run() -> int:
    """Build the image, then run each closed CI command in order."""
    bootstrap = run_process([ROOT / "scripts" / "bootstrap.sh"], cwd=ROOT, check=False)
    if bootstrap.returncode:
        return bootstrap.returncode
    for display in COMMANDS:
        arguments = shlex.split(display)
        if arguments[0] == "alkahest":
            arguments = [sys.executable, "-m", "alkahest", *arguments[1:]]
        else:
            arguments[0] = sys.executable
        result = run_process(arguments, cwd=ROOT, check=False)
        if result.returncode:
            print(f"error: CI command failed: {display}", file=sys.stderr)
            return result.returncode
    return 0


if __name__ == "__main__":
    raise SystemExit(run())
