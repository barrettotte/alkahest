"""Generate or verify reusable full/preview profiles for one book."""

import argparse
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR / "lib"))

from alkahest.release_profiles import ReleaseProfileError, sync_project_releases


def main():
    parser = argparse.ArgumentParser(
        description="Resolve book/releases.json over installed release defaults."
    )
    parser.add_argument(
        "--check", action="store_true", help="fail instead of updating stale profiles"
    )
    arguments = parser.parse_args()
    result = sync_project_releases(SCRIPT_DIR.parent, check=arguments.check)
    action = "verified" if arguments.check else "generated"
    profiles = result["resolved"]["profiles"]
    print(
        f"ok: {action} book release profiles "
        f"({result['outputs']} adapters; full {len(profiles['full']['chapters'])} chapters; "
        f"preview {len(profiles['preview']['chapters'])} entries)"
    )


if __name__ == "__main__":
    try:
        main()
    except (OSError, ReleaseProfileError, UnicodeError) as error:
        print(error, file=sys.stderr)
        raise SystemExit(1)
