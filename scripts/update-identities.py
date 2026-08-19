"""Refresh the identity lock while requiring migrations for removals or renames."""

import json
import os
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR / "lib"))

from alkahest.common import ContractError, fail
from alkahest.identities import add_companion_assets, add_reusable_content, canonical_variant, identity_key, inventory_book, load_identity_policy, load_json_file, validate_edition_manifests, validate_language_variants, validate_migrations


def main():
    if len(sys.argv) != 1: raise RuntimeError(f"usage: {sys.argv[0]}")
    root = Path(os.environ.get("ALKAHEST_IDENTITY_BOOK_ROOT", SCRIPT_DIR.parent / "book")).resolve()
    if not root.is_dir(): fail("identity book root does not exist")
    policy = load_identity_policy(root / "identities.json"); validate_migrations(policy)
    records = inventory_book(root, policy, canonical_variant(root, policy))
    add_companion_assets(root, policy, records); add_reusable_content(root, policy, records)
    validate_language_variants(root, policy, records); validate_edition_manifests(root, policy, records)
    lock_path = root / "identity-lock.json"
    old = load_json_file(lock_path, "identity lock") if lock_path.is_file() else {"version": 1, "book_id": policy["book_id"], "identities": []}
    if old.get("book_id", "") != policy["book_id"]: fail("identity lock belongs to a different book_id")
    old_active, old_retired = {}, {}
    for entry in old.get("identities", []):
        key = identity_key(entry)
        if key in old_active or key in old_retired: fail("duplicate existing identity-lock entry")
        if entry.get("status", "") == "active": old_active[key] = entry
        elif entry.get("status", "") == "retired": old_retired[key] = entry
        else: fail("malformed existing identity-lock entry")
    migrations = {(item["namespace"], item["from"]): item for item in policy["migrations"]}
    identities = []
    for key in sorted(old_retired):
        entry = old_retired[key]
        if key in records: fail(f"retired identity '{entry['namespace']}:{entry['id']}' was reused")
        migration = migrations.get(key)
        if not migration: fail(f"retired identity '{entry['namespace']}:{entry['id']}' has no migration record")
        changed = entry.get("reason", "") != migration["reason"] or (entry.get("replaced_by") != migration.get("to"))
        if changed: fail(f"migration for retired identity '{entry['namespace']}:{entry['id']}' changed after retirement")
        identities.append(entry)
    for key in sorted(old_active):
        if key in records: continue
        entry = old_active[key]; migration = migrations.get(key)
        if not migration: fail(f"identity '{entry['namespace']}:{entry['id']}' disappeared without a migration")
        if "to" in migration and (migration["namespace"], migration["to"]) not in records: fail(f"migration target '{migration['namespace']}:{migration['to']}' does not exist")
        retired = dict(entry, status="retired", reason=migration["reason"])
        if "to" in migration: retired["replaced_by"] = migration["to"]
        else: retired.pop("replaced_by", None)
        identities.append(retired)
    for key in sorted(records):
        record = records[key]
        if key in old_retired: fail(f"retired identity '{record['namespace']}:{record['id']}' was reused")
        entry = {field: value for field, value in record.items() if field != "line"}; entry["status"] = "active"; identities.append(entry)
    for key, migration in sorted(migrations.items()):
        if key not in old_retired and not (key in old_active and key not in records): fail(f"migration '{migration['namespace']}:{migration['from']}' does not name a retired or removed identity")
    identities.sort(key=lambda item: (item["namespace"], item["id"], item["status"]))
    output = {"version": 1, "book_id": policy["book_id"], "identities": identities}
    lock_path.write_text(json.dumps(output, indent=3, ensure_ascii=True, sort_keys=True) + "\n", encoding="utf-8")
    print(f"updated {lock_path} ({len(identities)} retained active/retired identities)")


if __name__ == "__main__":
    try: main()
    except (ContractError, OSError, UnicodeError, RuntimeError, KeyError, TypeError) as error:
        print(error if isinstance(error, ContractError) else f"error: {error}", file=sys.stderr); raise SystemExit(1)
