"""Validate rights coverage and private metadata in rendered release artifacts."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts" / "lib"))

from alkahest.assets import (  # noqa: E402
    AssetError,
    check_epub,
    check_html,
    check_pdfs,
    load_policy,
)


DEFAULT_POLICY = ROOT / "book" / "assets.json"


def arguments():
    parser = argparse.ArgumentParser(
        description="Validate rendered release assets, metadata, and privacy."
    )
    parser.add_argument("policy", nargs="?", type=Path, default=DEFAULT_POLICY)
    parser.add_argument("--repo-root", type=Path, default=ROOT)
    return parser.parse_args()


def main():
    options = arguments()
    root = options.repo_root.resolve()
    policy_path = options.policy
    if not policy_path.is_absolute():
        policy_path = root / policy_path
    try:
        policy, approved, counts = load_policy(root, policy_path)
        html_assets = check_html(root, policy, approved)
        epub_media = check_epub(root, policy, approved)
        pdf_count = check_pdfs(root, policy)
    except (OSError, AssetError) as error:
        print(f"error: {error}", file=sys.stderr)
        return 1
    print(
        "ok: rendered release assets "
        f"({len(approved)} approved source assets; {html_assets} HTML assets; "
        f"{epub_media} EPUB media objects; {pdf_count} PDFs; "
        f"{counts['runtime_bundles']} licensed runtime bundles)"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
