"""Unit tests for the minimal author workflow."""

from types import SimpleNamespace

import pytest

from alkahest import author_project


def render_context(monkeypatch, tmp_path):
    root = tmp_path / "book"
    stage = root / "_build" / ".work" / "full"
    stage.mkdir(parents=True)
    monkeypatch.setattr(
        author_project,
        "compile_workspace",
        lambda *_arguments: {"stage": stage, "config": {}},
    )
    return root, stage


def test_author_render_hides_success_noise(monkeypatch, tmp_path, capsys) -> None:
    root, stage = render_context(monkeypatch, tmp_path)

    def run(_command, **_options):
        output = stage / "_output" / "html"
        output.mkdir(parents=True)
        (output / "index.html").write_text("complete", encoding="utf-8")
        return SimpleNamespace(returncode=0, stdout="verbose renderer details")

    monkeypatch.setattr(author_project, "run_process", run)
    author_project.render(root, tmp_path / "engine", "full", ["html"])
    output = capsys.readouterr().out
    assert output == "rendering: full html\nbuilt: _build/full/html\n"
    assert (root / "_build" / "full" / "html" / "index.html").is_file()


def test_author_render_preserves_failure_diagnostics(monkeypatch, tmp_path) -> None:
    root, _stage = render_context(monkeypatch, tmp_path)
    monkeypatch.setattr(
        author_project,
        "run_process",
        lambda *_arguments, **_options: SimpleNamespace(
            returncode=9, stdout="specific renderer diagnostic"
        ),
    )
    with pytest.raises(author_project.AuthorProjectError) as failure:
        author_project.render(root, tmp_path / "engine", "full", ["html"])
    assert "html render failed with status 9" in str(failure.value)
    assert "specific renderer diagnostic" in str(failure.value)
