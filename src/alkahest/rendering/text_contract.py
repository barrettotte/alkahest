"""Check normalized print text and positioned PDF word-box contracts."""

import argparse
import re
import sys
from pathlib import Path


def require(pattern, text, message):
    match = re.search(pattern, text)
    if not match:
        raise RuntimeError(message)
    return match


def validate(mode, text):
    """Validate one normalized-text or positioned-word contract."""
    if mode == "bbox":
        width = None
        failed = False
        for line in text.splitlines():
            page = re.search(r'<page width="([0-9.]+)"', line)
            if page:
                width = float(page.group(1))
            for word in re.finditer(r'<word xMin="([0-9.-]+)"[^>]*xMax="([0-9.-]+)"', line):
                minimum, maximum = map(float, word.groups())
                if width is not None and (minimum < -0.1 or maximum > width + 0.1):
                    print(
                        f"word box {minimum:.3f}..{maximum:.3f} crosses {width:.3f}-point page",
                        file=sys.stderr,
                    )
                    failed = True
        if failed:
            raise RuntimeError("positioned word crosses the physical page")
    elif mode == "generated-lists":
        require(
            r"Figure\s+1\.1\s+—\s+Information flow through a half-adder",
            text,
            "missing numbered figure list entry",
        )
        require(
            r"Figure\s+A\.1\s+—\s+Appendix signal-chain fixture",
            text,
            "missing appendix-numbered list entry",
        )
        require(
            r"electric current\s+\(Equation\s+\(?1\.1\)?\)",
            text,
            "missing numbered equation terminology target",
        )
        if "??" in text:
            raise RuntimeError("unresolved generated-list reference")
    else:
        require(
            r"computation,\s*[0-9]+,\s*[0-9]+;\s*see also Turing, Alan",
            text,
            "missing two-page point entry",
        )
        match = require(r"book design,\s*([0-9]+)–([0-9]+)", text, "missing resolved range")
        if int(match.group(2)) <= int(match.group(1)):
            raise RuntimeError("invalid resolved range")
        require(r"Knuth, Donald E\.,\s*[0-9]+", text, "missing person page")
        if "??" in text:
            raise RuntimeError("unresolved page reference")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("mode", choices=("bbox", "generated-lists", "index"))
    parser.add_argument("path")
    arguments = parser.parse_args()
    validate(arguments.mode, Path(arguments.path).read_text(encoding="utf-8"))


if __name__ == "__main__":
    try:
        main()
    except (OSError, UnicodeError, RuntimeError) as error:
        print(error, file=sys.stderr)
        raise SystemExit(1)
