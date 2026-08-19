"""Generate a disposable Quarto project containing exactly one book edition."""

import os
import re
import shutil
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR / "lib"))

from alkahest.common import ContractError, fail
from alkahest.editions import edition_paths, load_editions, render_book_structure


def main():
    if len(sys.argv) != 2 or not re.fullmatch(r"[a-z][a-z0-9-]*", sys.argv[1]):
        print(f"usage: {sys.argv[0]} EDITION", file=sys.stderr)
        raise SystemExit(2)
    edition_name = sys.argv[1]
    book_root = SCRIPT_DIR.parent / "book"
    registry = load_editions(book_root / "editions.json")
    if edition_name not in registry["editions"]:
        fail(f"unknown edition '{edition_name}'")
    staging_parent = book_root / "_build" / "staging" / "editions"
    stage_root = staging_parent / edition_name
    if stage_root.parent != staging_parent:
        fail("unsafe edition staging path")
    if stage_root.exists() or stage_root.is_symlink():
        shutil.rmtree(stage_root)
    stage_root.mkdir(parents=True)
    registered_top = {Path(item["path"]).parts[0] for item in registry["sources"].values()}
    skip = {".quarto", "_build", "_quarto.yml", "site_libs"}
    generated = re.compile(r"^(?:Alkahest-Reference-Book\.(?:epub|pdf)|index\.(?:html|log|tex|typ)|reference\.html|references\.html)$")
    for entry in sorted(book_root.iterdir(), key=lambda path: path.name):
        if entry.name in skip or entry.name in registered_top or entry.name.endswith("_files") or generated.fullmatch(entry.name):
            continue
        (stage_root / entry.name).symlink_to(Path("../../../../") / entry.name)
    for relative in edition_paths(registry, edition_name):
        source = book_root / relative
        if not source.is_file():
            fail(f"edition source does not exist: {relative}")
        destination = stage_root / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.symlink_to(Path(os.path.relpath(source, destination.parent)))
    config = (book_root / "_quarto.yml").read_text(encoding="utf-8")
    structure = render_book_structure(registry, edition_name)
    config, replacements = re.subn(r"^  chapters:\n.*?(?=^\S)", lambda _: structure, config, count=1, flags=re.M | re.S)
    if replacements != 1:
        fail("canonical Quarto config has no replaceable book structure")
    config = config.replace("../scripts/", "../../../../../scripts/")
    (stage_root / "_quarto.yml").write_text(config, encoding="utf-8")
    (stage_root / f"_quarto-edition-{edition_name}.yml").write_text(
        f"# Generated from editions.json; do not edit.\nalkahest:\n  content-edition: {edition_name}\n",
        encoding="utf-8",
    )
    print(stage_root)


if __name__ == "__main__":
    try:
        main()
    except (ContractError, OSError) as error:
        print(error if isinstance(error, ContractError) else f"error: {error}", file=sys.stderr)
        raise SystemExit(1)
