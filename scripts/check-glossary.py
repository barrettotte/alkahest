"""Validate the glossary registry, aliases, forms, and manuscript references."""

import os
import re
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent


def fail(message):
    raise RuntimeError(f"error: {message}")


def main():
    root = Path(os.environ.get("ALKAHEST_GLOSSARY_BOOK_ROOT", SCRIPT_DIR.parent / "book")).resolve()
    if not root.is_dir():
        fail("glossary book root does not exist")
    registry_path = root / "glossary.yml"
    entries, version, language, saw_terms, current, mode = {}, None, None, False, None, None
    for line_number, line in enumerate(registry_path.read_text(encoding="utf-8").splitlines(), 1):
        if current and mode == "definition" and re.match(r"^      \S", line):
            entries[current]["definition"] = (entries[current]["definition"] + " " + line[6:]).strip()
            continue
        alias = re.match(r"^      - ([a-z][a-z0-9-]*)$", line) if current and mode == "aliases" else None
        if alias:
            entries[current]["aliases"].append(alias.group(1))
            continue
        mode = None
        if re.match(r"^\s*(?:#.*)?$", line):
            continue
        match = re.fullmatch(r"version: ([0-9]+)", line)
        if match:
            if version is not None:
                fail(f"{registry_path}:{line_number}: duplicate version")
            version = int(match.group(1)); continue
        match = re.fullmatch(r"lang: (\S+)", line)
        if match:
            if language is not None:
                fail(f"{registry_path}:{line_number}: duplicate language tag")
            language = match.group(1); continue
        if line == "terms:":
            if saw_terms:
                fail(f"{registry_path}:{line_number}: duplicate terms mapping")
            saw_terms = True; continue
        match = re.fullmatch(r"  ([a-z][a-z0-9-]*):", line)
        if match:
            current = match.group(1)
            if current in entries:
                fail(f"{registry_path}:{line_number}: duplicate glossary ID: {current}")
            entries[current] = {"aliases": [], "line": line_number}; continue
        if current is None:
            fail(f"{registry_path}:{line_number}: field appears before a glossary ID")
        if line == "    aliases:":
            if entries[current].get("saw_aliases"):
                fail(f"{registry_path}:{line_number}: duplicate aliases field for {current}")
            entries[current]["saw_aliases"] = True; mode = "aliases"; continue
        if line == "    definition: >-":
            if "definition" in entries[current]:
                fail(f"{registry_path}:{line_number}: duplicate definition for {current}")
            entries[current]["definition"] = ""; mode = "definition"; continue
        match = re.fullmatch(r"    (term|plural|acronym|acronym-plural): (\S.*)", line)
        if match:
            field, value = match.groups()
            if field in entries[current]:
                fail(f"{registry_path}:{line_number}: duplicate {field} for {current}")
            entries[current][field] = value; continue
        fail(f"{registry_path}:{line_number}: unsupported glossary syntax: {line}")
    if version != 1:
        fail("glossary registry version must be 1")
    if not language or not re.fullmatch(r"[A-Za-z]{2,3}(?:-[A-Za-z0-9]{2,8})*", language):
        fail("glossary registry language must be a BCP 47-style tag")
    if not saw_terms:
        fail("glossary registry has no terms mapping")
    if not entries:
        fail("glossary registry has no entries")
    lookup, display_terms = {}, set()
    for name in sorted(entries):
        entry = entries[name]
        for required in ("term", "definition"):
            if not entry.get(required, "").strip():
                fail(f"glossary {name} has no {required}")
        normalized = entry["term"].lower()
        if normalized in display_terms:
            fail(f"duplicate glossary display term: {entry['term']}")
        display_terms.add(normalized)
        if "acronym-plural" in entry and "acronym" not in entry:
            fail(f"glossary {name} has acronym-plural without acronym")
        for key in (name, *entry["aliases"]):
            if key in lookup:
                fail(f"duplicate glossary name or alias: {key}")
            lookup[key] = name
    valid_forms = {"term", "plural", "acronym", "acronym-plural", "first", "first-plural"}
    valid_cases = {"as-written", "sentence"}
    first_uses, referenced, calls, generators = {}, {}, 0, 0
    pattern = re.compile(r"\{\{<\s*alk-term\s+(.+?)\s*>\}\}")
    for source in sorted(path for path in root.rglob("*.qmd") if ".quarto" not in path.parts and "_build" not in path.parts):
        disabled = ""
        for line_number, line in enumerate(source.read_text(encoding="utf-8").splitlines(), 1):
            if disabled:
                if re.fullmatch(re.escape(disabled) + r"\s*", line): disabled = ""
                continue
            fence = re.match(r"^(`{3,}|~{3,}).*\bshortcodes=false\b", line)
            if fence:
                disabled = fence.group(1); continue
            if re.search(r"\{\{<\s*alk-term\s*>\}\}", line):
                fail(f"{source}:{line_number}: alk-term is missing a glossary name")
            if re.fullmatch(r":::\s+\{\.alkahest-glossary-placeholder\}\s*", line):
                generators += 1
            for call in pattern.finditer(line):
                arguments = call.group(1)
                parsed = re.fullmatch(r"([a-z][a-z0-9-]*)(.*)", arguments)
                if not parsed: fail(f"{source}:{line_number}: invalid alk-term glossary name")
                requested, remainder = parsed.groups()
                if requested not in lookup: fail(f"{source}:{line_number}: unknown glossary name or alias: {requested}")
                named = {}
                argument = re.compile(r'''\b(form|case|link)\s*=\s*(?:"([^"]+)"|'([^']+)'|([^\s]+))''')
                while True:
                    match = argument.search(remainder)
                    if not match: break
                    key = match.group(1); value = next(value for value in match.groups()[1:] if value is not None)
                    if key in named: fail(f"{source}:{line_number}: duplicate alk-term argument: {key}")
                    named[key] = value
                    remainder = remainder[:match.start()] + remainder[match.end():]
                remainder = re.sub(r"\s+", "", remainder)
                if remainder: fail(f"{source}:{line_number}: unexpected alk-term arguments: {remainder}")
                form, text_case, link = named.get("form", "term"), named.get("case", "as-written"), named.get("link", "true")
                if form not in valid_forms: fail(f"{source}:{line_number}: unknown alk-term form: {form}")
                if text_case not in valid_cases: fail(f"{source}:{line_number}: unknown alk-term case: {text_case}")
                if link not in {"true", "false"}: fail(f"{source}:{line_number}: alk-term link must be true or false")
                name = lookup[requested]; entry = entries[name]
                required = {"plural": "plural", "acronym": "acronym", "acronym-plural": "acronym-plural", "first-plural": "plural"}.get(form)
                if required and required not in entry: fail(f"{source}:{line_number}: form {form} is unavailable for {name}")
                if form == "first-plural" and "acronym" in entry and "acronym-plural" not in entry:
                    fail(f"{source}:{line_number}: first-plural needs acronym-plural for {name}")
                if form in {"first", "first-plural"}:
                    if name in first_uses: fail(f"{source}:{line_number}: duplicate explicit first use for {name}; first marked at {first_uses[name]}")
                    first_uses[name] = f"{source}:{line_number}"
                referenced[name] = referenced.get(name, 0) + 1; calls += 1
    if not calls: fail("no alk-term glossary references were found")
    if generators != 1: fail(f"expected exactly one generated-glossary placeholder; found {generators}")
    for name in sorted(referenced):
        if name not in first_uses: fail(f"referenced glossary entry {name} has no explicit first-use marker")
    for name in sorted(entries):
        if name not in referenced: fail(f"glossary entry {name} is unused; remove it or reference it before generating back matter")
    print(f"ok: glossary registry ({len(entries)} entries; {len(lookup)} names and aliases; {len(referenced)} referenced entries; {calls} manuscript calls; {language}; one generated glossary)")


if __name__ == "__main__":
    try: main()
    except (OSError, UnicodeError, RuntimeError) as error:
        print(error, file=sys.stderr); raise SystemExit(1)
