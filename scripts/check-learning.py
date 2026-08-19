"""Validate semantic learning blocks, pairings, metadata, and private answers."""

import os
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR / "lib"))

from alkahest.common import ContractError
from alkahest.editions import load_editions
from alkahest.learning import TYPES, validate_learning


def main():
    root = Path(os.environ.get("ALKAHEST_LEARNING_BOOK_ROOT", SCRIPT_DIR.parent / "book")).resolve()
    if not root.is_dir():
        raise ContractError("error: learning book root does not exist")
    counts = validate_learning(root, load_editions(root / "editions.json"))
    summary = "; ".join(f"{counts[item]} {item}" for item in TYPES)
    print(f"ok: learning components ({summary}; paired relationships; private answer isolation)")


if __name__ == "__main__":
    try:
        main()
    except ContractError as error:
        print(error, file=sys.stderr)
        raise SystemExit(1)
