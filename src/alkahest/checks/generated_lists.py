"""Validate generated-list configuration, object coverage, terminology, and placement."""

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
    root = Path(os.environ.get("ALKAHEST_GENERATED_LISTS_BOOK_ROOT", ROOT / "book")).resolve()
    if not root.is_dir():
        fail("generated-list book root does not exist")
    path = root / "generated-lists.yml"
    registry = load_yaml(path, "generated-list registry")
    unknown = set(registry) - {"version", "lang", "order", "lists", "objects", "terms"}
    if unknown:
        fail(
            "generated-list registry has unsupported fields: "
            + ", ".join(sorted(map(str, unknown)))
        )
    if registry.get("version") != 1:
        fail("generated-list registry version must be 1")
    language = registry.get("lang")
    if not isinstance(language, str) or not re.fullmatch(
        r"[A-Za-z]{2,3}(?:-[A-Za-z0-9]{2,8})*", language
    ):
        fail("generated-list registry language must be a BCP 47 tag")
    raw_order = registry.get("order")
    raw_lists = registry.get("lists")
    raw_objects = registry.get("objects")
    raw_terms = registry.get("terms")
    if not isinstance(raw_order, list) or not all(isinstance(name, str) for name in raw_order):
        fail("generated-list order must be a list of names")
    if not isinstance(raw_lists, dict):
        fail("generated-list lists must be a mapping")
    if not isinstance(raw_objects, list):
        fail("generated-list objects must be a list")
    if not isinstance(raw_terms, dict):
        fail("generated-list terms must be a mapping")
    order: list[str] = raw_order
    lists: dict[str, dict[str, Any]] = {}
    terms: dict[str, dict[str, Any]] = {}
    for name, raw_item in raw_lists.items():
        if not isinstance(name, str) or not re.fullmatch(r"[a-z][a-z0-9-]*", name):
            fail(f"invalid generated-list name: {name}")
        if not isinstance(raw_item, dict):
            fail(f"configured list {name} must be a mapping")
        unknown = set(raw_item) - {"title", "source", "prefix", "enabled"}
        if unknown:
            fail(
                f"configured list {name} has unsupported fields: "
                f"{', '.join(sorted(map(str, unknown)))}"
            )
        item = dict(raw_item)
        for field in ("title", "source", "prefix"):
            if field in item and not isinstance(item[field], str):
                fail(f"configured list {name} {field} must be text")
        lists[name] = item
    objects: list[dict[str, Any]] = []
    for raw_object in raw_objects:
        if not isinstance(raw_object, dict) or set(raw_object) - {"id", "title"}:
            fail("each generated-list object must contain only id and title")
        if not all(isinstance(raw_object.get(field), str) for field in ("id", "title")):
            fail("each generated-list object needs text id and title fields")
        if not re.fullmatch(r"[a-z][a-z0-9-]*", raw_object["id"]):
            fail(f"invalid generated-list object ID: {raw_object['id']}")
        objects.append(dict(raw_object))
    for name, raw_term in raw_terms.items():
        if not isinstance(name, str) or not re.fullmatch(r"[a-z][a-z0-9-]*", name):
            fail(f"invalid generated-list term: {name}")
        if not isinstance(raw_term, dict):
            fail(f"generated-list term {name} must be a mapping")
        allowed = {"list", "display", "alt", "meaning", "sort", "target"}
        unknown = set(raw_term) - allowed
        if unknown:
            fail(
                f"generated-list term {name} has unsupported fields: "
                f"{', '.join(sorted(map(str, unknown)))}"
            )
        if not all(isinstance(value, str) for value in raw_term.values()):
            fail(f"generated-list term {name} fields must be text")
        terms[name] = dict(raw_term)
    if not lists:
        fail("generated-list registry has no configured lists")
    ordered: set[str] = set()
    prefix_owner: dict[str, str] = {}
    source_count: dict[str, int] = {}
    for name in order:
        if name in ordered:
            fail(f"duplicate list in order: {name}")
        ordered.add(name)
        if name not in lists:
            fail(f"unknown list in order: {name}")
    for name in sorted(lists):
        item = lists[name]
        if name not in ordered:
            fail(f"configured list {name} is missing from order")
        if not item.get("title", "").strip():
            fail(f"configured list {name} has no title")
        if item.get("source") not in {"crossref", "glossary-acronyms", "terms"}:
            fail(f"configured list {name} has unsupported source")
        item.setdefault("enabled", True)
        if not isinstance(item["enabled"], bool):
            fail(f"configured list {name} enabled must be true or false")
        source_count[item["source"]] = source_count.get(item["source"], 0) + 1
        if item["source"] == "crossref":
            prefix = item.get("prefix", "")
            if not re.fullmatch(r"[a-z][a-z0-9]*", prefix):
                fail(f"cross-reference list {name} has invalid prefix")
            if prefix in prefix_owner:
                fail(f"duplicate cross-reference prefix {prefix}")
            prefix_owner[prefix] = name
        elif "prefix" in item:
            fail(f"non-cross-reference list {name} cannot declare a prefix")
    if source_count.get("glossary-acronyms", 0) > 1:
        fail("generated-list registry permits at most one glossary-acronyms list")
    definitions: set[str] = set()
    locations: dict[str, str] = {}
    placeholders = 0
    for source in sorted(
        item
        for item in root.rglob("*.qmd")
        if ".quarto" not in item.parts and "_build" not in item.parts
    ):
        fence = ""
        for number, line in enumerate(source.read_text(encoding="utf-8").splitlines(), 1):
            if fence:
                if re.fullmatch(re.escape(fence) + r"\s*", line):
                    fence = ""
                    continue
                label = re.fullmatch(
                    r"\s*(?:#|//|%%)\|\s*label:\s*([a-z][a-z0-9]*-[a-z0-9-]+)\s*", line
                )
                if label and label.group(1).split("-", 1)[0] in prefix_owner:
                    identity = label.group(1)
                    if identity in definitions:
                        fail(f"duplicate generated-list object definition {identity}")
                    definitions.add(identity)
                    locations[identity] = f"{source}:{number}"
                continue
            placeholders += line.count("{.alkahest-generated-lists-placeholder}")
            if re.search(r"\\(?:listoffigures|listoftables|listoflistings)\b", line):
                fail(
                    f"{source}:{number}: use generated lists rather than a backend-specific list command"
                )
            for identity in re.findall(r"#([a-z][a-z0-9]*-[a-z0-9-]+)", line):
                if identity.split("-", 1)[0] not in prefix_owner:
                    continue
                if identity in definitions:
                    fail(f"duplicate generated-list object definition {identity}")
                definitions.add(identity)
                locations[identity] = f"{source}:{number}"
            opening = re.match(r"^(`{3,}|~{3,})", line)
            if opening:
                fence = opening.group(1)
    if placeholders != 1:
        fail(f"expected exactly one generated-lists placeholder; found {placeholders}")
    registered: set[str] = set()
    counts: dict[str, int] = {}
    for obj in objects:
        identity = obj["id"]
        if identity in registered:
            fail(f"duplicate generated-list object {identity}")
        registered.add(identity)
        if not obj.get("title", "").strip():
            fail(f"generated-list object {identity} has no title")
        owner = prefix_owner.get(identity.split("-", 1)[0])
        if not owner:
            fail(f"no configured cross-reference list owns {identity}")
        if identity not in definitions:
            fail(f"generated-list object target does not exist: {identity}")
        counts[owner] = counts.get(owner, 0) + 1
    for identity in sorted(definitions - registered):
        fail(
            f"{locations[identity]}: cross-reference object {identity} is missing from generated-lists.yml"
        )
    display_seen = set()
    for name in sorted(terms):
        term = terms[name]
        for field in ("list", "display", "alt", "meaning", "sort", "target"):
            if not term.get(field, "").strip():
                fail(f"generated-list term {name} has no {field}")
        if "$" in term["display"]:
            fail(f"generated-list term {name} display is a TeX fragment without dollar delimiters")
        term_list = lists.get(term["list"])
        if not term_list or term_list["source"] != "terms":
            fail(f"generated-list term {name} targets an unknown terms list")
        if term["display"] in display_seen:
            fail(f"duplicate generated-list term display {term['display']}")
        display_seen.add(term["display"])
        if term["target"] not in definitions:
            fail(f"generated-list term {name} targets unknown object {term['target']}")
        counts[term["list"]] = counts.get(term["list"], 0) + 1
    glossary_terms = load_yaml(root / "glossary.yml", "glossary registry").get("terms", {})
    if not isinstance(glossary_terms, dict):
        fail("glossary registry terms must be a mapping")
    acronyms = sum(
        isinstance(entry, dict) and bool(entry.get("acronym")) for entry in glossary_terms.values()
    )
    for name, item in lists.items():
        if item["source"] == "glossary-acronyms":
            counts[name] = acronyms
    empty = sorted(name for name, item in lists.items() if item["enabled"] and not counts.get(name))
    print(
        f"ok: generated lists ({len(lists)} configured; {len(lists) - len(empty)} nonempty; {len(objects)} cross-reference objects; {acronyms} acronyms; {len(terms)} terms; empty enabled: {', '.join(empty) if empty else 'none'})"
    )


if __name__ == "__main__":
    try:
        main()
    except (OSError, UnicodeError, RuntimeError) as error:
        print(error, file=sys.stderr)
        raise SystemExit(1) from None
