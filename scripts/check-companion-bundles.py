"""Verify companion ZIPs, manifests, licenses, and checksums against source."""

import argparse
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR / "lib"))

from alkahest.common import ContractError
from alkahest.companion_bundles import check_companion_bundles


def arguments():
    parser = argparse.ArgumentParser(description="Check companion-material bundles.")
    parser.add_argument(
        "--book-root", type=Path, default=SCRIPT_DIR.parent / "book"
    )
    parser.add_argument(
        "--output-root",
        type=Path,
        default=SCRIPT_DIR.parent / "book/_build/companion",
    )
    return parser.parse_args()


def main():
    options = arguments()
    result = check_companion_bundles(options.book_root, options.output_root)
    print(
        "ok: companion bundles "
        f"({result['bundles']} deterministic bundle; {result['items']} items; "
        f"license, manifest, internal/outer checksums; {result['bytes']} bytes)"
    )


if __name__ == "__main__":
    try:
        main()
    except (ContractError, OSError) as error:
        print(error, file=sys.stderr)
        raise SystemExit(1)
