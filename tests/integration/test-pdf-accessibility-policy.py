"""Exercise valid and invalid PDF accessibility evidence and claim states."""

import copy
import json
import subprocess
import sys
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent.parent
CHECKER = ("-m", "alkahest.checks.pdf_accessibility")
SOURCE = ROOT / "book" / "pdf-accessibility.json"


def run_case(name, policy, expected, message=None):
    with tempfile.NamedTemporaryFile("w", suffix=".json", encoding="utf-8") as handle:
        json.dump(policy, handle)
        handle.flush()
        result = subprocess.run(
            [sys.executable, *CHECKER, handle.name],
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=False,
        )
    if result.returncode != expected:
        raise RuntimeError(
            f"{name}: expected status {expected}, got {result.returncode}\n"
            f"stdout: {result.stdout}\nstderr: {result.stderr}"
        )
    if message and message not in result.stderr:
        raise RuntimeError(f"{name}: missing diagnostic '{message}': {result.stderr}")


def changed(base, mutate):
    policy = copy.deepcopy(base)
    mutate(policy)
    return policy


def claim_while_blocked(policy):
    policy["claim"].update(
        {
            "status": "conformant",
            "target_backends": ["typst"],
            "conformance_claim": True,
            "conformance_string": "ISO 14289-1:2014 (PDF/UA-1)",
            "report_location": "reports/pdf-accessibility/typst-review.md",
        }
    )


def block_candidate(policy, blocker):
    policy["backends"][0]["candidate"]["render"].update(
        {
            "status": "blocked",
            "source_revision": None,
            "artifact_sha256": None,
            "blocker": blocker,
        }
    )


def incomplete_manual_pass(policy):
    manual = policy["backends"][0]["candidate"]["manual_review"]
    manual.update(
        {
            "status": "pass",
            "reviewer": "Qualified accessibility reviewer",
            "evaluated_at": "2026-08-20",
        }
    )


def main():
    base = json.loads(SOURCE.read_text(encoding="utf-8"))
    cases = [
        ("current-policy", base, 0, None),
        (
            "missing-criterion",
            changed(base, lambda policy: policy["criteria"].pop()),
            1,
            "complete review set",
        ),
        (
            "wrong-backend-profile",
            changed(
                base,
                lambda policy: policy["backends"][0].update(
                    {"profile": "book/_quarto.yml"}
                ),
            ),
            1,
            "wrong standard",
        ),
        (
            "blocked-without-reason",
            changed(
                base,
                lambda policy: block_candidate(policy, None),
            ),
            1,
            "substantive blocker",
        ),
        (
            "automation-before-render",
            changed(
                base,
                lambda policy: block_candidate(
                    policy,
                    "A deliberately blocked fixture has no renderable candidate artifact.",
                ),
            ),
            1,
            "did not render",
        ),
        (
            "incomplete-manual-pass",
            changed(base, incomplete_manual_pass),
            1,
            "cover every criterion",
        ),
        (
            "tagged-without-verapdf-failure",
            changed(
                base,
                lambda policy: policy["backends"][0]["ordinary_pdf_observation"][
                    "automated_validation"
                ].update({"status": "pass"}),
            ),
            1,
            "retain its failed veraPDF result",
        ),
        (
            "claim-before-gates",
            changed(base, claim_while_blocked),
            1,
            "before every gate passes",
        ),
    ]
    for name, policy, expected, message in cases:
        run_case(name, policy, expected, message)
    print(f"ok: PDF accessibility policy fixtures ({len(cases)} cases)")


if __name__ == "__main__":
    main()
