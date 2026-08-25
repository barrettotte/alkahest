"""Create and validate minimal book repositories for the rootless engine image."""

import json
import os
import re
import shutil
import tempfile
import unicodedata
import uuid
from datetime import UTC, date, datetime
from pathlib import Path, PurePosixPath

from .author_project import (
    TOOLCHAIN_IMAGE,
    AuthorProjectError,
    discover_content,
    load_author_config,
)
from .common import fail, load_json

POLICY_PATH = "config/template/new-book.json"
BOOK_ID = re.compile(r"[a-z0-9]+(?:-[a-z0-9]+)*")
LANGUAGE = re.compile(r"[A-Za-z]{2,3}(?:-[A-Za-z0-9]{2,8})*")
SEMVER = re.compile(r"(?:0|[1-9][0-9]*)\.(?:0|[1-9][0-9]*)\.(?:0|[1-9][0-9]*)")


def _exact(value, fields, label):
    if not isinstance(value, dict) or set(value) != set(fields):
        fail(f"{label} fields do not match the version 1 contract")
    return value


def _relative(value, label):
    if not isinstance(value, str) or not value:
        fail(f"{label} must be a normalized relative path")
    path = PurePosixPath(value)
    if path.is_absolute() or ".." in path.parts or str(path) != value:
        fail(f"{label} must be a normalized relative path")
    return value


def _json(document):
    return (json.dumps(document, indent=2, sort_keys=True) + "\n").encode("utf-8")


def _yaml_string(value):
    return json.dumps(value, ensure_ascii=False)


def _plain_text(value, label):
    if not isinstance(value, str) or not value.strip():
        fail(f"{label} must be nonempty")
    if value != value.strip():
        fail(f"{label} must not have leading or trailing whitespace")
    if any(unicodedata.category(character) == "Cc" for character in value):
        fail(f"{label} must be one line without control characters")
    return value


def _slug(value):
    normalized = unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9]+", "-", normalized.lower()).strip("-")


def load_new_book_policy(root):
    """Validate the new-book generator contract."""
    root = Path(root)
    policy = load_json(root / POLICY_PATH, "new-book policy")
    _exact(
        policy,
        {
            "schema_version",
            "generator",
            "engine_image",
            "defaults",
            "required_scaffold_paths",
        },
        "new-book policy",
    )
    if policy["schema_version"] != 1:
        fail("new-book policy schema_version must be 1")
    generator = _exact(
        policy["generator"], {"id", "version", "uuid_namespace"}, "new-book generator"
    )
    if not isinstance(generator["id"], str) or BOOK_ID.fullmatch(generator["id"]) is None:
        fail("new-book generator id must be lowercase kebab-case")
    if not isinstance(generator["version"], str) or SEMVER.fullmatch(generator["version"]) is None:
        fail("new-book generator version must use semantic versioning")
    try:
        namespace = uuid.UUID(generator["uuid_namespace"])
    except (AttributeError, TypeError, ValueError):
        fail("new-book generator uuid_namespace must be a UUID")
    if namespace.version != 5:
        fail("new-book generator uuid_namespace must be a version 5 UUID")
    if policy["engine_image"] != TOOLCHAIN_IMAGE:
        fail("new-book generator must use the canonical engine image")
    defaults = _exact(
        policy["defaults"], {"subtitle", "description", "language"}, "new-book defaults"
    )
    _plain_text(defaults["subtitle"], "default subtitle")
    _plain_text(defaults["description"], "default description")
    if (
        not isinstance(defaults["language"], str)
        or LANGUAGE.fullmatch(defaults["language"]) is None
    ):
        fail("default language must be a language tag")
    required = policy["required_scaffold_paths"]
    if not isinstance(required, list) or not required or len(required) != len(set(required)):
        fail("new-book required scaffold paths must be a unique nonempty array")
    for value in required:
        _relative(value, "new-book required scaffold path")
    return policy


def normalize_book_options(
    root, title, author, book_id=None, subtitle=None, language=None, created=None
):
    """Normalize author inputs and derive stable identity fields."""
    policy = load_new_book_policy(root)
    defaults = policy["defaults"]
    title = _plain_text(title, "book title")
    author = _plain_text(author, "book author")
    subtitle = _plain_text(subtitle or defaults["subtitle"], "book subtitle")
    language = language or defaults["language"]
    if not isinstance(language, str) or LANGUAGE.fullmatch(language) is None:
        fail("book language must be a language tag such as en-US")
    identifier = book_id or _slug(title)
    if not identifier or BOOK_ID.fullmatch(identifier) is None:
        fail("book id must be supplied as lowercase kebab-case")
    created_value = created or datetime.now(tz=UTC).date().isoformat()
    try:
        created_date = date.fromisoformat(created_value)
    except (TypeError, ValueError):
        fail("book creation date must use YYYY-MM-DD")
    if created_date < date(1980, 1, 1):
        fail("book creation date must be 1980-01-01 or later")
    namespace = uuid.UUID(policy["generator"]["uuid_namespace"])
    epub_uuid = uuid.uuid5(namespace, identifier)
    preview_uuid = uuid.uuid5(namespace, identifier + ":preview")
    return {
        "id": identifier,
        "title": title,
        "subtitle": subtitle,
        "author": author,
        "description": defaults["description"],
        "language": language,
        "created": created_date.isoformat(),
        "epub_identifier": f"urn:uuid:{epub_uuid}",
        "preview_identifier": f"urn:uuid:{preview_uuid}",
    }


def _minimal_book_toml(options):
    quote = _yaml_string
    return f"""# Author-owned book facts. Everything under .alkahest/ is managed.
schema_version = 2

[book]
title = {quote(options["title"])}
subtitle = {quote(options["subtitle"])}
author = {quote(options["author"])}
language = {quote(options["language"])}
description = {quote(options["description"])}

[excerpt]
chapters = ["01-first-chapter.qmd"]
message = "This excerpt contains selected chapters, not the complete book."

# Optional design overrides:
# [theme.colors]
# primary = "#334155"
# accent = "#9a4f12"
# [theme.typography]
# display = "Libertinus Serif Display"
""".encode()


def _minimal_authored_files(options, engine_image):
    makefile = rb""".DEFAULT_GOAL := help

PODMAN ?= podman
IMAGE ?= localhost/alkahest-book:development
ALK := $(PODMAN) run --rm --pull=never --network=none \
	--userns=keep-id --user "$$(id -u):$$(id -g)" \
	--security-opt label=disable \
	--tmpfs /tmp:rw,size=2g,mode=1777 \
	--env HOME=/tmp \
	--env JAVA_TOOL_OPTIONS=-Duser.home=/tmp \
	--env TEXMFCACHE=/tmp \
	--env TEXMFVAR=/tmp \
	--env XDG_CACHE_HOME=/tmp/cache \
	--volume "$(CURDIR):/book:rw" \
	--workdir /book \
	$(IMAGE)

.PHONY: help bootstrap chapter doctor draft check build build-all excerpt clean

help: ## Show the writer workflow.
	@awk 'BEGIN {FS = ":.*## "; printf "Usage: make <target>\n\n"} /^[a-zA-Z0-9_-]+:.*## / {printf "  %-12s %s\n", $$1, $$2}' $(MAKEFILE_LIST)

bootstrap: ## Build this book's rootless container from the Alkahest engine.
	$(PODMAN) build --pull=never --file Containerfile --tag $(IMAGE) .

chapter: ## Create the next numbered chapter: make chapter TITLE="My Chapter".
	@test -n "$(TITLE)" || (echo 'error: TITLE is required' >&2; exit 2)
	$(ALK) chapter "$(TITLE)"

doctor: ## Check book inputs and the local rendering environment.
	$(ALK) doctor

draft: ## Build the full HTML draft.
	$(ALK) draft

check: ## Validate book.toml and compile disposable workspaces.
	$(ALK) check

build: ## Build full HTML, EPUB, and production Typst editions.
	$(ALK) build

build-all: ## Also build the advanced LuaLaTeX edition.
	$(ALK) build-all

excerpt: ## Build the selected public HTML, EPUB, and Typst excerpt.
	$(ALK) excerpt

clean: ## Remove disposable build output.
	$(ALK) clean
"""
    return {
        ".gitignore": b"_build/\n.DS_Store\n",
        "Containerfile": f"""# Use the complete rootless Alkahest author runtime.
# The public template will pin a released GHCR image by digest.
FROM {engine_image}

WORKDIR /book
ENTRYPOINT ["/opt/alkahest/tools/bin/python", "/opt/alkahest/engine/scripts/author.py"]
""".encode(),
        "README.md": f"""# {options["title"]}

Write in `manuscript/`. Change title, excerpt selection, or optional theme
choices in `book.toml`. Everything under `.alkahest/` is managed.

```sh
make bootstrap                        # Build this book's container once.
make chapter TITLE="A New Chapter"  # Create the next numbered chapter.
make doctor                          # Check whether this book is ready to build.
make draft                           # Build the full HTML draft.
make check                           # Validate configuration and content.
make build                           # Build HTML, EPUB, and the production PDF.
make excerpt                         # Build the selected public excerpt.
```

Run `make help` for the complete concise workflow. Build output is disposable
and lives under `_build/`; open `_build/full/html/index.html` after `make draft`.
This development scaffold expects the Alkahest engine image to have been built
once in the source toolkit. Normal author commands need no host Python, uv,
Quarto, or network access.
""".encode(),
        "Makefile": makefile,
        "book.toml": _minimal_book_toml(options),
        "manuscript/index.qmd": f"""# Welcome {{.unnumbered}}

::: {{.alkahest-preview-placeholder}}
:::

This is **{options["title"]}** by {options["author"]}.

Replace this page with the preface or introduction.
""".encode(),
        "manuscript/chapters/01-first-chapter.qmd": b"""# First chapter

Start writing here.

## A section

The same manuscript builds as HTML, EPUB, and a production Typst PDF.
""",
        "manuscript/references.qmd": b"""# References {.unnumbered}

::: {#refs}
:::
""",
        "manuscript/appendices/README.md": b"Add numbered NN-name.qmd appendix files here when needed.\n",
        "assets/README.md": b"Store book images and other public source assets here.\n",
        "references.bib": b"% Add BibLaTeX or BibTeX records here.\n",
    }


def scaffold_members(root, options):
    """Return all deterministic scaffold members without writing them."""
    root = Path(root)
    policy = load_new_book_policy(root)
    files = _minimal_authored_files(options, policy["engine_image"])
    files[".alkahest/scaffold.json"] = _json(
        {
            "schema_version": 1,
            "generator": policy["generator"],
            "book": {
                "id": options["id"],
                "created": options["created"],
                "identifier": options["epub_identifier"],
                "excerpt_identifier": options["preview_identifier"],
            },
            "engine": {
                "image": policy["engine_image"],
            },
        }
    )
    required = set(policy["required_scaffold_paths"])
    missing = required - set(files)
    if missing:
        fail(f"new-book scaffold omits required path: {min(missing)}")
    return files


def validate_scaffold(root, expected=None):
    """Validate a generated scaffold's closed files and image boundary."""
    root = Path(root)
    if not root.is_dir() or root.is_symlink():
        fail("generated book root is missing or unsafe")
    actual = {}
    for current, directories, names in os.walk(root, topdown=True, followlinks=False):
        current_path = Path(current)
        for directory in directories:
            if (current_path / directory).is_symlink():
                fail("generated book contains a symlink")
        for name in names:
            path = current_path / name
            if path.is_symlink() or not path.is_file():
                fail("generated book contains a nonregular file")
            actual[path.relative_to(root).as_posix()] = path.read_bytes()
    if expected is not None and actual != expected:
        fail("generated book files differ from the deterministic scaffold")
    scaffold = load_json(root / ".alkahest/scaffold.json", "generated scaffold record")
    _exact(scaffold, {"schema_version", "generator", "book", "engine"}, "generated scaffold")
    if scaffold["schema_version"] != 1:
        fail("generated scaffold schema_version must be 1")
    engine = _exact(scaffold["engine"], {"image"}, "generated scaffold engine")
    image = engine["image"]
    if image != TOOLCHAIN_IMAGE:
        fail("generated scaffold engine image differs from the current engine")
    containerfile = actual.get("Containerfile", b"")
    if f"FROM {image}\n".encode() not in containerfile:
        fail("generated scaffold Containerfile does not pin its engine image")
    makefile = actual.get("Makefile", b"")
    if b"--network=none" not in makefile or b"bootstrap: ##" not in makefile:
        fail("generated scaffold does not use the rootless container workflow")
    if b"PYTHON ?=" in makefile or b"UV ?=" in makefile:
        fail("generated scaffold requires a host Python toolchain")
    if any(path.endswith((".zip", ".pyc")) for path in actual):
        fail("generated scaffold contains a vendored engine or Python cache")
    try:
        config = load_author_config(root)
        discovered = discover_content(root, config)
    except AuthorProjectError as error:
        fail(str(error).removeprefix("error: "))
    for path, content in actual.items():
        text = content.decode("utf-8", errors="ignore")
        if "Alkahest Reference Book" in text or "REFERENCE SPECIMEN" in text:
            fail(f"generated scaffold leaks reference-book content: {path}")
    return {
        "files": len(actual),
        "engine_image": image,
        "chapters": len(discovered["chapters"]),
    }


def create_new_book(root, destination, **values):
    """Create one new repository without overwriting an existing path."""
    root = Path(root)
    destination = Path(destination).absolute()
    if os.path.lexists(destination):
        fail(f"destination already exists: {destination}")
    parent = destination.parent
    if not parent.is_dir() or parent.is_symlink():
        fail(f"destination parent must be an existing regular directory: {parent}")
    options = normalize_book_options(root, **values)
    members = scaffold_members(root, options)
    temporary = Path(tempfile.mkdtemp(prefix=f".{destination.name}.alkahest-", dir=parent))
    try:
        for relative, content in sorted(members.items()):
            target = temporary.joinpath(*PurePosixPath(relative).parts)
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(content)
        validate_scaffold(temporary, members)
        if os.path.lexists(destination):
            fail(f"destination appeared while creating book: {destination}")
        temporary.rename(destination)
    except BaseException:
        if temporary.exists():
            shutil.rmtree(temporary)
        raise
    return {"destination": destination, "options": options, "files": len(members)}
