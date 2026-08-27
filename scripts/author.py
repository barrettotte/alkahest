"""Run the minimal author workflow from a packaged or in-tree Alkahest engine."""

from __future__ import annotations

import argparse
import shutil
import sys
import tempfile
from collections.abc import Generator
from contextlib import contextmanager
from pathlib import Path
from typing import cast

SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR.parent / "src"))

from alkahest.author_project import (
    AuthorProjectError,
    add_chapter,
    compile_workspace,
    doctor,
    render,
)


class Arguments(argparse.Namespace):
    """Typed author command-line arguments."""

    command: str
    title: str


def parse_arguments() -> Arguments:
    """Parse one author command."""
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("doctor", help="check book inputs and rendering tools")
    commands.add_parser("check", help="validate book.toml and compile both workspaces")

    chapter = commands.add_parser("chapter", help="create the next numbered chapter")
    chapter.add_argument("title")

    commands.add_parser("draft", help="build the full HTML draft")
    commands.add_parser("build", help="build HTML, EPUB, and production Typst")
    commands.add_parser("excerpt", help="build the public HTML, EPUB, and Typst excerpt")
    commands.add_parser("clean", help="remove disposable build output")
    return cast(Arguments, parser.parse_args())


@contextmanager
def engine_root(book_root: Path) -> Generator[Path]:
    """Expose in-tree sources in the same layout as the embedded engine."""
    root = SCRIPT_DIR.parent
    source_root = root / "book"
    if not source_root.is_dir():
        yield root
        return

    development_root = Path(book_root) / "_build"
    development_root.mkdir(parents=True, exist_ok=True)

    with tempfile.TemporaryDirectory(prefix=".development-engine.", dir=development_root) as temporary:
        engine = Path(temporary)
        for directory in ("_extensions", "filters", "icons", "theme", "typst"):
            (engine / directory).symlink_to(source_root / directory, target_is_directory=True)
        defaults = engine / "defaults"
        defaults.mkdir()
        (defaults / "quarto.yml").symlink_to(source_root / "alkahest-defaults.yml")
        (engine / "_brand.yml").symlink_to(source_root / "_brand.yml")
        yield engine


def main() -> None:
    """Run the selected author workflow."""
    arguments = parse_arguments()
    root = Path.cwd().resolve()
    with engine_root(root) as engine:
        if arguments.command == "doctor":
            environment = doctor(root)
            print(f"ok: author environment ({environment['renderer']}; {environment['chapters']} chapters)")
        elif arguments.command == "check":
            full = compile_workspace(root, engine, "full")
            excerpt = compile_workspace(root, engine, "excerpt")
            print(
                f"ok: author project ({len(full['sources'])} full sources; {len(excerpt['sources'])} excerpt sources)"
            )
        elif arguments.command == "chapter":
            print(add_chapter(root, arguments.title).relative_to(root))
        elif arguments.command == "draft":
            render(root, engine, "full", ["html"])
        elif arguments.command == "build":
            render(root, engine, "full", ["html", "epub", "typst"])
        elif arguments.command == "excerpt":
            render(root, engine, "excerpt", ["html", "epub", "typst"])
        elif arguments.command == "clean":
            output = root / "_build"
            if output.exists() and output.parent == root:
                shutil.rmtree(output)
            print("ok: removed disposable build output")


if __name__ == "__main__":
    try:
        main()
    except (AuthorProjectError, OSError, UnicodeError) as error:
        print(error, file=sys.stderr)
        raise SystemExit(1) from None
