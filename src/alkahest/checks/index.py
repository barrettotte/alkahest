"""Validate subject/person index identities, hierarchy, markers, ranges, and redirects."""

import os
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal, Never, NotRequired, TypedDict, cast

from alkahest.common import DataValue, load_yaml

ROOT = Path(__file__).resolve().parents[3]
SCALAR_FIELDS = {"term", "kind", "sort", "parent", "see"}
LIST_FIELDS = {"aliases", "locations", "ranges", "see-also"}
CALL_PATTERN = re.compile(r"\{\{<\s*alk-index\b(.*?)>\}\}")
type LocatorKey = tuple[str, str, str]


class IndexEntry(TypedDict):
    """One validated subject or person index entry."""

    term: str
    kind: str
    sort: NotRequired[str]
    parent: NotRequired[str]
    see: NotRequired[str]
    aliases: list[str]
    locations: list[str]
    ranges: list[str]
    see_also: list[str]


@dataclass
class DeclaredLocators:
    """Point and range locators declared by the registry."""

    points: set[LocatorKey] = field(default_factory=set)
    ranges: set[LocatorKey] = field(default_factory=set)


@dataclass
class ObservedMarkers:
    """Point and range markers observed in manuscript sources."""

    points: set[LocatorKey] = field(default_factory=set)
    edges: dict[LocatorKey, dict[str, int]] = field(default_factory=dict)
    aliases_used: set[str] = field(default_factory=set)
    placeholders: int = 0


def fail(message: str) -> Never:
    """Raise one index contract error."""
    raise RuntimeError(f"error: {message}")


def validate_entry(name: str, raw_entry: DataValue) -> IndexEntry:
    """Validate one index registry entry."""
    if not re.fullmatch(r"[a-z][a-z0-9-]*", name):
        fail(f"invalid index ID: {name}")
    if not isinstance(raw_entry, dict):
        fail(f"index entry {name} must be a mapping")

    unknown = set(raw_entry) - SCALAR_FIELDS - LIST_FIELDS
    if unknown:
        fail(f"index entry {name} has unsupported fields: {', '.join(sorted(map(str, unknown)))}")

    entry = dict(raw_entry)
    for scalar_field in SCALAR_FIELDS:
        if scalar_field in entry and not isinstance(entry[scalar_field], str):
            fail(f"index entry {name} {scalar_field} must be text")

    for list_field in LIST_FIELDS:
        values = entry.get(list_field, [])
        if not isinstance(values, list) or not all(isinstance(value, str) for value in values):
            fail(f"index entry {name} {list_field} must be a list of values")
        entry[list_field] = values

    entry["see_also"] = entry.pop("see-also")
    return cast(IndexEntry, entry)


def load_entries(root: Path) -> tuple[str, dict[str, IndexEntry]]:
    """Load and validate index registry structure."""
    registry = load_yaml(root / "index.yml", "index registry")
    unknown = set(registry) - {"version", "lang", "entries"}
    if unknown:
        fail(f"index registry has unsupported fields: {', '.join(sorted(map(str, unknown)))}")
    if registry.get("version") != 1:
        fail("index registry version must be 1")

    language = registry.get("lang")
    if not isinstance(language, str) or not re.fullmatch(r"[A-Za-z]{2,3}(?:-[A-Za-z0-9]{2,8})*", language):
        fail("index registry language must be a BCP 47 tag")

    raw_entries = registry.get("entries")
    if not isinstance(raw_entries, dict) or not raw_entries:
        fail("index registry has no entries")
    entries = {name: validate_entry(name, raw_entry) for name, raw_entry in raw_entries.items()}
    return language, entries


def build_lookup(entries: dict[str, IndexEntry]) -> dict[str, str]:
    """Validate entry metadata and build the alias lookup."""
    lookup = {name: name for name in entries}
    for name in sorted(entries):
        entry = entries[name]

        if not entry.get("term", "").strip():
            fail(f"index entry {name} has no term")
        if entry.get("kind") not in {"subject", "person"}:
            fail(f"index entry {name} has unsupported kind")
        if "sort" in entry and not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9 .,'-]*", entry["sort"]):
            fail(f"index entry {name} has invalid sort value")

        for list_field in ("aliases", "locations", "ranges", "see_also"):
            values = entry[list_field]
            if len(values) != len(set(values)):
                duplicate = next(value for value in values if values.count(value) > 1)
                fail(f"index entry {name} has duplicate {list_field} value {duplicate}")

        for alias in entry.get("aliases", []):
            if not re.fullmatch(r"[a-z][a-z0-9-]*", alias):
                fail(f"index entry {name} has invalid alias {alias}")
            if alias in lookup:
                fail(f"duplicate index name or alias: {alias}")
            lookup[alias] = name
    return lookup


def validate_relationships(entries: dict[str, IndexEntry]) -> dict[str, int]:
    """Validate hierarchy and redirects and count child entries."""
    child_count: dict[str, int] = {}
    for name in sorted(entries):
        entry = entries[name]
        parent = entry.get("parent")
        if parent:
            if not re.fullmatch(r"[a-z][a-z0-9-]*", parent) or parent not in entries or parent == name:
                fail(f"index entry {name} has invalid parent")
            if entry["kind"] != entries[parent]["kind"]:
                fail(f"index entry {name} and its parent have different kinds")
            child_count[parent] = child_count.get(parent, 0) + 1

        target = entry.get("see")
        if target:
            if not re.fullmatch(r"[a-z][a-z0-9-]*", target) or target not in entries or target == name:
                fail(f"index entry {name} has invalid see target")
            if any(entry[field] for field in ("locations", "ranges", "see_also")):
                fail(f"redirect index entry {name} cannot have locators, ranges, or see-also")

        for target in entry["see_also"]:
            if not re.fullmatch(r"[a-z][a-z0-9-]*", target) or target not in entries or target == name:
                fail(f"index entry {name} has invalid see-also target {target}")

    for relationship in ("parent", "see"):
        validate_cycles(entries, relationship)
    return child_count


def relationship_target(entry: IndexEntry, relationship: Literal["parent", "see"]) -> str | None:
    """Return one optional hierarchy or redirect target."""
    return entry.get("parent") if relationship == "parent" else entry.get("see")


def validate_cycles(entries: dict[str, IndexEntry], relationship: Literal["parent", "see"]) -> None:
    """Reject cycles in one index relationship."""
    for name in sorted(entries):
        visited: set[str] = set()
        cursor = name
        next_cursor = relationship_target(entries[cursor], relationship)
        while next_cursor:
            if cursor in visited:
                fail(f"index {relationship} cycle includes {cursor}")
            visited.add(cursor)
            cursor = next_cursor
            next_cursor = relationship_target(entries[cursor], relationship)


def declared_locators(root: Path, entries: dict[str, IndexEntry], child_count: dict[str, int]) -> DeclaredLocators:
    """Validate and collect locators declared by index entries."""
    declared = DeclaredLocators()
    for name in sorted(entries):
        entry = entries[name]
        for locator_kind, target in (("locations", declared.points), ("ranges", declared.ranges)):
            locators = entry["locations"] if locator_kind == "locations" else entry["ranges"]
            for locator in locators:
                match = re.fullmatch(r"((?:appendices/)?[a-z0-9][a-z0-9-]*\.qmd)#([a-z][a-z0-9-]*)", locator)
                if not match:
                    fail(f"index entry {name} has malformed {locator_kind} locator {locator}")

                source, marker = match.groups()
                if not (root / source).is_file():
                    fail(f"index locator source does not exist: {source}")

                key = (name, source, marker)
                if key in target:
                    fail(f"duplicate declared index locator {name} {source}#{marker}")
                target.add(key)

        if not entry.get("see") and not entry["locations"] and not entry["ranges"] and not child_count.get(name):
            fail(f"index entry {name} has no locator, range, child, or redirect")
    return declared


def record_marker(
    arguments: str,
    relative: str,
    number: int,
    lookup: dict[str, str],
    observed: ObservedMarkers,
) -> None:
    """Validate and record one manuscript index marker."""
    match = re.fullmatch(
        r"\s+([a-z][a-z0-9-]*)\s+id=([a-z][a-z0-9-]*)(?:\s+range=(start|end))?\s*",
        arguments,
    )
    if not match:
        fail(f"{relative}:{number}: malformed alk-index shortcode")
    requested, marker, edge = match.groups()
    if requested not in lookup:
        fail(f"{relative}:{number}: unknown index name or alias {requested}")

    canonical = lookup[requested]
    if requested != canonical:
        observed.aliases_used.add(requested)

    key = (canonical, relative, marker)
    if edge:
        edges = observed.edges.setdefault(key, {})
        if edges.get(edge):
            fail(f"duplicate index range {edge} marker for {canonical} {relative}#{marker}")
        edges[edge] = 1
    elif key in observed.points:
        fail(f"duplicate index point marker for {canonical} {relative}#{marker}")
    else:
        observed.points.add(key)


def scan_source(root: Path, source: Path, lookup: dict[str, str], observed: ObservedMarkers) -> None:
    """Collect index markers from one manuscript source."""
    relative = source.relative_to(root).as_posix()
    fence = ""
    for number, line in enumerate(source.read_text(encoding="utf-8").splitlines(), 1):
        if fence:
            if re.fullmatch(re.escape(fence) + r"\s*", line):
                fence = ""
            continue

        if opening := re.match(r"^(`{3,}|~{3,})", line):
            fence = opening.group(1)
            continue

        observed.placeholders += line.count("{.alkahest-index-placeholder}")
        if re.search(r"\\index\s*\{", line):
            fail(f"{relative}:{number}: use alk-index rather than a backend-specific index command")

        for call in CALL_PATTERN.finditer(line):
            record_marker(call.group(1), relative, number, lookup, observed)

        if "{{< alk-index" in line and not CALL_PATTERN.search(line):
            fail(f"{relative}:{number}: unterminated alk-index shortcode")


def observed_markers(root: Path, lookup: dict[str, str]) -> ObservedMarkers:
    """Collect index markers across manuscript sources."""
    observed = ObservedMarkers()
    sources = sorted(path for path in root.rglob("*.qmd") if ".quarto" not in path.parts and "_build" not in path.parts)
    for source in sources:
        scan_source(root, source, lookup, observed)
    return observed


def validate_marker_contract(declared: DeclaredLocators, observed: ObservedMarkers) -> None:
    """Match declared index locators to manuscript markers."""
    if observed.placeholders != 1:
        fail(f"expected exactly one index placeholder; found {observed.placeholders}")

    for key in sorted(declared.points - observed.points):
        fail("declared index point has no matching marker: " + " ".join(key))
    for key in sorted(observed.points - declared.points):
        fail("undeclared index point marker: " + " ".join(key))

    for key in sorted(declared.ranges):
        edges = observed.edges.get(key, {})
        if edges.get("start", 0) != 1 or edges.get("end", 0) != 1:
            fail("declared index range needs exactly one start and one end: " + " ".join(key))

    for key in sorted(set(observed.edges) - declared.ranges):
        fail("undeclared index range marker: " + " ".join(key))


def main() -> None:
    """Validate index identities, locators, and manuscript markers."""
    root = Path(os.environ.get("ALKAHEST_INDEX_BOOK_ROOT", ROOT / "book")).resolve()
    if not root.is_dir():
        fail("index book root does not exist")

    _language, entries = load_entries(root)
    lookup = build_lookup(entries)
    child_count = validate_relationships(entries)
    declared = declared_locators(root, entries, child_count)
    observed = observed_markers(root, lookup)
    validate_marker_contract(declared, observed)

    print(
        f"ok: subject/person indexes ({len(entries)} entries; {len(declared.points)} point markers; "
        f"{len(declared.ranges)} range; {len(observed.aliases_used)} aliases exercised; "
        "nested entries; see/see-also; one generated index)"
    )


if __name__ == "__main__":
    try:
        main()
    except (OSError, UnicodeError, RuntimeError) as error:
        print(error, file=sys.stderr)
        raise SystemExit(1) from None
