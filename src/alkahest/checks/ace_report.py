"""Turn the pinned Ace JSON report into a concise pass/fail gate."""

import os
import sys
import tempfile
from pathlib import Path
from typing import Never

from alkahest.common import DataValue, load_json

EXPECTED_ACE_VERSION = "1.4.6"


def fail(message: str) -> Never:
    """Raise one Ace report contract error."""
    raise RuntimeError(f"error: {message}")


def mapping(value: DataValue | None) -> dict[str, DataValue]:
    """Return a structured mapping or an empty mapping."""
    return value if isinstance(value, dict) else {}


def values(value: DataValue | None) -> list[DataValue]:
    """Return a structured list or an empty list."""
    return value if isinstance(value, list) else []


def text(value: DataValue | None, default: str) -> str:
    """Return a report string or a fallback label."""
    return value if isinstance(value, str) else default


def validate_report(path: Path) -> int:
    """Validate an Ace report and return its document count."""
    report_value = load_json(path, "Ace report")
    if not isinstance(report_value, dict):
        fail("Ace report must contain a top-level object")

    report = report_value
    asserted_by = mapping(report.get("earl:assertedBy"))
    release = mapping(asserted_by.get("doap:release")).get("doap:revision")
    if release != EXPECTED_ACE_VERSION:
        fail(f"Ace report must come from version {EXPECTED_ACE_VERSION}, found {release}")

    failures: list[tuple[str, str, str]] = []
    document_count = 0
    for document_value in values(report.get("assertions")):
        document = mapping(document_value)
        document_count += 1
        subject = text(mapping(document.get("earl:testSubject")).get("url"), "unknown document")

        for assertion_value in values(document.get("assertions")):
            assertion = mapping(assertion_value)
            result = mapping(assertion.get("earl:result"))
            if result.get("earl:outcome") != "fail":
                continue
            test = mapping(assertion.get("earl:test"))
            failures.append(
                (
                    subject,
                    text(test.get("dct:title"), "unknown rule"),
                    text(result.get("dct:description"), text(test.get("dct:description"), "failed")),
                )
            )

    if failures:
        lines = [f"Ace found {len(failures)} automated accessibility failure(s):"]
        for subject, rule, description in failures[:20]:
            lines.append(f"  {subject}: {rule}: {description}")
        if len(failures) > 20:
            lines.append(f"  ... {len(failures) - 20} additional failure(s)")
        fail("\n".join(lines))

    properties = mapping(report.get("properties"))
    if properties.get("hasMathML") is not True:
        fail("Ace report did not detect the reference book's MathML")
    return document_count


def main() -> None:
    """Validate the selected Ace JSON report."""
    default = Path(tempfile.gettempdir()) / "alkahest-ace" / "report.json"
    report_path = Path(os.environ.get("ALKAHEST_ACE_REPORT", default))

    if len(sys.argv) > 2:
        fail("usage: python -m alkahest.checks.ace_report [REPORT_JSON]")
    if len(sys.argv) == 2:
        report_path = Path(sys.argv[1])

    count = validate_report(report_path)
    print(f"ok: Ace by DAISY {EXPECTED_ACE_VERSION} ({count} document reports; zero automated failures)")


if __name__ == "__main__":
    try:
        main()
    except RuntimeError as error:
        print(error, file=sys.stderr)
        raise SystemExit(1) from None
