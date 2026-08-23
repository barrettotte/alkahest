"""Run cross-tool accessibility, preview, and publication artifact suites."""

from __future__ import annotations

import argparse
import os
import shutil
import sys
import tempfile
from pathlib import Path

from alkahest.process import run_process

ROOT = Path(__file__).resolve().parents[3]
INTEGRATION_FIXTURES = ROOT / "tests" / "integration"
EPUB = ROOT / "book" / "_build" / "epub" / "Alkahest-Reference-Book.epub"
PREVIEW_ROOT = ROOT / "book" / "_build" / "smoke" / "editions" / "preview"


class SuiteError(RuntimeError):
    """Report one failed specialist command."""


def executable(name: str) -> str:
    """Resolve one required locked-toolchain command."""
    path = shutil.which(name)
    if path is None:
        raise SuiteError(f"{name} is required for artifact validation")
    return path


def run(arguments: list[str], *, check: bool = True) -> int:
    """Run one command in the current locked environment."""
    result = run_process(
        arguments,
        cwd=ROOT,
        check=False,
    )
    if check and result.returncode:
        raise SuiteError(f"command failed with status {result.returncode}: {' '.join(arguments)}")
    return result.returncode


def module(name: str, *arguments: str) -> None:
    """Run one installed Alkahest module."""
    run([sys.executable, "-m", name, *arguments])


def operation(name: str) -> None:
    """Run one registered direct operation."""
    module("alkahest.operations", name)


def accessibility() -> None:
    """Run deterministic policy and browser accessibility checks."""
    module("alkahest.checks.accessibility_policy")
    if not (ROOT / "book" / "_build" / "html").is_dir():
        raise SuiteError("missing rendered HTML; run make render-html first")
    run([executable("node"), str(ROOT / "scripts" / "check-accessibility-browser.mjs")])


def browser_fixture() -> None:
    """Run the pinned browser against the small accessibility fixture set."""
    run([executable("node"), str(INTEGRATION_FIXTURES / "test-accessibility-browser.mjs")])


def epub_accessibility() -> None:
    """Run EPUB policy, EPUBCheck, and Ace by DAISY checks."""
    operation("check-epub-accessibility-policy")
    run([executable("java"), "-jar", os.environ["EPUBCHECK_JAR"], str(EPUB)])
    with tempfile.TemporaryDirectory(prefix="alkahest-ace-") as directory:
        report_root = Path(directory) / "report"
        temp_root = Path(directory) / "temp"
        ace_status = run(
            [
                executable("ace-cli"),
                "--outdir",
                str(report_root),
                "--tempdir",
                str(temp_root),
                "--force",
                "--silent",
                "--exiterror2",
                str(EPUB),
            ],
            check=False,
        )
        module("alkahest.checks.ace_report", str(report_root / "report.json"))
        if ace_status:
            raise SuiteError(f"Ace by DAISY failed with status {ace_status}")


def preview() -> None:
    """Validate isolated public-preview products."""
    module("alkahest", "check", "--source", "editions")
    module("alkahest.checks.html_links", str(PREVIEW_ROOT / "html"))
    run(
        [
            executable("java"),
            "-jar",
            os.environ["EPUBCHECK_JAR"],
            str(PREVIEW_ROOT / "epub" / "Alkahest-Reference-Book.epub"),
        ]
    )
    operation("check-preview-artifacts")


def publication() -> None:
    """Run cross-format publication conformance checks."""
    html_roots = [
        ROOT / "book" / "_build" / "html",
        ROOT / "book" / "_build" / "locale" / "fr" / "html",
        *(
            ROOT / "book" / "_build" / "smoke" / "editions" / edition / "html"
            for edition in ("abridged", "preview", "public", "private", "supplemental")
        ),
    ]
    for root in html_roots:
        module("alkahest.checks.html_links", str(root))
    for check in ("notes", "identities", "index", "lists"):
        module("alkahest.checks.rendered", check)
    module("alkahest.checks.rendered_localization")
    for epub in (
        EPUB,
        PREVIEW_ROOT / "epub" / "Alkahest-Reference-Book.epub",
    ):
        run([executable("java"), "-jar", os.environ["EPUBCHECK_JAR"], str(epub)])
    operation("check-release-assets")
    operation("check-rights-report")
    module("alkahest.checks.publication")


def main(arguments: list[str] | None = None) -> int:
    """Dispatch one locked artifact suite."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "suite",
        choices=(
            "accessibility",
            "browser-fixture",
            "epub-accessibility",
            "preview",
            "publication",
        ),
    )
    options = parser.parse_args(arguments)
    try:
        if options.suite == "accessibility":
            accessibility()
        elif options.suite == "browser-fixture":
            browser_fixture()
        elif options.suite == "epub-accessibility":
            epub_accessibility()
        elif options.suite == "preview":
            preview()
        else:
            publication()
    except (KeyError, OSError, SuiteError) as error:
        print(f"error: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
