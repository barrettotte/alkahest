"""Verify exact template-engine package bytes and extracted structure."""

import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR / "lib"))

from alkahest.common import ContractError
from alkahest.template_package import check_template_package


def main():
    result = check_template_package(SCRIPT_DIR.parent)
    print(
        "ok: template engine package "
        f"({result['source_files']} exact reusable files; "
        f"{result['members']} verified members; extracted smoke: yes)"
    )


if __name__ == "__main__":
    try:
        main()
    except (ContractError, OSError, RuntimeError, UnicodeError) as error:
        print(error, file=sys.stderr)
        raise SystemExit(1)
