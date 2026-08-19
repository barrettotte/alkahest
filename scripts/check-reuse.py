"""Validate controlled reusable fragments, parameters, contexts, and use sites."""

import os
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR / "lib"))

from alkahest.common import ContractError
from alkahest.reuse import KINDS, validate_reuse


def main():
    root = Path(os.environ.get("ALKAHEST_REUSE_BOOK_ROOT", SCRIPT_DIR.parent / "book")).resolve()
    if not root.is_dir():
        raise ContractError("error: reusable-content book root does not exist")
    result = validate_reuse(root)
    kinds = ", ".join(f"{result['kinds'][kind]} {kind}" for kind in KINDS)
    print(f"ok: controlled content reuse ({result['items']} fragments; {result['calls']} explicit use sites; {kinds}; version, checksum, provenance, context, parameters, and dependency boundary)")


if __name__ == "__main__":
    try:
        main()
    except ContractError as error:
        print(error, file=sys.stderr)
        raise SystemExit(1)
