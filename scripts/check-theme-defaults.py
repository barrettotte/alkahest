"""Validate shared theme defaults and exact generated format adapters."""

import json
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR / "lib"))

from alkahest.theme import ThemeError, sync_project_theme, theme_outputs


ROOT = SCRIPT_DIR.parent


def validate_integration():
    files = {
        "makefile": ROOT / "Makefile",
        "dispatcher": ROOT / "scripts/check-source.py",
        "ci": ROOT / "scripts/ci.sh",
        "readme": ROOT / "README.md",
        "documentation": ROOT / "docs/theme-overrides.md",
        "template_policy": ROOT / "config/template/template-package.json",
        "new_book_policy": ROOT / "config/template/new-book.json",
    }
    texts = {name: path.read_text(encoding="utf-8") for name, path in files.items()}
    for marker in ("generate-theme:", "check-theme-defaults:", "test-theme-defaults:"):
        if marker not in texts["makefile"]:
            raise ThemeError(f"error: Makefile is missing theme target {marker}")
    for marker in (
        '("theme-defaults", "check-theme-defaults.py", False)',
        '("theme-defaults", "test-theme-defaults.py", False)',
    ):
        if marker not in texts["dispatcher"]:
            raise ThemeError(f"error: source dispatcher is missing {marker}")
    if 'sync-theme.py" --check' not in texts["ci"]:
        raise ThemeError("error: CI is missing exact theme-adapter verification")
    if "make generate-theme" not in texts["readme"]:
        raise ThemeError("error: README is missing the theme author command")
    for marker in (
        "book/theme.json",
        "book/alkahest-theme-defaults.json",
        "make check-theme-defaults",
        "Shared defaults",
        "per-book override",
    ):
        if marker not in texts["documentation"]:
            raise ThemeError(f"error: theme documentation is missing {marker!r}")
    for marker in (
        '"destination": "defaults/quarto.yml"',
        '"destination": "defaults/theme.json"',
        '"destination": "scripts/sync-theme.py"',
    ):
        if marker not in texts["template_policy"]:
            raise ThemeError(f"error: template package is missing theme member {marker}")
    for marker in (
        '".alkahest/alkahest-book-template-engine-0.2.0.zip"',
        '"book.toml"',
        '"scripts/author.py"',
    ):
        if marker not in texts["new_book_policy"]:
            raise ThemeError(f"error: new-book policy is missing theme path {marker}")


def main():
    validate_integration()
    result = sync_project_theme(ROOT, check=True)
    defaults = (ROOT / "book/alkahest-theme-defaults.json").read_bytes()
    override = json.dumps(
        {
            "schema_version": 1,
            "colors": {"primary": "#1d4ed8", "accent": "#b45309"},
            "typography": {"display": "Libertinus Sans"},
        },
        sort_keys=True,
    ).encode("utf-8")
    first_theme, first = theme_outputs(defaults, override)
    second_theme, second = theme_outputs(defaults, override)
    if first != second or first_theme != second_theme:
        raise ThemeError("error: resolved theme adapters are not deterministic")
    required = (b"#1d4ed8", b"1D4ED8")
    for path in ("_brand.yml", "generated/theme-overrides.css"):
        if required[0] not in first[path]:
            raise ThemeError(f"error: theme override did not reach {path}")
    if required[1] not in first["generated/theme-overrides.tex"]:
        raise ThemeError("error: theme override did not reach LuaLaTeX")
    if b"renewfontfamily\\alkahestdisplayfont{Libertinus Sans}" not in first[
        "generated/theme-overrides.tex"
    ]:
        raise ThemeError("error: display-font override did not reach LuaLaTeX")
    if b"Libertinus Sans" not in first["generated/theme-metadata.yml"]:
        raise ThemeError("error: typography override did not reach shared metadata")
    print(
        "ok: shared theme defaults "
        f"({len(result['theme']['colors'])} colors; "
        f"{len(result['theme']['typography'])} font roles; "
        f"{result['outputs']} exact adapters; partial override smoke passed)"
    )


if __name__ == "__main__":
    try:
        main()
    except (OSError, ThemeError, UnicodeError) as error:
        print(error, file=sys.stderr)
        raise SystemExit(1)
