"""Stage an isolated full or preview project from its book-local allowlist."""

import argparse
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR.parent / "src"))

from alkahest.release_profiles import ReleaseProfileError, stage_project_release


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("profile", choices=("full", "preview"))
    parser.add_argument(
        "--html-resources",
        action="store_true",
        help="materialize only rich-media resources referenced by selected sources",
    )
    arguments = parser.parse_args()
    result = stage_project_release(
        SCRIPT_DIR.parent, arguments.profile, html_resources=arguments.html_resources
    )
    print(result["stage"])


if __name__ == "__main__":
    try:
        main()
    except (OSError, ReleaseProfileError, UnicodeError) as error:
        print(error, file=sys.stderr)
        raise SystemExit(1)
