"""Validate asset rights records, checksums, coverage, and source privacy."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts" / "lib"))

from alkahest.assets import (  # noqa: E402
    AssetError,
    book_path,
    check_embedded_metadata,
    check_privacy,
    forbidden_patterns,
    load_policy,
)


DEFAULT_POLICY = ROOT / "book" / "assets.json"


def arguments():
    parser = argparse.ArgumentParser(
        description="Validate the asset rights and source-privacy contract."
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
        privacy = forbidden_patterns(policy["artifact_contract"])
        for relative in sorted(approved):
            path = book_path(root, relative, "approved asset")
            content = path.read_bytes()
            check_privacy(f"source asset {relative}", content, privacy)
            check_embedded_metadata(f"source asset {relative}", content)
    except (OSError, AssetError) as error:
        print(f"error: {error}", file=sys.stderr)
        return 1
    print(
        "ok: asset rights and source privacy "
        f"({counts['collections']} collections; {counts['registries']} registries; "
        f"{counts['items']} registry items; {counts['files']} checksum-locked files; "
        f"{counts['runtime_bundles']} runtime bundles)"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
