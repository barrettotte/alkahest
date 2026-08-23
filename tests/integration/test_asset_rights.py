"""Exercise asset rights, coverage, metadata, and release-privacy contracts."""

from __future__ import annotations

import json
import sys
import tempfile
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT / "src"))

from alkahest.assets import (
    AssetError,
    check_embedded_metadata,
    check_epub,
    check_html,
    check_privacy,
    digest_bytes,
    forbidden_patterns,
    load_policy,
    validate_pdf_metadata,
    validate_source_assets,
)

SVG = b'<svg xmlns="http://www.w3.org/2000/svg"><title>Fixture</title></svg>\n'


def write(path, content):
    path.parent.mkdir(parents=True, exist_ok=True)
    if isinstance(content, bytes):
        path.write_bytes(content)
    else:
        path.write_text(content, encoding="utf-8")


def rights():
    return {
        "creator": "Fixture creator",
        "owner": "Fixture owner",
        "origin": "Original fixture",
        "created": "2026-08-21",
        "license": "CC0-1.0",
        "permission_evidence": "Original-work declaration",
        "modifications": "None",
        "credit_text": "Fixture, CC0 1.0.",
        "public_distribution": True,
    }


def fixture_policy(font_license_hash):
    collection = rights()
    collection.update(
        {
            "id": "figures",
            "source_files": [],
            "distributed_files": {"figures/a.svg": digest_bytes(SVG)},
            "coverage_globs": ["figures/*.svg"],
        }
    )
    return {
        "schema_version": 1,
        "allowed_licenses": ["CC0-1.0", "MIT", "OFL-1.1"],
        "collections": [collection],
        "registries": [
            {
                "id": "media",
                "path": "book/media.json",
                "root": "media",
                "file_fields": {"asset": "sha256"},
                "rights_defaults": rights(),
            }
        ],
        "runtime_bundles": [
            {
                "id": "runtime",
                "kind": "generated-runtime",
                "html_root": "site_libs",
                "provider": "Pinned fixture",
                "licenses": ["MIT"],
                "credit_text": "Fixture runtime, MIT License.",
                "license_evidence": "Preserved header",
                "required_markers": {"runtime.js": "MIT License"},
            },
            {
                "id": "fonts",
                "kind": "fonts",
                "html_root": "theme/fonts",
                "epub_root": "EPUB/fonts",
                "provider": "Pinned fixture font",
                "license": "OFL-1.1",
                "licenses": ["OFL-1.1"],
                "credit_text": "Fixture font, SIL Open Font License 1.1.",
                "html_license_files": {"licenses/OFL.txt": font_license_hash},
                "epub_license_markers": ["SIL OPEN FONT LICENSE"],
            },
        ],
        "artifact_contract": {
            "html_root": "book/_build/html",
            "epub": "book/_build/epub/book.epub",
            "pdf_policy": "config/pdf/preflight.json",
            "expected_pdf_title": "Fixture Book",
            "expected_pdf_author": "Fixture Author",
            "expected_pdf_subject": "Fixture description",
            "expected_pdf_keywords": "fixture, metadata",
            "allowed_pdf_creator_patterns": ["^Typst 1\\.0$"],
            "allowed_pdf_producer_patterns": ["^$"],
            "forbidden_entry_patterns": [
                "(^|/)(\\.DS_Store|\\.env)(/|$)",
                "\\.(aux|tmp)($|/)",
            ],
            "forbidden_content_patterns": [
                {"label": "home path", "pattern": "/home/[^/]+/"},
                {"label": "private key", "pattern": "BEGIN PRIVATE KEY"},
            ],
        },
    }


def create_fixture(root):
    license_text = b"SIL OPEN FONT LICENSE"
    data = fixture_policy(digest_bytes(license_text))
    write(root / "book/figures/a.svg", SVG)
    write(root / "book/media/a.svg", SVG)
    write(
        root / "book/media.json",
        json.dumps(
            {
                "items": {
                    "media-a": {
                        "asset": "media/a.svg",
                        "sha256": digest_bytes(SVG),
                    }
                }
            }
        ),
    )
    write(root / "book/assets.json", json.dumps(data, indent=2))

    write(root / "book/_build/html/figures/a.svg", SVG)
    write(root / "book/_build/html/media/a.svg", SVG)
    write(root / "book/_build/html/site_libs/runtime.js", "/* MIT License */")
    write(root / "book/_build/html/theme/fonts/font.woff2", b"font")
    write(root / "book/_build/html/theme/fonts/licenses/OFL.txt", license_text)
    epub = root / "book/_build/epub/book.epub"
    epub.parent.mkdir(parents=True, exist_ok=True)
    with ZipFile(epub, "w", ZIP_DEFLATED) as archive:
        archive.writestr("EPUB/media/file0.svg", SVG)
        archive.writestr("EPUB/fonts/font.woff2", b"font")
        archive.writestr("EPUB/styles/book.css", "/* SIL OPEN FONT LICENSE */")
    return data


def save_policy(root, data):
    write(root / "book/assets.json", json.dumps(data, indent=2))


def rewrite_epub(root, mutation):
    path = root / "book/_build/epub/book.epub"
    with ZipFile(path) as source:
        entries = {name: source.read(name) for name in source.namelist()}
    mutation(entries)
    with ZipFile(path, "w", ZIP_DEFLATED) as target:
        for name, content in entries.items():
            target.writestr(name, content)


def run_source(root):
    return validate_source_assets(root, "book/assets.json")


def update_asset(root, data, content):
    write(root / "book/figures/a.svg", content)
    data["collections"][0]["distributed_files"]["figures/a.svg"] = digest_bytes(content)
    save_policy(root, data)


def expect_failure(name, mutation, expected):
    with tempfile.TemporaryDirectory(prefix="alkahest-assets-") as temporary:
        root = Path(temporary)
        data = create_fixture(root)
        mutation(root, data)
        try:
            run_source(root)
        except AssetError as error:
            if expected not in str(error):
                raise AssertionError(f"{name}: expected {expected!r}; received: {error}") from error
        else:
            raise AssertionError(f"{name}: invalid fixture passed")


def source_cases():
    return (
        (
            "missing rights field",
            lambda root, data: (
                data["collections"][0].pop("creator"),
                save_policy(root, data),
            ),
            "missing rights field 'creator'",
        ),
        (
            "undeclared license",
            lambda root, data: (
                data["collections"][0].update(license="Unknown-1.0"),
                save_policy(root, data),
            ),
            "uses undeclared license",
        ),
        (
            "invalid date",
            lambda root, data: (
                data["collections"][0].update(created="August 21"),
                save_policy(root, data),
            ),
            "created date must use ISO 8601",
        ),
        (
            "runtime license missing",
            lambda root, data: (
                data["runtime_bundles"][0].pop("licenses"),
                save_policy(root, data),
            ),
            "needs declared SPDX licenses",
        ),
        (
            "runtime credit missing",
            lambda root, data: (
                data["runtime_bundles"][0].update(credit_text=""),
                save_policy(root, data),
            ),
            "needs credit_text",
        ),
        (
            "font license mismatch",
            lambda root, data: (
                data["runtime_bundles"][1].update(licenses=["MIT"]),
                save_policy(root, data),
            ),
            "license differs from its SPDX licenses",
        ),
        (
            "checksum drift",
            lambda root, _: write(root / "book/figures/a.svg", SVG + b" "),
            "checksum drift",
        ),
        (
            "unregistered collection file",
            lambda root, _: write(root / "book/figures/b.svg", SVG),
            "unregistered: figures/b.svg",
        ),
        (
            "unregistered registry file",
            lambda root, _: write(root / "book/media/b.svg", SVG),
            "unregistered: media/b.svg",
        ),
        (
            "source home path",
            lambda root, data: update_asset(
                root, data, SVG.replace(b"</svg>", b"/home/alice/draft</svg>")
            ),
            "contains home path",
        ),
        (
            "source private key",
            lambda root, data: update_asset(
                root, data, SVG.replace(b"</svg>", b"BEGIN PRIVATE KEY</svg>")
            ),
            "contains private key",
        ),
        (
            "SVG editor metadata",
            lambda root, data: update_asset(
                root,
                data,
                SVG.replace(b"<svg ", b'<svg sodipodi:docname="draft.svg" '),
            ),
            "removable SVG editor metadata",
        ),
    )


def expect_asset_error(name, callback, expected):
    try:
        callback()
    except AssetError as error:
        if expected not in str(error):
            raise AssertionError(f"{name}: expected {expected!r}; received {error}")
    else:
        raise AssertionError(f"{name}: invalid fixture passed")


def rendered_cases():
    with tempfile.TemporaryDirectory(prefix="alkahest-assets-") as temporary:
        root = Path(temporary)
        create_fixture(root)
        policy, approved, _ = load_policy(root, root / "book/assets.json")
        if check_html(root, policy, approved) != 2:
            raise AssertionError("valid HTML fixture returned the wrong asset count")
        if check_epub(root, policy, approved) != 1:
            raise AssertionError("valid EPUB fixture returned the wrong media count")

        write(root / "book/_build/html/figures/extra.svg", SVG)
        expect_asset_error(
            "unauthorized HTML asset",
            lambda: check_html(root, policy, approved),
            "absent from rights manifest",
        )
        (root / "book/_build/html/figures/extra.svg").unlink()

        write(root / "book/_build/html/.env", "SECRET=value")
        expect_asset_error(
            "private HTML entry",
            lambda: check_html(root, policy, approved),
            "temporary/private entry",
        )
        (root / "book/_build/html/.env").unlink()

        rewrite_epub(root, lambda entries: entries.update({"EPUB/media/file0.svg": b"unknown"}))
        expect_asset_error(
            "unauthorized EPUB media",
            lambda: check_epub(root, policy, approved),
            "absent from rights manifest",
        )
        create_fixture(root)
        rewrite_epub(root, lambda entries: entries.update({"EPUB/.env": b"SECRET=value"}))
        expect_asset_error(
            "private EPUB entry",
            lambda: check_epub(root, policy, approved),
            "temporary/private entry",
        )
        create_fixture(root)
        rewrite_epub(
            root,
            lambda entries: entries.update({"EPUB/styles/book.css": b"/* missing font notice */"}),
        )
        expect_asset_error(
            "missing EPUB font license",
            lambda: check_epub(root, policy, approved),
            "font license marker is missing",
        )

    contract = fixture_policy(digest_bytes(b"license"))["artifact_contract"]
    valid_info = "\n".join(
        (
            "Title: Fixture Book",
            "Author: Fixture Author",
            "Creator: Typst 1.0",
            "Producer:",
            "Subject: Fixture description",
            "Keywords: fixture, metadata",
        )
    )
    validate_pdf_metadata("fixture", valid_info, "<xmp/>", contract)
    expect_asset_error(
        "PDF author drift",
        lambda: validate_pdf_metadata(
            "fixture", valid_info.replace("Fixture Author", "Other Author"), "", contract
        ),
        "Author metadata must be",
    )
    expect_asset_error(
        "PDF subject drift",
        lambda: validate_pdf_metadata(
            "fixture", valid_info.replace("Fixture description", "Other description"), "", contract
        ),
        "Subject metadata must be",
    )
    expect_asset_error(
        "PDF keyword drift",
        lambda: validate_pdf_metadata(
            "fixture", valid_info.replace("fixture, metadata", "other"), "", contract
        ),
        "Keywords metadata must be",
    )
    expect_asset_error(
        "PDF path leakage",
        lambda: validate_pdf_metadata(
            "fixture", valid_info, "<path>/home/alice/book</path>", contract
        ),
        "contains home path",
    )
    expect_asset_error(
        "JPEG EXIF",
        lambda: check_embedded_metadata("photo.jpg", b"JPEG Exif\x00\x00 data"),
        "EXIF/XMP/editor metadata",
    )
    privacy = forbidden_patterns(contract)
    expect_asset_error(
        "secret scan",
        lambda: check_privacy("artifact", b"BEGIN PRIVATE KEY", privacy),
        "contains private key",
    )
    return 10


def main():
    with tempfile.TemporaryDirectory(prefix="alkahest-assets-") as temporary:
        root = Path(temporary)
        create_fixture(root)
        counts = run_source(root)
        if counts != {
            "collections": 1,
            "registries": 1,
            "items": 1,
            "files": 2,
            "runtime_bundles": 2,
        }:
            raise AssertionError(f"valid source fixture returned wrong counts: {counts}")
    cases = source_cases()
    for name, mutation, expected in cases:
        expect_failure(name, mutation, expected)
    rendered_count = rendered_cases()
    print(f"ok: asset-rights fixtures ({len(cases) + 1} source; {rendered_count} rendered/privacy)")
    return 0


def test_contract():
    result = main()
    assert result in (None, 0)
