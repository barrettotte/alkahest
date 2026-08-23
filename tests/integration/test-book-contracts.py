"""Exercise reusable schema and override-layer failure fixtures."""

import copy
import json
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR.parents[1] / "src"))

from alkahest.book_contracts import EXPECTED_IDS, validate_book_contracts
from alkahest.common import ContractError

ROOT = SCRIPT_DIR.parents[1]
POLICY = json.loads((ROOT / "config/template/book-contracts.json").read_text())
RECORDS = {
    domain["id"]: json.loads((ROOT / domain["record"]).read_text()) for domain in POLICY["domains"]
}
SCHEMAS = {
    domain["id"]: json.loads((ROOT / domain["schema"]).read_text()) for domain in POLICY["domains"]
}


def expect_failure(name, expected, mutate):
    policy = copy.deepcopy(POLICY)
    records = copy.deepcopy(RECORDS)
    schemas = copy.deepcopy(SCHEMAS)
    mutate(policy, records, schemas)
    try:
        validate_book_contracts(ROOT, policy, records, schemas)
    except ContractError as error:
        if expected not in str(error):
            raise RuntimeError(
                f"error: book-contract fixture {name} missed {expected!r}: {error}"
            ) from error
    else:
        raise RuntimeError(f"error: book-contract fixture {name} unexpectedly passed")


def remove_required(domain_id, property_name):
    return lambda _policy, records, _schemas: records[domain_id].pop(property_name)


def main():
    expect_failure(
        "version",
        "semantic versioning",
        lambda policy, _records, _schemas: policy.update(contract_version="next"),
    )
    expect_failure(
        "domain-order",
        "seven canonical domains",
        lambda policy, _records, _schemas: policy["domains"].reverse(),
    )
    expect_failure(
        "composition",
        "book-owned replacement",
        lambda policy, _records, _schemas: policy["domains"][0].update(composition="merge"),
    )
    expect_failure(
        "validator-task",
        "validator task is inconsistent",
        lambda policy, _records, _schemas: policy["domains"][0].update(validator_task="unknown"),
    )
    expect_failure(
        "unsupported-schema-keyword",
        "unsupported keywords",
        lambda _policy, _records, schemas: schemas["stable-ids"].update(default={}),
    )
    required = {
        "stable-ids": "book_id",
        "edition-manifests": "editions",
        "publishing-metadata": "work",
        "rights-records": "allowed_licenses",
        "accessibility-metadata": "discovery",
        "cover-parameters": "template",
        "localized-labels": "locales",
    }
    for domain_id in EXPECTED_IDS:
        expect_failure(
            f"{domain_id}-required-field",
            "missing required property",
            remove_required(domain_id, required[domain_id]),
        )
    result = validate_book_contracts(ROOT, POLICY, RECORDS, SCHEMAS)
    if result != {"version": "0.1.0", "domains": 7, "schemas": 7, "adapters": 2}:
        raise RuntimeError("error: valid book-contract fixture returned wrong facts")
    print(
        "ok: reusable book-contract fixtures "
        "(7 domains and 12 inventory, layering, schema, and record failures rejected)"
    )


if __name__ == "__main__":
    try:
        main()
    except (ContractError, OSError, RuntimeError, UnicodeError) as error:
        print(error, file=sys.stderr)
        raise SystemExit(1)
