"""Parse, validate, and stage complete book editions."""

import json
import os
import re
import shutil
from pathlib import Path

from .common import fail, load_json, qmd_sources

REQUIRED_EDITIONS = (
    "abridged",
    "epub",
    "full",
    "preview",
    "print",
    "private",
    "public",
    "supplemental",
    "web",
)
REQUIRED_STRUCTURES = ("abridged", "full", "preview", "private", "supplemental", "web")


def _same_set(actual, expected):
    return len(actual) == len(expected) and set(actual) == set(expected)


def structure_source_ids(registry, structure_name):
    structure = registry.get("structures", {}).get(structure_name)
    if structure is None:
        fail(f"unknown edition structure '{structure_name}'")
    result: list[str] = []
    for item in structure["chapters"]:
        result.extend([item["source"]] if "source" in item else item["sources"])
    for group in structure["appendices"]:
        result.extend(group["sources"])
    return result


def edition_source_ids(registry, edition_name):
    edition = registry.get("editions", {}).get(edition_name)
    if edition is None:
        fail(f"unknown edition '{edition_name}'")
    return structure_source_ids(registry, edition["structure"])


def edition_paths(registry, edition_name):
    return [
        registry["sources"][item]["path"] for item in edition_source_ids(registry, edition_name)
    ]


def _render_items(registry, items, indent):
    lines = []
    for item in items:
        if "source" in item:
            lines.append(" " * indent + "- " + registry["sources"][item["source"]]["path"])
        else:
            lines.append(" " * indent + f'- part: "{item["part"]}"')
            lines.append(" " * (indent + 2) + "chapters:")
            for source_id in item["sources"]:
                lines.append(" " * (indent + 4) + "- " + registry["sources"][source_id]["path"])
    return lines


def render_book_structure(registry, edition_name):
    edition = registry.get("editions", {}).get(edition_name)
    if edition is None:
        fail(f"unknown edition '{edition_name}'")
    structure = registry["structures"][edition["structure"]]
    lines = ["  chapters:"]
    lines.extend(_render_items(registry, structure["chapters"], 4))
    lines.append("  appendices:")
    for group in structure["appendices"]:
        lines.extend((f'    - part: "{group["part"]}"', "      chapters:"))
        for source_id in group["sources"]:
            lines.append("        - " + registry["sources"][source_id]["path"])
    return "\n".join(lines) + "\n\n"


def _selected_media_files(book_root, source_paths):
    calls = set()
    for relative in source_paths:
        content = (book_root / relative).read_text(encoding="utf-8")
        calls.update(re.findall(r"\{\{<\s+alk-media\s+(media-[a-z0-9-]+)\s*>\}\}", content))
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
            if value is None:
                continue
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


def _stage_resource_files(book_root, stage_root, relative_paths):
    for relative in relative_paths:
        source = book_root / relative
        if not source.is_file():
            fail(f"selected resource does not exist: {relative}")
        destination = stage_root / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, destination)


def stage_edition(book_root, edition_name, html_resources=False):
    """Create a disposable Quarto project containing exactly one edition."""
    book_root = Path(book_root).resolve()
    registry = load_editions(book_root / "editions.json")
    if edition_name not in registry["editions"]:
        fail(f"unknown edition '{edition_name}'")
    source_paths = edition_paths(registry, edition_name)
    media_files = _selected_media_files(book_root, source_paths) if html_resources else []
    staging_parent = book_root / "_build/staging/editions"
    stage_root = staging_parent / edition_name
    if stage_root.parent != staging_parent:
        fail("unsafe edition staging path")
    if stage_root.exists() or stage_root.is_symlink():
        shutil.rmtree(stage_root)
    stage_root.mkdir(parents=True)

    registered_top = {Path(item["path"]).parts[0] for item in registry["sources"].values()}
    skip = {".quarto", "_build", "_quarto.yml", "site_libs"}
    generated = re.compile(
        r"^(?:Alkahest-Reference-Book\.(?:epub|pdf)|index\.(?:html|log|tex|typ)|"
        r"reference\.html|references\.html)$"
    )
    for entry in sorted(book_root.iterdir(), key=lambda path: path.name):
        if (
            entry.name in skip
            or entry.name in registered_top
            or entry.name.endswith("_files")
            or generated.fullmatch(entry.name)
        ):
            continue
        # Quarto does not expand a resource glob through a symlinked media
        # directory, so HTML stages copy only media selected by this edition.
        if html_resources and entry.name == "media" and entry.is_dir():
            _stage_resource_files(book_root, stage_root, media_files)
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
    config, replacements = re.subn(
        r"^  chapters:\n.*?(?=^\S)",
        lambda _: structure,
        config,
        count=1,
        flags=re.MULTILINE | re.DOTALL,
    )
    if replacements != 1:
        fail("canonical Quarto config has no replaceable book structure")
    config = config.replace("../scripts/", "../../../../../scripts/")
    (stage_root / "_quarto.yml").write_text(config, encoding="utf-8")
    (stage_root / f"_quarto-edition-{edition_name}.yml").write_text(
        "# Generated from editions.json; do not edit.\n"
        f"alkahest:\n  content-edition: {edition_name}\n",
        encoding="utf-8",
    )
    return stage_root


def load_editions(path):
    registry = load_json(path, "edition manifest")
    if registry.get("version", 0) != 1:
        fail("edition manifest version must be 1")
    editions = registry.get("editions", {})
    structures = registry.get("structures", {})
    sources = registry.get("sources", {})
    if not _same_set(list(editions), REQUIRED_EDITIONS):
        fail("editions must be exactly: " + ", ".join(REQUIRED_EDITIONS))
    if not _same_set(list(structures), REQUIRED_STRUCTURES):
        fail("edition structures must be exactly: " + ", ".join(REQUIRED_STRUCTURES))

    roles = {"front", "chapter", "back", "appendix"}
    availabilities = {"core", "online-only", "supplemental", "private"}
    formats = {"html", "epub", "typst", "latex"}
    paths = set()
    for source_id in sorted(sources):
        if not re.fullmatch(r"[a-z][a-z0-9-]*", source_id):
            fail(f"invalid edition source ID '{source_id}'")
        source = sources[source_id]
        if not isinstance(source, dict):
            fail(f"edition source '{source_id}' must be an object")
        source_path = source.get("path", "")
        if not re.fullmatch(r"(?:[a-z0-9][a-z0-9-]*/)*[a-z0-9][a-z0-9-]*\.qmd", source_path):
            fail(f"invalid edition source path for '{source_id}'")
        if source_path in paths:
            fail(f"edition source path '{source_path}' is registered more than once")
        paths.add(source_path)
        if source.get("role", "") not in roles:
            fail(f"edition source '{source_id}' has invalid role")
        if source.get("availability", "") not in availabilities:
            fail(f"edition source '{source_id}' has invalid availability")
        source_formats = source.get("formats")
        if not isinstance(source_formats, list) or not source_formats:
            fail(f"edition source '{source_id}' must declare formats")
        seen = set()
        for output_format in source_formats:
            if output_format not in formats:
                fail(f"edition source '{source_id}' has unsupported format '{output_format}'")
            if output_format in seen:
                fail(f"edition source '{source_id}' repeats format '{output_format}'")
            seen.add(output_format)
        if source["availability"] != "core" and not (
            source["role"] == "appendix"
            or source["availability"] == "private"
            and source["role"] == "chapter"
        ):
            fail(f"non-core source '{source_id}' must be an appendix or private chapter")
    if not sources:
        fail("edition manifest has no sources")

    structure_sets = {}
    for name in REQUIRED_STRUCTURES:
        structure = structures[name]
        chapters = structure.get("chapters")
        appendices = structure.get("appendices")
        if not isinstance(chapters, list) or not chapters or not isinstance(appendices, list):
            fail(f"structure '{name}' must have chapters and appendices arrays")
        selected, parts = set(), set()
        for item in chapters:
            if not isinstance(item, dict):
                fail(f"structure '{name}' has an invalid chapter item")
            if "source" in item:
                if len(item) != 1:
                    fail(f"structure '{name}' direct chapter item is malformed")
                source_ids = [item["source"]]
            else:
                part = item.get("part", "")
                if not re.fullmatch(r"[A-Za-z][A-Za-z0-9 -]*", part) or part in parts:
                    fail(f"structure '{name}' has an invalid or duplicate part")
                parts.add(part)
                registered_sources = item.get("sources")
                if not isinstance(registered_sources, list) or not registered_sources:
                    fail(f"structure '{name}' part '{part}' has no sources")
                source_ids = registered_sources
            for source_id in source_ids:
                if source_id not in sources:
                    fail(f"structure '{name}' references unknown source '{source_id}'")
                if sources[source_id]["role"] == "appendix":
                    fail(f"structure '{name}' puts appendix '{source_id}' in chapters")
                if source_id in selected:
                    fail(f"structure '{name}' repeats source '{source_id}'")
                selected.add(source_id)
        for group in appendices:
            part = group.get("part", "")
            if not re.fullmatch(r"[A-Za-z][A-Za-z0-9 -]*", part) or part in parts:
                fail(f"structure '{name}' has an invalid or duplicate appendix part")
            parts.add(part)
            ids = group.get("sources")
            if not isinstance(ids, list) or not ids:
                fail(f"structure '{name}' appendix part '{part}' has no sources")
            for source_id in ids:
                if source_id not in sources:
                    fail(f"structure '{name}' references unknown appendix '{source_id}'")
                if sources[source_id]["role"] != "appendix":
                    fail(f"structure '{name}' puts non-appendix '{source_id}' in appendices")
                if source_id in selected:
                    fail(f"structure '{name}' repeats source '{source_id}'")
                selected.add(source_id)
        structure_sets[name] = selected

    expected = {
        "full": ("full", "public", ["html", "epub", "typst", "latex"]),
        "abridged": ("abridged", "public", ["html", "epub", "typst", "latex"]),
        "preview": ("preview", "public", ["html", "epub", "typst"]),
        "print": ("full", "public", ["typst", "latex"]),
        "epub": ("full", "public", ["epub"]),
        "web": ("web", "public", ["html"]),
        "public": ("full", "public", ["html", "epub", "typst", "latex"]),
        "private": ("private", "private", ["html"]),
        "supplemental": ("supplemental", "public", ["html"]),
    }
    for name in REQUIRED_EDITIONS:
        structure, access, output_formats = expected[name]
        edition = editions[name]
        if edition.get("structure", "") != structure:
            fail(f"edition '{name}' must use structure '{structure}'")
        if edition.get("access", "") != access:
            fail(f"edition '{name}' must have access '{access}'")
        if not isinstance(edition.get("formats"), list) or not _same_set(
            edition["formats"], output_formats
        ):
            fail(f"edition '{name}' has invalid formats")
        for source_id in structure_sets[structure]:
            for output_format in edition["formats"]:
                if output_format not in sources[source_id]["formats"]:
                    fail(
                        f"edition '{name}' selects '{source_id}', which does not support {output_format}"
                    )
            if access == "public" and sources[source_id]["availability"] == "private":
                fail(f"public edition '{name}' includes private source '{source_id}'")

    availability_sets = {
        availability: {
            key for key, value in sources.items() if value["availability"] == availability
        }
        for availability in availabilities
    }
    for structure, classes in (
        ("full", ("core",)),
        ("web", ("core", "online-only")),
        ("supplemental", ("core", "supplemental")),
        ("private", ("core", "private")),
    ):
        wanted = set().union(*(availability_sets[item] for item in classes))
        if structure_sets[structure] != wanted:
            fail(
                f"structure '{structure}' does not select exactly its allowed availability classes"
            )
    for structure in ("abridged", "preview"):
        for source_id in structure_sets[structure]:
            if sources[source_id]["availability"] != "core":
                fail(f"structure '{structure}' includes exceptional source '{source_id}'")
        if not structure_sets[structure] or len(structure_sets[structure]) >= len(
            structure_sets["full"]
        ):
            fail(f"structure '{structure}' must be a nonempty proper subset of full")
    chapter_count = {
        name: sum(sources[item]["role"] == "chapter" for item in structure_sets[name])
        for name in ("preview", "abridged", "full")
    }
    if not 1 <= chapter_count["preview"] <= 2:
        fail("preview structure must contain one or two manuscript chapters")
    if not chapter_count["preview"] < chapter_count["abridged"] < chapter_count["full"]:
        fail("abridged structure must contain more chapters than preview and fewer than full")
    return registry


def _visible_content(content, edition_name):
    pattern = rf'^:::\s+\{{\.content-visible\s+unless-profile="edition-{re.escape(edition_name)}"\}}\s*\n.*?^:::\s*$'
    return re.sub(pattern, "", content, flags=re.MULTILINE | re.DOTALL)


def validate_edition_book(book_root):
    """Validate whole-book edition structure, source metadata, and references."""
    from .preview import validate_preview_presentation

    book_root = Path(book_root).resolve()
    if not book_root.is_dir():
        fail("edition book root does not exist")
    registry = load_editions(book_root / "editions.json")
    preview = validate_preview_presentation(book_root.parent)
    config = (book_root / "_quarto.yml").read_text(encoding="utf-8")
    structure_match = re.search(r"(^  chapters:\n.*?)(?=^\S)", config, re.MULTILINE | re.DOTALL)
    if not structure_match:
        fail("canonical Quarto config has no book structure")
    if structure_match.group(1) != render_book_structure(registry, "full"):
        fail("canonical Quarto structure must match the full edition exactly")

    registered = {value["path"]: key for key, value in registry["sources"].items()}
    disk_sources = [path.relative_to(book_root).as_posix() for path in qmd_sources(book_root)]
    for source in sorted(disk_sources):
        if source not in registered:
            fail(f"manuscript source '{source}' is absent from editions.json")
    for source in sorted(registered):
        if not (book_root / source).is_file():
            fail(f"edition manifest references missing source '{source}'")
    if len(disk_sources) != len(registered):
        fail("edition manifest and manuscript tree contain different source counts")

    owners: dict[str, str] = {}
    for source in sorted(registered):
        source_id = registered[source]
        metadata = registry["sources"][source_id]
        content = (book_root / source).read_text(encoding="utf-8")
        front_match = re.match(r"\A---\s*\n(.*?)^---\s*$", content, re.MULTILINE | re.DOTALL)
        front_matter = front_match.group(1) if front_match else None
        if front_matter and re.search(r"^bibliography\s*:", front_matter, re.MULTILINE):
            fail(
                f"source '{source}' declares a local bibliography; use the shared book bibliography"
            )
        headings = re.findall(r"^(# (?!#).*?)$", content, re.MULTILINE)
        if len(headings) != 1 or not re.search(r"\{[^}]*#[A-Za-z][A-Za-z0-9_.:-]*", headings[0]):
            fail(f"source '{source}' must have exactly one H1 with a persistent ID")
        if metadata["availability"] == "private":
            if front_matter is None or not re.search(
                r"^alkahest-edition:\s*\n\s+access:\s*private\s*$", front_matter, re.MULTILINE
            ):
                fail(f"private source '{source}' must declare alkahest-edition access: private")
        elif front_matter and re.search(r"^alkahest-edition:", front_matter, re.MULTILINE):
            fail(f"public source '{source}' must not declare private edition metadata")
        if metadata["role"] == "appendix":
            declared_match = re.search(
                r"^alkahest-appendix:\s*\n\s+availability:\s*([a-z-]+)\s*$",
                front_matter or "",
                re.MULTILINE,
            )
            declared = declared_match.group(1) if declared_match else None
            if metadata["availability"] == "core" and declared is not None:
                fail(f"core appendix '{source}' must not declare exceptional availability")
            if metadata["availability"] != "core" and declared != metadata["availability"]:
                fail(f"appendix '{source}' must declare availability '{metadata['availability']}'")
        for identity in re.findall(r"\{[^}\n]*#([A-Za-z][A-Za-z0-9_.:-]*)", content):
            if identity in owners:
                fail(
                    f"content identity '{identity}' is declared in both '{source}' and '{owners[identity]}'"
                )
            owners[identity] = source

    for edition_name, edition in sorted(registry["editions"].items()):
        source_ids = edition_source_ids(registry, edition_name)
        selected = {registry["sources"][item]["path"] for item in source_ids}
        for source_id in source_ids:
            source = registry["sources"][source_id]["path"]
            content = _visible_content(
                (book_root / source).read_text(encoding="utf-8"), edition_name
            )
            for target in re.findall(r"@([A-Za-z][A-Za-z0-9_.:-]*)", content):
                if target in owners and owners[target] not in selected:
                    fail(
                        f"edition '{edition_name}' leaves dangling reference '@{target}' in '{source}'"
                    )
        if "index-backmatter.qmd" in selected:
            for line in (book_root / "index.yml").read_text(encoding="utf-8").splitlines():
                locator = re.fullmatch(r"\s+-\s+([A-Za-z0-9_/-]+\.qmd)#[A-Za-z0-9_.:-]+\s*", line)
                if locator and locator.group(1) not in selected:
                    fail(
                        f"edition '{edition_name}' retains index locator into omitted '{locator.group(1)}'"
                    )
        if edition["access"] == "public":
            for source_id in source_ids:
                if registry["sources"][source_id]["availability"] == "private":
                    fail(f"public edition '{edition_name}' includes private source '{source_id}'")
    return {
        "editions": len(registry["editions"]),
        "structures": len(registry["structures"]),
        "sources": len(registry["sources"]),
        "preview": preview,
    }
