"""Validate cover profiles, geometry inputs, and manifestation relationships."""

import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR / "lib"))

from alkahest.common import ContractError
from alkahest.covers import load_cover_policy


def main():
    context = load_cover_policy(SCRIPT_DIR.parent)
    template = context["template"]
    print(
        "ok: cover policy "
        f"({len(context['profiles'])} print profiles; {template['binding']}; "
        f"{template['paper']['id']}; {template['bleed_in']} in bleed; "
        f"{template['finish']}; development-only generic template)"
    )


if __name__ == "__main__":
    try:
        main()
    except (ContractError, OSError, UnicodeError) as error:
        print(error, file=sys.stderr)
        raise SystemExit(1)
