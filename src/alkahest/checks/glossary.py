"""Validate the glossary registry, aliases, forms, and manuscript references."""

import os
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Never, NotRequired, TypedDict, cast

from alkahest.common import DataValue, load_yaml

ROOT = Path(__file__).resolve().parents[3]
ALLOWED_FIELDS = {"term", "plural", "acronym", "acronym-plural", "aliases", "definition"}
VALID_FORMS = {"term", "plural", "acronym", "acronym-plural", "first", "first-plural"}
VALID_CASES = {"as-written", "sentence"}
CALL_PATTERN = re.compile(r"\{\{<\s*alk-term\s+(.+?)\s*>\}\}")
ARGUMENT_PATTERN = re.compile(r"""\b(form|case|link)\s*=\s*(?:"([^"]+)"|'([^']+)'|([^\s]+))""")


GlossaryEntry = TypedDict(
    "GlossaryEntry",
    {
        "term": str,
        "definition": str,
        "aliases": list[str],
        "plural": NotRequired[str],
        "acronym": NotRequired[str],
        "acronym-plural": NotRequired[str],
    },
)


@dataclass
class GlossaryUsage:
    """Observed glossary calls and generated back matter."""

    first_uses: dict[str, str] = field(default_factory=dict)
    referenced: dict[str, int] = field(default_factory=dict)
    calls: int = 0
    generators: int = 0


def fail(message: str) -> Never:
    """Raise one glossary contract error."""
    raise RuntimeError(f"error: {message}")


def validate_entry(name: str, raw_entry: DataValue) -> GlossaryEntry:
    """Validate one glossary registry entry."""
    if not re.fullmatch(r"[a-z][a-z0-9-]*", name):
        fail(f"invalid glossary ID: {name}")
    if not isinstance(raw_entry, dict):
        fail(f"glossary {name} must be a mapping")
    unknown = set(raw_entry) - ALLOWED_FIELDS
    if unknown:
        fail(f"glossary {name} has unsupported fields: {', '.join(sorted(map(str, unknown)))}")
    aliases = raw_entry.get("aliases", [])
    if not isinstance(aliases, list) or not all(isinstance(alias, str) for alias in aliases):
        fail(f"glossary {name} aliases must be a list of names")
    entry = dict(raw_entry)
    entry["aliases"] = aliases
    for entry_field in ALLOWED_FIELDS - {"aliases"}:
        if entry_field in entry and not isinstance(entry[entry_field], str):
            fail(f"glossary {name} {entry_field} must be text")
    return cast(GlossaryEntry, entry)


def load_entries(root: Path) -> tuple[str, dict[str, GlossaryEntry]]:
    """Load and validate glossary registry structure."""
    registry = load_yaml(root / "glossary.yml", "glossary registry")
    unknown = set(registry) - {"version", "lang", "terms"}
    if unknown:
        fail(f"glossary registry has unsupported fields: {', '.join(sorted(map(str, unknown)))}")
    if registry.get("version") != 1:
        fail("glossary registry version must be 1")

    language = registry.get("lang")
    if not isinstance(language, str) or not re.fullmatch(r"[A-Za-z]{2,3}(?:-[A-Za-z0-9]{2,8})*", language):
        fail("glossary registry language must be a BCP 47-style tag")

    raw_entries = registry.get("terms")
    if not isinstance(raw_entries, dict) or not raw_entries:
        fail("glossary registry has no entries")

    entries = {name: validate_entry(name, raw_entry) for name, raw_entry in raw_entries.items()}
    return language, entries


def build_lookup(entries: dict[str, GlossaryEntry]) -> dict[str, str]:
    """Validate entry identities and build the alias lookup."""
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
    return lookup


def parse_arguments(remainder: str, source: Path, line_number: int) -> dict[str, str]:
    """Parse named arguments from one glossary shortcode."""
    named: dict[str, str] = {}
    while match := ARGUMENT_PATTERN.search(remainder):
        key = match.group(1)
        value = next(value for value in match.groups()[1:] if value is not None)
        if key in named:
            fail(f"{source}:{line_number}: duplicate alk-term argument: {key}")

        named[key] = value
        remainder = remainder[: match.start()] + remainder[match.end() :]

    remainder = re.sub(r"\s+", "", remainder)
    if remainder:
        fail(f"{source}:{line_number}: unexpected alk-term arguments: {remainder}")
    return named


def validate_call(
    arguments: str,
    source: Path,
    line_number: int,
    entries: dict[str, GlossaryEntry],
    lookup: dict[str, str],
    usage: GlossaryUsage,
) -> None:
    """Validate and record one glossary shortcode call."""
    parsed = re.fullmatch(r"([a-z][a-z0-9-]*)(.*)", arguments)
    if not parsed:
        fail(f"{source}:{line_number}: invalid alk-term glossary name")
    requested, remainder = parsed.groups()
    if requested not in lookup:
        fail(f"{source}:{line_number}: unknown glossary name or alias: {requested}")

    named = parse_arguments(remainder, source, line_number)
    form = named.get("form", "term")
    text_case = named.get("case", "as-written")
    link = named.get("link", "true")
    if form not in VALID_FORMS:
        fail(f"{source}:{line_number}: unknown alk-term form: {form}")
    if text_case not in VALID_CASES:
        fail(f"{source}:{line_number}: unknown alk-term case: {text_case}")
    if link not in {"true", "false"}:
        fail(f"{source}:{line_number}: alk-term link must be true or false")

    name = lookup[requested]
    entry = entries[name]
    required_form = {
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
        if name in usage.first_uses:
            fail(
                f"{source}:{line_number}: duplicate explicit first use for {name}; "
                f"first marked at {usage.first_uses[name]}"
            )
        usage.first_uses[name] = f"{source}:{line_number}"
    usage.referenced[name] = usage.referenced.get(name, 0) + 1
    usage.calls += 1


def scan_source(source: Path, entries: dict[str, GlossaryEntry], lookup: dict[str, str], usage: GlossaryUsage) -> None:
    """Validate glossary calls in one manuscript source."""
    disabled = ""
    for line_number, line in enumerate(source.read_text(encoding="utf-8").splitlines(), 1):
        if disabled:
            if re.fullmatch(re.escape(disabled) + r"\s*", line):
                disabled = ""
            continue
        if fence := re.match(r"^(`{3,}|~{3,}).*\bshortcodes=false\b", line):
            disabled = fence.group(1)
            continue
        if re.search(r"\{\{<\s*alk-term\s*>\}\}", line):
            fail(f"{source}:{line_number}: alk-term is missing a glossary name")
        if re.fullmatch(r":::\s+\{\.alkahest-glossary-placeholder\}\s*", line):
            usage.generators += 1
        for call in CALL_PATTERN.finditer(line):
            validate_call(call.group(1), source, line_number, entries, lookup, usage)


def scan_usage(root: Path, entries: dict[str, GlossaryEntry], lookup: dict[str, str]) -> GlossaryUsage:
    """Collect glossary usage across manuscript sources."""
    usage = GlossaryUsage()
    sources = sorted(path for path in root.rglob("*.qmd") if ".quarto" not in path.parts and "_build" not in path.parts)
    for source in sources:
        scan_source(source, entries, lookup, usage)
    return usage


def validate_usage(entries: dict[str, GlossaryEntry], usage: GlossaryUsage) -> None:
    """Require complete and singular glossary usage."""
    if not usage.calls:
        fail("no alk-term glossary references were found")
    if usage.generators != 1:
        fail(f"expected exactly one generated-glossary placeholder; found {usage.generators}")
    for name in sorted(usage.referenced):
        if name not in usage.first_uses:
            fail(f"referenced glossary entry {name} has no explicit first-use marker")
    for name in sorted(entries):
        if name not in usage.referenced:
            fail(f"glossary entry {name} is unused; remove it or reference it before generating back matter")


def main() -> None:
    """Validate the glossary registry and manuscript calls."""
    root = Path(os.environ.get("ALKAHEST_GLOSSARY_BOOK_ROOT", ROOT / "book")).resolve()
    if not root.is_dir():
        fail("glossary book root does not exist")
    language, entries = load_entries(root)
    lookup = build_lookup(entries)
    usage = scan_usage(root, entries, lookup)
    validate_usage(entries, usage)
    print(
        f"ok: glossary registry ({len(entries)} entries; {len(lookup)} names and aliases; "
        f"{len(usage.referenced)} referenced entries; {usage.calls} manuscript calls; "
        f"{language}; one generated glossary)"
    )


if __name__ == "__main__":
    try:
        main()
    except (OSError, UnicodeError, RuntimeError) as error:
        print(error, file=sys.stderr)
        raise SystemExit(1) from None
