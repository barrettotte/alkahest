"""Validate private source-archive selection, history, and restoration policy."""

import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR / "lib"))

from alkahest.common import ContractError
from alkahest.source_archive import load_archive_policy


def main():
    context = load_archive_policy(SCRIPT_DIR.parent)
    print(
        "ok: source archive policy "
        f"({len(context['selected'])} source files; "
        f"{len(context['redirects'])} redirects; "
        f"{len(context['prior_editions'])} prior editions; "
        f"{context['package']['confidentiality']})"
    )


if __name__ == "__main__":
    try:
        main()
    except (ContractError, OSError, UnicodeError) as error:
        print(error, file=sys.stderr)
        raise SystemExit(1)
