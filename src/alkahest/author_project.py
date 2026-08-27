"""Build a small author repository with the bundled Quarto theme."""

from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import tomllib
import unicodedata
import uuid
from pathlib import Path, PurePosixPath
from typing import Never, TypedDict, cast

from .process import run_process

CHAPTER = re.compile(r"[0-9]{2}-[a-z0-9]+(?:-[a-z0-9]+)*\.qmd")
FORMATS = {"html", "epub", "typst"}
PROFILES = {"full", "excerpt"}
NAMESPACE = uuid.UUID("919b5b6c-28cf-5f5f-a202-b72f0ed50ac3")


class AuthorProjectError(RuntimeError):
    """Report an invalid author project or failed build."""


class BookSettings(TypedDict):
    """Validated publication metadata used by every output."""

    title: str
    subtitle: str
    author: str
    language: str
    description: str
    identifier: str


class ExcerptSettings(TypedDict):
    """Validated excerpt selection."""

    chapters: list[str]
    message: str


class AuthorConfig(TypedDict):
    """Complete validated author configuration."""

    book: BookSettings
    excerpt: ExcerptSettings


class Workspace(TypedDict):
    """Compiled author workspace returned to the thin CLI."""

    stage: Path
    sources: list[str]
    config: AuthorConfig


def fail(message: str) -> Never:
    """Raise one author-facing project error."""
    raise AuthorProjectError(f"error: {message}")


def plain(value: object, label: str, *, required: bool = True) -> str:
    """Validate one human-readable configuration value."""
    if value is None and not required:
        return ""
    if not isinstance(value, str) or not value.strip() or value != value.strip():
        fail(f"{label} must be nonempty without surrounding whitespace")
    if any(character in value for character in "\r\n\0"):
        fail(f"{label} must be one line")
    return value


def slug(value: str) -> str:
    """Create a stable ASCII filename component."""
    normalized = unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9]+", "-", normalized.lower()).strip("-")


def load_config_tables(root: Path) -> tuple[dict[str, object], dict[str, object]]:
    """Read and validate the two supported book configuration tables."""
    try:
        document_value = cast(object, tomllib.loads((root / "book.toml").read_text(encoding="utf-8")))
    except (OSError, UnicodeError, tomllib.TOMLDecodeError) as error:
        fail(f"cannot read book.toml: {error}")

    if not isinstance(document_value, dict):
        fail("book.toml must contain a top-level table")

    document = cast(dict[str, object], document_value)
    if set(document) - {"book", "excerpt"}:
        fail("book.toml supports only [book] and [excerpt]")

    book_value = document.get("book")
    if not isinstance(book_value, dict):
        fail("book.toml requires a [book] table")

    book = cast(dict[str, object], book_value)
    excerpt_value = document.get("excerpt", {})
    if not isinstance(excerpt_value, dict):
        fail("[excerpt] must be a table")
    return book, cast(dict[str, object], excerpt_value)


def parse_book_settings(book: dict[str, object]) -> BookSettings:
    """Validate publication metadata from the book table."""
    if set(book) - {"title", "subtitle", "author", "language", "description"}:
        fail("[book] contains unsupported fields")

    title = plain(book.get("title"), "book title")
    author = plain(book.get("author"), "book author")
    language = plain(book.get("language", "en-US"), "book language")
    if re.fullmatch(r"[A-Za-z]{2,3}(?:-[A-Za-z0-9]{2,8})*", language) is None:
        fail("book language must be a language tag such as en-US")

    return {
        "title": title,
        "subtitle": plain(book.get("subtitle"), "book subtitle", required=False),
        "author": author,
        "language": language,
        "description": plain(book.get("description"), "book description", required=False),
        "identifier": f"urn:uuid:{uuid.uuid5(NAMESPACE, f'{title}\0{author}')}",
    }


def parse_excerpt_settings(excerpt: dict[str, object]) -> ExcerptSettings:
    """Validate chapter selection and messaging from the excerpt table."""
    if set(excerpt) - {"chapters", "message"}:
        fail("[excerpt] contains unsupported fields")

    chapters_value = excerpt.get("chapters", [])
    if not isinstance(chapters_value, list):
        fail("excerpt chapters must contain at most two unique filenames")

    chapter_objects = cast(list[object], chapters_value)
    if len(chapter_objects) > 2 or any(not isinstance(item, str) for item in chapter_objects):
        fail("excerpt chapters must contain at most two unique filenames")

    chapters = cast(list[str], chapter_objects)
    if len(chapters) != len(set(chapters)):
        fail("excerpt chapters must contain at most two unique filenames")
    if any(CHAPTER.fullmatch(item) is None for item in chapters):
        fail("excerpt chapter names must use NN-kebab-case.qmd")

    message = plain(
        excerpt.get("message", "This excerpt contains selected chapters, not the complete book."),
        "excerpt message",
    )
    return {"chapters": chapters, "message": message}


def load_author_config(root: Path) -> AuthorConfig:
    """Load the intentionally small author-owned configuration."""
    book, excerpt = load_config_tables(root)
    return {"book": parse_book_settings(book), "excerpt": parse_excerpt_settings(excerpt)}


def discover_content(root: Path, config: AuthorConfig) -> dict[str, list[str]]:
    """Discover numbered chapters and appendices without a second manifest."""
    required = ("manuscript/index.qmd", "manuscript/references.qmd", "references.bib")
    for relative in required:
        if not (root / relative).is_file():
            fail(f"required author file is missing: {relative}")

    discovered: dict[str, list[str]] = {}
    for kind in ("chapters", "appendices"):
        directory = root / "manuscript" / kind
        if not directory.is_dir():
            fail(f"content directory is missing: manuscript/{kind}")
        invalid = [path.name for path in directory.glob("*.qmd") if CHAPTER.fullmatch(path.name) is None]
        if invalid:
            fail(f"{kind} filename must use NN-kebab-case.qmd: {min(invalid)}")
        discovered[kind] = [path.relative_to(root).as_posix() for path in sorted(directory.glob("*.qmd"))]

    if not discovered["chapters"]:
        fail("book needs at least one numbered chapter")

    requested = set(config["excerpt"]["chapters"])
    names = {PurePosixPath(path).name for path in discovered["chapters"]}
    if requested - names:
        fail(f"excerpt references a missing chapter: {min(requested - names)}")

    discovered["excerpt"] = [path for path in discovered["chapters"] if PurePosixPath(path).name in requested]
    return discovered


def yaml_string(value: str) -> str:
    """Serialize one scalar in YAML-compatible JSON form."""
    return json.dumps(value, ensure_ascii=False)


def project_config(config: AuthorConfig, sources: list[str], appendices: list[str]) -> str:
    """Create the sole generated Quarto project file."""
    book = config["book"]
    lines = [
        "project:",
        "  type: book",
        "",
        "metadata-files:",
        "  - alkahest-defaults.yml",
        "",
        "book:",
        f"  title: {yaml_string(book['title'])}",
        f"  author: {yaml_string(book['author'])}",
    ]
    for field in ("subtitle", "description"):
        if book[field]:
            lines.append(f"  {field}: {yaml_string(book[field])}")

    lines.extend(["  chapters:", *[f"    - {source}" for source in sources]])
    if appendices:
        lines.extend(["  appendices:", *[f"    - {source}" for source in appendices]])

    lines.extend(
        [
            "",
            f"lang: {yaml_string(book['language'])}",
            f"identifier: {yaml_string(book['identifier'])}",
            "bibliography: references.bib",
            "brand: _brand.yml",
            "",
        ]
    )
    return "\n".join(lines)


FORMAT_PROFILES = {
    "html": """project:\n  output-dir: _output/html\n\nformat:\n  html:\n    code-copy: true\n    code-overflow: scroll\n    html-math-method: mathml\n    include-before-body: theme/accessibility-before-body.html\n    theme: theme/alkahest.scss\n    css: theme/alkahest-fonts.css\n""",
    "epub": """project:\n  output-dir: _output/epub\n\nformat:\n  epub:\n    css: theme/alkahest-epub.css\n    epub-fonts:\n      - theme/fonts/LibertinusSerif-Regular.woff2\n      - theme/fonts/LibertinusSerif-Italic.woff2\n      - theme/fonts/LibertinusSerif-Bold.woff2\n      - theme/fonts/LibertinusSerif-BoldItalic.woff2\n      - theme/fonts/LibertinusSerifDisplay-Regular.woff2\n      - theme/fonts/LibertinusSans-Regular.woff2\n      - theme/fonts/LibertinusSans-Italic.woff2\n      - theme/fonts/LibertinusSans-Bold.woff2\n      - theme/fonts/SourceCodePro-Regular.otf.woff2\n      - theme/fonts/SourceCodePro-It.otf.woff2\n      - theme/fonts/SourceCodePro-Bold.otf.woff2\n      - theme/fonts/SourceCodePro-BoldIt.otf.woff2\n""",
    "typst": """project:\n  output-dir: _output/typst\n\nformat:\n  typst:\n    citeproc: true\n    keep-typ: true\n    template-partials:\n      - typst/typst-show.typ\n    margin:\n      top: 0.70in\n      bottom: 0.80in\n    margin-geometry:\n      inner:\n        far: 0.85in\n        width: 0in\n        separation: 0in\n      outer:\n        far: 0.70in\n        width: 0in\n        separation: 0in\n      clearance: 8pt\n\ntrim-width: 7in\ntrim-height: 10in\nbody-font-size: 10pt\nbody-leading: 3pt\nparagraph-indent: 1em\nparagraph-spacing: 3pt\n""",
}


def replace_workspace(path: Path, root: Path) -> None:
    """Remove only a known disposable author workspace."""
    expected = root / "_build" / ".work"
    if path.parent != expected or path.name not in PROFILES:
        fail("refusing unsafe author workspace cleanup")
    if path.exists():
        shutil.rmtree(path)


def relative_symlink(source: Path, target: Path) -> None:
    """Create a relative symbolic link at the requested target."""
    target.symlink_to(Path(os.path.relpath(source, target.parent)))


def stage_engine_runtime(stage: Path, engine_root: Path) -> None:
    """Link immutable engine resources into an author workspace."""
    for directory in ("_extensions", "filters", "icons", "theme", "typst"):
        source = engine_root / directory
        if not source.is_dir():
            fail(f"engine runtime is missing {directory}")
        relative_symlink(source, stage / directory)
    for source_name, target_name in (("defaults/quarto.yml", "alkahest-defaults.yml"), ("_brand.yml", "_brand.yml")):
        source = engine_root / source_name
        if not source.is_file():
            fail(f"engine runtime is missing {source_name}")
        relative_symlink(source, stage / target_name)


def stage_manuscript(
    stage: Path,
    root: Path,
    sources: list[str],
    appendices: list[str],
    config: AuthorConfig,
    profile: str,
) -> None:
    """Stage manuscript files and customize the book home page."""
    marker = "::: {.alkahest-excerpt-placeholder}\n:::"
    replacement = "" if profile == "full" else f"::: {{.callout-note}}\n{config['excerpt']['message']}\n:::"
    for relative in [*sources, *appendices]:
        source = root / ("manuscript/index.qmd" if relative == "index.qmd" else relative)
        target = stage / relative
        target.parent.mkdir(parents=True, exist_ok=True)

        if relative == "index.qmd":
            text = source.read_text(encoding="utf-8")
            target.write_text(text.replace(marker, replacement), encoding="utf-8")
        else:
            relative_symlink(source, target)


def stage_author_resources(stage: Path, root: Path, config: AuthorConfig) -> None:
    """Stage the bibliography, assets, and optional registries."""
    relative_symlink(root / "references.bib", stage / "references.bib")
    if (root / "assets").is_dir():
        relative_symlink(root / "assets", stage / "assets")

    for registry, empty in (
        ("glossary.yml", "version: 1\nlang: en-US\nterms: {}\n"),
        ("index.yml", "version: 1\nlang: en-US\nentries: {}\n"),
    ):
        source = root / registry
        target = stage / registry
        if source.is_file():
            relative_symlink(source, target)
        else:
            target.write_text(empty.replace("en-US", config["book"]["language"]), encoding="utf-8")


def write_workspace_config(stage: Path, config: AuthorConfig, sources: list[str], appendices: list[str]) -> None:
    """Write project and output-format configuration files."""
    (stage / "_quarto.yml").write_text(project_config(config, sources, appendices), encoding="utf-8")
    for name, text in FORMAT_PROFILES.items():
        (stage / f"_quarto-{name}.yml").write_text(text, encoding="utf-8")


def compile_workspace(root: Path, engine_root: Path, profile: str = "full") -> Workspace:
    """Compile one disposable full or excerpt Quarto workspace."""
    root = root.resolve()
    engine_root = engine_root.resolve()
    if profile not in PROFILES:
        fail(f"unknown author profile: {profile}")

    config = load_author_config(root)
    content = discover_content(root, config)
    selected = content["chapters"] if profile == "full" else content["excerpt"]

    # Quarto requires a book home page at the project root, so stage the
    # author-facing manuscript/index.qmd there without exposing that detail.
    sources = ["index.qmd", *selected, "manuscript/references.qmd"]
    appendices = content["appendices"] if profile == "full" else []
    stage = root / "_build" / ".work" / profile

    replace_workspace(stage, root)
    stage.mkdir(parents=True)
    stage_engine_runtime(stage, engine_root)
    stage_manuscript(stage, root, sources, appendices, config, profile)
    stage_author_resources(stage, root, config)
    write_workspace_config(stage, config, sources, appendices)
    return {"stage": stage, "sources": [*sources, *appendices], "config": config}


def add_chapter(root: Path, title: str) -> Path:
    """Create the next numbered chapter."""
    root = root.resolve()
    title = plain(title, "chapter title")
    config = load_author_config(root)
    discover_content(root, config)

    directory = root / "manuscript" / "chapters"
    numbers = [int(path.name[:2]) for path in directory.glob("*.qmd")]
    number = max(numbers, default=0) + 1
    name = slug(title)
    if number > 99 or not name:
        fail("chapter title cannot produce a valid numbered filename")

    path = directory / f"{number:02d}-{name}.qmd"
    path.write_text(f"# {title}\n\nStart writing here.\n", encoding="utf-8")
    return path


def doctor(root: Path) -> dict[str, object]:
    """Validate author inputs and the renderer available inside the image."""
    config = load_author_config(root.resolve())
    content = discover_content(root.resolve(), config)
    quarto = shutil.which("quarto")
    if quarto is None:
        fail("Quarto is unavailable; run this command through the book container")
    result = run_process([quarto, "--version"], check=True, capture_output=True, text=True)
    return {"renderer": f"Quarto {result.stdout.strip()}", "chapters": len(content["chapters"])}


def render(root: Path, engine_root: Path, profile: str, formats: list[str]) -> Workspace:
    """Build selected formats from one disposable workspace."""
    unknown = set(formats) - FORMATS
    if unknown:
        fail(f"unknown render format: {min(unknown)}")

    result = compile_workspace(root, engine_root, profile)
    stage = result["stage"]
    for format_name in formats:
        print(f"rendering: {profile} {format_name}", flush=True)
        completed = run_process(
            ["quarto", "render", "--profile", format_name],
            cwd=stage,
            check=False,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
        )
        if completed.returncode:
            fail(f"{format_name} render failed with status {completed.returncode}\n{completed.stdout.strip()}")

        generated = stage / "_output" / format_name
        destination = root.resolve() / "_build" / profile / format_name
        if not generated.is_dir() or destination.parent != root.resolve() / "_build" / profile:
            fail(f"{format_name} render did not create its expected output")

        if destination.exists():
            shutil.rmtree(destination)

        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copytree(generated, destination)
        print(f"built: _build/{profile}/{format_name}")
    return result


__all__ = [
    "AuthorProjectError",
    "add_chapter",
    "compile_workspace",
    "discover_content",
    "doctor",
    "load_author_config",
    "render",
]
