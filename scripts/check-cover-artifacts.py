"""Verify generated cover geometry against selected interior PDF artifacts."""

import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR / "lib"))

from alkahest.common import ContractError
from alkahest.covers import check_cover_artifacts


def main():
    result = check_cover_artifacts(SCRIPT_DIR.parent)
    print(
        "ok: cover artifacts "
        f"({result['profiles']} profiles; {result['files']} exact files; "
        f"{result['production_pages']} combined production pages; "
        f"{result['blockers']} explicit press-readiness blockers)"
    )


if __name__ == "__main__":
    try:
        main()
    except (ContractError, OSError, UnicodeError) as error:
        print(error, file=sys.stderr)
        raise SystemExit(1)
