"""Validate and identify manual EPUB reading-system review evidence."""

import hashlib
import json
import re
import zipfile
from datetime import date, datetime
from pathlib import Path, PurePosixPath
from xml.etree import ElementTree as ET


EXPECTED_STANDARD = "EPUB Accessibility 1.1"
EXPECTED_TARGET = "WCAG 2.2 Level AA"
EXPECTED_CONFORMANCE_STRING = f"{EXPECTED_STANDARD} - {EXPECTED_TARGET}"
EXPECTED_CRITERIA = {
    "assistive-technology",
    "code-and-tables",
    "images-and-diagrams",
    "import-and-publication-information",
    "keyboard-and-focus",
    "language-and-pronunciation",
    "links-notes-and-backlinks",
    "mathematics",
    "navigation-and-landmarks",
    "reading-order-and-structure",
}
EXPECTED_LOCATIONS = {
    "backmatter",
    "code",
    "core-structure",
    "figures-and-diagrams",
    "frontmatter-and-navigation",
    "generated-navigation",
    "language-and-script",
    "mathematics",
    "tables-and-components",
}
EXPECTED_SCALES = {"default": 100, "enlarged": 150, "extra-large": 200}
RESULT_STATUSES = {"pending", "pass", "fail"}


class EpubReviewError(RuntimeError):
    """Report an invalid reading-system review contract."""


def fail(message):
    raise EpubReviewError(f"error: {message}")


def load_json(path, label):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError) as error:
        fail(f"cannot read {label} '{path}': {error}")
    except json.JSONDecodeError as error:
        fail(f"invalid {label} JSON in {path}: {error}")


def root_path(root, relative, label):
    if not isinstance(relative, str) or not relative:
        fail(f"{label} must be a nonempty repository-relative path")
    value = PurePosixPath(relative)
    if value.is_absolute() or ".." in value.parts or str(value) != relative:
        fail(f"{label} must be a normalized repository-relative path")
    return root / Path(*value.parts)


def canonical_epub_sha256(path):
    """Hash EPUB names and content while ignoring generated package dates."""
    digest = hashlib.sha256()
    try:
        with zipfile.ZipFile(path) as archive:
            names = [name for name in archive.namelist() if not name.endswith("/")]
            if len(names) != len(set(names)):
                fail("review EPUB contains duplicate ZIP member names")
            for name in sorted(names):
                content = archive.read(name)
                if name.endswith(".opf"):
                    text = content.decode("utf-8")
                    text = re.sub(
                        r"(<dc:date\b(?=[^>]*\bid=[\"']epub-date[\"'])[^>]*>)[^<]*(</dc:date>)",
                        r"\g<1>GENERATED-DATE\g<2>",
                        text,
                    )
                    text = re.sub(
                        r"(<meta\b(?=[^>]*\bproperty=[\"']dcterms:modified[\"'])"
                        r"[^>]*>)[^<]*(</meta>)",
                        r"\g<1>GENERATED-DATE\g<2>",
                        text,
                    )
                    content = text.encode("utf-8")
                encoded_name = name.encode("utf-8")
                digest.update(len(encoded_name).to_bytes(8, "big"))
                digest.update(encoded_name)
                digest.update(len(content).to_bytes(8, "big"))
                digest.update(content)
    except (OSError, UnicodeError, zipfile.BadZipFile) as error:
        fail(f"cannot identify review EPUB '{path}': {error}")
    return digest.hexdigest()


def epub_ids(path):
    identifiers = set()
    try:
        with zipfile.ZipFile(path) as archive:
            for name in archive.namelist():
                if not name.endswith((".xhtml", ".html")):
                    continue
                root = ET.fromstring(archive.read(name))
                identifiers.update(
                    identifier
                    for element in root.iter()
                    if (identifier := element.get("id"))
                )
    except (ET.ParseError, OSError, zipfile.BadZipFile) as error:
        fail(f"cannot inspect review EPUB '{path}': {error}")
    return identifiers


def unique_items(items, key, label):
    if not isinstance(items, list):
        fail(f"{label} must be an array")
    indexed = {}
    for item in items:
        if not isinstance(item, dict):
            fail(f"{label} entries must be objects")
        value = item.get(key)
        if not isinstance(value, str) or not value:
            fail(f"{label} entries need a nonempty {key}")
        if value in indexed:
            fail(f"{label} contains duplicate {key} '{value}'")
        indexed[value] = item
    return indexed


def substantive(value, minimum=20):
    return isinstance(value, str) and len(value.strip()) >= minimum


def iso_date(value, label):
    try:
        date.fromisoformat(value)
    except (TypeError, ValueError):
        fail(f"{label} must be an ISO date")


def iso_datetime(value, label):
    try:
        datetime.fromisoformat(value.replace("Z", "+00:00"))
    except (AttributeError, TypeError, ValueError):
        fail(f"{label} must be an ISO date-time")


def validate_scales(review):
    scales = unique_items(review.get("text_scales"), "id", "review text scales")
    if set(scales) != set(EXPECTED_SCALES):
        fail("review text scales must include default, enlarged, and extra-large")
    for scale_id, minimum in EXPECTED_SCALES.items():
        scale = scales[scale_id]
        if scale.get("minimum_percent") != minimum:
            fail(f"review text scale '{scale_id}' must require {minimum} percent")
        if not substantive(scale.get("instruction"), 30):
            fail(f"review text scale '{scale_id}' needs a substantive instruction")
    return scales


def validate_criteria(review):
    criteria = unique_items(review.get("criteria"), "id", "review criteria")
    if set(criteria) != EXPECTED_CRITERIA:
        fail("review criteria must match the complete EPUB manual test set")
    for criterion_id, criterion in criteria.items():
        if not substantive(criterion.get("instruction"), 50):
            fail(f"review criterion '{criterion_id}' needs a substantive instruction")
    return criteria


def validate_locations(review, artifact_path):
    locations = unique_items(
        review.get("representative_locations"), "id", "representative locations"
    )
    if set(locations) != EXPECTED_LOCATIONS:
        fail("review must retain the complete representative-location set")
    identifiers = epub_ids(artifact_path)
    targets = set()
    for location_id, location in locations.items():
        target = location.get("target_id")
        if not isinstance(target, str) or not target:
            fail(f"representative location '{location_id}' needs a target_id")
        if target in targets:
            fail(f"representative target '{target}' is duplicated")
        targets.add(target)
        if target not in identifiers:
            fail(f"representative target '{target}' does not resolve in the EPUB")
        if not substantive(location.get("purpose"), 30):
            fail(f"representative location '{location_id}' needs a purpose")
    return locations


def validate_result_entries(system_id, system, criteria, scales):
    results = unique_items(
        system.get("results"), "criterion", f"reading system '{system_id}' results"
    )
    if set(results) != set(criteria):
        fail(f"reading system '{system_id}' must cover every manual criterion")
    scale_results = unique_items(
        system.get("scale_results"),
        "scale",
        f"reading system '{system_id}' scale results",
    )
    if set(scale_results) != set(scales):
        fail(f"reading system '{system_id}' must cover every text scale")

    statuses = []
    for criterion_id, result in results.items():
        status = result.get("status")
        if status not in RESULT_STATUSES:
            fail(f"reading system '{system_id}' criterion '{criterion_id}' has invalid status")
        statuses.append(status)
        evidence = result.get("evidence")
        if status == "pending" and evidence is not None:
            fail(f"pending criterion '{system_id}/{criterion_id}' must not carry evidence")
        if status != "pending" and not substantive(evidence):
            fail(f"completed criterion '{system_id}/{criterion_id}' needs evidence")

    for scale_id, result in scale_results.items():
        status = result.get("status")
        if status not in RESULT_STATUSES:
            fail(f"reading system '{system_id}' scale '{scale_id}' has invalid status")
        statuses.append(status)
        evidence = result.get("evidence")
        actual = result.get("actual_percent")
        if status == "pending":
            if evidence is not None or actual is not None:
                fail(f"pending scale '{system_id}/{scale_id}' must not carry evidence")
            continue
        if not substantive(evidence):
            fail(f"completed scale '{system_id}/{scale_id}' needs evidence")
        if not isinstance(actual, int) or isinstance(actual, bool):
            fail(f"completed scale '{system_id}/{scale_id}' needs actual_percent")
        minimum = scales[scale_id]["minimum_percent"]
        if actual < minimum:
            fail(f"completed scale '{system_id}/{scale_id}' is below {minimum} percent")
    return statuses


def validate_environment(system_id, system):
    environment = system.get("environment")
    if not isinstance(environment, dict):
        fail(f"completed reading system '{system_id}' needs an environment")
    for field in (
        "reader_version",
        "engine_version",
        "os_version",
        "assistive_technology",
        "tester",
    ):
        if not substantive(environment.get(field), 2):
            fail(f"completed reading system '{system_id}' needs environment {field}")
    if environment["reader_version"] != system["planned_version"]:
        fail(f"reading system '{system_id}' tested version must match planned_version")
    iso_date(environment.get("tested_at"), f"reading system '{system_id}' tested_at")


def validate_artifact(review, root, artifact_override, completed):
    artifact = review.get("artifact")
    if not isinstance(artifact, dict):
        fail("EPUB review needs artifact metadata")
    artifact_path = (
        Path(artifact_override)
        if artifact_override is not None
        else root_path(root, artifact.get("path"), "review artifact path")
    )
    if not artifact_path.is_file():
        fail(f"review artifact is missing: {artifact_path}")
    revision = artifact.get("source_revision")
    content_digest = artifact.get("content_sha256")
    prepared_at = artifact.get("prepared_at")
    populated = any(value is not None for value in (revision, content_digest, prepared_at))
    if populated and not all(
        value is not None for value in (revision, content_digest, prepared_at)
    ):
        fail("review artifact identity must be entirely populated or entirely empty")
    if populated or completed:
        if not re.fullmatch(r"(?:[0-9a-f]{40}|[0-9a-f]{64})", revision or ""):
            fail("prepared review needs a full Git source revision")
        if not re.fullmatch(r"[0-9a-f]{64}", content_digest or ""):
            fail("prepared review needs a canonical EPUB content SHA-256")
        iso_datetime(prepared_at, "review artifact prepared_at")
    if content_digest is not None:
        actual = canonical_epub_sha256(artifact_path)
        if actual != content_digest:
            fail("rendered EPUB content does not match the prepared review artifact")
    return artifact_path, populated


def validate_claim(review, policy, statuses, artifact_populated):
    claim = review.get("claim")
    if not isinstance(claim, dict):
        fail("EPUB review needs claim metadata")
    status = claim.get("status")
    if status not in {"pending-manual-review", "reviewed-no-claim", "conformant"}:
        fail("EPUB review claim status is invalid")
    if status != policy.get("claim_status"):
        fail("EPUB review claim status must match the EPUB accessibility policy")
    conformance_claim = claim.get("conformance_claim")
    if not isinstance(conformance_claim, bool):
        fail("EPUB review conformance_claim must be boolean")
    if not substantive(claim.get("summary"), 60):
        fail("EPUB review claim needs a substantive summary")
    conformance_string = claim.get("conformance_string")
    pending = statuses.count("pending")
    failed = statuses.count("fail")
    if status == "pending-manual-review":
        if conformance_claim:
            fail("a pending manual review cannot make a conformance claim")
        if pending == 0:
            fail("pending-manual-review status requires pending evidence")
        if claim.get("evaluator") is not None or claim.get("evaluated_at") is not None:
            fail("pending manual review must not identify a completed evaluation")
        for field in ("conformance_string", "evaluator_credential", "report_location"):
            if claim.get(field) is not None:
                fail(f"pending manual review must not declare {field}")
    else:
        if pending:
            fail("a completed EPUB review cannot contain pending evidence")
        if not artifact_populated:
            fail("a completed EPUB review needs prepared artifact identity")
        if not substantive(claim.get("evaluator"), 3):
            fail("a completed EPUB review needs an evaluator")
        iso_date(claim.get("evaluated_at"), "EPUB review evaluated_at")
    if status == "reviewed-no-claim" and conformance_claim:
        fail("reviewed-no-claim status cannot make a conformance claim")
    if status == "reviewed-no-claim" and conformance_string is not None:
        fail("reviewed-no-claim status cannot declare a conformance string")
    if status == "conformant":
        if not conformance_claim:
            fail("conformant status requires an explicit conformance claim")
        if failed or set(statuses) != {"pass"}:
            fail("an EPUB conformance claim requires every manual result to pass")
        if conformance_string != EXPECTED_CONFORMANCE_STRING:
            fail("EPUB conformance string must match the standard and WCAG target")
        for field in ("evaluator_credential", "report_location"):
            value = claim.get(field)
            if value is not None and not substantive(value, 3):
                fail(f"EPUB conformance claim has invalid {field}")
    return pending, failed, conformance_claim


def validate_review(review, policy, root, artifact_override=None):
    if review.get("schema_version") != 1:
        fail("EPUB reading-system review schema_version must be 1")
    if review.get("standard") != EXPECTED_STANDARD:
        fail("EPUB reading-system review must target EPUB Accessibility 1.1")
    if review.get("target") != EXPECTED_TARGET:
        fail("EPUB reading-system review must target WCAG 2.2 Level AA")
    if policy.get("standard") != EXPECTED_STANDARD:
        fail("EPUB accessibility policy and reading-system review standards differ")
    expected_policy = review.get("policy")
    if expected_policy != "book/epub-accessibility.json":
        fail("EPUB review must reference the canonical accessibility policy")

    scales = validate_scales(review)
    criteria = validate_criteria(review)
    systems = unique_items(
        review.get("reading_systems"), "id", "EPUB reading systems"
    )
    if len(systems) < 3:
        fail("EPUB review requires at least three reading systems")
    engine_families = set()
    all_statuses = []
    completed_systems = []
    for system_id, system in systems.items():
        for field in ("name", "planned_version", "engine_family", "platform"):
            if not substantive(system.get(field), 2):
                fail(f"reading system '{system_id}' needs {field}")
        if not re.fullmatch(r"\d+(?:\.\d+){1,3}", system["planned_version"]):
            fail(f"reading system '{system_id}' planned_version is invalid")
        engine = system["engine_family"].casefold()
        if engine in engine_families:
            fail("EPUB reading systems must use distinct engine families")
        engine_families.add(engine)
        source = system.get("release_source", "")
        if not re.fullmatch(r"https://[^\s]+", source):
            fail(f"reading system '{system_id}' needs an HTTPS release source")
        statuses = validate_result_entries(system_id, system, criteria, scales)
        all_statuses.extend(statuses)
        if set(statuses) != {"pending"}:
            completed_systems.append(system_id)
            validate_environment(system_id, system)

    artifact_path, artifact_populated = validate_artifact(
        review, root, artifact_override, bool(completed_systems)
    )
    locations = validate_locations(review, artifact_path)
    pending, failed, claim = validate_claim(
        review, policy, all_statuses, artifact_populated
    )
    return {
        "systems": len(systems),
        "engines": len(engine_families),
        "criteria": len(criteria),
        "locations": len(locations),
        "scales": len(scales),
        "pending": pending,
        "failed": failed,
        "claim": claim,
    }
