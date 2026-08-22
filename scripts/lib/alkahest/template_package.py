"""Extract and verify the reusable template engine package."""

import hashlib
import io
import json
import os
import re
import tempfile
import zipfile
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath

from .common import fail, load_json


POLICY_PATH = "config/template/template-package.json"
ID = re.compile(r"[a-z0-9]+(?:-[a-z0-9]+)*")
SEMVER = re.compile(
    r"(?:0|[1-9][0-9]*)\.(?:0|[1-9][0-9]*)\.(?:0|[1-9][0-9]*)"
)
PACKAGE_FILES = {"MANIFEST.json", "SHA256SUMS"}


def _exact(value, fields, label):
    if not isinstance(value, dict) or set(value) != set(fields):
        fail(f"{label} fields do not match the version 1 contract")
    return value


def _normalized(value, label):
    if not isinstance(value, str) or not value:
        fail(f"{label} must be a normalized relative path")
    path = PurePosixPath(value)
    if path.is_absolute() or ".." in path.parts or str(path) != value:
        fail(f"{label} must be a normalized relative path")
    return value


def _sha256(content):
    return hashlib.sha256(content).hexdigest()


def _source_date(root):
    policy = load_json(root / "book/reproducibility.json", "reproducibility policy")
    epoch = policy.get("source_date_epoch")
    source_date = policy.get("source_date_utc")
    if not isinstance(epoch, int) or epoch < 315532800:
        fail("template package needs a ZIP-compatible source_date_epoch")
    expected = datetime.fromtimestamp(epoch, timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    if source_date != expected:
        fail("template package source date differs from reproducibility policy")
    return epoch, source_date


def _exclusions(values, label):
    if not isinstance(values, list):
        fail(f"{label} exclude_patterns must be an array")
    compiled = []
    for value in values:
        if not isinstance(value, str) or not value:
            fail(f"{label} exclusion pattern must be nonempty")
        try:
            compiled.append(re.compile(value))
        except re.error as error:
            fail(f"{label} has invalid exclusion pattern: {error}")
    return compiled


def _walk_component(root, component):
    source_root = root / component["source"]
    if not source_root.is_dir() or source_root.is_symlink():
        fail(f"template component source is missing or unsafe: {component['source']}")
    exclusions = _exclusions(component["exclude_patterns"], component["id"])
    files = []
    for current, directories, names in os.walk(source_root, topdown=True, followlinks=False):
        current_path = Path(current)
        retained = []
        for directory in sorted(directories):
            candidate = current_path / directory
            relative = candidate.relative_to(source_root).as_posix()
            if any(pattern.search(relative + "/") for pattern in exclusions):
                continue
            if candidate.is_symlink():
                fail(f"template component contains symlink: {candidate.relative_to(root)}")
            retained.append(directory)
        directories[:] = retained
        for name in sorted(names):
            candidate = current_path / name
            relative = candidate.relative_to(source_root).as_posix()
            if any(pattern.search(relative) for pattern in exclusions):
                continue
            if candidate.is_symlink() or not candidate.is_file():
                fail(f"template component contains nonregular file: {candidate.relative_to(root)}")
            destination = str(PurePosixPath(component["destination"]) / relative)
            files.append((candidate.relative_to(root).as_posix(), destination))
    if not files:
        fail(f"template directory component is empty: {component['id']}")
    return files


def load_template_policy(root):
    """Validate the closed extraction boundary and return source mappings."""
    root = Path(root)
    policy = load_json(root / POLICY_PATH, "template package policy")
    _exact(
        policy,
        {
            "schema_version",
            "package",
            "directory_components",
            "file_components",
            "required_paths",
            "forbidden_content",
        },
        "template package policy",
    )
    if policy["schema_version"] != 1:
        fail("template package policy schema_version must be 1")
    package = _exact(
        policy["package"],
        {
            "id",
            "version",
            "filename",
            "root_name",
            "output_root",
            "license",
            "compression",
        },
        "template package",
    )
    if not isinstance(package["id"], str) or ID.fullmatch(package["id"]) is None:
        fail("template package id must be lowercase kebab-case")
    if not isinstance(package["version"], str) or SEMVER.fullmatch(package["version"]) is None:
        fail("template package version must use semantic versioning")
    expected_root = f"{package['id']}-{package['version']}"
    if package["root_name"] != expected_root or package["filename"] != expected_root + ".zip":
        fail("template package filename and root must derive from id and version")
    if package["output_root"] != "book/_build/template":
        fail("template package output must remain under book/_build/template")
    if package["license"] != "MIT":
        fail("template engine package must retain its MIT license")
    if package["compression"] != "stored":
        fail("template package compression must be stored for reproducibility")

    directories = policy["directory_components"]
    files = policy["file_components"]
    if not isinstance(directories, list) or not directories:
        fail("template package needs directory components")
    if not isinstance(files, list) or not files:
        fail("template package needs file components")
    identifiers = set()
    mappings = []
    for component in directories:
        _exact(
            component,
            {"id", "source", "destination", "exclude_patterns"},
            "template directory component",
        )
        identifier = component["id"]
        if not isinstance(identifier, str) or ID.fullmatch(identifier) is None:
            fail("template component id must be lowercase kebab-case")
        if identifier in identifiers:
            fail(f"template component id is duplicated: {identifier}")
        identifiers.add(identifier)
        _normalized(component["source"], f"template component {identifier} source")
        _normalized(component["destination"], f"template component {identifier} destination")
        mappings.extend(
            (source, destination, identifier)
            for source, destination in _walk_component(root, component)
        )
    for component in files:
        _exact(
            component,
            {"id", "source", "destination"},
            "template file component",
        )
        identifier = component["id"]
        if not isinstance(identifier, str) or ID.fullmatch(identifier) is None:
            fail("template component id must be lowercase kebab-case")
        if identifier in identifiers:
            fail(f"template component id is duplicated: {identifier}")
        identifiers.add(identifier)
        source = _normalized(component["source"], f"template component {identifier} source")
        destination = _normalized(
            component["destination"], f"template component {identifier} destination"
        )
        source_path = root / source
        if not source_path.is_file() or source_path.is_symlink():
            fail(f"template file component is missing or unsafe: {source}")
        mappings.append((source, destination, identifier))
    sources = [source for source, _destination, _identifier in mappings]
    destinations = [destination for _source, destination, _identifier in mappings]
    if len(sources) != len(set(sources)):
        fail("template package selects a source file more than once")
    if len(destinations) != len(set(destinations)):
        fail("template package maps more than one source to a destination")
    if PACKAGE_FILES & set(destinations):
        fail("template sources conflict with generated package files")

    required = policy["required_paths"]
    if not isinstance(required, list) or not required or len(required) != len(set(required)):
        fail("template package required_paths must be a unique nonempty array")
    for value in required:
        _normalized(value, "template required path")
        if value not in destinations:
            fail(f"template required path is not packaged: {value}")
    forbidden = policy["forbidden_content"]
    if not isinstance(forbidden, list) or not forbidden or any(
        not isinstance(value, str) or not value for value in forbidden
    ):
        fail("template forbidden_content must be a nonempty string array")
    return {
        "policy": policy,
        "package": package,
        "mappings": sorted(mappings, key=lambda item: item[1]),
        "required": required,
        "forbidden": forbidden,
    }


def validate_template_integration(root):
    """Keep extraction policy, package checks, CI, and documentation connected."""
    root = Path(root)
    files = {
        "makefile": root / "Makefile",
        "dispatcher": root / "scripts/check-source.py",
        "ci": root / "scripts/ci.sh",
        "readme": root / "README.md",
        "documentation": root / "docs/template-engine.md",
    }
    texts = {name: path.read_text(encoding="utf-8") for name, path in files.items()}
    for marker in (
        "check-template-engine:",
        "package-template-engine:",
        "check-template-package:",
        "test-template-engine:",
    ):
        if marker not in texts["makefile"]:
            fail(f"Makefile is missing template-engine target {marker}")
    for marker in (
        '("template-engine", "check-template-engine.py", False)',
        '("template-engine", "test-template-engine.py", False)',
    ):
        if marker not in texts["dispatcher"]:
            fail(f"source dispatcher is missing template-engine entry {marker}")
    for marker in ("package-template-engine.py", "check-template-package.py"):
        if marker not in texts["ci"]:
            fail(f"CI is missing template-engine command {marker}")
    if "make package-template-engine" not in texts["readme"]:
        fail("README is missing the template-engine author command")
    for marker in (
        "config/template/template-package.json",
        "make package-template-engine",
        "make check-template-package",
        "65 source files",
        "Deliberate boundary",
    ):
        if marker not in texts["documentation"]:
            fail(f"template-engine documentation is missing {marker!r}")


def template_members(root):
    root = Path(root)
    context = load_template_policy(root)
    _epoch, source_date = _source_date(root)
    members = {}
    records = []
    combined = []
    for source, destination, component in context["mappings"]:
        content = (root / source).read_bytes()
        members[destination] = content
        combined.append(content.decode("latin-1", errors="ignore"))
        records.append(
            {
                "component": component,
                "source": source,
                "path": destination,
                "sha256": _sha256(content),
                "bytes": len(content),
            }
        )
    text = "\n".join(combined)
    for marker in context["forbidden"]:
        if marker.casefold() in text.casefold():
            fail(f"template package contains specimen-specific content: {marker}")
    for marker in (str(root), "/workspace/"):
        if marker in text:
            fail(f"template package contains local build path: {marker}")
    manifest = {
        "schema_version": 1,
        "package": context["package"],
        "source_date_utc": source_date,
        "files": records,
        "required_paths": context["required"],
        "boundary": {
            "included": [
                "semantic Quarto extensions",
                "portable Lua filters",
                "shared brand and format themes",
                "Typst and LuaLaTeX book adapters",
                "shared Quarto and theme defaults",
                "deterministic cross-format theme synchronization",
                "reusable book-record schemas and ownership inventory",
                "minimal book.toml author compiler and render command",
            ],
            "deferred": [
                "schema and content migrations",
                "engine installation and upgrade migrations",
            ],
        },
    }
    members["MANIFEST.json"] = (
        json.dumps(manifest, indent=2, sort_keys=True) + "\n"
    ).encode("utf-8")
    checksums = [
        f"{_sha256(content)}  {path}" for path, content in sorted(members.items())
    ]
    members["SHA256SUMS"] = ("\n".join(checksums) + "\n").encode("utf-8")
    return context, members


def _archive_bytes(root_name, members, epoch):
    timestamp = datetime.fromtimestamp(epoch, timezone.utc).timetuple()[:6]
    output = io.BytesIO()
    with zipfile.ZipFile(output, "w", compression=zipfile.ZIP_STORED) as archive:
        for relative, content in sorted(members.items()):
            info = zipfile.ZipInfo(f"{root_name}/{relative}", timestamp)
            info.compress_type = zipfile.ZIP_STORED
            info.create_system = 3
            info.external_attr = 0o100644 << 16
            archive.writestr(info, content, compress_type=zipfile.ZIP_STORED)
    return output.getvalue()


def expected_template_outputs(root):
    root = Path(root)
    context, members = template_members(root)
    epoch, _source_date_value = _source_date(root)
    filename = context["package"]["filename"]
    archive = _archive_bytes(context["package"]["root_name"], members, epoch)
    outputs = {
        filename: archive,
        filename + ".sha256": f"{_sha256(archive)}  {filename}\n".encode("utf-8"),
    }
    return context, members, outputs


def package_template(root, output_root=None):
    context, members, outputs = expected_template_outputs(root)
    output_root = (
        Path(output_root)
        if output_root is not None
        else Path(root) / context["package"]["output_root"]
    )
    output_root.mkdir(parents=True, exist_ok=True)
    package_prefix = context["package"]["id"] + "-"
    for path in output_root.iterdir():
        if (
            path.is_file()
            and path.name.startswith(package_prefix)
            and (path.name.endswith(".zip") or path.name.endswith(".zip.sha256"))
            and path.name not in outputs
        ):
            path.unlink()
    for filename, content in outputs.items():
        (output_root / filename).write_bytes(content)
    return {
        "source_files": len(context["mappings"]),
        "members": len(members),
        "outputs": len(outputs),
        "bytes": len(outputs[context["package"]["filename"]]),
    }


def inspect_template_archive(filename, content, context, expected_members):
    try:
        with zipfile.ZipFile(io.BytesIO(content)) as archive:
            infos = archive.infolist()
            names = [info.filename for info in infos]
            if names != sorted(names) or len(names) != len(set(names)):
                fail("template package members must be unique and sorted")
            epoch, _source_date_value = _source_date_from_members(expected_members)
            timestamp = datetime.fromtimestamp(epoch, timezone.utc).timetuple()[:6]
            root_name = context["package"]["root_name"]
            relative = {}
            for info in infos:
                path = PurePosixPath(info.filename)
                if (
                    path.is_absolute()
                    or ".." in path.parts
                    or not path.parts
                    or path.parts[0] != root_name
                ):
                    fail(f"template package has unsafe member: {info.filename}")
                name = str(path.relative_to(root_name))
                if info.date_time != timestamp:
                    fail(f"template package member has unstable timestamp: {name}")
                if info.compress_type != zipfile.ZIP_STORED:
                    fail(f"template package member is compressed: {name}")
                if info.create_system != 3 or (info.external_attr >> 16) != 0o100644:
                    fail(f"template package member has unstable mode: {name}")
                relative[name] = archive.read(info)
            if set(relative) != set(expected_members):
                fail("template package member coverage is stale or incomplete")
            if any(relative[name] != value for name, value in expected_members.items()):
                fail("template package member content differs from canonical engine sources")
            checksum_lines = relative["SHA256SUMS"].decode("utf-8").splitlines()
            expected = {
                f"{_sha256(value)}  {name}"
                for name, value in relative.items()
                if name != "SHA256SUMS"
            }
            if set(checksum_lines) != expected or len(checksum_lines) != len(expected):
                fail("template package internal checksums are invalid")
            manifest = json.loads(relative["MANIFEST.json"])
            if manifest.get("schema_version") != 1:
                fail("template package manifest is invalid")
            return relative
    except (KeyError, UnicodeError, json.JSONDecodeError, zipfile.BadZipFile) as error:
        fail(f"cannot inspect template package '{filename}': {error}")


def _source_date_from_members(members):
    manifest = json.loads(members["MANIFEST.json"])
    value = manifest["source_date_utc"]
    parsed = datetime.strptime(value, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
    return int(parsed.timestamp()), value


def _extracted_smoke(relative, context):
    with tempfile.TemporaryDirectory(prefix="alkahest-template-engine.") as temporary:
        root = Path(temporary)
        for path, content in relative.items():
            target = root.joinpath(*PurePosixPath(path).parts)
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(content)
        if any(not (root / path).is_file() for path in context["required"]):
            fail("extracted template package is missing a required path")
        extension_manifests = sorted((root / "_extensions").glob("*/_extension.yml"))
        if len(extension_manifests) != 8:
            fail("extracted template package must contain eight extension manifests")
        for path in extension_manifests:
            text = path.read_text(encoding="utf-8")
            if "contributes:" not in text or "quarto-required:" not in text:
                fail(f"extracted template extension manifest is incomplete: {path.name}")
        if "#show" not in (root / "typst/typst-show.typ").read_text(encoding="utf-8"):
            fail("extracted template Typst adapter lacks its show rule")
        if "\\usepackage" not in (root / "latex/book-layout.tex").read_text(
            encoding="utf-8"
        ):
            fail("extracted template LuaLaTeX adapter lacks package configuration")


def check_template_package(root, output_root=None, extract=True):
    root = Path(root)
    context, members, outputs = expected_template_outputs(root)
    output_root = (
        Path(output_root)
        if output_root is not None
        else root / context["package"]["output_root"]
    )
    if not output_root.is_dir():
        fail("template package output directory is missing")
    actual = {path.name for path in output_root.iterdir()}
    if actual != set(outputs) or any(not (output_root / name).is_file() for name in outputs):
        fail("template package output files are stale or incomplete")
    relative = None
    for filename, expected in outputs.items():
        content = (output_root / filename).read_bytes()
        if content != expected:
            fail(f"template package output is stale or changed: {filename}")
        if filename.endswith(".zip"):
            relative = inspect_template_archive(filename, content, context, members)
    if extract:
        _extracted_smoke(relative, context)
    return {
        "source_files": len(context["mappings"]),
        "members": len(members),
        "outputs": len(outputs),
        "bytes": len(outputs[context["package"]["filename"]]),
        "extracted": extract,
    }
