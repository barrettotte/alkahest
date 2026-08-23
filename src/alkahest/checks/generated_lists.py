"""Validate generated-list configuration, object coverage, terminology, and placement."""

import os
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]


def fail(message):
    raise RuntimeError(f"error: {message}")


def scalar(raw, location):
    value = raw.strip()
    if len(value) >= 2 and value[0] == value[-1] == "'":
        value = value[1:-1].replace("''", "'")
    elif len(value) >= 2 and value[0] == value[-1] == '"':
        value = value[1:-1].replace(r"\"", '"').replace(r"\\", "\\")
    if not value.strip():
        fail(f"{location}: empty scalar value")
    return value


def main():
    root = Path(os.environ.get("ALKAHEST_GENERATED_LISTS_BOOK_ROOT", ROOT / "book")).resolve()
    if not root.is_dir():
        fail("generated-list book root does not exist")
    path = root / "generated-lists.yml"
    version = language = section = current_list = current_term = None
    order, objects, lists, terms, sections = [], [], {}, {}, set()
    for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if re.match(r"^\s*(?:#.*)?$", line):
            continue
        match = re.fullmatch(r"version: ([0-9]+)", line)
        if match:
            if version is not None:
                fail(f"{path}:{number}: duplicate version")
            version = int(match.group(1))
            continue
        match = re.fullmatch(r"lang: (\S+)", line)
        if match:
            if language is not None:
                fail(f"{path}:{number}: duplicate language")
            language = match.group(1)
            continue
        match = re.fullmatch(r"(order|lists|objects|terms):", line)
        if match:
            section = match.group(1)
            if section in sections:
                fail(f"{path}:{number}: duplicate {section} section")
            sections.add(section)
            current_list = current_term = None
            continue
        if section is None:
            fail(f"{path}:{number}: field appears before a section")
        match = re.fullmatch(r"  - ([a-z][a-z0-9-]*)", line) if section == "order" else None
        if match:
            order.append(match.group(1))
            continue
        match = re.fullmatch(r"  ([a-z][a-z0-9-]*):", line) if section == "lists" else None
        if match:
            current_list = match.group(1)
            if current_list in lists:
                fail(f"{path}:{number}: duplicate list {current_list}")
            lists[current_list] = {"line": number}
            continue
        match = (
            re.fullmatch(r"    (title|source|prefix|enabled): (\S.*)", line)
            if section == "lists"
            else None
        )
        if match:
            if current_list is None:
                fail(f"{path}:{number}: list field before list name")
            field, raw = match.groups()
            if field in lists[current_list]:
                fail(f"{path}:{number}: duplicate {field} for {current_list}")
            lists[current_list][field] = scalar(raw, f"{path}:{number}")
            continue
        match = re.fullmatch(r"  - id: ([a-z][a-z0-9-]*)", line) if section == "objects" else None
        if match:
            objects.append({"id": match.group(1), "line": number})
            continue
        match = re.fullmatch(r"    title: (\S.*)", line) if section == "objects" else None
        if match:
            if not objects:
                fail(f"{path}:{number}: object title before object ID")
            if "title" in objects[-1]:
                fail(f"{path}:{number}: duplicate object title")
            objects[-1]["title"] = scalar(match.group(1), f"{path}:{number}")
            continue
        match = re.fullmatch(r"  ([a-z][a-z0-9-]*):", line) if section == "terms" else None
        if match:
            current_term = match.group(1)
            if current_term in terms:
                fail(f"{path}:{number}: duplicate term {current_term}")
            terms[current_term] = {"line": number}
            continue
        match = (
            re.fullmatch(r"    (list|display|alt|meaning|sort|target): (\S.*)", line)
            if section == "terms"
            else None
        )
        if match:
            if current_term is None:
                fail(f"{path}:{number}: term field before term ID")
            field, raw = match.groups()
            if field in terms[current_term]:
                fail(f"{path}:{number}: duplicate {field} for {current_term}")
            terms[current_term][field] = scalar(raw, f"{path}:{number}")
            continue
        fail(f"{path}:{number}: unsupported generated-list syntax: {line}")
    if version != 1:
        fail("generated-list registry version must be 1")
    if not language or not re.fullmatch(r"[A-Za-z]{2,3}(?:-[A-Za-z0-9]{2,8})*", language):
        fail("generated-list registry language must be a BCP 47 tag")
    for required in ("order", "lists", "objects", "terms"):
        if required not in sections:
            fail(f"generated-list registry has no {required} section")
    if not lists:
        fail("generated-list registry has no configured lists")
    ordered, prefix_owner, source_count = set(), {}, {}
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
        item.setdefault("enabled", "true")
        if item["enabled"] not in {"true", "false"}:
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
    definitions, locations, placeholders = set(), {}, 0
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
    registered, counts = set(), {}
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
        owner = lists.get(term["list"])
        if not owner or owner["source"] != "terms":
            fail(f"generated-list term {name} targets an unknown terms list")
        if term["display"] in display_seen:
            fail(f"duplicate generated-list term display {term['display']}")
        display_seen.add(term["display"])
        if term["target"] not in definitions:
            fail(f"generated-list term {name} targets unknown object {term['target']}")
        counts[term["list"]] = counts.get(term["list"], 0) + 1
    acronyms = sum(
        bool(re.match(r"^    acronym: \S", line))
        for line in (root / "glossary.yml").read_text(encoding="utf-8").splitlines()
    )
    for name, item in lists.items():
        if item["source"] == "glossary-acronyms":
            counts[name] = acronyms
    empty = sorted(
        name for name, item in lists.items() if item["enabled"] == "true" and not counts.get(name)
    )
    print(
        f"ok: generated lists ({len(lists)} configured; {len(lists) - len(empty)} nonempty; {len(objects)} cross-reference objects; {acronyms} acronyms; {len(terms)} terms; empty enabled: {', '.join(empty) if empty else 'none'})"
    )


if __name__ == "__main__":
    try:
        main()
    except (OSError, UnicodeError, RuntimeError) as error:
        print(error, file=sys.stderr)
        raise SystemExit(1)
