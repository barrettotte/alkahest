"""Regenerate shared Quarto, release-manifest, and optional ONIX metadata."""

import argparse
import sys
from pathlib import Path

from lib.alkahest.metadata_generation import ContractError, generate


ROOT = Path(__file__).resolve().parent.parent


def main():
    parser = argparse.ArgumentParser(
        description="Generate deterministic publication metadata adapters."
    )
    parser.add_argument(
        "--require-onix",
        action="store_true",
        help="fail unless at least one complete retail product produces ONIX XML",
    )
    arguments = parser.parse_args()
    status = generate(ROOT, require_onix=arguments.require_onix)
    if status["generated"]:
        print(
            "ok: generated shared publication metadata and ONIX 3.1 "
            f"({len(status['eligible_manifestations'])} product records; "
            f"code lists issue {status['code_list_issue']})"
        )
    else:
        print(
            "ok: generated shared publication metadata; ONIX withheld "
            f"(0 eligible products; code lists issue {status['code_list_issue']})"
        )


if __name__ == "__main__":
    try:
        main()
    except (ContractError, OSError, UnicodeError) as error:
        print(error, file=sys.stderr)
        raise SystemExit(1)
