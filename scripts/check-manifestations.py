"""Validate publication manifestations, relations, and typed identifiers."""

import sys
from collections import Counter
from pathlib import Path

from lib.alkahest.manifestations import ContractError, load_and_validate


ROOT = Path(__file__).resolve().parent.parent


def main():
    _registry, records = load_and_validate(ROOT)
    formats = Counter(record["format"] for record in records.values())
    identifiers = sum(len(record["identifiers"]) for record in records.values())
    summary = ", ".join(f"{count} {name}" for name, count in sorted(formats.items()))
    print(
        f"ok: publication manifestations ({len(records)} records; {summary}; "
        f"{identifiers} typed publication identifier)"
    )


if __name__ == "__main__":
    try:
        main()
    except (ContractError, OSError, UnicodeError) as error:
        print(error, file=sys.stderr)
        raise SystemExit(1)
