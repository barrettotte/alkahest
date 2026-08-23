"""Exercise deterministic source archives, history policy, and artifact drift."""

import io
import json
import sys
import tempfile
import zipfile
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath

SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR.parents[1] / "src"))

from alkahest.common import ContractError
from alkahest.source_archive import (
    check_source_archive,
    expected_source_archive_outputs,
    inspect_archive,
    load_archive_policy,
    source_archive_members,
)


ROOT = SCRIPT_DIR.parents[1]


def write_tree(root, context, members):
    for path in context["selected"]:
        target = root.joinpath(*PurePosixPath(path).parts)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(members[path])


def write_outputs(root, outputs):
    root.mkdir(parents=True, exist_ok=True)
    for filename, content in outputs.items():
        (root / filename).write_bytes(content)


def expect_failure(name, expected, callback):
    try:
        callback()
    except ContractError as error:
        if expected not in str(error):
            raise RuntimeError(
                f"error: source-archive fixture {name} missed {expected!r}: {error}"
            ) from error
    else:
        raise RuntimeError(f"error: source-archive fixture {name} unexpectedly passed")


def edit_json(path, mutate):
    document = json.loads(path.read_text(encoding="utf-8"))
    mutate(document)
    path.write_text(json.dumps(document, indent=2) + "\n", encoding="utf-8")


def policy_failure(name, expected, mutate):
    context, members = source_archive_members(ROOT)
    with tempfile.TemporaryDirectory(prefix=f"alkahest-archive-policy-{name}.") as temporary:
        fixture = Path(temporary)
        write_tree(fixture, context, members)
        mutate(fixture)
        expect_failure(name, expected, lambda: load_archive_policy(fixture))


def artifact_failure(name, expected, mutate):
    _context, _members, outputs = expected_source_archive_outputs(ROOT)
    with tempfile.TemporaryDirectory(prefix=f"alkahest-archive-output-{name}.") as temporary:
        output_root = Path(temporary)
        write_outputs(output_root, outputs)
        mutate(output_root)
        expect_failure(
            name,
            expected,
            lambda: check_source_archive(ROOT, output_root=output_root, restore=False),
        )


def unsafe_archive():
    context, members = source_archive_members(ROOT)
    timestamp = datetime.fromtimestamp(context["epoch"], timezone.utc).timetuple()[:6]
    output = io.BytesIO()
    with zipfile.ZipFile(output, "w", compression=zipfile.ZIP_STORED) as archive:
        info = zipfile.ZipInfo(
            f"{context['package']['root_name']}/../escape.txt", timestamp
        )
        info.compress_type = zipfile.ZIP_STORED
        info.create_system = 3
        info.external_attr = 0o100644 << 16
        archive.writestr(info, b"escape", compress_type=zipfile.ZIP_STORED)
    expect_failure(
        "unsafe-member",
        "unsafe member",
        lambda: inspect_archive(
            context["package"]["filename"], output.getvalue(), context, members
        ),
    )


def main():
    first_context, first_members, first = expected_source_archive_outputs(ROOT)
    second_context, second_members, second = expected_source_archive_outputs(ROOT)
    if (
        first != second
        or first_members != second_members
        or first_context["selected"] != second_context["selected"]
    ):
        raise RuntimeError("error: source archive output is not deterministic")
    with tempfile.TemporaryDirectory(prefix="alkahest-archive-valid.") as temporary:
        output_root = Path(temporary)
        write_outputs(output_root, first)
        result = check_source_archive(ROOT, output_root=output_root, restore=False)
        if result["archive_members"] != len(first_members):
            raise RuntimeError("error: valid source archive returned incorrect facts")

    policy_failure(
        "version",
        "semantic versioning",
        lambda root: edit_json(
            root / "config/archive/source-package.json",
            lambda document: document["package"].update(version="next"),
        ),
    )
    policy_failure(
        "unlisted-root-file",
        "root-file coverage differs",
        lambda root: (root / "secret.txt").write_text("local", encoding="utf-8"),
    )
    policy_failure(
        "excluded-required-file",
        "is not packaged",
        lambda root: edit_json(
            root / "config/archive/source-package.json",
            lambda document: document["exclude_patterns"].append(
                "^book/publication.json$"
            ),
        ),
    )
    policy_failure(
        "redirect-loop",
        "source and target must differ",
        lambda root: edit_json(
            root / "book/redirects.json",
            lambda document: document["redirects"].append(
                {
                    "from": "/old",
                    "to": "/old",
                    "effective_date": "2026-08-22",
                    "reason": "Fixture",
                }
            ),
        ),
    )
    policy_failure(
        "prior-edition-digest",
        "manifest_sha256",
        lambda root: edit_json(
            root / "book/prior-editions.json",
            lambda document: document["editions"].append(
                {
                    "id": "first-edition",
                    "edition_statement": "First edition",
                    "publication_date": "2026-08-22",
                    "identifiers": ["urn:isbn:9780000000000"],
                    "archive_uri": "urn:example:first-edition",
                    "manifest_sha256": "bad",
                }
            ),
        ),
    )

    archive_name = first_context["package"]["filename"]
    artifact_failure(
        "archive-drift",
        "stale or changed",
        lambda root: (root / archive_name).write_bytes(
            (root / archive_name).read_bytes() + b"changed"
        ),
    )
    artifact_failure(
        "sidecar-drift",
        "stale or changed",
        lambda root: (root / f"{archive_name}.sha256").write_text(
            "0" * 64 + f"  {archive_name}\n", encoding="utf-8"
        ),
    )
    artifact_failure(
        "missing",
        "stale or incomplete",
        lambda root: (root / archive_name).unlink(),
    )
    artifact_failure(
        "extra",
        "stale or incomplete",
        lambda root: (root / "old-source.zip").write_bytes(b"stale"),
    )
    unsafe_archive()
    print(
        "ok: source-archive fixtures "
        "(deterministic package; 5 policy and 5 artifact/safety failures rejected)"
    )


if __name__ == "__main__":
    try:
        main()
    except (ContractError, OSError, RuntimeError, UnicodeError) as error:
        print(error, file=sys.stderr)
        raise SystemExit(1)
