"""Validate the reusable template-engine extraction boundary."""

import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR / "lib"))

from alkahest.common import ContractError
from alkahest.template_package import load_template_policy, validate_template_integration


def main():
    validate_template_integration(SCRIPT_DIR.parent)
    context = load_template_policy(SCRIPT_DIR.parent)
    directory_count = len(context["policy"]["directory_components"])
    print(
        "ok: template engine policy "
        f"({len(context['mappings'])} reusable files; {directory_count} directories; "
        f"version {context['package']['version']}; {context['package']['license']})"
    )


if __name__ == "__main__":
    try:
        main()
    except (ContractError, OSError, UnicodeError) as error:
        print(error, file=sys.stderr)
        raise SystemExit(1)
