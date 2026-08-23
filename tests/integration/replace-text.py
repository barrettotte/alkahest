"""Apply explicit literal or regular-expression edits to fixture text files."""

import argparse
import re
import sys
from pathlib import Path


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--regex", action="store_true", help="interpret PATTERN as a Python regular expression")
    parser.add_argument("--all", action="store_true", help="replace every match in each file")
    parser.add_argument("pattern", metavar="PATTERN")
    parser.add_argument("replacement", metavar="REPLACEMENT")
    parser.add_argument("files", metavar="FILE", nargs="+")
    arguments = parser.parse_args()
    for filename in arguments.files:
        path = Path(filename)
        content = path.read_text(encoding="utf-8")
        if arguments.regex:
            changed, count = re.subn(
                arguments.pattern,
                arguments.replacement,
                content,
                count=0 if arguments.all else 1,
                flags=re.M,
            )
        else:
            available = content.count(arguments.pattern)
            count = available if arguments.all else min(available, 1)
            changed = content.replace(arguments.pattern, arguments.replacement, -1 if arguments.all else 1)
        if count == 0:
            raise RuntimeError(f"error: fixture edit did not match {arguments.pattern!r} in {path}")
        path.write_text(changed, encoding="utf-8")


if __name__ == "__main__":
    try:
        main()
    except (OSError, UnicodeError, re.error, RuntimeError) as error:
        print(error, file=sys.stderr)
        raise SystemExit(1)
