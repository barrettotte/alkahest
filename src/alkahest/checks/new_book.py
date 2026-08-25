"""Validate new-book policy and smoke-test a deterministic generated project."""

import json
import shutil
import sys
import tempfile
import tomllib
from pathlib import Path

from alkahest.author_project import TOOLCHAIN_IMAGE
from alkahest.common import ContractError
from alkahest.new_book import (
    create_new_book,
    load_new_book_policy,
    normalize_book_options,
    scaffold_members,
    validate_new_book_integration,
    validate_scaffold,
)
from alkahest.process import run_process

ROOT = Path(__file__).resolve().parents[3]


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
    if (
        b"doctor: ##" not in first["Makefile"]
        or b"bootstrap: ##" not in first["Makefile"]
        or b"build-all: ##" not in first["Makefile"]
        or b"--network=none" not in first["Makefile"]
        or b"book.toml" not in first["README.md"]
        or f"FROM {TOOLCHAIN_IMAGE}\n".encode() not in first["Containerfile"]
        or any(path.endswith((".zip", ".py")) for path in first)
    ):
        raise RuntimeError("error: new-book concise author workflow is incomplete")
    author_command = (ROOT / "scripts/author.py").read_text(encoding="utf-8")
    if (
        '"full", ["html", "epub", "typst"]' not in author_command
        or '"full", ["html", "epub", "typst", "latex"]' not in author_command
    ):
        raise RuntimeError("error: routine and advanced author builds are not separated")
    book_toml = tomllib.loads(first["book.toml"].decode("utf-8"))
    if (
        book_toml["schema_version"] != 2
        or "identifier" in book_toml["book"]
        or "content" in book_toml
        or "theme" in book_toml
    ):
        raise RuntimeError("error: generated book.toml exposes managed details")
    if b"alkahest-preview-placeholder" not in first["manuscript/index.qmd"]:
        raise RuntimeError("error: new-book preview notice placeholder is missing")
    guide = ROOT / "guide"
    guide_config = tomllib.loads((guide / "book.toml").read_text(encoding="utf-8"))
    guide_containerfile = (guide / "Containerfile").read_text(encoding="utf-8")
    guide_makefile = (guide / "Makefile").read_text(encoding="utf-8")
    if (
        guide_config["book"]["title"] != "Writing Books with Alkahest"
        or len(guide_config["excerpt"]["chapters"]) != 2
        or any((guide / ".alkahest").glob("*.zip"))
        or f"FROM {TOOLCHAIN_IMAGE}\n" not in guide_containerfile
        or 'ENTRYPOINT ["/opt/alkahest/tools/bin/python"' not in guide_containerfile
        or "bootstrap: ##" not in guide_makefile
        or "--network=none" not in guide_makefile
        or "UV ?=" in guide_makefile
    ):
        raise RuntimeError("error: checked-in author guide is stale or misconfigured")
    with tempfile.TemporaryDirectory(prefix="alkahest-new-book-check.") as temporary:
        temporary_root = Path(temporary)
        guide_smoke = temporary_root / "author-guide"
        shutil.copytree(
            guide,
            guide_smoke,
            ignore=shutil.ignore_patterns("_build", "cache", ".uv-cache", "__pycache__"),
        )
        run_process(
            [sys.executable, str(ROOT / "scripts/author.py"), "check"],
            cwd=guide_smoke,
            check=True,
            capture_output=True,
            text=True,
        )
        guide_manifest = json.loads(
            (guide_smoke / "_build/.work/full/author-workspace.json").read_text()
        )
        if len(guide_manifest["sources"]) != 7:
            raise RuntimeError("error: checked-in author guide source discovery is incomplete")
        guide_workspace = guide_smoke / "_build/.work/full"
        if (
            "theme/alkahest-fonts.css" not in (guide_workspace / "_quarto-html.yml").read_text()
            or "epub-fonts:" not in (guide_workspace / "_quarto-epub.yml").read_text()
        ):
            raise RuntimeError("error: author profiles do not package the locked web fonts")
        destination = temporary_root / "small-book"
        second_destination = temporary_root / "second-book"
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
        run_process(
            [sys.executable, str(ROOT / "scripts/author.py"), "check"],
            cwd=destination,
            check=True,
            capture_output=True,
            text=True,
        )
        help_result = run_process(
            ["make", "help"],
            cwd=destination,
            check=True,
            capture_output=True,
            text=True,
        )
        if not all(
            marker in help_result.stdout for marker in ("bootstrap", "doctor", "build", "build-all")
        ):
            raise RuntimeError("error: generated-book help is incomplete")
        full = json.loads((destination / "_build/.work/full/author-workspace.json").read_text())
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
        first_scaffold = json.loads((destination / ".alkahest/scaffold.json").read_text())
        second_scaffold = json.loads((second_destination / ".alkahest/scaffold.json").read_text())
        if (
            second_result["files"] != facts["files"]
            or second_facts["chapters"] != 1
            or first_scaffold["engine"]["image"] != second_scaffold["engine"]["image"]
            or first_scaffold["engine"]["image"] != TOOLCHAIN_IMAGE
            or (destination / "book.toml").read_bytes()
            == (second_destination / "book.toml").read_bytes()
        ):
            raise RuntimeError("error: second tiny book does not share the engine cleanly")
    print(
        "ok: new-book generator "
        f"({facts['files']} committed files; rootless image {facts['engine_image']}; "
        f"version {policy['generator']['version']}; "
        "two-book author-workspace and checked-in guide smoke passed)"
    )


if __name__ == "__main__":
    try:
        main()
    except (ContractError, OSError, RuntimeError, UnicodeError) as error:
        print(error, file=sys.stderr)
        raise SystemExit(1) from None
