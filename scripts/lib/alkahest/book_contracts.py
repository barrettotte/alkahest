"""Validate reusable schemas and book-owned metadata override layers."""

import re
from pathlib import Path, PurePosixPath

from .common import fail, load_json
from .json_schema import validate_instance


POLICY_PATH = "config/template/book-contracts.json"
DOCUMENTATION_PATH = "docs/book-contracts.md"
EXPECTED_IDS = (
    "stable-ids",
    "edition-manifests",
    "publishing-metadata",
    "rights-records",
    "accessibility-metadata",
    "cover-parameters",
    "localized-labels",
)


def _exact(value, fields, label):
    if not isinstance(value, dict) or set(value) != set(fields):
        fail(f"{label} fields differ from the version 1 contract")
    return value


def _path(value, label):
    if not isinstance(value, str) or not value:
        fail(f"{label} must be a normalized relative path")
    path = PurePosixPath(value)
    if path.is_absolute() or ".." in path.parts or str(path) != value:
        fail(f"{label} must be a normalized relative path")
    return value


def validate_book_contracts(root, document=None, records=None, schemas=None):
    """Validate all seven schema-backed, book-owned contract domains."""
    root = Path(root)
    document = document or load_json(root / POLICY_PATH, "book-contract inventory")
    _exact(
        document,
        {
            "schema_version",
            "contract_version",
            "schema_standard",
            "layer_order",
            "domains",
        },
        "book-contract inventory",
    )
    if document["schema_version"] != 1:
        fail("book-contract schema_version must be 1")
    if not isinstance(document["contract_version"], str) or re.fullmatch(
        r"(?:0|[1-9][0-9]*)\.(?:0|[1-9][0-9]*)\.(?:0|[1-9][0-9]*)",
        document["contract_version"],
    ) is None:
        fail("book-contract version must use semantic versioning")
    if document["schema_standard"] != "https://json-schema.org/draft/2020-12/schema":
        fail("book contracts must use JSON Schema draft 2020-12")
    if document["layer_order"] != [
        "engine-schema",
        "book-record",
        "generated-adapter",
    ]:
        fail("book-contract layer order must keep generated adapters last")
    domains = document["domains"]
    if not isinstance(domains, list):
        fail("book-contract domains must be an array")
    ids = [domain.get("id") if isinstance(domain, dict) else None for domain in domains]
    if tuple(ids) != EXPECTED_IDS:
        fail("book-contract domains must be the seven canonical domains in order")

    documentation = (root / DOCUMENTATION_PATH).read_text(encoding="utf-8")
    schema_ids = set()
    for domain in domains:
        domain_id = domain["id"]
        _exact(
            domain,
            {
                "id",
                "schema",
                "installed_schema",
                "record",
                "validator",
                "composition",
                "generated_adapter",
            },
            f"book-contract domain {domain_id}",
        )
        if domain["composition"] != "replace":
            fail(f"book-contract domain {domain_id} must use book-owned replacement")
        for field in ("schema", "record", "validator"):
            _path(domain[field], f"book-contract {domain_id} {field}")
            if not (root / domain[field]).is_file():
                fail(f"book-contract {domain_id} {field} does not exist: {domain[field]}")
        installed_schema = _path(
            domain["installed_schema"], f"book-contract {domain_id} installed schema"
        )
        expected_installed = f"schemas/{Path(domain['schema']).name}"
        if installed_schema != expected_installed:
            fail(f"book-contract {domain_id} installed schema path is inconsistent")
        adapter = domain["generated_adapter"]
        if adapter is not None:
            _path(adapter, f"book-contract {domain_id} generated adapter")
        schema = (
            schemas[domain_id]
            if schemas is not None and domain_id in schemas
            else load_json(root / domain["schema"], f"{domain_id} schema")
        )
        schema_id = schema.get("$id") if isinstance(schema, dict) else None
        if schema_id in schema_ids:
            fail(f"book-contract schema ID is duplicated: {schema_id}")
        schema_ids.add(schema_id)
        record = (
            records[domain_id]
            if records is not None and domain_id in records
            else load_json(root / domain["record"], f"{domain_id} record")
        )
        validate_instance(record, schema)
        for marker in (
            f"{{#contract-{domain_id}}}",
            domain["schema"],
            domain["record"],
            domain["validator"],
        ):
            if marker not in documentation:
                fail(f"book-contract documentation is missing {domain_id} marker {marker!r}")
    return {
        "version": document["contract_version"],
        "domains": len(domains),
        "schemas": len(schema_ids),
        "adapters": sum(domain["generated_adapter"] is not None for domain in domains),
    }


__all__ = ["EXPECTED_IDS", "validate_book_contracts"]
