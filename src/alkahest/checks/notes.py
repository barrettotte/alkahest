"""Validate semantic note identities, definitions, sources, repeats, and apparatus."""

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
    root = Path(os.environ.get("ALKAHEST_NOTES_BOOK_ROOT", ROOT / "book")).resolve()
    if not root.is_dir():
        fail("notes book root does not exist")
    registry_path = root / "notes.yml"
    registry = load_yaml(registry_path, "notes registry")
    unknown = set(registry) - {"version", "order", "notes"}
    if unknown:
        fail(f"notes registry has unsupported fields: {', '.join(sorted(map(str, unknown)))}")
    if registry.get("version") != 1:
        fail("notes registry version must be 1")
    raw_order = registry.get("order")
    if not isinstance(raw_order, list) or not all(isinstance(name, str) for name in raw_order):
        fail("notes order must be a list of note IDs")
    order: list[str] = raw_order
    raw_entries = registry.get("notes")
    if not isinstance(raw_entries, dict):
        fail("notes registry notes must be a mapping")
    entries: dict[str, dict[str, Any]] = {}
    order_seen: set[str] = set()
    if not order:
        fail("notes registry has no ordered notes")
    for name in order:
        if not re.fullmatch(r"[a-z][a-z0-9-]*", name):
            fail(f"invalid note ID in order: {name}")
        if name in order_seen:
            fail(f"duplicate note in order: {name}")
        order_seen.add(name)
    for name, raw_entry in raw_entries.items():
        if not isinstance(name, str) or not re.fullmatch(r"[a-z][a-z0-9-]*", name):
            fail(f"invalid note ID: {name}")
        if not isinstance(raw_entry, dict):
            fail(f"note {name} must be a mapping")
        unknown = set(raw_entry) - {"source", "repeat", "references"}
        if unknown:
            fail(f"note {name} has unsupported fields: {', '.join(sorted(map(str, unknown)))}")
        entries[name] = dict(raw_entry)
    if len(order) != len(entries):
        fail("notes order and mapping contain different entry counts")
    for name in order:
        if name not in entries:
            fail(f"notes order references unknown note {name}")
    for name in sorted(entries):
        entry = entries[name]
        if name not in order_seen:
            fail(f"note {name} is absent from order")
        source = entry.get("source")
        if not isinstance(source, str) or not re.fullmatch(
            r"(?:appendices/)?[a-z0-9][a-z0-9-]*\.qmd", source
        ):
            fail(f"note {name} has invalid source")
        repeat = entry.get("repeat")
        if not isinstance(repeat, str) or repeat not in {"once", "reuse"}:
            fail(f"note {name} has unsupported repeat policy")
        if type(entry.get("references")) is not int or entry["references"] < 1:
            fail(f"note {name} has invalid reference count")
        if entry["repeat"] == "once" and entry["references"] != 1:
            fail(f"note {name} uses repeat=once with more than one reference")
    definitions: dict[str, dict[str, str]] = {}
    references: dict[str, int] = {}
    reference_sources: dict[str, set[str]] = {}
    placeholders = 0
    for source in sorted(
        path
        for path in root.rglob("*.qmd")
        if ".quarto" not in path.parts and "_build" not in path.parts
    ):
        relative = source.relative_to(root).as_posix()
        lines = source.read_text(encoding="utf-8").splitlines(keepends=True)
        content = "".join(lines)
        placeholders += len(
            re.findall(r"^:::\s+\{\.alkahest-book-notes-placeholder\}\s*$", content, re.MULTILINE)
        )
        if "^[" in content:
            fail(f"{relative} uses an inline note; use a registered named note")
        fence, index = "", 0
        while index < len(lines):
            line = lines[index]
            if fence:
                if re.fullmatch(re.escape(fence) + r"\s*\n?", line):
                    fence = ""
                index += 1
                continue
            opening = re.match(r"^(`{3,}|~{3,})", line)
            if opening:
                fence = opening.group(1)
                index += 1
                continue
            for name in re.findall(r"\[\^([a-z][a-z0-9-]*)\]", line):
                references[name] = references.get(name, 0) + 1
                reference_sources.setdefault(name, set()).add(relative)
            definition_match = re.match(r"^\[\^([a-z][a-z0-9-]*)\]:\s*(.*)$", line)
            if definition_match:
                name, marker = definition_match.groups()
                if name in definitions:
                    fail(f"duplicate note definition: {name}")
                location = f"{relative}:{index + 1}"
                while index + 1 < len(lines) and (
                    re.match(r"^(?: {4}|\t)", lines[index + 1]) or not lines[index + 1].strip()
                ):
                    index += 1
                    marker += lines[index]
                definitions[name] = {"marker": marker, "source": relative, "location": location}
            index += 1
    if placeholders != 1:
        fail(f"expected exactly one book-notes placeholder; found {placeholders}")
    for name in sorted(definitions):
        if name not in entries:
            fail(f"unregistered note definition: {name}")
    for name in sorted(references):
        if name not in definitions or name not in entries:
            fail(f"note reference has no registered definition: {name}")
    total = 0
    for name in order:
        entry = entries[name]
        definition = definitions.get(name)
        if not definition:
            fail(f"registered note {name} has no definition")
        if definition["source"] != entry["source"]:
            fail(f"note {name} definition is in {definition['source']}; expected {entry['source']}")
        if not re.search(rf"\{{#note-{re.escape(name)}\s+\.alkahest-note\}}", definition["marker"]):
            fail(f"{definition['location']}: note marker must be #note-{name} .alkahest-note")
        actual = references.get(name, 0) - 1
        if actual < 1:
            fail(f"note {name} has no manuscript references")
        if actual != entry["references"]:
            fail(f"note {name} has {actual} references; registry expects {entry['references']}")
        if any(item != entry["source"] for item in reference_sources[name]):
            fail(f"note {name} is referenced outside {entry['source']}")
        if actual > 1 and entry["repeat"] != "reuse":
            fail(f"note {name} repeats without repeat=reuse")
        total += actual
    print(
        f"ok: semantic notes ({len(order)} definitions; {total} references; footnote/chapter-endnote/book-endnote/sidenote placements; one generated apparatus)"
    )


if __name__ == "__main__":
    try:
        main()
    except (OSError, UnicodeError, RuntimeError) as error:
        print(error, file=sys.stderr)
        raise SystemExit(1) from None
