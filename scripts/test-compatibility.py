"""Exercise compatibility, release, deprecation, and migration fixtures."""

import copy
import json
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR / "lib"))

from alkahest.common import ContractError
from alkahest.compatibility import (
    migrate_round_trip,
    validate_compatibility,
    validate_migration,
)


ROOT = SCRIPT_DIR.parent
POLICY = json.loads((ROOT / "config/template/compatibility.json").read_text())
RELEASES = json.loads((ROOT / "config/template/releases.json").read_text())
DOMAIN_MAP = {domain["id"]: domain for domain in POLICY["domains"]}


def expect_policy_failure(name, expected, mutate):
    policy = copy.deepcopy(POLICY)
    releases = copy.deepcopy(RELEASES)
    mutate(policy, releases)
    try:
        validate_compatibility(ROOT, policy, releases)
    except ContractError as error:
        if expected not in str(error):
            raise RuntimeError(
                f"error: compatibility fixture {name} missed {expected!r}: {error}"
            ) from error
    else:
        raise RuntimeError(f"error: compatibility fixture {name} unexpectedly passed")


def expect_migration_failure(name, expected, migration, record=None):
    try:
        validate_migration(migration, DOMAIN_MAP)
        if record is not None:
            migrate_round_trip(record, migration, ["/work/id"])
    except ContractError as error:
        if expected not in str(error):
            raise RuntimeError(
                f"error: migration fixture {name} missed {expected!r}: {error}"
            ) from error
    else:
        raise RuntimeError(f"error: migration fixture {name} unexpectedly passed")


def migration_fixture():
    return {
        "schema_version": 1,
        "id": "publishing-metadata-v1-to-v2",
        "domain": "publishing-metadata",
        "from_version": 1,
        "to_version": 2,
        "up": [
            {"op": "replace", "path": "/schema_version", "value": 2},
            {"op": "rename", "from": "/work/summary", "path": "/work/short_summary"},
        ],
        "down": [
            {"op": "rename", "from": "/work/short_summary", "path": "/work/summary"},
            {"op": "replace", "path": "/schema_version", "value": 1},
        ],
    }


def main():
    expect_policy_failure(
        "version",
        "semantic versioning",
        lambda policy, _releases: policy["engine"].update(current_version="next"),
    )
    expect_policy_failure(
        "release-channel",
        "private-development channel",
        lambda _policy, releases: releases.update(channel="stable"),
    )
    expect_policy_failure(
        "fake-publication",
        "cannot claim publication evidence",
        lambda _policy, releases: releases["releases"][0].update(
            published_at="2026-08-22"
        ),
    )
    expect_policy_failure(
        "domain-drift",
        "match the book-contract inventory",
        lambda policy, _releases: policy["domains"].reverse(),
    )
    expect_policy_failure(
        "version-gap",
        "contiguous through current",
        lambda policy, _releases: policy["domains"][0].update(
            current_schema_version=3, supported_schema_versions=[1, 3]
        ),
    )
    expect_policy_failure(
        "premature-removal",
        "cannot be removed before",
        lambda policy, _releases: policy["deprecation_policy"]["entries"].append(
            {
                "id": "old-shortcode",
                "surface": "alk-old",
                "deprecated_in": "0.1.0",
                "remove_in": "1.0.0",
                "replacement": "alk-new",
                "warning": "Use alk-new.",
                "status": "removed",
            }
        ),
    )

    record = {
        "schema_version": 1,
        "work": {"id": "stable-book-id", "summary": "Original summary"},
    }
    migration = migration_fixture()
    validate_migration(migration, DOMAIN_MAP)
    upgraded = migrate_round_trip(record, migration, ["/work/id"])
    if upgraded != {
        "schema_version": 2,
        "work": {"id": "stable-book-id", "short_summary": "Original summary"},
    }:
        raise RuntimeError("error: valid migration produced incorrect upgraded data")

    invalid_version = migration_fixture()
    invalid_version["to_version"] = 3
    expect_migration_failure(
        "skipped-version", "advance exactly one", invalid_version
    )
    invalid_round_trip = migration_fixture()
    invalid_round_trip["down"].pop()
    expect_migration_failure(
        "not-reversible", "do not exactly restore", invalid_round_trip, record
    )
    identity_change = migration_fixture()
    identity_change["up"].append(
        {"op": "replace", "path": "/work/id", "value": "changed-book-id"}
    )
    identity_change["down"].insert(
        0, {"op": "replace", "path": "/work/id", "value": "stable-book-id"}
    )
    expect_migration_failure(
        "stable-id-change", "protected stable identity", identity_change, record
    )
    invalid_operation = migration_fixture()
    invalid_operation["up"].append({"op": "move", "path": "/work/value"})
    expect_migration_failure(
        "unsupported-operation", "unsupported operation", invalid_operation
    )

    result = validate_compatibility(ROOT, POLICY, RELEASES)
    if result != {
        "version": "0.1.0",
        "domains": 7,
        "migrations": 0,
        "deprecations": 0,
        "releases": 1,
    }:
        raise RuntimeError("error: valid compatibility fixture returned wrong facts")
    print(
        "ok: compatibility fixtures "
        "(private baseline and reversible migration accepted; "
        "10 version, release, deprecation, migration, and stable-ID failures rejected)"
    )


if __name__ == "__main__":
    try:
        main()
    except (ContractError, OSError, RuntimeError, UnicodeError) as error:
        print(error, file=sys.stderr)
        raise SystemExit(1)
