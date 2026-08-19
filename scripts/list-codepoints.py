"""List non-ASCII manuscript code points for font coverage checks."""

import sys
from pathlib import Path


def main():
    values = set()
    for argument in sys.argv[1:]:
        for character in Path(argument).read_text(encoding="utf-8"):
            codepoint = ord(character)
            if codepoint >= 0x80 and codepoint not in {0x00A0, 0x202F}: values.add(codepoint)
    for codepoint in sorted(values): print(f"{codepoint:04X}")


if __name__ == "__main__": main()
