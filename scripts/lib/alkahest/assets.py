"""Shared rights, asset-coverage, and release-privacy validation."""

from __future__ import annotations

import hashlib
import json
import re
import shutil
import subprocess
from datetime import date
from pathlib import Path, PurePosixPath
from zipfile import BadZipFile, ZipFile


RIGHTS_FIELDS = (
    "creator",
    "owner",
    "origin",
    "created",
    "license",
    "permission_evidence",
    "modifications",
    "credit_text",
    "public_distribution",
)
SHA256 = re.compile(r"[0-9a-f]{64}")
ID = re.compile(r"[a-z0-9]+(?:-[a-z0-9]+)*")


class AssetError(RuntimeError):
    """Report an invalid rights record or unsafe release asset."""


def fail(message):
    raise AssetError(message)


def read_json(path, label):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        fail(f"cannot read {label}: {error}")


def normalized_path(value, label):
    if not isinstance(value, str) or not value:
        fail(f"{label} must be a repository-relative path")
    path = PurePosixPath(value)
    if path.is_absolute() or ".." in path.parts or str(path) != value:
        fail(f"{label} must be a normalized repository-relative path")
    return path


def repo_path(root, value, label):
    path = normalized_path(value, label)
    return root.joinpath(*path.parts)


def book_path(root, value, label):
    path = normalized_path(value, label)
    return root / "book" / Path(*path.parts)


def digest_bytes(content):
    return hashlib.sha256(content).hexdigest()


def digest_file(path):
    return digest_bytes(path.read_bytes())


def validate_rights(record, label, allowed_licenses):
    for field in RIGHTS_FIELDS:
        if field not in record:
            fail(f"{label} is missing rights field '{field}'")
    for field in RIGHTS_FIELDS[:-1]:
        if not isinstance(record[field], str) or not record[field].strip():
            fail(f"{label} rights field '{field}' must be nonempty")
    try:
        date.fromisoformat(record["created"])
    except ValueError:
        fail(f"{label} created date must use ISO 8601")
    if record["license"] not in allowed_licenses:
        fail(f"{label} uses undeclared license '{record['license']}'")
    if not isinstance(record["public_distribution"], bool):
        fail(f"{label} public_distribution must be true or false")


def add_approved(approved, path, digest, label, is_public):
    normalized_path(path, f"{label} file")
    if not isinstance(digest, str) or not SHA256.fullmatch(digest):
        fail(f"{label} file {path} needs a lowercase SHA-256 digest")
    if path in approved:
        fail(f"asset path is declared more than once: {path}")
    if is_public:
        approved[path] = digest


def validate_collections(root, policy, allowed_licenses, approved):
    collections = policy.get("collections")
    if not isinstance(collections, list) or not collections:
        fail("asset policy needs nonempty collections")
    identifiers = set()
    file_count = 0
    for collection in collections:
        identifier = collection.get("id") if isinstance(collection, dict) else None
        if not isinstance(identifier, str) or not ID.fullmatch(identifier):
            fail("asset collection needs a kebab-case id")
        if identifier in identifiers:
            fail(f"duplicate asset collection id '{identifier}'")
        identifiers.add(identifier)
        label = f"asset collection {identifier}"
        validate_rights(collection, label, allowed_licenses)

        sources = collection.get("source_files")
        if not isinstance(sources, list):
            fail(f"{label} source_files must be an array")
        for source in sources:
            path = book_path(root, source, f"{label} source")
            if not path.is_file():
                fail(f"{label} source does not exist: {source}")

        files = collection.get("distributed_files")
        if not isinstance(files, dict) or not files:
            fail(f"{label} needs distributed_files")
        for path, expected in files.items():
            source = book_path(root, path, f"{label} distributed file")
            if not source.is_file():
                fail(f"{label} distributed file does not exist: {path}")
            actual = digest_file(source)
            if actual != expected:
                fail(f"{label} checksum drift for {path}: {actual}")
            add_approved(
                approved,
                path,
                expected,
                label,
                collection["public_distribution"],
            )
            file_count += 1

        globs = collection.get("coverage_globs")
        if not isinstance(globs, list) or not globs:
            fail(f"{label} needs coverage_globs")
        covered = {
            path.relative_to(root / "book").as_posix()
            for pattern in globs
            for path in (root / "book").glob(pattern)
            if path.is_file()
        }
        declared = set(files)
        if covered != declared:
            missing = sorted(covered - declared)
            stale = sorted(declared - covered)
            details = []
            if missing:
                details.append(f"unregistered: {', '.join(missing)}")
            if stale:
                details.append(f"not covered: {', '.join(stale)}")
            fail(f"{label} coverage mismatch ({'; '.join(details)})")
    return len(collections), file_count


def validate_registries(root, policy, allowed_licenses, approved):
    specifications = policy.get("registries")
    if not isinstance(specifications, list) or not specifications:
        fail("asset policy needs nonempty registries")
    identifiers = set()
    item_count = 0
    file_count = 0
    for specification in specifications:
        identifier = specification.get("id") if isinstance(specification, dict) else None
        if not isinstance(identifier, str) or not ID.fullmatch(identifier):
            fail("asset registry needs a kebab-case id")
        if identifier in identifiers:
            fail(f"duplicate asset registry id '{identifier}'")
        identifiers.add(identifier)
        label = f"asset registry {identifier}"
        registry_path = repo_path(root, specification.get("path"), f"{label} path")
        registry = read_json(registry_path, label)
        items = registry.get("items") if isinstance(registry, dict) else None
        if not isinstance(items, dict) or not items:
            fail(f"{label} needs nonempty items")
        fields = specification.get("file_fields")
        if not isinstance(fields, dict) or not fields:
            fail(f"{label} needs file_fields")
        defaults = specification.get("rights_defaults")
        if not isinstance(defaults, dict):
            fail(f"{label} needs rights_defaults")
        root_name = specification.get("root")
        registry_root = book_path(root, root_name, f"{label} root")
        if not registry_root.is_dir():
            fail(f"{label} root does not exist: {root_name}")

        declared_paths = set()
        for item_id, item in items.items():
            if not isinstance(item, dict):
                fail(f"{label} item {item_id} must be an object")
            rights = dict(defaults)
            rights.update(item)
            item_label = f"{label} item {item_id}"
            validate_rights(rights, item_label, allowed_licenses)
            found = False
            for path_field, hash_field in fields.items():
                if path_field not in item:
                    continue
                found = True
                path = item[path_field]
                expected = item.get(hash_field)
                source = book_path(root, path, f"{item_label} {path_field}")
                if not source.is_file():
                    fail(f"{item_label} file does not exist: {path}")
                if path in declared_paths:
                    fail(f"{label} declares file more than once: {path}")
                declared_paths.add(path)
                actual = digest_file(source)
                if actual != expected:
                    fail(f"{item_label} checksum drift for {path}: {actual}")
                add_approved(
                    approved,
                    path,
                    expected,
                    item_label,
                    rights["public_distribution"],
                )
                file_count += 1
            if not found:
                fail(f"{item_label} declares no asset files")
            item_count += 1

        actual_paths = {
            path.relative_to(root / "book").as_posix()
            for path in registry_root.rglob("*")
            if path.is_file()
        }
        if actual_paths != declared_paths:
            missing = sorted(actual_paths - declared_paths)
            stale = sorted(declared_paths - actual_paths)
            details = []
            if missing:
                details.append(f"unregistered: {', '.join(missing)}")
            if stale:
                details.append(f"missing: {', '.join(stale)}")
            fail(f"{label} file coverage mismatch ({'; '.join(details)})")
    return len(specifications), item_count, file_count


def validate_runtime_policy(policy):
    bundles = policy.get("runtime_bundles")
    if not isinstance(bundles, list) or not bundles:
        fail("asset policy needs runtime_bundles")
    identifiers = set()
    for bundle in bundles:
        identifier = bundle.get("id") if isinstance(bundle, dict) else None
        if not isinstance(identifier, str) or not ID.fullmatch(identifier):
            fail("runtime bundle needs a kebab-case id")
        if identifier in identifiers:
            fail(f"duplicate runtime bundle id '{identifier}'")
        identifiers.add(identifier)
        if bundle.get("kind") not in {"fonts", "generated-runtime"}:
            fail(f"runtime bundle {identifier} has unsupported kind")
        for field in ("html_root", "provider"):
            if not isinstance(bundle.get(field), str) or not bundle[field]:
                fail(f"runtime bundle {identifier} needs {field}")
        if bundle["kind"] == "generated-runtime":
            if not isinstance(bundle.get("license_evidence"), str) or not bundle[
                "license_evidence"
            ]:
                fail(f"runtime bundle {identifier} needs license_evidence")
        elif bundle.get("license") not in policy["allowed_licenses"]:
            fail(f"font bundle {identifier} uses an undeclared license")
    return len(bundles)


def load_policy(root, policy_path):
    policy = read_json(policy_path, "asset policy")
    if not isinstance(policy, dict) or policy.get("schema_version") != 1:
        fail("asset policy must use schema_version 1")
    licenses = policy.get("allowed_licenses")
    if not isinstance(licenses, list) or not licenses:
        fail("asset policy needs allowed_licenses")
    if any(not isinstance(value, str) or not value for value in licenses):
        fail("allowed_licenses must contain nonempty SPDX identifiers")
    approved = {}
    collection_count, collection_files = validate_collections(
        root, policy, set(licenses), approved
    )
    registry_count, item_count, registry_files = validate_registries(
        root, policy, set(licenses), approved
    )
    runtime_count = validate_runtime_policy(policy)
    contract = policy.get("artifact_contract")
    if not isinstance(contract, dict):
        fail("asset policy needs artifact_contract")
    return policy, approved, {
        "collections": collection_count,
        "registries": registry_count,
        "items": item_count,
        "files": collection_files + registry_files,
        "runtime_bundles": runtime_count,
    }


def forbidden_patterns(contract):
    patterns = contract.get("forbidden_content_patterns")
    if not isinstance(patterns, list) or not patterns:
        fail("artifact contract needs forbidden_content_patterns")
    compiled = []
    for record in patterns:
        if not isinstance(record, dict) or not record.get("label") or not record.get("pattern"):
            fail("forbidden content patterns need labels and expressions")
        try:
            compiled.append((record["label"], re.compile(record["pattern"], re.I)))
        except re.error as error:
            fail(f"invalid forbidden pattern {record['label']}: {error}")
    return compiled


def check_privacy(label, content, patterns):
    text = content.decode("latin-1", errors="ignore")
    for pattern_label, pattern in patterns:
        match = pattern.search(text)
        if match:
            fail(f"{label} contains {pattern_label}: {match.group(0)!r}")


def check_embedded_metadata(label, content):
    lower = label.lower()
    if lower.endswith((".jpg", ".jpeg")):
        for marker in (b"Exif\x00\x00", b"http://ns.adobe.com/xap/1.0/", b"Photoshop 3.0"):
            if marker in content:
                fail(f"{label} contains removable JPEG EXIF/XMP/editor metadata")
    elif lower.endswith(".png") and content.startswith(b"\x89PNG\r\n\x1a\n"):
        offset = 8
        while offset + 12 <= len(content):
            length = int.from_bytes(content[offset : offset + 4], "big")
            chunk = content[offset + 4 : offset + 8]
            if chunk in {b"eXIf", b"iTXt", b"tEXt", b"zTXt"}:
                fail(f"{label} contains removable PNG metadata chunk {chunk.decode()}")
            offset += 12 + length
    elif lower.endswith(".webp"):
        if b"EXIF" in content or b"XMP " in content:
            fail(f"{label} contains removable WebP EXIF/XMP metadata")
    elif lower.endswith(".svg"):
        text = content.decode("utf-8", errors="ignore")
        editor_markers = (
            "inkscape:export-filename",
            "sodipodi:docname",
            "<rdf:RDF",
        )
        for marker in editor_markers:
            if marker in text:
                fail(f"{label} contains removable SVG editor metadata: {marker}")
    elif lower.endswith(".wav") and content.startswith(b"RIFF"):
        if b"LIST" in content and b"INFO" in content:
            fail(f"{label} contains removable WAV INFO metadata")
        if b"ID3 " in content or b"XMP " in content:
            fail(f"{label} contains removable WAV ID3/XMP metadata")


def entry_patterns(contract):
    values = contract.get("forbidden_entry_patterns")
    if not isinstance(values, list) or not values:
        fail("artifact contract needs forbidden_entry_patterns")
    try:
        return [re.compile(value, re.I) for value in values]
    except re.error as error:
        fail(f"invalid forbidden entry pattern: {error}")


def check_entry_name(name, patterns):
    candidate = name[:-1] if name.endswith("/") else name
    if not candidate:
        fail("artifact contains an empty entry name")
    normalized_path(candidate, "artifact entry")
    for pattern in patterns:
        if pattern.search(name):
            fail(f"artifact contains temporary/private entry: {name}")


def check_html(root, policy, approved):
    contract = policy["artifact_contract"]
    html_root = repo_path(root, contract.get("html_root"), "HTML artifact root")
    if not html_root.is_dir():
        fail(f"HTML artifact root does not exist: {html_root}")
    privacy = forbidden_patterns(contract)
    entries = entry_patterns(contract)
    controlled_roots = {
        PurePosixPath(path).parts[0]
        for collection in policy["collections"]
        for path in collection["distributed_files"]
    }
    controlled_roots.update(specification["root"] for specification in policy["registries"])
    checked_assets = 0
    for path in sorted(html_root.rglob("*")):
        if not path.is_file():
            continue
        relative = path.relative_to(html_root).as_posix()
        check_entry_name(relative, entries)
        content = path.read_bytes()
        check_privacy(f"HTML entry {relative}", content, privacy)
        if PurePosixPath(relative).parts[0] in controlled_roots:
            if relative not in approved:
                fail(f"HTML contains asset absent from rights manifest: {relative}")
            actual = digest_bytes(content)
            if actual != approved[relative]:
                fail(f"HTML asset checksum drift: {relative}")
            check_embedded_metadata(f"HTML asset {relative}", content)
            checked_assets += 1

    for bundle in policy["runtime_bundles"]:
        bundle_root = html_root / Path(*PurePosixPath(bundle["html_root"]).parts)
        if not bundle_root.is_dir():
            fail(f"HTML runtime bundle is missing: {bundle['id']}")
        if bundle["kind"] == "generated-runtime":
            markers = bundle.get("required_markers")
            if not isinstance(markers, dict) or not markers:
                fail(f"runtime bundle {bundle['id']} needs required_markers")
            for relative, marker in markers.items():
                target = bundle_root / Path(*PurePosixPath(relative).parts)
                if not target.is_file() or marker not in target.read_text(
                    encoding="utf-8", errors="ignore"
                ):
                    fail(f"runtime license marker is missing: {bundle['id']} {relative}")
        else:
            license_files = bundle.get("html_license_files")
            if not isinstance(license_files, dict) or not license_files:
                fail(f"font bundle {bundle['id']} needs HTML license files")
            for relative, expected in license_files.items():
                target = bundle_root / Path(*PurePosixPath(relative).parts)
                if not target.is_file() or digest_file(target) != expected:
                    fail(f"font license file is missing or changed: {relative}")
    return checked_assets


def check_epub(root, policy, approved):
    contract = policy["artifact_contract"]
    epub_path = repo_path(root, contract.get("epub"), "EPUB artifact")
    if not epub_path.is_file():
        fail(f"EPUB artifact does not exist: {epub_path}")
    privacy = forbidden_patterns(contract)
    entries = entry_patterns(contract)
    approved_hashes = set(approved.values())
    media_count = 0
    try:
        with ZipFile(epub_path) as archive:
            names = archive.namelist()
            for name in names:
                check_entry_name(name, entries)
                content = archive.read(name)
                check_privacy(f"EPUB entry {name}", content, privacy)
                if name.startswith("EPUB/media/") and not name.endswith("/"):
                    if digest_bytes(content) not in approved_hashes:
                        fail(f"EPUB contains media absent from rights manifest: {name}")
                    check_embedded_metadata(f"EPUB media {name}", content)
                    media_count += 1
            styles = "\n".join(
                archive.read(name).decode("utf-8", errors="ignore")
                for name in names
                if name.endswith(".css")
            )
            for bundle in policy["runtime_bundles"]:
                if bundle["kind"] != "fonts":
                    continue
                font_root = bundle.get("epub_root")
                if not isinstance(font_root, str):
                    fail(f"font bundle {bundle['id']} needs epub_root")
                if not any(name.startswith(font_root + "/") for name in names):
                    fail(f"EPUB font bundle is missing: {bundle['id']}")
                for marker in bundle.get("epub_license_markers", []):
                    if marker not in styles:
                        fail(f"EPUB font license marker is missing: {marker}")
    except (BadZipFile, KeyError, UnicodeDecodeError) as error:
        fail(f"cannot inspect EPUB assets: {error}")
    return media_count


def parse_pdfinfo(output):
    fields = {}
    current = None
    for line in output.splitlines():
        match = re.match(r"^([A-Za-z][A-Za-z ]+):\s*(.*)$", line)
        if match:
            current = match.group(1).strip()
            fields[current] = match.group(2).strip()
        elif current and line.strip():
            fields[current] += "\n" + line.strip()
    return fields


def matches_one(value, expressions):
    return any(re.fullmatch(expression, value) for expression in expressions)


def validate_pdf_metadata(label, info, metadata, contract):
    fields = parse_pdfinfo(info)
    expected = {
        "Title": contract["expected_pdf_title"],
        "Author": contract["expected_pdf_author"],
    }
    for field, value in expected.items():
        if fields.get(field) != value:
            fail(f"{label} {field} metadata must be {value!r}; found {fields.get(field)!r}")
    if not matches_one(fields.get("Creator", ""), contract["allowed_pdf_creator_patterns"]):
        fail(f"{label} has unexpected PDF Creator metadata: {fields.get('Creator')!r}")
    if not matches_one(fields.get("Producer", ""), contract["allowed_pdf_producer_patterns"]):
        fail(f"{label} has unexpected PDF Producer metadata: {fields.get('Producer')!r}")
    for field in ("Subject", "Keywords"):
        if fields.get(field, ""):
            fail(f"{label} has unintended PDF {field} metadata")
    privacy = forbidden_patterns(contract)
    check_privacy(f"{label} PDF info", info.encode(), privacy)
    check_privacy(f"{label} PDF metadata", metadata.encode(), privacy)


def run_command(command, label):
    result = subprocess.run(command, check=False, capture_output=True, text=True)
    if result.returncode:
        fail(f"{label} failed: {result.stderr.strip() or result.stdout.strip()}")
    return result.stdout


def check_pdfs(root, policy):
    for command in ("pdfdetach", "pdfinfo"):
        if shutil.which(command) is None:
            fail(f"{command} is required for release-asset checks")
    contract = policy["artifact_contract"]
    pdf_policy_path = repo_path(root, contract.get("pdf_policy"), "PDF policy")
    pdf_policy = read_json(pdf_policy_path, "PDF policy")
    profiles = pdf_policy.get("profiles") if isinstance(pdf_policy, dict) else None
    if not isinstance(profiles, list) or not profiles:
        fail("PDF policy contains no profiles")
    privacy = forbidden_patterns(contract)
    for profile in profiles:
        label = profile.get("label", profile.get("id", "PDF"))
        path = repo_path(root, profile.get("artifact"), f"{label} artifact")
        if not path.is_file():
            fail(f"missing PDF artifact: {path}")
        info = run_command(["pdfinfo", str(path)], f"{label} pdfinfo")
        metadata = run_command(["pdfinfo", "-meta", str(path)], f"{label} XMP")
        attachments = run_command(["pdfdetach", "-list", str(path)], f"{label} attachments")
        validate_pdf_metadata(label, info, metadata, contract)
        if attachments.strip() != "0 embedded files":
            fail(f"{label} contains embedded files: {attachments.strip()}")
        check_privacy(f"{label} PDF bytes", path.read_bytes(), privacy)
    return len(profiles)
