"""Generate or verify every format adapter from one book-local theme override."""

import argparse
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR / "lib"))

from alkahest.theme import ThemeError, sync_project_theme


def parse_arguments():
    parser = argparse.ArgumentParser(
        description="Resolve book/theme.json over installed Alkahest defaults."
    )
    parser.add_argument(
        "--check", action="store_true", help="fail instead of updating stale adapters"
    )
    return parser.parse_args()


def main():
    arguments = parse_arguments()
    result = sync_project_theme(SCRIPT_DIR.parent, check=arguments.check)
    action = "verified" if arguments.check else "generated"
    colors = result["theme"]["colors"]
    print(
        f"ok: {action} book theme "
        f"({result['outputs']} adapters; primary {colors['primary']}; accent {colors['accent']})"
    )


if __name__ == "__main__":
    try:
        main()
    except (OSError, ThemeError, UnicodeError) as error:
        print(error, file=sys.stderr)
        raise SystemExit(1)
