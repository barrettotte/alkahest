"""Parse and validate semantic learning blocks and stable relationships."""

import re
from pathlib import Path

from .common import fail, qmd_sources


CLASS_TYPE = {
    "learning-objectives": ("objectives", "obj-"),
    "learning-prerequisites": ("prerequisites", "pre-"),
    "learning-plan": ("plan", "plan-"),
    "learning-summary": ("summary", "sum-"),
    "review-question": ("review-question", "rev-"),
    "question-hint": ("hint", "hint-"),
    "answer-key": ("answer-key", "ans-"),
}
TYPES = ("objectives", "prerequisites", "plan", "summary", "review-question", "hint", "exercise", "solution", "answer-key")


def _registered_selection(registry, edition_name):
    edition = registry["editions"][edition_name]
    structure = registry["structures"][edition["structure"]]
    result = []
    for item in structure.get("chapters", []):
        result.extend([item["source"]] if "source" in item else item.get("sources", []))
    for group in structure.get("appendices", []):
        result.extend(group.get("sources", []))
    return result


def _parse_source(path, source, records):
    stack, code_fence = [], ""
    try:
        lines = Path(path).read_text(encoding="utf-8").splitlines(keepends=True)
    except (OSError, UnicodeError) as error:
        fail(f"cannot read learning source '{source}': {error}")
    for line_number, line in enumerate(lines, 1):
        if code_fence:
            if re.fullmatch(re.escape(code_fence) + r"\s*\n?", line):
                code_fence = ""
            continue
        fence = re.match(r"^(`{3,}|~{3,})", line)
        if fence:
            code_fence = fence.group(1)
            continue
        opening = re.match(r"^:{3,}\s+\{([^}]*)\}\s*$", line)
        if opening:
            attributes = opening.group(1)
            id_match = re.search(r"#([A-Za-z][A-Za-z0-9_.:-]*)", attributes)
            identity = id_match.group(1) if id_match else None
            classes = set(re.findall(r"\.([A-Za-z][A-Za-z0-9_-]*)", attributes))
            native_callout = any(item.startswith("callout-") for item in classes)
            learning_classes = [item for item in CLASS_TYPE if item in classes]
            if len(learning_classes) > 1:
                fail(f"{source}:{line_number}: a block cannot have multiple learning roles")
            block_type = prefix = None
            if learning_classes:
                block_type, prefix = CLASS_TYPE[learning_classes[0]]
            elif identity and identity.startswith("exr-"):
                block_type, prefix = "exercise", "exr-"
            elif identity and identity.startswith("sol-"):
                block_type, prefix = "solution", "sol-"
            values = dict(re.findall(r'([a-z][a-z0-9-]*)="([^"]*)"', attributes))
            record = None
            if block_type:
                if identity is None or not identity.startswith(prefix):
                    fail(f"{source}:{line_number}: {block_type} block needs a stable '{prefix}...' ID")
                if identity in records:
                    fail(f"duplicate learning identity '{identity}' in {source} and {records[identity]['source']}")
                record = {
                    "id": identity, "type": block_type, "source": source,
                    "line": line_number, "classes": classes, "attributes": values,
                    "headings": 0, "content": "", "direct_callout": native_callout,
                    "nested_callouts": 0,
                }
                records[identity] = record
            elif native_callout:
                for parent in reversed(stack):
                    if parent is not None:
                        parent["nested_callouts"] += 1
                        break
            stack.append(record)
            continue
        if re.match(r"^:{3,}\s*$", line):
            if stack:
                stack.pop()
            continue
        for record in (item for item in stack if item is not None):
            if re.match(r"^## (?!#)", line):
                record["headings"] += 1
            elif line.strip():
                record["content"] += line
    if code_fence:
        fail(f"{source}: unclosed fenced code block")
    if stack:
        fail(f"{source}: unclosed fenced division")


def validate_learning(book_root, registry):
    root = Path(book_root)
    records = {}
    for path in qmd_sources(root):
        _parse_source(path, path.relative_to(root).as_posix(), records)
    counts = {}
    for record in records.values():
        counts[record["type"]] = counts.get(record["type"], 0) + 1
    for block_type in TYPES:
        if not counts.get(block_type):
            fail(f"learning contract has no {block_type} specimen")
    for record in records.values():
        location = f"{record['source']}:{record['line']}"
        if record["headings"] != 1:
            fail(f"{location}: {record['type']} block must contain exactly one visible H2 title")
        if not record["content"].strip():
            fail(f"{location}: {record['type']} block has no content")
        if record["type"] not in {"exercise", "solution"}:
            if record["direct_callout"]:
                fail(f"{location}: {record['type']} identity must use a neutral wrapper around its native callout")
            if record["nested_callouts"] != 1:
                fail(f"{location}: {record['type']} block must contain exactly one native callout")
    for plan in (item for item in records.values() if item["type"] == "plan"):
        time = plan["attributes"].get("expected-time", "")
        difficulty = plan["attributes"].get("difficulty", "")
        location = f"{plan['source']}:{plan['line']}"
        if not re.fullmatch(r"[1-9][0-9]* (?:minute|minutes|hour|hours)", time):
            fail(f"{location}: learning plan has invalid expected-time")
        if difficulty not in {"foundational", "intermediate", "advanced"}:
            fail(f"{location}: learning plan has invalid difficulty")
        if time.lower() not in plan["content"].lower():
            fail(f"{location}: expected time must remain visible")
        if difficulty.lower() not in plan["content"].lower():
            fail(f"{location}: difficulty must remain visible")

    solutions_for, hints_for, answers_for = {}, {}, {}
    for record in records.values():
        if record["type"] not in {"solution", "hint", "answer-key"}:
            continue
        target = record["attributes"].get("data-for", "")
        location = f"{record['source']}:{record['line']}"
        if not target:
            fail(f"{location}: {record['type']} block needs a data-for= relationship")
        if target not in records:
            fail(f"{location}: {record['type']} targets unknown '{target}'")
        if record["type"] == "solution":
            if records[target]["type"] != "exercise":
                fail(f"solution '{record['id']}' must target an exercise")
            if solutions_for.get(target):
                fail(f"exercise '{target}' has more than one solution")
            solutions_for[target] = 1
        elif record["type"] == "hint":
            if records[target]["type"] != "review-question":
                fail(f"hint '{record['id']}' must target a review question")
            hints_for[target] = hints_for.get(target, 0) + 1
        else:
            if records[target]["type"] not in {"review-question", "exercise"}:
                fail(f"answer key '{record['id']}' must target a review question or exercise")
            if answers_for.get(target):
                fail(f"learning target '{target}' has more than one answer-key entry")
            answers_for[target] = 1
    for exercise in (item for item in records.values() if item["type"] == "exercise"):
        if not solutions_for.get(exercise["id"]):
            fail(f"exercise '{exercise['id']}' has no paired solution")
    for question in (item for item in records.values() if item["type"] == "review-question"):
        policy = question["attributes"].get("answer", "")
        if policy not in {"private", "none"}:
            fail(f"review question '{question['id']}' must declare answer=private or answer=none")
        if policy == "private" and not answers_for.get(question["id"]):
            fail(f"review question '{question['id']}' requires a private answer-key entry")
        if policy == "none" and answers_for.get(question["id"]):
            fail(f"review question '{question['id']}' forbids an answer-key entry")
    source_ids = {value["path"]: key for key, value in registry.get("sources", {}).items()}
    for answer in (item for item in records.values() if item["type"] == "answer-key"):
        source_id = source_ids.get(answer["source"])
        if not source_id:
            fail(f"answer-key source '{answer['source']}' is absent from the edition manifest")
        if registry["sources"][source_id].get("availability", "") != "private":
            fail(f"answer-key source '{answer['source']}' must have private availability")
        for edition_name, edition in registry.get("editions", {}).items():
            if edition.get("access", "") == "public" and source_id in _registered_selection(registry, edition_name):
                fail(f"public edition '{edition_name}' selects answer-key source '{answer['source']}'")
    return counts

