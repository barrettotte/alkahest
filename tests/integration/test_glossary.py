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
    """Replace one literal or regular-expression fixture fragment."""
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
    """Run the glossary validator against one fixture root."""
    monkeypatch.setenv("ALKAHEST_GLOSSARY_BOOK_ROOT", str(root))
    glossary.main()


def test_valid_glossary(monkeypatch: pytest.MonkeyPatch) -> None:
    """Accept the complete glossary fixture."""
    run(FIXTURE, monkeypatch)


Mutation = Callable[[Path], None]


def edit(relative: str, old: str, new: str, *, regex: bool = False) -> Mutation:
    """Create one typed glossary fixture mutation."""

    def mutate(root: Path) -> None:
        """Apply the configured glossary fixture replacement."""
        replace(root / relative, old, new, regex=regex)

    return mutate


@pytest.mark.parametrize(
    ("name", "expected", "mutate"),
    (
        (
            "duplicate-display",
            "duplicate glossary display term",
            edit("glossary.yml", "term: matrix", "term: central processing unit"),
        ),
        (
            "duplicate-alias",
            "duplicate glossary name or alias",
            edit("glossary.yml", "      - array", "      - cpu"),
        ),
        (
            "undefined-term",
            "unknown glossary name or alias",
            edit("chapter-two.qmd", "alk-term matrix", "alk-term missing-term"),
        ),
        (
            "unused-entry",
            "is unused",
            edit(
                "chapter-two.qmd",
                r" and\n+an unlinked \{\{< alk-term matrix form=first link=false >\}\} reference",
                " reference",
                regex=True,
            ),
        ),
        (
            "duplicate-first-use",
            "duplicate explicit first use",
            edit(
                "chapter-one.qmd",
                "examples begin here.",
                "examples begin here.\n\n{{< alk-term cpu form=first >}} again.",
            ),
        ),
        (
            "missing-first-use",
            "has no explicit first-use marker",
            edit("chapter-one.qmd", "form=first case=sentence", "form=term case=sentence"),
        ),
        (
            "invalid-case",
            "unknown alk-term case",
            edit("chapter-one.qmd", "case=sentence", "case=uppercase"),
        ),
        (
            "invalid-link",
            "alk-term link must be true or false",
            edit("chapter-two.qmd", "link=false", "link=maybe"),
        ),
        (
            "unavailable-form",
            "form acronym is unavailable",
            edit("chapter-two.qmd", "form=first link=false", "form=acronym link=false"),
        ),
        (
            "invalid-language",
            "language must be a BCP 47-style tag",
            edit("glossary.yml", "lang: en-US", "lang: en_US"),
        ),
        (
            "missing-placeholder",
            "expected exactly one generated-glossary placeholder",
            edit("glossary-backmatter.qmd", "::: {.alkahest-glossary-placeholder}\n:::\n", ""),
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
    """Reject one deliberately invalid glossary fixture."""
    root = tmp_path / name
    shutil.copytree(FIXTURE, root)
    mutate(root)
    with pytest.raises(RuntimeError) as error:
        run(root, monkeypatch)
    assert expected in str(error.value)
