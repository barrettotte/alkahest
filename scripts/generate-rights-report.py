"""Generate deterministic human and machine release rights reports."""

import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR / "lib"))

from alkahest.assets import AssetError
from alkahest.rights_report import generate_outputs


def main():
    summary = generate_outputs(SCRIPT_DIR.parent)
    print(
        "ok: generated release rights report "
        f"({summary['included_assets']} included assets; "
        f"{summary['excluded_private_assets']} excluded private assets; "
        f"{summary['runtime_bundles']} runtime bundles)"
    )


if __name__ == "__main__":
    try:
        main()
    except (AssetError, OSError, UnicodeError) as error:
        print(f"error: {error}", file=sys.stderr)
        raise SystemExit(1)
