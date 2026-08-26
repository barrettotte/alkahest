"""Validate subject/person index identities, hierarchy, markers, ranges, and redirects."""

import os
import re
import sys
from pathlib import Path
from typing import Any, Never

from alkahest.common import load_yaml

ROOT = Path(__file__).resolve().parents[3]


def fail(message: str) -> Never:
    raise RuntimeError(f"error: {message}")


def main():
    root = Path(os.environ.get("ALKAHEST_INDEX_BOOK_ROOT", ROOT / "book")).resolve()
    if not root.is_dir():
        fail("index book root does not exist")
    registry_path = root / "index.yml"
    registry = load_yaml(registry_path, "index registry")
    unknown = set(registry) - {"version", "lang", "entries"}
    if unknown:
        fail(f"index registry has unsupported fields: {', '.join(sorted(map(str, unknown)))}")
    if registry.get("version") != 1:
        fail("index registry version must be 1")
    language = registry.get("lang")
    if not isinstance(language, str) or not re.fullmatch(
        r"[A-Za-z]{2,3}(?:-[A-Za-z0-9]{2,8})*", language
    ):
        fail("index registry language must be a BCP 47 tag")
    raw_entries = registry.get("entries")
    if not isinstance(raw_entries, dict) or not raw_entries:
        fail("index registry has no entries")
    entries: dict[str, dict[str, Any]] = {}
    scalar_fields = {"term", "kind", "sort", "parent", "see"}
    list_fields = {"aliases", "locations", "ranges", "see-also"}
    for name, raw_entry in raw_entries.items():
        if not isinstance(name, str) or not re.fullmatch(r"[a-z][a-z0-9-]*", name):
            fail(f"invalid index ID: {name}")
        if not isinstance(raw_entry, dict):
            fail(f"index entry {name} must be a mapping")
        unknown = set(raw_entry) - scalar_fields - list_fields
        if unknown:
            fail(
                f"index entry {name} has unsupported fields: {', '.join(sorted(map(str, unknown)))}"
            )
        entry = dict(raw_entry)
        for field in scalar_fields:
            if field in entry and not isinstance(entry[field], str):
                fail(f"index entry {name} {field} must be text")
        for field in list_fields:
            values = entry.get(field, [])
            if not isinstance(values, list) or not all(isinstance(value, str) for value in values):
                fail(f"index entry {name} {field} must be a list of values")
            entry[field] = values
        entries[name] = entry
    lookup = {name: name for name in entries}
    child_count: dict[str, int] = {}
    for name in sorted(entries):
        entry = entries[name]
        if not entry.get("term", "").strip():
            fail(f"index entry {name} has no term")
        if entry.get("kind") not in {"subject", "person"}:
            fail(f"index entry {name} has unsupported kind")
        if "sort" in entry and not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9 .,'-]*", entry["sort"]):
            fail(f"index entry {name} has invalid sort value")
        for field in ("aliases", "locations", "ranges", "see-also"):
            values = entry.get(field, [])
            if len(values) != len(set(values)):
                duplicate = next(value for value in values if values.count(value) > 1)
                fail(f"index entry {name} has duplicate {field} value {duplicate}")
        for alias in entry.get("aliases", []):
            if not re.fullmatch(r"[a-z][a-z0-9-]*", alias):
                fail(f"index entry {name} has invalid alias {alias}")
            if alias in lookup:
                fail(f"duplicate index name or alias: {alias}")
            lookup[alias] = name
    for name in sorted(entries):
        entry = entries[name]
        parent = entry.get("parent")
        if parent:
            if (
                not re.fullmatch(r"[a-z][a-z0-9-]*", parent)
                or parent not in entries
                or parent == name
            ):
                fail(f"index entry {name} has invalid parent")
            if entry["kind"] != entries[parent]["kind"]:
                fail(f"index entry {name} and its parent have different kinds")
            child_count[parent] = child_count.get(parent, 0) + 1
        target = entry.get("see")
        if target:
            if (
                not re.fullmatch(r"[a-z][a-z0-9-]*", target)
                or target not in entries
                or target == name
            ):
                fail(f"index entry {name} has invalid see target")
            if any(entry.get(field, []) for field in ("locations", "ranges", "see-also")):
                fail(f"redirect index entry {name} cannot have locators, ranges, or see-also")
        for target in entry.get("see-also", []):
            if (
                not re.fullmatch(r"[a-z][a-z0-9-]*", target)
                or target not in entries
                or target == name
            ):
                fail(f"index entry {name} has invalid see-also target {target}")
    for field in ("parent", "see"):
        for name in sorted(entries):
            visited, cursor = set(), name
            while entries[cursor].get(field):
                if cursor in visited:
                    fail(f"index {field} cycle includes {cursor}")
                visited.add(cursor)
                cursor = entries[cursor][field]
    expected_points: set[tuple[str, str, str]] = set()
    expected_ranges: set[tuple[str, str, str]] = set()
    for name in sorted(entries):
        entry = entries[name]
        for field, target in (("locations", expected_points), ("ranges", expected_ranges)):
            for locator in entry.get(field, []):
                match = re.fullmatch(
                    r"((?:appendices/)?[a-z0-9][a-z0-9-]*\.qmd)#([a-z][a-z0-9-]*)", locator
                )
                if not match:
                    fail(f"index entry {name} has malformed {field} locator {locator}")
                source, marker = match.groups()
                if not (root / source).is_file():
                    fail(f"index locator source does not exist: {source}")
                key = (name, source, marker)
                if key in target:
                    fail(f"duplicate declared index locator {name} {source}#{marker}")
                target.add(key)
        if (
            not entry.get("see")
            and not entry.get("locations")
            and not entry.get("ranges")
            and not child_count.get(name)
        ):
            fail(f"index entry {name} has no locator, range, child, or redirect")
    observed_points: set[tuple[str, str, str]] = set()
    observed_edges: dict[tuple[str, str, str], dict[str, int]] = {}
    aliases_used: set[str] = set()
    placeholders = 0
    call_pattern = re.compile(r"\{\{<\s*alk-index\b(.*?)>\}\}")
    for source in sorted(
        path
        for path in root.rglob("*.qmd")
        if ".quarto" not in path.parts and "_build" not in path.parts
    ):
        relative = source.relative_to(root).as_posix()
        fence = ""
        for number, line in enumerate(source.read_text(encoding="utf-8").splitlines(), 1):
            if fence:
                if re.fullmatch(re.escape(fence) + r"\s*", line):
                    fence = ""
                continue
            opening = re.match(r"^(`{3,}|~{3,})", line)
            if opening:
                fence = opening.group(1)
                continue
            placeholders += line.count("{.alkahest-index-placeholder}")
            if re.search(r"\\index\s*\{", line):
                fail(
                    f"{relative}:{number}: use alk-index rather than a backend-specific index command"
                )
            for call in call_pattern.finditer(line):
                match = re.fullmatch(
                    r"\s+([a-z][a-z0-9-]*)\s+id=([a-z][a-z0-9-]*)(?:\s+range=(start|end))?\s*",
                    call.group(1),
                )
                if not match:
                    fail(f"{relative}:{number}: malformed alk-index shortcode")
                requested, marker, edge = match.groups()
                if requested not in lookup:
                    fail(f"{relative}:{number}: unknown index name or alias {requested}")
                canonical = lookup[requested]
                if requested != canonical:
                    aliases_used.add(requested)
                key = (canonical, relative, marker)
                if edge:
                    edges = observed_edges.setdefault(key, {})
                    if edges.get(edge):
                        fail(
                            f"duplicate index range {edge} marker for {canonical} {relative}#{marker}"
                        )
                    edges[edge] = 1
                else:
                    if key in observed_points:
                        fail(f"duplicate index point marker for {canonical} {relative}#{marker}")
                    observed_points.add(key)
            if "{{< alk-index" in line and not call_pattern.search(line):
                fail(f"{relative}:{number}: unterminated alk-index shortcode")
    if placeholders != 1:
        fail(f"expected exactly one index placeholder; found {placeholders}")
    for key in sorted(expected_points - observed_points):
        fail("declared index point has no matching marker: " + " ".join(key))
    for key in sorted(observed_points - expected_points):
        fail("undeclared index point marker: " + " ".join(key))
    for key in sorted(expected_ranges):
        edges = observed_edges.get(key, {})
        if edges.get("start", 0) != 1 or edges.get("end", 0) != 1:
            fail("declared index range needs exactly one start and one end: " + " ".join(key))
    for key in sorted(set(observed_edges) - expected_ranges):
        fail("undeclared index range marker: " + " ".join(key))
    print(
        f"ok: subject/person indexes ({len(entries)} entries; {len(expected_points)} point markers; {len(expected_ranges)} range; {len(aliases_used)} aliases exercised; nested entries; see/see-also; one generated index)"
    )


if __name__ == "__main__":
    try:
        main()
    except (OSError, UnicodeError, RuntimeError) as error:
        print(error, file=sys.stderr)
        raise SystemExit(1) from None
