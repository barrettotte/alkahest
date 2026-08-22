"""Exercise valid and invalid static-only execution-policy fixtures."""

import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path


SCRIPT_DIR = Path(__file__).resolve().parent
BASE = SCRIPT_DIR.parent / "tests" / "execution" / "base"
VALIDATOR = SCRIPT_DIR / "check-execution-policy.py"


def run(root):
    environment = os.environ.copy()
    environment["ALKAHEST_EXECUTION_BOOK_ROOT"] = str(root)
    return subprocess.run(
        [sys.executable, str(VALIDATOR)],
        env=environment,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        encoding="utf-8",
    )


def replace(path, old, new):
    text = path.read_text(encoding="utf-8")
    if old not in text:
        raise RuntimeError("fixture mutation text not found: " + old)
    path.write_text(text.replace(old, new, 1), encoding="utf-8")


def expect_failure(parent, name, expected, mutate):
    root = parent / name
    shutil.copytree(str(BASE), str(root))
    mutate(root)
    result = run(root)
    if result.returncode == 0:
        raise RuntimeError("invalid execution fixture unexpectedly passed: " + name)
    if expected not in result.stdout:
        raise RuntimeError(
            "execution fixture '" + name + "' missed diagnostic '" + expected + "':\n" + result.stdout
        )


def main():
    with tempfile.TemporaryDirectory(prefix="alkahest-execution-tests.") as directory:
        parent = Path(directory)
        valid = parent / "valid"
        shutil.copytree(str(BASE), str(valid))
        result = run(valid)
        if result.returncode != 0:
            raise RuntimeError("valid execution fixture failed:\n" + result.stdout)

        shared = parent / "valid-shared-defaults"
        shutil.copytree(str(BASE), str(shared))
        canonical = shared / "_quarto.yml"
        canonical_text = canonical.read_text(encoding="utf-8")
        execute_block = "execute:\n  enabled: false\n  cache: false\n  freeze: false\n"
        if execute_block not in canonical_text:
            raise RuntimeError("valid execution fixture lacks its static block")
        canonical.write_text(
            canonical_text.replace(
                execute_block,
                "metadata-files:\n  - alkahest-defaults.yml\n",
                1,
            ),
            encoding="utf-8",
        )
        (shared / "alkahest-defaults.yml").write_text(execute_block, encoding="utf-8")
        result = run(shared)
        if result.returncode != 0:
            raise RuntimeError("valid shared-default execution fixture failed:\n" + result.stdout)

        expect_failure(
            parent,
            "executable-fence",
            "uses executable cell syntax '{python}'",
            lambda root: replace(root / "chapter.qmd", "{.python}", "{python}"),
        )
        expect_failure(
            parent,
            "tilde-executable-fence",
            "uses executable cell syntax '{bash}'",
            lambda root: (root / "chapter.qmd").write_text(
                "# Fixture\n\n~~~{bash}\necho unsafe\n~~~\n", encoding="utf-8"
            ),
        )
        expect_failure(
            parent,
            "document-execute",
            "overrides forbidden execution key 'execute'",
            lambda root: (root / "chapter.qmd").write_text(
                "---\nexecute:\n  enabled: true\n---\n\n# Fixture\n", encoding="utf-8"
            ),
        )
        expect_failure(
            parent,
            "document-jupyter",
            "overrides forbidden execution key 'jupyter'",
            lambda root: (root / "chapter.qmd").write_text(
                "---\njupyter: python3\n---\n\n# Fixture\n", encoding="utf-8"
            ),
        )
        expect_failure(
            parent,
            "enabled-config",
            "must disable execution, cache, and freeze",
            lambda root: replace(root / "_quarto.yml", "enabled: false", "enabled: true"),
        )
        expect_failure(
            parent,
            "profile-override",
            "may not override execute, cache, or freeze policy",
            lambda root: (root / "_quarto-preview.yml").write_text(
                "execute:\n  enabled: true\n", encoding="utf-8"
            ),
        )
        expect_failure(
            parent,
            "missing-shared-defaults",
            "shared Alkahest defaults file is missing",
            lambda root: (root / "_quarto.yml").write_text(
                "metadata-files:\n  - alkahest-defaults.yml\n", encoding="utf-8"
            ),
        )
        expect_failure(
            parent,
            "notebook-source",
            "registered manuscript source uses an executable notebook format",
            lambda root: json.loads((root / "editions.json").read_text(encoding="utf-8"))
            and (root / "editions.json").write_text(
                '{"sources":{"chapter":{"path":"chapter.ipynb"}}}\n', encoding="utf-8"
            ),
        )
        expect_failure(
            parent,
            "release-policy",
            "does not match the static publication contract",
            lambda root: replace(root / "execution-policy.json", '"release": "static-only"', '"release": "allowed"'),
        )
        expect_failure(
            parent,
            "cache-policy",
            "does not match the static publication contract",
            lambda root: replace(
                root / "execution-policy.json",
                '"cache": "disabled-until-verifier-exists"',
                '"cache": "enabled"',
            ),
        )

    print(
        "ok: execution-policy fixtures "
        "(direct and shared static defaults accepted; 10 execution, override, "
        "notebook, defaults, and policy violations rejected)"
    )


if __name__ == "__main__":
    try:
        main()
    except RuntimeError as error:
        print("error: " + str(error), file=sys.stderr)
        sys.exit(1)
