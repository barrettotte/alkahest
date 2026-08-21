"""Exercise valid and invalid manuscript editorial-integrity contracts."""

import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path


SCRIPT_DIR = Path(__file__).resolve().parent
FIXTURE = SCRIPT_DIR.parent / "tests" / "editorial-integrity" / "base"


def replace(path, old, new):
    content = path.read_text(encoding="utf-8")
    if old not in content:
        raise RuntimeError(f"error: fixture mutation cannot find {old!r} in {path}")
    path.write_text(content.replace(old, new, 1), encoding="utf-8")


def run_validator(root):
    environment = os.environ.copy()
    environment["ALKAHEST_EDITORIAL_BOOK_ROOT"] = str(root)
    return subprocess.run(
        [sys.executable, str(SCRIPT_DIR / "check-editorial-integrity.py")],
        env=environment,
        text=True,
        capture_output=True,
        check=False,
    )


def expect_failure(parent, name, expected, mutation):
    root = parent / name
    shutil.copytree(FIXTURE, root)
    mutation(root)
    result = run_validator(root)
    output = result.stdout + result.stderr
    if result.returncode == 0:
        raise RuntimeError(f"error: editorial fixture {name} unexpectedly passed")
    if expected not in output:
        raise RuntimeError(
            f"error: editorial fixture {name} missed diagnostic {expected!r}:\n{output}"
        )


def main():
    with tempfile.TemporaryDirectory(prefix="alkahest-editorial-tests.") as directory:
        parent = Path(directory)
        valid = parent / "valid"
        shutil.copytree(FIXTURE, valid)
        result = run_validator(valid)
        if result.returncode:
            raise RuntimeError(
                "error: valid editorial fixture failed:\n"
                + result.stdout
                + result.stderr
            )

        expect_failure(
            parent,
            "broken-link",
            "link target 'missing.qmd#sec-other' does not exist",
            lambda root: replace(root / "chapter.qmd", "other.qmd#sec-other", "missing.qmd#sec-other"),
        )
        expect_failure(
            parent,
            "broken-image",
            "image target 'assets/missing.svg' does not exist",
            lambda root: replace(root / "chapter.qmd", "assets/pixel.svg", "assets/missing.svg"),
        )
        expect_failure(
            parent,
            "missing-alt",
            "needs nonempty alt text, fig-alt, or .decorative",
            lambda root: replace(root / "chapter.qmd", "![A fixture pixel]", "![]"),
        )
        expect_failure(
            parent,
            "missing-diagram-alt",
            "mermaid diagram needs a nonempty fig-alt option",
            lambda root: replace(
                root / "chapter.qmd",
                'fig-alt="One node named A."',
                'fig-alt=""',
            ),
        )
        expect_failure(
            parent,
            "missing-inline-math-alt",
            "inline math needs an .alkahest-math-alt span",
            lambda root: replace(
                root / "chapter.qmd",
                '[$V = I R$]{.alkahest-math-alt alt="voltage equals current times resistance"}',
                "$V = I R$",
            ),
        )
        expect_failure(
            parent,
            "missing-display-math-alt",
            "display math needs nonempty alt text",
            lambda root: replace(
                root / "chapter.qmd",
                '$$ {#eq-fixture alt="Ohm\'s law"}',
                "$$ {#eq-fixture}",
            ),
        )
        expect_failure(
            parent,
            "duplicate-id",
            "duplicate ID 'sec-fixture'",
            lambda root: replace(root / "other.qmd", "sec-other", "sec-fixture"),
        )
        expect_failure(
            parent,
            "missing-fragment",
            "link fragment '#sec-missing' is not declared",
            lambda root: replace(root / "chapter.qmd", "other.qmd#sec-other", "other.qmd#sec-missing"),
        )
        expect_failure(
            parent,
            "dangling-reference",
            "dangling cross-reference '@sec-missing'",
            lambda root: replace(root / "chapter.qmd", "@sec-other.", "@sec-missing."),
        )
    print(
        "ok: editorial-integrity fixtures "
        "(valid links, alternatives, decorative image, diagram, IDs, and references; "
        "9 invalid contracts rejected)"
    )


if __name__ == "__main__":
    try:
        main()
    except (OSError, RuntimeError) as error:
        print(error, file=sys.stderr)
        raise SystemExit(1)
