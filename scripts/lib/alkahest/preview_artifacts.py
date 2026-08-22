"""Validate rendered preview products without requiring full-book artifacts."""

import re
import subprocess
import zipfile
from pathlib import Path

from .common import fail, load_json
from .editions import edition_source_ids, load_editions


PREVIEW_DESCRIPTION = (
    "A two-chapter preview of Alkahest Reference Book for evaluating the book "
    "before the full edition is published."
)
PREVIEW_UUID = "urn:uuid:551be2aa-8be0-4078-b9dc-3f29e1088092"
LINKS_PENDING = (
    "Full-edition and purchase links will appear here when publication URLs "
    "are assigned."
)
PRIVATE_CANARIES = (
    "internal editorial canary and must never appear in a public artifact",
    "Answer key: threshold evidence",
)


def _source_record(book_root, source_id, source):
    text = (book_root / source["path"]).read_text(encoding="utf-8")
    heading = re.search(r"^#\s+(.+?)(?:\s+\{([^}]*)\})?\s*$", text, re.MULTILINE)
    if heading is None:
        fail(f"edition source '{source_id}' has no level-one heading")
    identifier = re.search(r"#([A-Za-z][\w:.-]*)", heading.group(2) or "")
    if identifier is None:
        fail(f"edition source '{source_id}' has no explicit heading ID")
    return {
        "source_id": source_id,
        "path": source["path"],
        "title": heading.group(1).strip(),
        "identifier": identifier.group(1),
        "private": source["availability"] == "private",
    }


def preview_inventory(root):
    """Derive selected and omitted source identities from the canonical manifest."""
    book_root = Path(root) / "book"
    registry = load_editions(book_root / "editions.json")
    selected_ids = set(edition_source_ids(registry, "preview"))
    selected, omitted = [], []
    for source_id, source in registry["sources"].items():
        record = _source_record(book_root, source_id, source)
        (selected if source_id in selected_ids else omitted).append(record)
    assets = load_json(book_root / "assets.json", "asset registry")
    patterns = assets.get("artifact_contract", {}).get(
        "forbidden_content_patterns", []
    )
    return {
        "selected": selected,
        "omitted": omitted,
        "forbidden_patterns": patterns,
    }


def _run(command, label):
    try:
        result = subprocess.run(
            command, check=True, capture_output=True, text=True, encoding="utf-8"
        )
    except (OSError, subprocess.CalledProcessError) as error:
        fail(f"cannot inspect preview {label}: {error}")
    return result.stdout


def _read_text_tree(root):
    chunks = []
    for path in sorted(root.rglob("*")):
        if path.is_file():
            try:
                chunks.append(path.read_text(encoding="utf-8"))
            except (UnicodeDecodeError, OSError):
                continue
    return "\n".join(chunks)


def collect_preview_artifacts(root):
    """Collect a normalized snapshot from all three rendered preview formats."""
    root = Path(root)
    preview_root = root / "book/_build/smoke/editions/preview"
    html_root = preview_root / "html"
    epub_path = preview_root / "epub/Alkahest-Reference-Book.epub"
    pdf_path = preview_root / "typst/Alkahest-Reference-Book.pdf"
    typ_path = preview_root / "typst/Alkahest-Reference-Book.typ"
    for path, label in (
        (html_root, "HTML directory"),
        (epub_path, "EPUB"),
        (pdf_path, "PDF"),
        (typ_path, "Typst source"),
    ):
        if not path.exists():
            fail(f"preview {label} is missing: {path.relative_to(root)}")

    html_entries = {
        path.relative_to(html_root).as_posix()
        for path in html_root.rglob("*")
        if path.is_file()
    }
    html_pages = {name for name in html_entries if name.endswith(".html")}

    try:
        with zipfile.ZipFile(epub_path) as archive:
            epub_entries = set(archive.namelist())
            epub_text = "\n".join(
                archive.read(name).decode("utf-8", errors="replace")
                for name in sorted(epub_entries)
                if name.endswith((".xhtml", ".opf", ".ncx", ".css", ".xml"))
            )
            epub_nav = archive.read("EPUB/nav.xhtml").decode("utf-8")
            epub_opf = archive.read("EPUB/content.opf").decode("utf-8")
    except (OSError, KeyError, zipfile.BadZipFile) as error:
        fail(f"cannot inspect preview EPUB: {error}")

    return {
        **preview_inventory(root),
        "html_entries": html_entries,
        "html_pages": html_pages,
        "html_text": _read_text_tree(html_root),
        "epub_entries": epub_entries,
        "epub_text": epub_text,
        "epub_nav": epub_nav,
        "epub_opf": epub_opf,
        "pdf_text": _run(["pdftotext", "-layout", str(pdf_path), "-"], "PDF text"),
        "pdf_info": _run(["pdfinfo", str(pdf_path)], "PDF metadata"),
        "pdf_fonts": _run(["pdffonts", str(pdf_path)], "PDF fonts"),
        "typ_text": typ_path.read_text(encoding="utf-8"),
    }


def _require(text, marker, label):
    if marker not in text:
        fail(f"preview {label} is missing {marker!r}")


def _reject(text, marker, label):
    if marker in text:
        fail(f"preview {label} exposes forbidden marker {marker!r}")


def _pdf_metadata(text):
    result = {}
    for line in text.splitlines():
        if ":" in line:
            key, value = line.split(":", 1)
            result[key.strip()] = value.strip()
    return result


def validate_preview_artifacts(snapshot):
    """Enforce preview selection, privacy, metadata, and navigation contracts."""
    selected = snapshot["selected"]
    omitted = snapshot["omitted"]
    expected_pages = {str(Path(item["path"]).with_suffix(".html")) for item in selected}
    actual_pages = set(snapshot["html_pages"])
    if actual_pages != expected_pages:
        missing = sorted(expected_pages - actual_pages)
        extra = sorted(actual_pages - expected_pages)
        fail(f"preview HTML page allowlist differs (missing={missing}, extra={extra})")

    chapter_entries = {
        name
        for name in snapshot["epub_entries"]
        if re.fullmatch(r"EPUB/text/ch\d+\.xhtml", name)
    }
    if len(chapter_entries) != len(selected):
        fail(
            "preview EPUB chapter count differs from source allowlist "
            f"({len(chapter_entries)} != {len(selected)})"
        )

    for item in selected:
        marker = item["identifier"]
        _require(snapshot["html_text"], marker, f"HTML selected source {item['source_id']}")
        _require(snapshot["epub_text"], marker, f"EPUB selected source {item['source_id']}")
        _require(snapshot["epub_nav"], marker, f"EPUB navigation for {item['source_id']}")
        _require(snapshot["pdf_text"], item["title"], f"PDF selected source {item['source_id']}")

    combined = "\n".join(
        (
            snapshot["html_text"],
            snapshot["epub_text"],
            snapshot["pdf_text"],
            snapshot["typ_text"],
        )
    )
    for item in omitted:
        _reject(combined, item["identifier"], f"artifact content from omitted source {item['source_id']}")
    for canary in PRIVATE_CANARIES:
        _reject(combined, canary, "private content")

    all_entries = set(snapshot["html_entries"]) | set(snapshot["epub_entries"])
    omitted_basenames = {Path(item["path"]).stem for item in omitted if item["private"]}
    for name in sorted(all_entries):
        parts = Path(name).parts
        if "private" in parts or any(stem in Path(name).stem for stem in omitted_basenames):
            fail(f"preview artifact contains private path '{name}'")

    for entry in snapshot["forbidden_patterns"]:
        label = entry.get("label", "unnamed content pattern")
        pattern = entry.get("pattern", "")
        try:
            match = re.search(pattern, combined)
        except re.error as error:
            fail(f"invalid forbidden-content pattern '{label}': {error}")
        if match:
            fail(f"preview artifacts match forbidden content pattern '{label}'")

    html = snapshot["html_text"]
    for marker in (
        PREVIEW_DESCRIPTION,
        "alkahest-preview-notice",
        "alkahest-preview-watermark",
        'data-full-edition-link="unassigned"',
        'data-purchase-link="unassigned"',
        LINKS_PENDING,
        "Preview chapters",
        "Preview reference",
        'role="doc-biblioref"',
        "ref-turing1936",
        "ref-knuth1984",
        'href="appendices/page-system-checklist.html#sec-appendix-numbering"',
        'href="../reference.html#sec-heading-hierarchy"',
        'href="../reference.html#eq-ohms-law"',
    ):
        _require(html, marker, "HTML contract")

    epub = snapshot["epub_text"]
    for marker in (
        PREVIEW_UUID,
        PREVIEW_DESCRIPTION,
        "alkahest-preview-notice",
        "alkahest-preview-watermark",
        LINKS_PENDING,
        "ref-turing1936",
        "ref-knuth1984",
        'href="ch007.xhtml#sec-appendix-numbering"',
        'href="ch002.xhtml#sec-heading-hierarchy"',
        'href="ch002.xhtml#eq-ohms-law"',
    ):
        _require(epub, marker, "EPUB contract")
    for marker in ("<dc:language>en-US</dc:language>", "<h1 id=\"toc-title\">Contents</h1>"):
        _require(snapshot["epub_opf"] + snapshot["epub_nav"], marker, "EPUB metadata/navigation")

    pdf = " ".join(snapshot["pdf_text"].split())
    for marker in (
        "Contents",
        "Preview chapters",
        "Preview reference",
        LINKS_PENDING,
        "Turing 1936",
        "Knuth 1984",
        "chapter-to-appendix route reaches",
        "appendix-to-chapter route returns",
    ):
        _require(pdf, marker, "PDF contract")
    info = _pdf_metadata(snapshot["pdf_info"])
    if info.get("Subject") != PREVIEW_DESCRIPTION:
        fail("preview PDF Subject does not match preview description")
    if info.get("Page size") != "504 x 720 pts":
        fail(f"preview PDF trim is not 7 x 10 inches: {info.get('Page size', 'missing')}")
    for key, value in (("Tagged", "yes"), ("JavaScript", "no"), ("Encrypted", "no")):
        if info.get(key) != value:
            fail(f"preview PDF {key} must be {value}")
    try:
        if int(info.get("Pages", "0")) < 1:
            fail("preview PDF has no pages")
    except ValueError:
        fail("preview PDF page count is invalid")

    font_rows = [
        line
        for line in snapshot["pdf_fonts"].splitlines()[2:]
        if line.strip() and not set(line.strip()) <= {"-"}
    ]
    if len(font_rows) < 5:
        fail("preview PDF does not report the expected embedded font stack")
    for row in font_rows:
        if re.search(r"\byes\s+yes\s+yes\b", row) is None:
            fail(f"preview PDF font is not embedded, subset, and Unicode mapped: {row}")

    for marker in ('fill: rgb("#33415518")', ")[PREVIEW]"):
        _require(snapshot["typ_text"], marker, "PDF watermark source")
    for marker in ("example.invalid", 'class="alkahest-preview-purchase"'):
        _reject(combined, marker, "unassigned preview links")

    return {
        "sources": len(selected),
        "html_pages": len(actual_pages),
        "epub_chapters": len(chapter_entries),
        "pdf_pages": int(info["Pages"]),
        "fonts": len(font_rows),
    }
