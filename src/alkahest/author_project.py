"""Compile a small author repository into disposable Quarto workspaces."""

import hashlib
import json
import os
import re
import shutil
import subprocess
import tomllib
import unicodedata
import uuid
from datetime import UTC, date, datetime
from pathlib import Path, PurePosixPath
from typing import Never

from .process import run_process
from .release_profiles import ReleaseProfileError, release_outputs
from .theme import COLOR_FIELDS, FONT_FIELDS, FONT_NAME, HEX_COLOR, ThemeError, theme_outputs

BOOK_ID = re.compile(r"[a-z0-9]+(?:-[a-z0-9]+)*")
LANGUAGE = re.compile(r"[A-Za-z]{2,3}(?:-[A-Za-z0-9]{2,8})*")
CHAPTER = re.compile(r"[0-9]{2}-[a-z0-9]+(?:-[a-z0-9]+)*\.qmd")
PROFILES = {"full", "excerpt"}
FORMATS = {"html", "epub", "typst", "latex"}
TOOLCHAIN_IMAGE = "localhost/alkahest-publishing:quarto-1.10.18-v20"
DEFAULT_CONTENT = {
    "front": ["manuscript/index.qmd"],
    "chapter_directory": "manuscript/chapters",
    "appendix_directory": "manuscript/appendices",
    "back": ["manuscript/references.qmd"],
    "bibliography": "references.bib",
}


class AuthorProjectError(RuntimeError):
    """A user-facing minimal-author-project violation."""


def _fail(message: str) -> Never:
    raise AuthorProjectError(f"error: {message}")


def _exact(value, fields, label):
    if not isinstance(value, dict) or set(value) != set(fields):
        _fail(f"{label} fields differ from the author contract")
    return value


def _optional(value, required, optional, label):
    if not isinstance(value, dict):
        _fail(f"{label} must be a table")
    fields = set(value)
    if not set(required) <= fields or not fields <= set(required) | set(optional):
        _fail(f"{label} fields differ from the author contract")
    return value


def _plain(value, label):
    if not isinstance(value, str) or not value or value != value.strip():
        _fail(f"{label} must be nonempty without surrounding whitespace")
    if any(unicodedata.category(character) == "Cc" for character in value):
        _fail(f"{label} must be one line")
    return value


def _relative(value, label, suffix=None):
    if not isinstance(value, str) or not value:
        _fail(f"{label} must be a normalized relative path")
    path = PurePosixPath(value)
    if path.is_absolute() or ".." in path.parts or str(path) != value:
        _fail(f"{label} must be a normalized relative path")
    if suffix is not None and path.suffix != suffix:
        _fail(f"{label} must end in {suffix}")
    return value


def _quote(value):
    return json.dumps(value, ensure_ascii=False)


def _sha256(content):
    return hashlib.sha256(content).hexdigest()


def _slug(value):
    normalized = unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9]+", "-", normalized.lower()).strip("-")


def _load_toml(path):
    try:
        return tomllib.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, tomllib.TOMLDecodeError) as error:
        _fail(f"cannot read book.toml: {error}")


def _load_scaffold_identity(root):
    path = root / ".alkahest" / "scaffold.json"
    try:
        document = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError, UnicodeError) as error:
        _fail(f"cannot read managed scaffold identity: {error}")
    if not isinstance(document, dict) or document.get("schema_version") != 1:
        _fail("managed scaffold identity schema_version must be 1")
    identity = _exact(
        document.get("book"),
        {"id", "created", "identifier", "excerpt_identifier"},
        "managed book identity",
    )
    if not isinstance(identity["id"], str) or BOOK_ID.fullmatch(identity["id"]) is None:
        _fail("book id must be lowercase kebab-case")
    _plain(identity["created"], "book created")
    try:
        date.fromisoformat(identity["created"])
    except ValueError:
        _fail("book created must use YYYY-MM-DD")
    for field in ("identifier", "excerpt_identifier"):
        value = identity[field]
        if not isinstance(value, str) or not value.startswith("urn:uuid:"):
            _fail(f"book {field} must be a UUID URN")
        try:
            uuid.UUID(value.removeprefix("urn:uuid:"))
        except ValueError:
            _fail(f"book {field} must be a UUID URN")
    if identity["identifier"] == identity["excerpt_identifier"]:
        _fail("book and excerpt identifiers must differ")
    return identity


def load_author_config(root):
    """Load the small author config and merge its managed project defaults."""
    root = Path(root)
    document = _load_toml(root / "book.toml")
    _optional(document, {"schema_version", "book", "excerpt"}, {"theme"}, "book.toml")
    if document["schema_version"] != 2:
        _fail("book.toml schema_version must be 2")
    book = _exact(
        document["book"],
        {"title", "subtitle", "author", "language", "description"},
        "book settings",
    )
    for field in ("title", "subtitle", "author", "description"):
        _plain(book[field], f"book {field}")
    if not isinstance(book["language"], str) or LANGUAGE.fullmatch(book["language"]) is None:
        _fail("book language must be a language tag such as en-US")
    identity = _load_scaffold_identity(root)
    book = {**book, **identity}
    content = {
        key: list(value) if isinstance(value, list) else value
        for key, value in DEFAULT_CONTENT.items()
    }
    for field in ("front", "back"):
        values = content[field]
        if not isinstance(values, list) or not values or len(values) != len(set(values)):
            _fail(f"content {field} must be a unique nonempty path array")
        for value in values:
            _relative(value, f"content {field} path", ".qmd")
    for field in ("chapter_directory", "appendix_directory"):
        _relative(content[field], f"content {field}")
    _relative(content["bibliography"], "content bibliography", ".bib")
    excerpt = _exact(document["excerpt"], {"chapters", "message"}, "excerpt settings")
    if (
        not isinstance(excerpt["chapters"], list)
        or not 1 <= len(excerpt["chapters"]) <= 2
        or len(excerpt["chapters"]) != len(set(excerpt["chapters"]))
    ):
        _fail("excerpt chapters must select one or two unique chapter filenames")
    for value in excerpt["chapters"]:
        if not isinstance(value, str) or CHAPTER.fullmatch(value) is None:
            _fail("excerpt chapter names must use NN-kebab-case.qmd")
    _plain(excerpt["message"], "excerpt message")
    theme = _optional(document.get("theme", {}), set(), {"colors", "typography"}, "theme settings")
    theme = {
        "colors": theme.get("colors", {}),
        "typography": theme.get("typography", {}),
    }
    if not isinstance(theme["colors"], dict) or not isinstance(theme["typography"], dict):
        _fail("theme colors and typography must be tables")
    if not set(theme["colors"]) <= set(COLOR_FIELDS):
        _fail("theme override colors contain an unknown field")
    if not set(theme["typography"]) <= set(FONT_FIELDS):
        _fail("theme override typography contains an unknown field")
    for field, value in theme["colors"].items():
        if not isinstance(value, str) or HEX_COLOR.fullmatch(value) is None:
            _fail(f"theme color {field} must use #RRGGBB")
    for field, value in theme["typography"].items():
        if not isinstance(value, str) or FONT_NAME.fullmatch(value) is None:
            _fail(f"theme font {field} contains unsupported characters")
    return {
        "schema_version": document["schema_version"],
        "book": book,
        "content": content,
        "excerpt": excerpt,
        "theme": theme,
    }


def discover_content(root, config):
    """Discover numbered chapters and appendices without duplicate manifests."""
    root = Path(root)
    content = config["content"]
    for relative in [*content["front"], *content["back"], content["bibliography"]]:
        if not (root / relative).is_file():
            _fail(f"configured author file is missing: {relative}")
    discovered = {}
    for kind, field in (("chapters", "chapter_directory"), ("appendices", "appendix_directory")):
        directory = root / content[field]
        if not directory.is_dir():
            _fail(f"content directory is missing: {content[field]}")
        invalid = [
            path.name for path in directory.glob("*.qmd") if CHAPTER.fullmatch(path.name) is None
        ]
        if invalid:
            _fail(f"{kind} filename must use NN-kebab-case.qmd: {min(invalid)}")
        discovered[kind] = [
            path.relative_to(root).as_posix() for path in sorted(directory.glob("*.qmd"))
        ]
    if not discovered["chapters"]:
        _fail("book needs at least one numbered chapter")
    chapter_names = {PurePosixPath(path).name for path in discovered["chapters"]}
    missing_excerpt = set(config["excerpt"]["chapters"]) - chapter_names
    if missing_excerpt:
        _fail(f"excerpt references a missing chapter: {min(missing_excerpt)}")
    all_sources = [
        *content["front"],
        *discovered["chapters"],
        *discovered["appendices"],
        *content["back"],
    ]
    if len(all_sources) != len(set(all_sources)):
        _fail("author content paths must be unique")
    discovered["front"] = list(content["front"])
    discovered["back"] = list(content["back"])
    discovered["all"] = all_sources
    discovered["excerpt"] = [
        path
        for path in discovered["chapters"]
        if PurePosixPath(path).name in set(config["excerpt"]["chapters"])
    ]
    return discovered


def _theme_override(config):
    return (
        json.dumps(
            {
                "schema_version": 1,
                "colors": config["theme"]["colors"],
                "typography": config["theme"]["typography"],
            },
            indent=2,
            sort_keys=True,
        )
        + "\n"
    ).encode()


def _release_record(config, discovered):
    book = config["book"]
    sources = {}
    ids = {}
    for role in ("front", "chapters", "appendices", "back"):
        target_role = {
            "front": "front",
            "chapters": "chapter",
            "appendices": "appendix",
            "back": "back",
        }[role]
        for path in discovered[role]:
            base = PurePosixPath(path).stem
            source_id = base if re.fullmatch(r"[a-z][a-z0-9-]*", base) else f"source-{base}"
            if source_id in sources:
                _fail(f"discovered source IDs collide: {source_id}")
            sources[source_id] = {"path": path, "role": target_role, "availability": "release"}
            ids[path] = source_id
    full_chapters = [
        ids[path] for path in [*discovered["front"], *discovered["chapters"], *discovered["back"]]
    ]
    full_appendices = [ids[path] for path in discovered["appendices"]]
    excerpt_chapters = [
        ids[path] for path in [*discovered["front"], *discovered["excerpt"], *discovered["back"]]
    ]
    return {
        "schema_version": 1,
        "sources": sources,
        "profiles": {
            "full": {
                "chapters": full_chapters,
                "appendices": full_appendices,
                "metadata": {
                    "subtitle": book["subtitle"],
                    "description": book["description"],
                    "edition": "Development edition",
                    "identifier": book["identifier"],
                },
                "presentation": {},
            },
            "preview": {
                "chapters": excerpt_chapters,
                "appendices": [],
                "metadata": {
                    "subtitle": f"Excerpt from {book['title']}",
                    "description": f"A selected-chapter excerpt from {book['title']}.",
                    "edition": "Excerpt edition; not the complete book.",
                    "identifier": book["excerpt_identifier"],
                },
                "presentation": {"message": config["excerpt"]["message"]},
            },
        },
    }


def _metadata(config):
    book = config["book"]
    return f"""# Generated from book.toml; do not edit.
book:
  title: {_quote(book["title"])}
  subtitle: {_quote(book["subtitle"])}
  author:
    - name: {_quote(book["author"])}
  description: {_quote(book["description"])}
author:
  - name: {_quote(book["author"])}
date: {_quote(book["created"])}
lang: {_quote(book["language"])}
description: {_quote(book["description"])}
alkahest:
  work-id: {_quote(book["id"])}
  publication-status: "development"
  edition: "Development edition"
  identifier: {_quote(book["identifier"])}
""".encode()


def _author_release_profile(content):
    """Keep product metadata on the book without overriding chapter headings."""
    lines = content.decode("utf-8").splitlines()
    lines = [
        line
        for line in lines
        if not line.startswith("subtitle: ") and not line.startswith("description: ")
    ]
    return ("\n".join(lines) + "\n").encode("utf-8")


def _structure(sources, appendices):
    lines = ["  chapters:", *[f"    - {path}" for path in sources]]
    if appendices:
        lines.extend(["  appendices:", *[f"    - {path}" for path in appendices]])
    return "\n".join(lines)


def _quarto(config, sources, appendices):
    bibliography = config["content"]["bibliography"]
    return f"""project:
  type: book

metadata-files:
  - alkahest-defaults.yml
  - generated/theme-metadata.yml
  - generated/metadata.yml

book:
{_structure(sources, appendices)}

bibliography: {bibliography}
""".encode()


FORMAT_PROFILES = {
    "html": b"""project:\n  output-dir: _output/html\n\nbrand: false\n\nformat:\n  html:\n    code-copy: true\n    include-before-body: theme/accessibility-before-body.html\n    code-overflow: scroll\n    html-math-method: mathml\n    theme: theme/alkahest.scss\n    css:\n      - theme/alkahest-fonts.css\n      - generated/theme-overrides.css\n""",
    "epub": b"""project:\n  output-dir: _output/epub\n\nformat:\n  epub:\n    css:\n      - theme/alkahest-epub.css\n      - generated/theme-overrides.css\n    epub-fonts:\n      - theme/fonts/LibertinusSerif-Regular.woff2\n      - theme/fonts/LibertinusSerif-Italic.woff2\n      - theme/fonts/LibertinusSerif-Bold.woff2\n      - theme/fonts/LibertinusSerif-BoldItalic.woff2\n      - theme/fonts/LibertinusSerifDisplay-Regular.woff2\n      - theme/fonts/LibertinusSans-Regular.woff2\n      - theme/fonts/LibertinusSans-Italic.woff2\n      - theme/fonts/LibertinusSans-Bold.woff2\n      - theme/fonts/SourceCodePro-Regular.otf.woff2\n      - theme/fonts/SourceCodePro-It.otf.woff2\n      - theme/fonts/SourceCodePro-Bold.otf.woff2\n      - theme/fonts/SourceCodePro-BoldIt.otf.woff2\n""",
    "typst": b"""project:\n  output-dir: _output/typst\n\ntrim-width: 7in\ntrim-height: 10in\nbody-font-size: 10pt\nbody-leading: 3pt\nparagraph-indent: 1em\nparagraph-spacing: 3pt\n\nformat:\n  typst:\n    citeproc: true\n    keep-typ: true\n    template-partials:\n      - typst/typst-show.typ\n    margin:\n      top: 0.70in\n      bottom: 0.80in\n    margin-geometry:\n      inner:\n        far: 0.85in\n        width: 0in\n        separation: 0in\n      outer:\n        far: 0.70in\n        width: 0in\n        separation: 0in\n      clearance: 8pt\n""",
    "latex": b"""project:\n  output-dir: _output/latex\n\nformat:\n  pdf:\n    fig-pos: htbp\n    documentclass: scrbook\n    classoption: [twoside, openright]\n    pdf-engine: lualatex\n    keep-tex: true\n    include-in-header:\n      - latex/book-layout.tex\n      - generated/theme-overrides.tex\n    template-partials:\n      - latex/title.tex\n      - latex/before-body.tex\n    geometry: [paperwidth=7in, paperheight=10in, inner=0.85in, outer=0.70in, top=0.70in, bottom=0.80in]\n""",
}


EMPTY_REGISTRIES = {
    "companion.json": b'{"version": 1, "items": {}, "bundles": {}}\n',
    "generated-lists.yml": b"version: 1\nlang: en-US\norder: []\nlists: {}\nobjects: []\nterms: {}\n",
    "glossary.yml": b"version: 1\nlang: en-US\nterms: {}\n",
    "index.yml": b"version: 1\nlang: en-US\nentries: {}\n",
    "media.json": b'{"version": 1, "items": {}}\n',
    "notes.yml": b"version: 1\norder: []\nnotes: {}\n",
    "reusable-content.json": b'{"version": 1, "items": {}}\n',
}


def _safe_remove_workspace(path, root):
    expected_parent = root / "_build" / ".work"
    if path.parent != expected_parent or path.name not in PROFILES:
        _fail("refusing unsafe author workspace cleanup")
    if path.exists() or path.is_symlink():
        shutil.rmtree(path)


def compile_workspace(root, engine_root, profile="full"):
    """Create one disposable full or excerpt Quarto workspace."""
    root = Path(root).resolve()
    engine_root = Path(engine_root).resolve()
    if profile not in PROFILES:
        _fail(f"unknown author profile {profile!r}")
    config = load_author_config(root)
    discovered = discover_content(root, config)
    stage = root / "_build" / ".work" / profile
    _safe_remove_workspace(stage, root)
    stage.mkdir(parents=True)
    for directory in ("_extensions", "filters", "latex", "theme", "typst"):
        source = engine_root / directory
        if not source.is_dir():
            _fail(f"engine runtime is missing {directory}")
        (stage / directory).symlink_to(Path(os.path.relpath(source, stage)))
    defaults = engine_root / "defaults"
    (stage / "alkahest-defaults.yml").symlink_to(
        Path(os.path.relpath(defaults / "quarto.yml", stage))
    )
    try:
        theme, theme_files = theme_outputs(
            (defaults / "theme.json").read_bytes(), _theme_override(config)
        )
    except ThemeError as error:
        _fail(str(error).removeprefix("error: "))
    release_record = _release_record(config, discovered)
    release_content = (json.dumps(release_record, indent=2, sort_keys=True) + "\n").encode()
    try:
        resolved, release_files = release_outputs(
            (defaults / "releases.json").read_bytes(), release_content
        )
    except ReleaseProfileError as error:
        _fail(str(error).removeprefix("error: "))
    selected_name = "full" if profile == "full" else "preview"
    selected = resolved["profiles"][selected_name]
    source_paths = [
        resolved["sources"][item]["path"]
        for item in [*selected["chapters"], *selected["appendices"]]
    ]
    stage_paths = []
    for relative in source_paths:
        source = root / relative
        stage_relative = "index.qmd" if relative == config["content"]["front"][0] else relative
        stage_paths.append(stage_relative)
        destination = stage / stage_relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.symlink_to(Path(os.path.relpath(source, destination.parent)))
    bibliography = config["content"]["bibliography"]
    bibliography_target = stage / bibliography
    bibliography_target.parent.mkdir(parents=True, exist_ok=True)
    bibliography_target.symlink_to(
        Path(os.path.relpath(root / bibliography, bibliography_target.parent))
    )
    assets = root / "assets"
    if assets.is_dir():
        (stage / "assets").symlink_to(Path(os.path.relpath(assets, stage)))
    generated = stage / "generated"
    generated.mkdir()
    for relative, content in theme_files.items():
        target = stage / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(content)
    (generated / "metadata.yml").write_bytes(_metadata(config))
    (generated / "release-profile-manifest.json").write_bytes(
        release_files["generated/release-profile-manifest.json"]
    )
    for name, content in EMPTY_REGISTRIES.items():
        authored = root / name
        target = stage / name
        if authored.is_file():
            target.symlink_to(Path(os.path.relpath(authored, stage)))
        else:
            target.write_bytes(content.replace(b"en-US", config["book"]["language"].encode()))
    (stage / "_quarto.yml").write_bytes(
        _quarto(
            config,
            stage_paths[: len(selected["chapters"])],
            stage_paths[len(selected["chapters"]) :],
        )
    )
    for name, content in FORMAT_PROFILES.items():
        (stage / f"_quarto-{name}.yml").write_bytes(content)
    (stage / f"_quarto-release-{selected_name}.yml").write_bytes(
        _author_release_profile(release_files[f"_quarto-release-{selected_name}.yml"])
    )
    manifest = {
        "schema_version": 1,
        "profile": profile,
        "book_toml_sha256": _sha256((root / "book.toml").read_bytes()),
        "sources": source_paths,
        "theme": theme,
    }
    (stage / "author-workspace.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    return {"stage": stage, "sources": source_paths, "config": config}


def add_chapter(root, title):
    """Create the next numbered chapter without editing a second manifest."""
    root = Path(root).resolve()
    title = _plain(title, "chapter title")
    config = load_author_config(root)
    discover_content(root, config)
    directory = root / config["content"]["chapter_directory"]
    numbers = [int(path.name[:2]) for path in directory.glob("*.qmd")]
    number = max(numbers, default=0) + 1
    if number > 99:
        _fail("chapter numbering supports at most 99 chapters")
    slug = _slug(title)
    if not slug:
        _fail("chapter title must produce an ASCII filename; rename it explicitly")
    path = directory / f"{number:02d}-{slug}.qmd"
    if path.exists():
        _fail(f"chapter already exists: {path.name}")
    path.write_text(f"# {title}\n\nStart writing here.\n", encoding="utf-8")
    return path


def doctor(root):
    """Validate author inputs and report the available rendering environment."""
    root = Path(root).resolve()
    config = load_author_config(root)
    discovered = discover_content(root, config)
    configured_quarto = os.environ.get("QUARTO")
    quarto = configured_quarto or shutil.which("quarto")
    if quarto is not None:
        try:
            result = run_process(
                [quarto, "--version"],
                check=True,
                capture_output=True,
                text=True,
                timeout=15,
            )
        except (OSError, subprocess.CalledProcessError, subprocess.TimeoutExpired) as error:
            if configured_quarto:
                _fail(f"QUARTO={configured_quarto!r} cannot run: {error}")
            _fail(f"Quarto on PATH cannot run: {error}")
        version = (result.stdout or result.stderr).strip().splitlines()
        return {
            "mode": "local",
            "renderer": f"Quarto {version[0] if version else 'version unknown'}",
            "chapters": len(discovered["chapters"]),
        }
    podman = shutil.which("podman")
    if podman is None:
        _fail(
            "no renderer is available; install Quarto or install Podman and build "
            "the pinned Alkahest publishing image"
        )
    image = os.environ.get("ALKAHEST_TOOLCHAIN_IMAGE", TOOLCHAIN_IMAGE)
    try:
        available = (
            run_process(
                [podman, "image", "exists", image],
                check=False,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                timeout=15,
            ).returncode
            == 0
        )
    except (OSError, subprocess.TimeoutExpired) as error:
        _fail(f"Podman cannot inspect the pinned publishing image: {error}")
    if not available:
        _fail(
            f"pinned publishing image {image!r} is unavailable; run `make bootstrap` "
            "in the Alkahest toolkit or install Quarto locally"
        )
    return {
        "mode": "container",
        "renderer": f"rootless Podman image {image}",
        "chapters": len(discovered["chapters"]),
    }


def render(root, engine_root, profile, formats):
    """Compile and render selected formats from one disposable workspace."""
    unknown = set(formats) - FORMATS
    if unknown:
        _fail(f"unknown render format: {min(unknown)}")
    if profile == "excerpt" and "latex" in formats:
        _fail("excerpt output does not include the LuaLaTeX diagnostic profile")
    result = compile_workspace(root, engine_root, profile)
    release = "full" if profile == "full" else "preview"
    root = Path(root).resolve()
    created = datetime.fromisoformat(result["config"]["book"]["created"])
    epoch = int(created.replace(tzinfo=UTC).timestamp())
    render_environment = os.environ.copy()
    render_environment["SOURCE_DATE_EPOCH"] = str(epoch)
    render_environment["FORCE_SOURCE_DATE"] = "1"
    configured_quarto = os.environ.get("QUARTO")
    quarto = configured_quarto or shutil.which("quarto")
    container: list[str] | None = None
    if quarto is None and shutil.which("podman"):
        image = os.environ.get("ALKAHEST_TOOLCHAIN_IMAGE", TOOLCHAIN_IMAGE)
        available = (
            run_process(
                ["podman", "image", "exists", image],
                check=False,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            ).returncode
            == 0
        )
        if available:
            relative_stage = result["stage"].relative_to(root).as_posix()
            container_tmp = PurePosixPath("/") / "tmp"
            container = [
                "podman",
                "run",
                "--rm",
                "--pull=never",
                "--network=none",
                "--userns=keep-id",
                "--user",
                f"{os.getuid()}:{os.getgid()}",
                "--security-opt",
                "label=disable",
                "--tmpfs",
                f"{container_tmp}:rw,size=2g,mode=1777",
                "--env",
                f"HOME={container_tmp}",
                "--env",
                f"JAVA_TOOL_OPTIONS=-Duser.home={container_tmp}",
                "--env",
                f"TEXMFCACHE={container_tmp}",
                "--env",
                f"TEXMFVAR={container_tmp}",
                "--env",
                f"XDG_CACHE_HOME={container_tmp / 'cache'}",
                "--env",
                f"SOURCE_DATE_EPOCH={epoch}",
                "--env",
                "FORCE_SOURCE_DATE=1",
                "--volume",
                f"{root}:/alkahest-book:rw",
                "--workdir",
                f"/alkahest-book/{relative_stage}",
                image,
                "quarto",
            ]
    if quarto is None and container is None:
        _fail("Quarto is not on PATH and the pinned Alkahest Podman image is unavailable")
    for format_name in formats:
        print(f"rendering: {profile} {format_name}", flush=True)
        if quarto is not None:
            command = [quarto, "render", "--profile", f"release-{release},{format_name}"]
        elif container is not None:
            command = [
                *container,
                "render",
                "--profile",
                f"release-{release},{format_name}",
            ]
        else:
            _fail("renderer selection failed")
        try:
            completed = run_process(
                command,
                cwd=result["stage"],
                check=False,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                env=render_environment,
            )
        except OSError as error:
            _fail(f"{format_name} render could not start: {error}")
        if completed.returncode:
            detail = completed.stdout.strip()
            suffix = f"\n{detail}" if detail else ""
            _fail(f"{format_name} render failed with status {completed.returncode}{suffix}")
        generated = result["stage"] / "_output" / format_name
        destination = root / "_build" / profile / format_name
        if not generated.is_dir():
            _fail(f"{format_name} render did not create its expected output directory")
        if destination.parent != root / "_build" / profile:
            _fail("refusing unsafe author output replacement")
        if destination.is_symlink() or destination.is_file():
            destination.unlink()
        elif destination.is_dir():
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
