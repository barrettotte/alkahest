"""Apply versioned accessibility metadata, semantics, and optional page navigation."""

import os
import sys
from pathlib import Path

from lib.alkahest.epub_accessibility import EpubPolicyError, finalize_epub


ROOT = Path(__file__).resolve().parent.parent
DEFAULT_EPUB = ROOT / "book" / "_build" / "epub" / "Alkahest-Reference-Book.epub"
DEFAULT_POLICY = ROOT / "book" / "epub-accessibility.json"


def main() -> None:
    epub = Path(os.environ.get("ALKAHEST_EPUB", DEFAULT_EPUB))
    policy = Path(os.environ.get("ALKAHEST_EPUB_ACCESSIBILITY_POLICY", DEFAULT_POLICY))
    if len(sys.argv) > 2:
        raise EpubPolicyError("error: usage: finalize-epub.py [EPUB]")
    if len(sys.argv) == 2:
        epub = Path(sys.argv[1])
    if not epub.is_file():
        raise EpubPolicyError(f"error: missing rendered EPUB: {epub}")
    finalize_epub(epub, policy)
    print(f"ok: finalized EPUB accessibility semantics ({epub})")


if __name__ == "__main__":
    try:
        main()
    except (OSError, EpubPolicyError) as error:
        print(error, file=sys.stderr)
        raise SystemExit(1)
