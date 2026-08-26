"""Exercise valid, invalid, and empty generated-list registry contracts."""

import shutil
from collections.abc import Callable
from pathlib import Path

import pytest

from alkahest.checks import generated_lists

ROOT = Path(__file__).resolve().parents[2]
FIXTURE = ROOT / "tests/generated-lists/base"
Mutation = Callable[[Path], None]


def replace(path: Path, old: str, new: str) -> None:
    text = path.read_text(encoding="utf-8")
    if old not in text:
        raise RuntimeError(f"fixture edit did not match {old!r} in {path}")
    path.write_text(text.replace(old, new, 1), encoding="utf-8")


def edit(relative: str, old: str, new: str) -> Mutation:
    return lambda root: replace(root / relative, old, new)


def append(relative: str, content: str) -> Mutation:
    def mutate(root: Path) -> None:
        path = root / relative
        path.write_text(path.read_text(encoding="utf-8") + content, encoding="utf-8")

    return mutate


def duplicate_file(source: str, destination: str) -> Mutation:
    return lambda root: shutil.copy2(root / source, root / destination)


def run(root: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ALKAHEST_GENERATED_LISTS_BOOK_ROOT", str(root))
    generated_lists.main()


def test_valid_generated_lists(monkeypatch: pytest.MonkeyPatch) -> None:
    run(FIXTURE, monkeypatch)


@pytest.mark.parametrize(
    ("name", "expected", "mutate"),
    (
        (
            "duplicate-order",
            "duplicate list in order",
            edit("generated-lists.yml", "  - figures\n", "  - figures\n  - figures\n"),
        ),
        (
            "unknown-order",
            "unknown list in order",
            edit("generated-lists.yml", "  - figures\n", "  - absent\n"),
        ),
        (
            "missing-order",
            "missing from order",
            edit("generated-lists.yml", "  - algorithms\n", ""),
        ),
        (
            "unsupported-source",
            "unsupported source",
            edit("generated-lists.yml", "source: terms", "source: external"),
        ),
        (
            "duplicate-prefix",
            "duplicate cross-reference prefix",
            edit("generated-lists.yml", "prefix: tbl", "prefix: fig"),
        ),
        ("invalid-prefix", "invalid prefix", edit("generated-lists.yml", "    prefix: fig\n", "")),
        (
            "duplicate-object",
            "duplicate generated-list object",
            edit(
                "generated-lists.yml",
                "  - id: fig-sample\n    title: Sample figure\n",
                "  - id: fig-sample\n    title: Sample figure\n  - id: fig-sample\n    title: Sample figure\n",
            ),
        ),
        (
            "missing-object",
            "missing from generated-lists.yml",
            edit("generated-lists.yml", "  - id: fig-sample\n    title: Sample figure\n", ""),
        ),
        (
            "absent-target",
            "target does not exist",
            edit("generated-lists.yml", "fig-sample", "fig-absent"),
        ),
        (
            "unknown-prefix",
            "no configured cross-reference list owns",
            edit("generated-lists.yml", "id: fig-sample", "id: vid-sample"),
        ),
        (
            "unknown-terms-list",
            "unknown terms list",
            edit("generated-lists.yml", "list: symbols", "list: figures"),
        ),
        (
            "unknown-term-target",
            "targets unknown object",
            edit("generated-lists.yml", "target: eq-sample", "target: eq-absent"),
        ),
        (
            "tex-display",
            "without dollar delimiters",
            edit("generated-lists.yml", "display: I", "display: '$I$'"),
        ),
        (
            "missing-alt",
            "term current has no alt",
            edit("generated-lists.yml", "    alt: capital I, electric current\n", ""),
        ),
        (
            "invalid-language",
            "BCP 47",
            edit("generated-lists.yml", "lang: en-US", "lang: english_US"),
        ),
        (
            "missing-placeholder",
            "placeholder; found 0",
            edit(
                "generated-lists.qmd", "alkahest-generated-lists-placeholder", "not-a-placeholder"
            ),
        ),
        (
            "duplicate-placeholder",
            "placeholder; found 2",
            duplicate_file("generated-lists.qmd", "second-lists.qmd"),
        ),
        (
            "backend-command",
            "backend-specific list command",
            append("chapter.qmd", "\\listoffigures\n"),
        ),
        (
            "duplicate-acronym-list",
            "at most one glossary-acronyms list",
            edit(
                "generated-lists.yml",
                "  algorithms:\n    title: List of algorithms\n    source: crossref\n    prefix: alg\n",
                "  algorithms:\n    title: List of algorithms\n    source: glossary-acronyms\n",
            ),
        ),
    ),
)
def test_invalid_generated_lists(
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
