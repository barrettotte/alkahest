"""Validate PDF/UA evaluation evidence and prevent premature conformance claims."""

import argparse
import json
import re
import sys
from datetime import date
from pathlib import Path, PurePosixPath

ROOT = Path(__file__).resolve().parents[3]
EXPECTED_CRITERIA = {
    "tags-and-reading-order",
    "headings",
    "lists",
    "tables",
    "mathematics",
    "figures",
    "links",
    "document-language",
    "bookmarks",
    "form-free-navigation",
    "metadata-and-claim",
}
EXPECTED_BACKENDS = {
    "typst": ("PDF/UA-1", "ua1", "book/_quarto-pdf-ua-typst.yml"),
    "lualatex": ("PDF/UA-2", "ua2", "book/_quarto-pdf-ua-latex.yml"),
}
EXPECTED_IMAGE = "localhost/alkahest-publishing:quarto-1.10.18-v20"
SHA256 = re.compile(r"[0-9a-f]{64}")
REVISION = re.compile(r"[0-9a-f]{40}")


class PolicyError(RuntimeError):
    """Report an invalid PDF accessibility policy."""


def fail(message):
    raise PolicyError(f"error: {message}")


def substantive(value, minimum=20):
    return isinstance(value, str) and len(value.strip()) >= minimum


def indexed(items, key, label):
    if not isinstance(items, list):
        fail(f"{label} must be an array")
    result = {}
    for item in items:
        if not isinstance(item, dict) or not isinstance(item.get(key), str):
            fail(f"{label} entries need a string {key}")
        value = item[key]
        if value in result:
            fail(f"{label} contains duplicate {key} '{value}'")
        result[value] = item
    return result


def repo_path(value, label):
    if not isinstance(value, str) or not value:
        fail(f"{label} must be a repository-relative path")
    path = PurePosixPath(value)
    if path.is_absolute() or ".." in path.parts or str(path) != value:
        fail(f"{label} must be a normalized repository-relative path")
    return ROOT / Path(*path.parts)


def validate_candidate(backend_id, candidate, criteria):
    if not isinstance(candidate, dict):
        fail(f"backend '{backend_id}' needs candidate evidence")
    render = candidate.get("render")
    if not isinstance(render, dict) or render.get("status") not in {
        "blocked",
        "rendered-unbound",
        "pass",
    }:
        fail(f"backend '{backend_id}' render status must be blocked, rendered-unbound, or pass")
    if render["status"] == "blocked":
        if not substantive(render.get("blocker"), 40):
            fail(f"blocked backend '{backend_id}' needs a substantive blocker")
        if render.get("source_revision") is not None or render.get("artifact_sha256") is not None:
            fail(f"blocked backend '{backend_id}' must not identify a nonexistent candidate")
    elif render["status"] == "rendered-unbound":
        if render.get("source_revision") is not None:
            fail(f"unbound backend '{backend_id}' must not claim a source revision")
        if not SHA256.fullmatch(str(render.get("artifact_sha256", ""))):
            fail(f"unbound backend '{backend_id}' needs an artifact digest")
        if not substantive(render.get("note"), 40):
            fail(f"unbound backend '{backend_id}' needs a render note")
    else:
        if not REVISION.fullmatch(str(render.get("source_revision", ""))):
            fail(f"passing backend '{backend_id}' needs a source revision")
        if not SHA256.fullmatch(str(render.get("artifact_sha256", ""))):
            fail(f"passing backend '{backend_id}' needs an artifact digest")

    automated = candidate.get("automated_validation")
    if not isinstance(automated, dict) or automated.get("status") not in {
        "not-run",
        "fail",
        "pass",
    }:
        fail(f"backend '{backend_id}' has an invalid automated-validation status")
    if render["status"] == "blocked" and automated["status"] != "not-run":
        fail(f"backend '{backend_id}' cannot validate a candidate that did not render")
    failed_rules = automated.get("failed_rules")
    if not isinstance(failed_rules, list) or not all(
        isinstance(rule, str) and rule for rule in failed_rules
    ):
        fail(f"backend '{backend_id}' failed_rules must be an array of rule IDs")
    if automated["status"] == "fail" and not failed_rules:
        fail(f"failed backend '{backend_id}' automated validation needs rule evidence")
    if automated["status"] == "fail":
        if automated.get("failed_rule_count") != len(failed_rules):
            fail(f"failed backend '{backend_id}' rule count disagrees with evidence")
        if not isinstance(automated.get("failed_check_count"), int):
            fail(f"failed backend '{backend_id}' needs a failed-check count")
        if not substantive(automated.get("summary"), 60):
            fail(f"failed backend '{backend_id}' needs a substantive summary")
    if automated["status"] == "pass" and failed_rules:
        fail(f"passing backend '{backend_id}' automated validation has failed rules")

    manual = candidate.get("manual_review")
    if not isinstance(manual, dict) or manual.get("status") not in {"pending", "fail", "pass"}:
        fail(f"backend '{backend_id}' has an invalid manual-review status")
    results = manual.get("results")
    if not isinstance(results, list):
        fail(f"backend '{backend_id}' manual results must be an array")
    if manual["status"] == "pending":
        if results or manual.get("reviewer") is not None or manual.get("evaluated_at") is not None:
            fail(f"pending backend '{backend_id}' manual review must be empty")
    else:
        if not substantive(manual.get("reviewer")) or not isinstance(
            manual.get("evaluated_at"), str
        ):
            fail(f"completed backend '{backend_id}' manual review needs evaluator evidence")
        by_criterion = indexed(results, "criterion", f"backend '{backend_id}' manual results")
        if set(by_criterion) != criteria:
            fail(f"backend '{backend_id}' manual review must cover every criterion")
        statuses = {item.get("status") for item in by_criterion.values()}
        if not statuses <= {"pass", "fail"}:
            fail(f"backend '{backend_id}' completed manual results must pass or fail")
        if any(not substantive(item.get("evidence")) for item in by_criterion.values()):
            fail(f"backend '{backend_id}' completed manual results need evidence")
        expected = "pass" if statuses == {"pass"} else "fail"
        if manual["status"] != expected:
            fail(f"backend '{backend_id}' manual summary disagrees with its results")


def validate_observation(backend_id, observation):
    if not isinstance(observation, dict):
        fail(f"backend '{backend_id}' needs an ordinary-PDF observation")
    repo_path(observation.get("artifact"), f"backend '{backend_id}' ordinary artifact")
    if not isinstance(observation.get("tagged"), bool):
        fail(f"backend '{backend_id}' tagged observation must be boolean")
    if not isinstance(observation.get("pages"), int) or observation["pages"] < 1:
        fail(f"backend '{backend_id}' page count must be positive")
    automated = observation.get("automated_validation")
    if not isinstance(automated, dict) or automated.get("status") != "fail":
        fail(f"ordinary backend '{backend_id}' must retain its failed veraPDF result")
    rules = automated.get("failed_rules")
    if (
        not isinstance(rules, list)
        or not rules
        or len(rules) != automated.get("failed_rule_count_observed")
    ):
        fail(f"ordinary backend '{backend_id}' failed-rule evidence is inconsistent")
    if not all(isinstance(rule, str) and rule for rule in rules):
        fail(f"ordinary backend '{backend_id}' failed rules need IDs")
    checks = automated.get("failed_check_count_observed")
    limit = automated.get("check_limit")
    if (
        not isinstance(checks, int)
        or not isinstance(limit, int)
        or checks < 1
        or limit < 1
        or checks > limit
    ):
        fail(f"ordinary backend '{backend_id}' failed-check evidence is invalid")
    if not substantive(observation.get("summary"), 60):
        fail(f"ordinary backend '{backend_id}' needs a substantive finding")


def validate(policy):
    if not isinstance(policy, dict) or policy.get("schema_version") != 1:
        fail("PDF accessibility policy must use schema_version 1")
    if policy.get("toolchain_image") != EXPECTED_IMAGE:
        fail("PDF accessibility evidence must name the current locked image")
    try:
        date.fromisoformat(policy.get("evaluated_at"))
    except (TypeError, ValueError):
        fail("PDF accessibility evaluated_at must be an ISO date")
    verifier = policy.get("verifier")
    if (
        not isinstance(verifier, dict)
        or verifier.get("name") != "veraPDF"
        or verifier.get("version") != "1.30.2"
    ):
        fail("PDF accessibility policy must pin veraPDF 1.30.2")
    if not substantive(verifier.get("limitation"), 80):
        fail("veraPDF limitations must be explicit")

    criteria = indexed(policy.get("criteria"), "id", "PDF accessibility criteria")
    if set(criteria) != EXPECTED_CRITERIA:
        fail("PDF accessibility criteria must cover the complete review set")
    if any(item.get("method") != "automated-and-manual" for item in criteria.values()):
        fail("every PDF accessibility criterion must require automation and human review")

    backends = indexed(policy.get("backends"), "id", "PDF backends")
    if set(backends) != set(EXPECTED_BACKENDS):
        fail("PDF accessibility evidence must cover Typst and LuaLaTeX")
    for backend_id, backend in backends.items():
        standard, flavour, profile = EXPECTED_BACKENDS[backend_id]
        configured = (
            backend.get("target_standard"),
            backend.get("verapdf_flavour"),
            backend.get("profile"),
        )
        if configured != (standard, flavour, profile):
            fail(f"backend '{backend_id}' has the wrong standard, veraPDF flavour, or profile")
        if not repo_path(profile, f"backend '{backend_id}' profile").is_file():
            fail(f"backend '{backend_id}' profile does not exist")
        repo_path(backend.get("candidate_artifact"), f"backend '{backend_id}' candidate artifact")
        validate_candidate(backend_id, backend.get("candidate"), set(criteria))
        validate_observation(backend_id, backend.get("ordinary_pdf_observation"))

    claim = policy.get("claim")
    if not isinstance(claim, dict) or not isinstance(claim.get("conformance_claim"), bool):
        fail("PDF accessibility claim state is missing")
    targets = claim.get("target_backends")
    if (
        not isinstance(targets, list)
        or len(targets) != len(set(targets))
        or not set(targets) <= set(backends)
    ):
        fail("PDF accessibility claim targets must be unique known backends")
    if not substantive(claim.get("summary"), 60):
        fail("PDF accessibility claim needs a substantive summary")
    if not claim["conformance_claim"]:
        if claim.get("status") not in {"blocked", "pending-manual-review"}:
            fail("a no-claim PDF accessibility state must be blocked or pending review")
        if (
            targets
            or claim.get("conformance_string") is not None
            or claim.get("report_location") is not None
        ):
            fail("a no-claim PDF accessibility state must not publish claim metadata")
    else:
        if claim.get("status") != "conformant" or not targets:
            fail("a conformance claim needs conformant status and target backends")
        if not substantive(claim.get("conformance_string")) or not substantive(
            claim.get("report_location")
        ):
            fail("a conformance claim needs a string and report location")
        for backend_id in targets:
            candidate = backends[backend_id]["candidate"]
            gates = (
                candidate["render"]["status"],
                candidate["automated_validation"]["status"],
                candidate["manual_review"]["status"],
            )
            if gates != ("pass", "pass", "pass"):
                fail(f"backend '{backend_id}' cannot be claimed before every gate passes")
    return {
        "backends": len(backends),
        "criteria": len(criteria),
        "claim": claim["conformance_claim"],
    }


def main():
    parser = argparse.ArgumentParser(description="Validate PDF accessibility evaluation evidence.")
    parser.add_argument(
        "policy",
        nargs="?",
        type=Path,
        default=ROOT / "book" / "pdf-accessibility.json",
    )
    arguments = parser.parse_args()
    try:
        policy = json.loads(arguments.policy.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        fail(f"cannot read PDF accessibility policy: {error}")
    result = validate(policy)
    print(
        "ok: PDF accessibility evidence "
        f"({result['backends']} backends; {result['criteria']} automated/manual "
        f"criteria; conformance claim: {'yes' if result['claim'] else 'no'})"
    )


if __name__ == "__main__":
    try:
        main()
    except PolicyError as error:
        print(error, file=sys.stderr)
        raise SystemExit(1) from None
