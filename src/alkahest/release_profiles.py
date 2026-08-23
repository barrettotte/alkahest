"""Resolve reusable full/preview profiles and stage isolated releases."""

import hashlib
import json
import os
import re
import shutil
import unicodedata
import uuid
from pathlib import Path, PurePosixPath


PROFILE_NAMES = ("full", "preview")
FORMATS = ("html", "epub", "typst", "latex")
ROLES = ("front", "chapter", "back", "appendix")
AVAILABILITIES = ("release", "supplemental", "private")
SOURCE_ID = re.compile(r"[a-z][a-z0-9-]*")
SOURCE_PATH = re.compile(
    r"(?:[a-z0-9][a-z0-9-]*/)*[a-z0-9][a-z0-9-]*\.qmd"
)
OUTPUT_PATHS = (
    "_quarto-release-full.yml",
    "_quarto-release-preview.yml",
    "generated/release-profile-manifest.json",
)
PRESENTATION_FIELDS = (
    "label",
    "message",
    "full_edition_label",
    "full_edition_url",
    "purchase_label",
    "purchase_url",
    "links_pending",
    "watermark",
)


class ReleaseProfileError(RuntimeError):
    """A user-facing release-profile contract violation."""


def _fail(message):
    raise ReleaseProfileError(f"error: {message}")


def _sha256(content):
    return hashlib.sha256(content).hexdigest()


def _json(document):
    return (json.dumps(document, indent=2, sort_keys=True) + "\n").encode("utf-8")


def _yaml_string(value):
    return json.dumps(value, ensure_ascii=False)


def _exact(value, fields, label):
    if not isinstance(value, dict) or set(value) != set(fields):
        _fail(f"{label} fields differ from the version 1 contract")
    return value


def _plain(value, label, allow_empty=False):
    if not isinstance(value, str) or (not value and not allow_empty):
        _fail(f"{label} must be {'a string' if allow_empty else 'nonempty'}")
    if value != value.strip() or any(
        unicodedata.category(character) == "Cc" for character in value
    ):
        _fail(f"{label} must be one line without surrounding whitespace")
    return value


def _load(content, label):
    try:
        return json.loads(content.decode("utf-8"))
    except (UnicodeError, json.JSONDecodeError) as error:
        _fail(f"invalid {label} JSON: {error}")


def _validate_url(value, label):
    _plain(value, label, allow_empty=True)
    if value and re.fullmatch(r"https://[^\s]+", value) is None:
        _fail(f"{label} must be empty or use HTTPS")


def _validate_identifier(value, label):
    _plain(value, label)
    if not value.startswith("urn:uuid:"):
        _fail(f"{label} must be a UUID URN")
    try:
        uuid.UUID(value.removeprefix("urn:uuid:"))
    except ValueError:
        _fail(f"{label} must be a UUID URN")


def validate_documents(defaults, local):
    """Validate and resolve shared behavior plus one book's release choices."""
    _exact(defaults, {"schema_version", "profiles"}, "release defaults")
    if defaults["schema_version"] != 1:
        _fail("release defaults schema_version must be 1")
    default_profiles = _exact(
        defaults["profiles"], PROFILE_NAMES, "release default profiles"
    )
    for name in PROFILE_NAMES:
        profile = _exact(
            default_profiles[name], {"formats", "preview"}, f"{name} defaults"
        )
        expected_formats = list(FORMATS if name == "full" else FORMATS[:-1])
        if profile["formats"] != expected_formats:
            _fail(f"{name} default formats must be {', '.join(expected_formats)}")
        preview = _exact(
            profile["preview"],
            {"enabled", *PRESENTATION_FIELDS},
            f"{name} preview defaults",
        )
        if preview["enabled"] is not (name == "preview"):
            _fail(f"{name} preview enabled default is invalid")
        for field in PRESENTATION_FIELDS[:-1]:
            _plain(
                preview[field],
                f"{name} preview {field}",
                allow_empty=field.endswith("_url"),
            )
        for field in ("full_edition_url", "purchase_url"):
            _validate_url(preview[field], f"{name} preview {field}")
        watermark = _exact(
            preview["watermark"], {"enabled", "text"}, f"{name} watermark"
        )
        if not isinstance(watermark["enabled"], bool):
            _fail(f"{name} watermark enabled must be boolean")
        _plain(watermark["text"], f"{name} watermark text")

    _exact(local, {"schema_version", "sources", "profiles"}, "book releases")
    if local["schema_version"] != 1:
        _fail("book releases schema_version must be 1")
    sources = local["sources"]
    if not isinstance(sources, dict) or not sources:
        _fail("book releases must register manuscript sources")
    paths = set()
    for source_id, source in sorted(sources.items()):
        if SOURCE_ID.fullmatch(source_id) is None:
            _fail(f"invalid release source ID '{source_id}'")
        _exact(source, {"path", "role", "availability"}, f"source {source_id}")
        if not isinstance(source["path"], str) or SOURCE_PATH.fullmatch(
            source["path"]
        ) is None:
            _fail(f"source {source_id} has an invalid path")
        if source["path"] in paths:
            _fail(f"release source path is registered twice: {source['path']}")
        paths.add(source["path"])
        if source["role"] not in ROLES:
            _fail(f"source {source_id} has an invalid role")
        if source["availability"] not in AVAILABILITIES:
            _fail(f"source {source_id} has an invalid availability")

    profiles = _exact(local["profiles"], PROFILE_NAMES, "book release profiles")
    resolved = {"schema_version": 1, "sources": sources, "profiles": {}}
    selected = {}
    identifiers = set()
    for name in PROFILE_NAMES:
        profile = _exact(
            profiles[name],
            {"chapters", "appendices", "metadata", "presentation"},
            f"book {name} profile",
        )
        metadata = _exact(
            profile["metadata"],
            {"subtitle", "description", "edition", "identifier"},
            f"book {name} metadata",
        )
        for field in ("subtitle", "description", "edition"):
            _plain(metadata[field], f"book {name} metadata {field}")
        _validate_identifier(metadata["identifier"], f"book {name} identifier")
        if metadata["identifier"] in identifiers:
            _fail("full and preview releases need distinct identifiers")
        identifiers.add(metadata["identifier"])
        presentation = profile["presentation"]
        if not isinstance(presentation, dict) or not set(presentation) <= set(
            PRESENTATION_FIELDS
        ):
            _fail(f"book {name} presentation contains an unknown field")
        for field, value in presentation.items():
            if field == "watermark":
                if not isinstance(value, dict) or not set(value) <= {"enabled", "text"}:
                    _fail(f"book {name} watermark contains an unknown field")
                if "enabled" in value and not isinstance(value["enabled"], bool):
                    _fail(f"book {name} watermark enabled must be boolean")
                if "text" in value:
                    _plain(value["text"], f"book {name} watermark text")
            else:
                _plain(
                    value,
                    f"book {name} presentation {field}",
                    allow_empty=field.endswith("_url"),
                )
                if field.endswith("_url"):
                    _validate_url(value, f"book {name} presentation {field}")
        preview = dict(default_profiles[name]["preview"])
        preview["watermark"] = dict(preview["watermark"])
        for field, value in presentation.items():
            if field == "watermark":
                preview["watermark"].update(value)
            else:
                preview[field] = value

        chosen = []
        for section, wanted_role in (("chapters", None), ("appendices", "appendix")):
            values = profile[section]
            if not isinstance(values, list) or len(values) != len(set(values)):
                _fail(f"book {name} {section} must be a unique array")
            for source_id in values:
                if source_id not in sources:
                    _fail(f"book {name} references unknown source '{source_id}'")
                is_appendix = sources[source_id]["role"] == "appendix"
                if is_appendix != (wanted_role == "appendix"):
                    _fail(f"book {name} places source '{source_id}' in the wrong section")
                if sources[source_id]["availability"] != "release":
                    _fail(f"book {name} selects non-release source '{source_id}'")
                chosen.append(source_id)
        if not profile["chapters"]:
            _fail(f"book {name} must select at least one non-appendix source")
        selected[name] = chosen
        resolved["profiles"][name] = {
            "formats": default_profiles[name]["formats"],
            "chapters": list(profile["chapters"]),
            "appendices": list(profile["appendices"]),
            "metadata": dict(metadata),
            "preview": preview,
        }

    release_sources = {
        source_id
        for source_id, source in sources.items()
        if source["availability"] == "release"
    }
    if set(selected["full"]) != release_sources:
        _fail("full release must select every source with release availability")
    if not set(selected["preview"]) <= set(selected["full"]):
        _fail("preview release must be a subset of the full release")
    preview_chapters = sum(
        sources[source_id]["role"] == "chapter" for source_id in selected["preview"]
    )
    if not 1 <= preview_chapters <= 2:
        _fail("preview release must select one or two manuscript chapters")
    return resolved


def _profile_yaml(name, profile):
    quote = _yaml_string
    metadata = profile["metadata"]
    preview = profile["preview"]
    watermark = preview["watermark"]
    return f"""# Generated from shared release defaults and book/releases.json; do not edit.
book:
  subtitle: {quote(metadata['subtitle'])}
  description: {quote(metadata['description'])}
subtitle: {quote(metadata['subtitle'])}
description: {quote(metadata['description'])}
identifier: {quote(metadata['identifier'])}

alkahest:
  edition: {quote(metadata['edition'])}
  identifier: {quote(metadata['identifier'])}
  release:
    profile: {name}
    formats: {json.dumps(profile['formats'])}
  preview:
    enabled: {str(preview['enabled']).lower()}
    label: {quote(preview['label'])}
    message: {quote(preview['message'])}
    full-edition-label: {quote(preview['full_edition_label'])}
    full-edition-url: {quote(preview['full_edition_url'])}
    purchase-label: {quote(preview['purchase_label'])}
    purchase-url: {quote(preview['purchase_url'])}
    links-pending: {quote(preview['links_pending'])}
    watermark:
      enabled: {str(watermark['enabled']).lower()}
      text: {quote(watermark['text'])}
""".encode("utf-8")


def release_outputs(defaults_content, local_content):
    """Return resolved release facts and deterministic Quarto profile bytes."""
    defaults = _load(defaults_content, "release defaults")
    local = _load(local_content, "book releases")
    resolved = validate_documents(defaults, local)
    outputs = {
        f"_quarto-release-{name}.yml": _profile_yaml(name, resolved["profiles"][name])
        for name in PROFILE_NAMES
    }
    manifest = {
        "schema_version": 1,
        "defaults_sha256": _sha256(defaults_content),
        "book_sha256": _sha256(local_content),
        "profiles": resolved["profiles"],
        "sources": resolved["sources"],
        "outputs": [
            {"path": path, "sha256": _sha256(content), "bytes": len(content)}
            for path, content in sorted(outputs.items())
        ],
    }
    outputs["generated/release-profile-manifest.json"] = _json(manifest)
    return resolved, outputs


def project_release_paths(root):
    """Locate canonical or installed release defaults for one repository."""
    book = Path(root) / "book"
    candidates = (
        book / "alkahest-release-defaults.json",
        book / ".alkahest/release-defaults.json",
    )
    defaults = next((path for path in candidates if path.is_file()), None)
    if defaults is None:
        _fail("book is missing installed Alkahest release defaults")
    return book, defaults, book / "releases.json"


def sync_project_releases(root, check=False):
    """Write or exactly verify one project's derived release profiles."""
    book, defaults_path, local_path = project_release_paths(root)
    try:
        defaults_content = defaults_path.read_bytes()
        local_content = local_path.read_bytes()
    except OSError as error:
        _fail(f"cannot read book release inputs: {error}")
    resolved, outputs = release_outputs(defaults_content, local_content)
    if check:
        for relative, expected in outputs.items():
            path = book / relative
            if not path.is_file() or path.read_bytes() != expected:
                _fail(f"generated release profile is missing or stale: book/{relative}")
    else:
        for relative, content in outputs.items():
            path = book / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(content)
    return {"resolved": resolved, "outputs": len(outputs), "check": check}


def _selected_media_files(book, source_paths):
    calls = set()
    for relative in source_paths:
        content = (book / relative).read_text(encoding="utf-8")
        calls.update(
            re.findall(r"\{\{<\s+alk-media\s+(media-[a-z0-9-]+)\s*>\}\}", content)
        )
    registry_path = book / "media.json"
    if not registry_path.is_file():
        return []
    registry = _load(registry_path.read_bytes(), "rich-media registry")
    files = set()
    for identifier in calls:
        item = registry.get("items", {}).get(identifier)
        if not isinstance(item, dict):
            _fail(f"selected source references unknown rich-media item '{identifier}'")
        for field in ("asset", "fallback", "transcript", "captions"):
            value = item.get(field)
            if value is None:
                continue
            path = PurePosixPath(value) if isinstance(value, str) else None
            if (
                path is None
                or path.is_absolute()
                or not path.parts
                or path.parts[0] != "media"
                or ".." in path.parts
            ):
                _fail(f"rich-media item '{identifier}' has unsafe {field}")
            files.add(value)
    return sorted(files)


def _render_structure(resolved, name):
    profile = resolved["profiles"][name]
    sources = resolved["sources"]
    lines = ["  chapters:"]
    lines.extend(f"    - {sources[item]['path']}" for item in profile["chapters"])
    if profile["appendices"]:
        lines.append("  appendices:")
        lines.extend(f"    - {sources[item]['path']}" for item in profile["appendices"])
    return "\n".join(lines) + "\n\n"


def stage_project_release(root, name, html_resources=False):
    """Create an isolated project containing exactly one release allowlist."""
    if name not in PROFILE_NAMES:
        _fail(f"unknown release profile '{name}'")
    root = Path(root).resolve()
    result = sync_project_releases(root, check=True)
    resolved = result["resolved"]
    book = root / "book"
    selected_ids = (
        resolved["profiles"][name]["chapters"]
        + resolved["profiles"][name]["appendices"]
    )
    source_paths = [resolved["sources"][item]["path"] for item in selected_ids]
    staging_parent = book / "_build" / "staging" / "releases"
    stage = staging_parent / name
    if stage.parent != staging_parent:
        _fail("unsafe release staging path")
    if stage.exists() or stage.is_symlink():
        shutil.rmtree(stage)
    stage.mkdir(parents=True)
    registered_top = {
        PurePosixPath(source["path"]).parts[0]
        for source in resolved["sources"].values()
    }
    media_files = _selected_media_files(book, source_paths) if html_resources else []
    skip = {".quarto", "_build", "_quarto.yml", "site_libs"}
    generated = re.compile(r"^(?:index\.(?:html|log|tex|typ)|.*\.(?:epub|pdf))$")
    for entry in sorted(book.iterdir(), key=lambda path: path.name):
        if (
            entry.name in skip
            or entry.name in registered_top
            or entry.name.endswith("_files")
            or generated.fullmatch(entry.name)
        ):
            continue
        if html_resources and entry.name == "media" and entry.is_dir():
            for relative in media_files:
                source = book / relative
                if not source.is_file():
                    _fail(f"selected resource does not exist: {relative}")
                destination = stage / relative
                destination.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(source, destination)
            continue
        (stage / entry.name).symlink_to(Path("../../../../") / entry.name)
    for relative in source_paths:
        source = book / relative
        if not source.is_file():
            _fail(f"release source does not exist: {relative}")
        destination = stage / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.symlink_to(Path(os.path.relpath(source, destination.parent)))
    config_path = book / "_quarto.yml"
    config = config_path.read_text(encoding="utf-8")
    config, replacements = re.subn(
        r"^  chapters:\n.*?(?=^\S)",
        lambda _: _render_structure(resolved, name),
        config,
        count=1,
        flags=re.M | re.S,
    )
    if replacements != 1:
        _fail("canonical Quarto config has no replaceable book structure")
    config = config.replace("../scripts/", "../../../../../scripts/")
    (stage / "_quarto.yml").write_text(config, encoding="utf-8")
    return {
        "stage": stage,
        "sources": source_paths,
        "profile": resolved["profiles"][name],
    }


def validate_project_releases(root, check_outputs=True):
    """Validate paths, source coverage, and optionally exact adapters."""
    root = Path(root)
    result = sync_project_releases(root, check=check_outputs)
    book = root / "book"
    registered = {source["path"] for source in result["resolved"]["sources"].values()}
    actual = {
        path.relative_to(book).as_posix()
        for path in book.rglob("*.qmd")
        if "_build" not in path.relative_to(book).parts
    }
    if actual != registered:
        missing = sorted(actual - registered)
        stale = sorted(registered - actual)
        detail = missing[0] if missing else stale[0]
        _fail(f"release source registry does not exactly cover manuscripts: {detail}")
    return result
