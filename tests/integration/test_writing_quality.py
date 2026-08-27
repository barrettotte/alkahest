"""Exercise end-to-end writing fixtures with the pinned CSpell and Vale tools."""

import os
import re
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Never, TypedDict

import pytest

from alkahest.process import run_process

ROOT = Path(__file__).resolve().parent.parent.parent
FIXTURES = ROOT / "tests/writing"
TOOLCHAIN_LIBRARY = ROOT / "scripts/toolchain.sh"
SOURCE_SUFFIXES = {".md", ".qmd"}


class Case(TypedDict):
    """One writing-quality fixture contract."""

    name: str
    source: str
    destination: str
    checker: str
    returncode: int
    required: tuple[str, ...]
    forbidden: tuple[str, ...]


CASES: tuple[Case, ...] = (
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
        "source": "negative/cspell/rejected-shared.qmd",
        "destination": "docs/rejected-shared.qmd",
        "checker": "cspell",
        "returncode": 1,
        "required": ("typst",),
        "forbidden": (),
    },
    {
        "name": "book rejected term",
        "source": "negative/cspell/rejected-book.qmd",
        "destination": "book/rejected-book.qmd",
        "checker": "cspell",
        "returncode": 1,
        "required": ("verilog",),
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


def fail(message: str) -> Never:
    """Raise one writing-quality fixture error."""
    raise RuntimeError(message)


def toolchain_image() -> str:
    """Read the pinned publishing image name."""
    text = TOOLCHAIN_LIBRARY.read_text(encoding="utf-8")
    match = re.search(r'ALKAHEST_TOOLCHAIN_IMAGE="([^"]+)"', text)
    if not match:
        fail("cannot read the publishing image from scripts/toolchain.sh")
    return match.group(1)


def copy_environment(destination: Path) -> None:
    """Copy the shared writing-check configuration."""
    destination.mkdir(parents=True)
    shutil.copy2(ROOT / "cspell.json", destination / "cspell.json")
    shutil.copy2(ROOT / ".vale.ini", destination / ".vale.ini")
    (destination / "book/dictionaries").mkdir(parents=True)
    shutil.copy2(ROOT / "book/dictionaries/accepted.txt", destination / "book/dictionaries/accepted.txt")


def copy_tree_contents(source: Path, destination: Path) -> None:
    """Copy one fixture tree into an isolated root."""
    for path in sorted(source.rglob("*")):
        if not path.is_file():
            continue
        target = destination / path.relative_to(source)
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(path, target)


def sources(root: Path) -> list[str]:
    """List writing sources below one fixture root."""
    return sorted(
        path.relative_to(root).as_posix()
        for tree in (root / "book", root / "docs")
        if tree.is_dir()
        for path in tree.rglob("*")
        if path.is_file() and path.suffix.lower() in SOURCE_SUFFIXES
    )


def checker_arguments(checker: str, paths: list[str]) -> list[str]:
    """Build arguments for one writing checker."""
    if checker == "cspell":
        return [
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
    if checker == "vale":
        return ["vale", "--config=.vale.ini", "--no-global", "--no-wrap", "--output=line", *paths]
    fail("unknown writing checker: " + checker)


def run_container(
    root: Path, image: str, checker: str, paths: list[str], podman: str
) -> subprocess.CompletedProcess[str]:
    """Run one writing checker in the locked container."""
    container_tmp = Path("/") / "tmp"
    command = [
        podman,
        "run",
        "--rm",
        "--pull=never",
        "--network=none",
        "--userns=keep-id",
        "--user",
        f"{os.getuid()}:{os.getgid()}",
        "--security-opt",
        "label=disable",
        "--tmpfs",
        f"{container_tmp}:rw,size=128m,mode=1777",
        "--env",
        f"HOME={container_tmp}",
        "--volume",
        f"{root}:/workspace:ro",
        "--workdir",
        "/workspace",
        image,
        *checker_arguments(checker, paths),
    ]
    try:
        return run_process(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            encoding="utf-8",
            timeout=20,
            check=False,
        )
    except subprocess.TimeoutExpired:
        fail(f"{checker} exceeded the 20-second fixture runtime limit")


def require_result(
    name: str,
    result: subprocess.CompletedProcess[str],
    returncode: int,
    required: tuple[str, ...] | list[str] = (),
    forbidden: tuple[str, ...] | list[str] = (),
) -> None:
    """Validate one writing-check process result."""
    if result.returncode != returncode:
        fail(f"{name} returned {result.returncode}, expected {returncode}:\n{result.stdout}")
    for marker in required:
        if marker not in result.stdout:
            fail(f"{name} missed expected marker '{marker}':\n{result.stdout}")
    for marker in forbidden:
        if marker in result.stdout:
            fail(f"{name} exposed excluded marker '{marker}':\n{result.stdout}")


def check_positive(parent: Path, image: str, podman: str) -> None:
    """Require all positive writing fixtures to pass quietly."""
    root = parent / "positive"
    copy_environment(root)
    copy_tree_contents(FIXTURES / "positive", root)
    paths = sources(root)
    if len(paths) != 4:
        fail(f"positive fixture inventory has {len(paths)} sources, expected 4")

    for checker in ("cspell", "vale"):
        result = run_container(root, image, checker, paths, podman)
        require_result(f"positive {checker} fixtures", result, 0)
        if result.stdout.strip():
            fail(f"positive {checker} fixtures produced findings:\n{result.stdout}")


def check_cases(parent: Path, image: str, podman: str) -> None:
    """Require grouped negative writing fixtures to fail correctly."""
    groups: dict[tuple[str, int], list[Case]] = {}
    for case in CASES:
        groups.setdefault((case["checker"], case["returncode"]), []).append(case)
    for index, ((checker, returncode), cases) in enumerate(groups.items(), start=1):
        root = parent / f"case-group-{index}"
        copy_environment(root)
        destinations: list[str] = []
        required: list[str] = []
        forbidden: list[str] = []

        for case in cases:
            source = FIXTURES / case["source"]
            destination = root / case["destination"]
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, destination)
            destinations.append(case["destination"])
            required.extend(case["required"])
            forbidden.extend(case["forbidden"])

        name = ", ".join(case["name"] for case in cases)
        result = run_container(root, image, checker, destinations, podman)
        require_result(name, result, returncode, required, forbidden)


def main() -> None:
    """Exercise end-to-end writing-quality fixtures."""
    if os.getuid() == 0:
        fail("writing-quality fixtures must run as a non-root host user")
    podman = shutil.which("podman")
    if podman is None:
        fail("Podman is required but was not found")
    image = toolchain_image()

    try:
        image_check = run_process(
            [podman, "image", "exists", image],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            timeout=10,
            check=False,
        )
    except subprocess.TimeoutExpired:
        fail("Podman image lookup exceeded the 10-second runtime limit")
    if image_check.returncode != 0:
        fail("publishing image is not available locally; run make bootstrap")

    with tempfile.TemporaryDirectory(prefix="alkahest-writing-quality.") as directory:
        parent = Path(directory)
        check_positive(parent, image, podman)
        check_cases(parent, image, podman)

    print(
        "ok: writing-quality fixtures (4 positive sources; 8 negative/warning "
        "cases; syntax, front matter, icons, terminology, and overrides locked)"
    )


@pytest.mark.locked
def test_contract() -> None:
    """Run the writing-quality contract fixtures under pytest."""
    main()
