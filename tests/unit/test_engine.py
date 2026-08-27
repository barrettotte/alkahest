"""Unit tests for the remaining engine orchestration."""

import os
import subprocess
from collections.abc import Sequence
from pathlib import Path

import pytest

from alkahest import ci
from alkahest.rendering.pipeline import FORMATS, PLANS
from alkahest.staging import copy_if_changed

ROOT = Path(__file__).resolve().parents[2]


def test_guide_uses_the_locked_toolchain_image() -> None:
    """Keep the guide base image synchronized with the toolchain lock."""
    toolchain_lines = (ROOT / "scripts/toolchain.sh").read_text(encoding="utf-8").splitlines()
    image_line = next(line for line in toolchain_lines if line.startswith("readonly ALKAHEST_TOOLCHAIN_IMAGE="))
    locked_image = image_line.split('"', 2)[1]
    guide_lines = (ROOT / "guide/Containerfile").read_text(encoding="utf-8").splitlines()
    guide_image = next(line.removeprefix("FROM ") for line in guide_lines if line.startswith("FROM "))
    assert guide_image == locked_image


def test_render_surface_is_typst_only() -> None:
    """Expose only HTML, EPUB, and Typst rendering."""
    assert FORMATS == ("html", "epub", "typst")
    assert PLANS["typst"] == ("typst",)
    assert PLANS["all"] == FORMATS
    assert "latex" not in PLANS


def test_staging_copy_skips_identical_bytes(tmp_path: Path) -> None:
    """Avoid replacing an unchanged staged file."""
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


def test_ci_runs_the_small_pipeline(monkeypatch: pytest.MonkeyPatch) -> None:
    """Run the compact CI command sequence in order."""
    observed: list[list[str]] = []

    def record(arguments: Sequence[str | os.PathLike[str]], **_options: object) -> subprocess.CompletedProcess[str]:
        """Record one orchestrated command."""
        observed.append([str(value) for value in arguments])
        return subprocess.CompletedProcess(observed[-1], 0)

    monkeypatch.setattr(ci, "run_process", record)
    assert ci.run() == 0
    assert observed[0][-1].endswith("scripts/bootstrap.sh")

    commands = [command[-len(step) :] for command, step in zip(observed[1:], ci.COMMANDS, strict=True)]
    assert commands == [list(step) for step in ci.COMMANDS]
