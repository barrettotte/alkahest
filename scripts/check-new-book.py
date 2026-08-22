"""Validate new-book policy and smoke-test a deterministic generated project."""

import json
import subprocess
import sys
import tempfile
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR / "lib"))

from alkahest.common import ContractError
from alkahest.new_book import (
    create_new_book,
    load_new_book_policy,
    normalize_book_options,
    scaffold_members,
    validate_new_book_integration,
    validate_scaffold,
)
ROOT = SCRIPT_DIR.parent


def main():
    policy = load_new_book_policy(ROOT)
    validate_new_book_integration(ROOT)
    options = normalize_book_options(
        ROOT,
        title="A Small Independent Book",
        author="Example Author",
        created="2026-08-22",
    )
    first = scaffold_members(ROOT, options)
    second = scaffold_members(ROOT, options)
    if first != second:
        raise RuntimeError("error: new-book scaffold is not deterministic")
    if b"excerpt: ##" not in first["Makefile"] or b"book.toml" not in first["README.md"]:
        raise RuntimeError("error: new-book concise author workflow is incomplete")
    if b"alkahest-preview-placeholder" not in first["manuscript/index.qmd"]:
        raise RuntimeError("error: new-book preview notice placeholder is missing")
    with tempfile.TemporaryDirectory(prefix="alkahest-new-book-check.") as temporary:
        destination = Path(temporary) / "small-book"
        second_destination = Path(temporary) / "second-book"
        result = create_new_book(
            ROOT,
            destination,
            title=options["title"],
            author=options["author"],
            created=options["created"],
        )
        facts = validate_scaffold(destination, first)
        if result["files"] != facts["files"]:
            raise RuntimeError("error: new-book result file count is inconsistent")
        subprocess.run(
            [sys.executable, ".alkahest/alkahest.py", "check"],
            cwd=destination,
            check=True,
            capture_output=True,
            text=True,
        )
        full = json.loads(
            (destination / "_build/.work/full/author-workspace.json").read_text()
        )
        excerpt = json.loads(
            (destination / "_build/.work/excerpt/author-workspace.json").read_text()
        )
        if (
            full["sources"]
            != [
                "manuscript/index.qmd",
                "manuscript/chapters/01-first-chapter.qmd",
                "manuscript/references.qmd",
            ]
            or excerpt["sources"] != full["sources"]
            or facts["chapters"] != 1
        ):
            raise RuntimeError("error: generated-book author workspace is inconsistent")
        second_result = create_new_book(
            ROOT,
            second_destination,
            title="A Different Tiny Book",
            author="Second Example",
            created="2026-08-22",
        )
        second_facts = validate_scaffold(second_destination)
        first_scaffold = json.loads(
            (destination / ".alkahest/scaffold.json").read_text()
        )
        second_scaffold = json.loads(
            (second_destination / ".alkahest/scaffold.json").read_text()
        )
        if (
            second_result["files"] != facts["files"]
            or second_facts["chapters"] != 1
            or first_scaffold["engine"]["archive_sha256"]
            != second_scaffold["engine"]["archive_sha256"]
            or (destination / "book.toml").read_bytes()
            == (second_destination / "book.toml").read_bytes()
        ):
            raise RuntimeError("error: second tiny book does not share the engine cleanly")
    print(
        "ok: new-book generator "
        f"({facts['files']} committed files; {facts['engine_files']} pinned engine archive; "
        f"{facts['engine_members']} managed members; version {policy['generator']['version']}; "
        "two-book author-workspace smoke passed)"
    )


if __name__ == "__main__":
    try:
        main()
    except (ContractError, OSError, RuntimeError, UnicodeError) as error:
        print(error, file=sys.stderr)
        raise SystemExit(1)
