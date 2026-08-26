"""Exercise valid and deliberately invalid glossary registries and references."""

import re
import shutil
from collections.abc import Callable
from pathlib import Path

import pytest

from alkahest.checks import glossary

ROOT = Path(__file__).resolve().parents[2]
FIXTURE = ROOT / "tests/glossary/base"


def replace(path: Path, old: str, new: str, *, regex: bool = False) -> None:
    text = path.read_text(encoding="utf-8")
    if regex:
        changed, count = re.subn(old, new, text, count=1, flags=re.MULTILINE)
    else:
        count = int(old in text)
        changed = text.replace(old, new, 1)
    if count != 1:
        raise RuntimeError(f"fixture edit did not match {old!r} in {path}")
    path.write_text(changed, encoding="utf-8")


def run(root: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ALKAHEST_GLOSSARY_BOOK_ROOT", str(root))
    glossary.main()


def test_valid_glossary(monkeypatch: pytest.MonkeyPatch) -> None:
    run(FIXTURE, monkeypatch)


Mutation = Callable[[Path], None]


@pytest.mark.parametrize(
    ("name", "expected", "mutate"),
    (
        (
            "duplicate-display",
            "duplicate glossary display term",
            lambda root: replace(
                root / "glossary.yml", "term: matrix", "term: central processing unit"
            ),
        ),
        (
            "duplicate-alias",
            "duplicate glossary name or alias",
            lambda root: replace(root / "glossary.yml", "      - array", "      - cpu"),
        ),
        (
            "undefined-term",
            "unknown glossary name or alias",
            lambda root: replace(
                root / "chapter-two.qmd", "alk-term matrix", "alk-term missing-term"
            ),
        ),
        (
            "unused-entry",
            "is unused",
            lambda root: replace(
                root / "chapter-two.qmd",
                r" and\n+an unlinked \{\{< alk-term matrix form=first link=false >\}\} reference",
                " reference",
                regex=True,
            ),
        ),
        (
            "duplicate-first-use",
            "duplicate explicit first use",
            lambda root: replace(
                root / "chapter-one.qmd",
                "examples begin here.",
                "examples begin here.\n\n{{< alk-term cpu form=first >}} again.",
            ),
        ),
        (
            "missing-first-use",
            "has no explicit first-use marker",
            lambda root: replace(
                root / "chapter-one.qmd", "form=first case=sentence", "form=term case=sentence"
            ),
        ),
        (
            "invalid-case",
            "unknown alk-term case",
            lambda root: replace(root / "chapter-one.qmd", "case=sentence", "case=uppercase"),
        ),
        (
            "invalid-link",
            "alk-term link must be true or false",
            lambda root: replace(root / "chapter-two.qmd", "link=false", "link=maybe"),
        ),
        (
            "unavailable-form",
            "form acronym is unavailable",
            lambda root: replace(
                root / "chapter-two.qmd", "form=first link=false", "form=acronym link=false"
            ),
        ),
        (
            "invalid-language",
            "language must be a BCP 47-style tag",
            lambda root: replace(root / "glossary.yml", "lang: en-US", "lang: en_US"),
        ),
        (
            "missing-placeholder",
            "expected exactly one generated-glossary placeholder",
            lambda root: replace(
                root / "glossary-backmatter.qmd", "::: {.alkahest-glossary-placeholder}\n:::\n", ""
            ),
        ),
    ),
)
def test_invalid_glossary(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    name: str,
    expected: str,
    mutate: Mutation,
) -> None:
    root = tmp_path / name
    shutil.copytree(FIXTURE, root)
    mutate(root)
    with pytest.raises(RuntimeError) as error:
        run(root, monkeypatch)
    assert expected in str(error.value)
