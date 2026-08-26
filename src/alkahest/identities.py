"""Discover and validate manuscript, registry, asset, and reusable identities."""

import re
from pathlib import Path
from typing import Any

from .common import fail, load_json

IDENTITY_KINDS = (
    "chapter",
    "section",
    "figure",
    "table",
    "equation",
    "listing",
    "exercise",
    "solution",
    "learning-objectives",
    "learning-prerequisites",
    "learning-plan",
    "learning-summary",
    "review-question",
    "question-hint",
    "answer-key",
    "reusable-use",
    "glossary-term",
    "index-concept",
    "companion-asset",
    "reusable-content",
)


def load_identity_policy(path):
    policy = load_json(path, "identity policy")
    if policy.get("version", 0) != 1:
        fail("identity policy version must be 1")
    if not re.fullmatch(
        r"[A-Za-z]{2,3}(?:-[A-Za-z0-9]{2,8})*", policy.get("canonical_language", "")
    ):
        fail("identity policy canonical_language must be a BCP 47 tag")
    if not isinstance(policy.get("language_variants"), list) or not policy["language_variants"]:
        fail("identity policy language_variants must be a nonempty array")
    if not isinstance(policy.get("edition_manifests"), list):
        fail("identity policy edition_manifests must be an array")
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.-]*\.json", policy.get("companion_registry", "")):
        fail("identity policy companion_registry must name a root JSON file")
    if not re.fullmatch(
        r"[A-Za-z0-9][A-Za-z0-9_.-]*\.json", policy.get("reusable_content_registry", "")
    ):
        fail("identity policy reusable_content_registry must name a root JSON file")
    return policy


def identity_key(record):
    return (record["namespace"], record["id"])


def _add(records, record):
    key = identity_key(record)
    if key in records:
        previous = records[key]
        fail(
            f"duplicate {record['namespace']} identity '{record['id']}' in {record['source']} and {previous['source']}"
        )
    records[key] = record


def _content_kind(identity):
    prefixes = (
        ("fig-", "figure"),
        ("tbl-", "table"),
        ("eq-", "equation"),
        ("lst-", "listing"),
        ("exr-", "exercise"),
        ("sol-", "solution"),
        ("obj-", "learning-objectives"),
        ("pre-", "learning-prerequisites"),
        ("plan-", "learning-plan"),
        ("sum-", "learning-summary"),
        ("rev-", "review-question"),
        ("hint-", "question-hint"),
        ("ans-", "answer-key"),
        ("reuse-use-", "reusable-use"),
    )
    return next((kind for prefix, kind in prefixes if identity.startswith(prefix)), "anchor")


def _reject_setext(lines, source):
    fence, front = "", False
    for index, line in enumerate(lines):
        if index == 0 and re.fullmatch(r"---\s*\n?", line):
            front = True
            continue
        if front:
            if re.fullmatch(r"---\s*\n?", line):
                front = False
            continue
        if fence:
            if re.fullmatch(re.escape(fence) + r"\s*\n?", line):
                fence = ""
            continue
        opening = re.match(r"^(`{3,}|~{3,})", line)
        if opening:
            fence = opening.group(1)
            continue
        if index and re.fullmatch(r"(?:={2,}|-{2,})\s*\n?", line) and lines[index - 1].strip():
            fail(
                f"{source}:{index + 1}: Setext headings cannot carry the required explicit ID; use an ATX heading"
            )


def _scan_qmd(path, source, records):
    lines = Path(path).read_text(encoding="utf-8").splitlines(keepends=True)
    _reject_setext(lines, source)
    fence, executable, div_stack = "", False, []
    for number, line in enumerate(lines, 1):
        if fence:
            if re.fullmatch(re.escape(fence) + r"\s*\n?", line):
                fence, executable = "", False
                continue
            label = (
                re.fullmatch(r"\s*(?:#|%%|//)\|\s*label:\s*([A-Za-z][A-Za-z0-9_.:-]*)\s*\n?", line)
                if executable
                else None
            )
            if label:
                _add(
                    records,
                    {
                        "namespace": "content",
                        "id": label.group(1),
                        "kind": _content_kind(label.group(1)),
                        "source": source,
                        "line": number,
                    },
                )
            continue
        opening = re.match(r"^(`{3,}|~{3,})(.*)$", line)
        if opening:
            marker, info = opening.groups()
            for identity in re.findall(r"\{[^}\n]*#([A-Za-z][A-Za-z0-9_.:-]*)", info):
                _add(
                    records,
                    {
                        "namespace": "content",
                        "id": identity,
                        "kind": _content_kind(identity),
                        "source": source,
                        "line": number,
                    },
                )
            fence = marker
            executable = re.search(r"\{(?:mermaid|dot|graphviz|python|r|julia)\b", info) is not None
            continue
        division = re.match(r"^:{3,}\s+\{([^}]*)\}\s*$", line)
        if division:
            identity = re.search(r"#([A-Za-z][A-Za-z0-9_.:-]*)", division.group(1))
            div_stack.append(identity.group(1) if identity else "")
        elif re.match(r"^:{3,}\s*$", line) and div_stack:
            div_stack.pop()
        heading = re.match(r"^(#{1,6})\s+", line)
        if heading:
            ids = re.findall(r"\{[^}\n]*#([A-Za-z][A-Za-z0-9_.:-]*)", line)
            semantic = next(
                (
                    item
                    for item in reversed(div_stack)
                    if re.match(
                        r"^(?:ans|cau|cnj|cor|def|exm|exr|hint|imp|lab|lem|nte|obj|plan|pre|prp|project|rev|sol|sum|thm|tip|wrn)-",
                        item,
                    )
                ),
                None,
            )
            if semantic:
                if ids:
                    fail(
                        f"{source}:{number}: a semantic block title must use its enclosing '{semantic}' identity, not a second heading ID"
                    )
                continue
            if len(ids) != 1:
                fail(
                    f"{source}:{number}: every heading must have exactly one explicit persistent ID"
                )
            _add(
                records,
                {
                    "namespace": "content",
                    "id": ids[0],
                    "kind": "chapter" if len(heading.group(1)) == 1 else "section",
                    "source": source,
                    "line": number,
                },
            )
            continue
        for identity in re.findall(r"\{[^}\n]*#([A-Za-z][A-Za-z0-9_.:-]*)", line) + re.findall(
            r"""\bid=["']([A-Za-z][A-Za-z0-9_.:-]*)["']""", line
        ):
            _add(
                records,
                {
                    "namespace": "content",
                    "id": identity,
                    "kind": _content_kind(identity),
                    "source": source,
                    "line": number,
                },
            )
    if fence:
        fail(f"{source}: unclosed fenced code block")


def _yaml_keys(path, section, namespace, kind, source, records):
    inside = found = False
    for number, line in enumerate(Path(path).read_text(encoding="utf-8").splitlines(), 1):
        if not inside and re.fullmatch(re.escape(section) + r":\s*", line):
            inside = found = True
            continue
        if not inside:
            continue
        if line and not line[0].isspace():
            break
        match = re.fullmatch(r"  ([a-z][a-z0-9-]*):\s*", line)
        if match:
            _add(
                records,
                {
                    "namespace": namespace,
                    "id": match.group(1),
                    "kind": kind,
                    "source": source,
                    "line": number,
                },
            )
    if not found:
        fail(f"{source} has no '{section}' mapping")
    if not any(record["namespace"] == namespace for record in records.values()):
        fail(f"{source} has no persistent {kind} identities")


def inventory_book(book_root, policy, variant):
    book_root = Path(book_root).resolve()
    variant_root = variant.get("root", "")
    if variant_root != "." and not re.fullmatch(r"[a-zA-Z0-9][a-zA-Z0-9_./-]*", variant_root):
        fail(f"invalid language-variant root '{variant_root}'")
    if ".." in Path(variant_root).parts:
        fail("language-variant root must not contain '..'")
    content_root = (book_root / variant_root).resolve()
    if not content_root.is_dir():
        fail(f"language-variant root '{variant_root}' does not exist")
    excluded = []
    for other in policy["language_variants"]:
        if other.get("root", "") == variant_root:
            continue
        candidate = (book_root / other.get("root", "")).resolve()
        try:
            candidate.relative_to(content_root)
        except ValueError:
            continue
        excluded.append(candidate)
    qmd = []
    for path in content_root.rglob("*.qmd"):
        if any(part in {"_build", "_extensions", ".quarto"} for part in path.parts):
            continue
        if any(path == item or item in path.parents for item in excluded):
            continue
        qmd.append(path)
    if not qmd:
        fail(f"language variant '{variant['language']}' contains no manuscript sources")
    records: dict[tuple[str, str], dict[str, Any]] = {}
    for path in sorted(qmd):
        _scan_qmd(path, path.relative_to(content_root).as_posix(), records)
    for filename, section, namespace, kind in (
        ("glossary.yml", "terms", "glossary", "glossary-term"),
        ("index.yml", "entries", "index", "index-concept"),
    ):
        path = content_root / filename
        if not path.is_file():
            fail(f"language variant '{variant['language']}' is missing {filename}")
        _yaml_keys(path, section, namespace, kind, filename, records)
    return records


def _validate_variants(book_root, policy):
    languages, canonical = set(), []
    for variant in policy["language_variants"]:
        if not isinstance(variant, dict):
            fail("each language variant must be an object")
        language = variant.get("language", "")
        if not re.fullmatch(r"[A-Za-z]{2,3}(?:-[A-Za-z0-9]{2,8})*", language):
            fail(f"invalid language-variant tag '{language}'")
        if language in languages:
            fail(f"duplicate language variant '{language}'")
        languages.add(language)
        mode = variant.get("mode", "")
        if mode not in {"canonical", "shared-source", "translated"}:
            fail(f"unsupported language-variant mode '{mode}'")
        if mode == "canonical":
            canonical.append(variant)
        root = variant.get("root", "")
        if root != "." and not re.fullmatch(r"[a-zA-Z0-9][a-zA-Z0-9_./-]*", root):
            fail(f"invalid language-variant root '{root}'")
        if ".." in Path(root).parts:
            fail(f"language-variant root '{root}' must not contain '..'")
        if not (Path(book_root) / root).is_dir():
            fail(f"language-variant root '{root}' does not exist")
        if "profile" in variant:
            profile = variant["profile"]
            if (
                not re.fullmatch(r"_quarto-[a-zA-Z0-9-]+\.yml", profile)
                or not (Path(book_root) / profile).is_file()
            ):
                fail(f"invalid language profile '{profile}'")
            declared = re.findall(
                r"^lang:\s*([A-Za-z0-9-]+)\s*$",
                (Path(book_root) / profile).read_text(encoding="utf-8"),
                re.MULTILINE,
            )
            if declared != [language]:
                fail(f"language profile '{profile}' must declare lang: {language} exactly once")
        if mode == "shared-source" and "profile" not in variant:
            fail(f"shared-source language '{language}' needs an explicit locale profile")
    if len(canonical) != 1:
        fail("identity policy must declare exactly one canonical language variant")
    if canonical[0]["language"] != policy["canonical_language"]:
        fail("canonical variant language must match canonical_language")
    return canonical[0]


def canonical_variant(book_root, policy):
    return _validate_variants(book_root, policy)


def validate_language_variants(book_root, policy, canonical_records):
    canonical = _validate_variants(book_root, policy)
    semantic = {
        key: value["kind"]
        for key, value in canonical_records.items()
        if value["namespace"] not in {"asset", "reuse"}
    }
    for variant in policy["language_variants"]:
        if variant["mode"] == "canonical":
            continue
        if variant["mode"] == "shared-source":
            if variant["root"] != canonical["root"]:
                fail(f"shared-source language '{variant['language']}' must use the canonical root")
            continue
        translated = {
            key: value["kind"] for key, value in inventory_book(book_root, policy, variant).items()
        }
        for key in sorted(semantic):
            namespace, identity = key
            if key not in translated:
                fail(
                    f"translation '{variant['language']}' is missing {namespace} identity '{identity}'"
                )
            if translated[key] != semantic[key]:
                fail(
                    f"translation '{variant['language']}' changes the kind of {namespace} identity '{identity}'"
                )
        for key in sorted(translated):
            if key not in semantic:
                fail(
                    f"translation '{variant['language']}' adds unmatched {key[0]} identity '{key[1]}'"
                )
    return canonical


def add_companion_assets(book_root, policy, records):
    registry = load_json(Path(book_root) / policy["companion_registry"], "companion registry")
    if registry.get("version", 0) != 1:
        fail("companion registry version must be 1")
    items = registry.get("items")
    if not isinstance(items, dict) or not items:
        fail("companion registry items must be a nonempty object")
    paths = set()
    for identity in sorted(items):
        if not re.fullmatch(r"asset-[a-z][a-z0-9-]*", identity):
            fail(f"invalid companion-asset ID '{identity}'; expected asset-...")
        asset = items[identity]
        if not isinstance(asset, dict):
            fail(f"companion asset '{identity}' must be an object")
        path = asset.get("path", "")
        if not re.fullmatch(
            r"companion/[A-Za-z0-9][A-Za-z0-9_.-]*(?:/[A-Za-z0-9][A-Za-z0-9_.-]*)*", path
        ):
            fail(f"invalid companion-asset path for '{identity}'")
        if path in paths:
            fail(f"companion-asset path '{path}' is registered more than once")
        paths.add(path)
        if not (Path(book_root) / path).is_file():
            fail(f"companion asset '{identity}' references missing file '{path}'")
        if not re.fullmatch(
            r"[a-z0-9.+-]+/[a-z0-9.+-]+", asset.get("media_type", ""), re.IGNORECASE
        ):
            fail(f"companion asset '{identity}' needs a media_type")
        if not asset.get("description", "").strip():
            fail(f"companion asset '{identity}' needs a concise description")
        _add(
            records,
            {"namespace": "asset", "id": identity, "kind": "companion-asset", "source": path},
        )


def add_reusable_content(book_root, policy, records):
    registry = load_json(
        Path(book_root) / policy["reusable_content_registry"], "reusable-content registry"
    )
    if registry.get("version", 0) != 1:
        fail("reusable-content registry version must be 1")
    items = registry.get("items")
    if not isinstance(items, dict) or not items:
        fail("reusable-content registry items must be a nonempty object")
    paths = set()
    for identity in sorted(items):
        if not re.fullmatch(r"reuse-[a-z][a-z0-9-]*", identity):
            fail(f"invalid reusable-content ID '{identity}'; expected reuse-...")
        item = items[identity]
        if not isinstance(item, dict):
            fail(f"reusable-content item '{identity}' must be an object")
        path = item.get("path", "")
        if not re.fullmatch(
            r"reuse/[A-Za-z0-9][A-Za-z0-9_.-]*(?:/[A-Za-z0-9][A-Za-z0-9_.-]*)*\.md", path
        ):
            fail(f"invalid reusable-content path for '{identity}'")
        if path in paths:
            fail(f"reusable-content path '{path}' is registered more than once")
        paths.add(path)
        if not (Path(book_root) / path).is_file():
            fail(f"reusable-content item '{identity}' references missing fragment '{path}'")
        if not item.get("title", "").strip():
            fail(f"reusable-content item '{identity}' needs a concise title")
        if not re.fullmatch(r"\d+\.\d+\.\d+(?:-[0-9A-Za-z.-]+)?", item.get("version", "")):
            fail(f"reusable-content item '{identity}' needs a semantic version")
        _add(
            records,
            {"namespace": "reuse", "id": identity, "kind": "reusable-content", "source": path},
        )


def validate_edition_manifests(book_root, policy, records):
    for manifest_path in policy["edition_manifests"]:
        if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.-]*\.json", manifest_path):
            fail(f"invalid edition-manifest path '{manifest_path}'")
        manifest = load_json(Path(book_root) / manifest_path, "edition manifest")
        if not all(
            isinstance(manifest.get(field), dict) for field in ("sources", "structures", "editions")
        ):
            fail(
                f"edition manifest '{manifest_path}' must have source, structure, and edition objects"
            )
        for source_id in sorted(manifest["sources"]):
            source_path = manifest["sources"][source_id].get("path", "")
            chapters = [
                record
                for record in records.values()
                if record["namespace"] == "content"
                and record["kind"] == "chapter"
                and record["source"] == source_path
            ]
            if len(chapters) != 1:
                fail(
                    f"edition source '{source_id}' in {manifest_path} must resolve to one persistently identified chapter"
                )
        for name in sorted(manifest["structures"]):
            selected = set()
            structure = manifest["structures"][name]
            groups = []
            for item in structure.get("chapters", []):
                groups.append([item["source"]] if "source" in item else item.get("sources", []))
            groups.extend(group.get("sources", []) for group in structure.get("appendices", []))
            for group in groups:
                for source_id in group:
                    if source_id not in manifest["sources"]:
                        fail(f"edition structure '{name}' references unknown source '{source_id}'")
                    if source_id in selected:
                        fail(f"edition structure '{name}' repeats source '{source_id}'")
                    selected.add(source_id)
            if not selected:
                fail(f"edition structure '{name}' has no persistently identified sources")


def inventory_identity_book(book_root):
    """Build the canonical identity inventory shared by source and rendered checks."""
    book_root = Path(book_root).resolve()
    if not book_root.is_dir():
        fail("identity book root does not exist")
    policy = load_identity_policy(book_root / "identities.json")
    records = inventory_book(book_root, policy, canonical_variant(book_root, policy))
    add_companion_assets(book_root, policy, records)
    add_reusable_content(book_root, policy, records)
    validate_language_variants(book_root, policy, records)
    validate_edition_manifests(book_root, policy, records)
    return policy, records


def validate_identity_book(book_root):
    """Validate the current canonical identity inventory."""
    policy, records = inventory_identity_book(book_root)
    counts: dict[str, int] = {}
    for record in records.values():
        counts[record["kind"]] = counts.get(record["kind"], 0) + 1
    return {
        "identities": len(records),
        "counts": counts,
        "language_variants": len(policy["language_variants"]),
        "edition_manifests": len(policy["edition_manifests"]),
    }
