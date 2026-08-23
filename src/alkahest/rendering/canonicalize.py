"""Stabilize attribute ordering in rendered HTML and XHTML files."""

import argparse
import sys
from pathlib import Path

from alkahest.markup import canonicalize_markup

SUFFIXES = {".html", ".htm", ".xhtml"}
COPY_ONLY_DIRECTORIES = {"media"}


def candidates(paths):
    for path in paths:
        if path.is_dir():
            yield from (
                candidate
                for candidate in sorted(path.rglob("*"))
                if candidate.is_file()
                and candidate.suffix.lower() in SUFFIXES
                and not COPY_ONLY_DIRECTORIES.intersection(candidate.relative_to(path).parts)
            )
        elif path.is_file() and path.suffix.lower() in SUFFIXES:
            yield path
        else:
            raise RuntimeError(f"error: markup path is missing or unsupported: {path}")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("paths", nargs="+", type=Path)
    arguments = parser.parse_args()
    checked = 0
    changed = 0
    for path in candidates(arguments.paths):
        original = path.read_text(encoding="utf-8")
        canonical = canonicalize_markup(original)
        if canonical != original:
            path.write_text(canonical, encoding="utf-8")
            changed += 1
        checked += 1
    print(f"ok: canonical markup ({checked} files; {changed} rewritten)")


if __name__ == "__main__":
    try:
        main()
    except (OSError, RuntimeError, UnicodeError) as error:
        print(error, file=sys.stderr)
        raise SystemExit(1)
