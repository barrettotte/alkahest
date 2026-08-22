"""Validate new-book policy and smoke-test a deterministic generated project."""

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
from alkahest.release_profiles import stage_project_release


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
    if b"--profile release-preview,epub" not in first["Makefile"]:
        raise RuntimeError("error: new-book preview profile precedence is incorrect")
    if b"alkahest-preview-placeholder" not in first["book/index.qmd"]:
        raise RuntimeError("error: new-book preview notice placeholder is missing")
    with tempfile.TemporaryDirectory(prefix="alkahest-new-book-check.") as temporary:
        destination = Path(temporary) / "small-book"
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
        full = stage_project_release(destination, "full")
        preview = stage_project_release(destination, "preview")
        if (
            full["sources"] != ["index.qmd", "chapter-01.qmd", "references.qmd"]
            or preview["sources"] != full["sources"]
            or not (preview["stage"] / "chapter-01.qmd").is_symlink()
        ):
            raise RuntimeError("error: generated-book release staging is inconsistent")
    print(
        "ok: new-book generator "
        f"({facts['files']} files; {facts['engine_files']} installed engine files; "
        f"version {policy['generator']['version']}; deterministic release smoke passed)"
    )


if __name__ == "__main__":
    try:
        main()
    except (ContractError, OSError, RuntimeError, UnicodeError) as error:
        print(error, file=sys.stderr)
        raise SystemExit(1)
