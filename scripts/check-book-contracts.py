"""Check reusable schemas and the book-owned override-layer inventory."""

import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR / "lib"))

from alkahest.book_contracts import validate_book_contracts
from alkahest.common import ContractError, fail


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
    for marker in ("check-book-contracts:", "test-book-contracts:"):
        if marker not in texts["makefile"]:
            fail(f"Makefile is missing book-contract target {marker}")
    for marker in (
        '("book-contracts", "check-book-contracts.py", False)',
        '("book-contracts", "test-book-contracts.py", False)',
    ):
        if marker not in texts["dispatcher"]:
            fail(f"source dispatcher is missing book-contract entry {marker}")
    if "check-book-contracts.py" not in texts["ci"]:
        fail("CI is missing book-contract validation")
    if "docs/book-contracts.md" not in texts["readme"]:
        fail("README documentation map is missing the book-contract reference")
    for marker in (
        '"destination": "defaults/book-contracts.json"',
        '"destination": "docs/book-contracts.md"',
        '"destination": "schemas/identities.schema.json"',
    ):
        if marker not in texts["template"]:
            fail(f"template package is missing book-contract member {marker}")
    for marker in (
        '"book/.alkahest/book-contracts.json"',
        '"book/.alkahest/schemas/identities.schema.json"',
        '"docs/book-contracts.md"',
    ):
        if marker not in texts["new_book"]:
            fail(f"new-book policy is missing book-contract path {marker}")


def main():
    validate_integration()
    result = validate_book_contracts(ROOT)
    print(
        "ok: reusable book contracts "
        f"({result['domains']} domains; {result['schemas']} schemas; "
        f"{result['adapters']} generated adapters; {result['version']})"
    )


if __name__ == "__main__":
    try:
        main()
    except (ContractError, OSError, UnicodeError) as error:
        print(error, file=sys.stderr)
        raise SystemExit(1)
