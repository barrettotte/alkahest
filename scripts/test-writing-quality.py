"""Exercise end-to-end writing fixtures with the pinned CSpell and Vale tools."""

import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
FIXTURES = ROOT / "tests/writing"
OVERRIDE_VALIDATOR = ROOT / "scripts/check-writing-overrides.py"
TOOLCHAIN_LIBRARY = ROOT / "scripts/lib/toolchain.sh"
SOURCE_SUFFIXES = {".md", ".qmd"}

CASES = (
    {
        "name": "visible spelling",
        "source": "negative/cspell/visible.qmd",
        "destination": "book/visible.qmd",
        "checker": "cspell",
        "returncode": 1,
        "required": ("visiblemisspellng",),
        "forbidden": (),
    },
    {
        "name": "syntax boundary",
        "source": "negative/cspell/adjacent.qmd",
        "destination": "book/adjacent.qmd",
        "checker": "cspell",
        "returncode": 1,
        "required": ("adjacentmisspellng", "displayadjacentmisspellng"),
        "forbidden": ("inlinecodemisspellng", "mathmisspellng"),
    },
    {
        "name": "front matter value",
        "source": "negative/cspell/frontmatter.qmd",
        "destination": "book/frontmatter.qmd",
        "checker": "cspell",
        "returncode": 1,
        "required": ("Frontmattermisspellng",),
        "forbidden": ("structuralkeymisspellng",),
    },
    {
        "name": "visible icon label",
        "source": "negative/cspell/icon-label.qmd",
        "destination": "book/icon-label.qmd",
        "checker": "cspell",
        "returncode": 1,
        "required": ("Warnnglabel",),
        "forbidden": ("iconnamemisspellng",),
    },
    {
        "name": "per-path dictionary",
        "source": "negative/cspell/path-scope.md",
        "destination": "docs/path-scope.md",
        "checker": "cspell",
        "returncode": 1,
        "required": ("Donaudampfschifffahrtsgesellschaft",),
        "forbidden": (),
    },
    {
        "name": "shared rejected term",
        "source": "negative/vale/rejected-shared.qmd",
        "destination": "docs/rejected-shared.qmd",
        "checker": "vale",
        "returncode": 1,
        "required": ("Alkahest.Terminology", "Typst"),
        "forbidden": (),
    },
    {
        "name": "book rejected term",
        "source": "negative/vale/rejected-book.qmd",
        "destination": "book/rejected-book.qmd",
        "checker": "vale",
        "returncode": 1,
        "required": ("AlkahestReferenceBook.Terminology", "Verilog"),
        "forbidden": (),
    },
    {
        "name": "subjective warning",
        "source": "negative/vale/warning-only.qmd",
        "destination": "book/warning-only.qmd",
        "checker": "vale",
        "returncode": 0,
        "required": ("Vale.Repetition",),
        "forbidden": (),
    },
)


def fail(message):
    raise RuntimeError(message)


def toolchain_image():
    text = TOOLCHAIN_LIBRARY.read_text(encoding="utf-8")
    match = re.search(r'ALKAHEST_TOOLCHAIN_IMAGE="([^"]+)"', text)
    if not match:
        fail("cannot read the publishing image from scripts/lib/toolchain.sh")
    return match.group(1)


def copy_environment(destination):
    destination.mkdir(parents=True)
    shutil.copy2(ROOT / "cspell.json", destination / "cspell.json")
    shutil.copy2(ROOT / ".vale.ini", destination / ".vale.ini")
    shutil.copytree(ROOT / ".vale", destination / ".vale")
    shutil.copytree(ROOT / "config/writing", destination / "config/writing")
    (destination / "book/dictionaries").mkdir(parents=True)
    shutil.copy2(
        ROOT / "book/dictionaries/accepted.txt",
        destination / "book/dictionaries/accepted.txt",
    )


def copy_tree_contents(source, destination):
    for path in sorted(source.rglob("*")):
        if not path.is_file():
            continue
        target = destination / path.relative_to(source)
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(path, target)


def sources(root):
    return sorted(
        path.relative_to(root).as_posix()
        for tree in (root / "book", root / "docs")
        if tree.is_dir()
        for path in tree.rglob("*")
        if path.is_file() and path.suffix.lower() in SOURCE_SUFFIXES
    )


def run_container(root, image, checker, paths):
    uid = os.getuid()
    gid = os.getgid()
    command = [
        "podman",
        "run",
        "--rm",
        "--pull=never",
        "--network=none",
        "--userns=keep-id",
        "--user",
        f"{uid}:{gid}",
        "--security-opt",
        "label=disable",
        "--tmpfs",
        "/tmp:rw,size=128m,mode=1777",
        "--env",
        "HOME=/tmp",
        "--volume",
        f"{root}:/workspace:ro",
        "--workdir",
        "/workspace",
        image,
    ]
    if checker == "cspell":
        command.extend(
            [
                "cspell",
                "lint",
                "--config",
                "cspell.json",
                "--no-config-search",
                "--root",
                "/workspace",
                "--no-cache",
                "--no-progress",
                "--no-summary",
                "--no-color",
                "--unique",
                "--validate-directives",
                *paths,
            ]
        )
    elif checker == "vale":
        command.extend(
            [
                "vale",
                "--config=.vale.ini",
                "--no-global",
                "--no-wrap",
                "--output=line",
                *paths,
            ]
        )
    else:
        fail("unknown writing checker: " + checker)
    try:
        return subprocess.run(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            encoding="utf-8",
            timeout=20,
        )
    except subprocess.TimeoutExpired:
        fail(f"{checker} exceeded the 20-second fixture runtime limit")


def require_result(name, result, returncode, required=(), forbidden=()):
    if result.returncode != returncode:
        fail(
            f"{name} returned {result.returncode}, expected {returncode}:\n{result.stdout}"
        )
    for marker in required:
        if marker not in result.stdout:
            fail(f"{name} missed expected marker '{marker}':\n{result.stdout}")
    for marker in forbidden:
        if marker in result.stdout:
            fail(f"{name} exposed excluded marker '{marker}':\n{result.stdout}")


def check_positive(parent, image):
    root = parent / "positive"
    copy_environment(root)
    copy_tree_contents(FIXTURES / "positive", root)
    paths = sources(root)
    if len(paths) != 4:
        fail(f"positive fixture inventory has {len(paths)} sources, expected 4")

    try:
        override_result = subprocess.run(
            [sys.executable, str(OVERRIDE_VALIDATOR), "--root", str(root)],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            encoding="utf-8",
            timeout=20,
        )
    except subprocess.TimeoutExpired:
        fail("override validator exceeded the 20-second fixture runtime limit")
    require_result("positive override policy", override_result, 0)

    for checker in ("cspell", "vale"):
        result = run_container(root, image, checker, paths)
        require_result(f"positive {checker} fixtures", result, 0)
        if result.stdout.strip():
            fail(f"positive {checker} fixtures produced findings:\n{result.stdout}")


def check_cases(parent, image):
    groups = {}
    for case in CASES:
        groups.setdefault((case["checker"], case["returncode"]), []).append(case)
    for index, ((checker, returncode), cases) in enumerate(groups.items(), start=1):
        root = parent / f"case-group-{index}"
        copy_environment(root)
        destinations = []
        required = []
        forbidden = []
        for case in cases:
            source = FIXTURES / case["source"]
            destination = root / case["destination"]
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, destination)
            destinations.append(case["destination"])
            required.extend(case["required"])
            forbidden.extend(case["forbidden"])
        name = ", ".join(case["name"] for case in cases)
        result = run_container(root, image, checker, destinations)
        require_result(
            name,
            result,
            returncode,
            required,
            forbidden,
        )


def main():
    if os.getuid() == 0:
        fail("writing-quality fixtures must run as a non-root host user")
    if shutil.which("podman") is None:
        fail("Podman is required but was not found")
    image = toolchain_image()
    try:
        image_check = subprocess.run(
            ["podman", "image", "exists", image],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            timeout=10,
        )
    except subprocess.TimeoutExpired:
        fail("Podman image lookup exceeded the 10-second runtime limit")
    if image_check.returncode != 0:
        fail("publishing image is not available locally; run make bootstrap")

    with tempfile.TemporaryDirectory(prefix="alkahest-writing-quality.") as directory:
        parent = Path(directory)
        check_positive(parent, image)
        check_cases(parent, image)

    print(
        "ok: writing-quality fixtures (4 positive sources; 8 negative/warning "
        "cases; syntax, front matter, icons, terminology scopes, and overrides locked)"
    )


if __name__ == "__main__":
    try:
        main()
    except (OSError, RuntimeError) as error:
        print("error: " + str(error), file=sys.stderr)
        sys.exit(1)
