"""Exercise valid and deliberately invalid semantic-note source contracts."""

import re
import shutil
from collections.abc import Callable
from pathlib import Path

import pytest

from alkahest.checks import notes

ROOT = Path(__file__).resolve().parents[2]
FIXTURE = ROOT / "tests/notes/base"
Mutation = Callable[[Path], None]


def replace(
    path: Path, old: str, new: str, *, regex: bool = False, all_matches: bool = False
) -> None:
    text = path.read_text(encoding="utf-8")
    if regex:
        changed, count = re.subn(old, new, text, count=0 if all_matches else 1)
    else:
        count = text.count(old)
        changed = text.replace(old, new, -1 if all_matches else 1)
    if count == 0:
        raise RuntimeError(f"fixture edit did not match {old!r} in {path}")
    path.write_text(changed, encoding="utf-8")


def edit(
    relative: str, old: str, new: str, *, regex: bool = False, all_matches: bool = False
) -> Mutation:
    return lambda root: replace(root / relative, old, new, regex=regex, all_matches=all_matches)


def run(root: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ALKAHEST_NOTES_BOOK_ROOT", str(root))
    notes.main()


def test_valid_notes(monkeypatch: pytest.MonkeyPatch) -> None:
    run(FIXTURE, monkeypatch)


@pytest.mark.parametrize(
    ("name", "expected", "mutate"),
    (
        (
            "missing-definition",
            "note reference has no registered definition: source-order",
            edit("components.qmd", r"\n\[\^source-order\]:.*?\n", "\n", regex=True),
        ),
        (
            "duplicate-definition",
            "duplicate note definition: page-geometry",
            edit("reference.qmd", r"(\[\^page-geometry\]:[^\n]+\n)", r"\1\1", regex=True),
        ),
        (
            "unregistered-definition",
            "unregistered note definition: extra-note",
            edit("components.qmd", "source-order", "extra-note", all_matches=True),
        ),
        (
            "unknown-reference",
            "note reference has no registered definition: missing",
            edit("reference.qmd", "First reference.[^page-geometry]", "First reference.[^missing]"),
        ),
        (
            "forbidden-repeat",
            "uses repeat=once with more than one reference",
            edit("notes.yml", "repeat: reuse", "repeat: once"),
        ),
        (
            "reference-count",
            "registry expects 3",
            edit("notes.yml", "references: 2", "references: 3"),
        ),
        (
            "wrong-source",
            "expected components.qmd",
            edit("notes.yml", "source: reference.qmd", "source: components.qmd"),
        ),
        (
            "wrong-marker",
            "note marker must be #note-page-geometry",
            edit("reference.qmd", "note-page-geometry", "note-wrong"),
        ),
        (
            "inline-note",
            "uses an inline note",
            edit("reference.qmd", "First reference", "Inline^[unregistered note]. First reference"),
        ),
        (
            "missing-placeholder",
            "expected exactly one book-notes placeholder; found 0",
            edit("glossary-backmatter.qmd", "::: {.alkahest-book-notes-placeholder}\n:::\n", ""),
        ),
        (
            "duplicate-placeholder",
            "expected exactly one book-notes placeholder; found 2",
            edit(
                "glossary-backmatter.qmd",
                "::: {.alkahest-book-notes-placeholder}\n:::\n",
                "::: {.alkahest-book-notes-placeholder}\n:::\n\n::: {.alkahest-book-notes-placeholder}\n:::\n",
            ),
        ),
        (
            "missing-order",
            "order and mapping contain different entry counts",
            edit("notes.yml", "  - source-order\n", ""),
        ),
    ),
)
def test_invalid_notes(
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
