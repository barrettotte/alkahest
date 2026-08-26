"""Validate the glossary registry, aliases, forms, and manuscript references."""

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
    root = Path(os.environ.get("ALKAHEST_GLOSSARY_BOOK_ROOT", ROOT / "book")).resolve()
    if not root.is_dir():
        fail("glossary book root does not exist")
    registry_path = root / "glossary.yml"
    registry = load_yaml(registry_path, "glossary registry")
    unknown = set(registry) - {"version", "lang", "terms"}
    if unknown:
        fail(f"glossary registry has unsupported fields: {', '.join(sorted(map(str, unknown)))}")
    if registry.get("version") != 1:
        fail("glossary registry version must be 1")
    language = registry.get("lang")
    if not isinstance(language, str) or not re.fullmatch(
        r"[A-Za-z]{2,3}(?:-[A-Za-z0-9]{2,8})*", language
    ):
        fail("glossary registry language must be a BCP 47-style tag")
    raw_entries = registry.get("terms")
    if not isinstance(raw_entries, dict) or not raw_entries:
        fail("glossary registry has no entries")
    entries: dict[str, dict[str, Any]] = {}
    allowed_fields = {"term", "plural", "acronym", "acronym-plural", "aliases", "definition"}
    for name, raw_entry in raw_entries.items():
        if not isinstance(name, str) or not re.fullmatch(r"[a-z][a-z0-9-]*", name):
            fail(f"invalid glossary ID: {name}")
        if not isinstance(raw_entry, dict):
            fail(f"glossary {name} must be a mapping")
        unknown = set(raw_entry) - allowed_fields
        if unknown:
            fail(f"glossary {name} has unsupported fields: {', '.join(sorted(map(str, unknown)))}")
        aliases = raw_entry.get("aliases", [])
        if not isinstance(aliases, list) or not all(isinstance(alias, str) for alias in aliases):
            fail(f"glossary {name} aliases must be a list of names")
        entry = dict(raw_entry)
        entry["aliases"] = aliases
        for field in allowed_fields - {"aliases"}:
            if field in entry and not isinstance(entry[field], str):
                fail(f"glossary {name} {field} must be text")
        entries[name] = entry
    lookup: dict[str, str] = {}
    display_terms: set[str] = set()
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
    first_uses: dict[str, str] = {}
    referenced: dict[str, int] = {}
    calls = 0
    generators = 0
    pattern = re.compile(r"\{\{<\s*alk-term\s+(.+?)\s*>\}\}")
    for source in sorted(
        path
        for path in root.rglob("*.qmd")
        if ".quarto" not in path.parts and "_build" not in path.parts
    ):
        disabled = ""
        for line_number, line in enumerate(source.read_text(encoding="utf-8").splitlines(), 1):
            if disabled:
                if re.fullmatch(re.escape(disabled) + r"\s*", line):
                    disabled = ""
                continue
            fence = re.match(r"^(`{3,}|~{3,}).*\bshortcodes=false\b", line)
            if fence:
                disabled = fence.group(1)
                continue
            if re.search(r"\{\{<\s*alk-term\s*>\}\}", line):
                fail(f"{source}:{line_number}: alk-term is missing a glossary name")
            if re.fullmatch(r":::\s+\{\.alkahest-glossary-placeholder\}\s*", line):
                generators += 1
            for call in pattern.finditer(line):
                arguments = call.group(1)
                parsed = re.fullmatch(r"([a-z][a-z0-9-]*)(.*)", arguments)
                if not parsed:
                    fail(f"{source}:{line_number}: invalid alk-term glossary name")
                requested, remainder = parsed.groups()
                if requested not in lookup:
                    fail(f"{source}:{line_number}: unknown glossary name or alias: {requested}")
                named: dict[str, str] = {}
                argument = re.compile(
                    r"""\b(form|case|link)\s*=\s*(?:"([^"]+)"|'([^']+)'|([^\s]+))"""
                )
                while True:
                    match = argument.search(remainder)
                    if not match:
                        break
                    key = match.group(1)
                    value = next(value for value in match.groups()[1:] if value is not None)
                    if key in named:
                        fail(f"{source}:{line_number}: duplicate alk-term argument: {key}")
                    named[key] = value
                    remainder = remainder[: match.start()] + remainder[match.end() :]
                remainder = re.sub(r"\s+", "", remainder)
                if remainder:
                    fail(f"{source}:{line_number}: unexpected alk-term arguments: {remainder}")
                form, text_case, link = (
                    named.get("form", "term"),
                    named.get("case", "as-written"),
                    named.get("link", "true"),
                )
                if form not in valid_forms:
                    fail(f"{source}:{line_number}: unknown alk-term form: {form}")
                if text_case not in valid_cases:
                    fail(f"{source}:{line_number}: unknown alk-term case: {text_case}")
                if link not in {"true", "false"}:
                    fail(f"{source}:{line_number}: alk-term link must be true or false")
                name = lookup[requested]
                entry = entries[name]
                required_form: str | None = {
                    "plural": "plural",
                    "acronym": "acronym",
                    "acronym-plural": "acronym-plural",
                    "first-plural": "plural",
                }.get(form)
                if required_form and required_form not in entry:
                    fail(f"{source}:{line_number}: form {form} is unavailable for {name}")
                if form == "first-plural" and "acronym" in entry and "acronym-plural" not in entry:
                    fail(f"{source}:{line_number}: first-plural needs acronym-plural for {name}")
                if form in {"first", "first-plural"}:
                    if name in first_uses:
                        fail(
                            f"{source}:{line_number}: duplicate explicit first use for {name}; first marked at {first_uses[name]}"
                        )
                    first_uses[name] = f"{source}:{line_number}"
                referenced[name] = referenced.get(name, 0) + 1
                calls += 1
    if not calls:
        fail("no alk-term glossary references were found")
    if generators != 1:
        fail(f"expected exactly one generated-glossary placeholder; found {generators}")
    for name in sorted(referenced):
        if name not in first_uses:
            fail(f"referenced glossary entry {name} has no explicit first-use marker")
    for name in sorted(entries):
        if name not in referenced:
            fail(
                f"glossary entry {name} is unused; remove it or reference it before generating back matter"
            )
    print(
        f"ok: glossary registry ({len(entries)} entries; {len(lookup)} names and aliases; {len(referenced)} referenced entries; {calls} manuscript calls; {language}; one generated glossary)"
    )


if __name__ == "__main__":
    try:
        main()
    except (OSError, UnicodeError, RuntimeError) as error:
        print(error, file=sys.stderr)
        raise SystemExit(1) from None
