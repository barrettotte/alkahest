"""Exercise valid and invalid writing-override policy fixtures."""

import json
import subprocess
import sys
import tempfile
from pathlib import Path

from alkahest.process import run_process

VALIDATOR = ("-m", "alkahest.checks.writing_overrides")
VALID_CHAPTER = """# Fixture

<!-- writing-override: Preserve the quoted vendor spelling exactly here. -->
<!-- cspell:disable-next-line -->
quotedwrd

<!-- writing-override: Preserve this deliberately unedited historical passage. -->
<!-- cspell:disable -->
historicalwrd
<!-- cspell:enable -->

<!-- cspell:ignore Oneoffword -->
Oneoffword appears once.

<!-- cspell:words CaseName -->
CaseName appears twice in this CaseName-only file.

<!-- vale Style.Terms["deliberate form"] = NO -->
The deliberate form appears here.
<!-- vale Style.Terms["deliberate form"] = YES -->

<!-- writing-override: Repetition is meaningful in this logic-gate description. -->
<!-- vale Vale.Repetition = NO -->
AND and AND name two gates.
<!-- vale Vale.Repetition = YES -->
"""


def write_root(parent, name, chapter=VALID_CHAPTER):
    root = parent / name
    (root / "book").mkdir(parents=True)
    (root / "docs").mkdir()
    (root / "config/writing").mkdir(parents=True)
    (root / "book/chapter.qmd").write_text(chapter, encoding="utf-8")
    (root / "cspell.json").write_text(
        json.dumps({"version": "0.2", "overrides": []}) + "\n",
        encoding="utf-8",
    )
    (root / ".vale.ini").write_text(
        "[*.{md,qmd}]\nVale.Spelling = NO\n",
        encoding="utf-8",
    )
    (root / "config/writing/terminology.json").write_text(
        json.dumps({"rejected_terms": [{"term": "typst"}]}) + "\n",
        encoding="utf-8",
    )
    return root


def run(root):
    return run_process(
        [sys.executable, *VALIDATOR, "--root", str(root)],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        encoding="utf-8",
        check=False,
    )


def replace(path, old, new):
    text = path.read_text(encoding="utf-8")
    if old not in text:
        raise RuntimeError("fixture mutation text not found: " + old)
    path.write_text(text.replace(old, new, 1), encoding="utf-8")


def expect_failure(parent, name, expected, mutate):
    root = write_root(parent, name)
    mutate(root)
    result = run(root)
    if result.returncode == 0:
        raise RuntimeError("invalid writing-override fixture unexpectedly passed: " + name)
    if expected not in result.stdout:
        raise RuntimeError(
            f"writing-override fixture '{name}' missed '{expected}':\n{result.stdout}"
        )


def main():
    with tempfile.TemporaryDirectory(prefix="alkahest-writing-overrides.") as directory:
        parent = Path(directory)
        valid = write_root(parent, "valid")
        result = run(valid)
        if result.returncode != 0:
            raise RuntimeError("valid writing-override fixture failed:\n" + result.stdout)

        expect_failure(
            parent,
            "missing-reason",
            "broad override needs an immediately preceding writing-override reason",
            lambda root: replace(
                root / "book/chapter.qmd",
                "<!-- writing-override: Preserve the quoted vendor spelling exactly here. -->\n",
                "",
            ),
        )
        expect_failure(
            parent,
            "weak-reason",
            "reason must contain at least four words",
            lambda root: replace(
                root / "book/chapter.qmd",
                "Preserve the quoted vendor spelling exactly here.",
                "Vendor spelling.",
            ),
        )
        expect_failure(
            parent,
            "stale-reason",
            "writing-override reason is not attached to an override",
            lambda root: replace(
                root / "book/chapter.qmd",
                "# Fixture\n",
                "# Fixture\n\n<!-- writing-override: This reason has no attached local suppression. -->\n",
            ),
        )
        expect_failure(
            parent,
            "blanket-vale",
            "blanket Vale off/on overrides are not allowed",
            lambda root: replace(
                root / "book/chapter.qmd",
                "<!-- cspell:ignore Oneoffword -->",
                "<!-- vale off -->",
            ),
        )
        expect_failure(
            parent,
            "unbalanced-cspell",
            "cspell:disable is not restored with cspell:enable",
            lambda root: replace(root / "book/chapter.qmd", "<!-- cspell:enable -->", ""),
        )
        expect_failure(
            parent,
            "unbalanced-vale",
            "Vale rule override is not restored with YES",
            lambda root: replace(
                root / "book/chapter.qmd",
                '<!-- vale Style.Terms["deliberate form"] = YES -->',
                "",
            ),
        )
        expect_failure(
            parent,
            "repeated-one-off",
            "recurs; use cspell:words",
            lambda root: replace(
                root / "book/chapter.qmd",
                "Oneoffword appears once.",
                "Oneoffword appears beside Oneoffword.",
            ),
        )
        expect_failure(
            parent,
            "cross-file-word",
            "appears in multiple files",
            lambda root: (root / "docs/second.md").write_text(
                "# Second\n\nCaseName appears here too.\n", encoding="utf-8"
            ),
        )
        expect_failure(
            parent,
            "rejected-token",
            "broad override needs an immediately preceding writing-override reason",
            lambda root: replace(
                root / "book/chapter.qmd",
                "<!-- cspell:ignore Oneoffword -->\nOneoffword appears once.",
                "<!-- cspell:ignore typst -->\ntypst appears once.",
            ),
        )
        expect_failure(
            parent,
            "rejected-match",
            "broad override needs an immediately preceding writing-override reason",
            lambda root: replace(
                root / "book/chapter.qmd",
                'Style.Terms["deliberate form"]',
                'Style.Terms["typst"]',
            ),
        )
        expect_failure(
            parent,
            "manual-config-word",
            "put accepted terminology in the registry",
            lambda root: (root / "cspell.json").write_text(
                '{"overrides":[{"filename":"book/**","words":["Hidden"]}]}\n',
                encoding="utf-8",
            ),
        )
        expect_failure(
            parent,
            "unjustified-config-rule",
            "disabled rule needs an immediately preceding",
            lambda root: (root / ".vale.ini").write_text(
                "[*.qmd]\nStyle.Terms = NO\n", encoding="utf-8"
            ),
        )

    print(
        "ok: writing-override fixtures (valid narrow overrides accepted; "
        "12 reason, balance, scope, terminology, and config violations rejected)"
    )


def test_contract():
    result = main()
    assert result in (None, 0)
