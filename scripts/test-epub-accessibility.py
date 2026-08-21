"""Exercise EPUB semantic, page-navigation, and Ace-report failure contracts."""

import copy
import json
import os
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path

from lib.alkahest.epub_accessibility import (
    EpubPolicyError,
    finalize_epub,
    validate_epub,
)


ROOT = Path(__file__).resolve().parent.parent
ACE_REPORT_CHECKER = ROOT / "scripts" / "check-ace-report.py"


def base_policy():
    return {
        "schema_version": 1,
        "standard": "EPUB Accessibility 1.1",
        "language": "en-US",
        "claim_status": "pending-manual-review",
        "discovery": {
            "access_modes": ["textual", "visual"],
            "access_mode_sufficient": ["textual"],
            "accessibility_features": [
                "MathML",
                "alternativeText",
                "readingOrder",
                "structuralNavigation",
                "tableOfContents",
            ],
            "accessibility_hazards": ["none"],
            "accessibility_summary": (
                "This fixture exercises automated EPUB accessibility contracts. "
                "Manual review remains pending, and no accessibility conformance "
                "claim is made."
            ),
        },
        "sections": [
            {
                "id": "sec-main",
                "epub_type": "chapter",
                "role": "doc-chapter",
                "body_type": "bodymatter",
            }
        ],
        "landmarks": [
            {"type": "titlepage", "special": "titlepage", "label": "Title page"},
            {"type": "toc", "special": "toc", "label": "Table of contents"},
            {
                "type": "bodymatter",
                "target_id": "sec-main",
                "label": "Start of main content",
            },
        ],
        "pagination": {
            "mode": "not-applicable",
            "rationale": (
                "This synthetic reflowable fixture is not paired with an identified "
                "static edition, so emitting page locations would falsely imply a "
                "print equivalence that the test does not possess."
            ),
        },
    }


def fixture_members():
    return {
        "mimetype": b"application/epub+zip",
        "META-INF/container.xml": b"""<?xml version="1.0"?>
<container xmlns="urn:oasis:names:tc:opendocument:xmlns:container" version="1.0">
  <rootfiles><rootfile full-path="EPUB/content.opf" media-type="application/oebps-package+xml"/></rootfiles>
</container>
""",
        "EPUB/content.opf": b"""<?xml version="1.0" encoding="UTF-8"?>
<package xmlns="http://www.idpf.org/2007/opf" version="3.0" unique-identifier="id" xml:lang="en-US">
  <metadata xmlns:dc="http://purl.org/dc/elements/1.1/">
    <dc:identifier id="id">urn:uuid:fixture</dc:identifier>
    <dc:title>Accessible fixture</dc:title>
    <dc:language>en-US</dc:language>
    <meta property="dcterms:modified">2026-08-20T00:00:00Z</meta>
  </metadata>
  <manifest>
    <item id="nav" href="nav.xhtml" media-type="application/xhtml+xml" properties="nav"/>
    <item id="title" href="title.xhtml" media-type="application/xhtml+xml"/>
    <item id="chapter" href="chapter.xhtml" media-type="application/xhtml+xml" properties="mathml"/>
  </manifest>
  <spine><itemref idref="title"/><itemref idref="nav"/><itemref idref="chapter"/></spine>
</package>
""",
        "EPUB/nav.xhtml": b"""<?xml version="1.0" encoding="UTF-8"?>
<html xmlns="http://www.w3.org/1999/xhtml" xmlns:epub="http://www.idpf.org/2007/ops" lang="en-US" xml:lang="en-US">
<head><title>Contents</title></head><body epub:type="frontmatter">
<nav epub:type="toc" id="toc"><h1>Contents</h1><ol><li><a href="chapter.xhtml#sec-main">Main</a></li></ol></nav>
</body></html>
""",
        "EPUB/title.xhtml": b"""<?xml version="1.0" encoding="UTF-8"?>
<html xmlns="http://www.w3.org/1999/xhtml" xmlns:epub="http://www.idpf.org/2007/ops" lang="en-US" xml:lang="en-US">
<head><title>Accessible fixture</title></head><body epub:type="frontmatter">
<section epub:type="titlepage"><h1>Accessible fixture</h1></section>
</body></html>
""",
        "EPUB/chapter.xhtml": b"""<?xml version="1.0" encoding="UTF-8"?>
<html xmlns="http://www.w3.org/1999/xhtml" xmlns:epub="http://www.idpf.org/2007/ops" lang="en-US" xml:lang="en-US">
<head><title>Main</title></head><body epub:type="bodymatter">
<section id="sec-main"><h1>Main</h1>
<p><img src="figure.svg" alt="A labeled signal path."/></p>
<section id="sec-data"><h2>Data</h2>
<table><caption>Truth table</caption><thead><tr><th>Input</th><th>Output</th></tr></thead><tbody><tr><td>0</td><td>1</td></tr></tbody></table>
<p><math xmlns="http://www.w3.org/1998/Math/MathML"><semantics><mi>x</mi><annotation encoding="application/x-tex">x</annotation></semantics></math></p>
<p><a href="#sec-data">Return to data</a></p></section></section>
</body></html>
""",
        "EPUB/figure.svg": b"<svg xmlns=\"http://www.w3.org/2000/svg\"></svg>",
    }


def write_epub(path, members):
    with zipfile.ZipFile(path, "w") as archive:
        archive.writestr("mimetype", members["mimetype"], compress_type=zipfile.ZIP_STORED)
        for name, content in members.items():
            if name == "mimetype":
                continue
            archive.writestr(name, content, compress_type=zipfile.ZIP_DEFLATED)


def write_policy(path, policy):
    path.write_text(json.dumps(policy, indent=2) + "\n", encoding="utf-8")


def rewrite_member(epub, member, mutate):
    with zipfile.ZipFile(epub) as archive:
        infos = archive.infolist()
        members = {info.filename: archive.read(info.filename) for info in infos}
    text = members[member].decode("utf-8")
    members[member] = mutate(text).encode("utf-8")
    write_epub(epub, members)


def replace(old, new):
    def mutate(text):
        if old not in text:
            raise RuntimeError(f"fixture mutation cannot find {old!r}")
        return text.replace(old, new, 1)

    return mutate


def expect_failure(epub, policy, name, member, mutation, expected):
    candidate = epub.with_name(f"{name}.epub")
    candidate.write_bytes(epub.read_bytes())
    rewrite_member(candidate, member, mutation)
    try:
        validate_epub(candidate, policy)
    except EpubPolicyError as error:
        if expected not in str(error):
            raise RuntimeError(f"fixture {name} missed {expected!r}: {error}") from error
        return
    raise RuntimeError(f"EPUB accessibility fixture {name} passed unexpectedly")


def ace_report(version="1.4.6", failure=False):
    assertions = []
    if failure:
        assertions = [
            {
                "earl:testSubject": {"url": "EPUB/chapter.xhtml"},
                "assertions": [
                    {
                        "earl:test": {"dct:title": "image-alt"},
                        "earl:result": {
                            "earl:outcome": "fail",
                            "dct:description": "Images must have alternate text",
                        },
                    }
                ],
            }
        ]
    return {
        "earl:assertedBy": {"doap:release": {"doap:revision": version}},
        "properties": {"hasMathML": True},
        "assertions": assertions,
    }


def run_ace_report_fixture(path, should_pass):
    result = subprocess.run(
        [sys.executable, str(ACE_REPORT_CHECKER), str(path)],
        text=True,
        capture_output=True,
        check=False,
    )
    if (result.returncode == 0) != should_pass:
        raise RuntimeError(result.stdout + result.stderr)


def main():
    with tempfile.TemporaryDirectory(prefix="alkahest-epub-accessibility.") as temp:
        root = Path(temp)
        policy_path = root / "policy.json"
        policy = base_policy()
        write_policy(policy_path, policy)
        epub = root / "valid.epub"
        write_epub(epub, fixture_members())
        finalize_epub(epub, policy_path)
        validate_epub(epub, policy_path)

        cases = [
            (
                "metadata",
                "EPUB/content.opf",
                replace('<meta property="schema:accessMode">visual</meta>', ""),
                "schema:accessMode",
            ),
            (
                "language",
                "EPUB/chapter.xhtml",
                replace('lang="en-US"', 'lang="fr-FR"'),
                "declare lang and xml:lang",
            ),
            (
                "landmark",
                "EPUB/nav.xhtml",
                replace('epub:type="bodymatter"', 'epub:type="chapter"'),
                "landmarks do not exactly match",
            ),
            (
                "toc-target",
                "EPUB/nav.xhtml",
                replace("chapter.xhtml#sec-main", "chapter.xhtml#missing"),
                "missing fragment",
            ),
            (
                "heading-outline",
                "EPUB/chapter.xhtml",
                replace("<h2>Data</h2>", "<h3>Data</h3>"),
                "skips a level",
            ),
            (
                "table-header",
                "EPUB/chapter.xhtml",
                lambda text: text.replace("<th>", "<td>").replace("</th>", "</td>"),
                "header cells",
            ),
            (
                "image-alt",
                "EPUB/chapter.xhtml",
                replace(' alt="A labeled signal path."', ""),
                "no alt attribute",
            ),
            (
                "math-annotation",
                "EPUB/chapter.xhtml",
                replace(
                    '<annotation encoding="application/x-tex">x</annotation>', ""
                ),
                "textual source annotation",
            ),
            (
                "link-purpose",
                "EPUB/chapter.xhtml",
                replace(">Return to data</a>", "></a>"),
                "no accessible purpose",
            ),
            (
                "premature-claim",
                "EPUB/content.opf",
                replace(
                    "</metadata>",
                    '<meta property="dcterms:conformsTo">EPUB Accessibility 1.1 - WCAG 2.2 Level AA</meta></metadata>',
                ),
                "must not emit a conformance claim",
            ),
        ]
        for name, member, mutation, expected in cases:
            expect_failure(epub, policy_path, name, member, mutation, expected)

        print_policy = copy.deepcopy(policy)
        print_policy["discovery"]["accessibility_features"].append("pageNavigation")
        print_policy["pagination"] = {
            "mode": "print-equivalent",
            "page_break_source": "urn:isbn:9780000000000",
            "pages": [{"label": "1", "anchor": "sec-data"}],
        }
        print_policy_path = root / "print-policy.json"
        write_policy(print_policy_path, print_policy)
        print_epub = root / "print-equivalent.epub"
        write_epub(print_epub, fixture_members())
        finalize_epub(print_epub, print_policy_path)
        validate_epub(print_epub, print_policy_path)
        expect_failure(
            print_epub,
            print_policy_path,
            "page-list",
            "EPUB/nav.xhtml",
            replace("chapter.xhtml#page-1", "chapter.xhtml#missing-page"),
            "missing marker",
        )

        pass_report = root / "ace-pass.json"
        pass_report.write_text(json.dumps(ace_report()) + "\n", encoding="utf-8")
        run_ace_report_fixture(pass_report, True)
        fail_report = root / "ace-fail.json"
        fail_report.write_text(
            json.dumps(ace_report(failure=True)) + "\n", encoding="utf-8"
        )
        run_ace_report_fixture(fail_report, False)
        drift_report = root / "ace-drift.json"
        drift_report.write_text(
            json.dumps(ace_report(version="latest")) + "\n", encoding="utf-8"
        )
        run_ace_report_fixture(drift_report, False)

    print(
        "ok: EPUB accessibility fixtures "
        "(valid reflowable and print-equivalent packages; "
        "11 semantic/page failures and 2 Ace report failures rejected)"
    )


if __name__ == "__main__":
    try:
        main()
    except (OSError, RuntimeError, EpubPolicyError, zipfile.BadZipFile) as error:
        print(f"error: {error}", file=sys.stderr)
        raise SystemExit(1)
