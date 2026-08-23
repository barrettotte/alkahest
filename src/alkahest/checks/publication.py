"""Validate the cross-format contract of rendered publication artifacts."""

import html
import re
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path

from alkahest.process import run_process

ROOT = Path(__file__).resolve().parents[3]
BOOK = ROOT / "book"
BUILD = BOOK / "_build"
EPUB_PATH = BUILD / "epub/Alkahest-Reference-Book.epub"


def fail(message):
    raise SystemExit(f"error: {message}")


def load(path):
    path = Path(path)
    if not path.is_absolute():
        path = ROOT / path
    if not path.is_file():
        fail(f"required publication artifact is missing: {path.relative_to(ROOT)}")
    return path.read_text(encoding="utf-8")


def require(content, needles, label):
    if isinstance(needles, str):
        needles = (needles,)
    for needle in needles:
        if needle not in content:
            fail(f"{label} is missing required text: {needle}")


def reject(content, needles, label):
    if isinstance(needles, str):
        needles = (needles,)
    for needle in needles:
        if needle in content:
            fail(f"{label} contains forbidden text: {needle}")


def require_patterns(content, patterns, label):
    for pattern in patterns:
        if not re.search(pattern, content, flags=re.MULTILINE):
            fail(f"{label} is missing required pattern: {pattern}")


def reject_pattern(content, pattern, label):
    if re.search(pattern, content, flags=re.IGNORECASE | re.MULTILINE):
        fail(f"{label} contains forbidden pattern: {pattern}")


def require_count(content, needle, count, label):
    actual = content.count(needle)
    if actual != count:
        fail(f"{label} contains {actual} copies of {needle!r}; expected {count}")


def require_files(root, names, label):
    for name in names:
        if not (root / name).is_file():
            fail(f"{label} is missing: {name}")


def normalize_html(content):
    content = re.sub(r"<[^>]+>", " ", content)
    content = html.unescape(content)
    content = re.sub(r"\s+", " ", content)
    content = re.sub(r"\s+([,.;:)])", r"\1", content)
    return re.sub(r"([(])\s+", r"\1", content)


def normalize_pdf(content):
    content = re.sub(r"([^\W_])-[ \t]*\r?\n[ \t]*([^\W_])", r"\1-\2", content)
    content = re.sub("\u00ad\\s*", "", content)
    content = re.sub(r"\s+", " ", content)
    return re.sub(r"/\s+", "/", content)


def html_tree(root):
    return normalize_html("".join(load(path) for path in sorted(root.rglob("*.html"))))


def run_checked(command, *, input_text=None):
    result = run_process(
        command,
        cwd=ROOT,
        input=input_text,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    if result.returncode:
        sys.stderr.write(result.stdout)
        sys.stderr.write(result.stderr)
        fail(f"command failed: {' '.join(map(str, command))}")
    return result.stdout


def check_fonts(html_theme, bootstrap_css, epub_css, epub_names):
    require(bootstrap_css, "--alkahest-primary", "HTML theme")
    require(epub_css, ("Embedded font notices", "color: #334155"), "EPUB theme")
    fonts = (
        "LibertinusSerif-Regular.woff2",
        "LibertinusSerif-Italic.woff2",
        "LibertinusSerif-Bold.woff2",
        "LibertinusSerif-BoldItalic.woff2",
        "LibertinusSerifDisplay-Regular.woff2",
        "LibertinusSans-Regular.woff2",
        "LibertinusSans-Italic.woff2",
        "LibertinusSans-Bold.woff2",
        "SourceCodePro-Regular.otf.woff2",
        "SourceCodePro-It.otf.woff2",
        "SourceCodePro-Bold.otf.woff2",
        "SourceCodePro-BoldIt.otf.woff2",
    )
    require_files(BUILD / "html/theme/fonts", fonts, "HTML theme font")
    archived_files = set(epub_names.splitlines())
    for font in fonts:
        require(html_theme, f"fonts/{font}", "HTML font theme")
        if f"EPUB/fonts/{font}" not in archived_files:
            fail(f"EPUB font archive is missing: {font}")
        require(epub_css, f"../fonts/{font}", "EPUB font theme")
    require_files(
        BUILD / "html/theme/fonts/licenses",
        ("Libertinus-OFL.txt", "Source-Code-Pro-OFL.md"),
        "HTML font license",
    )


def check_shared_markers(html_text, epub_text):
    markers = (
        "Publication data",
        "For the readers who build things to understand them.",
        "Appendix A",
        "Appendix B",
        "Appendix C",
        "Language and writing-system specimen",
        "A deliberately long chapter title for testing wrapping",
        "Page continuity after a pagination stress chapter",
        "Layout acceptance record",
        "Boundary Alpha begins",
        "Boundary Lima ends",
        "Contents",
        "Section 1.1",
        "Section 1.1.1",
        "Figure 1.1",
        "Table 1.1",
        "Equation 1.1",
        "Listing 1.1",
        "Code blocks and executable-example presentation",
        "counter.py",
        "status.py",
        "Clamp untrusted input before applying the thresholds.",
        "ALKAHEST_LONG_LINE_BEGIN",
        "LONG_LINE_END",
        "counter.patch",
        "python3 counter.py",
        "checksum.py",
        "standard output",
        "Mathematical notation and reasoning",
        "Aligned equations",
        "Cases and custom operators",
        "Matrices and vectors",
        "Theorem 6.1",
        "Saturation bounds",
        "Proof",
        "Figures and visual evidence",
        "Captions, alternatives, and provenance",
        "Subfigures and panel references",
        "Full-width and output-specific art",
        "Figure 7.1",
        "Figure 7.2",
        "Figure 7.2 (a)",
        "Figure 7.2 (b)",
        "Figure 7.3",
        "Source: original Alkahest fixture",
        "Tables and instructional blocks",
        "Measurement and acceptance plan",
        "Bench-test sequence",
        "Close the test session.",
        "Margin note: measure twice",
        "Disconnect power before changing leads",
        "Optional extension: characterize drift",
        "Exercise 8.1",
        "Solution 8.1",
        "Project: build a threshold indicator",
        "Lab: verify the threshold indicator",
        "Learning components",
        "Learning objectives",
        "Prerequisites",
        "Expected time:",
        "Difficulty:",
        "Review question: threshold evidence",
        "Operating-interval exercise",
        "Companion materials",
        "Half-adder Verilog source",
        "Half-adder truth-table dataset",
        "Half-adder logic schematic",
        "Half-adder bill of materials",
        "Half-adder project pack manifest",
        "Release package: companion/half-adder.v",
        "Controlled content reuse",
        "Safety notice — disconnect before changing connections.",
        "Observed value",
        "Rights review notice.",
        "Worked example — tolerance interval.",
        "Project prerequisites.",
        "Dependency boundary",
        "Semantic icons",
        "Initial semantic icon registry",
        "Equipment required.",
        "stored energy is present.",
        "Optional material.",
        "Stop if the hazard remains.",
        "Accessibility and narrow reflow",
        "Icon meaning remains in visible text",
        "Glossary authoring contract",
        "central processing unit (CPU)",
        "central processing units",
        "CPUs",
        "instruction set architecture (ISA)",
        "matrices",
        "quantum bits (qubits)",
        "A useful footnote should not depend on the geometry of a printed page.",
        "Semantic notes remain in manuscript source order even when an edition moves their presentation.",
    )
    require(html_text, markers, "HTML publication")
    require(epub_text, markers, "EPUB publication")


def check_notes(html_text, epub_text, epub_language):
    reference = load(BUILD / "html/reference.html")
    components = load(BUILD / "html/components.html")
    structures = (
        'data-note-id="page-geometry" data-note-occurrence="1"',
        'data-note-id="page-geometry" data-note-occurrence="2"',
    )
    require(reference, structures, "HTML semantic footnote")
    require(epub_language, structures, "EPUB semantic footnote")
    cross_chapter = 'data-note-id="source-order" data-note-occurrence="1"'
    require(components, cross_chapter, "HTML cross-chapter semantic footnote")
    require(epub_language, cross_chapter, "EPUB cross-chapter semantic footnote")
    require(
        reference,
        (
            'href="#fn1" class="footnote-ref" id="fnref1" role="doc-noteref"',
            'href="#fnref1" class="footnote-back" role="doc-backlink"',
        ),
        "HTML native footnote",
    )
    require(
        epub_language,
        (
            'class="footnote-ref" id="fnref1" epub:type="noteref" role="doc-noteref"',
            '<aside epub:type="footnote" role="doc-footnote" id="fn1">',
        ),
        "EPUB native footnote",
    )
    repeated = "A useful footnote should not depend on the geometry of a printed page."
    single = "Semantic notes remain in manuscript source order even when an edition moves their presentation."
    for content, label in ((html_text, "HTML"), (epub_text, "EPUB")):
        require_count(content, repeated, 2, f"{label} repeated semantic note")
        require_count(content, single, 1, f"{label} single-use semantic note")


def check_appendices_and_citations(html_text, epub_text, epub_language, epub_nav):
    appendix = load(BUILD / "html/appendices/page-system-checklist.html")
    reference = load(BUILD / "html/reference.html")
    bibliography = load(BUILD / "html/references.html")
    structures = tuple(
        f'id="{value}"'
        for value in (
            "sec-appendix-numbering",
            "fig-appendix-signal",
            "tbl-appendix-prefixes",
            "eq-appendix-scale",
            "lst-appendix-check",
            "thm-appendix-ordering",
            "nte-appendix-portability",
            "wrn-appendix-manual-labels",
            "exr-appendix-review",
            "sol-appendix-review",
        )
    )
    require(appendix, structures, "HTML appendix numbering specimen")
    require(epub_language, structures, "EPUB appendix numbering specimen")
    markers = (
        "A.2 Numbered appendix elements",
        "Figure A.1",
        "Table A.1",
        "Equation A.1",
        "Listing A.1",
        "Theorem A.1",
        "Note A.1",
        "Warning A.1",
        "Exercise A.1",
        "Solution A.1",
    )
    require(html_text, markers, "HTML appendix numbering specimen")
    require(epub_text, markers, "EPUB appendix numbering specimen")
    contents = '#sec-appendix-numbering"><span class="header-section-number">A.2</span> Numbered appendix elements'
    require(appendix, contents, "HTML appendix contents")
    require(epub_nav, contents, "EPUB appendix contents")

    chapter_links = (
        'href="appendices/page-system-checklist.html#sec-appendix-numbering"',
        'href="appendices/page-system-checklist.html#fig-appendix-signal"',
    )
    appendix_links = (
        'href="../reference.html#sec-heading-hierarchy"',
        'href="../reference.html#eq-ohms-law"',
    )
    require(reference, chapter_links, "HTML chapter-to-appendix reference")
    require(appendix, appendix_links, "HTML appendix-to-chapter reference")
    require_patterns(
        epub_language,
        (
            r'href="ch[0-9]+\.xhtml#sec-appendix-numbering"',
            r'href="ch[0-9]+\.xhtml#fig-appendix-signal"',
            r'href="ch[0-9]+\.xhtml#sec-heading-hierarchy"',
            r'href="ch[0-9]+\.xhtml#eq-ohms-law"',
        ),
        "EPUB bidirectional appendix reference",
    )
    require(
        appendix,
        ('data-cites="knuth1984"', 'href="../references.html#ref-knuth1984"', "Knuth 1984"),
        "HTML appendix citation",
    )
    require(bibliography, 'id="ref-knuth1984"', "HTML shared bibliography")
    require(
        epub_language,
        ('data-cites="knuth1984"', 'id="ref-knuth1984"', "Knuth 1984"),
        "EPUB appendix citation",
    )
    citations = (
        "narrative form with Turing (1936)",
        "page locator (Turing 1936, 230–31)",
        "multiple sources (Turing 1936; Knuth 1984)",
        "author suppression with Turing (1936)",
        "repeated source (Turing 1936)",
    )
    require(html_text, citations, "HTML author-date citation specimen")
    require(epub_text, citations, "EPUB author-date citation specimen")
    entries = (
        "Knuth, Donald E. 1984",
        "Literate Programming",
        "10.1093/comjnl/27.2.97",
        "Shannon, Claude E. 1948",
        "Mathematical Theory of",
        "10.1002/j.1538-7305.1948.tb01338.x",
    )
    require(bibliography, entries, "HTML shared bibliography")
    require(epub_language, entries, "EPUB shared bibliography")
    require_count(bibliography, 'id="ref-knuth1984"', 1, "HTML central bibliography")
    require_count(epub_language, 'id="ref-knuth1984"', 1, "EPUB central bibliography")


def check_numeric_citations():
    reference = load(BUILD / "smoke/citations/numeric/html/reference.html")
    bibliography = load(BUILD / "smoke/citations/numeric/html/references.html")
    pdf = BUILD / "smoke/citations/numeric/typst/Alkahest-Reference-Book.pdf"
    if not pdf.is_file():
        fail(f"numeric citation PDF is missing: {pdf.relative_to(ROOT)}")
    html_text = normalize_html(reference + bibliography)
    pdf_text = normalize_pdf(run_checked(("pdftotext", "-layout", str(pdf), "-")))
    markers = (
        "early citation [1]",
        "narrative form with [1]",
        "page locator [1, pp. 230–231]",
        "multiple sources [1], [2]",
        "author suppression with Turing [1]",
        "repeated source [1]",
        "References",
        "[1] A. M. Turing",
        "[2] D. E. Knuth",
        "[3] C. E. Shannon",
        "10.1112/plms/s2-42.1.230",
        "10.1093/comjnl/27.2.97",
        "10.1002/j.1538-7305.1948.tb01338.x",
    )
    require(html_text, markers, "numeric HTML citation smoke edition")
    require(pdf_text, markers, "numeric Typst citation smoke edition")
    require(
        bibliography,
        tuple(f'id="ref-{key}"' for key in ("turing1936", "knuth1984", "shannon1948")),
        "numeric HTML bibliography entry",
    )


def check_editions(html_text, epub_text, edition_text):
    html_index = load(BUILD / "html/index.html")
    require(html_text, "Foundations", "HTML publication")
    require(
        html_index,
        ("Production reference", "Language reference", "Online reference"),
        "HTML appendix group",
    )
    reject(epub_text, ("Production reference", "Language reference"), "EPUB publication")
    require(
        html_text,
        ("Appendix D", "Extended laboratory observations"),
        "HTML online-only appendix",
    )
    require(
        load(BUILD / "html/appendices/online-lab-notes.html"),
        'id="sec-extended-lab-observations"',
        "HTML online-only appendix",
    )
    reject(epub_text, "Extended laboratory observations", "EPUB publication")
    reject(html_text, "Supplemental workbook", "primary HTML publication")
    reject(epub_text, "Supplemental workbook", "primary EPUB publication")

    abridged = edition_text["abridged"]
    require(
        load(BUILD / "smoke/editions/abridged/html/index.html"),
        "Abridged foundations",
        "abridged part",
    )
    require(
        abridged,
        (
            "Core feature specimen",
            "Code blocks and executable-example presentation",
            "Mathematical notation and reasoning",
            "Figures and visual evidence",
            "Tables and instructional blocks",
            "Learning components",
            "Companion materials",
            "Controlled content reuse",
            "Glossary authoring contract",
        ),
        "abridged edition",
    )
    reject(
        abridged,
        (
            "A deliberately long chapter title for testing wrapping",
            "Page continuity after a pagination stress chapter",
            "Layout acceptance record",
            "Semantic icons",
        ),
        "abridged edition",
    )

    preview_root = BUILD / "smoke/editions/preview/html"
    preview = edition_text["preview"]
    preview_index = load(preview_root / "index.html")
    require(
        load(preview_root / "index.html"),
        ("Preview chapters", "Preview reference"),
        "preview edition",
    )
    require(
        preview_index,
        (
            'class="alkahest-preview-watermark"',
            'class="alkahest-preview-notice"',
            'data-full-edition-link="unassigned"',
            'data-purchase-link="unassigned"',
            'data-watermark="enabled"',
            "Preview edition",
            "This preview contains two selected chapters",
            "Full-edition and purchase links will appear here",
        ),
        "preview HTML presentation",
    )
    reject(
        preview_index,
        ("example.invalid", "Purchase the full edition</a>"),
        "unassigned preview HTML links",
    )

    preview_epub_path = BUILD / "smoke/editions/preview/epub/Alkahest-Reference-Book.epub"
    if not preview_epub_path.is_file():
        fail(f"preview EPUB is missing: {preview_epub_path.relative_to(ROOT)}")
    with zipfile.ZipFile(preview_epub_path) as archive:
        preview_epub_names = archive.namelist()
        preview_epub_raw = "".join(
            archive.read(name).decode("utf-8")
            for name in preview_epub_names
            if name.endswith(".xhtml")
        )
        preview_epub_opf = archive.read("EPUB/content.opf").decode("utf-8")
    require(
        preview_epub_raw,
        (
            "alkahest-preview-watermark",
            "alkahest-preview-notice",
            "Preview edition",
            "This preview contains two selected chapters",
            "Full-edition and purchase links will appear here",
        ),
        "preview EPUB presentation",
    )
    require(
        preview_epub_opf,
        (
            "urn:uuid:551be2aa-8be0-4078-b9dc-3f29e1088092",
            "A two-chapter preview of Alkahest Reference Book",
        ),
        "preview EPUB metadata",
    )
    reject(
        preview_epub_raw,
        ("example.invalid", "Purchase the full edition</a>"),
        "unassigned preview EPUB links",
    )

    preview_pdf_path = BUILD / "smoke/editions/preview/typst/Alkahest-Reference-Book.pdf"
    if not preview_pdf_path.is_file():
        fail(f"preview PDF is missing: {preview_pdf_path.relative_to(ROOT)}")
    preview_pdf = normalize_pdf(run_checked(("pdftotext", "-layout", str(preview_pdf_path), "-")))
    preview_typ = load(BUILD / "smoke/editions/preview/typst/Alkahest-Reference-Book.typ")
    require(
        preview_typ,
        ('fill: rgb("#33415518")', ")[PREVIEW]"),
        "preview PDF watermark source",
    )
    require(
        preview_pdf,
        (
            "Two-chapter preview edition",
            "Preview edition",
            "This preview contains two selected chapters",
            "Full-edition and purchase links will appear here",
        ),
        "preview PDF presentation",
    )
    require(
        preview,
        (
            "Appendix A",
            "A.2 Numbered appendix elements",
            "Figure A.1",
            "A chapter-to-appendix route reaches",
        ),
        "preview edition",
    )
    preview_reference = load(preview_root / "reference.html")
    require(
        preview_reference,
        'href="appendices/page-system-checklist.html#sec-appendix-numbering"',
        "preview chapter-to-appendix reference",
    )
    require(
        load(preview_root / "appendices/page-system-checklist.html"),
        'href="../reference.html#sec-heading-hierarchy"',
        "preview appendix-to-chapter reference",
    )
    reject(
        preview,
        (
            "Code blocks and executable-example presentation",
            "Mathematical notation and reasoning",
            "Figures and visual evidence",
            "Tables and instructional blocks",
            "Learning components",
            "Companion materials",
            "Controlled content reuse",
            "Semantic icons",
            "Format behavior",
            "Language and writing-system specimen",
            "Extended laboratory observations",
            "Supplemental workbook",
        ),
        "preview edition",
    )
    reject(
        preview_reference, ("sec-format-behavior", "sec-language-and-script"), "preview references"
    )

    public = edition_text["public"]
    private = edition_text["private"]
    supplemental = edition_text["supplemental"]
    private_canary = "internal editorial canary and must never appear in a public artifact"
    private_answer = "Answer key: threshold evidence"
    require(public, "Core feature specimen", "public edition")
    require(
        load(BUILD / "smoke/editions/private/html/index.html"),
        "Private working material",
        "private edition part",
    )
    require(private, (private_canary, private_answer), "private edition")
    answer_key = load(BUILD / "smoke/editions/private/html/private/answer-key.html")
    require(
        answer_key,
        ('id="ans-threshold-reasoning"', 'data-for="rev-threshold-reasoning"'),
        "private answer-key contract",
    )
    public_artifacts = (
        html_text,
        epub_text,
        edition_text["abridged"],
        preview,
        public,
        supplemental,
    )
    for artifact in public_artifacts:
        reject(artifact, (private_canary, private_answer), "public artifact")
    reject(public, "Extended laboratory observations", "public/full edition")
    reject(private, "Supplemental workbook", "private edition")

    supplemental_root = BUILD / "smoke/editions/supplemental/html"
    require(
        load(supplemental_root / "index.html"),
        "Supplemental reference",
        "supplemental appendix group",
    )
    require(
        supplemental,
        ("Appendix A", "Appendix B", "Appendix C", "Appendix D", "Supplemental workbook"),
        "supplemental edition",
    )
    require(
        load(supplemental_root / "appendices/supplemental-workbook.html"),
        'id="sec-supplemental-workbook"',
        "supplemental appendix",
    )
    reject(supplemental, "Extended laboratory observations", "supplemental edition")


def check_code_and_math(bootstrap_css, epub_css, epub_language):
    require_patterns(
        bootstrap_css,
        (
            r"widows:\s*2",
            r"orphans:\s*2",
            r"overflow-wrap:\s*anywhere",
            r"overflow-x:\s*auto",
        ),
        "HTML reflow theme",
    )
    require_patterns(
        epub_css,
        (r"widows:\s*2", r"orphans:\s*2", r"overflow-wrap:\s*anywhere", r"white-space:\s*pre-wrap"),
        "EPUB reflow theme",
    )
    html_code = load(BUILD / "html/code-blocks.html")
    require(
        html_code,
        (
            'class="code-with-filename"',
            'class="code-with-filename-file"',
            "number-lines",
            "code-annotation-container-grid",
            "code-copy-button",
            "code-output",
        ),
        "HTML code specimen",
    )
    require(
        epub_language,
        (
            'class="code-with-filename"',
            'class="code-with-filename-file"',
            "number-lines",
            'data-code-annotation="1"',
            "code-output",
        ),
        "EPUB code specimen",
    )

    html_math = load(BUILD / "html/math.html")
    math_structures = (
        '<math display="inline"',
        '<math display="block"',
        'id="eq-state-update"',
        'id="eq-saturation"',
        'id="eq-coordinate-rotation"',
        'id="thm-saturation-bounds" class="theorem"',
        'class="theorem-title"',
        'class="proof"',
        'class="proof-title"',
    )
    require(html_math, math_structures, "HTML math specimen")
    require(epub_language, math_structures, "EPUB math specimen")
    all_html = "".join(load(path) for path in sorted((BUILD / "html").rglob("*.html")))
    reject_pattern(all_html, r"<script[^>]+src=[^>]*mathjax", "HTML math")
    require(
        load(BOOK / "math.qmd"),
        (
            "Discrete state-space update and output equations",
            "Piecewise saturation of x between lower and upper bounds",
            "Two-dimensional coordinate rotation matrix",
        ),
        "math source description",
    )


def check_figures(epub_language, epub_svg, epub_names):
    figures = load(BUILD / "html/figures.html")
    structures = (
        'id="fig-signal-chain"',
        'id="fig-waveform-comparison" class="quarto-layout-panel"',
        'id="fig-waveform-raw"',
        'id="fig-waveform-filtered"',
        'data-ref-parent="fig-waveform-comparison"',
        'id="fig-system-map" class="figure-full-width',
        'id="fig-build-dependency-graph"',
        'id="fig-response-time-chart"',
        'id="fig-voltage-divider"',
        'id="fig-fischer-esterification"',
        'id="fig-memory-read-cycle"',
        'id="fig-half-adder-gates"',
        'id="fig-memory-instruction-layout"',
        'id="fig-processor-datapath"',
        'id="fig-velocity-vector"',
        'id="fig-inverse-square-field"',
        'class="figure-source"',
    )
    require(figures, structures, "HTML figure specimen")
    require(epub_language, structures, "EPUB figure specimen")
    require(
        figures,
        tuple(
            f"figures/generated/{name}.svg"
            for name in (
                "response-time",
                "voltage-divider",
                "fischer-esterification",
                "read-cycle-timing",
                "half-adder-gates",
                "memory-instruction-layout",
                "processor-datapath",
                "velocity-vector",
                "inverse-square-field",
            )
        ),
        "HTML generated figure asset",
    )
    alternatives = (
        "A three-stage signal chain runs from a sensor through signal conditioning to a decision stage.",
        "A jagged sampled waveform varies around a broad rise and fall",
        "A smooth waveform rises to one broad peak and falls",
        "Four modules form a closed loop: observe, model, decide, and act.",
        "A line chart with five points. Response time rises from 18 milliseconds",
        "A nine-volt source drives a one-kilohm upper resistor",
        "Skeletal structures show acetic acid plus ethanol yielding ethyl acetate plus water",
        "Four timing lanes show a clock, an active-high read control",
        "Inputs A and B each branch to an XOR gate producing SUM",
        "A sixteen-bit address space is divided into equal ROM, RAM, reserved",
        "A program counter addresses instruction memory",
        "A velocity vector points up and right",
        "Twenty-four arrows sampled on a one-meter square grid point inward",
        "Diagram description: Manuscript source and data/assets",
    )
    require(figures, alternatives, "HTML figure alternative")
    require(epub_language, alternatives, "EPUB figure alternative")
    require(
        load(BUILD / "html/reference.html"),
        "Diagram description: Inputs A and B",
        "HTML Mermaid description",
    )
    require(epub_language, "Diagram description: Inputs A and B", "EPUB Mermaid description")
    require(figures, "figures/system-map-screen.svg", "HTML figure variant")
    require(epub_svg, "screen edition", "EPUB figure variant")
    reject(figures, "system-map-print.svg", "HTML reflowable figure")
    reject(epub_svg, "print edition", "EPUB reflowable figure")

    media_ids = ("reference-tone", "moving-square-video", "circular-orbit", "vector-components")
    for media_id in media_ids:
        marker = f'id="media-{media_id}" class="rich-media'
        require(figures, marker, "HTML rich-media specimen")
        require(epub_language, marker, "EPUB rich-media specimen")
    require(
        figures,
        (
            'class="rich-media-player rich-media-audio" controls="" preload="metadata"',
            'class="rich-media-player rich-media-video" controls="" preload="metadata"',
            '<track kind="captions" src="media/moving-square-captions.vtt"',
            'class="rich-media-player rich-media-animation"',
            'title="Circular-orbit animation" loading="lazy" sandbox=""',
            'class="rich-media-player rich-media-interactive"',
            'title="Vector-component interactive" loading="lazy" sandbox="allow-scripts"',
        ),
        "HTML rich-media enhancement",
    )
    require_files(
        BUILD / "html/media",
        (
            "reference-tone.wav",
            "tone-waveform.svg",
            "tone-transcript.md",
            "moving-square.webm",
            "moving-square-poster.svg",
            "moving-square-captions.vtt",
            "moving-square-transcript.md",
            "orbit-animation.html",
            "orbit-poster.svg",
            "orbit-transcript.md",
            "vector-interactive.html",
            "vector-interactive-poster.svg",
            "vector-interactive-transcript.md",
        ),
        "HTML rich-media asset",
    )
    static_text = (
        "Transcript and description",
        "A steady 440 hertz sine tone plays for one second",
        "one solid black square moves from left to right",
        "A visible checkbox pauses the motion",
        "Arrow keys operate the focused range control",
    )
    require(figures, static_text, "HTML rich-media static equivalent")
    require(epub_language, static_text, "EPUB rich-media static equivalent")
    require(
        epub_language,
        (
            "A regular sine wave oscillates around a horizontal center line",
            "Five outlined square positions trace motion from left to right",
            "A small body is shown at four positions on a dashed circular path",
            "A ten-unit vector at thirty-seven degrees",
        ),
        "EPUB rich-media alternative",
    )
    reject_pattern(figures, r"<(audio|video)[^>]*autoplay", "HTML rich media")
    reject_pattern(epub_language, r"<(audio|video|iframe)([ >])", "EPUB rich media")
    reject_pattern(epub_names, r"^EPUB/media/.*\.(wav|webm|html|vtt|js)$", "EPUB archive")


def check_components(epub_language, html_css, epub_css):
    components = load(BUILD / "html/components.html")
    structures = tuple(
        f'id="{value}"'
        for value in (
            "tbl-measurement-plan",
            "test-sequence-table",
            "nte-measure-twice",
            "wrn-disconnect-power",
            "exr-divider-budget",
            "sol-divider-budget",
            "project-threshold-indicator",
            "lab-verify-threshold",
        )
    ) + ('data-tbl-colwidths="[24,22,18,36]"',)
    require(components, structures, "HTML component specimen")
    require(epub_language, structures, "EPUB component specimen")
    require(
        components,
        (
            'class="margin-note icon-notice callout',
            'class="icon-notice callout callout-style-simple callout-warning no-icon',
            'class="optional-material-block icon-notice callout',
            'class="project-block icon-notice callout',
            'class="lab-block icon-notice callout',
        ),
        "HTML component specimen",
    )
    require(
        epub_language,
        (
            "callout-note",
            "callout-warning",
            'class="optional-material-block icon-notice"',
            'class="project-block icon-notice"',
            'class="lab-block icon-notice"',
            "project-anchor",
            "lab-anchor",
        ),
        "EPUB component specimen",
    )
    for icon in ("idea", "warning", "optional-material", "equipment", "experiment"):
        require(components, f'data-icon="{icon}"', "HTML notice icon")
        require(epub_language, f'data-icon="{icon}"', "EPUB notice icon")
    require(components, "no-icon callout-titled", "HTML notice built-in icon suppression")
    require(epub_language, "no-icon callout-titled", "EPUB notice built-in icon suppression")
    require(
        html_css,
        (
            ".callout.icon-notice .callout-title-container .semantic-icon",
            "vertical-align:-0.12em",
        ),
        "HTML notice icon theme",
    )
    require(
        epub_css,
        (
            ".icon-notice .callout-title .semantic-icon",
            "vertical-align: -0.12em",
            "margin-right: 0.28em",
        ),
        "EPUB notice icon theme",
    )
    require(components, ("<table", "<th"), "HTML table semantics")
    require(epub_language, ("<table", "<th"), "EPUB table semantics")
    require(
        components,
        (
            "Table&nbsp;<span>8.1</span>",
            "Note&nbsp;<span>8.1</span>",
            "Warning&nbsp;<span>8.1</span>",
        ),
        "HTML component reference",
    )

    learning = load(BUILD / "html/learning.html")
    learning_structures = tuple(
        f'id="{value}"'
        for value in (
            "obj-threshold-reasoning",
            "pre-threshold-reasoning",
            "plan-threshold-reasoning",
            "sum-threshold-reasoning",
            "rev-threshold-reasoning",
            "hint-threshold-reasoning",
            "exr-learning-interval",
            "sol-learning-interval",
        )
    )
    roles = (
        "learning-objectives",
        "learning-prerequisites",
        "learning-plan",
        "learning-summary",
        "review-question",
        "question-hint",
    )
    require(learning, learning_structures + roles, "HTML learning component")
    require(epub_language, learning_structures + roles, "EPUB learning component")
    require(learning, "20 minutes", "HTML expected time")
    require(epub_language, "Foundational", "EPUB difficulty")
    relationships = ('data-for="rev-threshold-reasoning"', 'data-for="exr-learning-interval"')
    require(learning, relationships, "HTML learning relationship")
    require(epub_language, relationships, "EPUB learning relationship")


def check_companions_and_reuse(epub_text, epub_language, html_css, epub_css):
    companions = load(BUILD / "html/companion-materials.html")
    companion_ids = (
        "asset-half-adder-verilog",
        "asset-half-adder-data",
        "asset-half-adder-schematic",
        "asset-half-adder-bom",
        "asset-half-adder-project-pack",
    )
    require(
        companions, tuple(f'id="{value}"' for value in companion_ids), "HTML companion identity"
    )
    require(
        epub_language, tuple(f'id="{value}"' for value in companion_ids), "EPUB companion identity"
    )
    kinds = ("code", "dataset", "schematic", "bill-of-materials", "download")
    require(companions, tuple(f"companion-kind-{kind}" for kind in kinds), "HTML companion kind")
    require(epub_language, tuple(f"companion-kind-{kind}" for kind in kinds), "EPUB companion kind")
    require(
        companions,
        (
            'data-companion-sha256="9f5af146dd486b46c75395650a3ef95bd346b7055bf0180e89ec37e64d9fae60"',
            'href="companion/half-adder.v"',
        ),
        "HTML companion metadata",
    )
    require(epub_language, 'data-companion-version="1.0.0"', "EPUB companion version")
    bundle_markers = (
        'data-companion-bundle="bundle-half-adder-project"',
        'data-companion-bundle-version="1.0.0"',
        'data-companion-bundle-path="companion/alkahest-half-adder-companion-1.0.0.zip"',
        "Versioned bundle: Half-adder project companion bundle, version 1.0.0.",
        "Bundle license: CC0-1.0.",
        "Release package: companion/alkahest-half-adder-companion-1.0.0.zip",
    )
    require(companions, bundle_markers, "HTML companion bundle")
    require(epub_language, bundle_markers, "EPUB companion bundle")
    require(epub_text, "Release package: companion/half-adder.v", "EPUB companion fallback")
    require_files(
        BUILD / "html/companion",
        (
            "half-adder.v",
            "half-adder-truth-table.csv",
            "half-adder-schematic.svg",
            "half-adder-bom.csv",
            "half-adder-project-pack.md",
        ),
        "HTML companion download",
    )

    reuse = load(BUILD / "html/content-reuse.html")
    use_sites = (
        "reuse-use-safety-disconnect",
        "reuse-use-observed-value-definition",
        "reuse-use-rights-review",
        "reuse-use-tolerance-example",
        "reuse-use-project-prerequisites",
    )
    require(reuse, tuple(f'id="{value}"' for value in use_sites), "HTML reusable-content use site")
    require(
        epub_language,
        tuple(f'id="{value}"' for value in use_sites),
        "EPUB reusable-content use site",
    )
    reuse_kinds = ("notice", "definition", "legal", "example", "project-prerequisite")
    require(
        reuse, tuple(f"reuse-kind-{kind}" for kind in reuse_kinds), "HTML reusable-content kind"
    )
    require(
        epub_language,
        tuple(f"reuse-kind-{kind}" for kind in reuse_kinds),
        "EPUB reusable-content kind",
    )
    require(
        reuse,
        (
            'data-reuse-sha256="d3607e3cdc8ae5fb347b4f82ff9649f3724c2e7c46205dcb0c83c9477fd0a570"',
            'data-reuse-context="project"',
            "De-energize the test fixture",
        ),
        "HTML reusable-content metadata",
    )
    require(
        epub_language,
        (
            'data-reuse-version="1.0.0"',
            'data-reuse-origin="alkahest-reference-book"',
            "a current-limited supply and multimeter",
        ),
        "EPUB reusable-content metadata",
    )
    require(html_css, ".reusable-content", "HTML reusable-content styling")
    require(epub_css, ".reusable-content", "EPUB reusable-content styling")


def check_icons(epub_language, epub_svg, html_css, epub_css, temp_epub):
    icons = load(BUILD / "html/icons.html")
    components = BUILD / "html/components.html"
    names = ("equipment", "warning", "danger", "idea", "experiment", "optional-material")
    for name in names:
        require(icons, (f'data-icon="{name}"', f"icons/{name}.svg"), "HTML icon specimen")
        require(epub_language, f'data-icon="{name}"', "EPUB icon specimen")
    alternatives = (
        "Equipment required",
        "Warning",
        "Danger",
        "Idea",
        "Experiment",
        "Optional material",
        "Stop; danger remains",
    )
    require(icons, tuple(f'alt="{label}"' for label in alternatives), "HTML icon alternative")
    require(
        epub_language, tuple(f'alt="{label}"' for label in alternatives), "EPUB icon alternative"
    )
    require(
        epub_svg,
        (
            "Equipment symbol",
            "Warning symbol",
            "Danger symbol",
            "Idea symbol",
            "Experiment symbol",
            "Optional material symbol",
        ),
        "EPUB icon asset",
    )
    require(
        icons,
        ('class="semantic-icon semantic-icon-danger"', 'data-icon-label="Stop; danger remains"'),
        "HTML icon alias and label override",
    )
    run_checked(
        (
            sys.executable,
            "-m",
            "alkahest.checks.rendered_icons",
            str(BUILD / "html/icons.html"),
            str(components),
            temp_epub,
        )
    )
    require(
        html_css,
        (".icon-accessibility-specimen{", "@media(max-width: 480px)", "overflow-wrap:anywhere"),
        "HTML narrow icon theme",
    )
    require(
        epub_css,
        (
            ".icon-accessibility-specimen",
            "max-width: 18rem",
            "overflow-wrap: anywhere",
            "vertical-align: -0.14em",
        ),
        "EPUB narrow icon theme",
    )


def check_glossary(epub_language, html_css, epub_css):
    glossary = load(BUILD / "html/glossary.html")
    backmatter = load(BUILD / "html/glossary-backmatter.html")
    locale_backmatter = load(BUILD / "locale/fr/html/glossary-backmatter.html")
    require(
        backmatter,
        (
            'class="generated-glossary"',
            'data-glossary-count="4"',
            'class="glossary-entry"',
            'aria-labelledby="glossary-central-processing-unit"',
            'role="definition"',
        ),
        "HTML generated glossary",
    )
    require(
        epub_language,
        ('class="generated-glossary"', 'data-glossary-count="4"', 'role="definition"'),
        "EPUB generated glossary",
    )
    reference = load(BUILD / "html/reference.html")
    require(
        reference,
        (
            "glossary-backmatter.html#glossary-central-processing-unit",
            'data-glossary-case="sentence"',
            'data-glossary-link="true"',
            'lang="en-US"',
            "Central processing unit (CPU)",
        ),
        "HTML cross-chapter glossary reference",
    )
    require(
        epub_language,
        ('data-glossary-case="sentence"', "Central processing unit (CPU)"),
        "EPUB sentence-cased glossary reference",
    )
    require(
        glossary,
        (
            '<span id="glossary-unlinked-fallback"><span class="glossary-term"',
            'data-glossary-link="false"',
            ">matrix</span></span>",
        ),
        "HTML unlinked glossary fallback",
    )
    require(
        epub_language,
        ('id="glossary-unlinked-fallback"', 'data-glossary-link="false"', ">matrix</span></span>"),
        "EPUB unlinked glossary fallback",
    )
    glossary_ids = (
        "central-processing-unit",
        "instruction-set-architecture",
        "matrix",
        "quantum-bit",
    )
    positions = []
    for glossary_id in glossary_ids:
        require(glossary, f'data-glossary-id="{glossary_id}"', "HTML glossary reference")
        require(epub_language, f'data-glossary-id="{glossary_id}"', "EPUB glossary reference")
        anchor = f'id="glossary-{glossary_id}"'
        require(backmatter, anchor, "HTML glossary anchor")
        require(epub_language, anchor, "EPUB glossary anchor")
        link = f'glossary-{glossary_id}" class="glossary-link" title="'
        require(glossary, link, "HTML glossary link and tooltip")
        require(epub_language, link, "EPUB glossary link and tooltip")
        positions.append(backmatter.index(anchor))
    if positions != sorted(positions) or len(set(positions)) != len(positions):
        fail("HTML glossary entries are not in stable display-term order")
    forms = ("term", "plural", "acronym", "acronym-plural", "first", "first-plural")
    form_markers = tuple(f'data-glossary-form="{form}"' for form in forms)
    require(glossary, form_markers, "HTML glossary form")
    require(epub_language, form_markers, "EPUB glossary form")
    require(glossary, '<span class="glossary-term"', "HTML portable glossary span")
    require(epub_language, '<span class="glossary-term"', "EPUB portable glossary span")
    require(html_css, ".glossary-entry{", "HTML glossary entry theme")
    require(epub_css, ".glossary-entry", "EPUB glossary entry theme")
    language_contract = ('class="generated-glossary"', 'lang="en-US"', 'role="definition"')
    require(backmatter, language_contract, "HTML generated glossary language scope")
    require(epub_language, language_contract, "EPUB generated glossary language scope")
    require(locale_backmatter, language_contract, "localized generated glossary language scope")


def check_locale(epub_language, temp_epub):
    language = load(BUILD / "html/appendices/language-and-script.html")
    locale_index = load(BUILD / "locale/fr/html/index.html")
    locale_reference = load(BUILD / "locale/fr/html/reference.html")
    require(load(BUILD / "html/index.html"), 'lang="en-US"', "HTML root")
    require(locale_index, 'lang="fr-FR"', "French HTML root")
    semantics = (
        'lang="en-US"',
        'lang="fr-FR"',
        'lang="de-DE"',
        'lang="el-GR"',
        'lang="ru-RU"',
        'lang="he-IL" dir="rtl"',
    )
    require(language, semantics, "HTML language specimen")
    require(epub_language, semantics, "EPUB language specimen")
    require(locale_index, "Table des matières", "French HTML")
    require(
        locale_reference,
        ("Tableau&nbsp;", "Équation&nbsp;", "Extrait&nbsp;", "Annexe A"),
        "French HTML",
    )
    require(language, ("25&nbsp;MHz", "Figure&nbsp;1"), "HTML language specimen")
    run_checked(
        (
            sys.executable,
            "-m",
            "alkahest.rendering.unicode_spaces",
            "html",
            str(BUILD / "html/appendices/language-and-script.html"),
        )
    )
    run_checked((sys.executable, "-m", "alkahest.rendering.unicode_spaces", "epub", temp_epub))


def main():
    if not EPUB_PATH.is_file():
        fail(f"EPUB is missing: {EPUB_PATH.relative_to(ROOT)}")
    html_root = BUILD / "html"
    bootstrap_root = html_root / "site_libs/bootstrap"
    bootstrap_files = sorted(bootstrap_root.glob("bootstrap-*.css"))
    component_files = sorted(bootstrap_root.glob("bootstrap-*.min.css"))
    if not bootstrap_files:
        fail("HTML bootstrap theme is missing")
    if not component_files:
        fail("HTML component theme is missing")
    bootstrap_css = "".join(load(path) for path in bootstrap_files)
    component_css = load(component_files[0])
    html_theme = load(html_root / "theme/alkahest-fonts.css")
    html_text = html_tree(html_root)
    edition_text = {
        edition: html_tree(BUILD / f"smoke/editions/{edition}/html")
        for edition in ("abridged", "preview", "public", "private", "supplemental")
    }

    with zipfile.ZipFile(EPUB_PATH) as archive:
        names = archive.namelist()
        epub_names = "\n".join(names)
        epub_css = archive.read("EPUB/styles/stylesheet1.css").decode("utf-8")
        text_names = sorted(
            name for name in names if name.startswith("EPUB/text/") and name.endswith(".xhtml")
        )
        svg_names = sorted(
            name for name in names if name.startswith("EPUB/media/") and name.endswith(".svg")
        )
        epub_language = "".join(archive.read(name).decode("utf-8") for name in text_names)
        epub_nav = archive.read("EPUB/nav.xhtml").decode("utf-8")
        epub_svg = "".join(archive.read(name).decode("utf-8") for name in svg_names)
    epub_text = normalize_html(epub_nav + epub_language)

    with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", suffix=".xhtml") as temp:
        temp.write(epub_language)
        temp.flush()
        check_fonts(html_theme, bootstrap_css, epub_css, epub_names)
        check_shared_markers(html_text, epub_text)
        check_notes(html_text, epub_text, epub_language)
        check_appendices_and_citations(html_text, epub_text, epub_language, epub_nav)
        check_numeric_citations()
        check_editions(html_text, epub_text, edition_text)
        check_code_and_math(bootstrap_css, epub_css, epub_language)
        check_figures(epub_language, epub_svg, epub_names)
        reject(html_text, "1.1.1.1", "HTML heading hierarchy")
        reject(epub_text, "1.1.1.1", "EPUB heading hierarchy")
        check_components(epub_language, component_css, epub_css)
        check_companions_and_reuse(epub_text, epub_language, component_css, epub_css)
        check_icons(epub_language, epub_svg, component_css, epub_css, temp.name)
        check_glossary(epub_language, component_css, epub_css)
        check_locale(epub_language, temp.name)
    print(
        "ok: HTML/EPUB structure, citation-style parity and numeric override, "
        "bidirectional appendix references, shared bibliography, whole-book "
        "edition grouping/omission/privacy/numbering, code/math/figure/rich-media/"
        "component/companion/reuse/icon/notice/glossary/semantic-note/index/"
        "generated-list/persistent-ID contracts, locale semantics, theme, "
        "embedded fonts, and heading markers"
    )


if __name__ == "__main__":
    main()
