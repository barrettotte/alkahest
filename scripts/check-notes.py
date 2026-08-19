"""Validate semantic note identities, definitions, sources, repeats, and apparatus."""

import os
import re
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent


def fail(message): raise RuntimeError(f"error: {message}")


def main():
    root = Path(os.environ.get("ALKAHEST_NOTES_BOOK_ROOT", SCRIPT_DIR.parent / "book")).resolve()
    if not root.is_dir(): fail("notes book root does not exist")
    registry_path = root / "notes.yml"
    version, section, current, order, entries, order_seen = None, None, None, [], {}, set()
    for number, line in enumerate(registry_path.read_text(encoding="utf-8").splitlines(), 1):
        if re.match(r"^\s*(?:#.*)?$", line): continue
        match = re.fullmatch(r"version: ([0-9]+)", line)
        if match:
            if version is not None: fail(f"{registry_path}:{number}: duplicate version")
            version = int(match.group(1)); continue
        if line in {"order:", "notes:"}:
            section, current = line[:-1], None; continue
        match = re.fullmatch(r"  - ([a-z][a-z0-9-]*)", line) if section == "order" else None
        if match:
            name = match.group(1)
            if name in order_seen: fail(f"{registry_path}:{number}: duplicate note in order: {name}")
            order_seen.add(name); order.append(name); continue
        match = re.fullmatch(r"  ([a-z][a-z0-9-]*):", line) if section == "notes" else None
        if match:
            current = match.group(1)
            if current in entries: fail(f"{registry_path}:{number}: duplicate note ID: {current}")
            entries[current] = {"line": number}; continue
        if section != "notes" or current is None: fail(f"{registry_path}:{number}: field appears before a note ID")
        match = re.fullmatch(r"    (source|repeat|references): (\S.*)", line)
        if match:
            field, value = match.groups()
            if field in entries[current]: fail(f"{registry_path}:{number}: duplicate {field} for {current}")
            entries[current][field] = value; continue
        fail(f"{registry_path}:{number}: unsupported notes syntax: {line}")
    if version != 1: fail("notes registry version must be 1")
    if not order: fail("notes registry has no ordered notes")
    if len(order) != len(entries): fail("notes order and mapping contain different entry counts")
    for name in order:
        if name not in entries: fail(f"notes order references unknown note {name}")
    for name in sorted(entries):
        entry = entries[name]
        if name not in order_seen: fail(f"note {name} is absent from order")
        if not re.fullmatch(r"(?:appendices/)?[a-z0-9][a-z0-9-]*\.qmd", entry.get("source", "")): fail(f"note {name} has invalid source")
        if entry.get("repeat") not in {"once", "reuse"}: fail(f"note {name} has unsupported repeat policy")
        if not re.fullmatch(r"[1-9][0-9]*", entry.get("references", "")): fail(f"note {name} has invalid reference count")
        entry["references"] = int(entry["references"])
        if entry["repeat"] == "once" and entry["references"] != 1: fail(f"note {name} uses repeat=once with more than one reference")
    definitions, references, reference_sources, placeholders = {}, {}, {}, 0
    for source in sorted(path for path in root.rglob("*.qmd") if ".quarto" not in path.parts and "_build" not in path.parts):
        relative = source.relative_to(root).as_posix(); lines = source.read_text(encoding="utf-8").splitlines(keepends=True); content = "".join(lines)
        placeholders += len(re.findall(r"^:::\s+\{\.alkahest-book-notes-placeholder\}\s*$", content, re.M))
        if "^[" in content: fail(f"{relative} uses an inline note; use a registered named note")
        fence, index = "", 0
        while index < len(lines):
            line = lines[index]
            if fence:
                if re.fullmatch(re.escape(fence) + r"\s*\n?", line): fence = ""
                index += 1; continue
            opening = re.match(r"^(`{3,}|~{3,})", line)
            if opening: fence = opening.group(1); index += 1; continue
            for name in re.findall(r"\[\^([a-z][a-z0-9-]*)\]", line):
                references[name] = references.get(name, 0) + 1
                reference_sources.setdefault(name, set()).add(relative)
            definition = re.match(r"^\[\^([a-z][a-z0-9-]*)\]:\s*(.*)$", line)
            if definition:
                name, marker = definition.groups()
                if name in definitions: fail(f"duplicate note definition: {name}")
                location = f"{relative}:{index + 1}"
                while index + 1 < len(lines) and (re.match(r"^(?: {4}|\t)", lines[index + 1]) or not lines[index + 1].strip()):
                    index += 1; marker += lines[index]
                definitions[name] = {"marker": marker, "source": relative, "location": location}
            index += 1
    if placeholders != 1: fail(f"expected exactly one book-notes placeholder; found {placeholders}")
    for name in sorted(definitions):
        if name not in entries: fail(f"unregistered note definition: {name}")
    for name in sorted(references):
        if name not in definitions or name not in entries: fail(f"note reference has no registered definition: {name}")
    total = 0
    for name in order:
        entry = entries[name]; definition = definitions.get(name)
        if not definition: fail(f"registered note {name} has no definition")
        if definition["source"] != entry["source"]: fail(f"note {name} definition is in {definition['source']}; expected {entry['source']}")
        if not re.search(rf"\{{#note-{re.escape(name)}\s+\.alkahest-note\}}", definition["marker"]): fail(f"{definition['location']}: note marker must be #note-{name} .alkahest-note")
        actual = references.get(name, 0) - 1
        if actual < 1: fail(f"note {name} has no manuscript references")
        if actual != entry["references"]: fail(f"note {name} has {actual} references; registry expects {entry['references']}")
        if any(item != entry["source"] for item in reference_sources[name]): fail(f"note {name} is referenced outside {entry['source']}")
        if actual > 1 and entry["repeat"] != "reuse": fail(f"note {name} repeats without repeat=reuse")
        total += actual
    print(f"ok: semantic notes ({len(order)} definitions; {total} references; footnote/chapter-endnote/book-endnote/sidenote placements; one generated apparatus)")


if __name__ == "__main__":
    try: main()
    except (OSError, UnicodeError, RuntimeError) as error:
        print(error, file=sys.stderr); raise SystemExit(1)
