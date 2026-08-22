"""Reject stale generated publication metadata and drifting ONIX mappings."""

import sys
from pathlib import Path

from lib.alkahest.metadata_generation import (
    ContractError,
    check_generated,
    validate_repository,
)


ROOT = Path(__file__).resolve().parent.parent


def main():
    status = check_generated(ROOT)
    validate_repository(ROOT)
    state = "generated" if status["generated"] else "withheld until retail metadata is complete"
    print(
        "ok: generated publication metadata "
        f"(ONIX 3.1 {state}; code lists issue {status['code_list_issue']})"
    )


if __name__ == "__main__":
    try:
        main()
    except (ContractError, OSError, UnicodeError) as error:
        print(error, file=sys.stderr)
        raise SystemExit(1)
