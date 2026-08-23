"""Validate registered reusable fragments, parameters, and use sites."""

import hashlib
import re
from pathlib import Path

from .common import fail, load_json, qmd_sources


KINDS = ("notice", "definition", "legal", "example", "project-prerequisite")
CONTEXTS = {"front-matter", "chapter", "appendix", "project", "back-matter"}


def _parse_call(source, line_number, arguments):
    match = re.fullmatch(r"(reuse-[a-z][a-z0-9-]*)(.*)", arguments)
    if not match:
        fail(f"{source}:{line_number}: invalid alk-reuse ID")
    item_id, remainder = match.groups()
    kwargs = {}
    while remainder.strip():
        remainder = remainder.lstrip()
        argument = re.match(r'''^([a-z][a-z0-9_]*)=(?:"([^"]*)"|'([^']*)'|(\S+))(.*)$''', remainder)
        if not argument:
            fail(f"{source}:{line_number}: malformed alk-reuse arguments '{remainder}'")
        name, double, single, bare, remainder = argument.groups()
        if name in kwargs:
            fail(f"{source}:{line_number}: repeated alk-reuse argument '{name}'")
        value = double if double is not None else single if single is not None else bare
        if not value:
            fail(f"{source}:{line_number}: alk-reuse argument '{name}' cannot be empty")
        kwargs[name] = value
    return item_id, kwargs


def validate_reuse(book_root):
    root = Path(book_root)
    registry = load_json(root / "reusable-content.json", "reusable-content registry")
    if registry.get("version", 0) != 1:
        fail("reusable-content registry version must be 1")
    items = registry.get("items")
    if not isinstance(items, dict) or not items:
        fail("reusable-content registry items must be a nonempty object")
    allowed_fields = {"kind", "title", "path", "version", "sha256", "origin", "scope", "allowed_contexts", "parameters"}
    path_values = [item.get("path", "") for item in items.values() if isinstance(item, dict)]
    for path in path_values:
        if path and path_values.count(path) > 1:
            fail(f"reusable-content path '{path}' is registered more than once")

    paths, kind_count, parameters_by_id, contexts_by_id = set(), {}, {}, {}
    for item_id in sorted(items):
        if not re.fullmatch(r"reuse-[a-z][a-z0-9-]*", item_id):
            fail(f"invalid reusable-content ID '{item_id}'; expected reuse-...")
        item = items[item_id]
        if not isinstance(item, dict):
            fail(f"reusable-content item '{item_id}' must be an object")
        for field in item:
            if field not in allowed_fields:
                fail(f"reusable-content item '{item_id}' has unknown field '{field}'")
        kind = item.get("kind", "")
        if kind not in KINDS:
            fail(f"reusable-content item '{item_id}' has unsupported kind '{kind}'")
        kind_count[kind] = kind_count.get(kind, 0) + 1
        title = item.get("title", "")
        if not isinstance(title, str) or not re.fullmatch(r"\S(?:.*\S)?", title) or len(title) > 100:
            fail(f"reusable-content item '{item_id}' needs a concise title")
        path = item.get("path", "")
        if not isinstance(path, str) or not re.fullmatch(r"reuse/[A-Za-z0-9][A-Za-z0-9_.-]*(?:/[A-Za-z0-9][A-Za-z0-9_.-]*)*\.md", path):
            fail(f"reusable-content item '{item_id}' has unsafe path '{path}'")
        paths.add(path)
        fragment_path = root / path
        if not fragment_path.is_file():
            fail(f"reusable-content item '{item_id}' references missing fragment '{path}'")
        version = item.get("version", "")
        if not isinstance(version, str) or not re.fullmatch(r"(?:0|[1-9][0-9]*)\.(?:0|[1-9][0-9]*)\.(?:0|[1-9][0-9]*)(?:-[0-9A-Za-z.-]+)?", version):
            fail(f"reusable-content item '{item_id}' has invalid semantic version")
        digest = item.get("sha256", "")
        if not isinstance(digest, str) or not re.fullmatch(r"[0-9a-f]{64}", digest):
            fail(f"reusable-content item '{item_id}' has invalid SHA-256")
        actual = hashlib.sha256(fragment_path.read_bytes()).hexdigest()
        if actual != digest:
            fail(f"reusable-content item '{item_id}' checksum drift: expected {digest}, found {actual}")
        origin = item.get("origin", "")
        if not isinstance(origin, str) or not re.fullmatch(r"[a-z][a-z0-9-]*", origin):
            fail(f"reusable-content item '{item_id}' has invalid origin")
        if item.get("scope", "") not in {"book-local", "template-package"}:
            fail(f"reusable-content item '{item_id}' has unsupported scope")
        contexts = item.get("allowed_contexts")
        if not isinstance(contexts, list) or not contexts:
            fail(f"reusable-content item '{item_id}' allowed_contexts must be a nonempty array")
        context_set = set()
        for context in contexts:
            if not isinstance(context, str) or context not in CONTEXTS:
                fail(f"reusable-content item '{item_id}' has invalid context '{context}'")
            if context in context_set:
                fail(f"reusable-content item '{item_id}' repeats context '{context}'")
            context_set.add(context)
        contexts_by_id[item_id] = context_set
        parameters = item.get("parameters")
        if not isinstance(parameters, list):
            fail(f"reusable-content item '{item_id}' parameters must be an array")
        parameter_set = set()
        for parameter in parameters:
            if not isinstance(parameter, str) or not re.fullmatch(r"[a-z][a-z0-9_]*", parameter):
                fail(f"reusable-content item '{item_id}' has invalid parameter '{parameter}'")
            if parameter in parameter_set:
                fail(f"reusable-content item '{item_id}' repeats parameter '{parameter}'")
            parameter_set.add(parameter)
        parameters_by_id[item_id] = parameter_set
        fragment = fragment_path.read_text(encoding="utf-8")
        if not re.search(r"[A-Za-z]", fragment):
            fail(f"reusable fragment '{path}' must contain visible prose")
        if re.search(r"^\s*#", fragment, re.M):
            fail(f"reusable fragment '{path}' must not contain headings")
        if re.search(r'''\{#[A-Za-z]|\bid=["']''', fragment):
            fail(f"reusable fragment '{path}' must not define persistent IDs")
        if re.search(r"\{\{[<%]\s*alk-reuse\b", fragment):
            fail(f"reusable fragment '{path}' must not contain nested reuse calls")
        if re.search(r"\{\{[<%]\s*include\b", fragment):
            fail(f"reusable fragment '{path}' must not contain include directives")
        if re.search(r"\{=(?:html|latex|typst)\}|^\s*\\(?:begin|input|include)\b|</?[A-Za-z][^>]*>", fragment, re.M):
            fail(f"reusable fragment '{path}' must remain backend-neutral Markdown")
        placeholders = re.findall(r"\{\{([a-z][a-z0-9_]*)\}\}", fragment)
        placeholder_check = re.sub(r"\{\{[a-z][a-z0-9_]*\}\}", "", fragment)
        if "{{" in placeholder_check or "}}" in placeholder_check:
            fail(f"reusable fragment '{path}' contains a malformed placeholder")
        for parameter in sorted(parameter_set):
            if parameter not in placeholders:
                fail(f"reusable-content item '{item_id}' declares unused parameter '{parameter}'")
        for placeholder in sorted(set(placeholders)):
            if placeholder not in parameter_set:
                fail(f"reusable fragment '{path}' uses undeclared parameter '{placeholder}'")
    for kind in KINDS:
        if not kind_count.get(kind):
            fail(f"reusable-content registry has no {kind} specimen")
    for file_path in (root / "reuse").rglob("*"):
        if file_path.is_file():
            relative = file_path.relative_to(root).as_posix()
            if relative not in paths:
                fail(f"unregistered reusable fragment '{relative}'")

    calls, instances = {}, set()
    pattern = re.compile(r"\{\{<\s*alk-reuse\s+(.+?)\s*>\}\}")
    for source_path in qmd_sources(root):
        disabled_fence = ""
        for line_number, line in enumerate(source_path.read_text(encoding="utf-8").splitlines(), 1):
            if disabled_fence:
                if re.fullmatch(re.escape(disabled_fence) + r"\s*", line):
                    disabled_fence = ""
                continue
            fence = re.match(r"^(`{3,}|~{3,}).*\bshortcodes=false\b", line)
            if fence:
                disabled_fence = fence.group(1)
                continue
            if re.search(r'''(?:\]\(|include\s+)["']?reuse/''', line):
                fail(f"{source_path}:{line_number}: use alk-reuse rather than a raw reusable-fragment path")
            for match in pattern.finditer(line):
                item_id, kwargs = _parse_call(source_path, line_number, match.group(1))
                if item_id not in items:
                    fail(f"{source_path}:{line_number}: unknown reusable-content ID '{item_id}'")
                instance = kwargs.pop("id", "")
                if not re.fullmatch(r"reuse-use-[a-z][a-z0-9-]*", instance):
                    fail(f'{source_path}:{line_number}: reusable-content call \'{item_id}\' needs id="reuse-use-..."')
                if instance in instances:
                    fail(f"{source_path}:{line_number}: duplicate reusable-content instance '{instance}'")
                instances.add(instance)
                context = kwargs.pop("context", "")
                if context not in contexts_by_id[item_id]:
                    fail(f"{source_path}:{line_number}: reusable-content '{item_id}' is not allowed in context '{context}'")
                for parameter in sorted(parameters_by_id[item_id]):
                    if parameter not in kwargs:
                        fail(f"{source_path}:{line_number}: reusable-content '{item_id}' needs parameter '{parameter}'")
                    del kwargs[parameter]
                if kwargs:
                    fail(f"{source_path}:{line_number}: reusable-content '{item_id}' has unexpected argument '{sorted(kwargs)[0]}'")
                calls[item_id] = calls.get(item_id, 0) + 1
    for item_id in sorted(items):
        if not calls.get(item_id):
            fail(f"reusable-content item '{item_id}' is never referenced")
    return {"items": len(items), "calls": len(instances), "kinds": kind_count}

