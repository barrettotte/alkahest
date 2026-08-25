"""Validate rendered notes, identities, indexes, and generated lists."""

from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path
from typing import Never

from alkahest.process import run_process
from alkahest.rendering.text_contract import validate as validate_text_contract
from alkahest.rendering.text_normalize import normalize

ROOT = Path(__file__).resolve().parents[3]
BUILD = ROOT / "book" / "_build"


class RenderedContractError(RuntimeError):
    """Report a rendered-artifact contract violation."""


def fail(message: str) -> Never:
    raise RenderedContractError(f"error: {message}")


def require_path(path: Path, label: str) -> None:
    if not path.exists():
        fail(f"{label} is missing: {path.relative_to(ROOT)}")


def read_text(path: Path, label: str) -> str:
    require_path(path, label)
    return path.read_text(encoding="utf-8", errors="replace")


def require_literal(text: str, literal: str, label: str) -> None:
    if literal not in text:
        fail(f"{label} is missing required text: {literal}")


def reject_literal(text: str, literal: str, label: str) -> None:
    if literal in text:
        fail(f"{label} contains forbidden text: {literal}")


def require_pattern(text: str, pattern: str, label: str) -> None:
    if not re.search(pattern, text):
        fail(f"{label} is missing required pattern: {pattern}")


def run(arguments: list[str], *, capture: bool = True) -> subprocess.CompletedProcess[str]:
    try:
        return run_process(
            arguments,
            cwd=ROOT,
            check=True,
            capture_output=capture,
            text=True,
        )
    except (OSError, subprocess.CalledProcessError) as error:
        detail = ""
        if isinstance(error, subprocess.CalledProcessError):
            detail = (error.stderr or error.stdout or "").strip()
        fail(f"command failed: {' '.join(arguments)}: {detail or error}")


def check_html_links(root: Path) -> None:
    run(
        [sys.executable, "-m", "alkahest.checks.html_links", str(root.relative_to(ROOT))],
        capture=False,
    )


def epub_text(path: Path) -> str:
    require_path(path, "EPUB")
    with zipfile.ZipFile(path) as archive:
        names = sorted(
            name
            for name in archive.namelist()
            if name.startswith("EPUB/text/") and name.endswith(".xhtml")
        )
        if not names:
            fail(f"EPUB contains no XHTML documents: {path.relative_to(ROOT)}")
        return "".join(archive.read(name).decode("utf-8") for name in names)


def pdftotext() -> str:
    executable = shutil.which("pdftotext")
    if executable is None:
        fail("pdftotext is required for rendered artifact checks")
    return executable


def pdf_text(path: Path) -> str:
    require_path(path, "PDF")
    result = run([pdftotext(), str(path), "-"])
    return normalize(result.stdout, "pdf")


def validate_pdf_bbox(path: Path, label: str) -> None:
    require_path(path, label)
    with tempfile.TemporaryDirectory(prefix="alkahest-rendered-bbox.") as temporary:
        bbox = Path(temporary) / "words.html"
        result = run([pdftotext(), "-bbox", str(path), str(bbox)])
        diagnostics = [
            line for line in result.stderr.splitlines() if line and line != "no word list"
        ]
        if diagnostics:
            fail(
                "positioned-text extraction reported unexpected diagnostics: "
                + "; ".join(diagnostics)
            )
        try:
            validate_text_contract("bbox", bbox.read_text(encoding="utf-8"))
        except RuntimeError as error:
            fail(f"{label} text crosses the physical page: {error}")


def check_notes() -> None:
    chapter_root = BUILD / "smoke/notes/chapter/html"
    book_root = BUILD / "smoke/notes/book/html"
    sidenote_root = BUILD / "smoke/notes/sidenote/html"
    typst_root = BUILD / "smoke/notes/sidenote/typst"
    for root in (chapter_root, book_root, sidenote_root):
        check_html_links(root)

    chapter_reference = read_text(chapter_root / "reference.html", "chapter endnotes")
    chapter_components = read_text(chapter_root / "components.html", "chapter endnotes")
    for literal, label in (
        ('class="footnotes footnotes-end-of-document" role="doc-endnotes"', "chapter endnotes"),
        ('data-note-id="page-geometry" data-note-occurrence="1"', "chapter endnotes"),
        ('data-note-id="page-geometry" data-note-occurrence="2"', "chapter repeated note"),
        ('href="#fnref1" class="footnote-back" role="doc-backlink"', "chapter endnote backlink"),
    ):
        require_literal(chapter_reference, literal, label)
    require_literal(
        chapter_components,
        'data-note-id="source-order" data-note-occurrence="1"',
        "second chapter endnote",
    )

    book_reference = read_text(book_root / "reference.html", "book endnotes")
    book_components = read_text(book_root / "components.html", "book endnotes")
    book_apparatus = read_text(book_root / "glossary-backmatter.html", "book endnotes")
    reject_literal(book_reference, 'class="footnote-ref"', "book endnote references")
    for literal, label in (
        (
            'id="note-ref-page-geometry-1" class="book-endnote-reference"',
            "first book endnote reference",
        ),
        (
            'id="note-ref-page-geometry-2" class="book-endnote-reference"',
            "reused book endnote reference",
        ),
        ('data-note-number="1"', "book note number reuse"),
    ):
        require_literal(book_reference, literal, label)
    require_literal(
        book_components,
        'id="note-ref-source-order-1" class="book-endnote-reference"',
        "cross-chapter book endnote reference",
    )
    for literal, label in (
        ('class="level2 generated-book-notes" data-note-count="2"', "generated book notes"),
        ('id="book-note-page-geometry" class="book-endnote"', "first generated book note"),
        ('data-note-number="1"', "reused book note number"),
        ('data-note-backlinks="2"', "reused book note backlinks"),
        ('href="./reference.html#note-ref-page-geometry-1"', "first book note backlink"),
        ('href="./reference.html#note-ref-page-geometry-2"', "second book note backlink"),
        ('id="book-note-source-order" class="book-endnote"', "second generated book note"),
        ('href="./components.html#note-ref-source-order-1"', "cross-chapter book note backlink"),
    ):
        require_literal(book_apparatus, literal, label)

    sidenote_reference = read_text(sidenote_root / "reference.html", "HTML sidenotes")
    for literal, label in (
        ('class="no-row-height column-margin column-container"', "HTML sidenotes"),
        ('data-note-id="page-geometry" data-note-occurrence="1"', "first HTML sidenote"),
        ('data-note-id="page-geometry" data-note-occurrence="2"', "reused HTML sidenote"),
    ):
        require_literal(sidenote_reference, literal, label)
    reject_literal(sidenote_reference, "footnotes-end-of-document", "HTML sidenotes")

    typst_pdf = typst_root / "Alkahest-Reference-Book.pdf"
    typst_source = read_text(typst_root / "Alkahest-Reference-Book.typ", "Typst sidenote source")
    require_literal(
        typst_source,
        "#show footnote: it => column-sidenote(it.body)",
        "Typst sidenote show rule",
    )
    require_literal(
        typst_source,
        "#footnote[A useful footnote should not depend on the geometry of a printed page.]",
        "Typst repeated sidenote",
    )
    rendered = pdf_text(typst_pdf)
    require_literal(rendered, "A useful footnote should not depend on the", "Typst sidenote PDF")
    require_literal(
        rendered,
        "Semantic notes remain in manuscript source order",
        "Typst cross-chapter sidenote PDF",
    )
    validate_pdf_bbox(typst_pdf, "Typst sidenote")
    print(
        "ok: rendered semantic notes (native chapter backlinks; consolidated book "
        "apparatus; HTML and Typst sidenotes)"
    )


def require_id(text: str, identity: str, label: str) -> None:
    if f'id="{identity}"' not in text:
        fail(f"{label} does not preserve identity '{identity}'")


def check_id_file(path: Path, identity: str, label: str) -> None:
    require_id(read_text(path, label), identity, label)


def check_id_literal(path: Path, literal: str, label: str) -> None:
    if literal not in read_text(path, label):
        fail(f"{label} does not preserve '{literal}'")


def check_identities() -> None:
    lock_path = ROOT / "book/identity-lock.json"
    html_root = BUILD / "html"
    locale_root = BUILD / "locale/fr/html"
    preview_root = BUILD / "smoke/editions/preview/html"
    supplemental_root = BUILD / "smoke/editions/supplemental/html"
    private_root = BUILD / "smoke/editions/private/html"
    epub = epub_text(BUILD / "epub/Alkahest-Reference-Book.epub")
    for path in (lock_path, html_root, locale_root, preview_root, supplemental_root, private_root):
        require_path(path, "rendered-identity input")
    identities = json.loads(lock_path.read_text(encoding="utf-8"))["identities"]
    checked_content = checked_assets = checked_reuse = 0
    for entry in identities:
        if entry.get("status") != "active":
            continue
        namespace = entry["namespace"]
        kind = entry["kind"]
        identity = entry["id"]
        source = entry["source"]
        if namespace == "asset":
            require_path(ROOT / "book" / source, f"companion identity '{identity}'")
            for variant_root, label in (
                (html_root, "HTML companion registry"),
                (locale_root, "locale companion registry"),
                (supplemental_root, "supplemental companion registry"),
                (private_root, "private companion registry"),
            ):
                check_id_file(variant_root / "companion-materials.html", identity, label)
            checked_assets += 1
            continue
        if namespace == "reuse":
            require_path(ROOT / "book" / source, f"reusable-content identity '{identity}'")
            literal = f'data-reuse-id="{identity}"'
            for variant_root in (html_root, locale_root, supplemental_root, private_root):
                check_id_literal(
                    variant_root / "content-reuse.html",
                    literal,
                    "rendered reusable-content registry",
                )
            require_literal(epub, literal, "EPUB reusable-content registry")
            checked_reuse += 1
            continue
        if namespace == "glossary":
            output_id = f"glossary-{identity}"
            check_id_file(html_root / "glossary-backmatter.html", output_id, "HTML glossary")
            check_id_file(locale_root / "glossary-backmatter.html", output_id, "locale glossary")
            continue
        if namespace == "index":
            output_id = f"index-entry-{identity}"
            check_id_file(html_root / "index-backmatter.html", output_id, "HTML index")
            check_id_file(locale_root / "index-backmatter.html", output_id, "locale index")
            continue
        content_kinds = {
            "chapter",
            "section",
            "figure",
            "table",
            "equation",
            "listing",
            "exercise",
            "solution",
            "learning-objectives",
            "learning-prerequisites",
            "learning-plan",
            "learning-summary",
            "review-question",
            "question-hint",
            "answer-key",
            "reusable-use",
        }
        if kind not in content_kinds:
            continue
        relative_html = Path(source).with_suffix(".html")
        canonical = next(
            (
                root / relative_html
                for root in (html_root, supplemental_root, private_root)
                if (root / relative_html).is_file()
            ),
            None,
        )
        if canonical is None:
            fail(f"no rendered edition contains active identity '{identity}' from {source}")
        check_id_file(canonical, identity, f"rendered source {source}")
        checked_content += 1
        for variant_root in (locale_root, preview_root, supplemental_root, private_root):
            variant = variant_root / relative_html
            if variant.is_file():
                check_id_file(
                    variant,
                    identity,
                    f"rendered variant {variant_root.relative_to(ROOT)}",
                )

    for identity in (
        "sec-core-feature-specimen",
        "sec-heading-hierarchy",
        "fig-half-adder",
        "tbl-half-adder",
        "eq-ohms-law",
        "lst-half-adder",
        "exr-divider-budget",
        "asset-half-adder-verilog",
        "asset-half-adder-data",
        "asset-half-adder-schematic",
        "asset-half-adder-bom",
        "asset-half-adder-project-pack",
        "glossary-central-processing-unit",
        "index-entry-technical-publishing",
    ):
        require_id(epub, identity, "EPUB")
    print(
        f"ok: rendered identities ({checked_content} chapter/section/numbered-object/use-site "
        f"IDs; {checked_assets} companion-asset IDs; {checked_reuse} reusable-content IDs; "
        "glossary/index IDs; HTML, EPUB, preview, supplemental, private, and locale preservation)"
    )


def check_index() -> None:
    html_root = BUILD / "html"
    check_html_links(html_root)
    html_index = read_text(html_root / "index-backmatter.html", "HTML generated index")
    for literal in (
        'class="generated-indexes"',
        'data-index-entry-count="7"',
        'lang="en-US"',
        'class="index-entry index-entry-depth-1 index-entry-kind-subject"',
        'id="index-entry-processor-architecture" class="index-entry-term"',
        'href="#index-entry-instruction-set-architecture" class="index-relation-link"',
        'href="#index-entry-turing-alan" class="index-relation-link"',
        'href="./reference.html#index-ref-computation-abstract-model" class="index-locator-link"',
        'href="./reference.html#index-range-book-design-reference-tour-start" class="index-range-link index-range-start"',
        'href="./reference.html#index-range-book-design-reference-tour-end" class="index-range-link index-range-end"',
    ):
        require_literal(html_index, literal, "HTML generated index")
    for pattern, label in (
        (
            r'id="index-subject"[^>]*data-index-kind="subject"[^>]*data-index-root-count="3"|id="index-subject"[^>]*data-index-root-count="3"[^>]*data-index-kind="subject"',
            "HTML subject-index group",
        ),
        (
            r'id="index-person"[^>]*data-index-kind="person"[^>]*data-index-root-count="2"|id="index-person"[^>]*data-index-root-count="2"[^>]*data-index-kind="person"',
            "HTML person-index group",
        ),
    ):
        require_pattern(html_index, pattern, label)
    reference = read_text(html_root / "reference.html", "HTML index markers")
    for literal, label in (
        ('id="index-ref-computation-abstract-model" class="index-marker"', "HTML alias marker"),
        ('data-index-requested="computing"', "HTML alias marker"),
        (
            'id="index-range-book-design-reference-tour-start" class="index-marker"',
            "HTML range start",
        ),
        ('id="index-range-book-design-reference-tour-end" class="index-marker"', "HTML range end"),
    ):
        require_literal(reference, literal, label)

    epub = epub_text(BUILD / "epub/Alkahest-Reference-Book.epub")
    for literal in (
        'class="generated-indexes"',
        'data-index-entry-count="7"',
        'lang="en-US"',
        'id="index-entry-computation" class="index-entry-term"',
        'id="index-entry-book-design" class="index-entry-term"',
        'id="index-entry-turing-alan" class="index-entry-term"',
        'id="index-ref-computation-abstract-model" class="index-marker"',
        'id="index-range-book-design-reference-tour-start" class="index-marker"',
        'id="index-range-book-design-reference-tour-end" class="index-marker"',
    ):
        require_literal(epub, literal, "EPUB generated index")
    for target in (
        "index-ref-computation-abstract-model",
        "index-range-book-design-reference-tour-start",
        "index-range-book-design-reference-tour-end",
    ):
        require_pattern(epub, rf'href="ch[0-9]+\.xhtml#{target}"', "EPUB index")

    for path in (
        BUILD / "print/7x10/typst/Alkahest-Reference-Book.pdf",
        BUILD / "print/7x10/latex/Alkahest-Reference-Book.pdf",
    ):
        text = pdf_text(path)
        for marker in (
            "Subject index",
            "Name index",
            "processor architecture, see instruction set architecture",
            "technical publishing",
            "see also book design",
            "Turing, Alan",
            "see also computation",
        ):
            require_literal(text, marker, "page-resolved print index")
        try:
            validate_text_contract("index", text)
        except RuntimeError as error:
            fail(f"print index page-number contract failed: {error}")
    print(
        "ok: rendered indexes (linked HTML/EPUB points and ranges; nested entries; "
        "see/see-also; page-resolved Typst/LuaLaTeX ranges)"
    )


def check_lists() -> None:
    html_root = BUILD / "html"
    check_html_links(html_root)
    html_lists = read_text(html_root / "generated-lists.html", "HTML generated lists")
    for literal in (
        'class="generated-reference-lists"',
        'data-generated-list-count="7"',
        'data-configured-list-count="8"',
        'href="reference.html#fig-half-adder" class="quarto-xref"',
        'href="appendices/page-system-checklist.html#fig-appendix-signal" class="quarto-xref"',
        'href="reference.html#eq-ohms-law" class="quarto-xref"',
        'href="./glossary-backmatter.html#glossary-central-processing-unit" class="generated-list-acronym-link"',
        'data-entry-id="electric-current"',
        'data-entry-id="state-vector"',
    ):
        require_literal(html_lists, literal, "HTML generated lists")
    for group, count in (
        ("figures", 17),
        ("tables", 4),
        ("listings", 2),
        ("equations", 5),
        ("acronyms", 3),
        ("symbols", 3),
        ("nomenclature", 2),
    ):
        require_pattern(
            html_lists,
            rf'id="generated-list-{group}"[^>]*data-entry-count="{count}"',
            "HTML generated-list group",
        )
    list_titles = (
        "List of figures",
        "List of tables",
        "List of listings",
        "List of equations",
        "List of acronyms",
        "List of symbols",
        "Nomenclature",
    )
    for title in list_titles:
        require_literal(html_lists, title, "HTML generated lists")
    reject_literal(html_lists, 'data-list-name="algorithms"', "HTML empty-list omission")
    reject_literal(html_lists, "List of algorithms", "HTML empty-list omission")

    epub = epub_text(BUILD / "epub/Alkahest-Reference-Book.epub")
    for literal in (
        'class="generated-reference-lists"',
        'data-generated-list-count="7"',
        'data-configured-list-count="8"',
        'data-entry-id="fig-half-adder"',
        'data-entry-id="eq-state-update"',
        'data-entry-id="central-processing-unit"',
        'data-entry-id="electric-current"',
        'data-entry-id="state-vector"',
    ):
        require_literal(epub, literal, "EPUB generated lists")
    for target in (
        "fig-half-adder",
        "fig-appendix-signal",
        "eq-state-update",
        "glossary-central-processing-unit",
    ):
        require_pattern(epub, rf'href="ch[0-9]+\.xhtml#{target}"', "EPUB generated lists")
    reject_literal(epub, 'data-list-name="algorithms"', "EPUB empty-list omission")
    reject_literal(epub, "List of algorithms", "EPUB empty-list omission")

    print_markers = (
        "List of figures",
        "Information flow through a half-adder",
        "List of tables",
        "Measurement and acceptance plan",
        "List of listings",
        "A combinational half-adder",
        "List of equations",
        "Discrete state-space update and output equations",
        "List of acronyms",
        "CPU — central processing unit",
        "List of symbols",
        "electric current",
        "Nomenclature",
        "system state vector at discrete step",
    )
    for path in (
        BUILD / "print/7x10/typst/Alkahest-Reference-Book.pdf",
        BUILD / "print/7x10/latex/Alkahest-Reference-Book.pdf",
    ):
        text = pdf_text(path)
        for marker in print_markers:
            require_literal(text, marker, "print generated lists")
        reject_literal(text, "List of algorithms", "print empty-list omission")
        try:
            validate_text_contract("generated-lists", text)
        except RuntimeError as error:
            fail(f"print generated-list numbering contract failed: {error}")
    print(
        "ok: rendered generated lists (seven linked/numbered kinds; glossary acronyms; "
        "notation math; empty algorithm list omitted)"
    )


CHECKS = {
    "notes": check_notes,
    "identities": check_identities,
    "index": check_index,
    "lists": check_lists,
}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("contract", choices=CHECKS)
    arguments = parser.parse_args()
    CHECKS[arguments.contract]()


if __name__ == "__main__":
    try:
        main()
    except (
        json.JSONDecodeError,
        OSError,
        RenderedContractError,
        RuntimeError,
        UnicodeError,
        zipfile.BadZipFile,
    ) as error:
        print(error, file=sys.stderr)
        raise SystemExit(1) from None
