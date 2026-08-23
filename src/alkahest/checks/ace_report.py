"""Turn the pinned Ace JSON report into a concise pass/fail gate."""

import json
import os
import sys
import tempfile
from pathlib import Path

EXPECTED_ACE_VERSION = "1.4.6"


def fail(message):
    raise RuntimeError(f"error: {message}")


def validate_report(path):
    try:
        report = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        fail(f"cannot read Ace report {path}: {error}")
    release = report.get("earl:assertedBy", {}).get("doap:release", {}).get("doap:revision")
    if release != EXPECTED_ACE_VERSION:
        fail(f"Ace report must come from version {EXPECTED_ACE_VERSION}, found {release}")
    failures = []
    document_count = 0
    for document in report.get("assertions", []):
        document_count += 1
        subject = document.get("earl:testSubject", {}).get("url", "unknown document")
        for assertion in document.get("assertions", []):
            result = assertion.get("earl:result", {})
            if result.get("earl:outcome") != "fail":
                continue
            test = assertion.get("earl:test", {})
            failures.append(
                (
                    subject,
                    test.get("dct:title", "unknown rule"),
                    result.get("dct:description", test.get("dct:description", "failed")),
                )
            )
    if failures:
        lines = [f"Ace found {len(failures)} automated accessibility failure(s):"]
        for subject, rule, description in failures[:20]:
            lines.append(f"  {subject}: {rule}: {description}")
        if len(failures) > 20:
            lines.append(f"  ... {len(failures) - 20} additional failure(s)")
        fail("\n".join(lines))
    properties = report.get("properties", {})
    if properties.get("hasMathML") is not True:
        fail("Ace report did not detect the reference book's MathML")
    return document_count


def main():
    default = Path(tempfile.gettempdir()) / "alkahest-ace" / "report.json"
    report_path = Path(os.environ.get("ALKAHEST_ACE_REPORT", default))
    if len(sys.argv) > 2:
        fail("usage: python -m alkahest.checks.ace_report [REPORT_JSON]")
    if len(sys.argv) == 2:
        report_path = Path(sys.argv[1])
    count = validate_report(report_path)
    print(
        f"ok: Ace by DAISY {EXPECTED_ACE_VERSION} "
        f"({count} document reports; zero automated failures)"
    )


if __name__ == "__main__":
    try:
        main()
    except RuntimeError as error:
        print(error, file=sys.stderr)
        raise SystemExit(1)
