"""Bind a pending manual EPUB review to a clean revision and rendered artifact."""

import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

from lib.alkahest.epub_review import canonical_epub_sha256, load_json, root_path


ROOT = Path(__file__).resolve().parent.parent
REVIEW_PATH = ROOT / "book" / "epub-reading-system-review.json"


def git(*arguments):
    return subprocess.run(
        ["git", *arguments],
        cwd=ROOT,
        check=True,
        text=True,
        capture_output=True,
    ).stdout.strip()


def main():
    if git("status", "--porcelain", "--untracked-files=normal"):
        raise RuntimeError(
            "error: commit or remove worktree changes before preparing review evidence"
        )
    review = load_json(REVIEW_PATH, "EPUB reading-system review")
    statuses = [
        result.get("status")
        for system in review.get("reading_systems", [])
        for result in system.get("results", []) + system.get("scale_results", [])
    ]
    if set(statuses) != {"pending"}:
        raise RuntimeError(
            "error: cannot replace artifact identity after manual evidence is recorded"
        )
    artifact = review.get("artifact", {})
    artifact_path = root_path(ROOT, artifact.get("path"), "review artifact path")
    if not artifact_path.is_file():
        raise RuntimeError(f"error: missing rendered EPUB: {artifact_path}")
    artifact.update(
        source_revision=git("rev-parse", "HEAD"),
        content_sha256=canonical_epub_sha256(artifact_path),
        prepared_at=datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
    )
    REVIEW_PATH.write_text(json.dumps(review, indent=2) + "\n", encoding="utf-8")
    print(
        "prepared: EPUB manual review artifact "
        f"({artifact['source_revision'][:12]}; {artifact['content_sha256'][:12]}...)"
    )


if __name__ == "__main__":
    try:
        main()
    except (OSError, RuntimeError, subprocess.CalledProcessError) as error:
        print(error, file=sys.stderr)
        raise SystemExit(1)
