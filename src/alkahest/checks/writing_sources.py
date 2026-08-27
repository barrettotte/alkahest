"""List canonical manuscript and documentation files for writing checks."""

import argparse
from pathlib import Path
from typing import cast

ROOT = Path(__file__).resolve().parents[3]
ROOT_DOCUMENTS = ("README.md",)
SOURCE_TREES = {
    "book": {".md", ".qmd"},
    "docs": {".md"},
    "guide": {".md", ".qmd"},
}
EXCLUDED_PREFIXES = (
    Path("book/.quarto"),
    Path("book/_build"),
    Path("book/site_libs"),
    Path("book/theme/fonts"),
    Path("guide/.alkahest"),
    Path("guide/_build"),
)


class Arguments(argparse.Namespace):
    """Typed writing-source command arguments."""

    root: Path


def is_below(path: Path, prefix: Path) -> bool:
    """Return whether one relative path is below a prefix."""
    return path.parts[: len(prefix.parts)] == prefix.parts


def writing_sources(root: Path) -> list[str]:
    """List the canonical prose files checked by writing tools."""
    paths: list[Path] = []
    for name in ROOT_DOCUMENTS:
        path = root / name
        if path.is_file():
            paths.append(path)

    for tree, suffixes in SOURCE_TREES.items():
        directory = root / tree
        if not directory.is_dir():
            continue
        for path in directory.rglob("*"):
            if not path.is_file() or path.suffix.lower() not in suffixes:
                continue
            relative = path.relative_to(root)
            if any(is_below(relative, prefix) for prefix in EXCLUDED_PREFIXES):
                continue
            paths.append(path)

    return sorted({path.relative_to(root).as_posix() for path in paths})


def main() -> None:
    """Print the canonical writing-source inventory."""
    parser = argparse.ArgumentParser(description="Print one canonical writing-source path per line.")
    parser.add_argument(
        "--root",
        type=Path,
        default=ROOT,
        help="repository root to inventory (defaults to this checkout)",
    )
    args = cast(Arguments, parser.parse_args())

    sources = writing_sources(args.root.resolve())
    if not sources:
        raise SystemExit("error: no canonical writing sources found")
    if any("\n" in source for source in sources):
        raise SystemExit("error: writing-source paths must not contain newlines")
    print("\n".join(sources))


if __name__ == "__main__":
    main()
