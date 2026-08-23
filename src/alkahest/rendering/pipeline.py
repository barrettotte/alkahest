"""Render publication profiles through the locked Quarto boundary."""

from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

from ..markup import canonicalize_markup
from .canonicalize import candidates

ROOT = Path(__file__).resolve().parents[3]
BOOK = ROOT / "book"
BUILD = BOOK / "_build"
QUARTO = ROOT / "scripts" / "quarto.sh"
DEFAULT_PDF_PROFILE = "typst"


class RenderError(RuntimeError):
    """Report a failed or unsafe render operation."""


@dataclass(frozen=True)
class RenderSpec:
    """One isolated edition/profile/output render."""

    edition: str
    profile: str
    output: str


SPECS = {
    "html": RenderSpec("web", "html", "_build/html"),
    "epub": RenderSpec("epub", "epub", "_build/epub"),
    "typst": RenderSpec("print", "typst", "_build/print/7x10/typst"),
    "latex": RenderSpec("print", "latex", "_build/print/7x10/latex"),
    "typst-6x9": RenderSpec("print", "typst-6x9", "_build/print/6x9/typst"),
    "latex-6x9": RenderSpec("print", "latex-6x9", "_build/print/6x9/latex"),
    "typst-review": RenderSpec("print", "typst-review", "_build/review/letter/typst"),
    "latex-review": RenderSpec("print", "latex-review", "_build/review/letter/latex"),
    "locale-fr": RenderSpec("web", "locale-fr,html", "_build/locale/fr/html"),
    "citation-html": RenderSpec(
        "web", "citation-numeric,html", "_build/smoke/citations/numeric/html"
    ),
    "citation-typst": RenderSpec(
        "print", "citation-numeric,typst", "_build/smoke/citations/numeric/typst"
    ),
    "preview-html": RenderSpec("preview", "preview,html", "_build/smoke/editions/preview/html"),
    "preview-epub": RenderSpec("preview", "preview,epub", "_build/smoke/editions/preview/epub"),
    "preview-typst": RenderSpec("preview", "preview,typst", "_build/smoke/editions/preview/typst"),
    "abridged-html": RenderSpec("abridged", "html", "_build/smoke/editions/abridged/html"),
    "public-html": RenderSpec("public", "html", "_build/smoke/editions/public/html"),
    "private-html": RenderSpec("private", "html", "_build/smoke/editions/private/html"),
    "supplemental-html": RenderSpec(
        "supplemental", "html", "_build/smoke/editions/supplemental/html"
    ),
    "notes-chapter": RenderSpec("web", "html,notes-chapter", "_build/smoke/notes/chapter/html"),
    "notes-book": RenderSpec("web", "html,notes-book", "_build/smoke/notes/book/html"),
    "notes-sidenote-html": RenderSpec(
        "web", "html,notes-sidenote", "_build/smoke/notes/sidenote/html"
    ),
    "notes-sidenote-typst": RenderSpec(
        "print", "notes-sidenote-typst", "_build/smoke/notes/sidenote/typst"
    ),
    "pdf-ua-typst": RenderSpec(
        "print", "typst,pdf-ua-typst", "_build/smoke/pdf-accessibility/typst"
    ),
    "pdf-ua-latex": RenderSpec(
        "print", "latex,pdf-ua-latex", "_build/smoke/pdf-accessibility/lualatex"
    ),
}

PDF_PROFILES = (
    "typst",
    "latex",
    "typst-6x9",
    "latex-6x9",
    "typst-review",
    "latex-review",
)

PLANS = {
    "html": ("html",),
    "epub": ("epub",),
    "pdf": (DEFAULT_PDF_PROFILE,),
    "typst": ("typst",),
    "latex": ("latex",),
    "print-6x9": ("typst-6x9", "latex-6x9"),
    "review": ("typst-review", "latex-review"),
    "pdf-profiles": PDF_PROFILES,
    "locale-smoke": ("locale-fr",),
    "citation-smoke": ("citation-html", "citation-typst"),
    "preview": ("preview-html", "preview-epub", "preview-typst"),
    "edition-smoke": (
        "abridged-html",
        "preview-html",
        "preview-epub",
        "preview-typst",
        "public-html",
        "private-html",
        "supplemental-html",
    ),
    "notes-smoke": (
        "notes-chapter",
        "notes-book",
        "notes-sidenote-html",
        "notes-sidenote-typst",
    ),
    "pdf-ua-typst": ("pdf-ua-typst",),
    "pdf-ua-latex": ("pdf-ua-latex",),
    "pdf-accessibility-smoke": ("pdf-ua-typst", "pdf-ua-latex"),
    "all": ("html", "epub", "typst", "latex"),
    "complete": (
        "html",
        "epub",
        *PDF_PROFILES,
        "locale-fr",
        "citation-html",
        "citation-typst",
        "abridged-html",
        "preview-html",
        "preview-epub",
        "preview-typst",
        "public-html",
        "private-html",
        "supplemental-html",
        "notes-chapter",
        "notes-book",
        "notes-sidenote-html",
        "notes-sidenote-typst",
    ),
}


def run(arguments: list[str], *, stdout=None) -> None:
    """Run one closed render command."""
    result = subprocess.run(  # noqa: S603 - commands come from the fixed pipeline
        arguments,
        cwd=ROOT,
        stdout=stdout,
        check=False,
    )
    if result.returncode:
        raise RenderError(
            f"render command failed with status {result.returncode}: {' '.join(arguments)}"
        )


def operation(name: str, *arguments: str, quiet: bool = False) -> None:
    """Run one direct Alkahest operation."""
    output = subprocess.DEVNULL if quiet else None
    run([sys.executable, "-m", "alkahest.operations", name, *arguments], stdout=output)


def canonicalize(directory: Path) -> None:
    """Stabilize serialized HTML attributes after promotion."""
    for document in candidates([directory]):
        original = document.read_text(encoding="utf-8")
        normalized = canonicalize_markup(original)
        if normalized != original:
            document.write_text(normalized, encoding="utf-8")


def render_spec(spec: RenderSpec) -> None:
    """Stage, render, and atomically promote one edition profile."""
    stage_arguments = [spec.edition]
    if "html" in spec.profile.split(","):
        stage_arguments.append("--html-resources")
    operation("stage-edition", *stage_arguments, quiet=True)

    stage_root = BUILD / "staging" / "editions" / spec.edition
    staged_output = stage_root / "_rendered"
    run(
        [
            str(QUARTO),
            "render",
            f"book/_build/staging/editions/{spec.edition}",
            "--profile",
            f"edition-{spec.edition},{spec.profile}",
            "--output-dir",
            "_rendered",
        ]
    )

    for suffix in ("typ", "tex"):
        source = stage_root / f"index.{suffix}"
        if source.is_file():
            shutil.copyfile(source, staged_output / f"Alkahest-Reference-Book.{suffix}")

    destination = BOOK / spec.output
    try:
        destination.relative_to(BUILD)
    except ValueError as error:
        raise RenderError(f"unsafe canonical render path: {destination}") from error
    if not staged_output.exists():
        raise RenderError(f"render did not create staged output: {staged_output}")
    destination.parent.mkdir(parents=True, exist_ok=True)
    if destination.exists():
        shutil.rmtree(destination)
    staged_output.rename(destination)

    source_licenses = BOOK / "theme" / "fonts" / "licenses"
    rendered_fonts = destination / "theme" / "fonts"
    if rendered_fonts.is_dir() and source_licenses.is_dir():
        shutil.copytree(source_licenses, rendered_fonts / "licenses", dirs_exist_ok=True)
    if "html" in spec.profile.split(","):
        canonicalize(destination)


def render(target: str) -> None:
    """Render one public profile or aggregate plan."""
    try:
        steps = PLANS[target]
    except KeyError as error:
        raise RenderError(f"unknown render profile: {target}") from error
    failures: list[str] = []
    for step in steps:
        try:
            render_spec(SPECS[step])
            if step == "epub":
                operation("finalize-epub")
            elif step == "preview-epub":
                operation(
                    "finalize-epub",
                    "--reduced",
                    str(BUILD / "smoke/editions/preview/epub/Alkahest-Reference-Book.epub"),
                )
        except (OSError, RenderError, UnicodeError):
            if target != "pdf-accessibility-smoke":
                raise
            failures.append(step)
    if failures:
        raise RenderError("PDF accessibility renders failed: " + ", ".join(failures))


def main(arguments: list[str] | None = None) -> int:
    """Render a selected publication profile."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("profile", choices=tuple(PLANS))
    options = parser.parse_args(arguments)
    try:
        render(options.profile)
    except (OSError, RenderError, UnicodeError) as error:
        print(f"error: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
