"""Exercise valid and invalid manuscript editorial-integrity contracts."""

import os
import shutil
import subprocess
import sys
import tempfile
from collections.abc import Callable
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
FIXTURE = SCRIPT_DIR.parents[1] / "tests" / "editorial-integrity" / "base"
type Mutation = Callable[[Path], None]


def replace(path: Path, old: str, new: str) -> None:
    """Replace one exact fixture fragment."""
    content = path.read_text(encoding="utf-8")
    if old not in content:
        raise RuntimeError(f"error: fixture mutation cannot find {old!r} in {path}")
    path.write_text(content.replace(old, new, 1), encoding="utf-8")


def edit(relative: str, old: str, new: str) -> Mutation:
    """Create one typed fixture mutation."""

    def mutate(root: Path) -> None:
        """Apply the configured fixture replacement."""
        replace(root / relative, old, new)

    return mutate


def run_validator(root: Path) -> subprocess.CompletedProcess[str]:
    """Run the editorial validator against one fixture root."""
    environment = os.environ.copy()
    environment["ALKAHEST_EDITORIAL_BOOK_ROOT"] = str(root)
    return subprocess.run(
        [
            sys.executable,
            "-m",
            "alkahest.checks.editorial",
        ],
        env=environment,
        text=True,
        capture_output=True,
        check=False,
    )


def expect_failure(parent: Path, name: str, expected: str, mutation: Mutation) -> None:
    """Require one mutated fixture to fail with a diagnostic."""
    root = parent / name
    shutil.copytree(FIXTURE, root)
    mutation(root)
    result = run_validator(root)
    output = result.stdout + result.stderr

    if result.returncode == 0:
        raise RuntimeError(f"error: editorial fixture {name} unexpectedly passed")
    if expected not in output:
        raise RuntimeError(f"error: editorial fixture {name} missed diagnostic {expected!r}:\n{output}")


def main() -> None:
    """Exercise the editorial validator contract fixtures."""
    with tempfile.TemporaryDirectory(prefix="alkahest-editorial-tests.") as directory:
        parent = Path(directory)
        valid = parent / "valid"
        shutil.copytree(FIXTURE, valid)
        result = run_validator(valid)
        if result.returncode:
            raise RuntimeError("error: valid editorial fixture failed:\n" + result.stdout + result.stderr)

        expect_failure(
            parent,
            "broken-link",
            "link target 'missing.qmd#sec-other' does not exist",
            edit("chapter.qmd", "other.qmd#sec-other", "missing.qmd#sec-other"),
        )
        expect_failure(
            parent,
            "broken-image",
            "image target 'assets/missing.svg' does not exist",
            edit("chapter.qmd", "assets/pixel.svg", "assets/missing.svg"),
        )
        expect_failure(
            parent,
            "missing-alt",
            "needs nonempty alt text, fig-alt, or .decorative",
            edit("chapter.qmd", "![A fixture pixel]", "![]"),
        )
        expect_failure(
            parent,
            "missing-diagram-alt",
            "mermaid diagram needs a nonempty fig-alt option",
            edit(
                "chapter.qmd",
                'fig-alt="One node named A."',
                'fig-alt=""',
            ),
        )
        expect_failure(
            parent,
            "missing-inline-math-alt",
            "inline math needs an .alkahest-math-alt span",
            edit(
                "chapter.qmd",
                '[$V = I R$]{.alkahest-math-alt alt="voltage equals current times resistance"}',
                "$V = I R$",
            ),
        )
        expect_failure(
            parent,
            "missing-display-math-alt",
            "display math needs nonempty alt text",
            edit(
                "chapter.qmd",
                '$$ {#eq-fixture alt="Ohm\'s law"}',
                "$$ {#eq-fixture}",
            ),
        )
        expect_failure(
            parent,
            "duplicate-id",
            "duplicate ID 'sec-fixture'",
            edit("other.qmd", "sec-other", "sec-fixture"),
        )
        expect_failure(
            parent,
            "missing-fragment",
            "link fragment '#sec-missing' is not declared",
            edit("chapter.qmd", "other.qmd#sec-other", "other.qmd#sec-missing"),
        )
        expect_failure(
            parent,
            "dangling-reference",
            "dangling cross-reference '@sec-missing'",
            edit("chapter.qmd", "@sec-other.", "@sec-missing."),
        )
        expect_failure(
            parent,
            "raw-backend-markup",
            "manuscript source must remain backend-neutral",
            edit(
                "chapter.qmd",
                "# Editorial integrity fixture {#sec-fixture}",
                "# Editorial integrity fixture {#sec-fixture}\n\n#pagebreak(){=typst}",
            ),
        )
    print(
        "ok: editorial-integrity fixtures "
        "(valid links, alternatives, decorative image, diagram, IDs, and references; "
        "10 invalid contracts rejected)"
    )


def test_contract() -> None:
    """Run the editorial contract fixtures under pytest."""
    main()
