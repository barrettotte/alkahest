"""Cross-file integration checks consolidated from standalone launchers."""

import copy
import json
from pathlib import Path
from typing import Final

from .author_project import TOOLCHAIN_IMAGE
from .release_profiles import ReleaseProfileError, release_outputs, validate_project_releases
from .theme import ThemeError, sync_project_theme, theme_outputs

ROOT: Final = Path(__file__).resolve().parents[2]


def _texts(files: dict[str, Path]) -> dict[str, str]:
    return {name: path.read_text(encoding="utf-8") for name, path in files.items()}


def check_release_profiles() -> None:
    """Check reusable release profiles and a deterministic local override."""
    texts = _texts(
        {
            "makefile": ROOT / "Makefile",
            "tasks": ROOT / "src/alkahest/tasks.py",
            "ci": ROOT / "src/alkahest/ci.py",
            "readme": ROOT / "README.md",
            "documentation": ROOT / "docs/release-profiles.md",
            "containerfile": ROOT / "Containerfile",
            "new_book_policy": ROOT / "config/template/new-book.json",
        }
    )
    for marker in ("generate-%:", "check-%:", "test-%:"):
        if marker not in texts["makefile"]:
            raise ReleaseProfileError(f"error: Makefile is missing target {marker}")
    for marker in (
        '"release-profiles", ":check-release-profiles"',
        '"release-profiles", "sync-release-profiles.py"',
    ):
        if marker not in texts["tasks"]:
            raise ReleaseProfileError(f"error: task registry is missing {marker}")
    if "alkahest check" not in texts["ci"]:
        raise ReleaseProfileError("error: CI is missing release-profile verification")
    if "make generate-release-profiles" not in texts["readme"]:
        raise ReleaseProfileError("error: README is missing the release author command")
    for marker in (
        "book/releases.json",
        "full",
        "preview",
        "chapter allowlist",
        "metadata overrides",
        "isolated",
    ):
        if marker not in texts["documentation"]:
            raise ReleaseProfileError(f"error: release-profile documentation is missing {marker!r}")
    for marker in (
        "COPY book/alkahest-release-defaults.json /opt/alkahest/engine/defaults/releases.json",
        "src/alkahest/release_profiles.py",
        "/opt/alkahest/engine/src/alkahest/",
    ):
        if marker not in texts["containerfile"]:
            raise ReleaseProfileError(f"error: runtime image is missing {marker}")
    for marker in (
        f'"engine_image": "{TOOLCHAIN_IMAGE}"',
        '"Containerfile"',
        '"book.toml"',
    ):
        if marker not in texts["new_book_policy"]:
            raise ReleaseProfileError(f"error: new-book policy is missing {marker}")

    result = validate_project_releases(ROOT)
    defaults = (ROOT / "book/alkahest-release-defaults.json").read_bytes()
    local = json.loads((ROOT / "book/releases.json").read_text(encoding="utf-8"))
    overridden = copy.deepcopy(local)
    overridden["profiles"]["preview"]["metadata"]["subtitle"] = "Selected sample"
    overridden["profiles"]["preview"]["presentation"].update(
        {
            "full_edition_url": "https://example.com/full",
            "watermark": {"text": "SAMPLE"},
        }
    )
    content = (json.dumps(overridden, sort_keys=True) + "\n").encode()
    first_resolved, first = release_outputs(defaults, content)
    second_resolved, second = release_outputs(defaults, content)
    if first != second or first_resolved != second_resolved:
        raise ReleaseProfileError("error: release profile adapters are not deterministic")
    preview = first["_quarto-release-preview.yml"]
    for preview_marker in (
        b"Selected sample",
        b"https://example.com/full",
        b"SAMPLE",
        overridden["profiles"]["preview"]["metadata"]["identifier"].encode(),
    ):
        if preview_marker not in preview:
            raise ReleaseProfileError("error: book-local override did not reach preview")
    profiles = result["resolved"]["profiles"]
    print(
        "ok: reusable release profiles "
        f"({len(result['resolved']['sources'])} registered sources; "
        f"full {len(profiles['full']['chapters']) + len(profiles['full']['appendices'])}; "
        f"preview {len(profiles['preview']['chapters']) + len(profiles['preview']['appendices'])}; "
        f"{result['outputs']} exact adapters)"
    )


def check_theme_defaults() -> None:
    """Check shared theme defaults and a deterministic partial override."""
    texts = _texts(
        {
            "makefile": ROOT / "Makefile",
            "tasks": ROOT / "src/alkahest/tasks.py",
            "ci": ROOT / "src/alkahest/ci.py",
            "readme": ROOT / "README.md",
            "documentation": ROOT / "docs/theme-overrides.md",
            "containerfile": ROOT / "Containerfile",
            "new_book_policy": ROOT / "config/template/new-book.json",
        }
    )
    for marker in ("generate-%:", "check-%:", "test-%:"):
        if marker not in texts["makefile"]:
            raise ThemeError(f"error: Makefile is missing theme target {marker}")
    for marker in (
        '"theme-defaults", ":check-theme-defaults"',
        '"theme", "sync-theme.py"',
    ):
        if marker not in texts["tasks"]:
            raise ThemeError(f"error: task registry is missing {marker}")
    if "alkahest check" not in texts["ci"]:
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
        "COPY book/alkahest-defaults.yml /opt/alkahest/engine/defaults/quarto.yml",
        "COPY book/alkahest-theme-defaults.json /opt/alkahest/engine/defaults/theme.json",
        "src/alkahest/theme.py",
    ):
        if marker not in texts["containerfile"]:
            raise ThemeError(f"error: runtime image is missing theme member {marker}")
    for marker in (
        f'"engine_image": "{TOOLCHAIN_IMAGE}"',
        '"Containerfile"',
        '"book.toml"',
    ):
        if marker not in texts["new_book_policy"]:
            raise ThemeError(f"error: new-book policy is missing theme path {marker}")

    result = sync_project_theme(ROOT, check=True)
    defaults = (ROOT / "book/alkahest-theme-defaults.json").read_bytes()
    override = json.dumps(
        {
            "schema_version": 1,
            "colors": {"primary": "#1d4ed8", "accent": "#b45309"},
            "typography": {"display": "Libertinus Sans"},
        },
        sort_keys=True,
    ).encode()
    first_theme, first = theme_outputs(defaults, override)
    second_theme, second = theme_outputs(defaults, override)
    if first != second or first_theme != second_theme:
        raise ThemeError("error: resolved theme adapters are not deterministic")
    if b"#1d4ed8" not in first["_brand.yml"]:
        raise ThemeError("error: theme override did not reach _brand.yml")
    if b"#1d4ed8" not in first["generated/theme-overrides.css"]:
        raise ThemeError("error: theme override did not reach generated/theme-overrides.css")
    if b"1D4ED8" not in first["generated/theme-overrides.tex"]:
        raise ThemeError("error: theme override did not reach LuaLaTeX")
    if (
        b"renewfontfamily\\alkahestdisplayfont{Libertinus Sans}"
        not in first["generated/theme-overrides.tex"]
    ):
        raise ThemeError("error: display-font override did not reach LuaLaTeX")
    if b"Libertinus Sans" not in first["generated/theme-metadata.yml"]:
        raise ThemeError("error: typography override did not reach shared metadata")
    print(
        "ok: shared theme defaults "
        f"({len(result['theme']['colors'])} colors; "
        f"{len(result['theme']['typography'])} font roles; "
        f"{result['outputs']} exact adapters; partial override smoke passed)"
    )


__all__ = [
    "check_release_profiles",
    "check_theme_defaults",
]
