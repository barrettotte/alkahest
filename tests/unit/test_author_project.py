"""Unit tests for the minimal author workflow."""

import os
import subprocess
from collections.abc import Sequence
from pathlib import Path

import pytest

from alkahest import author_project


def write_author_fixture(root: Path) -> None:
    """Create a minimal two-chapter author project."""
    (root / "manuscript/chapters").mkdir(parents=True)
    (root / "manuscript/appendices").mkdir()
    (root / "assets").mkdir()
    (root / "book.toml").write_text(
        """[book]
title = "Fixture Book"
subtitle = "A Test"
author = "Example Author"
language = "fr-CA"
description = "A minimal fixture."

[excerpt]
chapters = ["02-second.qmd"]
message = "Read the complete book for more."
""",
        encoding="utf-8",
    )
    (root / "manuscript/index.qmd").write_text(
        "# Fixture Book\n\n::: {.alkahest-excerpt-placeholder}\n:::\n",
        encoding="utf-8",
    )
    (root / "manuscript/references.qmd").write_text("# References\n", encoding="utf-8")
    (root / "manuscript/chapters/01-first.qmd").write_text("# First\n", encoding="utf-8")
    (root / "manuscript/chapters/02-second.qmd").write_text("# Second\n", encoding="utf-8")
    (root / "manuscript/appendices/01-extra.qmd").write_text("# Extra\n", encoding="utf-8")
    (root / "references.bib").write_text("", encoding="utf-8")
    (root / "glossary.yml").write_text("version: 1\nlang: fr-CA\nterms: {}\n", encoding="utf-8")
    (root / "assets/example.txt").write_text("asset\n", encoding="utf-8")


def write_engine_fixture(root: Path) -> None:
    """Create the engine resources required by workspace compilation."""
    for directory in ("_extensions", "filters", "icons", "theme", "typst", "defaults"):
        (root / directory).mkdir(parents=True)
    (root / "defaults/quarto.yml").write_text("number-sections: true\n", encoding="utf-8")
    (root / "_brand.yml").write_text("meta: {}\n", encoding="utf-8")


def render_context(tmp_path: Path) -> tuple[Path, Path, Path]:
    """Create a complete author and engine render context."""
    root = tmp_path / "book"
    engine = tmp_path / "engine"
    stage = root / "_build" / ".work" / "full"
    write_author_fixture(root)
    write_engine_fixture(engine)
    return root, engine, stage


def test_author_config_loads_validated_metadata(tmp_path: Path) -> None:
    """Load metadata defaults, excerpt selection, and a stable identifier."""
    root = tmp_path / "book"
    write_author_fixture(root)

    first = author_project.load_author_config(root)
    second = author_project.load_author_config(root)

    assert first == second
    assert first["book"]["title"] == "Fixture Book"
    assert first["book"]["language"] == "fr-CA"
    assert first["book"]["identifier"].startswith("urn:uuid:")
    assert first["excerpt"]["chapters"] == ["02-second.qmd"]


@pytest.mark.parametrize(
    ("document", "diagnostic"),
    (
        ("title = 'outside a table'\n", r"supports only \[book\] and \[excerpt\]"),
        ("[book]\ntitle = 'Book'\nauthor = 'Author'\nlanguage = 'not_a_tag'\n", "language tag"),
        (
            "[book]\ntitle = 'Book'\nauthor = 'Author'\n[excerpt]\nchapters = ['01-a.qmd', '02-b.qmd', '03-c.qmd']\n",
            "at most two unique filenames",
        ),
        (
            "[book]\ntitle = 'Book'\nauthor = 'Author'\n[excerpt]\nchapters = ['chapter.qmd']\n",
            "NN-kebab-case.qmd",
        ),
    ),
)
def test_author_config_rejects_invalid_contracts(tmp_path: Path, document: str, diagnostic: str) -> None:
    """Reject malformed metadata and excerpt configuration."""
    (tmp_path / "book.toml").write_text(document, encoding="utf-8")

    with pytest.raises(author_project.AuthorProjectError, match=diagnostic):
        author_project.load_author_config(tmp_path)


def test_workspace_compilation_separates_full_and_excerpt_content(tmp_path: Path) -> None:
    """Stage complete and excerpt workspaces from one author project."""
    root = tmp_path / "book"
    engine = tmp_path / "engine"
    write_author_fixture(root)
    write_engine_fixture(engine)

    full = author_project.compile_workspace(root, engine, "full")
    excerpt = author_project.compile_workspace(root, engine, "excerpt")

    assert full["sources"] == [
        "index.qmd",
        "manuscript/chapters/01-first.qmd",
        "manuscript/chapters/02-second.qmd",
        "manuscript/references.qmd",
        "manuscript/appendices/01-extra.qmd",
    ]
    assert excerpt["sources"] == [
        "index.qmd",
        "manuscript/chapters/02-second.qmd",
        "manuscript/references.qmd",
    ]
    assert "Read the complete book for more." not in (full["stage"] / "index.qmd").read_text(encoding="utf-8")
    assert "Read the complete book for more." in (excerpt["stage"] / "index.qmd").read_text(encoding="utf-8")
    assert (full["stage"] / "glossary.yml").is_symlink()
    assert (full["stage"] / "assets").is_symlink()
    assert (full["stage"] / "index.yml").read_text(encoding="utf-8") == ("version: 1\nlang: fr-CA\nentries: {}\n")
    assert "appendices:" in (full["stage"] / "_quarto.yml").read_text(encoding="utf-8")
    assert "appendices:" not in (excerpt["stage"] / "_quarto.yml").read_text(encoding="utf-8")


def test_author_render_hides_success_noise(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """Hide renderer output after a successful author build."""
    root, engine, stage = render_context(tmp_path)

    def run(_command: Sequence[str | os.PathLike[str]], **_options: object) -> subprocess.CompletedProcess[str]:
        """Create a successful fake renderer output."""
        output = stage / "_output" / "html"
        output.mkdir(parents=True)
        (output / "index.html").write_text("complete", encoding="utf-8")
        return subprocess.CompletedProcess(list(_command), 0, stdout="verbose renderer details", stderr="")

    monkeypatch.setattr(author_project, "run_process", run)
    author_project.render(root, engine, "full", ["html"])
    output = capsys.readouterr().out
    assert output == "rendering: full html\nbuilt: _build/full/html\n"
    assert (root / "_build" / "full" / "html" / "index.html").is_file()


def test_author_render_preserves_failure_diagnostics(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """Preserve renderer diagnostics when an author build fails."""
    root, engine, _stage = render_context(tmp_path)

    def fail_run(arguments: Sequence[str | os.PathLike[str]], **_options: object) -> subprocess.CompletedProcess[str]:
        """Return one failed renderer invocation."""
        return subprocess.CompletedProcess(list(arguments), 9, stdout="specific renderer diagnostic", stderr="")

    monkeypatch.setattr(author_project, "run_process", fail_run)
    with pytest.raises(author_project.AuthorProjectError) as failure:
        author_project.render(root, engine, "full", ["html"])

    assert "html render failed with status 9" in str(failure.value)
    assert "specific renderer diagnostic" in str(failure.value)
