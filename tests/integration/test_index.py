"""Exercise valid and invalid subject/person index registry and marker contracts."""

import re
import shutil
from collections.abc import Callable
from pathlib import Path

import pytest

from alkahest.checks import index

ROOT = Path(__file__).resolve().parents[2]
FIXTURE = ROOT / "tests/index/base"
Mutation = Callable[[Path], None]


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


def edit(relative: str, old: str, new: str, *, regex: bool = False) -> Mutation:
    """Create one typed index fixture replacement."""

    def mutate(root: Path) -> None:
        """Apply the configured index fixture replacement."""
        replace(root / relative, old, new, regex=regex)

    return mutate


def append(relative: str, content: str) -> Mutation:
    """Create one typed index fixture append."""

    def mutate(root: Path) -> None:
        """Append content to the configured fixture file."""
        path = root / relative
        path.write_text(path.read_text(encoding="utf-8") + content, encoding="utf-8")

    return mutate


def edits(*mutations: Mutation) -> Mutation:
    """Combine several index fixture mutations."""

    def mutate(root: Path) -> None:
        """Apply every configured fixture mutation."""
        for mutation in mutations:
            mutation(root)

    return mutate


def copy(relative: str, destination: str) -> Mutation:
    """Create one typed fixture-file copy."""

    def mutate(root: Path) -> None:
        """Copy the configured fixture file."""
        shutil.copy2(root / relative, root / destination)

    return mutate


def run(root: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Run the index validator against one fixture root."""
    monkeypatch.setenv("ALKAHEST_INDEX_BOOK_ROOT", str(root))
    index.main()


def test_valid_index(monkeypatch: pytest.MonkeyPatch) -> None:
    """Accept the complete index fixture."""
    run(FIXTURE, monkeypatch)


@pytest.mark.parametrize(
    ("name", "expected", "mutate"),
    (
        (
            "duplicate-alias",
            "duplicate index name or alias",
            edit("index.yml", "      - system-design", "      - architecture"),
        ),
        (
            "unknown-marker",
            "unknown index name or alias missing",
            edit("chapter.qmd", "alk-index system-design", "alk-index missing"),
        ),
        (
            "missing-marker",
            "declared index point has no matching marker",
            edit("chapter.qmd", r"^.*alk-index system-design.*\n", "", regex=True),
        ),
        (
            "duplicate-marker",
            "duplicate index point marker",
            edit(
                "chapter.qmd",
                "{{< alk-index system-design id=overview >}}",
                "{{< alk-index system-design id=overview >}}{{< alk-index system-design id=overview >}}",
            ),
        ),
        (
            "missing-range-end",
            "needs exactly one start and one end",
            edit("chapter.qmd", r"^.*range=end.*\n", "", regex=True),
        ),
        (
            "undeclared-range",
            "declared index range needs exactly one start and one end",
            edits(
                edit("chapter.qmd", "id=tour range=start", "id=extra range=start"),
                edit("chapter.qmd", "id=tour range=end", "id=extra range=end"),
            ),
        ),
        (
            "invalid-parent",
            "invalid parent",
            edit("index.yml", "parent: systems", "parent: absent"),
        ),
        (
            "parent-cycle",
            "index parent cycle",
            edit(
                "index.yml",
                "kind: subject\n    aliases:",
                "kind: subject\n    parent: architecture\n    aliases:",
            ),
        ),
        (
            "mixed-kind-parent",
            "different kinds",
            edit(
                "index.yml",
                "hopper-grace:\n    term: Hopper, Grace\n    kind: person",
                "hopper-grace:\n    term: Hopper, Grace\n    kind: person\n    parent: systems",
            ),
        ),
        (
            "invalid-see",
            "invalid see target",
            edit("index.yml", "see: architecture", "see: absent"),
        ),
        (
            "redirect-locator",
            "cannot have locators",
            edit(
                "index.yml",
                "see: architecture",
                "see: architecture\n    locations:\n      - chapter.qmd#redirect",
            ),
        ),
        ("invalid-language", "BCP 47", edit("index.yml", "lang: en-US", "lang: english_US")),
        (
            "missing-placeholder",
            "expected exactly one index placeholder; found 0",
            edit("index-backmatter.qmd", "alkahest-index-placeholder", "not-an-index-placeholder"),
        ),
        (
            "duplicate-placeholder",
            "expected exactly one index placeholder; found 2",
            copy("index-backmatter.qmd", "second-index.qmd"),
        ),
        (
            "backend-command",
            "backend-specific index command",
            append("chapter.qmd", "\\index{systems}\n"),
        ),
    ),
)
def test_invalid_index(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    name: str,
    expected: str,
    mutate: Mutation,
) -> None:
    """Reject one deliberately invalid index fixture."""
    root = tmp_path / name
    shutil.copytree(FIXTURE, root)
    mutate(root)
    with pytest.raises(RuntimeError) as error:
        run(root, monkeypatch)
    assert expected in str(error.value)
