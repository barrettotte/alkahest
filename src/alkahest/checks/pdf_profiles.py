"""Validate layout and content contracts in every rendered PDF profile."""

from __future__ import annotations

import re
import shutil
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path

from alkahest.rendering.text_contract import validate as validate_text_contract
from alkahest.rendering.text_normalize import normalize

ROOT = Path(__file__).resolve().parents[3]


class ProfileError(RuntimeError):
    """Report one violated PDF-profile contract."""


@dataclass(frozen=True)
class Profile:
    """One expected rendered PDF profile."""

    path: str
    width: float
    height: float
    label: str


PROFILES = (
    Profile(
        "book/_build/print/7x10/typst/Alkahest-Reference-Book.pdf",
        504,
        720,
        "Typst 7 x 10",
    ),
    Profile(
        "book/_build/print/7x10/latex/Alkahest-Reference-Book.pdf",
        504,
        720,
        "LuaLaTeX 7 x 10",
    ),
    Profile(
        "book/_build/print/6x9/typst/Alkahest-Reference-Book.pdf",
        432,
        648,
        "Typst 6 x 9",
    ),
    Profile(
        "book/_build/print/6x9/latex/Alkahest-Reference-Book.pdf",
        432,
        648,
        "LuaLaTeX 6 x 9",
    ),
    Profile(
        "book/_build/review/letter/typst/Alkahest-Reference-Book.pdf",
        612,
        792,
        "Typst Letter review",
    ),
    Profile(
        "book/_build/review/letter/latex/Alkahest-Reference-Book.pdf",
        612,
        792,
        "LuaLaTeX Letter review",
    ),
)

REQUIRED_FONTS = (
    "LibertinusSerif-Regular",
    "LibertinusSerif-Bold",
    "LibertinusSerif-Italic",
    "LibertinusSerif-BoldItalic",
    "LibertinusSerifDisplay-Regular",
    "LibertinusSans-Bold",
    "LibertinusMath-Regular",
    "SourceCodePro-Regular",
    "SourceCodePro-Bold",
)

REQUIRED_MARKERS = (
    "Publication data",
    "For the readers who build things to understand them.",
    "Lists and notation",
    "List of figures",
    "Information flow through a half-adder",
    "Validated source-to-publication dependency graph",
    "Response time by system load",
    "A nine-volt resistive voltage divider",
    "Diagram description: Inputs A and B",
    "Diagram description: Manuscript source and data/assets",
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
    "Foundations",
    "Core feature specimen",
    "A deliberately long chapter title for testing wrapping",
    "Page continuity after a pagination stress chapter",
    "Layout acceptance record",
    "Boundary Alpha begins",
    "Boundary Lima ends",
    "Page-system checklist",
    "Numbered appendix elements",
    "A chapter-to-appendix route reaches",
    "An appendix-to-chapter route returns to",
    "Literate Programming",
    "1093/comjnl/27.2.97",
    "Format behavior",
    "Language and writing",
    "English: The characteristically interdisciplinary electromechanical laboratory",
    "Français",
    "Deutsch: Die Donaudampfschifffahrtsgesellschaft",
    "Greek: Η τεχνολογία εξελίσσεται μέσα από τη γνώση.",
    "Cyrillic: Технология развивается благодаря знаниям.",
    "Hebrew:",
    "Contents",
    "Heading hierarchy",
    "Numbered subsection with a descriptive title",
    "Detail heading excluded from numbering and contents",
    "Section 1.1",
    "Section 1.1.1",
    "Figure 1.1",
    "Table 1.1",
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
    "Chemistry-diagram workflow evaluation",
    "Fischer esterification of acetic acid with ethanol",
    "Computing-diagram workflow",
    "A synchronous memory read cycle with explicit validity timing",
    "A half-adder expressed as a conventional two-gate network",
    "Explicit address ranges and bit positions keep a memory map",
    "A minimal processor datapath distinguishes data and address paths",
    "Physics-diagram workflow",
    "A velocity vector with explicit components and preserved display precision",
    "A normalized inverse-square field with an explicit sampling grid",
    "Rich-media workflow",
    "One-second reference tone",
    "Constant horizontal motion",
    "Circular-orbit animation",
    "Vector-component interactive",
    "Transcript and description",
    "A steady 440 hertz sine tone plays for one second",
    "one solid black square moves from left to right",
    "A visible checkbox pauses the motion",
    "Arrow keys operate the focused range control",
    "Figure 7.1",
    "Figure 7.2",
    "Figure 7.2a",
    "Figure 7.2b",
    "Figure 7.3",
    "Source: original Alkahest fixture",
    "Tables and instructional blocks",
    "Table 8.1",
    "Measurement and acceptance plan",
    "Bench-test sequence",
    "Close the test session.",
    "Note 8.1",
    "Warning 8.1",
    "Optional extension: characterize drift",
    "Exercise 8.1",
    "Solution 8.1",
    "Project: build a threshold indicator",
    "Lab: verify the threshold indicator",
    "Learning components",
    "Learning objectives",
    "Prerequisites",
    "Review question: threshold evidence",
    "Operating-interval exercise",
    "Companion materials",
    "Half-adder Verilog source",
    "Half-adder truth-table dataset",
    "Half-adder logic schematic",
    "Half-adder bill of materials",
    "Half-adder project pack manifest",
    "Release package:",
    "9f5af146dd48",
    "Controlled content reuse",
    "Safety notice — disconnect before changing connections.",
    "Observed value",
    "Rights review notice.",
    "Worked example — tolerance interval.",
    "Project prerequisites.",
    "test fixture, verify that its supply reads zero",
    "a current-limited supply and multimeter",
    "Dependency boundary",
    "Semantic icons",
    "Table 12.1",
    "Initial semantic icon registry",
    "Equipment required.",
    "Check the stated limits before energizing the circuit.",
    "Do not continue while stored energy is present.",
    "Record raw observations before writing an interpretation.",
    "Optional material.",
    "Stop if the hazard remains.",
    "Accessibility and narrow reflow",
    "Icon meaning remains in visible text",
    "Glossary authoring contract",
    "Central process",
    "The entries below are generated from glossary.yml",
    "The hardware unit that fetches, decodes, and executes instructions",
    "A rectangular arrangement of values",
    "First use: p.",
    "central processing unit (CPU)",
    "central processing units",
    "CPUs",
    "instruction set architecture (ISA)",
    "matrices",
    "quantum bits (qubits)",
    "A useful footnote should not depend on the geometry of a printed page.",
    "Semantic notes remain in manuscript source order even when an edition moves their presentation.",
    "Subject index",
    "Name index",
    "processor architecture, see instruction set architecture",
    "technical publishing",
    "see also book design",
    "Turing, Alan",
    "see also computation",
    "Production reference",
    "Language reference",
    "print edition",
)

COMMON_BACKEND_MARKERS = (
    "programming example (Knuth 1984)",
    "Knuth, Donald E. 1984",
    "narrative form with Turing (1936)",
    "page locator (Turing 1936, 230–31)",
    "multiple sources (Turing 1936; Knuth 1984)",
    "author suppression with Turing (1936)",
    "Shannon, Claude E. 1948",
    "j.1538-7305.1948",
    "Figure A.1",
    "Table A.1",
    "Listing A.1",
    "Theorem A.1",
    "Note A.1",
    "Warning A.1",
    "Exercise A.1",
    "Solution A.1",
)

RECTO_MARKERS = (
    ("reference chapter", "This chapter begins the cross-format test corpus."),
    ("layout-stress chapter", "This chapter is a pagination stress specimen"),
    ("continuity chapter", "This follow-on chapter proves"),
    ("acceptance chapter", "This final layout chapter records"),
    (
        "code-block chapter",
        "This chapter defines how source code, terminal transcripts, patches",
    ),
    ("math chapter", "This chapter defines the shared authoring contract for mathematical"),
    ("figure chapter", "This chapter defines the shared contract for authored images"),
    (
        "component chapter",
        "Technical books need more than prose, code, mathematics, and figures.",
    ),
    ("controlled-reuse chapter", "Repeated prose should have one reviewable source"),
    ("icon chapter", "Technical books repeat a small visual vocabulary"),
    ("glossary chapter", "Technical books need one durable definition"),
    ("generated glossary", "The entries below are generated from glossary.yml"),
    ("generated index", "The subject and name indexes below are generated from index.yml"),
    ("appendix A", "This appendix makes the first appendix opener"),
    ("appendix B", "This second appendix proves"),
    ("appendix C", "This appendix exercises language metadata"),
)

FORBIDDEN_MARKERS = (
    ("1.1.1.1", "incorrectly numbers the H4 detail heading"),
    ("screen edition", "contains the screen-only figure variant"),
    ("Extended laboratory observations", "contains the online-only appendix"),
    ("Supplemental workbook", "contains the supplemental appendix"),
    (
        "internal editorial canary and must never appear in a public artifact",
        "contains private manuscript content",
    ),
    ("Answer key: threshold evidence", "contains private answer-key content"),
)


def command(name: str) -> str:
    """Resolve one required locked-toolchain command."""
    resolved = shutil.which(name)
    if resolved is None:
        raise ProfileError(f"{name} is required for PDF profile checks")
    return resolved


def run(arguments: list[str], *, text: bool = True) -> subprocess.CompletedProcess:
    """Run one resolved command and preserve its diagnostics for validation."""
    return subprocess.run(  # noqa: S603 - executables are resolved from a closed set
        arguments,
        cwd=ROOT,
        capture_output=True,
        text=text,
        check=False,
    )


def metadata(output: str, name: str) -> str:
    """Extract one pdfinfo metadata value."""
    prefix = f"{name}:"
    for line in output.splitlines():
        if line.startswith(prefix):
            return line[len(prefix) :].strip()
    raise ProfileError(f"pdfinfo did not report {name}")


def split_pages(output: str) -> list[str]:
    """Split Poppler layout text without inventing a trailing empty page."""
    pages = output.split("\f")
    if pages and not pages[-1]:
        pages.pop()
    return pages


def page_for(pages: list[str], marker: str) -> int | None:
    """Return the physical page containing a normalized marker."""
    for index, page in enumerate(pages, start=1):
        if marker in re.sub(r"\s+", " ", page):
            return index
    return None


def validate_pdfinfo(profile: Profile, path: Path) -> tuple[float, float, int]:
    """Validate document geometry and return its reported dimensions and pages."""
    result = run([command("pdfinfo"), str(path)])
    if result.returncode:
        raise ProfileError(f"pdfinfo could not inspect {profile.label}:\n{result.stderr}")
    for diagnostic in result.stderr.splitlines():
        if not diagnostic:
            continue
        allowed = (
            profile.label.startswith("Typst")
            and diagnostic == "Syntax Error: Suspects object is wrong type (boolean)"
        )
        if not allowed:
            raise ProfileError(
                f"pdfinfo reported an unexpected diagnostic for {profile.label}: {diagnostic}"
            )
    size = metadata(result.stdout, "Page size").split()
    try:
        width, height = float(size[0]), float(size[2])
        pages = int(metadata(result.stdout, "Pages"))
    except (IndexError, ValueError) as error:
        raise ProfileError(f"pdfinfo reported malformed metadata for {profile.label}") from error
    if abs(width - profile.width) > 0.1 or abs(height - profile.height) > 0.1:
        raise ProfileError(
            f"{profile.label} is {width:g} x {height:g} points; "
            f"expected {profile.width:g} x {profile.height:g}"
        )
    if pages < 30:
        raise ProfileError(
            f"{profile.label} has {pages} pages; the specimen must retain the Phase 2 minimum of 30"
        )
    return width, height, pages


def validate_bounding_boxes(profile: Profile, path: Path) -> None:
    """Reject positioned words that cross a physical page boundary."""
    with tempfile.TemporaryDirectory(prefix="alkahest-pdf-bbox-") as directory:
        destination = Path(directory) / "bbox.html"
        result = run([command("pdftotext"), "-bbox", str(path), str(destination)])
        if result.returncode:
            raise ProfileError(
                f"pdftotext could not extract positioned text from {profile.label}:\n"
                f"{result.stderr}"
            )
        diagnostics = [
            line for line in result.stderr.splitlines() if line and line != "no word list"
        ]
        if diagnostics:
            raise ProfileError(
                "positioned-text extraction reported an unexpected diagnostic for "
                f"{profile.label}: {diagnostics[0]}"
            )
        try:
            validate_text_contract("bbox", destination.read_text(encoding="utf-8"))
        except (OSError, UnicodeError, RuntimeError) as error:
            raise ProfileError(
                f"{profile.label} contains text outside the physical page: {error}"
            ) from error


def validate_fonts(profile: Profile, path: Path) -> None:
    """Require the selected families to be embedded and subset."""
    result = run([command("pdffonts"), str(path)])
    if result.returncode:
        raise ProfileError(f"pdffonts could not inspect {profile.label}:\n{result.stderr}")
    for line in result.stdout.splitlines()[2:]:
        fields = line.split()
        if fields and (len(fields) < 5 or fields[-5:-3] != ["yes", "yes"]):
            raise ProfileError(f"{profile.label} contains a font that is not embedded and subset")
    for font in REQUIRED_FONTS:
        if font not in result.stdout:
            raise ProfileError(f"{profile.label} does not embed selected face {font}")


def backend_markers(profile: Profile) -> tuple[str, ...]:
    """Return backend-specific reference strings."""
    if profile.label.startswith("Typst"):
        return (
            "A. Page-system checklist",
            "B. Format behavior",
            "A.2 - Numbered appendix elements",
            "Section 1.1 and Equation (1.1)",
            "Equation (1.1)",
            "Equation (6.3)",
            "Equation (A.1)",
        )
    return (
        "A Page-system checklist",
        "B Format behavior",
        "A.2 Numbered appendix elements",
        "Section 1.1 and Equation 1.1",
        "Equation 1.1",
        "Equation 6.3",
        "Equation A.1",
    )


def validate_text(profile: Profile, text: str) -> None:
    """Validate stable publication markers in reading-order text."""
    for marker in (*REQUIRED_MARKERS, *backend_markers(profile), *COMMON_BACKEND_MARKERS):
        if marker not in text:
            raise ProfileError(f"{profile.label} is missing required marker: {marker}")
    if "List of algorithms" in text:
        raise ProfileError(f"{profile.label} rendered the configured but empty algorithm list")
    for marker, message in FORBIDDEN_MARKERS:
        if marker in text:
            raise ProfileError(f"{profile.label} {message}")
    note = "A useful footnote should not depend on the geometry of a printed page."
    count = text.count(note)
    if count != 2:
        raise ProfileError(
            f"{profile.label} has {count} native occurrences of the reusable semantic note; "
            "expected 2"
        )
    try:
        validate_text_contract("index", text)
    except RuntimeError as error:
        raise ProfileError(
            f"{profile.label} does not retain the page-resolved index contract: {error}"
        ) from error
    references = len(re.findall(r"First use: p\. [0-9]+", text))
    if references != 4:
        raise ProfileError(
            f"{profile.label} has {references} generated glossary page references; expected 4"
        )


def validate_pages(profile: Profile, pages: list[str]) -> None:
    """Validate physical rectos, blanks, and pagination stress behavior."""
    for description, marker in RECTO_MARKERS:
        page = page_for(pages, marker)
        if page is None:
            raise ProfileError(
                f"{profile.label} is missing recto marker for {description}: {marker}"
            )
        if page % 2 == 0:
            raise ProfileError(
                f"{profile.label} places {description} on physical page {page}, a verso"
            )
    if len(pages) < 4 or re.sub(r"\s+", "", pages[3]):
        raise ProfileError(
            f"{profile.label} physical page 4 is not the required furniture-free blank verso"
        )

    split_found = False
    for boundary in (
        "Alpha",
        "Bravo",
        "Charlie",
        "Delta",
        "Echo",
        "Foxtrot",
        "Golf",
        "Hotel",
        "India",
        "Juliett",
        "Kilo",
        "Lima",
    ):
        start = page_for(pages, f"Boundary {boundary} begins")
        end = page_for(pages, f"Boundary {boundary} ends")
        if start is None or end is None:
            raise ProfileError(f"{profile.label} is missing Boundary {boundary} markers")
        if start != end:
            if end - start != 1:
                raise ProfileError(
                    f"{profile.label} splits Boundary {boundary} across more than two pages"
                )
            split_found = True
    if not split_found:
        raise ProfileError(f"{profile.label} does not exercise a cross-page boundary paragraph")

    if "6 x 9" in profile.label:
        table_pages = sum(
            "Step Operation Expected evidence" in re.sub(r"\s+", " ", page) for page in pages
        )
        if table_pages < 2:
            raise ProfileError(
                f"{profile.label} does not repeat the long-table header across compact pages"
            )


def check_profile(profile: Profile) -> None:
    """Validate one rendered profile."""
    path = ROOT / profile.path
    if not path.is_file():
        raise ProfileError(f"missing {profile.label}: {profile.path}")
    width, height, page_count = validate_pdfinfo(profile, path)
    validate_bounding_boxes(profile, path)
    validate_fonts(profile, path)

    layout = run([command("pdftotext"), "-layout", str(path), "-"])
    if layout.returncode:
        raise ProfileError(f"pdftotext could not extract {profile.label}:\n{layout.stderr}")
    pages = split_pages(layout.stdout)
    if len(pages) != page_count:
        raise ProfileError(
            f"{profile.label} yielded {len(pages)} extracted pages; expected {page_count}"
        )

    reading_order = run([command("pdftotext"), str(path), "-"])
    if reading_order.returncode:
        raise ProfileError(
            f"pdftotext could not extract reading order from {profile.label}:\n"
            f"{reading_order.stderr}"
        )
    validate_text(profile, normalize(reading_order.stdout, "pdf"))
    validate_pages(profile, pages)
    print(
        f"ok: {profile.label} ({width:g} x {height:g} points; {page_count} pages; "
        "physical containment, bidirectional appendix references, shared bibliography, "
        "appendix numbering, code/math/figure/rich-media/component/companion/reuse/icon/"
        "notice/glossary/semantic-note/index/generated-list contracts, fonts, language "
        "scripts, recto/blank-page policy, pagination stress, headings, and references "
        "verified)"
    )


def main() -> int:
    """Run preflight and every specimen-specific profile check."""
    for name in ("pdfinfo", "pdffonts", "pdfimages", "pdftotext", "verapdf"):
        command(name)
    preflight = run([sys.executable, "-m", "alkahest.checks.pdf_preflight"])
    if preflight.stdout:
        print(preflight.stdout, end="")
    if preflight.stderr:
        print(preflight.stderr, end="", file=sys.stderr)
    if preflight.returncode:
        return preflight.returncode
    try:
        for profile in PROFILES:
            check_profile(profile)
    except ProfileError as error:
        print(f"error: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
