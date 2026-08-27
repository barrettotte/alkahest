"""Run the small rendered-output validation suite."""

from __future__ import annotations

import argparse
import os
import shutil
import sys
import tempfile
from pathlib import Path

from alkahest.pdf_preflight import PreflightError, inspect_pdf
from alkahest.process import run_process

ROOT = Path(__file__).resolve().parents[3]
HTML = ROOT / "book/_build/html"
EPUB = ROOT / "book/_build/epub/Alkahest-Reference-Book.epub"
PDF = ROOT / "book/_build/print/7x10/typst/Alkahest-Reference-Book.pdf"
PDF_PROFILE = {
    "backend": "typst",
    "trim_points": (504, 720),
    "bleed_points": 0,
}
PDF_POLICY = {
    "geometry_tolerance_points": 0.1,
    "continuous_tone_minimum_ppi": 300,
    "one_bit_minimum_ppi": 600,
    "allowed_pdf_versions": ["1.7"],
    "allowed_raster_color_models": [
        {"name": "mono", "components": 1},
        {"name": "gray", "components": 1},
        {"name": "rgb", "components": 3},
        {"name": "icc", "components": 1},
        {"name": "icc", "components": 3},
    ],
}


class SuiteError(RuntimeError):
    """Report one failed external validation command."""


def executable(name: str) -> str:
    """Resolve one executable bundled in the locked image."""
    path = shutil.which(name)
    if path is None:
        raise SuiteError(f"{name} is required for artifact validation")
    return path


def run(arguments: list[str], *, check: bool = True) -> int:
    """Run one external validator."""
    result = run_process(arguments, cwd=ROOT, check=False)
    if check and result.returncode:
        raise SuiteError(f"command failed with status {result.returncode}: {' '.join(arguments)}")
    return result.returncode


def module(name: str, *arguments: str) -> None:
    run([sys.executable, "-m", name, *arguments])


def accessibility() -> None:
    """Check rendered HTML with axe-core."""
    if not HTML.is_dir():
        raise SuiteError("missing rendered HTML; run make render first")
    run([executable("node"), str(ROOT / "scripts/check-accessibility-browser.mjs")])


def epub() -> None:
    """Validate EPUB structure and automated accessibility."""
    if not EPUB.is_file():
        raise SuiteError("missing rendered EPUB; run make render first")
    run([executable("java"), "-jar", os.environ["EPUBCHECK_JAR"], str(EPUB)])
    with tempfile.TemporaryDirectory(prefix="alkahest-ace-") as directory:
        report = Path(directory) / "report"
        status = run(
            [
                executable("ace-cli"),
                "--outdir",
                str(report),
                "--tempdir",
                str(Path(directory) / "temp"),
                "--force",
                "--silent",
                "--exiterror2",
                str(EPUB),
            ],
            check=False,
        )
        module("alkahest.checks.ace_report", str(report / "report.json"))
        if status:
            raise SuiteError(f"Ace by DAISY failed with status {status}")


def publication() -> None:
    """Validate links, EPUB, and the production Typst PDF."""
    module("alkahest.checks.html_links", str(HTML))
    epub()
    if not PDF.is_file():
        raise SuiteError("missing rendered Typst PDF; run make render first")
    try:
        pages, fonts, images = inspect_pdf(PDF, PDF_PROFILE, PDF_POLICY)
    except PreflightError as error:
        raise SuiteError(f"PDF preflight failed: {error}") from error
    print(
        f"ok: Typst 7 x 10 PDF ({pages} pages; no bleed; "
        f"{fonts} embedded/subset fonts; {images} raster images)"
    )


def main(arguments: list[str] | None = None) -> int:
    """Dispatch one rendered-output suite."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("suite", choices=("accessibility", "epub", "publication"))
    options = parser.parse_args(arguments)
    try:
        {
            "accessibility": accessibility,
            "epub": epub,
            "publication": publication,
        }[options.suite]()
    except (KeyError, OSError, SuiteError) as error:
        print(f"error: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
