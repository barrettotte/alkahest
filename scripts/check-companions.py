"""Validate companion metadata, files, checksums, delivery, and references."""

import os
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR / "lib"))

from alkahest.common import ContractError
from alkahest.companions import KINDS, validate_companions


def main():
    root = Path(os.environ.get("ALKAHEST_COMPANION_BOOK_ROOT", SCRIPT_DIR.parent / "book")).resolve()
    if not root.is_dir():
        raise ContractError("error: companion book root does not exist")
    result = validate_companions(root)
    kinds = ", ".join(f"{result['kinds'][kind]} {kind}" for kind in KINDS)
    print(f"ok: companion materials ({result['items']} items; {kinds}; version, checksum, compatibility, description, delivery, and references)")


if __name__ == "__main__":
    try:
        main()
    except ContractError as error:
        print(error, file=sys.stderr)
        raise SystemExit(1)
