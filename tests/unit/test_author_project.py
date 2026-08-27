"""Unit tests for the minimal author workflow."""

import os
import subprocess
from collections.abc import Sequence
from pathlib import Path
from typing import cast

import pytest

from alkahest import author_project
from alkahest.author_project import Workspace


def render_context(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> tuple[Path, Path]:
    """Create a staged render context with compilation isolated."""
    root = tmp_path / "book"
    stage = root / "_build" / ".work" / "full"
    stage.mkdir(parents=True)

    def compile_workspace(_root: Path, _engine_root: Path, _profile: str) -> Workspace:
        """Return the isolated fake workspace."""
        return cast(Workspace, {"stage": stage})

    monkeypatch.setattr(author_project, "compile_workspace", compile_workspace)
    return root, stage


def test_author_render_hides_success_noise(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """Hide renderer output after a successful author build."""
    root, stage = render_context(monkeypatch, tmp_path)

    def run(_command: Sequence[str | os.PathLike[str]], **_options: object) -> subprocess.CompletedProcess[str]:
        """Create a successful fake renderer output."""
        output = stage / "_output" / "html"
        output.mkdir(parents=True)
        (output / "index.html").write_text("complete", encoding="utf-8")
        return subprocess.CompletedProcess(list(_command), 0, stdout="verbose renderer details", stderr="")

    monkeypatch.setattr(author_project, "run_process", run)
    author_project.render(root, tmp_path / "engine", "full", ["html"])
    output = capsys.readouterr().out
    assert output == "rendering: full html\nbuilt: _build/full/html\n"
    assert (root / "_build" / "full" / "html" / "index.html").is_file()


def test_author_render_preserves_failure_diagnostics(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """Preserve renderer diagnostics when an author build fails."""
    root, _stage = render_context(monkeypatch, tmp_path)

    def fail_run(arguments: Sequence[str | os.PathLike[str]], **_options: object) -> subprocess.CompletedProcess[str]:
        """Return one failed renderer invocation."""
        return subprocess.CompletedProcess(list(arguments), 9, stdout="specific renderer diagnostic", stderr="")

    monkeypatch.setattr(author_project, "run_process", fail_run)
    with pytest.raises(author_project.AuthorProjectError) as failure:
        author_project.render(root, tmp_path / "engine", "full", ["html"])

    assert "html render failed with status 9" in str(failure.value)
    assert "specific renderer diagnostic" in str(failure.value)
