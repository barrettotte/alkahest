"""Verify rendered semantic icons retain accessible metadata and adjacent text."""

import html
import re
import sys
from pathlib import Path


def main():
    if len(sys.argv) < 2:
        raise RuntimeError(f"usage: {sys.argv[0]} HTML_OR_XHTML...")
    pattern = re.compile(r'''(<span\b(?=[^>]*class="semantic-icon\s)[^>]*>)(.*?)</span>((?:(?!</(?:p|div|h[1-6])>).){0,500})''', re.I | re.S)
    for argument in sys.argv[1:]:
        path = Path(argument)
        markup = path.read_text(encoding="utf-8")
        declared = len(re.findall(r'<span\b(?=[^>]*class="semantic-icon\s)', markup))
        checked = 0
        for opening, body, following in pattern.findall(markup):
            checked += 1
            if 'aria-hidden="true"' not in opening:
                raise RuntimeError(f"error: {path}: rendered semantic icon is not aria-hidden")
            if not re.search(r'\bdata-icon="[a-z][a-z0-9-]*"', opening):
                raise RuntimeError(f"error: {path}: rendered semantic icon has no canonical identity")
            if not re.search(r'\bdata-icon-label="[^"]+"', opening):
                raise RuntimeError(f"error: {path}: rendered semantic icon has no registry label metadata")
            if not re.search(r'<img\b(?=[^>]*\balt="[^"]+")[^>]*>', body, re.S):
                raise RuntimeError(f"error: {path}: rendered semantic icon image has no fallback alternative")
            visible = html.unescape(re.sub(r"<[^>]*>", "", following))
            if not any(character.isalnum() for character in visible):
                raise RuntimeError(f"error: {path}: rendered semantic icon is not followed by visible text")
        if not declared:
            raise RuntimeError(f"error: {path}: no rendered semantic icons were found")
        if checked != declared:
            raise RuntimeError(f"error: {path}: checked {checked} of {declared} rendered semantic icons")
        print(f"ok: rendered icon accessibility ({path}; {checked} icons)")


if __name__ == "__main__":
    try:
        main()
    except (OSError, RuntimeError) as error:
        print(error, file=sys.stderr)
        raise SystemExit(1)
