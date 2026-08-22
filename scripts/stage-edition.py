"""Generate a disposable Quarto project containing exactly one book edition."""

import json
import os
import re
import shutil
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR / "lib"))

from alkahest.common import ContractError, fail
from alkahest.editions import edition_paths, load_editions, render_book_structure


def selected_media_files(book_root, source_paths):
    """Return rich-media files referenced by selected manuscript sources."""
    calls = set()
    for relative in source_paths:
        content = (book_root / relative).read_text(encoding="utf-8")
        calls.update(
            re.findall(
                r"\{\{<\s+alk-media\s+(media-[a-z0-9-]+)\s*>\}\}", content
            )
        )
    try:
        registry = json.loads((book_root / "media.json").read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        fail(f"cannot load rich-media registry: {error}")
    items = registry.get("items", {})
    files = set()
    for identifier in calls:
        item = items.get(identifier)
        if not isinstance(item, dict):
            fail(f"selected source references unknown rich-media item '{identifier}'")
        for field in ("asset", "fallback", "transcript", "captions"):
            value = item.get(field)
            if value is not None:
                resource = Path(value) if isinstance(value, str) else None
                if (
                    resource is None
                    or resource.is_absolute()
                    or not resource.parts
                    or resource.parts[0] != "media"
                    or ".." in resource.parts
                ):
                    fail(f"rich-media item '{identifier}' has unsafe {field}")
                files.add(value)
    return sorted(files)


def stage_resource_files(book_root, stage_root, relative_paths):
    """Copy selected resources so Quarto can traverse its project glob."""
    for relative in relative_paths:
        source = book_root / relative
        if not source.is_file():
            fail(f"selected resource does not exist: {relative}")
        destination = stage_root / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, destination)


def main():
    valid_options = len(sys.argv) in (2, 3) and (
        len(sys.argv) == 2 or sys.argv[2] == "--html-resources"
    )
    if not valid_options or not re.fullmatch(r"[a-z][a-z0-9-]*", sys.argv[1]):
        print(f"usage: {sys.argv[0]} EDITION [--html-resources]", file=sys.stderr)
        raise SystemExit(2)
    edition_name = sys.argv[1]
    materialize_html_resources = len(sys.argv) == 3
    book_root = SCRIPT_DIR.parent / "book"
    registry = load_editions(book_root / "editions.json")
    if edition_name not in registry["editions"]:
        fail(f"unknown edition '{edition_name}'")
    source_paths = edition_paths(registry, edition_name)
    html_resources = (
        selected_media_files(book_root, source_paths)
        if materialize_html_resources
        else []
    )
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
        # Quarto follows explicitly referenced files but does not expand a
        # resource glob through a symlinked directory. Selected real files keep
        # web media discoverable without copying assets from omitted chapters.
        if materialize_html_resources and entry.name == "media" and entry.is_dir():
            stage_resource_files(book_root, stage_root, html_resources)
            continue
        (stage_root / entry.name).symlink_to(Path("../../../../") / entry.name)
    for relative in source_paths:
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
