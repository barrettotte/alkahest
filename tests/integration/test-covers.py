"""Exercise cover policy, geometry, deterministic output, and drift failures."""

import copy
import json
import sys
import tempfile
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR.parents[1] / "src"))

from alkahest.common import ContractError
from alkahest.covers import (
    check_cover_output_bytes,
    cover_geometry,
    expected_cover_outputs,
    validate_cover_document,
)
from alkahest.manifestations import load_and_validate


ROOT = SCRIPT_DIR.parents[1]
BASE_POLICY = json.loads(
    (ROOT / "config/covers/cover-policy.json").read_text(encoding="utf-8")
)
PUBLICATION = json.loads((ROOT / "book/publication.json").read_text(encoding="utf-8"))
_REGISTRY, RECORDS = load_and_validate(ROOT)


def expect_policy_failure(name, expected, mutate):
    policy = copy.deepcopy(BASE_POLICY)
    records = copy.deepcopy(RECORDS)
    publication = copy.deepcopy(PUBLICATION)
    mutate(policy, records, publication)
    try:
        validate_cover_document(policy, records, publication)
    except ContractError as error:
        if expected not in str(error):
            raise RuntimeError(
                f"error: cover fixture {name} missed {expected!r}: {error}"
            ) from error
    else:
        raise RuntimeError(f"error: cover fixture {name} unexpectedly passed")


def write_outputs(root, outputs):
    for profile_id, files in outputs.items():
        directory = root / profile_id
        directory.mkdir(parents=True)
        for filename, content in files.items():
            (directory / filename).write_bytes(content)


def expect_artifact_failure(name, expected, mutate):
    facts = {
        "cover-print-7x10": {"pages": 73, "sha256": "a" * 64},
        "cover-print-6x9": {"pages": 81, "sha256": "b" * 64},
    }
    _relative, outputs = expected_cover_outputs(ROOT, facts)
    with tempfile.TemporaryDirectory(prefix=f"alkahest-cover-{name}.") as temporary:
        output_root = Path(temporary)
        write_outputs(output_root, outputs)
        mutate(output_root)
        try:
            check_cover_output_bytes(output_root, outputs)
        except ContractError as error:
            if expected not in str(error):
                raise RuntimeError(
                    f"error: cover artifact fixture {name} missed {expected!r}: {error}"
                ) from error
        else:
            raise RuntimeError(
                f"error: cover artifact fixture {name} unexpectedly passed"
            )


def main():
    context = validate_cover_document(BASE_POLICY, RECORDS, PUBLICATION)
    geometry = cover_geometry(
        context["template"], RECORDS["print-full-7x10-en"]["dimensions"], 73
    )
    if (
        geometry["production_pages"] != 74
        or str(geometry["spine_width"]) != "0.166500"
        or str(geometry["wrap_width"]) != "14.416500"
        or geometry["spine_text_enabled"]
    ):
        raise RuntimeError("error: valid cover geometry returned incorrect facts")

    cases = [
        ("schema", "schema_version must be 1", lambda p, _r, _m: p.update(schema_version=2)),
        ("output", "outputs must remain", lambda p, _r, _m: p.update(output_root="covers")),
        ("printer-id", "printer template id", lambda p, _r, _m: p["template"]["printer_template"].update(id="Bad ID")),
        ("revision", "revision must be", lambda p, _r, _m: p["template"]["printer_template"].update(revision=0)),
        ("binding", "currently implements perfect-bound", lambda p, _r, _m: p["template"].update(binding="case-bound")),
        ("caliper", "outside its allowed range", lambda p, _r, _m: p["template"]["paper"].update(sheet_caliper_in="0")),
        ("page-policy", "must be round-up-even", lambda p, _r, _m: p["template"].update(page_count_policy="literal")),
        ("press-ready", "cannot claim press readiness", lambda p, _r, _m: p["template"].update(press_ready=True)),
        (
            "barcode",
            "does not fit",
            lambda _p, r, _m: (
                r["print-full-7x10-en"]["dimensions"].update(width=2.4),
                r["pdf-full-7x10-en"]["dimensions"].update(width=2.4),
            ),
        ),
        ("duplicate", "profile id is duplicated", lambda p, _r, _m: p["profiles"][1].update(id=p["profiles"][0]["id"])),
        ("unknown-print", "needs a print manifestation", lambda p, _r, _m: p["profiles"][0].update(manifestation="missing")),
        ("relation", "differs from its print interior relation", lambda p, _r, _m: p["profiles"][0].update(interior_manifestation="pdf-full-6x9-en")),
        ("coverage", "cover exactly", lambda p, _r, _m: p["profiles"].pop()),
        ("metadata", "canonical title", lambda _p, _r, m: m["work"].update(title="")),
    ]
    for name, expected, mutate in cases:
        expect_policy_failure(name, expected, mutate)

    facts = {
        "cover-print-7x10": {"pages": 73, "sha256": "a" * 64},
        "cover-print-6x9": {"pages": 81, "sha256": "b" * 64},
    }
    _relative, outputs = expected_cover_outputs(ROOT, facts)
    with tempfile.TemporaryDirectory(prefix="alkahest-cover-valid.") as temporary:
        output_root = Path(temporary)
        write_outputs(output_root, outputs)
        check_cover_output_bytes(output_root, outputs)
    expect_artifact_failure(
        "changed",
        "stale or changed",
        lambda root: (root / "cover-print-7x10/cover-template.svg").write_text(
            "changed", encoding="utf-8"
        ),
    )
    expect_artifact_failure(
        "missing",
        "stale or incomplete",
        lambda root: (root / "cover-print-7x10/front-thumbnail.svg").unlink(),
    )
    expect_artifact_failure(
        "extra-profile",
        "profile entries",
        lambda root: (root / "old-cover").mkdir(),
    )
    expect_artifact_failure(
        "root-file",
        "profile entries",
        lambda root: (root / "stale.txt").write_text("stale", encoding="utf-8"),
    )
    expect_artifact_failure(
        "nested-directory",
        "files are stale or incomplete",
        lambda root: (root / "cover-print-7x10/stale").mkdir(),
    )
    print(
        "ok: cover fixtures "
        "(valid geometry/output; 14 policy and 5 artifact failures rejected)"
    )


if __name__ == "__main__":
    try:
        main()
    except (ContractError, OSError, RuntimeError, UnicodeError) as error:
        print(error, file=sys.stderr)
        raise SystemExit(1)
