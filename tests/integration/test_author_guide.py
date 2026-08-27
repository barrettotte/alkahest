"""Render the author guide through its self-contained rootless container."""

import shutil
import tempfile
import zipfile
from pathlib import Path

import pytest

from alkahest.process import run_process

ROOT = Path(__file__).resolve().parents[2]
GUIDE = ROOT / "guide"
FOOTNOTE = "Native named footnotes stay simple and portable."


def guide_copy(destination: Path) -> Path:
    """Copy the author guide into one isolated test directory."""
    target = destination / "guide"
    shutil.copytree(
        GUIDE,
        target,
        ignore=shutil.ignore_patterns("_build", "cache", ".uv-cache", "__pycache__"),
    )
    return target


def run_make(book: Path, target: str) -> None:
    """Run one author-facing Make target."""
    result = run_process(
        ["make", target],
        cwd=book,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stdout + result.stderr


@pytest.mark.locked
def test_author_guide_builds_full_and_excerpt_outputs() -> None:
    """Build complete and excerpt guide publications."""
    with tempfile.TemporaryDirectory(prefix="alkahest-author-guide.") as temporary:
        guide = guide_copy(Path(temporary))
        run_make(guide, "bootstrap")
        run_make(guide, "build")
        run_make(guide, "excerpt")

        for profile in ("full", "excerpt"):
            output = guide / "_build" / profile
            html = output / "html/manuscript/chapters/02-write-and-organize.html"
            assert FOOTNOTE in html.read_text(encoding="utf-8")
            assert list((output / "html").rglob("LibertinusSerif-Regular.woff2"))

            epub = output / "epub/Writing-Books-with-Alkahest.epub"
            with zipfile.ZipFile(epub) as package:
                assert any(name.endswith("LibertinusSerif-Regular.woff2") for name in package.namelist())
                epub_text = "".join(
                    package.read(name).decode("utf-8", errors="ignore")
                    for name in package.namelist()
                    if name.lower().endswith((".html", ".xhtml"))
                )
            assert FOOTNOTE in epub_text

            pdf = output / "typst/Writing-Books-with-Alkahest.pdf"
            assert pdf.is_file() and pdf.stat().st_size > 10_000
