"""Validate manuscript links, image alternatives, IDs, and cross-references."""

import os
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Never
from urllib.parse import unquote, urlsplit

ROOT = Path(__file__).resolve().parents[3]
ID_PATTERN = r"[A-Za-z][A-Za-z0-9_.:-]*"
CROSSREF_PREFIXES = {
    "alg",
    "ans",
    "cau",
    "cnj",
    "cor",
    "def",
    "eq",
    "exm",
    "exr",
    "fig",
    "hint",
    "imp",
    "lab",
    "lem",
    "lst",
    "nte",
    "obj",
    "plan",
    "pre",
    "project",
    "prp",
    "rem",
    "rev",
    "sec",
    "sol",
    "sum",
    "tbl",
    "thm",
    "tip",
    "wrn",
}
DIAGRAM_ENGINES = {"dot", "graphviz", "mermaid"}
IMAGE_PATTERN = re.compile(
    r"!\[([^]\n]*)\]\(\s*(<[^>\n]+>|(?:\\.|[^)\s])+)"
    r"(?:\s+(?:\"[^\"\n]*\"|'[^'\n]*'))?\s*\)(\{[^}\n]*\})?"
)
LINK_PATTERN = re.compile(
    r"(?<!!)\[([^]\n]+)\]\(\s*(<[^>\n]+>|(?:\\.|[^)\s])+)"
    r"(?:\s+(?:\"[^\"\n]*\"|'[^'\n]*'))?\s*\)"
)
INLINE_MATH_PATTERN = re.compile(r"(?<![$\\])\$(?!\$)(?:\\.|[^$\\\n])+(?<!\\)\$(?!\$)")
RAW_BACKEND_PATTERN = re.compile(r"\{=typst\}|```\{typst\}")
type Link = tuple[Path, int, str, str]
type Reference = tuple[Path, int, str]
type ScanResult = tuple[list[str], int, int, int, int, int, int]


@dataclass
class EditorialScan:
    """Accumulated editorial facts and diagnostics."""

    errors: list[str] = field(default_factory=list)
    identities: dict[str, tuple[Path, str]] = field(default_factory=dict)
    per_source_ids: dict[Path, set[str]] = field(default_factory=dict)
    links: list[Link] = field(default_factory=list)
    references: list[Reference] = field(default_factory=list)
    image_count: int = 0
    diagram_count: int = 0
    math_count: int = 0
    external_count: int = 0


@dataclass
class SourceState:
    """State for fenced blocks and display math in one source."""

    fence_char: str | None = None
    fence_length: int = 0
    diagram: str | None = None
    diagram_alt: bool = False
    diagram_line: int = 0
    display_math_line: int | None = None


def fail(errors: list[str]) -> Never:
    """Print editorial errors and terminate the check."""
    print("error: editorial integrity validation failed", file=sys.stderr)
    for error in errors:
        print(f"  {error}", file=sys.stderr)
    raise SystemExit(1)


def sources_below(root: Path) -> list[Path]:
    """Find manuscript sources below one book root."""
    return sorted(
        path.resolve() for path in root.rglob("*.qmd") if "_build" not in path.parts and ".quarto" not in path.parts
    )


def strip_inline_code(line: str) -> str:
    """Remove inline code before scanning prose syntax."""
    return re.sub(r"(`+)(.*?)\1", "", line)


def option_value(value: str) -> str:
    """Normalize a fenced-block option value."""
    value = value.strip()
    if len(value) >= 2 and value[0] == value[-1] and value[0] in {'"', "'"}:
        value = value[1:-1].strip()
    return value


def add_id(
    identities: dict[str, tuple[Path, str]],
    errors: list[str],
    identity: str,
    source: Path,
    line_number: int,
    root: Path,
) -> None:
    """Register one unique source identity."""
    location = f"{source.relative_to(root)}:{line_number}"
    if identity in identities:
        errors.append(f"{location}: duplicate ID '{identity}'; first declared at {identities[identity][1]}")
        return
    identities[identity] = (source, location)


def image_has_alternative(alt: str, attributes: str) -> bool:
    """Return whether an image declares an accessible alternative."""
    if alt.strip():
        return True
    fig_alt = re.search(r"""\bfig-alt\s*=\s*(["'])(.*?)\1""", attributes)
    if fig_alt and fig_alt.group(2).strip():
        return True
    return bool(
        re.search(r"(?:^|[\s{])\.decorative(?:[\s}]|$)", attributes)
        or re.search(r"""\brole\s*=\s*(["'])presentation\1""", attributes)
        or re.search(r"""\baria-hidden\s*=\s*(["'])true\1""", attributes)
    )


def record_ids(attributes: str, source: Path, line_number: int, root: Path, scan: EditorialScan) -> None:
    """Register hash-prefixed identities from attributes."""
    for match in re.finditer(rf"#({ID_PATTERN})", attributes):
        identity = match.group(1)
        add_id(scan.identities, scan.errors, identity, source, line_number, root)
        scan.per_source_ids[source].add(identity)


def scan_fenced_line(
    root: Path,
    source: Path,
    line_number: int,
    line: str,
    state: SourceState,
    scan: EditorialScan,
) -> bool:
    """Consume one line while inside a fenced block."""
    if state.fence_char is None:
        return False
    if re.fullmatch(rf"\s*{re.escape(state.fence_char)}{{{state.fence_length},}}\s*", line):
        if state.diagram and not state.diagram_alt:
            scan.errors.append(
                f"{source.relative_to(root)}:{state.diagram_line}: {state.diagram} "
                "diagram needs a nonempty fig-alt option"
            )
        state.fence_char = None
        state.diagram = None
        return True
    if state.diagram:
        option = re.match(r"\s*(?:#|//|%%)\|\s*(label|fig-alt):\s*(.*?)\s*$", line)
        if option and option.group(1) == "label":
            identity = option_value(option.group(2))
            if re.fullmatch(ID_PATTERN, identity):
                add_id(scan.identities, scan.errors, identity, source, line_number, root)
                scan.per_source_ids[source].add(identity)
        elif option and option.group(1) == "fig-alt":
            state.diagram_alt = bool(option_value(option.group(2)))
    return True


def scan_display_math_line(
    root: Path,
    source: Path,
    line_number: int,
    line: str,
    state: SourceState,
    scan: EditorialScan,
) -> bool:
    """Consume one line while inside display math."""
    if state.display_math_line is None:
        return False
    if closing := re.fullmatch(r"\s*\$\$\s*(\{[^}\n]*\})?\s*", line):
        attributes = closing.group(1) or ""
        record_ids(attributes, source, line_number, root, scan)
        alt = re.search(r"""\balt\s*=\s*(["'])(.*?)\1""", attributes)
        if not alt or not alt.group(2).strip():
            scan.errors.append(
                f"{source.relative_to(root)}:{state.display_math_line}: display math needs nonempty alt text"
            )
        scan.math_count += 1
        state.display_math_line = None
    return True


def open_fence(
    root: Path,
    source: Path,
    line_number: int,
    line: str,
    state: SourceState,
    scan: EditorialScan,
) -> bool:
    """Open and record one fenced block."""
    opening = re.match(r"^\s*(`{3,}|~{3,})(.*)$", line)
    if not opening:
        return False
    marker, info = opening.groups()
    state.fence_char = marker[0]
    state.fence_length = len(marker)
    engine = re.search(r"\{([A-Za-z0-9_-]+)", info)
    state.diagram = engine.group(1).lower() if engine and engine.group(1).lower() in DIAGRAM_ENGINES else None
    inline_alt = re.search(r"""\bfig-alt\s*=\s*(["'])(.*?)\1""", info)
    state.diagram_alt = bool(inline_alt and inline_alt.group(2).strip())
    state.diagram_line = line_number
    if state.diagram:
        scan.diagram_count += 1
    record_ids(info, source, line_number, root, scan)
    return True


def scan_inline_math(root: Path, source: Path, line_number: int, visible: str, scan: EditorialScan) -> None:
    """Validate inline math alternatives on one visible line."""
    for math in INLINE_MATH_PATTERN.finditer(visible):
        annotation = (
            re.match(r"\]\{([^}\n]*)\}", visible[math.end() :])
            if math.start() > 0 and visible[math.start() - 1] == "["
            else None
        )
        attributes = annotation.group(1) if annotation else ""
        alt = re.search(r"""\balt\s*=\s*(["'])(.*?)\1""", attributes)
        if not re.search(r"(?:^|\s)\.alkahest-math-alt(?:\s|$)", attributes) or not alt or not alt.group(2).strip():
            scan.errors.append(
                f"{source.relative_to(root)}:{line_number}: inline math "
                "needs an .alkahest-math-alt span with nonempty alt text"
            )
        scan.math_count += 1


def scan_visible_ids(root: Path, source: Path, line_number: int, visible: str, scan: EditorialScan) -> None:
    """Register identities from one visible source line."""
    for attribute_match in re.finditer(r"\{([^}\n]*)\}", visible):
        record_ids(attribute_match.group(1), source, line_number, root, scan)
    for match in re.finditer(rf"""\bid\s*=\s*["']({ID_PATTERN})["']""", visible):
        identity = match.group(1)
        add_id(scan.identities, scan.errors, identity, source, line_number, root)
        scan.per_source_ids[source].add(identity)


def scan_visible_links(root: Path, source: Path, line_number: int, visible: str, scan: EditorialScan) -> None:
    """Collect images and links from one visible source line."""
    for image in IMAGE_PATTERN.finditer(visible):
        scan.image_count += 1
        image_alt, target, image_attributes = image.groups()
        if not image_has_alternative(image_alt, image_attributes or ""):
            scan.errors.append(
                f"{source.relative_to(root)}:{line_number}: image '{target}' "
                "needs nonempty alt text, fig-alt, or .decorative"
            )
        scan.links.append((source, line_number, target, "image"))
    without_images = IMAGE_PATTERN.sub("", visible)
    scan.links.extend((source, line_number, link.group(2), "link") for link in LINK_PATTERN.finditer(without_images))


def scan_reference_calls(source: Path, line_number: int, visible: str, scan: EditorialScan) -> None:
    """Collect cross-reference calls from one visible source line."""
    reference_line = re.sub(r"https?://\S+", "", visible)
    reference_line = re.sub(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+", "", reference_line)
    scan.references.extend(
        (source, line_number, match.group(1))
        for match in re.finditer(rf"(?<![A-Za-z0-9_])@({ID_PATTERN})", reference_line)
    )


def scan_source(root: Path, source: Path, scan: EditorialScan) -> None:
    """Scan one manuscript source for editorial facts."""
    content = source.read_text(encoding="utf-8")
    if RAW_BACKEND_PATTERN.search(content):
        scan.errors.append(f"{source.relative_to(root)}: manuscript source must remain backend-neutral")
    state = SourceState()
    for line_number, line in enumerate(content.splitlines(), 1):
        if scan_fenced_line(root, source, line_number, line, state, scan):
            continue
        if scan_display_math_line(root, source, line_number, line, state, scan):
            continue
        if re.fullmatch(r"\s*\$\$\s*", line):
            state.display_math_line = line_number
            continue
        if open_fence(root, source, line_number, line, state, scan):
            continue
        visible = strip_inline_code(line)
        scan_inline_math(root, source, line_number, visible, scan)
        scan_visible_ids(root, source, line_number, visible, scan)
        scan_visible_links(root, source, line_number, visible, scan)
        scan_reference_calls(source, line_number, visible, scan)
    if state.fence_char:
        scan.errors.append(f"{source.relative_to(root)}: unclosed fenced block")
    if state.display_math_line is not None:
        scan.errors.append(f"{source.relative_to(root)}:{state.display_math_line}: unclosed display math")


def validate_links(root: Path, sources: list[Path], scan: EditorialScan) -> None:
    """Validate collected local links and fragments."""
    source_set = set(sources)
    for source, line_number, raw_target, kind in scan.links:
        target = raw_target[1:-1] if raw_target.startswith("<") else raw_target
        parsed = urlsplit(target.replace("\\ ", " "))
        if parsed.scheme or parsed.netloc or target.startswith("//"):
            scan.external_count += 1
            continue

        path_value = unquote(parsed.path)
        if path_value.startswith("/"):
            resolved = root.joinpath(*filter(None, path_value.split("/")))
        elif path_value:
            resolved = source.parent / path_value
        else:
            resolved = source

        resolved = resolved.resolve()
        try:
            resolved.relative_to(root)
        except ValueError:
            scan.errors.append(
                f"{source.relative_to(root)}:{line_number}: {kind} target '{raw_target}' escapes the book root"
            )
            continue

        if not resolved.exists():
            html_source = resolved.with_suffix(".qmd") if resolved.suffix == ".html" else None
            if html_source and html_source in source_set:
                resolved = html_source
            else:
                scan.errors.append(
                    f"{source.relative_to(root)}:{line_number}: {kind} target '{raw_target}' does not exist"
                )
                continue

        fragment = unquote(parsed.fragment)
        if fragment and resolved in source_set and fragment not in scan.per_source_ids[resolved]:
            scan.errors.append(
                f"{source.relative_to(root)}:{line_number}: link fragment "
                f"'#{fragment}' is not declared in {resolved.relative_to(root)}"
            )


def validate_references(root: Path, scan: EditorialScan) -> None:
    """Validate collected cross-reference calls."""
    for source, line_number, raw_reference in scan.references:
        reference = raw_reference
        if reference not in scan.identities:
            reference = reference.rstrip(".,;:!?")
        prefix = reference.split("-", 1)[0]
        if prefix in CROSSREF_PREFIXES and reference not in scan.identities:
            scan.errors.append(f"{source.relative_to(root)}:{line_number}: dangling cross-reference '@{reference}'")


def scan_sources(root: Path, sources: list[Path]) -> ScanResult:
    """Scan manuscript sources and summarize editorial integrity."""
    scan = EditorialScan(per_source_ids={source: set() for source in sources})
    for source in sources:
        scan_source(root, source, scan)
    validate_links(root, sources, scan)
    validate_references(root, scan)

    return (
        scan.errors,
        len(scan.identities),
        len(scan.links),
        scan.image_count,
        scan.diagram_count,
        scan.math_count,
        scan.external_count,
    )


def main() -> None:
    """Validate editorial integrity for the selected book root."""
    root = Path(os.environ.get("ALKAHEST_EDITORIAL_BOOK_ROOT", ROOT / "book")).resolve()
    if not root.is_dir():
        raise RuntimeError("error: editorial book root does not exist")

    sources = sources_below(root)
    if not sources:
        raise RuntimeError("error: editorial book root contains no .qmd sources")

    errors, identities, links, images, diagrams, math, external = scan_sources(root, sources)
    if errors:
        fail(errors)

    print(
        "ok: editorial source integrity "
        f"({len(sources)} sources; {links} local/external targets; "
        f"{images} images; {diagrams} diagrams; {math} math expressions; "
        f"{identities} unique IDs; "
        f"{external} external targets skipped offline)"
    )


if __name__ == "__main__":
    try:
        main()
    except (OSError, RuntimeError, UnicodeError) as error:
        print(error, file=sys.stderr)
        raise SystemExit(1) from None
