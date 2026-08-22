"""Parse complete book structures and enforce edition policy."""

import re
from pathlib import Path

from .common import fail, load_json


REQUIRED_EDITIONS = (
    "abridged", "epub", "full", "preview", "print", "private", "public",
    "supplemental", "web",
)
REQUIRED_STRUCTURES = ("abridged", "full", "preview", "private", "supplemental", "web")


def _same_set(actual, expected):
    return len(actual) == len(expected) and set(actual) == set(expected)


def structure_source_ids(registry, structure_name):
    structure = registry.get("structures", {}).get(structure_name)
    if structure is None:
        fail(f"unknown edition structure '{structure_name}'")
    result = []
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
    return [registry["sources"][item]["path"] for item in edition_source_ids(registry, edition_name)]


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
            or source["availability"] == "private" and source["role"] == "chapter"
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
                ids = [item["source"]]
            else:
                part = item.get("part", "")
                if not re.fullmatch(r"[A-Za-z][A-Za-z0-9 -]*", part) or part in parts:
                    fail(f"structure '{name}' has an invalid or duplicate part")
                parts.add(part)
                ids = item.get("sources")
                if not isinstance(ids, list) or not ids:
                    fail(f"structure '{name}' part '{part}' has no sources")
            for source_id in ids:
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
        if not isinstance(edition.get("formats"), list) or not _same_set(edition["formats"], output_formats):
            fail(f"edition '{name}' has invalid formats")
        for source_id in structure_sets[structure]:
            for output_format in edition["formats"]:
                if output_format not in sources[source_id]["formats"]:
                    fail(f"edition '{name}' selects '{source_id}', which does not support {output_format}")
            if access == "public" and sources[source_id]["availability"] == "private":
                fail(f"public edition '{name}' includes private source '{source_id}'")

    availability_sets = {
        availability: {key for key, value in sources.items() if value["availability"] == availability}
        for availability in availabilities
    }
    for structure, classes in (
        ("full", ("core",)), ("web", ("core", "online-only")),
        ("supplemental", ("core", "supplemental")), ("private", ("core", "private")),
    ):
        wanted = set().union(*(availability_sets[item] for item in classes))
        if structure_sets[structure] != wanted:
            fail(f"structure '{structure}' does not select exactly its allowed availability classes")
    for structure in ("abridged", "preview"):
        for source_id in structure_sets[structure]:
            if sources[source_id]["availability"] != "core":
                fail(f"structure '{structure}' includes exceptional source '{source_id}'")
        if not structure_sets[structure] or len(structure_sets[structure]) >= len(structure_sets["full"]):
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
