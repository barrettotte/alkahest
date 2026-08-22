"""Verify exact private source-archive bytes and a fresh extracted restoration."""

import argparse
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR / "lib"))

from alkahest.common import ContractError
from alkahest.source_archive import check_source_archive


def arguments():
    parser = argparse.ArgumentParser(
        description="Check deterministic source archive and restoration smoke."
    )
    parser.add_argument(
        "--no-restore",
        action="store_true",
        help="check package bytes without running the extracted-tree smoke",
    )
    return parser.parse_args()


def main():
    options = arguments()
    result = check_source_archive(SCRIPT_DIR.parent, restore=not options.no_restore)
    print(
        "ok: private source archive "
        f"({result['source_files']} exact repository files; "
        f"{result['archive_members']} verified members; "
        f"restoration smoke: {'yes' if result['restored'] else 'skipped'})"
    )


if __name__ == "__main__":
    try:
        main()
    except (ContractError, OSError, RuntimeError, UnicodeError) as error:
        print(error, file=sys.stderr)
        raise SystemExit(1)
