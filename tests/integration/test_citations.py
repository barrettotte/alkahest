"""Exercise valid and deliberately invalid citation registries, styles, and calls."""

import shutil
from collections.abc import Callable
from pathlib import Path

import pytest

from alkahest.checks import citations

ROOT = Path(__file__).resolve().parents[2]
FIXTURE = ROOT / "tests/citations/base"


def replace(path: Path, old: str, new: str, *, regex: bool = False) -> None:
    text = path.read_text(encoding="utf-8")
    if regex:
        import re

        changed, count = re.subn(old, new, text, count=1, flags=re.MULTILINE)
    else:
        count = int(old in text)
        changed = text.replace(old, new, 1)
    if count != 1:
        raise RuntimeError(f"fixture edit did not match {old!r} in {path}")
    path.write_text(changed, encoding="utf-8")


def prepare(root: Path) -> None:
    shutil.copytree(FIXTURE, root)
    citations_root = root / "citations"
    citations_root.mkdir()
    for name in ("chicago-author-date.csl", "ieee.csl"):
        shutil.copy2(ROOT / "book/citations" / name, citations_root / name)


def run(root: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ALKAHEST_CITATION_BOOK_ROOT", str(root))
    citations.main()


def test_valid_citations(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    root = tmp_path / "valid"
    prepare(root)
    run(root, monkeypatch)


Mutation = Callable[[Path], None]


@pytest.mark.parametrize(
    ("name", "expected", "mutate"),
    (
        (
            "missing-key",
            "missing bibliography key missing",
            lambda root: replace(root / "chapter.qmd", "@primary", "@missing"),
        ),
        (
            "duplicate-key",
            "duplicate bibliography key primary",
            lambda root: replace(root / "references.bib", "@book{secondary,", "@book{primary,"),
        ),
        (
            "unused-key",
            "bibliography key background is unused",
            lambda root: replace(root / "_quarto.yml", "nocite: |\n  @background\n", ""),
        ),
        (
            "missing-nocite-key",
            "nocite metadata references missing bibliography key missing",
            lambda root: replace(root / "_quarto.yml", "@background", "@missing"),
        ),
        (
            "changed-style",
            "citation style citations/chicago-author-date.csl changed",
            lambda root: replace(
                root / "citations/chicago-author-date.csl", "<summary>", "<summary>Modified "
            ),
        ),
        (
            "drifted-profile",
            "numeric profile must select the locked IEEE file",
            lambda root: replace(
                root / "_quarto-citation-numeric.yml",
                "citations/ieee.csl",
                "citations/chicago-author-date.csl",
            ),
        ),
    ),
)
def test_invalid_citations(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    name: str,
    expected: str,
    mutate: Mutation,
) -> None:
    root = tmp_path / name
    prepare(root)
    mutate(root)
    with pytest.raises(RuntimeError) as error:
        run(root, monkeypatch)
    assert expected in str(error.value)
