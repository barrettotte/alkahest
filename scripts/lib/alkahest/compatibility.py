"""Validate template compatibility policy and reversible record migrations."""

import copy
import re
from datetime import date
from pathlib import Path, PurePosixPath

from .book_contracts import EXPECTED_IDS
from .common import fail, load_json


POLICY_PATH = "config/template/compatibility.json"
RELEASES_PATH = "config/template/releases.json"
DOCUMENTATION_PATH = "docs/compatibility.md"
SEMVER = re.compile(r"(?:0|[1-9][0-9]*)\.(?:0|[1-9][0-9]*)\.(?:0|[1-9][0-9]*)")
MIGRATION_ID = re.compile(r"[a-z][a-z0-9-]*-v[1-9][0-9]*-to-v[1-9][0-9]*")


def _exact(value, fields, label):
    if not isinstance(value, dict) or set(value) != set(fields):
        fail(f"{label} fields differ from the version 1 contract")
    return value


def _version(value, label):
    if not isinstance(value, str) or SEMVER.fullmatch(value) is None:
        fail(f"{label} must use semantic versioning")
    return tuple(int(part) for part in value.split("."))


def _path(value, label):
    if not isinstance(value, str) or not value:
        fail(f"{label} must be a normalized relative path")
    path = PurePosixPath(value)
    if path.is_absolute() or ".." in path.parts or str(path) != value:
        fail(f"{label} must be a normalized relative path")
    return value


def _pointer(value, label):
    if not isinstance(value, str) or re.fullmatch(
        r"/(?:[A-Za-z_][A-Za-z0-9_-]*)(?:/[A-Za-z_][A-Za-z0-9_-]*)*", value
    ) is None:
        fail(f"{label} must be an object-only JSON Pointer")
    return value


def _strings(value, label, allow_empty=False):
    if (
        not isinstance(value, list)
        or (not allow_empty and not value)
        or len(value) != len(set(value))
        or any(not isinstance(item, str) or not item.strip() for item in value)
    ):
        fail(f"{label} must be a unique string array")
    return value


def _at(document, pointer):
    value = document
    for token in pointer[1:].split("/"):
        if not isinstance(value, dict) or token not in value:
            fail(f"migration pointer does not exist: {pointer}")
        value = value[token]
    return copy.deepcopy(value)


def _parent(document, pointer):
    tokens = pointer[1:].split("/")
    value = document
    for token in tokens[:-1]:
        if not isinstance(value, dict) or token not in value:
            fail(f"migration pointer parent does not exist: {pointer}")
        value = value[token]
    if not isinstance(value, dict):
        fail(f"migration pointer parent is not an object: {pointer}")
    return value, tokens[-1]


def _validate_operation(operation, label):
    if not isinstance(operation, dict) or "op" not in operation:
        fail(f"{label} must be an operation object")
    kind = operation["op"]
    if kind in {"add", "replace"}:
        _exact(operation, {"op", "path", "value"}, label)
        _pointer(operation["path"], f"{label} path")
    elif kind == "remove":
        _exact(operation, {"op", "path"}, label)
        _pointer(operation["path"], f"{label} path")
    elif kind == "rename":
        _exact(operation, {"op", "from", "path"}, label)
        _pointer(operation["from"], f"{label} from")
        _pointer(operation["path"], f"{label} path")
        if operation["from"] == operation["path"]:
            fail(f"{label} rename must change the pointer")
    else:
        fail(f"{label} has unsupported operation {kind!r}")


def validate_migration(migration, domains):
    """Validate one explicit, reversible migration description."""
    _exact(
        migration,
        {"schema_version", "id", "domain", "from_version", "to_version", "up", "down"},
        "migration",
    )
    if migration["schema_version"] != 1:
        fail("migration schema_version must be 1")
    if not isinstance(migration["id"], str) or MIGRATION_ID.fullmatch(migration["id"]) is None:
        fail("migration id must name its vN-to-vN transition")
    if migration["domain"] not in domains:
        fail("migration domain is not a canonical book contract")
    source = migration["from_version"]
    target = migration["to_version"]
    if (
        not isinstance(source, int)
        or isinstance(source, bool)
        or not isinstance(target, int)
        or isinstance(target, bool)
        or source < 1
        or target != source + 1
    ):
        fail("migration versions must advance exactly one positive schema version")
    expected_id = f"{migration['domain']}-v{source}-to-v{target}"
    if migration["id"] != expected_id:
        fail("migration id differs from its domain and versions")
    for direction in ("up", "down"):
        operations = migration[direction]
        if not isinstance(operations, list) or not operations:
            fail(f"migration {direction} operations must be nonempty")
        for index, operation in enumerate(operations):
            _validate_operation(operation, f"migration {direction}/{index}")
    return migration


def apply_operations(document, operations):
    """Apply validated object-only operations to an isolated record copy."""
    result = copy.deepcopy(document)
    for operation in operations:
        kind = operation["op"]
        if kind == "rename":
            source_parent, source_name = _parent(result, operation["from"])
            target_parent, target_name = _parent(result, operation["path"])
            if source_name not in source_parent:
                fail(f"migration rename source does not exist: {operation['from']}")
            if target_name in target_parent:
                fail(f"migration rename target already exists: {operation['path']}")
            target_parent[target_name] = source_parent.pop(source_name)
            continue
        parent, name = _parent(result, operation["path"])
        if kind == "add":
            if name in parent:
                fail(f"migration add target already exists: {operation['path']}")
            parent[name] = copy.deepcopy(operation["value"])
        elif kind == "remove":
            if name not in parent:
                fail(f"migration remove target does not exist: {operation['path']}")
            del parent[name]
        elif kind == "replace":
            if name not in parent:
                fail(f"migration replace target does not exist: {operation['path']}")
            parent[name] = copy.deepcopy(operation["value"])
    return result


def migrate_round_trip(record, migration, protected_paths):
    """Prove an up/down migration is exact and preserves protected identities."""
    before = {_path: _at(record, _path) for _path in protected_paths}
    upgraded = apply_operations(record, migration["up"])
    for pointer, expected in before.items():
        if _at(upgraded, pointer) != expected:
            fail(f"migration changes protected stable identity {pointer}")
    restored = apply_operations(upgraded, migration["down"])
    if restored != record:
        fail("migration down operations do not exactly restore the source record")
    return upgraded


def validate_compatibility(root, policy=None, releases=None, migration_documents=None):
    """Validate policy, releases, current schemas, migrations, and documentation."""
    root = Path(root)
    policy = policy or load_json(root / POLICY_PATH, "compatibility policy")
    releases = releases or load_json(root / RELEASES_PATH, "template release registry")
    _exact(
        policy,
        {
            "schema_version",
            "policy_version",
            "engine",
            "semver",
            "deprecation_policy",
            "domains",
            "migration_registry",
        },
        "compatibility policy",
    )
    if policy["schema_version"] != 1:
        fail("compatibility schema_version must be 1")
    _version(policy["policy_version"], "compatibility policy version")
    engine = _exact(
        policy["engine"],
        {
            "id",
            "current_version",
            "status",
            "release_registry",
            "installed_release_registry",
        },
        "compatibility engine",
    )
    if engine["id"] != "alkahest-book-template-engine":
        fail("compatibility engine id is incorrect")
    current = _version(engine["current_version"], "current engine version")
    if engine["status"] != "private-development":
        fail("template engine must remain private-development until release is authorized")
    if engine["release_registry"] != RELEASES_PATH:
        fail("compatibility policy must use the canonical release registry")
    if engine["installed_release_registry"] != "defaults/template-releases.json":
        fail("compatibility policy has an incorrect installed release registry")
    semver = _exact(policy["semver"], {"patch", "minor", "major", "pre_1_0"}, "semver policy")
    for level in ("patch", "minor", "major"):
        _strings(semver[level], f"semver {level} changes")
    if "explicit migration" not in semver["pre_1_0"]:
        fail("pre-1.0 policy must still require explicit migrations")
    deprecations = _exact(
        policy["deprecation_policy"],
        {"minimum_minor_releases", "warning_required", "removal_requires_major", "entries"},
        "deprecation policy",
    )
    if deprecations["minimum_minor_releases"] != 1 or deprecations["warning_required"] is not True or deprecations["removal_requires_major"] is not True:
        fail("deprecation policy must warn for at least one minor release and remove only in a major")
    if not isinstance(deprecations["entries"], list):
        fail("deprecation entries must be an array")
    deprecation_ids = set()
    for entry in deprecations["entries"]:
        _exact(
            entry,
            {
                "id",
                "surface",
                "deprecated_in",
                "remove_in",
                "replacement",
                "warning",
                "status",
            },
            "deprecation entry",
        )
        identifier = entry["id"]
        if (
            not isinstance(identifier, str)
            or re.fullmatch(r"[a-z][a-z0-9-]*", identifier) is None
            or identifier in deprecation_ids
        ):
            fail("deprecation ids must be unique lowercase kebab-case")
        deprecation_ids.add(identifier)
        deprecated = _version(entry["deprecated_in"], "deprecation start")
        removal = _version(entry["remove_in"], "deprecation removal")
        if removal[0] <= deprecated[0]:
            fail("deprecation removal must target a later major version")
        if entry["status"] not in {"active", "removed"}:
            fail("deprecation status is invalid")
        if entry["status"] == "removed" and current < removal:
            fail("deprecation cannot be removed before its declared version")
        for field in ("surface", "replacement", "warning"):
            if not isinstance(entry[field], str) or not entry[field].strip():
                fail(f"deprecation {field} must be nonempty")

    contract = load_json(root / "config/template/book-contracts.json", "book contracts")
    contract_ids = [domain["id"] for domain in contract["domains"]]
    contract_by_id = {domain["id"]: domain for domain in contract["domains"]}
    domains = policy["domains"]
    ids = [domain.get("id") if isinstance(domain, dict) else None for domain in domains]
    if tuple(ids) != EXPECTED_IDS or ids != contract_ids:
        fail("compatibility domains must match the book-contract inventory")
    by_domain = {}
    registered = []
    for domain in domains:
        _exact(
            domain,
            {"id", "current_schema_version", "supported_schema_versions", "protected_paths", "migrations"},
            f"compatibility domain {domain['id']}",
        )
        version = domain["current_schema_version"]
        supported = domain["supported_schema_versions"]
        if not isinstance(version, int) or isinstance(version, bool) or version < 1:
            fail(f"compatibility domain {domain['id']} has an invalid current schema version")
        if (
            not isinstance(supported, list)
            or not supported
            or any(not isinstance(item, int) or isinstance(item, bool) for item in supported)
            or supported != list(range(min(supported), version + 1))
            or supported[-1] != version
        ):
            fail(f"compatibility domain {domain['id']} supported versions must be contiguous through current")
        paths = _strings(domain["protected_paths"], f"compatibility domain {domain['id']} protected paths", allow_empty=True)
        for pointer in paths:
            _pointer(pointer, f"compatibility domain {domain['id']} protected path")
        migrations = _strings(domain["migrations"], f"compatibility domain {domain['id']} migrations", allow_empty=True)
        if len(migrations) != version - min(supported):
            fail(f"compatibility domain {domain['id']} needs one migration per supported transition")
        registered.extend(migrations)
        by_domain[domain["id"]] = domain
        contract_domain = contract_by_id[domain["id"]]
        schema = load_json(root / contract_domain["schema"], f"{domain['id']} schema")
        if not schema.get("$id", "").endswith(f":{version}"):
            fail(f"compatibility domain {domain['id']} differs from its schema version")
        record = load_json(root / contract_domain["record"], f"{domain['id']} record")
        version_field = "version" if domain["id"] in {"stable-ids", "edition-manifests"} else "schema_version"
        if record.get(version_field) != version:
            fail(f"compatibility domain {domain['id']} differs from its record version")
    if policy["migration_registry"] != registered or len(registered) != len(set(registered)):
        fail("global migration registry must exactly flatten the domain migrations")
    documents = migration_documents or {}
    for migration_id in registered:
        relative = f"config/template/migrations/{migration_id}.json"
        document = documents.get(migration_id) or load_json(root / relative, "template migration")
        validate_migration(document, by_domain)
        if document["id"] != migration_id:
            fail("migration filename and id differ")

    _exact(releases, {"schema_version", "package_id", "channel", "current_version", "releases"}, "release registry")
    if releases["schema_version"] != 1 or releases["package_id"] != engine["id"]:
        fail("release registry identity is incorrect")
    if releases["channel"] != "private-development":
        fail("release registry must remain on the private-development channel")
    if _version(releases["current_version"], "release registry current version") != current:
        fail("release registry and compatibility versions differ")
    entries = releases["releases"]
    if not isinstance(entries, list) or not entries:
        fail("release registry must contain at least the development baseline")
    versions = []
    for entry in entries:
        _exact(entry, {"version", "status", "published_at", "git_tag", "artifact", "sha256", "compatibility", "migrations", "notes"}, "template release")
        version = _version(entry["version"], "template release version")
        versions.append(version)
        if entry["status"] not in {"development", "released", "withdrawn"}:
            fail("template release status is invalid")
        if entry["status"] == "development" and any(entry[field] is not None for field in ("published_at", "git_tag", "sha256")):
            fail("development template releases cannot claim publication evidence")
        if entry["status"] in {"released", "withdrawn"}:
            try:
                if not isinstance(entry["published_at"], str):
                    raise ValueError
                date.fromisoformat(entry["published_at"])
            except ValueError:
                fail("published template releases need an ISO publication date")
            if entry["git_tag"] != f"v{entry['version']}":
                fail("published template release tag differs from its version")
            if not isinstance(entry["sha256"], str) or re.fullmatch(r"[0-9a-f]{64}", entry["sha256"]) is None:
                fail("published template releases need an artifact checksum")
        expected_artifact = f"alkahest-book-template-engine-{entry['version']}.zip"
        if entry["artifact"] != expected_artifact:
            fail("template release artifact differs from its version")
        _strings(entry["migrations"], "template release migrations", allow_empty=True)
        if any(migration not in registered for migration in entry["migrations"]):
            fail("template release references an unknown migration")
        if any(not isinstance(entry[field], str) or not entry[field].strip() for field in ("compatibility", "notes")):
            fail("template release needs compatibility and notes")
    if versions != sorted(set(versions)) or versions[-1] != current:
        fail("template releases must be unique, ordered, and end at current")

    package = load_json(root / "config/template/template-package.json", "template package policy")["package"]
    if package["id"] != engine["id"] or _version(package["version"], "template package version") != current or package["filename"] != entries[-1]["artifact"]:
        fail("template package and release registry differ")
    documentation = (root / DOCUMENTATION_PATH).read_text(encoding="utf-8")
    for marker in (POLICY_PATH, RELEASES_PATH, "private-development", "stable content IDs", "make check-compatibility"):
        if marker not in documentation:
            fail(f"compatibility documentation is missing {marker!r}")
    return {
        "version": engine["current_version"],
        "domains": len(domains),
        "migrations": len(registered),
        "deprecations": len(deprecations["entries"]),
        "releases": len(entries),
    }


__all__ = [
    "apply_operations",
    "migrate_round_trip",
    "validate_compatibility",
    "validate_migration",
]
