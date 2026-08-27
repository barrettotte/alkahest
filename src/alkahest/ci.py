"""Run the complete provider-neutral publishing validation pipeline."""

from __future__ import annotations

import sys
from pathlib import Path

from .process import run_process

ROOT = Path(__file__).resolve().parents[2]

# Keep policy here instead of provider YAML so the exact sequence runs locally.
# Bootstrap is the sole networked stage; every later tool boundary is offline.
COMMANDS = (
    ("quality",),
    ("check",),
    ("check", "writing", "glyphs"),
    ("test", "author-guide", "writing-quality"),
    ("render", "all"),
    ("check", "accessibility", "publication"),
)


def run() -> int:
    """Build the image, then run each closed CI command in order."""
    bootstrap = run_process([ROOT / "scripts" / "bootstrap.sh"], cwd=ROOT, check=False)
    if bootstrap.returncode:
        return bootstrap.returncode

    for command in COMMANDS:
        arguments = [sys.executable, "-m", "alkahest", *command]
        result = run_process(arguments, cwd=ROOT, check=False)
        if result.returncode:
            print(f"error: CI command failed: alkahest {' '.join(command)}", file=sys.stderr)
            return result.returncode
    return 0


if __name__ == "__main__":
    raise SystemExit(run())
