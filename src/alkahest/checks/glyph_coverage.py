"""Check manuscript code points against the engine's primary font."""

from __future__ import annotations

import shutil
import sys
from pathlib import Path

from alkahest.process import run_process

ROOT = Path(__file__).resolve().parents[3]
FONT_FAMILY = "Libertinus Serif"
SOURCE_SUFFIXES = {".bib", ".qmd", ".yaml", ".yml"}
IGNORED_CODEPOINTS = {0x00A0, 0x202F}


def manuscript_codepoints() -> list[int]:
    """Collect non-ASCII code points used by publication sources."""
    values: set[int] = set()
    for path in sorted(ROOT.joinpath("book").rglob("*")):
        if (
            not path.is_file()
            or path.suffix not in SOURCE_SUFFIXES
            or "_build" in path.parts
            or ".quarto" in path.parts
        ):
            continue

        for character in path.read_text(encoding="utf-8"):
            codepoint = ord(character)
            if codepoint >= 0x80 and codepoint not in IGNORED_CODEPOINTS:
                values.add(codepoint)

    return sorted(values)


def families_for(codepoint: int) -> set[str]:
    """Return font families that cover one code point."""
    result = run_process(
        ["fc-list", f":charset={codepoint:04X}", "--format", "%{family[0]}\n"],
        check=False,
        capture_output=True,
        text=True,
    )
    if result.returncode:
        raise RuntimeError(f"fontconfig failed for U+{codepoint:04X}: {result.stderr.strip()}")
    return set(result.stdout.splitlines())


def main() -> int:
    """Check every manuscript code point against the body font."""
    if shutil.which("fc-list") is None:
        print("error: fc-list is required for glyph coverage checks", file=sys.stderr)
        return 1
    try:
        codepoints = manuscript_codepoints()
        missing = [codepoint for codepoint in codepoints if FONT_FAMILY not in families_for(codepoint)]
    except (OSError, RuntimeError) as error:
        print(f"error: {error}", file=sys.stderr)
        return 1
    for codepoint in missing:
        print(f"error: U+{codepoint:04X} is not covered by {FONT_FAMILY}", file=sys.stderr)
    if missing:
        print("add a locked, licensed locale font before publishing this manuscript", file=sys.stderr)
        return 1
    print(
        "ok: manuscript glyphs are covered by the declared "
        f"{FONT_FAMILY} family ({len(codepoints)} non-ASCII code points)"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
