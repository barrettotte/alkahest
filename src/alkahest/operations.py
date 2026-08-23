"""Direct maintainer operations that do not need standalone process wrappers."""

from __future__ import annotations

import os
import subprocess
import sys
from collections import Counter
from collections.abc import Callable, Sequence
from datetime import UTC, datetime
from pathlib import Path
from typing import Final

ROOT: Final = Path(__file__).resolve().parents[2]
Operation = Callable[[tuple[str, ...]], None]


def _require_no_arguments(arguments: Sequence[str]) -> None:
    if arguments:
        raise ValueError(f"operation does not accept arguments: {' '.join(arguments)}")


def check_source_archive_policy(arguments: tuple[str, ...]) -> None:
    _require_no_arguments(arguments)
    from .source_archive import load_archive_policy

    context = load_archive_policy(ROOT)
    print(
        "ok: source archive policy "
        f"({len(context['selected'])} source files; "
        f"{len(context['redirects'])} redirects; "
        f"{len(context['prior_editions'])} prior editions; "
        f"{context['package']['confidentiality']})"
    )


def check_manifestations(arguments: tuple[str, ...]) -> None:
    _require_no_arguments(arguments)
    from .manifestations import load_and_validate

    _registry, records = load_and_validate(ROOT)
    formats = Counter(record["format"] for record in records.values())
    identifiers = sum(len(record["identifiers"]) for record in records.values())
    summary = ", ".join(f"{count} {name}" for name, count in sorted(formats.items()))
    print(
        f"ok: publication manifestations ({len(records)} records; {summary}; "
        f"{identifiers} typed publication identifier)"
    )


def check_metadata_generation(arguments: tuple[str, ...]) -> None:
    _require_no_arguments(arguments)
    from .metadata_generation import check_generated, validate_repository

    status = check_generated(ROOT)
    validate_repository(ROOT)
    state = "generated" if status["generated"] else "withheld until retail metadata is complete"
    print(
        "ok: generated publication metadata "
        f"(ONIX 3.1 {state}; code lists issue {status['code_list_issue']})"
    )


def check_publication_metadata(arguments: tuple[str, ...]) -> None:
    _require_no_arguments(arguments)
    from .publication_metadata import load_and_validate

    record = load_and_validate(ROOT)
    work = record["work"]
    print(
        "ok: canonical publication metadata "
        f"({len(record['contributors'])} contributor; "
        f"{len(work['subjects'])} subjects; {len(work['keywords'])} keywords; "
        f"{len(work['audiences'])} audiences; {work['status']})"
    )


def check_covers(arguments: tuple[str, ...]) -> None:
    _require_no_arguments(arguments)
    from .covers import load_cover_policy

    context = load_cover_policy(ROOT)
    template = context["template"]
    print(
        "ok: cover policy "
        f"({len(context['profiles'])} print profiles; {template['binding']}; "
        f"{template['paper']['id']}; {template['bleed_in']} in bleed; "
        f"{template['finish']}; development-only generic template)"
    )


def check_asset_rights(arguments: tuple[str, ...]) -> None:
    _require_no_arguments(arguments)
    from .assets import validate_source_assets

    counts = validate_source_assets(ROOT, ROOT / "book/assets.json")
    print(
        "ok: asset rights and source privacy "
        f"({counts['collections']} collections; {counts['registries']} registries; "
        f"{counts['items']} registry items; {counts['files']} checksum-locked files; "
        f"{counts['runtime_bundles']} runtime bundles)"
    )


def check_release_assets(arguments: tuple[str, ...]) -> None:
    from .assets import validate_release_assets

    values = list(arguments)
    root = ROOT
    if "--repo-root" in values:
        index = values.index("--repo-root")
        if index + 1 >= len(values):
            raise ValueError("usage: check-release-assets [POLICY] [--repo-root ROOT]")
        root = Path(values[index + 1]).resolve()
        del values[index : index + 2]
    if len(values) > 1 or any(value.startswith("-") for value in values):
        raise ValueError("usage: check-release-assets [POLICY] [--repo-root ROOT]")
    policy = Path(values[0]) if values else root / "book/assets.json"
    result = validate_release_assets(root, policy)
    print(
        "ok: rendered release assets "
        f"({result['approved']} approved source assets; "
        f"{result['html_assets']} HTML assets; "
        f"{result['epub_media']} EPUB media objects; {result['pdfs']} PDFs; "
        f"{result['runtime_bundles']} licensed runtime bundles)"
    )


def check_identities(arguments: tuple[str, ...]) -> None:
    _require_no_arguments(arguments)
    from .identities import IDENTITY_KINDS, validate_identity_book

    root = Path(os.environ.get("ALKAHEST_IDENTITY_BOOK_ROOT", ROOT / "book")).resolve()
    result = validate_identity_book(root)
    counts = result["counts"]
    required = ", ".join(f"{counts.get(kind, 0)} {kind}" for kind in IDENTITY_KINDS)
    print(
        f"ok: persistent identities ({result['active']} active; "
        f"{result['retired']} retired; {required}; "
        f"{result['language_variants']} language variants; "
        f"{result['edition_manifests']} edition manifest)"
    )


def check_editions(arguments: tuple[str, ...]) -> None:
    _require_no_arguments(arguments)
    from .editions import validate_edition_book

    root = Path(os.environ.get("ALKAHEST_EDITION_BOOK_ROOT", ROOT / "book")).resolve()
    result = validate_edition_book(root)
    preview = result["preview"]
    print(
        f"ok: whole-book editions ({result['editions']} editions; "
        f"{result['structures']} reusable structures; {result['sources']} registered sources; "
        f"preview metadata, {preview['links']} assigned links, {preview['watermark']} watermark, "
        "abridged, format, public/private, and reference-integrity policy)"
    )


def check_learning(arguments: tuple[str, ...]) -> None:
    _require_no_arguments(arguments)
    from .common import fail
    from .editions import load_editions
    from .learning import TYPES, validate_learning

    root = Path(os.environ.get("ALKAHEST_LEARNING_BOOK_ROOT", ROOT / "book")).resolve()
    if not root.is_dir():
        fail("learning book root does not exist")
    counts = validate_learning(root, load_editions(root / "editions.json"))
    summary = "; ".join(f"{counts[item]} {item}" for item in TYPES)
    print(f"ok: learning components ({summary}; paired relationships; private answer isolation)")


def check_companions(arguments: tuple[str, ...]) -> None:
    _require_no_arguments(arguments)
    from .common import fail
    from .companions import KINDS, validate_companions

    root = Path(os.environ.get("ALKAHEST_COMPANION_BOOK_ROOT", ROOT / "book")).resolve()
    if not root.is_dir():
        fail("companion book root does not exist")
    result = validate_companions(root)
    kinds = ", ".join(f"{result['kinds'][kind]} {kind}" for kind in KINDS)
    print(
        f"ok: companion materials ({result['items']} items in {result['bundles']} "
        f"versioned bundle; {kinds}; version, checksum, license, compatibility, "
        "description, delivery, and references)"
    )


def check_reuse(arguments: tuple[str, ...]) -> None:
    _require_no_arguments(arguments)
    from .common import fail
    from .reuse import KINDS, validate_reuse

    root = Path(os.environ.get("ALKAHEST_REUSE_BOOK_ROOT", ROOT / "book")).resolve()
    if not root.is_dir():
        fail("reusable-content book root does not exist")
    result = validate_reuse(root)
    kinds = ", ".join(f"{result['kinds'][kind]} {kind}" for kind in KINDS)
    print(
        f"ok: controlled content reuse ({result['items']} fragments; "
        f"{result['calls']} explicit use sites; {kinds}; version, checksum, "
        "provenance, context, parameters, and dependency boundary)"
    )


def check_template_engine(arguments: tuple[str, ...]) -> None:
    _require_no_arguments(arguments)
    from .template_package import load_template_policy, validate_template_integration

    validate_template_integration(ROOT)
    context = load_template_policy(ROOT)
    directory_count = len(context["policy"]["directory_components"])
    print(
        "ok: template engine policy "
        f"({len(context['mappings'])} reusable files; {directory_count} directories; "
        f"version {context['package']['version']}; {context['package']['license']})"
    )


def check_book_contracts(arguments: tuple[str, ...]) -> None:
    _require_no_arguments(arguments)
    from .project_checks import check_book_contracts as validate

    validate()


def check_extension_apis(arguments: tuple[str, ...]) -> None:
    _require_no_arguments(arguments)
    from .project_checks import check_extension_apis as validate

    validate()


def check_release_profiles(arguments: tuple[str, ...]) -> None:
    _require_no_arguments(arguments)
    from .project_checks import check_release_profiles as validate

    validate()


def check_theme_defaults(arguments: tuple[str, ...]) -> None:
    _require_no_arguments(arguments)
    from .project_checks import check_theme_defaults as validate

    validate()


def check_companion_bundles_operation(arguments: tuple[str, ...]) -> None:
    _require_no_arguments(arguments)
    from .companion_bundles import check_companion_bundles

    result = check_companion_bundles(ROOT / "book", ROOT / "book/_build/companion")
    print(
        "ok: companion bundles "
        f"({result['bundles']} deterministic bundle; {result['items']} items; "
        f"license, manifest, internal/outer checksums; {result['bytes']} bytes)"
    )


def check_source_archive(arguments: tuple[str, ...]) -> None:
    _require_no_arguments(arguments)
    from .source_archive import check_source_archive as validate

    result = validate(ROOT)
    print(
        "ok: private source archive "
        f"({result['source_files']} exact repository files; "
        f"{result['archive_members']} verified members; "
        f"restoration smoke: {'yes' if result['restored'] else 'skipped'})"
    )


def check_template_package(arguments: tuple[str, ...]) -> None:
    _require_no_arguments(arguments)
    from .template_package import check_template_package as validate

    result = validate(ROOT)
    print(
        "ok: template engine package "
        f"({result['source_files']} exact reusable files; "
        f"{result['members']} verified members; extracted smoke: yes)"
    )


def check_rights_report(arguments: tuple[str, ...]) -> None:
    _require_no_arguments(arguments)
    from .rights_report import check_outputs

    summary = check_outputs(ROOT)
    print(
        "ok: release rights report "
        f"({summary['included_assets']} exact assets; "
        f"{summary['runtime_bundles']} licensed runtime bundles; "
        f"release ready: {'yes' if summary['ready'] else 'no'})"
    )


def check_cover_artifacts(arguments: tuple[str, ...]) -> None:
    _require_no_arguments(arguments)
    from .covers import check_cover_artifacts as validate

    result = validate(ROOT)
    print(
        "ok: cover artifacts "
        f"({result['profiles']} profiles; {result['files']} exact files; "
        f"{result['production_pages']} combined production pages; "
        f"{result['blockers']} explicit press-readiness blockers)"
    )


def check_preview_artifacts(arguments: tuple[str, ...]) -> None:
    _require_no_arguments(arguments)
    from .preview_artifacts import collect_preview_artifacts, validate_preview_artifacts

    root = Path(os.environ.get("ALKAHEST_PREVIEW_ROOT", ROOT))
    result = validate_preview_artifacts(collect_preview_artifacts(root))
    print(
        "ok: preview artifacts "
        f"({result['sources']} selected sources; {result['html_pages']} HTML pages; "
        f"{result['epub_chapters']} EPUB chapters; {result['pdf_pages']} PDF pages; "
        f"{result['fonts']} embedded fonts)"
    )


def check_epub_accessibility_policy(arguments: tuple[str, ...]) -> None:
    from .epub_accessibility import EpubPolicyError, validate_epub

    if len(arguments) > 1:
        raise EpubPolicyError("error: usage: EPUB accessibility policy check [EPUB]")
    default_epub = ROOT / "book/_build/epub/Alkahest-Reference-Book.epub"
    default_policy = ROOT / "book/epub-accessibility.json"
    epub = Path(arguments[0]) if arguments else Path(os.environ.get("ALKAHEST_EPUB", default_epub))
    policy = Path(os.environ.get("ALKAHEST_EPUB_ACCESSIBILITY_POLICY", default_policy))
    if not epub.is_file():
        raise EpubPolicyError(f"error: missing rendered EPUB; run make render-epub first: {epub}")
    counts = validate_epub(epub, policy)
    details = ", ".join(f"{value} {key}" for key, value in counts.items())
    print(f"ok: EPUB accessibility policy ({details}; no conformance claim)")


def finalize_epub_operation(arguments: tuple[str, ...]) -> None:
    from .epub_accessibility import EpubPolicyError, finalize_epub

    values = list(arguments)
    allow_missing_sections = False
    if "--reduced" in values:
        values.remove("--reduced")
        allow_missing_sections = True
    if len(values) > 1 or any(value.startswith("-") for value in values):
        raise EpubPolicyError("error: usage: finalize-epub [--reduced] [EPUB]")
    default_epub = ROOT / "book/_build/epub/Alkahest-Reference-Book.epub"
    default_policy = ROOT / "book/epub-accessibility.json"
    epub = Path(values[0]) if values else Path(os.environ.get("ALKAHEST_EPUB", default_epub))
    policy = Path(os.environ.get("ALKAHEST_EPUB_ACCESSIBILITY_POLICY", default_policy))
    if not epub.is_file():
        raise EpubPolicyError(f"error: missing rendered EPUB: {epub}")
    finalize_epub(epub, policy, allow_missing_sections=allow_missing_sections)
    print(f"ok: finalized EPUB accessibility semantics ({epub})")


def stage_edition_operation(arguments: tuple[str, ...]) -> None:
    from .common import fail
    from .editions import stage_edition

    values = list(arguments)
    html_resources = False
    if "--html-resources" in values:
        values.remove("--html-resources")
        html_resources = True
    if len(values) != 1 or any(value.startswith("-") for value in values):
        raise ValueError("usage: stage-edition EDITION [--html-resources]")
    edition = values[0]
    if (
        not edition
        or not edition[0].isalpha()
        or not all(
            character.islower() or character.isdigit() or character == "-" for character in edition
        )
    ):
        fail("edition name must use lowercase kebab-case")
    book_root = Path(os.environ.get("ALKAHEST_EDITION_BOOK_ROOT", ROOT / "book"))
    print(stage_edition(book_root, edition, html_resources=html_resources))


def update_identities_operation(arguments: tuple[str, ...]) -> None:
    _require_no_arguments(arguments)
    from .identities import update_identity_lock

    book_root = Path(os.environ.get("ALKAHEST_IDENTITY_BOOK_ROOT", ROOT / "book"))
    result = update_identity_lock(book_root)
    print(f"updated {result['path']} ({result['identities']} retained active/retired identities)")


def prepare_epub_review_operation(arguments: tuple[str, ...]) -> None:
    _require_no_arguments(arguments)
    from .epub_review import bind_review_artifact

    def git(*values: str) -> str:
        try:
            return subprocess.run(  # noqa: S603 - fixed Git lifecycle queries
                ["git", *values],  # noqa: S607 - fixed Git executable
                cwd=ROOT,
                check=True,
                text=True,
                capture_output=True,
            ).stdout.strip()
        except subprocess.CalledProcessError as error:
            raise RuntimeError(f"error: Git review preparation failed: {error}") from error

    if git("status", "--porcelain", "--untracked-files=normal"):
        raise RuntimeError(
            "error: commit or remove worktree changes before preparing review evidence"
        )
    review_path = ROOT / "book/epub-reading-system-review.json"
    artifact = bind_review_artifact(
        ROOT,
        review_path,
        git("rev-parse", "HEAD"),
        datetime.now(UTC).isoformat().replace("+00:00", "Z"),
    )
    print(
        "prepared: EPUB manual review artifact "
        f"({artifact['source_revision'][:12]}; {artifact['content_sha256'][:12]}...)"
    )


def check_epub_review(arguments: tuple[str, ...]) -> None:
    _require_no_arguments(arguments)
    from .epub_review import load_json, validate_review

    review_path = Path(
        os.environ.get(
            "ALKAHEST_EPUB_REVIEW",
            ROOT / "book/epub-reading-system-review.json",
        )
    )
    policy_path = Path(
        os.environ.get(
            "ALKAHEST_EPUB_ACCESSIBILITY_POLICY",
            ROOT / "book/epub-accessibility.json",
        )
    )
    artifact_override = os.environ.get("ALKAHEST_EPUB_REVIEW_ARTIFACT")
    result = validate_review(
        load_json(review_path, "EPUB reading-system review"),
        load_json(policy_path, "EPUB accessibility policy"),
        ROOT,
        artifact_override,
    )
    print(
        "ok: EPUB manual review contract "
        f"({result['systems']} reading systems/{result['engines']} engines; "
        f"{result['scales']} text scales; {result['locations']} locations; "
        f"{result['criteria']} criteria per system; {result['pending']} results "
        f"pending; conformance claim: {'yes' if result['claim'] else 'no'})"
    )


def generate_publication_metadata(arguments: tuple[str, ...]) -> None:
    if arguments not in ((), ("--require-onix",)):
        raise ValueError("usage: alkahest generate publication-metadata [--require-onix]")
    from .metadata_generation import generate

    status = generate(ROOT, require_onix=bool(arguments))
    if status["generated"]:
        print(
            "ok: generated shared publication metadata and ONIX 3.1 "
            f"({len(status['eligible_manifestations'])} product records; "
            f"code lists issue {status['code_list_issue']})"
        )
    else:
        print(
            "ok: generated shared publication metadata; ONIX withheld "
            f"(0 eligible products; code lists issue {status['code_list_issue']})"
        )


def generate_cover_artifacts_operation(arguments: tuple[str, ...]) -> None:
    _require_no_arguments(arguments)
    from .covers import generate_cover_artifacts

    result = generate_cover_artifacts(ROOT)
    print(
        "ok: generated cover artifacts "
        f"({result['profiles']} profiles; "
        f"{result['files']} templates, thumbnails, and manifests)"
    )


def generate_rights_report(arguments: tuple[str, ...]) -> None:
    _require_no_arguments(arguments)
    from .rights_report import generate_outputs

    summary = generate_outputs(ROOT)
    print(
        "ok: generated release rights report "
        f"({summary['included_assets']} included assets; "
        f"{summary['excluded_private_assets']} excluded private assets; "
        f"{summary['runtime_bundles']} runtime bundles)"
    )


def package_companion_bundles_operation(arguments: tuple[str, ...]) -> None:
    _require_no_arguments(arguments)
    from .companion_bundles import package_companion_bundles

    result = package_companion_bundles(ROOT / "book", ROOT / "book/_build/companion")
    print(
        "ok: packaged companion materials "
        f"({result['bundles']} bundle; {result['items']} items; "
        f"{result['files']} generated files)"
    )


def package_source_archive(arguments: tuple[str, ...]) -> None:
    _require_no_arguments(arguments)
    from .source_archive import package_source_archive as package

    result = package(ROOT)
    print(
        "ok: packaged private source archive "
        f"({result['source_files']} repository files; "
        f"{result['archive_members']} archive members; {result['bytes']} bytes)"
    )


def package_template_engine(arguments: tuple[str, ...]) -> None:
    _require_no_arguments(arguments)
    from .template_package import package_template

    result = package_template(ROOT)
    print(
        "ok: packaged template engine "
        f"({result['source_files']} reusable files; {result['members']} members; "
        f"{result['bytes']} bytes)"
    )


OPERATIONS: Final[dict[str, Operation]] = {
    "check-asset-rights": check_asset_rights,
    "check-book-contracts": check_book_contracts,
    "check-companion-bundles": check_companion_bundles_operation,
    "check-companions": check_companions,
    "check-cover-artifacts": check_cover_artifacts,
    "check-covers": check_covers,
    "check-editions": check_editions,
    "check-epub-accessibility-policy": check_epub_accessibility_policy,
    "check-epub-review": check_epub_review,
    "check-extension-apis": check_extension_apis,
    "check-identities": check_identities,
    "check-learning": check_learning,
    "check-manifestations": check_manifestations,
    "check-metadata-generation": check_metadata_generation,
    "check-publication-metadata": check_publication_metadata,
    "check-preview-artifacts": check_preview_artifacts,
    "check-reuse": check_reuse,
    "check-release-assets": check_release_assets,
    "check-release-profiles": check_release_profiles,
    "check-rights-report": check_rights_report,
    "check-source-archive": check_source_archive,
    "check-source-archive-policy": check_source_archive_policy,
    "check-template-engine": check_template_engine,
    "check-template-package": check_template_package,
    "check-theme-defaults": check_theme_defaults,
    "finalize-epub": finalize_epub_operation,
    "generate-covers": generate_cover_artifacts_operation,
    "generate-publication-metadata": generate_publication_metadata,
    "generate-rights-report": generate_rights_report,
    "package-companion-bundles": package_companion_bundles_operation,
    "package-source-archive": package_source_archive,
    "package-template-engine": package_template_engine,
    "prepare-epub-review": prepare_epub_review_operation,
    "stage-edition": stage_edition_operation,
    "update-identities": update_identities_operation,
}


def run_operation(name: str, arguments: tuple[str, ...] = ()) -> int:
    """Run one closed direct operation with the same user-facing error contract."""
    operation = OPERATIONS.get(name)
    if operation is None:
        print(f"error: unknown direct operation: {name}", file=sys.stderr)
        return 2
    try:
        operation(arguments)
    except (KeyError, OSError, RuntimeError, TypeError, UnicodeError, ValueError) as error:
        message = str(error)
        print(message if message.startswith("error:") else f"error: {message}", file=sys.stderr)
        return 1
    return 0


def main(arguments: Sequence[str] | None = None) -> int:
    """Run one direct operation inside the locked Python container."""
    values = tuple(sys.argv[1:] if arguments is None else arguments)
    if not values:
        print("error: direct operation name is required", file=sys.stderr)
        return 2
    return run_operation(values[0], values[1:])


__all__ = ["OPERATIONS", "main", "run_operation"]


if __name__ == "__main__":
    raise SystemExit(main())
