"""Build deterministic local ZIP packages for registered companion materials."""

import argparse
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR / "lib"))

from alkahest.common import ContractError
from alkahest.companion_bundles import package_companion_bundles


def arguments():
    parser = argparse.ArgumentParser(description="Package companion-material bundles.")
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
    result = package_companion_bundles(options.book_root, options.output_root)
    print(
        "ok: packaged companion materials "
        f"({result['bundles']} bundle; {result['items']} items; "
        f"{result['files']} generated files)"
    )


if __name__ == "__main__":
    try:
        main()
    except (ContractError, OSError) as error:
        print(error, file=sys.stderr)
        raise SystemExit(1)
