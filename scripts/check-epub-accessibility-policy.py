"""Validate rendered EPUB semantics beyond EPUBCheck and Ace automation."""

import os
import sys
from pathlib import Path

from lib.alkahest.epub_accessibility import EpubPolicyError, validate_epub


ROOT = Path(__file__).resolve().parent.parent
DEFAULT_EPUB = ROOT / "book" / "_build" / "epub" / "Alkahest-Reference-Book.epub"
DEFAULT_POLICY = ROOT / "book" / "epub-accessibility.json"


def main() -> None:
    epub = Path(os.environ.get("ALKAHEST_EPUB", DEFAULT_EPUB))
    policy = Path(os.environ.get("ALKAHEST_EPUB_ACCESSIBILITY_POLICY", DEFAULT_POLICY))
    if len(sys.argv) > 2:
        raise EpubPolicyError("error: usage: check-epub-accessibility-policy.py [EPUB]")
    if len(sys.argv) == 2:
        epub = Path(sys.argv[1])
    if not epub.is_file():
        raise EpubPolicyError(
            f"error: missing rendered EPUB; run make render-epub first: {epub}"
        )
    counts = validate_epub(epub, policy)
    details = ", ".join(f"{value} {key}" for key, value in counts.items())
    print(f"ok: EPUB accessibility policy ({details}; no conformance claim)")


if __name__ == "__main__":
    try:
        main()
    except (OSError, EpubPolicyError) as error:
        print(error, file=sys.stderr)
        raise SystemExit(1)
