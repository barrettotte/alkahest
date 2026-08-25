"""Exercise new-book identity, safety, determinism, and validation failures."""

import json
import sys
import tempfile
import tomllib
from pathlib import Path
from unittest.mock import patch

SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR.parents[1] / "src"))

from alkahest.author_project import add_chapter, discover_content, doctor, load_author_config
from alkahest.common import ContractError
from alkahest.new_book import create_new_book, normalize_book_options, validate_scaffold

ROOT = SCRIPT_DIR.parents[1]


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
        if (
            Path("Containerfile") not in first_files
            or any(path.suffix in {".zip", ".py"} for path in first_files)
            or b"--network=none" not in first_files[Path("Makefile")]
        ):
            raise RuntimeError("error: generated book does not use the container-only surface")
        author_toml = (first / "book.toml").read_text(encoding="utf-8")
        author_config = tomllib.loads(author_toml)
        resolved_config = load_author_config(first)
        scaffold = json.loads((first / ".alkahest/scaffold.json").read_text(encoding="utf-8"))
        if (
            author_config["book"]["title"] != values["title"]
            or resolved_config["book"]["author"] != values["author"]
            or scaffold["book"]["id"] != values["book_id"]
        ):
            raise RuntimeError("error: generated book metadata is not independent")
        if (
            "identifier" in author_config["book"]
            or "content" in author_config
            or "theme" in author_config
        ):
            raise RuntimeError("error: book.toml exposes managed project details")
        if resolved_config["content"]["chapter_directory"] != "manuscript/chapters":
            raise RuntimeError("error: managed content defaults were not restored")
        with patch.dict("os.environ", {"QUARTO": sys.executable}):
            environment = doctor(first)
        if environment["mode"] != "local" or environment["chapters"] != 1:
            raise RuntimeError("error: author doctor did not report the usable renderer")
        chapter = add_chapter(first, "A Second Chapter")
        discovered = discover_content(first, load_author_config(first))
        if chapter.name != "02-a-second-chapter.qmd" or len(discovered["chapters"]) != 2:
            raise RuntimeError("error: chapter command did not update automatic ordering")
        expect_failure(
            "existing-destination",
            "already exists",
            lambda: create_new_book(ROOT, first, **values),
        )
        containerfile = first / "Containerfile"
        containerfile.write_text(
            containerfile.read_text().replace(
                scaffold["engine"]["image"], "localhost/wrong-engine:development"
            ),
            encoding="utf-8",
        )
        expect_failure(
            "image-drift",
            "does not pin its engine image",
            lambda: validate_scaffold(first),
        )

        base_toml = (second / "book.toml").read_text(encoding="utf-8")

        def toml_failure(name, expected, content):
            (second / "book.toml").write_text(content, encoding="utf-8")
            try:
                expect_failure(name, expected, lambda: validate_scaffold(second))
            finally:
                (second / "book.toml").write_text(base_toml, encoding="utf-8")

        toml_failure(
            "unknown-author-field", "book.toml fields differ", "unexpected = true\n" + base_toml
        )
        toml_failure(
            "author-language",
            "language tag",
            base_toml.replace('language = "en-GB"', 'language = "English"'),
        )
        toml_failure(
            "missing-excerpt",
            "missing chapter",
            base_toml.replace("01-first-chapter.qmd", "02-missing.qmd"),
        )
        toml_failure(
            "unknown-theme",
            "unknown field",
            base_toml + '\n[theme.colors]\nmystery = "#000000"\n',
        )
        scaffold_path = second / ".alkahest/scaffold.json"
        base_scaffold = scaffold_path.read_text(encoding="utf-8")
        invalid_identity = json.loads(base_scaffold)
        invalid_identity["book"]["excerpt_identifier"] = invalid_identity["book"]["identifier"]
        scaffold_path.write_text(
            json.dumps(invalid_identity, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        try:
            expect_failure(
                "managed-identifiers",
                "identifiers must differ",
                lambda: validate_scaffold(second),
            )
        finally:
            scaffold_path.write_text(base_scaffold, encoding="utf-8")
        invalid_chapter = second / "manuscript/chapters/not-numbered.qmd"
        invalid_chapter.write_text("# Invalid\n", encoding="utf-8")
        try:
            expect_failure(
                "chapter-filename",
                "NN-kebab-case.qmd",
                lambda: validate_scaffold(second),
            )
        finally:
            invalid_chapter.unlink()

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
        "(compact author config, diagnostics, deterministic identity, and chapters; "
        "7 input and 9 author/filesystem/integrity failures rejected)"
    )


def test_contract():
    result = main()
    assert result in (None, 0)
