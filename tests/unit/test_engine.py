"""Unit tests for the remaining engine orchestration."""

from alkahest import ci
from alkahest.rendering.pipeline import FORMATS, PLANS
from alkahest.staging import copy_if_changed


def test_render_surface_is_typst_only() -> None:
    assert FORMATS == ("html", "epub", "typst")
    assert PLANS["typst"] == ("typst",)
    assert PLANS["all"] == FORMATS
    assert "latex" not in PLANS


def test_staging_copy_skips_identical_bytes(tmp_path) -> None:
    source = tmp_path / "source.woff2"
    destination = tmp_path / "destination.woff2"
    source.write_bytes(b"first")
    copy_if_changed(source, destination)
    initial_time = destination.stat().st_mtime_ns
    copy_if_changed(source, destination)
    assert destination.stat().st_mtime_ns == initial_time
    source.write_bytes(b"second")
    copy_if_changed(source, destination)
    assert destination.read_bytes() == b"second"


def test_ci_runs_the_small_pipeline(monkeypatch) -> None:
    observed = []

    def record(arguments, **_options):
        observed.append([str(value) for value in arguments])
        return type("Result", (), {"returncode": 0})()

    monkeypatch.setattr(ci, "run_process", record)
    assert ci.run() == 0
    assert observed[0][-1].endswith("scripts/bootstrap.sh")
    commands = [
        command[-len(step) :] for command, step in zip(observed[1:], ci.COMMANDS, strict=True)
    ]
    assert commands == [list(step) for step in ci.COMMANDS]
