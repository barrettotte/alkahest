"""Validate subject/person index identities, hierarchy, markers, ranges, and redirects."""

import os
import re
import sys
from pathlib import Path
from typing import Any, Never

ROOT = Path(__file__).resolve().parents[3]


def fail(message: str) -> Never:
    raise RuntimeError(f"error: {message}")


def main():
    root = Path(os.environ.get("ALKAHEST_INDEX_BOOK_ROOT", ROOT / "book")).resolve()
    if not root.is_dir():
        fail("index book root does not exist")
    registry_path = root / "index.yml"
    version: int | None = None
    language: str | None = None
    in_entries = False
    current: str | None = None
    list_field: str | None = None
    entries: dict[str, dict[str, Any]] = {}
    for number, line in enumerate(registry_path.read_text(encoding="utf-8").splitlines(), 1):
        if re.match(r"^\s*(?:#.*)?$", line):
            continue
        match = re.fullmatch(r"version: ([0-9]+)", line)
        if match:
            if version is not None:
                fail(f"{registry_path}:{number}: duplicate version")
            version = int(match.group(1))
            continue
        match = re.fullmatch(r"lang: (\S+)", line)
        if match:
            if language is not None:
                fail(f"{registry_path}:{number}: duplicate language")
            language = match.group(1)
            continue
        if line == "entries:":
            in_entries, current, list_field = True, None, None
            continue
        match = re.fullmatch(r"  ([a-z][a-z0-9-]*):", line) if in_entries else None
        if match:
            current = match.group(1)
            if current in entries:
                fail(f"{registry_path}:{number}: duplicate index ID: {current}")
            entries[current] = {"line": number}
            list_field = None
            continue
        if not in_entries or current is None:
            fail(f"{registry_path}:{number}: field appears before an index ID")
        match = re.fullmatch(r"    (term|kind|sort|parent|see): (\S.*)", line)
        if match:
            field, value = match.groups()
            if field in entries[current]:
                fail(f"{registry_path}:{number}: duplicate {field} for {current}")
            entries[current][field] = value
            list_field = None
            continue
        match = re.fullmatch(r"    (aliases|locations|ranges|see-also):", line)
        if match:
            list_field = match.group(1)
            if list_field in entries[current]:
                fail(f"{registry_path}:{number}: duplicate {list_field} for {current}")
            entries[current][list_field] = []
            continue
        match = re.fullmatch(r"      - (\S.*)", line) if list_field else None
        if match:
            if list_field is None:
                fail(f"{registry_path}:{number}: list value appears before a list field")
            entries[current][list_field].append(match.group(1))
            continue
        fail(f"{registry_path}:{number}: unsupported index syntax: {line}")
    if version != 1:
        fail("index registry version must be 1")
    if not language or not re.fullmatch(r"[A-Za-z]{2,3}(?:-[A-Za-z0-9]{2,8})*", language):
        fail("index registry language must be a BCP 47 tag")
    if not entries:
        fail("index registry has no entries")
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
