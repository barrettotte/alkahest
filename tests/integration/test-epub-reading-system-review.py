"""Exercise valid and invalid EPUB manual-review evidence contracts."""

import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path

from alkahest.epub_review import bind_review_artifact, canonical_epub_sha256

ROOT = Path(__file__).resolve().parent.parent.parent
SOURCE_REVIEW = ROOT / "book" / "epub-reading-system-review.json"
SOURCE_POLICY = ROOT / "book" / "epub-accessibility.json"


def write_json(path, value):
    path.write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8")


def prepare(parent, name):
    case = parent / name
    case.mkdir()
    files = {
        "review": case / "review.json",
        "policy": case / "policy.json",
        "epub": case / "book.epub",
    }
    shutil.copy2(SOURCE_REVIEW, files["review"])
    shutil.copy2(SOURCE_POLICY, files["policy"])
    shutil.copy2(parent / "fixture.epub", files["epub"])
    return files


def write_fixture_epub(path):
    review = json.loads(SOURCE_REVIEW.read_text(encoding="utf-8"))
    identifiers = [location["target_id"] for location in review["representative_locations"]]
    sections = "".join(f'<section id="{identifier}"/>' for identifier in identifiers)
    members = {
        "mimetype": b"application/epub+zip",
        "EPUB/content.opf": b"""<?xml version="1.0" encoding="UTF-8"?>
<package xmlns="http://www.idpf.org/2007/opf"
         xmlns:dc="http://purl.org/dc/elements/1.1/" version="3.0">
  <metadata>
    <dc:date id="epub-date">2026-08-20T12:00:00Z</dc:date>
    <meta property="dcterms:modified">2026-08-20T12:00:00Z</meta>
  </metadata>
</package>
""",
        "EPUB/chapter.xhtml": (
            '<?xml version="1.0" encoding="UTF-8"?>'
            '<html xmlns="http://www.w3.org/1999/xhtml"><body>' + sections + "</body></html>"
        ).encode("utf-8"),
    }
    with zipfile.ZipFile(path, "w") as archive:
        for name, content in members.items():
            compression = zipfile.ZIP_STORED if name == "mimetype" else zipfile.ZIP_DEFLATED
            archive.writestr(name, content, compress_type=compression)


def run(files):
    environment = os.environ.copy()
    environment.update(
        ALKAHEST_EPUB_REVIEW=str(files["review"]),
        ALKAHEST_EPUB_ACCESSIBILITY_POLICY=str(files["policy"]),
        ALKAHEST_EPUB_REVIEW_ARTIFACT=str(files["epub"]),
    )
    return subprocess.run(
        [sys.executable, "-m", "alkahest.operations", "check-epub-review"],
        env=environment,
        text=True,
        capture_output=True,
        check=False,
    )


def edit_json(files, key, mutate):
    value = json.loads(files[key].read_text(encoding="utf-8"))
    mutate(value)
    write_json(files[key], value)


def expect_failure(parent, name, expected, mutation):
    files = prepare(parent, name)
    mutation(files)
    result = run(files)
    output = result.stdout + result.stderr
    if result.returncode == 0:
        raise RuntimeError(f"error: EPUB manual-review fixture {name} passed")
    if expected not in output:
        raise RuntimeError(f"error: fixture {name} missed {expected!r}:\n{output}")


def mutate_review(change):
    return lambda files: edit_json(files, "review", change)


def completed_environment(system):
    system["environment"].update(
        reader_version=system["planned_version"],
        engine_version="documented engine 1.0",
        os_version="Fixture Linux 1",
        assistive_technology="Fixture Reader 1",
        tester="Fixture evaluator",
        tested_at="2026-08-20",
    )


def prepared_artifact(review, epub):
    review["artifact"].update(
        source_revision="a" * 40,
        content_sha256=canonical_epub_sha256(epub),
        prepared_at="2026-08-20T12:00:00Z",
    )


def complete_one(files):
    review = json.loads(files["review"].read_text(encoding="utf-8"))
    system = review["reading_systems"][0]
    system["results"][0].update(
        status="pass",
        evidence="The publication opened with correct title and language metadata.",
    )
    completed_environment(system)
    prepared_artifact(review, files["epub"])
    write_json(files["review"], review)


def complete_all(files, result_status="pass"):
    review = json.loads(files["review"].read_text(encoding="utf-8"))
    policy = json.loads(files["policy"].read_text(encoding="utf-8"))
    for system in review["reading_systems"]:
        completed_environment(system)
        for result in system["results"]:
            result.update(
                status=result_status,
                evidence="Fixture evidence records the observed result for this criterion.",
            )
        for result in system["scale_results"]:
            minimum = next(
                scale["minimum_percent"]
                for scale in review["text_scales"]
                if scale["id"] == result["scale"]
            )
            result.update(
                status=result_status,
                actual_percent=minimum,
                evidence="Fixture evidence records readable reflow at this text size.",
            )
    prepared_artifact(review, files["epub"])
    review["claim"].update(
        status="conformant",
        conformance_claim=True,
        conformance_string="EPUB Accessibility 1.1 - WCAG 2.2 Level AA",
        evaluator="Fixture evaluator",
        evaluator_credential="Fixture accessibility qualification",
        evaluated_at="2026-08-20",
        report_location="https://example.invalid/accessibility-report",
        summary=(
            "Fixture evaluation completed every reading-system and manual "
            "accessibility result against the prepared EPUB artifact."
        ),
    )
    policy["claim_status"] = "conformant"
    write_json(files["review"], review)
    write_json(files["policy"], policy)


def rebuild_epub_with_new_dates(path):
    with zipfile.ZipFile(path) as archive:
        members = [(info.filename, archive.read(info.filename)) for info in archive.infolist()]
    with zipfile.ZipFile(path, "w") as archive:
        for name, content in members:
            if name.endswith("content.opf"):
                text = content.decode("utf-8")
                text = re.sub(
                    r"(<dc:date\b(?=[^>]*\bid=[\"']epub-date[\"'])[^>]*>)[^<]*(</dc:date>)",
                    r"\g<1>2099-12-31T23:59:59Z\g<2>",
                    text,
                )
                text = re.sub(
                    r"(<meta\b(?=[^>]*\bproperty=[\"']dcterms:modified[\"'])[^>]*>)[^<]*(</meta>)",
                    r"\g<1>2099-12-31T23:59:59Z\g<2>",
                    text,
                )
                content = text.encode("utf-8")
            compression = zipfile.ZIP_STORED if name == "mimetype" else zipfile.ZIP_DEFLATED
            archive.writestr(name, content, compress_type=compression)


def main():
    with tempfile.TemporaryDirectory(prefix="alkahest-epub-review.") as temp:
        parent = Path(temp)
        write_fixture_epub(parent / "fixture.epub")
        valid = prepare(parent, "valid-pending")
        result = run(valid)
        if result.returncode:
            raise RuntimeError(result.stdout + result.stderr)

        binding = prepare(parent, "valid-artifact-binding")
        edit_json(
            binding,
            "review",
            lambda value: value["artifact"].update(path="book.epub"),
        )
        artifact = bind_review_artifact(
            binding["review"].parent,
            binding["review"],
            "b" * 40,
            "2026-08-20T12:00:00Z",
        )
        if artifact["content_sha256"] != canonical_epub_sha256(binding["epub"]):
            raise RuntimeError("error: EPUB review binding recorded the wrong artifact")
        result = run(binding)
        if result.returncode:
            raise RuntimeError(result.stdout + result.stderr)

        partial = prepare(parent, "valid-partial")
        complete_one(partial)
        result = run(partial)
        if result.returncode:
            raise RuntimeError(result.stdout + result.stderr)

        conformant = prepare(parent, "valid-conformant")
        complete_all(conformant)
        result = run(conformant)
        if result.returncode:
            raise RuntimeError(result.stdout + result.stderr)

        dated = prepare(parent, "canonical-date")
        before = canonical_epub_sha256(dated["epub"])
        rebuild_epub_with_new_dates(dated["epub"])
        if canonical_epub_sha256(dated["epub"]) != before:
            raise RuntimeError("error: generated EPUB dates changed the canonical digest")

        expect_failure(
            parent,
            "schema-drift",
            "schema_version must be 1",
            mutate_review(lambda value: value.update(schema_version=2)),
        )
        expect_failure(
            parent,
            "too-few-readers",
            "at least three reading systems",
            mutate_review(lambda value: value["reading_systems"].pop()),
        )
        expect_failure(
            parent,
            "duplicate-engine",
            "distinct engine families",
            mutate_review(
                lambda value: value["reading_systems"][1].update(
                    engine_family=value["reading_systems"][0]["engine_family"]
                )
            ),
        )
        expect_failure(
            parent,
            "missing-criterion",
            "complete EPUB manual test set",
            mutate_review(lambda value: value["criteria"].pop()),
        )
        expect_failure(
            parent,
            "reader-criterion-gap",
            "cover every manual criterion",
            mutate_review(lambda value: value["reading_systems"][0]["results"].pop()),
        )
        expect_failure(
            parent,
            "reader-scale-gap",
            "cover every text scale",
            mutate_review(lambda value: value["reading_systems"][0]["scale_results"].pop()),
        )
        expect_failure(
            parent,
            "stale-location",
            "does not resolve in the EPUB",
            mutate_review(
                lambda value: value["representative_locations"][0].update(
                    target_id="missing-review-target"
                )
            ),
        )
        expect_failure(
            parent,
            "invalid-status",
            "has invalid status",
            mutate_review(
                lambda value: value["reading_systems"][0]["results"][0].update(status="skipped")
            ),
        )
        expect_failure(
            parent,
            "pending-evidence",
            "must not carry evidence",
            mutate_review(
                lambda value: value["reading_systems"][0]["results"][0].update(
                    evidence="An observation without a completed result is ambiguous."
                )
            ),
        )
        expect_failure(
            parent,
            "completed-without-evidence",
            "needs evidence",
            mutate_review(
                lambda value: value["reading_systems"][0]["results"][0].update(status="pass")
            ),
        )
        expect_failure(
            parent,
            "scale-below-threshold",
            "is below 150 percent",
            mutate_review(
                lambda value: value["reading_systems"][0]["scale_results"][1].update(
                    status="pass",
                    actual_percent=125,
                    evidence="The fixture records an insufficient enlarged text setting.",
                )
            ),
        )
        expect_failure(
            parent,
            "missing-environment",
            "needs environment reader_version",
            lambda files: edit_json(
                files,
                "review",
                lambda value: value["reading_systems"][0]["results"][0].update(
                    status="pass",
                    evidence="The fixture has evidence but no reproducible environment.",
                ),
            ),
        )
        expect_failure(
            parent,
            "partial-artifact",
            "identity must be entirely populated",
            mutate_review(lambda value: value["artifact"].update(source_revision="a" * 40)),
        )

        def stale_digest(files):
            complete_one(files)
            edit_json(
                files,
                "review",
                lambda value: value["artifact"].update(content_sha256="0" * 64),
            )

        expect_failure(
            parent,
            "stale-digest",
            "does not match the prepared review artifact",
            stale_digest,
        )
        expect_failure(
            parent,
            "premature-claim",
            "pending manual review cannot make a conformance claim",
            mutate_review(lambda value: value["claim"].update(conformance_claim=True)),
        )
        expect_failure(
            parent,
            "claim-policy-drift",
            "must match the EPUB accessibility policy",
            mutate_review(lambda value: value["claim"].update(status="reviewed-no-claim")),
        )

        def failed_claim(files):
            complete_all(files, result_status="fail")

        expect_failure(
            parent,
            "failed-conformance",
            "requires every manual result to pass",
            failed_claim,
        )

    print(
        "ok: EPUB manual-review fixtures "
        "(pending, bound, partial, and conformant ledgers; timestamp-stable digest; "
        "17 invalid evidence and claim contracts rejected)"
    )


if __name__ == "__main__":
    try:
        main()
    except (OSError, RuntimeError, zipfile.BadZipFile) as error:
        print(error, file=sys.stderr)
        raise SystemExit(1)
