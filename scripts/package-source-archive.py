"""Package a deterministic private source archive for long-term recovery."""

import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR / "lib"))

from alkahest.common import ContractError
from alkahest.source_archive import package_source_archive


def main():
    result = package_source_archive(SCRIPT_DIR.parent)
    print(
        "ok: packaged private source archive "
        f"({result['source_files']} repository files; "
        f"{result['archive_members']} archive members; {result['bytes']} bytes)"
    )


if __name__ == "__main__":
    try:
        main()
    except (ContractError, OSError, UnicodeError) as error:
        print(error, file=sys.stderr)
        raise SystemExit(1)
