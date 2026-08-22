"""Validate the shipped extension API inventory and integration boundary."""

import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR / "lib"))

from alkahest.common import ContractError, fail
from alkahest.extension_apis import validate_extension_apis


ROOT = SCRIPT_DIR.parent


def validate_integration():
    files = {
        "makefile": ROOT / "Makefile",
        "dispatcher": ROOT / "scripts/check-source.py",
        "ci": ROOT / "scripts/ci.sh",
        "readme": ROOT / "README.md",
        "template": ROOT / "config/template/template-package.json",
        "new_book": ROOT / "config/template/new-book.json",
    }
    texts = {name: path.read_text(encoding="utf-8") for name, path in files.items()}
    for marker in ("check-extension-apis:", "test-extension-apis:"):
        if marker not in texts["makefile"]:
            fail(f"Makefile is missing extension API target {marker}")
    for marker in (
        '("extension-apis", "check-extension-apis.py", False)',
        '("extension-apis", "test-extension-apis.py", False)',
    ):
        if marker not in texts["dispatcher"]:
            fail(f"source dispatcher is missing extension API entry {marker}")
    if "check-extension-apis.py" not in texts["ci"]:
        fail("CI is missing extension API validation")
    if "docs/extension-apis.md" not in texts["readme"]:
        fail("README documentation map is missing the extension API reference")
    for marker in (
        '"destination": "defaults/extension-apis.json"',
        '"destination": "docs/extension-apis.md"',
    ):
        if marker not in texts["template"]:
            fail(f"template package is missing extension API member {marker}")
    for marker in (
        '".alkahest/alkahest.py"',
        '".alkahest/alkahest-book-template-engine-0.2.0.zip"',
    ):
        if marker not in texts["new_book"]:
            fail(f"new-book policy is missing extension API path {marker}")


def main():
    validate_integration()
    result = validate_extension_apis(ROOT)
    print(
        "ok: extension API reference "
        f"({result['entries']} surfaces; {result['levels']} authority levels; "
        f"{result['manifests']} extensions; {result['filters']} filters; "
        f"{result['generators']} generators; {result['stability']} {result['api_version']})"
    )


if __name__ == "__main__":
    try:
        main()
    except (ContractError, OSError, UnicodeError) as error:
        print(error, file=sys.stderr)
        raise SystemExit(1)
