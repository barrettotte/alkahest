"""Validate companion materials, delivery metadata, and manuscript calls."""

import hashlib
import re
from pathlib import Path

from .common import fail, load_json, qmd_sources


KINDS = ("code", "dataset", "schematic", "bill-of-materials", "download")


def _safe_path(value):
    return re.fullmatch(r"companion/[A-Za-z0-9][A-Za-z0-9_.-]*(?:/[A-Za-z0-9][A-Za-z0-9_.-]*)*", value) is not None


def validate_companions(book_root):
    root = Path(book_root)
    registry = load_json(root / "companion.json", "companion registry")
    if registry.get("version", 0) != 1:
        fail("companion registry version must be 1")
    items = registry.get("items")
    if not isinstance(items, dict) or not items:
        fail("companion registry items must be a nonempty object")
    allowed_fields = {
        "kind", "title", "path", "media_type", "version", "sha256",
        "compatibility", "description", "release_path", "url",
    }
    paths, release_paths, kind_count = set(), set(), {}
    for item_id in sorted(items):
        if not re.fullmatch(r"asset-[a-z][a-z0-9-]*", item_id):
            fail(f"invalid companion ID '{item_id}'; expected asset-...")
        item = items[item_id]
        if not isinstance(item, dict):
            fail(f"companion item '{item_id}' must be an object")
        for field in item:
            if field not in allowed_fields:
                fail(f"companion item '{item_id}' has unknown field '{field}'")
        kind = item.get("kind", "")
        if kind not in KINDS:
            fail(f"companion item '{item_id}' has unsupported kind '{kind}'")
        kind_count[kind] = kind_count.get(kind, 0) + 1
        title = item.get("title", "")
        if not isinstance(title, str) or not re.fullmatch(r"\S(?:.*\S)?", title) or len(title) > 100:
            fail(f"companion item '{item_id}' needs a concise title")
        path = item.get("path", "")
        if not isinstance(path, str) or not _safe_path(path):
            fail(f"companion item '{item_id}' has unsafe path '{path}'")
        if path in paths:
            fail(f"companion path '{path}' is registered more than once")
        paths.add(path)
        file_path = root / path
        if not file_path.is_file():
            fail(f"companion item '{item_id}' references missing file '{path}'")
        media_type = item.get("media_type", "")
        if not isinstance(media_type, str) or not re.fullmatch(r"[a-z0-9.+-]+/[a-z0-9.+-]+", media_type, re.I):
            fail(f"companion item '{item_id}' has invalid media_type")
        version = item.get("version", "")
        if not isinstance(version, str) or not re.fullmatch(r"(?:0|[1-9][0-9]*)\.(?:0|[1-9][0-9]*)\.(?:0|[1-9][0-9]*)(?:-[0-9A-Za-z.-]+)?", version):
            fail(f"companion item '{item_id}' has invalid semantic version")
        digest = item.get("sha256", "")
        if not isinstance(digest, str) or not re.fullmatch(r"[0-9a-f]{64}", digest):
            fail(f"companion item '{item_id}' has invalid SHA-256")
        actual = hashlib.sha256(file_path.read_bytes()).hexdigest()
        if actual != digest:
            fail(f"companion item '{item_id}' checksum drift: expected {digest}, found {actual}")
        compatibility = item.get("compatibility")
        if not isinstance(compatibility, list) or not compatibility:
            fail(f"companion item '{item_id}' compatibility must be a nonempty array")
        seen = set()
        for value in compatibility:
            if not isinstance(value, str) or not re.fullmatch(r"\S(?:.*\S)?", value):
                fail(f"companion item '{item_id}' has invalid compatibility text")
            if value in seen:
                fail(f"companion item '{item_id}' repeats compatibility '{value}'")
            seen.add(value)
        description = item.get("description", "")
        if not isinstance(description, str) or not re.fullmatch(r"\S(?:.*\S)?", description) or len(description) < 20:
            fail(f"companion item '{item_id}' needs an accessible description")
        release_path, url = item.get("release_path", ""), item.get("url", "")
        if not url and not release_path:
            fail(f"companion item '{item_id}' needs a durable HTTPS URL or release_path")
        if release_path and (not isinstance(release_path, str) or not _safe_path(release_path)):
            fail(f"companion item '{item_id}' has unsafe release_path '{release_path}'")
        if release_path in release_paths:
            fail(f"release path '{release_path}' is registered more than once")
        if release_path:
            release_paths.add(release_path)
        if url and (not isinstance(url, str) or not re.fullmatch(r"https://[A-Za-z0-9.-]+(?::[0-9]+)?/[A-Za-z0-9._~:/?#\[\]@!$&'()*+,;=%-]+", url)):
            fail(f"companion item '{item_id}' has invalid durable URL")
    for kind in KINDS:
        if not kind_count.get(kind):
            fail(f"companion registry has no {kind} specimen")
    companion_root = root / "companion"
    for file_path in companion_root.rglob("*"):
        if file_path.is_file():
            relative = file_path.relative_to(root).as_posix()
            if relative not in paths:
                fail(f"unregistered companion file '{relative}'")

    calls = {}
    call_pattern = re.compile(r"\{\{<\s*alk-companion\s+(.+?)\s*>\}\}")
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
            if "](companion/" in line:
                fail(f"{source_path}:{line_number}: use alk-companion rather than a raw companion link")
            for match in call_pattern.finditer(line):
                parsed = re.fullmatch(r"(asset-[a-z][a-z0-9-]*)(.*)", match.group(1))
                if not parsed:
                    fail(f"{source_path}:{line_number}: invalid alk-companion ID")
                item_id, remainder = parsed.groups()
                if item_id not in items:
                    fail(f"{source_path}:{line_number}: unknown companion ID '{item_id}'")
                remainder = re.sub(r"\s+", "", remainder)
                if remainder:
                    fail(f"{source_path}:{line_number}: unexpected alk-companion arguments '{remainder}'")
                calls[item_id] = calls.get(item_id, 0) + 1
    for item_id in sorted(items):
        if not calls.get(item_id):
            fail(f"companion item '{item_id}' is never referenced")
        if calls[item_id] != 1:
            fail(f"companion item '{item_id}' is referenced more than once")
    return {"items": len(items), "calls": len(calls), "kinds": kind_count}

