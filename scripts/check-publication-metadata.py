"""Validate canonical work-level publication metadata and adapter parity."""

import sys
from pathlib import Path

from lib.alkahest.publication_metadata import ContractError, load_and_validate


ROOT = Path(__file__).resolve().parent.parent


def main():
    record = load_and_validate(ROOT)
    work = record["work"]
    print(
        "ok: canonical publication metadata "
        f"({len(record['contributors'])} contributor; "
        f"{len(work['subjects'])} subjects; {len(work['keywords'])} keywords; "
        f"{len(work['audiences'])} audiences; {work['status']})"
    )


if __name__ == "__main__":
    try:
        main()
    except (ContractError, OSError, UnicodeError) as error:
        print(error, file=sys.stderr)
        raise SystemExit(1)
