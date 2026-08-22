"""Exercise preview artifact selection, privacy, metadata, and format failures."""

import copy
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR / "lib"))

from alkahest.common import ContractError
from alkahest.preview_artifacts import (
    LINKS_PENDING,
    PREVIEW_DESCRIPTION,
    PREVIEW_UUID,
    validate_preview_artifacts,
)


def valid_snapshot():
    selected = [
        {"source_id": "preface", "path": "index.qmd", "title": "Preface", "identifier": "sec-preface", "private": False},
        {"source_id": "reference", "path": "reference.qmd", "title": "Core feature specimen", "identifier": "sec-core-feature-specimen", "private": False},
    ]
    omitted = [
        {"source_id": "math", "path": "math.qmd", "title": "Mathematical notation", "identifier": "sec-math-system", "private": False},
        {"source_id": "private-notes", "path": "private/notes.qmd", "title": "Private notes", "identifier": "sec-private-notes", "private": True},
    ]
    html = " ".join(
        (
            PREVIEW_DESCRIPTION,
            "sec-preface sec-core-feature-specimen alkahest-preview-notice",
            "alkahest-preview-watermark",
            'data-full-edition-link="unassigned" data-purchase-link="unassigned"',
            LINKS_PENDING,
            "Preview chapters Preview reference",
            'role="doc-biblioref" ref-turing1936 ref-knuth1984',
            'href="appendices/page-system-checklist.html#sec-appendix-numbering"',
            'href="../reference.html#sec-heading-hierarchy"',
            'href="../reference.html#eq-ohms-law"',
        )
    )
    epub = " ".join(
        (
            PREVIEW_UUID,
            PREVIEW_DESCRIPTION,
            "sec-preface sec-core-feature-specimen alkahest-preview-notice",
            "alkahest-preview-watermark",
            LINKS_PENDING,
            "ref-turing1936 ref-knuth1984",
            'href="ch007.xhtml#sec-appendix-numbering"',
            'href="ch002.xhtml#sec-heading-hierarchy"',
            'href="ch002.xhtml#eq-ohms-law"',
        )
    )
    return {
        "selected": selected,
        "omitted": omitted,
        "forbidden_patterns": [],
        "html_entries": {"index.html", "reference.html"},
        "html_pages": {"index.html", "reference.html"},
        "html_text": html,
        "epub_entries": {"EPUB/text/ch001.xhtml", "EPUB/text/ch002.xhtml"},
        "epub_text": epub,
        "epub_nav": "Contents sec-preface sec-core-feature-specimen",
        "epub_opf": '<dc:language>en-US</dc:language><h1 id="toc-title">Contents</h1>',
        "pdf_text": (
            f"Preface Core feature specimen Contents Preview chapters Preview reference "
            f"{LINKS_PENDING} Turing 1936 Knuth 1984 chapter-to-appendix route "
            "reaches appendix-to-chapter route returns"
        ),
        "pdf_info": (
            f"Subject: {PREVIEW_DESCRIPTION}\nPages: 12\nPage size: 504 x 720 pts\n"
            "Tagged: yes\nJavaScript: no\nEncrypted: no\n"
        ),
        "pdf_fonts": (
            "name type encoding emb sub uni object ID\n----\n"
            + "\n".join(f"Font{i} Type Identity yes yes yes {i} 0" for i in range(5))
        ),
        "typ_text": 'fill: rgb("#33415518") )[PREVIEW]',
    }


def expect_failure(name, expected, mutate):
    snapshot = valid_snapshot()
    mutate(snapshot)
    try:
        validate_preview_artifacts(snapshot)
    except ContractError as error:
        if expected not in str(error):
            raise RuntimeError(
                f"error: preview artifact fixture {name} missed diagnostic "
                f"{expected!r}: {error}"
            ) from error
    else:
        raise RuntimeError(f"error: preview artifact fixture {name} unexpectedly passed")


def main():
    validate_preview_artifacts(valid_snapshot())
    expect_failure("extra-page", "HTML page allowlist differs", lambda s: s["html_pages"].add("math.html"))
    expect_failure("omitted-id", "omitted source math", lambda s: s.__setitem__("html_text", s["html_text"] + " sec-math-system"))
    expect_failure("private-path", "private path", lambda s: s["html_entries"].add("private/notes.html"))
    expect_failure("epub-identity", "EPUB contract", lambda s: s.__setitem__("epub_text", s["epub_text"].replace(PREVIEW_UUID, "urn:uuid:wrong")))
    expect_failure("citation", "ref-turing1936", lambda s: s.__setitem__("html_text", s["html_text"].replace("ref-turing1936", "missing-citation")))
    expect_failure("cross-reference", "sec-appendix-numbering", lambda s: s.__setitem__("html_text", s["html_text"].replace('href="appendices/page-system-checklist.html#sec-appendix-numbering"', "missing-cross-reference")))
    expect_failure("pdf-trim", "PDF trim", lambda s: s.__setitem__("pdf_info", s["pdf_info"].replace("504 x 720", "432 x 648")))
    expect_failure("watermark", "PDF watermark source", lambda s: s.__setitem__("typ_text", s["typ_text"].replace(")[PREVIEW]", ")[DRAFT]")))
    print("ok: preview artifact fixtures (valid contract; 8 invalid artifacts rejected)")


if __name__ == "__main__":
    try:
        main()
    except (ContractError, OSError, RuntimeError) as error:
        print(error, file=sys.stderr)
        raise SystemExit(1)
