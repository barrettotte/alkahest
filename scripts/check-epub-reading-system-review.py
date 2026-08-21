"""Validate the manual EPUB reader matrix, evidence, and claim state."""

import os
import sys
from pathlib import Path

from lib.alkahest.epub_review import EpubReviewError, load_json, validate_review


ROOT = Path(__file__).resolve().parent.parent


def main():
    review_path = Path(
        os.environ.get(
            "ALKAHEST_EPUB_REVIEW",
            ROOT / "book" / "epub-reading-system-review.json",
        )
    )
    policy_path = Path(
        os.environ.get(
            "ALKAHEST_EPUB_ACCESSIBILITY_POLICY",
            ROOT / "book" / "epub-accessibility.json",
        )
    )
    artifact_override = os.environ.get("ALKAHEST_EPUB_REVIEW_ARTIFACT")
    result = validate_review(
        load_json(review_path, "EPUB reading-system review"),
        load_json(policy_path, "EPUB accessibility policy"),
        ROOT,
        artifact_override,
    )
    print(
        "ok: EPUB manual review contract "
        f"({result['systems']} reading systems/{result['engines']} engines; "
        f"{result['scales']} text scales; {result['locations']} locations; "
        f"{result['criteria']} criteria per system; {result['pending']} results "
        f"pending; conformance claim: {'yes' if result['claim'] else 'no'})"
    )


if __name__ == "__main__":
    try:
        main()
    except (OSError, EpubReviewError) as error:
        print(error, file=sys.stderr)
        raise SystemExit(1)
