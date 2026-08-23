"""Unit tests for consolidated report, staging, and PDF helper behavior."""

from alkahest import ci
from alkahest.checks.pdf_profiles import metadata, page_for, split_pages
from alkahest.rendering.pipeline import DEFAULT_PDF_PROFILE, PLANS, SPECS
from alkahest.staging import copy_if_changed


def test_pdf_text_helpers_preserve_physical_pages() -> None:
    pages = split_pages("front\fchapter one\ncontinued\f")
    assert pages == ["front", "chapter one\ncontinued"]
    assert page_for(pages, "chapter one continued") == 2
    assert page_for(pages, "missing") is None


def test_pdf_metadata_extracts_named_values() -> None:
    assert metadata("Pages: 73\nPage size: 504 x 720 pts\n", "Pages") == "73"


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


def test_render_plans_reference_closed_specs() -> None:
    assert PLANS["pdf"] == (DEFAULT_PDF_PROFILE,)
    assert PLANS["preview"] == ("preview-html", "preview-epub", "preview-typst")
    assert set().union(*map(set, PLANS.values())) == set(SPECS)


def test_ci_preserves_module_commands(monkeypatch) -> None:
    observed = []

    def record(arguments, **_options):
        observed.append([str(value) for value in arguments])
        return type("Result", (), {"returncode": 0})()

    monkeypatch.setattr(ci, "run_process", record)
    assert ci.run() == 0
    assert observed[0][-1].endswith("scripts/bootstrap.sh")
    assert ["-m", "alkahest", "quality"] == observed[1][-3:]
    repeat = next(command for command in observed if "--repeat" in command)
    assert repeat[-4:] == ["-m", "alkahest.checks.reproducibility", "--repeat", "quick"]
