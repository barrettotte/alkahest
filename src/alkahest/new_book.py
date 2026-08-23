"""Create and validate minimal book repositories from the reusable engine."""

import hashlib
import json
import os
import re
import shutil
import tempfile
import unicodedata
import uuid
import zipfile
from datetime import date
from pathlib import Path, PurePosixPath

from .author_project import (
    AuthorProjectError,
    compile_workspace,
    discover_content,
    load_author_config,
)
from .common import fail, load_json
from .release_profiles import ReleaseProfileError
from .template_package import expected_template_outputs
from .theme import ThemeError


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


def _sha256(content):
    return hashlib.sha256(content).hexdigest()


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
            "engine_policy",
            "defaults",
            "engine_archive_members",
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
    if policy["engine_policy"] != "config/template/template-package.json":
        fail("new-book generator must use the canonical engine policy")
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
    evidence = policy["engine_archive_members"]
    if not isinstance(evidence, list) or evidence != [
        "LICENSE",
        "MANIFEST.json",
        "README.md",
        "SHA256SUMS",
        "scripts/author.py",
    ]:
        fail("new-book engine archive members must include evidence and author entrypoint")
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
    created_value = created or date.today().isoformat()
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
""".encode("utf-8")


def _author_bootstrap(engine_filename, engine_sha256):
    return f'''"""Verify, unpack, and run the pinned Alkahest author engine."""

import hashlib
import runpy
import shutil
import sys
import tempfile
import zipfile
from pathlib import Path, PurePosixPath


ROOT = Path(__file__).resolve().parent.parent
ARCHIVE = ROOT / ".alkahest" / "{engine_filename}"
EXPECTED_SHA256 = "{engine_sha256}"
CACHE = ROOT / ".alkahest" / "cache" / EXPECTED_SHA256[:16]


def engine_root():
    content = ARCHIVE.read_bytes()
    if hashlib.sha256(content).hexdigest() != EXPECTED_SHA256:
        raise RuntimeError("error: pinned Alkahest engine archive checksum differs")
    entrypoint = CACHE / "scripts" / "author.py"
    if entrypoint.is_file():
        return CACHE
    CACHE.parent.mkdir(parents=True, exist_ok=True)
    temporary = Path(tempfile.mkdtemp(prefix="engine-", dir=CACHE.parent))
    try:
        with zipfile.ZipFile(ARCHIVE) as package:
            names = package.namelist()
            paths = [PurePosixPath(name) for name in names if name]
            if any(path.is_absolute() or ".." in path.parts for path in paths):
                raise RuntimeError("error: Alkahest engine archive contains an unsafe path")
            roots = {{path.parts[0] for path in paths}}
            if len(roots) != 1:
                raise RuntimeError("error: Alkahest engine archive has an invalid root")
            package.extractall(temporary)
        extracted = temporary / roots.pop()
        if not (extracted / "scripts" / "author.py").is_file():
            raise RuntimeError("error: Alkahest engine archive has no author command")
        if CACHE.exists():
            shutil.rmtree(CACHE)
        extracted.rename(CACHE)
    finally:
        if temporary.exists():
            shutil.rmtree(temporary)
    return CACHE


if __name__ == "__main__":
    try:
        runpy.run_path(str(engine_root() / "scripts" / "author.py"), run_name="__main__")
    except (OSError, RuntimeError, UnicodeError, zipfile.BadZipFile) as error:
        print(error, file=sys.stderr)
        raise SystemExit(1)
'''.encode("utf-8")


def _minimal_authored_files(options, engine_filename, engine_content):
    engine_sha256 = _sha256(engine_content)
    return {
        ".gitignore": b"_build/\n.alkahest/cache/\n__pycache__/\n*.py[cod]\n.DS_Store\n",
        "README.md": f"""# {options["title"]}

Write in `manuscript/`. Change title, excerpt selection, or optional theme
choices in `book.toml`. Everything under `.alkahest/` is managed.

```sh
make chapter TITLE="A New Chapter"  # Create the next numbered chapter.
make doctor                          # Check whether this book is ready to build.
make draft                           # Build the full HTML draft.
make check                           # Validate configuration and content.
make build                           # Build HTML, EPUB, and the production PDF.
make excerpt                         # Build the selected public excerpt.
```

Run `make help` for the complete concise workflow. Build output is disposable
and lives under `_build/`; open `_build/full/html/index.html` after `make draft`.
""".encode("utf-8"),
        "Makefile": b""".DEFAULT_GOAL := help

PYTHON ?= python3
ALK := $(PYTHON) .alkahest/alkahest.py

.PHONY: help chapter doctor draft check build build-all excerpt clean

help: ## Show the writer workflow.
	@awk 'BEGIN {FS = ":.*## "; printf "Usage: make <target>\\n\\n"} /^[a-zA-Z0-9_-]+:.*## / {printf "  %-12s %s\\n", $$1, $$2}' $(MAKEFILE_LIST)

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
""",
        "book.toml": _minimal_book_toml(options),
        "manuscript/index.qmd": f"""# Welcome {{.unnumbered}}

::: {{.alkahest-preview-placeholder}}
:::

This is **{options["title"]}** by {options["author"]}.

Replace this page with the preface or introduction.
""".encode("utf-8"),
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
        ".alkahest/alkahest.py": _author_bootstrap(engine_filename, engine_sha256),
        f".alkahest/{engine_filename}": engine_content,
    }


def scaffold_members(root, options):
    """Return all deterministic scaffold members without writing them."""
    root = Path(root)
    policy = load_new_book_policy(root)
    engine_context, engine_members, engine_outputs = expected_template_outputs(root)
    missing_engine = set(policy["engine_archive_members"]) - set(engine_members)
    if missing_engine:
        fail(f"template engine omits required author member: {sorted(missing_engine)[0]}")
    filename = engine_context["package"]["filename"]
    archive = engine_outputs[filename]
    files = _minimal_authored_files(options, filename, archive)
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
                "id": engine_context["package"]["id"],
                "version": engine_context["package"]["version"],
                "archive": f".alkahest/{filename}",
                "archive_sha256": _sha256(archive),
                "package_members": len(engine_members),
            },
        }
    )
    required = set(policy["required_scaffold_paths"])
    missing = required - set(files)
    if missing:
        fail(f"new-book scaffold omits required path: {sorted(missing)[0]}")
    return files


def validate_scaffold(root, expected=None):
    """Validate a generated scaffold's closed files and engine evidence."""
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
    engine = scaffold.get("engine", {})
    archive_path = engine.get("archive")
    if not isinstance(archive_path, str) or archive_path not in actual:
        fail("generated scaffold has no pinned engine archive")
    if _sha256(actual[archive_path]) != engine.get("archive_sha256"):
        fail("generated scaffold engine archive is missing or changed")
    try:
        config = load_author_config(root)
        with tempfile.TemporaryDirectory(prefix="alkahest-engine-smoke.") as temporary:
            extracted = Path(temporary)
            with zipfile.ZipFile(root / archive_path) as package:
                roots = {PurePosixPath(name).parts[0] for name in package.namelist() if name}
                if len(roots) != 1:
                    fail("generated scaffold engine archive has an invalid root")
                package.extractall(extracted)
            engine_root = extracted / roots.pop()
            if engine.get("package_members") != len(
                [path for path in engine_root.rglob("*") if path.is_file()]
            ):
                fail("generated scaffold engine member count differs")
            compile_workspace(root, engine_root, "full")
            compile_workspace(root, engine_root, "excerpt")
    except (
        AuthorProjectError,
        ReleaseProfileError,
        ThemeError,
        zipfile.BadZipFile,
    ) as error:
        fail(str(error).removeprefix("error: "))
    finally:
        output = root / "_build"
        if output.is_dir():
            shutil.rmtree(output)
    for path in actual:
        text = actual[path].decode("utf-8", errors="ignore")
        if "Alkahest Reference Book" in text or "REFERENCE SPECIMEN" in text:
            fail(f"generated scaffold leaks reference-book content: {path}")
    return {
        "files": len(actual),
        "engine_files": 1,
        "engine_members": engine["package_members"],
        "chapters": len(discover_content(root, config)["chapters"]),
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


def validate_new_book_integration(root):
    """Keep the command, policy, tests, docs, and dispatcher connected."""
    root = Path(root)
    files = {
        "makefile": root / "Makefile",
        "tasks": root / "src/alkahest/tasks.py",
        "ci": root / "src/alkahest/ci.py",
        "readme": root / "README.md",
        "documentation": root / "docs/new-book.md",
    }
    texts = {name: path.read_text(encoding="utf-8") for name, path in files.items()}
    for marker in ("new-book:", "check-%:", "test-%:"):
        if marker not in texts["makefile"]:
            fail(f"Makefile is missing new-book target {marker}")
    for marker in ('"new-book", "@alkahest.checks.new_book"',):
        if marker not in texts["tasks"]:
            fail(f"task registry is missing new-book entry {marker}")
    if "alkahest check" not in texts["ci"]:
        fail("CI is missing the new-book smoke check")
    if "make new-book" not in texts["readme"]:
        fail("README is missing the new-book author command")
    for marker in (
        "config/template/new-book.json",
        "uv run --locked alkahest new-book",
        "will not overwrite",
        "book.toml",
        "make chapter",
        "checksum-pinned engine archive",
    ):
        if marker not in texts["documentation"]:
            fail(f"new-book documentation is missing {marker!r}")
