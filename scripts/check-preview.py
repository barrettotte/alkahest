"""Validate the standalone HTML, EPUB, and PDF preview artifact set."""

import os
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR / "lib"))

from alkahest.common import ContractError
from alkahest.preview_artifacts import (
    collect_preview_artifacts,
    validate_preview_artifacts,
)


def main():
    root = Path(os.environ.get("ALKAHEST_PREVIEW_ROOT", SCRIPT_DIR.parent))
    result = validate_preview_artifacts(collect_preview_artifacts(root))
    print(
        "ok: preview artifacts "
        f"({result['sources']} selected sources; {result['html_pages']} HTML pages; "
        f"{result['epub_chapters']} EPUB chapters; {result['pdf_pages']} PDF pages; "
        f"{result['fonts']} embedded fonts)"
    )


if __name__ == "__main__":
    try:
        main()
    except (ContractError, OSError) as error:
        print(error, file=sys.stderr)
        raise SystemExit(1)
