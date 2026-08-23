"""Run the minimal author workflow from an extracted Alkahest engine."""

import argparse
import shutil
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR.parent / "src"))

from alkahest.author_project import (
    AuthorProjectError,
    add_chapter,
    compile_workspace,
    doctor,
    render,
)


ENGINE_ROOT = SCRIPT_DIR.parent


def parse_arguments():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("doctor", help="check book inputs and rendering tools")
    commands.add_parser("check", help="validate book.toml and compile both workspaces")
    chapter = commands.add_parser("chapter", help="create the next numbered chapter")
    chapter.add_argument("title")
    commands.add_parser("draft", help="build the full HTML draft")
    commands.add_parser("build", help="build HTML, EPUB, and production Typst")
    commands.add_parser("build-all", help="also build the secondary LuaLaTeX PDF")
    commands.add_parser("excerpt", help="build the public HTML, EPUB, and Typst excerpt")
    commands.add_parser("clean", help="remove disposable build output")
    return parser.parse_args()


def main():
    arguments = parse_arguments()
    root = Path.cwd().resolve()
    if arguments.command == "doctor":
        environment = doctor(root)
        print(
            f"ok: author environment ({environment['renderer']}; "
            f"{environment['chapters']} chapters)"
        )
    elif arguments.command == "check":
        full = compile_workspace(root, ENGINE_ROOT, "full")
        excerpt = compile_workspace(root, ENGINE_ROOT, "excerpt")
        print(
            f"ok: author project ({len(full['sources'])} full sources; "
            f"{len(excerpt['sources'])} excerpt sources)"
        )
    elif arguments.command == "chapter":
        print(add_chapter(root, arguments.title).relative_to(root))
    elif arguments.command == "draft":
        render(root, ENGINE_ROOT, "full", ["html"])
    elif arguments.command == "build":
        render(root, ENGINE_ROOT, "full", ["html", "epub", "typst"])
    elif arguments.command == "build-all":
        render(root, ENGINE_ROOT, "full", ["html", "epub", "typst", "latex"])
    elif arguments.command == "excerpt":
        render(root, ENGINE_ROOT, "excerpt", ["html", "epub", "typst"])
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
        raise SystemExit(1)
