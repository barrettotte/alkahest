"""Generate deterministic wrap templates, thumbnails, and cover manifests."""

import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR / "lib"))

from alkahest.common import ContractError
from alkahest.covers import generate_cover_artifacts


def main():
    result = generate_cover_artifacts(SCRIPT_DIR.parent)
    print(
        "ok: generated cover artifacts "
        f"({result['profiles']} profiles; {result['files']} templates, thumbnails, and manifests)"
    )


if __name__ == "__main__":
    try:
        main()
    except (ContractError, OSError, UnicodeError) as error:
        print(error, file=sys.stderr)
        raise SystemExit(1)
