"""Exercise new-book identity, safety, determinism, and validation failures."""

import json
import sys
import tempfile
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR / "lib"))

from alkahest.common import ContractError
from alkahest.new_book import create_new_book, normalize_book_options, validate_scaffold


ROOT = SCRIPT_DIR.parent


def expect_failure(name, expected, callback):
    try:
        callback()
    except ContractError as error:
        if expected not in str(error):
            raise RuntimeError(
                f"error: new-book fixture {name} missed {expected!r}: {error}"
            ) from error
    else:
        raise RuntimeError(f"error: new-book fixture {name} unexpectedly passed")


def option_failure(name, expected, **values):
    defaults = {"title": "Fixture Book", "author": "Fixture Author", "created": "2026-08-22"}
    defaults.update(values)
    expect_failure(name, expected, lambda: normalize_book_options(ROOT, **defaults))


def main():
    option_failure("empty-title", "book title must be nonempty", title="")
    option_failure("newline-author", "one line", author="First\nSecond")
    option_failure("invalid-id", "lowercase kebab-case", book_id="Fixture Book")
    option_failure("empty-derived-id", "must be supplied", title="日本語")
    option_failure("invalid-language", "language tag", language="English (US)")
    option_failure("invalid-date", "YYYY-MM-DD", created="August 22")
    option_failure("old-date", "1980-01-01", created="1979-12-31")

    with tempfile.TemporaryDirectory(prefix="alkahest-new-book-fixtures.") as temporary:
        parent = Path(temporary)
        first = parent / "first"
        second = parent / "second"
        values = {
            "title": "Independent Metadata",
            "author": "Ada Example",
            "book_id": "independent-metadata",
            "subtitle": "One Book, Four Formats",
            "language": "en-GB",
            "created": "2026-08-22",
        }
        create_new_book(ROOT, first, **values)
        create_new_book(ROOT, second, **values)
        first_files = {
            path.relative_to(first): path.read_bytes()
            for path in first.rglob("*")
            if path.is_file()
        }
        second_files = {
            path.relative_to(second): path.read_bytes()
            for path in second.rglob("*")
            if path.is_file()
        }
        if first_files != second_files:
            raise RuntimeError("error: identical new-book inputs produced different files")
        publication = json.loads((first / "book/publication.json").read_text(encoding="utf-8"))
        scaffold = json.loads((first / ".alkahest/scaffold.json").read_text(encoding="utf-8"))
        if (
            publication["work"]["title"] != values["title"]
            or scaffold["book"]["author"] != values["author"]
        ):
            raise RuntimeError("error: generated book metadata is not independent")
        expect_failure(
            "existing-destination",
            "already exists",
            lambda: create_new_book(ROOT, first, **values),
        )
        engine_path = first / "book/filters/math-alt.lua"
        engine_path.write_bytes(engine_path.read_bytes() + b"\nchanged\n")
        expect_failure(
            "engine-drift",
            "missing or changed",
            lambda: validate_scaffold(first),
        )

    with tempfile.TemporaryDirectory(prefix="alkahest-new-book-parent.") as temporary:
        missing_parent = Path(temporary) / "missing" / "book"
        expect_failure(
            "missing-parent",
            "parent must be an existing",
            lambda: create_new_book(
                ROOT,
                missing_parent,
                title="Book",
                author="Author",
                created="2026-08-22",
            ),
        )
    print(
        "ok: new-book fixtures "
        "(deterministic independent scaffold; 7 input and 3 filesystem/integrity failures rejected)"
    )


if __name__ == "__main__":
    try:
        main()
    except (ContractError, OSError, RuntimeError, UnicodeError) as error:
        print(error, file=sys.stderr)
        raise SystemExit(1)
