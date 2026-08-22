"""Create and validate minimal book repositories from the reusable engine."""

import hashlib
import json
import os
import re
import shutil
import tempfile
import unicodedata
import uuid
from datetime import date, datetime, timezone
from pathlib import Path, PurePosixPath

from .common import fail, load_json
from .release_profiles import (
    ReleaseProfileError,
    release_outputs,
    sync_project_releases,
)
from .template_package import template_members
from .theme import ThemeError, sync_project_theme, theme_outputs


POLICY_PATH = "config/template/new-book.json"
BOOK_ID = re.compile(r"[a-z0-9]+(?:-[a-z0-9]+)*")
LANGUAGE = re.compile(r"[A-Za-z]{2,3}(?:-[A-Za-z0-9]{2,8})*")
SEMVER = re.compile(
    r"(?:0|[1-9][0-9]*)\.(?:0|[1-9][0-9]*)\.(?:0|[1-9][0-9]*)"
)
EVIDENCE_ROOT = PurePosixPath(".alkahest/engine")


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
            "engine_evidence_members",
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
    evidence = policy["engine_evidence_members"]
    if (
        not isinstance(evidence, list)
        or set(evidence) != {"LICENSE", "MANIFEST.json", "README.md", "SHA256SUMS"}
        or len(evidence) != 4
    ):
        fail("new-book engine evidence members must be the four package records")
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
        "author_id": _slug(author) or "author",
        "description": defaults["description"],
        "language": language,
        "created": created_date.isoformat(),
        "copyright_year": created_date.year,
        "epub_identifier": f"urn:uuid:{epub_uuid}",
        "preview_identifier": f"urn:uuid:{preview_uuid}",
        "source_date_epoch": int(
            datetime(
                created_date.year,
                created_date.month,
                created_date.day,
                tzinfo=timezone.utc,
            ).timestamp()
        ),
    }


def _metadata(options):
    quote = _yaml_string
    return f"""# Generated by the Alkahest new-book command; keep aligned with publication.json.
book:
  title: {quote(options['title'])}
  subtitle: {quote(options['subtitle'])}
  author:
    - name: {quote(options['author'])}
  description: {quote(options['description'])}
title: {quote(options['title'])}
subtitle: {quote(options['subtitle'])}
author:
  - name: {quote(options['author'])}
date: {quote(options['created'])}
lang: {quote(options['language'])}
description: {quote(options['description'])}
subject: "Technical book"
keywords:
  - "technical writing"
alkahest:
  work-id: {quote(options['id'])}
  publication-status: "development"
  edition: "Development edition"
  publisher: "Publisher not assigned"
  copyright-year: {quote(str(options['copyright_year']))}
  copyright-holder: {quote(options['author'])}
  rights-statement: "Publication rights and licenses remain undecided during development."
  identifier: {quote(options['epub_identifier'])}
""".encode("utf-8")


def _publication(options):
    return {
        "schema_version": 1,
        "work": {
            "id": options["id"],
            "status": "development",
            "title": options["title"],
            "subtitle": options["subtitle"],
            "descriptions": {
                "short": options["description"],
                "long": options["description"],
            },
            "series": None,
            "edition": {
                "name": "Development edition",
                "number": None,
                "statement": "Development edition; not for publication.",
            },
            "dates": {
                "created": options["created"],
                "modified": options["created"],
                "publication": None,
            },
            "language": {
                "primary": options["language"],
                "original": options["language"],
            },
            "territories": ["WORLD"],
            "subjects": [],
            "keywords": ["technical writing"],
            "audiences": [],
        },
        "contributors": [
            {
                "id": options["author_id"],
                "display_name": options["author"],
                "sort_name": options["author"],
                "roles": ["author"],
                "affiliation": None,
                "orcid": None,
            }
        ],
        "publication": {
            "publisher": {"name": None, "place": None, "website": None},
            "imprint": {"name": None, "place": None, "website": None},
        },
        "rights": {
            "copyright": {
                "year": options["copyright_year"],
                "holders": [options["author"]],
            },
            "statement": "Publication rights and licenses remain undecided during development.",
            "licenses": [
                {
                    "scope": "Publication text",
                    "status": "undecided",
                    "expression": None,
                    "url": None,
                    "policy": None,
                }
            ],
        },
        "accessibility": {
            "features": [
                "alternativeText",
                "readingOrder",
                "structuralNavigation",
                "tableOfContents",
            ],
            "hazards": ["none"],
            "summary": "Accessibility review is pending.",
            "review": {"standard": "EPUB Accessibility 1.1", "status": "pending-manual-review"},
        },
        "provenance": {
            "source_statement": "Canonical manuscripts are maintained as Quarto Markdown.",
            "reproducibility_statement": (
                "Build provenance is recorded in book/reproducibility.json."
            ),
            "repository": {"visibility": "private", "url": None},
            "policies": {
                "reproducibility": "book/reproducibility.json",
                "rights": None,
                "accessibility": None,
            },
        },
    }


def _releases(options):
    """Return book-local full/preview allowlists and product metadata."""
    return {
        "schema_version": 1,
        "sources": {
            "front": {
                "path": "index.qmd",
                "role": "front",
                "availability": "release",
            },
            "chapter-01": {
                "path": "chapter-01.qmd",
                "role": "chapter",
                "availability": "release",
            },
            "references": {
                "path": "references.qmd",
                "role": "back",
                "availability": "release",
            },
        },
        "profiles": {
            "full": {
                "chapters": ["front", "chapter-01", "references"],
                "appendices": [],
                "metadata": {
                    "subtitle": options["subtitle"],
                    "description": options["description"],
                    "edition": "Development edition",
                    "identifier": options["epub_identifier"],
                },
                "presentation": {},
            },
            "preview": {
                "chapters": ["front", "chapter-01", "references"],
                "appendices": [],
                "metadata": {
                    "subtitle": "One-chapter preview edition",
                    "description": f"A one-chapter preview of {options['title']}.",
                    "edition": "Preview edition; not for publication.",
                    "identifier": options["preview_identifier"],
                },
                "presentation": {
                    "message": "This preview contains one selected chapter, not the complete book."
                },
            },
        },
    }


def _authored_files(options):
    quote = _yaml_string
    files = {
        ".gitignore": b"book/_build/\nbook/.quarto/\n__pycache__/\n*.py[cod]\n.DS_Store\n",
        "README.md": f"""# {options['title']}

This book repository was created by Alkahest. Edit the Markdown files under
`book/`, keep canonical publication facts in `book/publication.json`, and keep
the Quarto adapter in `book/generated/metadata.yml` aligned when facts change.

Edit `book/theme.json` and run `make theme` to apply book-local colors or fonts.
Edit `book/releases.json` to choose full/preview chapters and product metadata,
then run `make releases`. Run `make help` to see the author workflow.
Rendering requires Quarto, Typst, and LuaLaTeX on `PATH`, or the pinned Alkahest
publishing environment.
""".encode("utf-8"),
        "Makefile": b""".DEFAULT_GOAL := help

QUARTO ?= quarto

.PHONY: help theme check-theme releases check-releases stage-full stage-preview render render-html render-epub render-typst render-latex render-preview clean

help: ## Show available author commands.
	@awk 'BEGIN {FS = ":.*## "; printf "Usage: make <target>\\n\\n"} /^[a-zA-Z0-9_-]+:.*## / {printf "  %-16s %s\\n", $$1, $$2}' $(MAKEFILE_LIST)

theme: ## Regenerate format adapters from book/theme.json.
	python3 scripts/sync-theme.py

check-theme: ## Verify that generated theme adapters are current.
	python3 scripts/sync-theme.py --check

releases: ## Regenerate full and preview profiles from book/releases.json.
	python3 scripts/sync-release-profiles.py

check-releases: ## Verify release profiles and metadata adapters are current.
	python3 scripts/sync-release-profiles.py --check

stage-full: releases ## Stage only sources allowlisted for the full release.
	python3 scripts/stage-release.py full --html-resources

stage-preview: releases ## Stage only sources allowlisted for the preview release.
	python3 scripts/stage-release.py preview --html-resources

render: theme releases ## Build the isolated full release in every format.
	python3 scripts/stage-release.py full --html-resources
	cd book/_build/staging/releases/full && $(QUARTO) render --profile release-full,html
	cd book/_build/staging/releases/full && $(QUARTO) render --profile release-full,epub
	cd book/_build/staging/releases/full && $(QUARTO) render --profile release-full,typst
	cd book/_build/staging/releases/full && $(QUARTO) render --profile release-full,latex

render-html: theme releases ## Build the allowlisted full HTML book.
	python3 scripts/stage-release.py full --html-resources
	cd book/_build/staging/releases/full && $(QUARTO) render --profile release-full,html

render-epub: theme releases ## Build the allowlisted full EPUB book.
	python3 scripts/stage-release.py full
	cd book/_build/staging/releases/full && $(QUARTO) render --profile release-full,epub

render-typst: theme releases ## Build the allowlisted full Typst PDF.
	python3 scripts/stage-release.py full
	cd book/_build/staging/releases/full && $(QUARTO) render --profile release-full,typst

render-latex: theme releases ## Build the allowlisted full LuaLaTeX PDF.
	python3 scripts/stage-release.py full
	cd book/_build/staging/releases/full && $(QUARTO) render --profile release-full,latex

render-preview: theme releases ## Build the isolated HTML, EPUB, and Typst preview.
	python3 scripts/stage-release.py preview --html-resources
	cd book/_build/staging/releases/preview && $(QUARTO) render --profile release-preview,html
	cd book/_build/staging/releases/preview && $(QUARTO) render --profile release-preview,epub
	cd book/_build/staging/releases/preview && $(QUARTO) render --profile release-preview,typst

clean: ## Remove generated book artifacts and Quarto state.
	rm -rf book/_build book/.quarto
""",
        "book/_quarto.yml": b"""project:
  type: book
  pre-render:
    - python3 ../scripts/sync-theme.py

metadata-files:
  - .alkahest/quarto.yml
  - generated/theme-metadata.yml
  - generated/metadata.yml

book:
  chapters:
    - index.qmd
    - chapter-01.qmd
    - references.qmd

bibliography: references.bib
""",
        "book/_quarto-html.yml": b"""project:
  output-dir: _build/html

brand: false

format:
  html:
    code-copy: true
    include-before-body: theme/accessibility-before-body.html
    code-overflow: scroll
    html-math-method: mathml
    theme: theme/alkahest.scss
    css: generated/theme-overrides.css
""",
        "book/_quarto-epub.yml": f"""project:
  output-dir: _build/epub

identifier: {quote(options['epub_identifier'])}

format:
  epub:
    css: generated/theme-overrides.css
""".encode("utf-8"),
        "book/_quarto-typst.yml": b"""project:
  output-dir: _build/print/typst

trim-width: 7in
trim-height: 10in
body-font-size: 10pt
body-leading: 3pt
paragraph-indent: 1em
paragraph-spacing: 3pt

format:
  typst:
    citeproc: true
    keep-typ: true
    template-partials:
      - typst/typst-show.typ
    margin:
      top: 0.70in
      bottom: 0.80in
    margin-geometry:
      inner:
        far: 0.85in
        width: 0in
        separation: 0in
      outer:
        far: 0.70in
        width: 0in
        separation: 0in
      clearance: 8pt
""",
        "book/_quarto-latex.yml": b"""project:
  output-dir: _build/print/latex

format:
  pdf:
    fig-pos: htbp
    documentclass: scrbook
    classoption:
      - twoside
      - openright
    pdf-engine: lualatex
    keep-tex: true
    include-in-header:
      - latex/book-layout.tex
      - generated/theme-overrides.tex
    template-partials:
      - latex/title.tex
      - latex/before-body.tex
    geometry:
      - paperwidth=7in
      - paperheight=10in
      - inner=0.85in
      - outer=0.70in
      - top=0.70in
      - bottom=0.80in
""",
        "book/generated/metadata.yml": _metadata(options),
        "book/companion.json": b'{\n  "version": 1,\n  "items": {},\n  "bundles": {}\n}\n',
        "book/generated-lists.yml": f"""version: 1
lang: {quote(options['language'])}
order: []
lists: {{}}
objects: []
terms: {{}}
""".encode("utf-8"),
        "book/glossary.yml": f"""version: 1
lang: {quote(options['language'])}
terms: {{}}
""".encode("utf-8"),
        "book/index.yml": f"""version: 1
lang: {quote(options['language'])}
entries: {{}}
""".encode("utf-8"),
        "book/media.json": b'{\n  "version": 1,\n  "items": {}\n}\n',
        "book/notes.yml": b"version: 1\norder: []\nnotes: {}\n",
        "book/theme.json": b'{\n  "schema_version": 1,\n  "colors": {},\n  "typography": {}\n}\n',
        "book/publication.json": _json(_publication(options)),
        "book/reproducibility.json": _json(
            {
                "schema_version": 1,
                "source_date_epoch": options["source_date_epoch"],
                "source_date_utc": options["created"] + "T00:00:00Z",
                "epub_identifier": options["epub_identifier"],
                "engine": {"id": "alkahest-book-template-engine", "version": "0.1.0"},
            }
        ),
        "book/releases.json": _json(_releases(options)),
        "book/index.qmd": f"""# Welcome {{.unnumbered}}

::: {{.alkahest-preview-placeholder}}
:::

This is **{options['title']}** by {options['author']}.

Replace this page with the book's preface or introduction, then begin writing
in `chapter-01.qmd`.
""".encode("utf-8"),
        "book/chapter-01.qmd": b"""# First chapter

Start writing here. Add chapters to the `book.chapters` list in `_quarto.yml`.

## A section

Alkahest keeps one neutral manuscript for HTML, EPUB, Typst PDF, and LuaLaTeX
PDF output.
""",
        "book/references.qmd": b"""# References {.unnumbered}

::: {#refs}
:::
""",
        "book/references.bib": b"% Add BibLaTeX or BibTeX records here.\n",
        "book/reusable-content.json": b'{\n  "version": 1,\n  "items": {}\n}\n',
    }
    return files


def _engine_destination(member):
    if member.startswith("scripts/"):
        return member
    if member == "defaults/quarto.yml":
        return "book/.alkahest/quarto.yml"
    if member == "defaults/extension-apis.json":
        return "book/.alkahest/extension-apis.json"
    if member == "defaults/book-contracts.json":
        return "book/.alkahest/book-contracts.json"
    if member == "defaults/releases.json":
        return "book/.alkahest/release-defaults.json"
    if member == "defaults/theme.json":
        return "book/.alkahest/theme-defaults.json"
    if member.startswith("schemas/"):
        return str(PurePosixPath("book/.alkahest") / member)
    if member.startswith("docs/"):
        return member
    return str(PurePosixPath("book") / member)


def scaffold_members(root, options):
    """Return all deterministic scaffold members without writing them."""
    root = Path(root)
    policy = load_new_book_policy(root)
    engine_context, engine = template_members(root)
    evidence = set(policy["engine_evidence_members"])
    files = _authored_files(options)
    installed = []
    for member, content in sorted(engine.items()):
        if member in evidence:
            destination = str(EVIDENCE_ROOT / member)
        else:
            destination = _engine_destination(member)
            installed.append(
                {"path": destination, "sha256": _sha256(content), "bytes": len(content)}
            )
        if destination in files:
            fail(f"new-book scaffold path conflicts with engine: {destination}")
        files[destination] = content
    try:
        _theme, theme_files = theme_outputs(
            files["book/.alkahest/theme-defaults.json"], files["book/theme.json"]
        )
    except ThemeError as error:
        fail(str(error).removeprefix("error: "))
    for relative, content in theme_files.items():
        destination = str(PurePosixPath("book") / relative)
        if destination in files:
            fail(f"new-book scaffold path conflicts with theme adapter: {destination}")
        files[destination] = content
    try:
        _releases_resolved, release_files = release_outputs(
            files["book/.alkahest/release-defaults.json"], files["book/releases.json"]
        )
    except ReleaseProfileError as error:
        fail(str(error).removeprefix("error: "))
    for relative, content in release_files.items():
        destination = str(PurePosixPath("book") / relative)
        if destination in files:
            fail(f"new-book scaffold path conflicts with release adapter: {destination}")
        files[destination] = content
    manifest_sha = _sha256(engine["MANIFEST.json"])
    files[".alkahest/scaffold.json"] = _json(
        {
            "schema_version": 1,
            "generator": policy["generator"],
            "book": {
                "id": options["id"],
                "title": options["title"],
                "author": options["author"],
                "language": options["language"],
                "created": options["created"],
                "epub_identifier": options["epub_identifier"],
            },
            "engine": {
                "id": engine_context["package"]["id"],
                "version": engine_context["package"]["version"],
                "manifest_sha256": manifest_sha,
                "installed_files": installed,
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
    records = engine.get("installed_files")
    if not isinstance(records, list) or not records:
        fail("generated scaffold has no installed engine inventory")
    for record in records:
        path = record.get("path")
        if path not in actual or _sha256(actual[path]) != record.get("sha256"):
            fail(f"generated scaffold engine file is missing or changed: {path}")
    try:
        sync_project_theme(root, check=True)
    except ThemeError as error:
        fail(str(error).removeprefix("error: "))
    try:
        sync_project_releases(root, check=True)
    except ReleaseProfileError as error:
        fail(str(error).removeprefix("error: "))
    for path in actual:
        text = actual[path].decode("utf-8", errors="ignore")
        if "Alkahest Reference Book" in text or "REFERENCE SPECIMEN" in text:
            fail(f"generated scaffold leaks reference-book content: {path}")
    return {"files": len(actual), "engine_files": len(records)}


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
        "dispatcher": root / "scripts/check-source.py",
        "ci": root / "scripts/ci.sh",
        "readme": root / "README.md",
        "documentation": root / "docs/new-book.md",
    }
    texts = {name: path.read_text(encoding="utf-8") for name, path in files.items()}
    for marker in ("new-book:", "check-new-book:", "test-new-book:"):
        if marker not in texts["makefile"]:
            fail(f"Makefile is missing new-book target {marker}")
    for marker in (
        '("new-book", "check-new-book.py", False)',
        '("new-book", "test-new-book.py", False)',
    ):
        if marker not in texts["dispatcher"]:
            fail(f"source dispatcher is missing new-book entry {marker}")
    if "check-new-book.py" not in texts["ci"]:
        fail("CI is missing the new-book smoke check")
    if "make new-book" not in texts["readme"]:
        fail("README is missing the new-book author command")
    for marker in (
        "config/template/new-book.json",
        "python3 scripts/new-book.py",
        "will not overwrite",
        "independent publication metadata",
    ):
        if marker not in texts["documentation"]:
            fail(f"new-book documentation is missing {marker!r}")
