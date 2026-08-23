"""Validate reproducibility policy and fingerprint publication artifacts."""

from __future__ import annotations

import hashlib
import json
import re
import zipfile
from datetime import datetime, timezone
from pathlib import Path


class ReproducibilityError(RuntimeError):
    """A reproducibility contract or artifact is invalid."""


ARTIFACT_FIELDS = {"id", "kind", "path", "render_target"}
ARTIFACT_KINDS = {"directory", "epub", "pdf"}
TOP_LEVEL_FIELDS = {
    "schema_version",
    "source_date_epoch",
    "source_date_utc",
    "epub_identifier",
    "contract",
    "verification",
    "documented_variation",
}


def fail(message):
    raise ReproducibilityError("error: " + message)


def read_policy(root: Path) -> dict:
    path = root / "book/reproducibility.json"
    try:
        policy = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        fail(f"cannot load book/reproducibility.json: {error}")
    validate_policy(policy)
    return policy


def validate_policy(policy: dict) -> None:
    if not isinstance(policy, dict) or set(policy) != TOP_LEVEL_FIELDS:
        fail("reproducibility policy has an unsupported top-level contract")
    if policy["schema_version"] != 1:
        fail("reproducibility policy schema_version must be 1")

    epoch = policy["source_date_epoch"]
    if not isinstance(epoch, int) or epoch < 315532800 or epoch % 2:
        fail("source_date_epoch must be an even, ZIP-safe Unix timestamp")
    expected_date = datetime.fromtimestamp(epoch, timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    if policy["source_date_utc"] != expected_date:
        fail("source_date_utc does not match source_date_epoch")
    if not re.fullmatch(
        r"urn:uuid:[0-9a-f]{8}(?:-[0-9a-f]{4}){3}-[0-9a-f]{12}", policy["epub_identifier"]
    ):
        fail("epub_identifier must be a lowercase UUID URN")

    contract = policy["contract"]
    if not isinstance(contract, dict) or set(contract) != {
        "comparison",
        "toolchain_image",
        "environment",
        "artifacts",
    }:
        fail("reproducibility contract fields are incomplete")
    if contract["comparison"] != "exact-content":
        fail("publication artifacts must use exact-content comparison")
    if not isinstance(contract["toolchain_image"], str) or ":" not in contract["toolchain_image"]:
        fail("reproducibility contract needs a tagged toolchain image")
    expected_environment = {
        "SOURCE_DATE_EPOCH": str(epoch),
        "FORCE_SOURCE_DATE": "1",
    }
    if contract["environment"] != expected_environment:
        fail("reproducibility environment does not match the frozen epoch")

    artifacts = contract["artifacts"]
    if not isinstance(artifacts, list) or len(artifacts) < 4:
        fail("reproducibility contract needs every primary artifact")
    identifiers = set()
    paths = set()
    for artifact in artifacts:
        if not isinstance(artifact, dict) or set(artifact) != ARTIFACT_FIELDS:
            fail("artifact fields do not match the version 1 contract")
        identifier = artifact["id"]
        path = artifact["path"]
        if not re.fullmatch(r"[a-z0-9-]+", identifier or "") or identifier in identifiers:
            fail(f"artifact identifier is invalid or duplicated: {identifier}")
        if artifact["kind"] not in ARTIFACT_KINDS:
            fail(f"artifact {identifier} has an unsupported kind")
        if not isinstance(path, str) or not path.startswith("book/_build/") or path in paths:
            fail(f"artifact {identifier} has an unsafe or duplicate path")
        if not re.fullmatch(r"[a-z0-9-]+", artifact["render_target"] or ""):
            fail(f"artifact {identifier} has an invalid render target")
        identifiers.add(identifier)
        paths.add(path)

    verification = policy["verification"]
    if not isinstance(verification, dict) or set(verification) != {
        "quick_repeat",
        "full_repeat",
    }:
        fail("reproducibility verification fields are incomplete")
    quick = verification["quick_repeat"]
    full = verification["full_repeat"]
    if not isinstance(quick, list) or not quick or len(quick) != len(set(quick)):
        fail("quick_repeat must be a nonempty unique artifact list")
    if full != [artifact["id"] for artifact in artifacts]:
        fail("full_repeat must preserve the complete artifact order")
    if not set(quick).issubset(identifiers):
        fail("quick_repeat names an unknown artifact")
    if not {"html", "epub", "pdf-typst-7x10"}.issubset(quick):
        fail("quick_repeat must cover HTML, EPUB, and the default PDF backend")

    variation = policy["documented_variation"]
    if not isinstance(variation, list) or len(variation) != 1:
        fail("documented variation must identify the diagnostic build report")
    entry = variation[0]
    if not isinstance(entry, dict) or set(entry) != {"output", "fields", "reason"}:
        fail("documented variation fields are incomplete")
    if entry["output"] != "make build-report" or len(entry["fields"]) < 4:
        fail("documented variation must cover local build measurements")
    if not isinstance(entry["reason"], str) or len(entry["reason"].split()) < 10:
        fail("documented variation needs a substantive reason")


def artifact_map(policy: dict) -> dict[str, dict]:
    return {artifact["id"]: artifact for artifact in policy["contract"]["artifacts"]}


def select_artifacts(policy: dict, identifiers=None) -> list[dict]:
    artifacts = artifact_map(policy)
    selected = list(artifacts) if identifiers is None else list(identifiers)
    unknown = sorted(set(selected) - set(artifacts))
    if unknown:
        fail("unknown reproducibility artifacts: " + ", ".join(unknown))
    return [artifacts[identifier] for identifier in selected]


def file_digest(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def directory_digest(path: Path) -> tuple[str, int]:
    digest = hashlib.sha256()
    files = [candidate for candidate in sorted(path.rglob("*")) if candidate.is_file()]
    if not files:
        fail(f"artifact directory is empty: {path}")
    for candidate in files:
        if candidate.is_symlink():
            fail(f"artifact directory contains a symlink: {candidate}")
        relative = candidate.relative_to(path).as_posix().encode("utf-8")
        digest.update(len(relative).to_bytes(8, "big"))
        digest.update(relative)
        size = candidate.stat().st_size
        digest.update(size.to_bytes(8, "big"))
        with candidate.open("rb") as stream:
            for chunk in iter(lambda: stream.read(1024 * 1024), b""):
                digest.update(chunk)
    return digest.hexdigest(), len(files)


def zip_datetime(epoch: int) -> tuple[int, int, int, int, int, int]:
    value = datetime.fromtimestamp(epoch, timezone.utc)
    return value.year, value.month, value.day, value.hour, value.minute, value.second


def validate_epub(path: Path, policy: dict) -> None:
    try:
        with zipfile.ZipFile(path) as archive:
            infos = archive.infolist()
            if not infos or infos[0].filename != "mimetype":
                fail("EPUB mimetype must be the first archive member")
            expected = zip_datetime(policy["source_date_epoch"])
            unstable = [info.filename for info in infos if info.date_time != expected]
            if unstable:
                fail("EPUB has non-reproducible member timestamps: " + ", ".join(unstable[:3]))
            opf_names = [info.filename for info in infos if info.filename.endswith("content.opf")]
            if len(opf_names) != 1:
                fail("EPUB must contain exactly one content.opf")
            opf = archive.read(opf_names[0]).decode("utf-8")
    except (OSError, UnicodeDecodeError, zipfile.BadZipFile) as error:
        fail(f"cannot inspect EPUB {path}: {error}")
    if policy["epub_identifier"] not in opf:
        fail("EPUB does not retain the locked publication identifier")
    if opf.count(policy["source_date_utc"]) < 2:
        fail("EPUB package dates do not match source_date_epoch")


def validate_pdf(path: Path, policy: dict) -> None:
    try:
        data = path.read_bytes()
    except OSError as error:
        fail(f"cannot read PDF {path}: {error}")
    if not data.startswith(b"%PDF-"):
        fail(f"artifact is not a PDF: {path}")
    stamp = (
        datetime.fromtimestamp(policy["source_date_epoch"], timezone.utc)
        .strftime("D:%Y%m%d%H%M%SZ")
        .encode("ascii")
    )
    if stamp not in data:
        fail(f"PDF does not retain the reproducible creation timestamp: {path}")


def snapshot(root: Path, policy: dict, identifiers=None, validate=True) -> dict:
    fingerprints = {}
    for artifact in select_artifacts(policy, identifiers):
        path = root / artifact["path"]
        if artifact["kind"] == "directory":
            if not path.is_dir():
                fail(f"missing artifact directory: {artifact['path']}")
            digest, count = directory_digest(path)
            fingerprints[artifact["id"]] = {"sha256": digest, "files": count}
        else:
            if not path.is_file():
                fail(f"missing artifact file: {artifact['path']}")
            if validate and artifact["kind"] == "epub":
                validate_epub(path, policy)
            if validate and artifact["kind"] == "pdf":
                validate_pdf(path, policy)
            fingerprints[artifact["id"]] = {
                "sha256": file_digest(path),
                "bytes": path.stat().st_size,
            }
    return {
        "schema_version": 1,
        "source_date_epoch": policy["source_date_epoch"],
        "artifacts": fingerprints,
    }


def compare_snapshots(before: dict, after: dict) -> None:
    if before.get("schema_version") != 1 or after.get("schema_version") != 1:
        fail("snapshot schema_version must be 1")
    if before.get("source_date_epoch") != after.get("source_date_epoch"):
        fail("snapshot source_date_epoch changed")
    if before.get("artifacts") != after.get("artifacts"):
        before_artifacts = before.get("artifacts", {})
        after_artifacts = after.get("artifacts", {})
        changed = sorted(
            identifier
            for identifier in set(before_artifacts) | set(after_artifacts)
            if before_artifacts.get(identifier) != after_artifacts.get(identifier)
        )
        fail("repeated build changed exact artifact content: " + ", ".join(changed))


def validate_integration(root: Path, policy: dict) -> None:
    paths = {
        "toolchain": root / "scripts/toolchain.sh",
        "wrapper": root / "scripts/quarto.sh",
        "render": root / "src/alkahest/rendering/pipeline.py",
        "epub_finalizer": root / "src/alkahest/epub_accessibility.py",
        "epub": root / "book/_quarto-epub.yml",
    }
    try:
        texts = {name: path.read_text(encoding="utf-8") for name, path in paths.items()}
    except OSError as error:
        fail(f"cannot read reproducibility integration: {error}")
    epoch = str(policy["source_date_epoch"])
    image = policy["contract"]["toolchain_image"]
    if f'ALKAHEST_SOURCE_DATE_EPOCH="{epoch}"' not in texts["toolchain"]:
        fail("toolchain source-date epoch does not match reproducibility policy")
    if f'ALKAHEST_TOOLCHAIN_IMAGE="{image}"' not in texts["toolchain"]:
        fail("toolchain image does not match reproducibility policy")
    if '--env "SOURCE_DATE_EPOCH=${ALKAHEST_SOURCE_DATE_EPOCH}"' not in texts["wrapper"]:
        fail("Quarto wrapper does not pass SOURCE_DATE_EPOCH")
    if "--env FORCE_SOURCE_DATE=1" not in texts["wrapper"]:
        fail("Quarto wrapper does not force the TeX source date")
    if "canonicalize_markup" not in texts["render"]:
        fail("HTML renderer does not canonicalize serialized attributes")
    if "canonicalize_markup(_decode(members, path))" not in texts["epub_finalizer"]:
        fail("EPUB finalizer does not canonicalize serialized attributes")
    if policy["epub_identifier"] not in texts["epub"]:
        fail("EPUB profile does not declare the locked publication identifier")
