"""Build and verify deterministic, self-contained companion ZIP bundles."""

import hashlib
import io
import json
import re
import zipfile
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath

from .common import fail, load_json
from .companions import validate_companions


def _sha256(content):
    return hashlib.sha256(content).hexdigest()


def _source_date(book_root):
    policy = load_json(book_root / "reproducibility.json", "reproducibility policy")
    epoch = policy.get("source_date_epoch")
    source_date = policy.get("source_date_utc")
    if not isinstance(epoch, int) or epoch < 315532800:
        fail("companion bundles need a ZIP-compatible source_date_epoch")
    expected = datetime.fromtimestamp(epoch, timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    if source_date != expected:
        fail("companion bundle source date does not match source_date_epoch")
    return epoch, source_date


def _readme(bundle_id, bundle, registry):
    lines = [
        f"# {bundle['title']}",
        "",
        f"Bundle ID: `{bundle_id}`  ",
        f"Version: `{bundle['version']}`  ",
        f"License: `{bundle['license']}`  ",
        f"Release path: `{bundle['release_path']}`",
        "",
        "## Compatibility",
        "",
    ]
    lines.extend(f"- {value}" for value in bundle["compatibility"])
    lines.extend(("", "## Included materials", ""))
    for item_id in bundle["items"]:
        item = registry["items"][item_id]
        lines.append(
            f"- `{item['path']}` — {item['title']} ({item['kind']}, version {item['version']})"
        )
    lines.extend(
        (
            "",
            "Verify the listed files with `SHA256SUMS` before use.",
            "",
            bundle["credit"],
            "",
        )
    )
    return "\n".join(lines).encode("utf-8")


def _manifest(bundle_id, bundle, registry, source_date):
    items = []
    for item_id in bundle["items"]:
        item = registry["items"][item_id]
        items.append(
            {
                "id": item_id,
                "kind": item["kind"],
                "title": item["title"],
                "path": item["path"],
                "media_type": item["media_type"],
                "version": item["version"],
                "sha256": item["sha256"],
                "compatibility": item["compatibility"],
                "description": item["description"],
            }
        )
    document = {
        "schema_version": 1,
        "bundle": {
            "id": bundle_id,
            "title": bundle["title"],
            "version": bundle["version"],
            "release_path": bundle["release_path"],
            "url": bundle.get("url") or None,
            "source_date_utc": source_date,
            "entrypoint": bundle["entrypoint"],
            "compatibility": bundle["compatibility"],
            "license": {
                "spdx": bundle["license"],
                "path": "LICENSE.txt",
                "sha256": bundle["license_sha256"],
                "credit": bundle["credit"],
            },
        },
        "items": items,
    }
    return (json.dumps(document, indent=2, sort_keys=True) + "\n").encode("utf-8")


def _bundle_members(book_root, bundle_id, bundle, registry, source_date):
    members = {}
    for item_id in bundle["items"]:
        item = registry["items"][item_id]
        members[item["path"]] = (book_root / item["path"]).read_bytes()
    members["LICENSE.txt"] = (book_root / bundle["license_path"]).read_bytes()
    members["MANIFEST.json"] = _manifest(bundle_id, bundle, registry, source_date)
    members["README.md"] = _readme(bundle_id, bundle, registry)
    checksum_lines = [f"{_sha256(content)}  {name}" for name, content in sorted(members.items())]
    members["SHA256SUMS"] = ("\n".join(checksum_lines) + "\n").encode("utf-8")
    return members


def _archive_bytes(root_name, members, epoch):
    timestamp = datetime.fromtimestamp(epoch, timezone.utc).timetuple()[:6]
    output = io.BytesIO()
    # Stored members avoid zlib-version variation, keeping bytes identical even
    # when this lightweight packager runs outside the publishing container.
    with zipfile.ZipFile(output, "w", compression=zipfile.ZIP_STORED) as archive:
        for relative, content in sorted(members.items()):
            info = zipfile.ZipInfo(f"{root_name}/{relative}", timestamp)
            info.compress_type = zipfile.ZIP_STORED
            info.create_system = 3
            info.external_attr = 0o100644 << 16
            archive.writestr(info, content, compress_type=zipfile.ZIP_STORED)
    return output.getvalue()


def bundle_outputs(book_root):
    """Return expected archive and sidecar bytes keyed by output filename."""
    book_root = Path(book_root)
    result = validate_companions(book_root)
    registry = result["registry"]
    epoch, source_date = _source_date(book_root)
    outputs = {}
    for bundle_id, bundle in sorted(registry["bundles"].items()):
        members = _bundle_members(book_root, bundle_id, bundle, registry, source_date)
        archive = _archive_bytes(bundle["filename"][:-4], members, epoch)
        outputs[bundle["filename"]] = archive
        sidecar_name = bundle["filename"] + ".sha256"
        outputs[sidecar_name] = (f"{_sha256(archive)}  {bundle['filename']}\n").encode("utf-8")
    return outputs, result


def package_companion_bundles(book_root, output_root):
    """Write every configured companion bundle and its outer checksum."""
    output_root = Path(output_root)
    outputs, result = bundle_outputs(book_root)
    output_root.mkdir(parents=True, exist_ok=True)
    for filename, content in outputs.items():
        (output_root / filename).write_bytes(content)
    return {
        "bundles": result["bundles"],
        "items": result["items"],
        "files": len(outputs),
    }


def _check_archive(filename, content, forbidden_patterns):
    try:
        with zipfile.ZipFile(io.BytesIO(content)) as archive:
            infos = archive.infolist()
            names = [info.filename for info in infos]
            if len(names) != len(set(names)):
                fail(f"companion bundle '{filename}' repeats an archive member")
            root_name = filename[:-4]
            for name in names:
                path = PurePosixPath(name)
                if (
                    path.is_absolute()
                    or ".." in path.parts
                    or not path.parts
                    or path.parts[0] != root_name
                ):
                    fail(f"companion bundle '{filename}' has unsafe member '{name}'")
            relative = {
                str(PurePosixPath(name).relative_to(root_name)): archive.read(name)
                for name in names
            }
            required = {"LICENSE.txt", "MANIFEST.json", "README.md", "SHA256SUMS"}
            if not required <= set(relative):
                fail(f"companion bundle '{filename}' lacks package documentation")
            manifest = json.loads(relative["MANIFEST.json"])
            if manifest.get("schema_version") != 1:
                fail(f"companion bundle '{filename}' has invalid manifest")
            checksums = relative["SHA256SUMS"].decode("utf-8").splitlines()
            expected = {
                f"{_sha256(data)}  {name}"
                for name, data in relative.items()
                if name != "SHA256SUMS"
            }
            if set(checksums) != expected or len(checksums) != len(expected):
                fail(f"companion bundle '{filename}' has invalid internal checksums")
            combined = b"\n".join(relative.values()).decode("latin-1", errors="ignore")
            for label, pattern in forbidden_patterns:
                if pattern.search(combined):
                    fail(
                        f"companion bundle '{filename}' matches forbidden content pattern '{label}'"
                    )
            for canary in (
                "internal editorial canary and must never appear in a public artifact",
                "Answer key: threshold evidence",
            ):
                if canary in combined:
                    fail(f"companion bundle '{filename}' contains private content")
    except (OSError, KeyError, UnicodeError, json.JSONDecodeError, zipfile.BadZipFile) as error:
        fail(f"cannot inspect companion bundle '{filename}': {error}")


def check_companion_bundles(book_root, output_root):
    """Require generated bundle bytes and checksums to match canonical inputs."""
    output_root = Path(output_root)
    book_root = Path(book_root)
    outputs, result = bundle_outputs(book_root)
    forbidden = []
    assets_path = book_root / "assets.json"
    if assets_path.is_file():
        assets = load_json(assets_path, "asset registry")
        for entry in assets.get("artifact_contract", {}).get("forbidden_content_patterns", []):
            try:
                forbidden.append((entry["label"], re.compile(entry["pattern"], re.I)))
            except (KeyError, re.error) as error:
                fail(f"invalid companion bundle privacy pattern: {error}")
    if output_root.is_dir():
        actual_names = {path.name for path in output_root.iterdir() if path.is_file()}
        unexpected = sorted(actual_names - set(outputs))
        if unexpected:
            fail(f"companion bundle output directory has unexpected files: {unexpected}")
    for filename, expected in outputs.items():
        path = output_root / filename
        if not path.is_file():
            fail(f"companion bundle output is missing: {filename}")
        actual = path.read_bytes()
        if actual != expected:
            fail(f"companion bundle output is stale or changed: {filename}")
        if filename.endswith(".zip"):
            _check_archive(filename, actual, forbidden)
    return {
        "bundles": result["bundles"],
        "items": result["items"],
        "files": len(outputs),
        "bytes": sum(len(content) for content in outputs.values()),
    }
