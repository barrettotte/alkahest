"""Exercise valid, invalid, translated, and editioned identity inventories."""

import shutil
from collections.abc import Callable
from pathlib import Path

import pytest

from alkahest.common import ContractError
from alkahest.identities import validate_identity_book

ROOT = Path(__file__).resolve().parents[2]
FIXTURE = ROOT / "tests/identities/base/book"


def replace(path: Path, old: str, new: str, *, all_matches: bool = False) -> None:
    text = path.read_text(encoding="utf-8")
    count = text.count(old)
    if count == 0:
        raise RuntimeError(f"fixture edit did not match {old!r} in {path}")
    path.write_text(text.replace(old, new, -1 if all_matches else 1), encoding="utf-8")


def test_valid_identities() -> None:
    validate_identity_book(FIXTURE)


Mutation = Callable[[Path], None]


@pytest.mark.parametrize(
    ("name", "expected", "mutate"),
    (
        (
            "implicit-heading",
            "every heading must have exactly one explicit persistent ID",
            lambda root: replace(root / "en/chapter.qmd", " {#sec-stable-section}", ""),
        ),
        (
            "setext-heading",
            "Setext headings cannot carry the required explicit ID",
            lambda root: replace(
                root / "en/chapter.qmd",
                "## Stable section {#sec-stable-section}",
                "Stable section\n--------------",
            ),
        ),
        (
            "duplicate-content",
            "duplicate content identity 'sec-identity-fixture'",
            lambda root: replace(
                root / "en/chapter.qmd", "sec-stable-section", "sec-identity-fixture"
            ),
        ),
        (
            "semantic-title-id",
            "semantic block title must use its enclosing 'exr-identity-sample' identity",
            lambda root: replace(
                root / "en/chapter.qmd",
                "## Fixture exercise",
                "## Fixture exercise {#sec-redundant-title}",
            ),
        ),
        (
            "translation-drift",
            "translation 'fr-FR' is missing content identity 'sec-stable-section'",
            lambda root: replace(
                root / "fr/chapitre.qmd", "sec-stable-section", "sec-section-traduite"
            ),
        ),
        (
            "translated-glossary-drift",
            "translation 'fr-FR' is missing glossary identity 'stable-term'",
            lambda root: replace(root / "fr/glossary.yml", "stable-term:", "terme-stable:"),
        ),
        (
            "missing-companion",
            "references missing file 'companion/sample.txt'",
            lambda root: (root / "companion/sample.txt").rename(root / "companion/not-sample.txt"),
        ),
        (
            "missing-reusable-content",
            "references missing fragment 'reuse/fixture-notice.md'",
            lambda root: (root / "reuse/fixture-notice.md").rename(root / "reuse/not-fixture.md"),
        ),
        (
            "edition-drift",
            "must resolve to one persistently identified chapter",
            lambda root: replace(root / "editions.json", "chapter.qmd", "missing.qmd"),
        ),
    ),
)
def test_invalid_identities(tmp_path: Path, name: str, expected: str, mutate: Mutation) -> None:
    root = tmp_path / name
    shutil.copytree(FIXTURE, root)
    mutate(root)
    with pytest.raises(ContractError) as error:
        validate_identity_book(root)
    assert expected in str(error.value)


def test_coordinated_identity_rename(tmp_path: Path) -> None:
    root = tmp_path / "coordinated-rename"
    shutil.copytree(FIXTURE, root)
    for relative in ("en/chapter.qmd", "fr/chapitre.qmd"):
        replace(root / relative, "sec-stable-section", "sec-renamed-section", all_matches=True)
    validate_identity_book(root)
