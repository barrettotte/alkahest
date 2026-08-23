"""Exercise deterministic companion packaging and stale-artifact failures."""

import shutil
import sys
import tempfile
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR.parents[1] / "src"))

from alkahest.common import ContractError
from alkahest.companion_bundles import (
    check_companion_bundles,
    package_companion_bundles,
)


FIXTURE = SCRIPT_DIR.parents[1] / "tests/companions/base"


def expect_failure(name, expected, mutate):
    with tempfile.TemporaryDirectory(
        prefix=f"alkahest-companion-bundle-{name}."
    ) as temporary:
        parent = Path(temporary)
        book_root = parent / "book"
        output_root = parent / "output"
        shutil.copytree(FIXTURE, book_root)
        package_companion_bundles(book_root, output_root)
        mutate(output_root)
        try:
            check_companion_bundles(book_root, output_root)
        except ContractError as error:
            if expected not in str(error):
                raise RuntimeError(
                    f"error: companion bundle fixture {name} missed "
                    f"{expected!r}: {error}"
                ) from error
        else:
            raise RuntimeError(
                f"error: companion bundle fixture {name} unexpectedly passed"
            )


def main():
    with tempfile.TemporaryDirectory(
        prefix="alkahest-companion-bundle-valid."
    ) as temporary:
        parent = Path(temporary)
        first, second = parent / "first", parent / "second"
        package_companion_bundles(FIXTURE, first)
        package_companion_bundles(FIXTURE, second)
        result = check_companion_bundles(FIXTURE, first)
        first_files = {path.name: path.read_bytes() for path in first.iterdir()}
        second_files = {path.name: path.read_bytes() for path in second.iterdir()}
        if first_files != second_files or result["bundles"] != 1:
            raise RuntimeError("error: companion bundle output is not deterministic")

    archive = "fixture-companion-1.0.0.zip"
    expect_failure(
        "archive-drift",
        "stale or changed",
        lambda root: (root / archive).write_bytes(
            (root / archive).read_bytes() + b"changed"
        ),
    )
    expect_failure(
        "sidecar-drift",
        "stale or changed",
        lambda root: (root / f"{archive}.sha256").write_text(
            "0" * 64 + f"  {archive}\n", encoding="utf-8"
        ),
    )
    expect_failure(
        "missing-archive",
        "output is missing",
        lambda root: (root / archive).unlink(),
    )
    expect_failure(
        "unexpected-output",
        "unexpected files",
        lambda root: (root / "old-companion.zip").write_bytes(b"stale"),
    )
    print(
        "ok: companion bundle fixtures "
        "(deterministic package; 4 stale/missing/unexpected artifacts rejected)"
    )


if __name__ == "__main__":
    try:
        main()
    except (ContractError, OSError, RuntimeError) as error:
        print(error, file=sys.stderr)
        raise SystemExit(1)
