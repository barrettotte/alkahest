"""Validate persistent IDs, the identity lock, variants, and migrations."""

import os
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR / "lib"))

from alkahest.common import ContractError, fail
from alkahest.identities import add_companion_assets, add_reusable_content, canonical_variant, identity_key, inventory_book, load_identity_policy, load_json_file, validate_edition_manifests, validate_language_variants, validate_migrations


KINDS = ("chapter", "section", "figure", "table", "equation", "listing", "exercise", "solution", "learning-objectives", "learning-prerequisites", "learning-plan", "learning-summary", "review-question", "question-hint", "answer-key", "reusable-use", "glossary-term", "index-concept", "companion-asset", "reusable-content")


def main():
    root = Path(os.environ.get("ALKAHEST_IDENTITY_BOOK_ROOT", SCRIPT_DIR.parent / "book")).resolve()
    if not root.is_dir(): fail("identity book root does not exist")
    policy = load_identity_policy(root / "identities.json"); validate_migrations(policy)
    records = inventory_book(root, policy, canonical_variant(root, policy))
    add_companion_assets(root, policy, records); add_reusable_content(root, policy, records)
    validate_language_variants(root, policy, records); validate_edition_manifests(root, policy, records)
    lock = load_json_file(root / "identity-lock.json", "identity lock")
    if lock.get("version", 0) != 1: fail("identity lock version must be 1")
    if lock.get("book_id", "") != policy["book_id"]: fail("identity lock book_id differs from identities.json")
    if not isinstance(lock.get("identities"), list): fail("identity lock identities must be an array")
    active, retired = {}, {}
    for entry in lock["identities"]:
        if not isinstance(entry, dict): fail("malformed identity-lock entry")
        key = identity_key(entry); status = entry.get("status", "")
        if key in active or key in retired: fail(f"duplicate identity-lock entry '{entry['namespace']}:{entry['id']}'")
        if status == "active": active[key] = entry
        elif status == "retired": retired[key] = entry
        else: fail(f"identity-lock entry '{entry['namespace']}:{entry['id']}' has invalid status")
    for key in sorted(records):
        record = records[key]
        if key in retired: fail(f"retired identity '{record['namespace']}:{record['id']}' was reused")
        if key not in active: fail(f"new identity '{record['namespace']}:{record['id']}' is not locked; run make update-identities")
        locked = active[key]
        if locked.get("kind", "") != record["kind"] or locked.get("source", "") != record["source"]: fail(f"locked identity '{record['namespace']}:{record['id']}' metadata changed; run make update-identities")
    for key in sorted(active):
        if key not in records:
            entry = active[key]; fail(f"active identity '{entry['namespace']}:{entry['id']}' disappeared; add an explicit migration, then run make update-identities")
    migrations = {(item["namespace"], item["from"]): item for item in policy["migrations"]}
    for key in sorted(retired):
        entry = retired[key]; migration = migrations.get(key)
        if not migration: fail(f"retired identity '{entry['namespace']}:{entry['id']}' has no migration record")
        if entry.get("reason", "") != migration["reason"]: fail(f"retired identity '{entry['namespace']}:{entry['id']}' migration reason differs from the lock")
        if "to" in migration:
            target = (migration["namespace"], migration["to"])
            if target not in active: fail(f"migration target '{migration['namespace']}:{migration['to']}' is not active")
            if entry.get("replaced_by", "") != migration["to"]: fail(f"retired identity '{entry['namespace']}:{entry['id']}' replacement differs from the lock")
        elif "replaced_by" in entry: fail(f"retired identity '{entry['namespace']}:{entry['id']}' unexpectedly has a replacement")
    for key, migration in sorted(migrations.items()):
        if key not in retired: fail(f"migration '{migration['namespace']}:{migration['from']}' does not name a retired identity")
    counts = {}
    for record in records.values(): counts[record["kind"]] = counts.get(record["kind"], 0) + 1
    required = ", ".join(f"{counts.get(kind, 0)} {kind}" for kind in KINDS)
    print(f"ok: persistent identities ({len(records)} active; {len(retired)} retired; {required}; {len(policy['language_variants'])} language variants; {len(policy['edition_manifests'])} edition manifest)")


if __name__ == "__main__":
    try: main()
    except (ContractError, OSError, UnicodeError, KeyError, TypeError) as error:
        print(error if isinstance(error, ContractError) else f"error: {error}", file=sys.stderr); raise SystemExit(1)
