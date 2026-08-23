"""Resolve book-local theme overrides into deterministic format adapters."""

import hashlib
import json
import re
import unicodedata
from pathlib import Path


COLOR_FIELDS = ("ink", "primary", "muted", "line", "surface", "paper", "accent")
FONT_FIELDS = ("body", "display", "sans", "math", "mono")
HEX_COLOR = re.compile(r"#[0-9a-fA-F]{6}")
FONT_NAME = re.compile(r"[A-Za-z0-9][A-Za-z0-9 ._+\-]*")
OUTPUT_PATHS = (
    "_brand.yml",
    "generated/theme-metadata.yml",
    "generated/theme-overrides.css",
    "generated/theme-overrides.tex",
    "generated/theme-manifest.json",
)


class ThemeError(RuntimeError):
    """A user-facing theme contract violation."""


def _fail(message):
    raise ThemeError(f"error: {message}")


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


def _font(value, label):
    if not isinstance(value, str) or not value or value != value.strip():
        _fail(f"{label} must be a nonempty font-family name")
    if (
        any(unicodedata.category(character) == "Cc" for character in value)
        or FONT_NAME.fullmatch(value) is None
    ):
        _fail(f"{label} contains unsupported characters")
    return value


def _load_document(content, label):
    try:
        return json.loads(content.decode("utf-8"))
    except (UnicodeError, json.JSONDecodeError) as error:
        _fail(f"invalid {label} JSON: {error}")


def validate_documents(defaults, overrides):
    """Validate closed defaults and partial override documents."""
    _exact(defaults, {"schema_version", "colors", "typography"}, "theme defaults")
    if defaults["schema_version"] != 1:
        _fail("theme defaults schema_version must be 1")
    colors = _exact(defaults["colors"], COLOR_FIELDS, "theme default colors")
    typography = _exact(defaults["typography"], FONT_FIELDS, "theme default typography")
    _exact(overrides, {"schema_version", "colors", "typography"}, "theme overrides")
    if overrides["schema_version"] != 1:
        _fail("theme overrides schema_version must be 1")
    if not isinstance(overrides["colors"], dict) or not set(overrides["colors"]) <= set(
        COLOR_FIELDS
    ):
        _fail("theme override colors contain an unknown field")
    if not isinstance(overrides["typography"], dict) or not set(overrides["typography"]) <= set(
        FONT_FIELDS
    ):
        _fail("theme override typography contains an unknown field")
    for field, value in {**colors, **overrides["colors"]}.items():
        if not isinstance(value, str) or HEX_COLOR.fullmatch(value) is None:
            _fail(f"theme color {field} must use #RRGGBB")
    for field, value in {**typography, **overrides["typography"]}.items():
        _font(value, f"theme font {field}")
    return {
        "schema_version": 1,
        "colors": {**colors, **overrides["colors"]},
        "typography": {**typography, **overrides["typography"]},
    }


def _brand(theme):
    colors = theme["colors"]
    fonts = theme["typography"]
    quote = _yaml_string
    return f"""# Generated from alkahest-theme-defaults.json and theme.json; do not edit.
color:
  palette:
    ink: {quote(colors["ink"])}
    slate: {quote(colors["primary"])}
    muted: {quote(colors["muted"])}
    line: {quote(colors["line"])}
    mist: {quote(colors["surface"])}
    paper: {quote(colors["paper"])}
    copper: {quote(colors["accent"])}
  foreground: ink
  background: paper
  primary: slate
  secondary: muted
  tertiary: mist
  warning: copper

typography:
  base:
    family: {quote(fonts["body"])}
  headings:
    family: {quote(fonts["sans"])}
  monospace:
    family: {quote(fonts["mono"])}

defaults:
  bootstrap:
    defaults:
      link-decoration: underline
""".encode("utf-8")


def _metadata(theme):
    fonts = theme["typography"]
    quote = _yaml_string
    return f"""# Generated from the resolved book theme; do not edit.
mainfont: {quote(fonts["body"])}
displayfont: {quote(fonts["display"])}
sansfont: {quote(fonts["sans"])}
mathfont: {quote(fonts["math"])}
monofont: {quote(fonts["mono"])}
""".encode("utf-8")


def _css(theme):
    colors = theme["colors"]
    fonts = theme["typography"]
    return f"""/* Generated from the resolved book theme; do not edit. */
:root {{
  --alkahest-ink: {colors["ink"]};
  --alkahest-primary: {colors["primary"]};
  --alkahest-muted: {colors["muted"]};
  --alkahest-line: {colors["line"]};
  --alkahest-mist: {colors["surface"]};
  --alkahest-paper: {colors["paper"]};
  --alkahest-accent: {colors["accent"]};
}}

html,
body {{
  color: {colors["ink"]};
  color: var(--alkahest-ink);
  background: {colors["paper"]};
  background: var(--alkahest-paper);
  font-family: {json.dumps(fonts["body"])}, Georgia, serif;
}}

h1,
h2,
h3,
h4,
h5,
h6 {{
  color: {colors["primary"]};
  color: var(--alkahest-primary);
  font-family: {json.dumps(fonts["sans"])}, system-ui, sans-serif;
}}

h1.title,
h1 .chapter-title,
.quarto-title-block .title {{
  font-family: {json.dumps(fonts["display"])}, {json.dumps(fonts["body"])}, serif;
}}

a {{
  color: {colors["primary"]};
  color: var(--alkahest-primary);
}}

a:hover,
a:focus-visible {{
  color: {colors["accent"]};
  color: var(--alkahest-accent);
}}

code,
pre {{
  color: {colors["ink"]};
  color: var(--alkahest-ink);
  background: {colors["surface"]};
  background: var(--alkahest-mist);
  font-family: {json.dumps(fonts["mono"])}, ui-monospace, monospace;
}}

blockquote,
.reusable-content,
.rich-media {{
  border-color: {colors["line"]};
  border-color: var(--alkahest-line);
}}

.reusable-content {{
  background: {colors["surface"]};
  background: var(--alkahest-mist);
  border-left-color: {colors["primary"]};
  border-left-color: var(--alkahest-primary);
}}

.reuse-kind-legal,
.alkahest-preview-notice {{
  border-left-color: {colors["accent"]};
  border-left-color: var(--alkahest-accent);
}}

.figure-source,
.diagram-description,
.book-endnote-backlink,
.glossary-entry-forms,
.glossary-page-reference {{
  color: {colors["muted"]};
  color: var(--alkahest-muted);
}}
""".encode("utf-8")


def _tex(theme):
    colors = theme["colors"]
    names = {
        "ink": "AlkahestInk",
        "primary": "AlkahestSlate",
        "muted": "AlkahestMuted",
        "line": "AlkahestLine",
        "surface": "AlkahestMist",
        "accent": "AlkahestCopper",
    }
    lines = ["% Generated from the resolved book theme; do not edit."]
    for field, latex_name in names.items():
        lines.append(f"\\definecolor{{{latex_name}}}{{HTML}}{{{colors[field][1:].upper()}}}")
    lines.append(f"\\renewfontfamily\\alkahestdisplayfont{{{theme['typography']['display']}}}")
    return ("\n".join(lines) + "\n").encode("utf-8")


def theme_outputs(defaults_content, overrides_content):
    """Return resolved theme facts and deterministic adapter bytes."""
    defaults = _load_document(defaults_content, "theme defaults")
    overrides = _load_document(overrides_content, "theme overrides")
    theme = validate_documents(defaults, overrides)
    outputs = {
        "_brand.yml": _brand(theme),
        "generated/theme-metadata.yml": _metadata(theme),
        "generated/theme-overrides.css": _css(theme),
        "generated/theme-overrides.tex": _tex(theme),
    }
    manifest = {
        "schema_version": 1,
        "defaults_sha256": _sha256(defaults_content),
        "overrides_sha256": _sha256(overrides_content),
        "resolved": theme,
        "outputs": [
            {"path": path, "sha256": _sha256(content), "bytes": len(content)}
            for path, content in sorted(outputs.items())
        ],
    }
    outputs["generated/theme-manifest.json"] = _json(manifest)
    return theme, outputs


def project_theme_paths(root):
    """Locate canonical or installed defaults for one repository root."""
    root = Path(root)
    book = root / "book"
    candidates = (
        book / "alkahest-theme-defaults.json",
        book / ".alkahest/theme-defaults.json",
    )
    defaults = next((path for path in candidates if path.is_file()), None)
    if defaults is None:
        _fail("book is missing installed Alkahest theme defaults")
    return book, defaults, book / "theme.json"


def sync_project_theme(root, check=False):
    """Write or exactly verify one project's derived theme adapters."""
    book, defaults_path, overrides_path = project_theme_paths(root)
    try:
        defaults_content = defaults_path.read_bytes()
        overrides_content = overrides_path.read_bytes()
    except OSError as error:
        _fail(f"cannot read book theme inputs: {error}")
    theme, outputs = theme_outputs(defaults_content, overrides_content)
    if check:
        for relative, expected in outputs.items():
            path = book / relative
            if not path.is_file() or path.read_bytes() != expected:
                _fail(f"generated theme adapter is missing or stale: book/{relative}")
    else:
        for relative, content in outputs.items():
            path = book / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(content)
    return {"theme": theme, "outputs": len(outputs), "check": check}
