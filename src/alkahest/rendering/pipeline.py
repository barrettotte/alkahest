"""Render the three supported publication formats."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import cast

from ..process import run_process

ROOT = Path(__file__).resolve().parents[3]
QUARTO = ROOT / "scripts" / "quarto.sh"
FORMATS = ("html", "epub", "typst")
PLANS = {
    "html": ("html",),
    "epub": ("epub",),
    "typst": ("typst",),
    "all": FORMATS,
}


class Arguments(argparse.Namespace):
    """Typed render command arguments."""

    profile: str


def render(target: str) -> None:
    """Render one format or all supported formats."""
    try:
        formats = PLANS[target]
    except KeyError as error:
        raise ValueError(f"unknown render profile: {target}") from error
    for format_name in formats:
        result = run_process(
            [QUARTO, "render", "book", "--profile", format_name],
            cwd=ROOT,
            check=False,
        )
        if result.returncode:
            raise RuntimeError(f"{format_name} render failed with status {result.returncode}")


def main(arguments: list[str] | None = None) -> int:
    """Render a selected publication format."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("profile", choices=tuple(PLANS))
    options = cast(Arguments, parser.parse_args(arguments))
    try:
        render(options.profile)
    except (OSError, RuntimeError, ValueError) as error:
        print(f"error: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
