"""Build and verify deterministic release rights and credits reports."""

import json
from pathlib import Path

from .assets import AssetError, load_policy, read_json


OUTPUT_ROOT = "book/_build/release"
OUTPUT_FILES = ("rights-credits.json", "rights-credits.md")


def fail(message):
    raise AssetError(message)


def _rights_fields(record):
    return {
        key: record[key]
        for key in (
            "creator",
            "owner",
            "origin",
            "created",
            "license",
            "permission_evidence",
            "modifications",
            "credit_text",
            "public_distribution",
        )
    }


def _asset_records(root, policy):
    records = []
    for collection in policy["collections"]:
        rights = _rights_fields(collection)
        for path, digest in collection["distributed_files"].items():
            records.append(
                {
                    "source": {"kind": "collection", "id": collection["id"]},
                    "asset_id": collection["id"],
                    "title": collection["id"].replace("-", " ").title(),
                    "path": path,
                    "sha256": digest,
                    "distribution": (
                        "included"
                        if rights["public_distribution"]
                        else "excluded-private"
                    ),
                    "rights": rights,
                }
            )
    for specification in policy["registries"]:
        registry = read_json(root / specification["path"], specification["id"])
        defaults = specification["rights_defaults"]
        for item_id, item in registry["items"].items():
            merged = dict(defaults)
            merged.update(item)
            rights = _rights_fields(merged)
            for path_field, hash_field in specification["file_fields"].items():
                if path_field not in item:
                    continue
                records.append(
                    {
                        "source": {"kind": "registry", "id": specification["id"]},
                        "asset_id": item_id,
                        "title": item.get("title", item_id.replace("-", " ").title()),
                        "path": item[path_field],
                        "sha256": item[hash_field],
                        "distribution": (
                            "included"
                            if rights["public_distribution"]
                            else "excluded-private"
                        ),
                        "rights": rights,
                    }
                )
    return sorted(records, key=lambda item: (item["path"], item["asset_id"]))


def _runtime_records(policy):
    return [
        {
            "id": bundle["id"],
            "kind": bundle["kind"],
            "provider": bundle["provider"],
            "licenses": sorted(bundle["licenses"]),
            "credit_text": bundle["credit_text"],
            "license_evidence": (
                bundle.get("license_evidence")
                or ", ".join(sorted(bundle.get("html_license_files", {})))
            ),
        }
        for bundle in sorted(policy["runtime_bundles"], key=lambda item: item["id"])
    ]


def _publication_rights(publication):
    text_license = next(
        (
            item
            for item in publication["rights"]["licenses"]
            if item["scope"] == "Publication text"
        ),
        None,
    )
    if text_license is None:
        fail("publication metadata has no Publication text license scope")
    return text_license


def _readiness_blockers(publication, text_license):
    work = publication["work"]
    blockers = []
    if work["status"] != "published":
        blockers.append(f"work lifecycle is {work['status']}")
    if work["dates"]["publication"] is None:
        blockers.append("publication date is unassigned")
    if publication["rights"]["copyright"]["year"] is None:
        blockers.append("copyright year is unassigned")
    if text_license["status"] != "selected":
        blockers.append("publication-text license is not selected")
    return blockers


def validate_asset_inventory(assets, approved, allowed_licenses):
    """Require exact coverage and releasable rights for every included asset."""
    included = [item for item in assets if item["distribution"] == "included"]
    included_paths = {item["path"]: item["sha256"] for item in included}
    if included_paths != approved:
        fail("rights report asset coverage differs from approved distribution assets")
    for item in included:
        if not item["rights"]["public_distribution"]:
            fail(f"rights report includes private asset: {item['path']}")
        if not item["rights"]["credit_text"].strip():
            fail(f"rights report asset lacks required attribution: {item['path']}")
        if item["rights"]["license"] not in allowed_licenses:
            fail(f"rights report asset is unlicensed: {item['path']}")


def validate_integration(root):
    """Keep the generator, exact checker, CI, publication gate, and docs connected."""
    root = Path(root)
    files = {
        "makefile": root / "Makefile",
        "tasks": root / "src/alkahest/tasks.py",
        "ci": root / "src/alkahest/ci.py",
        "publication": root / "src/alkahest/checks/suites.py",
        "documentation": root / "docs/quality.md",
    }
    texts = {name: path.read_text(encoding="utf-8") for name, path in files.items()}
    for marker in (
        "generate-%:",
        "check-%:",
        "test-%:",
    ):
        if marker not in texts["makefile"]:
            fail(f"Makefile is missing rights-report target {marker}")
    for marker in (
        '"rights-report", ":generate-rights-report"',
        '"rights-report", ":check-rights-report"',
        '"rights-report", "test-rights-report.py"',
    ):
        if marker not in texts["tasks"]:
            fail(f"task registry is missing rights-report entry {marker}")
    for marker in (
        "alkahest generate rights-report",
        "alkahest check rights-report",
    ):
        if marker not in texts["ci"]:
            fail(f"CI is missing rights-report command {marker}")
    if 'operation("check-rights-report")' not in texts["publication"]:
        fail("publication gate is missing the rights-report check")
    for marker in (
        "book/_build/release/rights-credits.md",
        "make generate-rights-report",
        "make check-rights-report",
        "BLOCKED",
    ):
        if marker not in texts["documentation"]:
            fail(f"rights-report documentation is missing {marker!r}")


def build_report(root):
    """Return the validated machine-readable rights report."""
    root = Path(root)
    validate_integration(root)
    policy, approved, _counts = load_policy(root, root / "book/assets.json")
    publication = read_json(root / "book/publication.json", "publication metadata")
    reproduction = read_json(root / "book/reproducibility.json", "reproducibility policy")
    source_date = reproduction.get("source_date_utc")
    if not isinstance(source_date, str) or not source_date:
        fail("rights report needs a reproducible source date")
    assets = _asset_records(root, policy)
    included = [item for item in assets if item["distribution"] == "included"]
    excluded = [item for item in assets if item["distribution"] != "included"]
    validate_asset_inventory(assets, approved, set(policy["allowed_licenses"]))
    runtime = _runtime_records(policy)
    text_license = _publication_rights(publication)
    blockers = _readiness_blockers(publication, text_license)
    licenses = sorted(
        {item["rights"]["license"] for item in included}
        | {license_id for item in runtime for license_id in item["licenses"]}
    )
    return {
        "schema_version": 1,
        "source_date_utc": source_date,
        "sources": {
            "publication": "book/publication.json",
            "assets": "book/assets.json",
            "reproducibility": "book/reproducibility.json",
        },
        "work": {
            "id": publication["work"]["id"],
            "title": publication["work"]["title"],
            "status": publication["work"]["status"],
        },
        "publication_rights": {
            "statement": publication["rights"]["statement"],
            "copyright": publication["rights"]["copyright"],
            "publication_text_license": text_license,
        },
        "readiness": {"ready": not blockers, "blockers": blockers},
        "summary": {
            "included_assets": len(included),
            "excluded_private_assets": len(excluded),
            "runtime_bundles": len(runtime),
            "licenses": licenses,
        },
        "assets": included,
        "runtime_bundles": runtime,
    }


def _cell(value):
    return str(value).replace("\n", " ").replace("|", "\\|")


def markdown_report(report):
    """Render the machine report as a stable human audit document."""
    readiness = report["readiness"]
    publication_rights = report["publication_rights"]
    copyright_data = publication_rights["copyright"]
    lines = [
        "# Release rights and credits report",
        "",
        f"Work: **{report['work']['title']}** (`{report['work']['id']}`)",
        "",
        f"Reproducible source date: `{report['source_date_utc']}`",
        "",
        f"Release readiness: **{'READY' if readiness['ready'] else 'BLOCKED'}**",
        "",
        "## Readiness",
        "",
    ]
    if readiness["blockers"]:
        lines.extend(f"- {blocker}." for blocker in readiness["blockers"])
    else:
        lines.append("- No publication-level rights blockers are recorded.")
    text_license = publication_rights["publication_text_license"]
    lines.extend(
        [
            "",
            "## Publication rights",
            "",
            f"Rights statement: {publication_rights['statement']}",
            "",
            "Copyright: "
            + (str(copyright_data["year"]) if copyright_data["year"] else "unassigned")
            + "; "
            + ", ".join(copyright_data["holders"])
            + ".",
            "",
            f"Publication-text license status: `{text_license['status']}`"
            + (f" (`{text_license['expression']}`)" if text_license["expression"] else "")
            + ".",
            "",
            "## Asset inventory",
            "",
            "| Distribution | Path | SHA-256 | License | Creator / owner | Credit |",
            "|---|---|---|---|---|---|",
        ]
    )
    for item in report["assets"]:
        rights = item["rights"]
        lines.append(
            "| "
            + " | ".join(
                _cell(value)
                for value in (
                    item["distribution"],
                    f"`{item['path']}`",
                    f"`{item['sha256']}`",
                    rights["license"],
                    f"{rights['creator']} / {rights['owner']}",
                    rights["credit_text"],
                )
            )
            + " |"
        )
    lines.extend(
        [
            "",
            "## Runtime bundles",
            "",
            "| Bundle | Provider | Licenses | Credit | Evidence |",
            "|---|---|---|---|---|",
        ]
    )
    for bundle in report["runtime_bundles"]:
        lines.append(
            "| "
            + " | ".join(
                _cell(value)
                for value in (
                    bundle["id"],
                    bundle["provider"],
                    ", ".join(bundle["licenses"]),
                    bundle["credit_text"],
                    bundle["license_evidence"],
                )
            )
            + " |"
        )
    summary = report["summary"]
    lines.extend(
        [
            "",
            "## Summary",
            "",
            f"- Included checksum-locked assets: {summary['included_assets']}",
            f"- Excluded private assets: {summary['excluded_private_assets']}",
            f"- Licensed runtime bundles: {summary['runtime_bundles']}",
            f"- SPDX licenses represented: {', '.join(summary['licenses'])}",
            "",
            "This report inventories approved source assets. Final HTML, EPUB, and PDF "
            "inclusion and privacy are independently enforced by `make check-release-assets`.",
            "",
        ]
    )
    return "\n".join(lines).encode("utf-8")


def expected_outputs(root):
    report = build_report(root)
    machine = (json.dumps(report, indent=2, sort_keys=True) + "\n").encode("utf-8")
    return {
        "rights-credits.json": machine,
        "rights-credits.md": markdown_report(report),
    }


def generate_outputs(root):
    outputs = expected_outputs(root)
    output_root = Path(root) / OUTPUT_ROOT
    output_root.mkdir(parents=True, exist_ok=True)
    for filename, content in outputs.items():
        (output_root / filename).write_bytes(content)
    return build_report(root)["summary"]


def check_output_bytes(output_root, outputs):
    output_root = Path(output_root)
    if not output_root.is_dir():
        fail("rights report output directory is missing")
    actual = {path.name for path in output_root.iterdir()}
    if actual != set(outputs) or any(
        not (output_root / filename).is_file() for filename in outputs
    ):
        fail("rights report output files are stale or incomplete")
    for filename, expected in outputs.items():
        content = (output_root / filename).read_bytes()
        if content != expected:
            fail(f"rights report is stale or changed: {filename}")
        if not content:
            fail(f"rights report is empty: {filename}")


def check_outputs(root):
    outputs = expected_outputs(root)
    check_output_bytes(Path(root) / OUTPUT_ROOT, outputs)
    report = json.loads(outputs["rights-credits.json"])
    summary = dict(report["summary"])
    summary["ready"] = report["readiness"]["ready"]
    return summary
