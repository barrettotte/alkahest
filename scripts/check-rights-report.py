"""Verify deterministic release rights reports against canonical policies."""

import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR / "lib"))

from alkahest.assets import AssetError
from alkahest.rights_report import check_outputs


def main():
    summary = check_outputs(SCRIPT_DIR.parent)
    print(
        "ok: release rights report "
        f"({summary['included_assets']} exact assets; "
        f"{summary['runtime_bundles']} licensed runtime bundles; "
        f"release ready: {'yes' if summary['ready'] else 'no'})"
    )


if __name__ == "__main__":
    try:
        main()
    except (AssetError, OSError, UnicodeError) as error:
        print(f"error: {error}", file=sys.stderr)
        raise SystemExit(1)
