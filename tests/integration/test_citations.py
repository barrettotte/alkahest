"""Validate the reference book's citation contract."""

from alkahest.checks import citations


def test_reference_citations_are_complete() -> None:
    citations.main()
