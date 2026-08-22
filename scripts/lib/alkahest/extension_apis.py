"""Validate the shipped extension API inventory and documentation."""

import re
from pathlib import Path, PurePosixPath

from .common import fail, load_json


POLICY_PATH = "config/template/extension-apis.json"
DOCUMENTATION_PATH = "docs/extension-apis.md"
EXPECTED_IDS = (
    "appendices",
    "companions",
    "components",
    "controlled-reuse",
    "filters",
    "generated-lists",
    "generators",
    "glossary",
    "icon-themes",
    "indexes",
    "learning-blocks",
    "localization",
    "notes",
    "rich-media",
    "semantic-icons",
)
LEVELS = {"author", "book-config", "engine-maintainer", "maintainer-tooling"}


def _exact(value, fields, label):
    if not isinstance(value, dict) or set(value) != set(fields):
        fail(f"{label} fields differ from the version 1 contract")
    return value


def _path(value, label):
    if not isinstance(value, str) or not value:
        fail(f"{label} must be a normalized relative path")
    path = PurePosixPath(value)
    if path.is_absolute() or ".." in path.parts or str(path) != value:
        fail(f"{label} must be a normalized relative path")
    if path.parts[0] not in {"book", "config", "docs", "scripts"}:
        fail(f"{label} must remain in a governed source root")
    return value


def _string_array(value, label, allow_empty=False):
    if (
        not isinstance(value, list)
        or (not value and not allow_empty)
        or len(value) != len(set(value))
        or any(not isinstance(item, str) or not item or "\n" in item for item in value)
    ):
        fail(f"{label} must be a unique {'possibly empty ' if allow_empty else ''}string array")
    return value


def validate_extension_apis(root, document=None):
    """Validate the closed inventory, entrypoints, and shipped prose."""
    root = Path(root)
    document = document or load_json(root / POLICY_PATH, "extension API inventory")
    _exact(
        document,
        {"schema_version", "api_version", "stability", "entries"},
        "extension API inventory",
    )
    if document["schema_version"] != 1:
        fail("extension API schema_version must be 1")
    if not isinstance(document["api_version"], str) or re.fullmatch(
        r"(?:0|[1-9][0-9]*)\.(?:0|[1-9][0-9]*)\.(?:0|[1-9][0-9]*)",
        document["api_version"],
    ) is None:
        fail("extension API version must use semantic versioning")
    if document["stability"] != "provisional":
        fail("extension API stability must remain provisional until compatibility policy exists")
    entries = document["entries"]
    if not isinstance(entries, list) or not entries:
        fail("extension API entries must be a nonempty array")
    ids = [entry.get("id") if isinstance(entry, dict) else None for entry in entries]
    if len(ids) != len(set(ids)):
        fail("extension API IDs must be unique")
    if set(ids) != set(EXPECTED_IDS) or len(ids) != len(EXPECTED_IDS):
        fail("extension API IDs must be exactly: " + ", ".join(EXPECTED_IDS))

    documentation = (root / DOCUMENTATION_PATH).read_text(encoding="utf-8")
    anchors = set()
    by_id = {}
    all_entrypoints = set()
    for position, entry in enumerate(entries):
        api_id = ids[position]
        _exact(
            entry,
            {
                "id",
                "title",
                "level",
                "documentation_anchor",
                "entrypoints",
                "book_inputs",
                "author_markers",
            },
            f"extension API {api_id}",
        )
        if not isinstance(api_id, str) or re.fullmatch(r"[a-z][a-z0-9-]*", api_id) is None:
            fail(f"extension API {api_id!r} has an invalid ID")
        if not isinstance(entry["title"], str) or not entry["title"].strip():
            fail(f"extension API {api_id} needs a title")
        if entry["level"] not in LEVELS:
            fail(f"extension API {api_id} has an invalid authority level")
        anchor = entry["documentation_anchor"]
        if anchor != f"api-{api_id}" or anchor in anchors:
            fail(f"extension API {api_id} has an invalid or duplicate documentation anchor")
        anchors.add(anchor)
        if f"{{#{anchor}}}" not in documentation:
            fail(f"extension API documentation is missing anchor {anchor}")
        entrypoints = _string_array(entry["entrypoints"], f"extension API {api_id} entrypoints")
        inputs = _string_array(
            entry["book_inputs"], f"extension API {api_id} book inputs", allow_empty=True
        )
        markers = _string_array(entry["author_markers"], f"extension API {api_id} author markers")
        for marker in markers:
            if marker not in documentation:
                fail(f"extension API documentation is missing {api_id} marker {marker!r}")
        for relative in entrypoints + inputs:
            _path(relative, f"extension API {api_id} path")
            if not (root / relative).is_file():
                fail(f"extension API {api_id} path does not exist: {relative}")
        all_entrypoints.update(entrypoints)
        by_id[api_id] = entry

    manifests = {
        path.relative_to(root).as_posix()
        for path in (root / "book/_extensions").glob("*/_extension.yml")
    }
    covered_manifests = {
        path for path in all_entrypoints if path.endswith("/_extension.yml")
    }
    if manifests != covered_manifests:
        fail("extension API inventory does not exactly cover bundled extension manifests")
    filters = {
        path.relative_to(root).as_posix() for path in (root / "book/filters").glob("*.lua")
    }
    if set(by_id["filters"]["entrypoints"]) != filters:
        fail("filter API does not exactly cover portable Lua filters")
    generators = {
        path.relative_to(root).as_posix() for path in (root / "scripts").glob("generate-*.py")
    }
    if set(by_id["generators"]["entrypoints"]) != generators:
        fail("generator API does not exactly cover deterministic Python generators")
    return {
        "api_version": document["api_version"],
        "stability": document["stability"],
        "entries": len(entries),
        "levels": len({entry["level"] for entry in entries}),
        "manifests": len(manifests),
        "filters": len(filters),
        "generators": len(generators),
    }
