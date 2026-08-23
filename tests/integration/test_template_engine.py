"""Exercise template extraction policy, deterministic bytes, and package safety."""

import io
import json
import shutil
import sys
import tempfile
import zipfile
from datetime import datetime, timezone
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR.parents[1] / "src"))

from alkahest.common import ContractError
from alkahest.template_package import (
    check_template_package,
    expected_template_outputs,
    inspect_template_archive,
    load_template_policy,
    template_members,
)

ROOT = SCRIPT_DIR.parents[1]


def copy_fixture(root):
    policy_path = ROOT / "config/template/template-package.json"
    policy = json.loads(policy_path.read_text(encoding="utf-8"))
    for relative in ("config/template/template-package.json", "book/reproducibility.json"):
        target = root / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(ROOT / relative, target)
    for component in policy["directory_components"]:
        ignore = shutil.ignore_patterns("fonts") if component["source"] == "book/theme" else None
        shutil.copytree(ROOT / component["source"], root / component["source"], ignore=ignore)
    for component in policy["file_components"]:
        target = root / component["source"]
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(ROOT / component["source"], target)


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
                f"error: template-engine fixture {name} missed {expected!r}: {error}"
            ) from error
    else:
        raise RuntimeError(f"error: template-engine fixture {name} unexpectedly passed")


def edit_policy(root, mutate):
    path = root / "config/template/template-package.json"
    document = json.loads(path.read_text(encoding="utf-8"))
    mutate(document)
    path.write_text(json.dumps(document, indent=2) + "\n", encoding="utf-8")


def policy_failure(name, expected, mutate, build=False):
    with tempfile.TemporaryDirectory(prefix=f"alkahest-template-policy-{name}.") as temporary:
        root = Path(temporary)
        copy_fixture(root)
        mutate(root)
        callback = template_members if build else load_template_policy
        expect_failure(name, expected, lambda: callback(root))


def artifact_failure(name, expected, mutate):
    _context, _members, outputs = expected_template_outputs(ROOT)
    with tempfile.TemporaryDirectory(prefix=f"alkahest-template-output-{name}.") as temporary:
        output_root = Path(temporary)
        write_outputs(output_root, outputs)
        mutate(output_root)
        expect_failure(
            name,
            expected,
            lambda: check_template_package(ROOT, output_root=output_root, extract=False),
        )


def unsafe_archive():
    context, members, _outputs = expected_template_outputs(ROOT)
    source_date = json.loads(members["MANIFEST.json"])["source_date_utc"]
    timestamp = (
        datetime.strptime(source_date, "%Y-%m-%dT%H:%M:%SZ")
        .replace(tzinfo=timezone.utc)
        .timetuple()[:6]
    )
    output = io.BytesIO()
    with zipfile.ZipFile(output, "w", compression=zipfile.ZIP_STORED) as archive:
        info = zipfile.ZipInfo(f"{context['package']['root_name']}/../escape.txt", timestamp)
        info.compress_type = zipfile.ZIP_STORED
        info.create_system = 3
        info.external_attr = 0o100644 << 16
        archive.writestr(info, b"escape", compress_type=zipfile.ZIP_STORED)
    expect_failure(
        "unsafe-member",
        "unsafe member",
        lambda: inspect_template_archive(
            context["package"]["filename"], output.getvalue(), context, members
        ),
    )


def main():
    first_context, first_members, first = expected_template_outputs(ROOT)
    second_context, second_members, second = expected_template_outputs(ROOT)
    if (
        first != second
        or first_members != second_members
        or first_context["mappings"] != second_context["mappings"]
    ):
        raise RuntimeError("error: template engine package is not deterministic")
    with tempfile.TemporaryDirectory(prefix="alkahest-template-valid.") as temporary:
        output_root = Path(temporary)
        write_outputs(output_root, first)
        result = check_template_package(ROOT, output_root=output_root)
        if result["source_files"] != 55 or result["members"] != 57:
            raise RuntimeError("error: valid template package returned incorrect facts")

    policy_failure(
        "schema",
        "schema_version must be 1",
        lambda root: edit_policy(root, lambda value: value.update(schema_version=2)),
    )
    policy_failure(
        "version",
        "semantic versioning",
        lambda root: edit_policy(root, lambda value: value["package"].update(version="next")),
    )
    policy_failure(
        "output",
        "must remain under",
        lambda root: edit_policy(root, lambda value: value["package"].update(output_root="dist")),
    )
    policy_failure(
        "duplicate-component",
        "component id is duplicated",
        lambda root: edit_policy(
            root,
            lambda value: value["file_components"][0].update(id="extensions"),
        ),
    )
    policy_failure(
        "required-path",
        "is not packaged",
        lambda root: edit_policy(root, lambda value: value["required_paths"].append("missing.txt")),
    )
    policy_failure(
        "specimen-leak",
        "specimen-specific content",
        lambda root: (root / "template/README.md").write_text(
            "Alkahest Reference Book", encoding="utf-8"
        ),
        build=True,
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
        lambda root: (root / "old-template.zip").write_bytes(b"stale"),
    )
    unsafe_archive()
    print(
        "ok: template-engine fixtures "
        "(deterministic extraction; 6 policy and 5 artifact/safety failures rejected)"
    )


def test_contract():
    result = main()
    assert result in (None, 0)
