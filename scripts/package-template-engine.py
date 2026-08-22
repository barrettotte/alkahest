"""Package the extracted reusable template engine deterministically."""

import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR / "lib"))

from alkahest.common import ContractError
from alkahest.template_package import package_template


def main():
    result = package_template(SCRIPT_DIR.parent)
    print(
        "ok: packaged template engine "
        f"({result['source_files']} reusable files; {result['members']} members; "
        f"{result['bytes']} bytes)"
    )


if __name__ == "__main__":
    try:
        main()
    except (ContractError, OSError, UnicodeError) as error:
        print(error, file=sys.stderr)
        raise SystemExit(1)
