"""Check manuscript code points against the locale policy's primary font."""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
POLICY = ROOT / "config" / "localization" / "locales.json"
SOURCE_SUFFIXES = {".bib", ".qmd", ".yaml", ".yml"}
IGNORED_CODEPOINTS = {0x00A0, 0x202F}


def manuscript_codepoints():
    values = set()
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


def families_for(codepoint):
    result = subprocess.run(
        [
            "fc-list",
            f":charset={codepoint:04X}",
            "--format",
            "%{family[0]}\n",
        ],
        check=False,
        capture_output=True,
        text=True,
    )
    if result.returncode:
        raise RuntimeError(
            f"fontconfig failed for U+{codepoint:04X}: {result.stderr.strip()}"
        )
    return set(result.stdout.splitlines())


def main():
    if shutil.which("fc-list") is None:
        print("error: fc-list is required for glyph coverage checks", file=sys.stderr)
        return 1
    try:
        policy = json.loads(POLICY.read_text(encoding="utf-8"))
        family = policy.get("font_family")
        if not isinstance(family, str) or not family.strip():
            raise RuntimeError("localization policy needs a font_family")
        codepoints = manuscript_codepoints()
        missing = [
            codepoint
            for codepoint in codepoints
            if family not in families_for(codepoint)
        ]
    except (OSError, json.JSONDecodeError, RuntimeError) as error:
        print(f"error: {error}", file=sys.stderr)
        return 1
    for codepoint in missing:
        print(
            f"error: U+{codepoint:04X} is not covered by {family}", file=sys.stderr
        )
    if missing:
        print(
            "add a locked, licensed locale font before publishing this manuscript",
            file=sys.stderr,
        )
        return 1
    print(
        "ok: manuscript glyphs are covered by the declared "
        f"{family} family ({len(codepoints)} non-ASCII code points)"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
