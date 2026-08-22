"""Build, inspect, and restore deterministic private source archives."""

import hashlib
import io
import json
import os
import re
import subprocess
import sys
import tempfile
import zipfile
from datetime import date, datetime, timezone
from pathlib import Path, PurePosixPath

from .common import fail, load_json


POLICY_PATH = "config/archive/source-package.json"
PACKAGE_METADATA_ROOT = ".archive"
RESERVED_MEMBERS = {
    f"{PACKAGE_METADATA_ROOT}/MANIFEST.json",
    f"{PACKAGE_METADATA_ROOT}/README.md",
    f"{PACKAGE_METADATA_ROOT}/DEPENDENCIES.json",
    f"{PACKAGE_METADATA_ROOT}/SHA256SUMS",
}
ROLE_NAMES = {
    "canonical_manuscripts",
    "metadata",
    "rights_records",
    "dependency_inventory",
    "lock_data",
    "build_instructions",
    "changelog",
    "redirects",
    "prior_editions",
}
DEPENDENCY_FIELDS = {
    "container_definition",
    "human_lock_record",
    "python_manifest",
    "python_lock",
    "writing_manifest",
    "writing_lock",
}
SOURCE_ROOTS = {
    ".github",
    ".vale",
    "book",
    "config",
    "docs",
    "scripts",
    "template",
    "tests",
    "tools",
}
ID = re.compile(r"[a-z0-9]+(?:-[a-z0-9]+)*")
SEMVER = re.compile(
    r"(?:0|[1-9][0-9]*)\.(?:0|[1-9][0-9]*)\.(?:0|[1-9][0-9]*)"
)
SHA256 = re.compile(r"[0-9a-f]{64}")


def _exact(value, fields, label):
    if not isinstance(value, dict) or set(value) != set(fields):
        fail(f"{label} fields do not match the version 1 contract")
    return value


def _normalized(value, label):
    if not isinstance(value, str) or not value:
        fail(f"{label} must be a repository-relative path")
    path = PurePosixPath(value)
    if path.is_absolute() or ".." in path.parts or str(path) != value:
        fail(f"{label} must be a normalized repository-relative path")
    return value


def _sha256(content):
    return hashlib.sha256(content).hexdigest()


def _source_date(root):
    reproduction = load_json(root / "book/reproducibility.json", "reproducibility policy")
    epoch = reproduction.get("source_date_epoch")
    source_date = reproduction.get("source_date_utc")
    if not isinstance(epoch, int) or epoch < 315532800:
        fail("source archive needs a ZIP-compatible source_date_epoch")
    expected = datetime.fromtimestamp(epoch, timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    if source_date != expected:
        fail("source archive date differs from reproducibility policy")
    return epoch, source_date


def _compile_exclusions(values):
    if not isinstance(values, list) or not values:
        fail("source archive needs exclusion patterns")
    compiled = []
    for value in values:
        if not isinstance(value, str) or not value:
            fail("source archive exclusion patterns must be nonempty strings")
        try:
            compiled.append(re.compile(value))
        except re.error as error:
            fail(f"source archive has invalid exclusion pattern: {error}")
    return compiled


def _excluded(path, patterns):
    return any(pattern.search(path) for pattern in patterns)


def _walk_root(root, relative_root, exclusions):
    selected = []
    source_root = root / relative_root
    if not source_root.is_dir() or source_root.is_symlink():
        fail(f"source archive root is missing or unsafe: {relative_root}")
    for current, directories, files in os.walk(source_root, topdown=True, followlinks=False):
        current_path = Path(current)
        retained = []
        for directory in sorted(directories):
            candidate = current_path / directory
            relative = candidate.relative_to(root).as_posix()
            if _excluded(relative + "/", exclusions):
                continue
            if candidate.is_symlink():
                fail(f"source archive cannot contain symlink: {relative}")
            retained.append(directory)
        directories[:] = retained
        for filename in sorted(files):
            candidate = current_path / filename
            relative = candidate.relative_to(root).as_posix()
            if _excluded(relative, exclusions):
                continue
            if candidate.is_symlink() or not candidate.is_file():
                fail(f"source archive cannot contain nonregular file: {relative}")
            selected.append(relative)
    return selected


def _validate_redirects(root, work_id):
    document = load_json(root / "book/redirects.json", "redirect registry")
    _exact(document, {"schema_version", "work_id", "redirects"}, "redirect registry")
    if document["schema_version"] != 1 or document["work_id"] != work_id:
        fail("redirect registry identity differs from publication metadata")
    redirects = document["redirects"]
    if not isinstance(redirects, list):
        fail("redirect registry redirects must be an array")
    sources = set()
    for record in redirects:
        _exact(record, {"from", "to", "effective_date", "reason"}, "redirect record")
        for field in ("from", "to"):
            value = record[field]
            if (
                not isinstance(value, str)
                or not value.startswith("/")
                or ".." in PurePosixPath(value).parts
                or str(PurePosixPath(value)) != value
            ):
                fail(f"redirect {field} must be a normalized root-relative URL path")
        if record["from"] == record["to"]:
            fail("redirect source and target must differ")
        if record["from"] in sources:
            fail(f"redirect source is duplicated: {record['from']}")
        sources.add(record["from"])
        try:
            date.fromisoformat(record["effective_date"])
        except (TypeError, ValueError):
            fail("redirect effective_date must use ISO 8601")
        if not isinstance(record["reason"], str) or not record["reason"].strip():
            fail("redirect reason must be nonempty")
    return redirects


def _validate_prior_editions(root, work_id):
    document = load_json(root / "book/prior-editions.json", "prior-edition registry")
    _exact(document, {"schema_version", "work_id", "editions"}, "prior-edition registry")
    if document["schema_version"] != 1 or document["work_id"] != work_id:
        fail("prior-edition registry identity differs from publication metadata")
    editions = document["editions"]
    if not isinstance(editions, list):
        fail("prior-edition registry editions must be an array")
    identifiers = set()
    for record in editions:
        _exact(
            record,
            {
                "id",
                "edition_statement",
                "publication_date",
                "identifiers",
                "archive_uri",
                "manifest_sha256",
            },
            "prior-edition record",
        )
        identifier = record["id"]
        if not isinstance(identifier, str) or ID.fullmatch(identifier) is None:
            fail("prior-edition id must be lowercase kebab-case")
        if identifier in identifiers:
            fail(f"prior-edition id is duplicated: {identifier}")
        identifiers.add(identifier)
        if not isinstance(record["edition_statement"], str) or not record[
            "edition_statement"
        ].strip():
            fail("prior-edition statement must be nonempty")
        try:
            date.fromisoformat(record["publication_date"])
        except (TypeError, ValueError):
            fail("prior-edition publication_date must use ISO 8601")
        values = record["identifiers"]
        if not isinstance(values, list) or not values or any(
            not isinstance(value, str) or not value for value in values
        ):
            fail("prior-edition identifiers must be nonempty strings")
        uri = record["archive_uri"]
        if not isinstance(uri, str) or not re.match(r"^(?:https://|urn:)", uri):
            fail("prior-edition archive_uri must be HTTPS or a URN")
        digest = record["manifest_sha256"]
        if not isinstance(digest, str) or SHA256.fullmatch(digest) is None:
            fail("prior-edition manifest_sha256 must be a lowercase SHA-256 digest")
    return editions


def _validate_integration(root):
    files = {
        "makefile": root / "Makefile",
        "dispatcher": root / "scripts/check-source.py",
        "ci": root / "scripts/ci.sh",
        "readme": root / "README.md",
        "documentation": root / "docs/archives.md",
    }
    texts = {name: path.read_text(encoding="utf-8") for name, path in files.items()}
    for marker in (
        "check-archive-policy:",
        "package-source-archive:",
        "check-source-archive:",
        "test-source-archive:",
    ):
        if marker not in texts["makefile"]:
            fail(f"Makefile is missing source-archive target {marker}")
    for marker in (
        '("source-archive", "check-archive-policy.py", False)',
        '("source-archive", "test-source-archive.py", False)',
    ):
        if marker not in texts["dispatcher"]:
            fail(f"source dispatcher is missing source-archive entry {marker}")
    for marker in ("package-source-archive.py", "check-source-archive.py"):
        if marker not in texts["ci"]:
            fail(f"CI is missing source-archive command {marker}")
    if "make package-source-archive" not in texts["readme"]:
        fail("README is missing the source-archive author command")
    for marker in (
        "config/archive/source-package.json",
        "book/redirects.json",
        "book/prior-editions.json",
        "make check-source-archive",
        "private recovery snapshot",
    ):
        if marker not in texts["documentation"]:
            fail(f"source-archive documentation is missing {marker!r}")


def load_archive_policy(root):
    """Validate archive policy, history registries, and exact source selection."""
    root = Path(root)
    policy = load_json(root / POLICY_PATH, "source archive policy")
    _exact(
        policy,
        {
            "schema_version",
            "package",
            "root_files",
            "source_roots",
            "exclude_patterns",
            "required_roles",
            "dependency_files",
            "restoration",
        },
        "source archive policy",
    )
    if policy["schema_version"] != 1:
        fail("source archive policy schema_version must be 1")
    package = _exact(
        policy["package"],
        {
            "id",
            "version",
            "filename",
            "root_name",
            "output_root",
            "confidentiality",
            "compression",
        },
        "source archive package",
    )
    if not isinstance(package["id"], str) or ID.fullmatch(package["id"]) is None:
        fail("source archive package id must be lowercase kebab-case")
    if not isinstance(package["version"], str) or SEMVER.fullmatch(package["version"]) is None:
        fail("source archive package version must use semantic versioning")
    expected_root = f"{package['id']}-{package['version']}"
    if package["root_name"] != expected_root or package["filename"] != expected_root + ".zip":
        fail("source archive filename and root must derive from id and version")
    if package["output_root"] != "book/_build/archive":
        fail("source archive output must remain under book/_build/archive")
    if package["confidentiality"] != "private-source-archive":
        fail("source archive must declare private-source-archive confidentiality")
    if package["compression"] != "stored":
        fail("source archive compression must be stored for reproducibility")

    root_files = policy["root_files"]
    if not isinstance(root_files, list) or not root_files or len(root_files) != len(set(root_files)):
        fail("source archive root_files must be a unique nonempty array")
    for value in root_files:
        _normalized(value, "source archive root file")
        if "/" in value:
            fail("source archive root_files must be top-level files")
    actual_root_files = {
        path.name for path in root.iterdir() if path.is_file() or path.is_symlink()
    }
    if actual_root_files != set(root_files):
        missing = sorted(actual_root_files - set(root_files))
        stale = sorted(set(root_files) - actual_root_files)
        fail(f"source archive root-file coverage differs (unlisted: {missing}; missing: {stale})")
    for value in root_files:
        if not (root / value).is_file() or (root / value).is_symlink():
            fail(f"source archive root file is missing or unsafe: {value}")

    source_roots = policy["source_roots"]
    if (
        not isinstance(source_roots, list)
        or not source_roots
        or len(source_roots) != len(set(source_roots))
    ):
        fail("source archive source_roots must be a unique nonempty array")
    if set(source_roots) != SOURCE_ROOTS:
        fail("source archive source_roots differ from the version 1 contract")
    exclusions = _compile_exclusions(policy["exclude_patterns"])
    selected = list(root_files)
    for value in source_roots:
        _normalized(value, "source archive source root")
        if "/" in value:
            fail("source archive source_roots must be top-level directories")
        selected.extend(_walk_root(root, value, exclusions))
    if len(selected) != len(set(selected)):
        fail("source archive selects a path more than once")
    selected_set = set(selected)
    if any(name in selected_set for name in RESERVED_MEMBERS):
        fail("source archive source files conflict with package metadata")

    roles = policy["required_roles"]
    if not isinstance(roles, dict) or set(roles) != ROLE_NAMES:
        fail("source archive required_roles differ from the version 1 contract")
    for role, paths in roles.items():
        if not isinstance(paths, list) or not paths:
            fail(f"source archive role {role} must contain paths")
        for value in paths:
            _normalized(value, f"source archive role {role}")
            if value not in selected_set:
                fail(f"source archive role {role} is not packaged: {value}")

    dependencies = policy["dependency_files"]
    if not isinstance(dependencies, dict) or set(dependencies) != DEPENDENCY_FIELDS:
        fail("source archive dependency_files differ from the version 1 contract")
    for field, value in dependencies.items():
        _normalized(value, f"source archive dependency {field}")
        if value not in roles["dependency_inventory"]:
            fail(f"source archive dependency {field} lacks its required role")

    restoration = _exact(
        policy["restoration"], {"source_check_groups", "make_target"}, "restoration policy"
    )
    groups = restoration["source_check_groups"]
    if not isinstance(groups, list) or not groups or len(groups) != len(set(groups)):
        fail("restoration source_check_groups must be a unique nonempty array")
    if any(not isinstance(group, str) or not ID.fullmatch(group) for group in groups):
        fail("restoration source check groups must be lowercase kebab-case")
    if restoration["make_target"] != "help":
        fail("restoration make target must be the non-mutating help target")

    publication = load_json(root / "book/publication.json", "publication metadata")
    work_id = publication.get("work", {}).get("id")
    if not isinstance(work_id, str) or not work_id:
        fail("source archive needs canonical work identity")
    redirects = _validate_redirects(root, work_id)
    prior_editions = _validate_prior_editions(root, work_id)
    changelog = (root / "CHANGELOG.md").read_text(encoding="utf-8")
    if "# Changelog" not in changelog or "## Unreleased" not in changelog:
        fail("source archive changelog needs Changelog and Unreleased headings")
    _validate_integration(root)
    return {
        "policy": policy,
        "package": package,
        "selected": sorted(selected),
        "publication": publication,
        "redirects": redirects,
        "prior_editions": prior_editions,
    }


def _dependency_inventory(root, context, source_date):
    policy = context["policy"]
    files = []
    for role, path in sorted(policy["dependency_files"].items()):
        content = (root / path).read_bytes()
        files.append(
            {"role": role, "path": path, "sha256": _sha256(content), "bytes": len(content)}
        )
    document = {
        "schema_version": 1,
        "source_date_utc": source_date,
        "containerized_build": True,
        "network_after_bootstrap": False,
        "files": files,
    }
    return (json.dumps(document, indent=2, sort_keys=True) + "\n").encode("utf-8")


def _archive_readme(context, source_date, file_count):
    package = context["package"]
    work = context["publication"]["work"]
    lines = [
        f"# {work['title']} private source archive",
        "",
        "This is a complete private recovery package, not a public book release.",
        "It may contain private manuscripts, test canaries, and unreleased policy data.",
        "",
        f"Package: `{package['id']}`  ",
        f"Version: `{package['version']}`  ",
        f"Reproducible source date: `{source_date}`  ",
        f"Repository source files: {file_count}",
        "",
        "## Verify",
        "",
        "Run `sha256sum -c .archive/SHA256SUMS` from this directory.",
        "The outer ZIP checksum is stored beside the archive.",
        "",
        "## Restore",
        "",
        "1. Extract the ZIP into an empty directory.",
        "2. Review `.archive/MANIFEST.json`, `.archive/DEPENDENCIES.json`, and `CHANGELOG.md`.",
        "3. Run `make help`, then `make check-source`.",
        "4. Run `make bootstrap` while connected if the locked image is unavailable.",
        "5. Run `make render` after bootstrap; generated outputs were intentionally omitted.",
        "",
        "Automated archive checking extracts a fresh copy and runs the configured",
        "non-mutating Make and semantic-source smoke checks.",
        "",
    ]
    return "\n".join(lines).encode("utf-8")


def _manifest(root, context, source_date, source_members, generated_members):
    policy = context["policy"]
    files = [
        {"path": path, "sha256": _sha256(content), "bytes": len(content)}
        for path, content in sorted(source_members.items())
    ]
    generated = [
        {"path": path, "sha256": _sha256(content), "bytes": len(content)}
        for path, content in sorted(generated_members.items())
    ]
    document = {
        "schema_version": 1,
        "package": context["package"],
        "source_date_utc": source_date,
        "work": {
            "id": context["publication"]["work"]["id"],
            "title": context["publication"]["work"]["title"],
            "status": context["publication"]["work"]["status"],
        },
        "source_files": files,
        "generated_package_files": generated,
        "required_roles": policy["required_roles"],
        "dependency_inventory": f"{PACKAGE_METADATA_ROOT}/DEPENDENCIES.json",
        "history": {
            "changelog": "CHANGELOG.md",
            "redirect_registry": "book/redirects.json",
            "redirects": len(context["redirects"]),
            "prior_edition_registry": "book/prior-editions.json",
            "prior_editions": len(context["prior_editions"]),
        },
        "restoration": policy["restoration"],
    }
    return (json.dumps(document, indent=2, sort_keys=True) + "\n").encode("utf-8")


def source_archive_members(root):
    root = Path(root)
    context = load_archive_policy(root)
    epoch, source_date = _source_date(root)
    context = dict(context)
    context["epoch"] = epoch
    context["source_date"] = source_date
    source_members = {path: (root / path).read_bytes() for path in context["selected"]}
    generated = {
        f"{PACKAGE_METADATA_ROOT}/README.md": _archive_readme(
            context, source_date, len(source_members)
        ),
        f"{PACKAGE_METADATA_ROOT}/DEPENDENCIES.json": _dependency_inventory(
            root, context, source_date
        ),
    }
    generated[f"{PACKAGE_METADATA_ROOT}/MANIFEST.json"] = _manifest(
        root, context, source_date, source_members, generated
    )
    members = dict(source_members)
    members.update(generated)
    checksum_lines = [
        f"{_sha256(content)}  {path}" for path, content in sorted(members.items())
    ]
    members[f"{PACKAGE_METADATA_ROOT}/SHA256SUMS"] = (
        "\n".join(checksum_lines) + "\n"
    ).encode("utf-8")
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


def expected_source_archive_outputs(root):
    root = Path(root)
    context, members = source_archive_members(root)
    filename = context["package"]["filename"]
    archive = _archive_bytes(context["package"]["root_name"], members, context["epoch"])
    return context, members, {
        filename: archive,
        filename + ".sha256": f"{_sha256(archive)}  {filename}\n".encode("utf-8"),
    }


def package_source_archive(root, output_root=None):
    context, members, outputs = expected_source_archive_outputs(root)
    output_root = (
        Path(output_root)
        if output_root is not None
        else Path(root) / context["package"]["output_root"]
    )
    output_root.mkdir(parents=True, exist_ok=True)
    for filename, content in outputs.items():
        (output_root / filename).write_bytes(content)
    return {
        "source_files": len(context["selected"]),
        "archive_members": len(members),
        "outputs": len(outputs),
        "bytes": len(outputs[context["package"]["filename"]]),
    }


def inspect_archive(filename, content, context, expected_members):
    try:
        with zipfile.ZipFile(io.BytesIO(content)) as archive:
            infos = archive.infolist()
            names = [info.filename for info in infos]
            if names != sorted(names) or len(names) != len(set(names)):
                fail("source archive members must be unique and sorted")
            root_name = context["package"]["root_name"]
            relative = {}
            timestamp = datetime.fromtimestamp(
                context["epoch"], timezone.utc
            ).timetuple()[:6]
            for info in infos:
                path = PurePosixPath(info.filename)
                if (
                    path.is_absolute()
                    or ".." in path.parts
                    or not path.parts
                    or path.parts[0] != root_name
                ):
                    fail(f"source archive has unsafe member: {info.filename}")
                name = str(path.relative_to(root_name))
                if info.date_time != timestamp:
                    fail(f"source archive member has unstable timestamp: {name}")
                if info.compress_type != zipfile.ZIP_STORED:
                    fail(f"source archive member is compressed: {name}")
                if info.create_system != 3 or (info.external_attr >> 16) != 0o100644:
                    fail(f"source archive member has unstable mode: {name}")
                relative[name] = archive.read(info)
            if set(relative) != set(expected_members):
                fail("source archive member coverage is stale or incomplete")
            if any(relative[name] != expected for name, expected in expected_members.items()):
                fail("source archive member content differs from canonical sources")
            checksum_path = f"{PACKAGE_METADATA_ROOT}/SHA256SUMS"
            checksums = relative[checksum_path].decode("utf-8").splitlines()
            expected_sums = {
                f"{_sha256(data)}  {name}"
                for name, data in relative.items()
                if name != checksum_path
            }
            if set(checksums) != expected_sums or len(checksums) != len(expected_sums):
                fail("source archive internal checksums are invalid")
            manifest = json.loads(
                relative[f"{PACKAGE_METADATA_ROOT}/MANIFEST.json"]
            )
            if manifest.get("schema_version") != 1:
                fail("source archive manifest is invalid")
            return relative
    except (KeyError, UnicodeError, json.JSONDecodeError, zipfile.BadZipFile) as error:
        fail(f"cannot inspect source archive '{filename}': {error}")
def _restoration_smoke(relative, context):
    with tempfile.TemporaryDirectory(prefix="alkahest-source-restore.") as temporary:
        restore_root = Path(temporary) / context["package"]["root_name"]
        restore_root.mkdir()
        for path, content in relative.items():
            target = restore_root.joinpath(*PurePosixPath(path).parts)
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(content)
        make_result = subprocess.run(
            ["make", context["policy"]["restoration"]["make_target"]],
            cwd=restore_root,
            check=False,
            capture_output=True,
            text=True,
        )
        if make_result.returncode:
            fail(f"restored source archive Make smoke failed: {make_result.stderr.strip()}")
        command = [
            sys.executable,
            "scripts/check-source.py",
            *context["policy"]["restoration"]["source_check_groups"],
        ]
        source_result = subprocess.run(
            command,
            cwd=restore_root,
            check=False,
            capture_output=True,
            text=True,
        )
        if source_result.returncode:
            detail = source_result.stderr.strip() or source_result.stdout.strip()
            fail(f"restored source archive semantic smoke failed: {detail}")


def check_source_archive(root, output_root=None, restore=True):
    root = Path(root)
    context, members, outputs = expected_source_archive_outputs(root)
    output_root = (
        Path(output_root)
        if output_root is not None
        else root / context["package"]["output_root"]
    )
    if not output_root.is_dir():
        fail("source archive output directory is missing")
    actual = {path.name for path in output_root.iterdir()}
    if actual != set(outputs) or any(not (output_root / name).is_file() for name in outputs):
        fail("source archive output files are stale or incomplete")
    archive_relative = None
    for filename, expected in outputs.items():
        actual_bytes = (output_root / filename).read_bytes()
        if actual_bytes != expected:
            fail(f"source archive output is stale or changed: {filename}")
        if filename.endswith(".zip"):
            archive_relative = inspect_archive(filename, actual_bytes, context, members)
    if restore:
        _restoration_smoke(archive_relative, context)
    return {
        "source_files": len(context["selected"]),
        "archive_members": len(members),
        "outputs": len(outputs),
        "bytes": len(outputs[context["package"]["filename"]]),
        "restored": restore,
    }
