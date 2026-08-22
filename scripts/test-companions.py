"""Exercise valid and deliberately invalid companion-material contracts."""

import hashlib
import json
import shutil
import sys
import tempfile
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR / "lib"))

from alkahest.common import ContractError
from alkahest.companions import validate_companions


FIXTURE = SCRIPT_DIR.parent / "tests" / "companions" / "base"


def load(root):
    return json.loads((root / "companion.json").read_text(encoding="utf-8"))


def save(root, registry):
    (root / "companion.json").write_text(json.dumps(registry, indent=2) + "\n", encoding="utf-8")


def replace(root, relative, old, new):
    path = root / relative
    text = path.read_text(encoding="utf-8")
    if old not in text:
        raise RuntimeError(f"error: companion fixture edit did not match {old!r}")
    path.write_text(text.replace(old, new, 1), encoding="utf-8")


def expect_failure(name, expected, mutate):
    with tempfile.TemporaryDirectory(prefix=f"alkahest-companion-{name}-") as temporary:
        root = Path(temporary)
        shutil.copytree(FIXTURE, root, dirs_exist_ok=True)
        mutate(root)
        try:
            validate_companions(root)
        except ContractError as error:
            if expected not in str(error):
                raise RuntimeError(f"error: companion fixture {name} missed expected diagnostic '{expected}': {error}")
        else:
            raise RuntimeError(f"error: companion fixture unexpectedly passed: {name}")


def registry_edit(callback):
    def mutate(root):
        registry = load(root)
        callback(registry)
        save(root, registry)
    return mutate


def main():
    validate_companions(FIXTURE)
    cases = []
    cases.append(("version", "registry version must be 1", registry_edit(lambda r: r.update(version=2))))
    cases.append(("missing-kind", "has no download specimen", registry_edit(lambda r: r["items"]["asset-fixture-download"].update(kind="code"))))
    def invalid_id(root):
        registry = load(root)
        registry["items"]["bad-fixture-code"] = registry["items"].pop("asset-fixture-code")
        save(root, registry)
        replace(root, "chapter.qmd", "asset-fixture-code", "bad-fixture-code")
    cases.append(("invalid-id", "invalid companion ID 'bad-fixture-code'", invalid_id))
    cases.append(("unknown-field", "unknown field 'mystery'", registry_edit(lambda r: r["items"]["asset-fixture-code"].update(mystery="value"))))
    cases.append(("duplicate-path", "path 'companion/sample.v' is registered more than once", registry_edit(lambda r: r["items"]["asset-fixture-data"].update(path="companion/sample.v"))))
    cases.append(("missing-file", "references missing file 'companion/sample.v'", lambda root: (root / "companion/sample.v").rename(root / "companion/missing.v")))
    cases.append(("media-type", "invalid media_type", registry_edit(lambda r: r["items"]["asset-fixture-code"].update(media_type="not-a-media-type"))))
    cases.append(("semantic-version", "invalid semantic version", registry_edit(lambda r: r["items"]["asset-fixture-code"].update(version="latest"))))
    cases.append(("checksum-format", "invalid SHA-256", registry_edit(lambda r: r["items"]["asset-fixture-code"].update(sha256="bad"))))
    cases.append(("checksum-drift", "checksum drift", lambda root: (root / "companion/sample.v").write_text((root / "companion/sample.v").read_text(encoding="utf-8") + "\nchanged\n", encoding="utf-8")))
    cases.append(("compatibility", "compatibility must be a nonempty array", registry_edit(lambda r: r["items"]["asset-fixture-code"].update(compatibility=[]))))
    cases.append(("description", "needs an accessible description", registry_edit(lambda r: r["items"]["asset-fixture-code"].update(description="Short."))))
    cases.append(("delivery", "needs a durable HTTPS URL or release_path", registry_edit(lambda r: r["items"]["asset-fixture-code"].pop("release_path"))))
    cases.append(("release-path", "unsafe release_path '../sample.v'", registry_edit(lambda r: r["items"]["asset-fixture-code"].update(release_path="../sample.v"))))
    cases.append(("unregistered-file", "unregistered companion file 'companion/extra.txt'", lambda root: (root / "companion/extra.txt").write_text("unregistered\n", encoding="utf-8")))
    cases.append(("unknown-reference", "unknown companion ID 'asset-unknown'", lambda root: replace(root, "chapter.qmd", "asset-fixture-code", "asset-unknown")))
    cases.append(("missing-reference", "item 'asset-fixture-code' is never referenced", lambda root: replace(root, "chapter.qmd", "{{< alk-companion asset-fixture-code >}}\n", "")))
    cases.append(("duplicate-reference", "item 'asset-fixture-code' is referenced more than once", lambda root: (root / "chapter.qmd").write_text((root / "chapter.qmd").read_text(encoding="utf-8") + "\n{{< alk-companion asset-fixture-code >}}\n", encoding="utf-8")))
    cases.append(("raw-link", "use alk-companion rather than a raw companion link", lambda root: (root / "chapter.qmd").write_text((root / "chapter.qmd").read_text(encoding="utf-8") + "\n[raw](companion/sample.v)\n", encoding="utf-8")))
    cases.append(("missing-bundles", "bundles must be a nonempty object", registry_edit(lambda r: r.pop("bundles"))))
    def invalid_bundle_id(registry):
        registry["bundles"]["bad-bundle"] = registry["bundles"].pop("bundle-fixture-project")
    cases.append(("bundle-id", "invalid companion bundle ID", registry_edit(invalid_bundle_id)))
    cases.append(("bundle-filename", "invalid versioned filename", registry_edit(lambda r: r["bundles"]["bundle-fixture-project"].update(filename="fixture-latest.zip"))))
    cases.append(("bundle-release-path", "release_path must match its filename", registry_edit(lambda r: r["bundles"]["bundle-fixture-project"].update(release_path="companion/other.zip"))))
    cases.append(("bundle-unknown-item", "references unknown item 'asset-missing'", registry_edit(lambda r: r["bundles"]["bundle-fixture-project"]["items"].append("asset-missing"))))
    cases.append(("bundle-duplicate-item", "repeats item 'asset-fixture-code'", registry_edit(lambda r: r["bundles"]["bundle-fixture-project"]["items"].append("asset-fixture-code"))))
    cases.append(("bundle-entrypoint", "entrypoint must be a download item", registry_edit(lambda r: r["bundles"]["bundle-fixture-project"].update(entrypoint="asset-fixture-code"))))
    def mismatched_bundle_version(registry):
        bundle = registry["bundles"]["bundle-fixture-project"]
        bundle.update(
            version="2.0.0",
            filename="fixture-companion-2.0.0.zip",
            release_path="companion/fixture-companion-2.0.0.zip",
        )
    cases.append(("bundle-version", "version must match its entrypoint", registry_edit(mismatched_bundle_version)))
    cases.append(("bundle-license", "license checksum drift", registry_edit(lambda r: r["bundles"]["bundle-fixture-project"].update(license_sha256="0" * 64))))
    cases.append(("bundle-orphan", "must belong to exactly one bundle", registry_edit(lambda r: r["bundles"]["bundle-fixture-project"]["items"].remove("asset-fixture-data"))))
    for name, expected, mutate in cases:
        expect_failure(name, expected, mutate)
    print("ok: companion fixtures (valid contract; 29 invalid item, bundle, file, delivery, checksum, license, and reference contracts rejected)")


if __name__ == "__main__":
    try:
        main()
    except (ContractError, OSError, RuntimeError) as error:
        print(error, file=sys.stderr)
        raise SystemExit(1)
