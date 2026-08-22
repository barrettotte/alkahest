"""Check template compatibility, migrations, deprecations, and release records."""

import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR / "lib"))

from alkahest.common import ContractError, fail
from alkahest.compatibility import validate_compatibility


ROOT = SCRIPT_DIR.parent


def validate_integration():
    files = {
        "makefile": ROOT / "Makefile",
        "dispatcher": ROOT / "scripts/check-source.py",
        "ci": ROOT / "scripts/ci.sh",
        "readme": ROOT / "README.md",
        "template": ROOT / "config/template/template-package.json",
        "new_book": ROOT / "config/template/new-book.json",
        "archive": ROOT / "config/archive/source-package.json",
    }
    texts = {name: path.read_text(encoding="utf-8") for name, path in files.items()}
    for marker in ("check-compatibility:", "test-compatibility:"):
        if marker not in texts["makefile"]:
            fail(f"Makefile is missing compatibility target {marker}")
    for marker in (
        '("compatibility", "check-compatibility.py", False)',
        '("compatibility", "test-compatibility.py", False)',
    ):
        if marker not in texts["dispatcher"]:
            fail(f"source dispatcher is missing compatibility entry {marker}")
    if "check-compatibility.py" not in texts["ci"]:
        fail("CI is missing compatibility validation")
    if "docs/compatibility.md" not in texts["readme"]:
        fail("README documentation map is missing compatibility guidance")
    for marker in (
        '"destination": "defaults/compatibility.json"',
        '"destination": "defaults/template-releases.json"',
        '"destination": "docs/compatibility.md"',
    ):
        if marker not in texts["template"]:
            fail(f"template package is missing compatibility member {marker}")
    for marker in (
        '".alkahest/alkahest.py"',
        '".alkahest/alkahest-book-template-engine-0.2.0.zip"',
        '"scripts/author.py"',
    ):
        if marker not in texts["new_book"]:
            fail(f"new-book policy is missing compatibility path {marker}")
    if '"compatibility"' not in texts["archive"]:
        fail("source archive restoration is missing compatibility validation")


def main():
    validate_integration()
    result = validate_compatibility(ROOT)
    print(
        "ok: template compatibility "
        f"({result['version']} private-development; {result['domains']} domains; "
        f"{result['migrations']} migrations; {result['deprecations']} deprecations; "
        f"{result['releases']} release records)"
    )


if __name__ == "__main__":
    try:
        main()
    except (ContractError, OSError, UnicodeError) as error:
        print(error, file=sys.stderr)
        raise SystemExit(1)
