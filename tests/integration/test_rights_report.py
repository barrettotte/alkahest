"""Exercise rights-report inventory, readiness, and exact-output failures."""

import copy
import json
import sys
import tempfile
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR.parents[1] / "src"))

from alkahest.assets import AssetError
from alkahest.rights_report import (
    build_report,
    check_output_bytes,
    expected_outputs,
    validate_asset_inventory,
)


ROOT = SCRIPT_DIR.parents[1]


def write_outputs(root, outputs):
    root.mkdir(parents=True, exist_ok=True)
    for filename, content in outputs.items():
        (root / filename).write_bytes(content)


def expect_failure(name, expected, callback):
    try:
        callback()
    except AssetError as error:
        if expected not in str(error):
            raise RuntimeError(
                f"error: rights-report fixture {name} missed {expected!r}: {error}"
            ) from error
    else:
        raise RuntimeError(f"error: rights-report fixture {name} unexpectedly passed")


def inventory_failure(name, expected, mutate):
    report = build_report(ROOT)
    assets = copy.deepcopy(report["assets"])
    included = next(item for item in assets if item["distribution"] == "included")
    approved = {
        item["path"]: item["sha256"] for item in assets if item["distribution"] == "included"
    }
    mutate(included)
    expect_failure(
        name,
        expected,
        lambda: validate_asset_inventory(
            assets, approved, {"Apache-2.0", "CC0-1.0", "MIT", "OFL-1.1"}
        ),
    )


def artifact_failure(name, expected, mutate):
    outputs = expected_outputs(ROOT)
    with tempfile.TemporaryDirectory(prefix=f"alkahest-rights-{name}.") as temporary:
        output_root = Path(temporary)
        write_outputs(output_root, outputs)
        mutate(output_root)
        expect_failure(
            name,
            expected,
            lambda: check_output_bytes(output_root, outputs),
        )


def main():
    report = build_report(ROOT)
    if (
        report["summary"]["included_assets"] != 39
        or report["summary"]["runtime_bundles"] != 2
        or report["readiness"]["ready"]
        or len(report["readiness"]["blockers"]) != 4
    ):
        raise RuntimeError("error: valid rights report returned incorrect facts")
    outputs = expected_outputs(ROOT)
    machine = json.loads(outputs["rights-credits.json"])
    if machine != report or b"Release readiness: **BLOCKED**" not in outputs["rights-credits.md"]:
        raise RuntimeError("error: valid rights report outputs differ")
    with tempfile.TemporaryDirectory(prefix="alkahest-rights-valid.") as temporary:
        output_root = Path(temporary)
        write_outputs(output_root, outputs)
        check_output_bytes(output_root, outputs)

    inventory_failure(
        "private-included",
        "includes private asset",
        lambda item: item["rights"].update(public_distribution=False),
    )
    inventory_failure(
        "missing-credit",
        "lacks required attribution",
        lambda item: item["rights"].update(credit_text=""),
    )
    inventory_failure(
        "unlicensed",
        "is unlicensed",
        lambda item: item["rights"].update(license="Unknown-1.0"),
    )
    artifact_failure(
        "changed",
        "stale or changed",
        lambda root: (root / "rights-credits.md").write_text("changed", encoding="utf-8"),
    )
    artifact_failure(
        "missing",
        "stale or incomplete",
        lambda root: (root / "rights-credits.json").unlink(),
    )
    artifact_failure(
        "extra",
        "stale or incomplete",
        lambda root: (root / "notes.txt").write_text("stale", encoding="utf-8"),
    )
    print(
        "ok: rights-report fixtures "
        "(valid blocked-development report; 3 rights and 3 artifact failures rejected)"
    )


def test_contract():
    result = main()
    assert result in (None, 0)
