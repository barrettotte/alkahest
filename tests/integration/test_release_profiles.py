"""Exercise release schemas, inheritance, isolation, and stale adapters."""

import copy
import json
import sys
import tempfile
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR.parents[1] / "src"))

from alkahest.release_profiles import (
    ReleaseProfileError,
    release_outputs,
    stage_project_release,
    sync_project_releases,
    validate_project_releases,
)

ROOT = SCRIPT_DIR.parents[1]
DEFAULTS = json.loads((ROOT / "book/alkahest-release-defaults.json").read_text(encoding="utf-8"))
LOCAL = {
    "schema_version": 1,
    "sources": {
        "front": {"path": "index.qmd", "role": "front", "availability": "release"},
        "one": {"path": "chapter-one.qmd", "role": "chapter", "availability": "release"},
        "two": {"path": "chapter-two.qmd", "role": "chapter", "availability": "release"},
        "back": {"path": "references.qmd", "role": "back", "availability": "release"},
        "appendix": {
            "path": "appendices/checklist.qmd",
            "role": "appendix",
            "availability": "release",
        },
        "private": {"path": "private/notes.qmd", "role": "chapter", "availability": "private"},
    },
    "profiles": {
        "full": {
            "chapters": ["front", "one", "two", "back"],
            "appendices": ["appendix"],
            "metadata": {
                "subtitle": "Complete book",
                "description": "The complete fixture book.",
                "edition": "First fixture edition",
                "identifier": "urn:uuid:9b24f874-f3fd-5aa7-83fe-47cf2ba44c4c",
            },
            "presentation": {},
        },
        "preview": {
            "chapters": ["front", "one", "back"],
            "appendices": [],
            "metadata": {
                "subtitle": "Sample chapter",
                "description": "One selected fixture chapter.",
                "edition": "Preview fixture edition",
                "identifier": "urn:uuid:5cedda2f-7758-5ed8-a856-a84bda714f00",
            },
            "presentation": {"watermark": {"text": "SAMPLE"}},
        },
    },
}


def encoded(value):
    return (json.dumps(value, indent=2, sort_keys=True) + "\n").encode("utf-8")


def expect_failure(name, expected, callback):
    try:
        callback()
    except ReleaseProfileError as error:
        if expected not in str(error):
            raise RuntimeError(
                f"error: release fixture {name} missed {expected!r}: {error}"
            ) from error
    else:
        raise RuntimeError(f"error: release fixture {name} unexpectedly passed")


def document_failure(name, expected, mutate_defaults=None, mutate_local=None):
    defaults = copy.deepcopy(DEFAULTS)
    local = copy.deepcopy(LOCAL)
    if mutate_defaults:
        mutate_defaults(defaults)
    if mutate_local:
        mutate_local(local)
    expect_failure(name, expected, lambda: release_outputs(encoded(defaults), encoded(local)))


def write_project(root):
    book = root / "book"
    (book / ".alkahest").mkdir(parents=True)
    (book / ".alkahest/release-defaults.json").write_bytes(encoded(DEFAULTS))
    (book / "releases.json").write_bytes(encoded(LOCAL))
    (book / "media.json").write_text('{"items": {}}\n', encoding="utf-8")
    (book / "_quarto.yml").write_text(
        "project:\n  type: book\nbook:\n  chapters:\n    - index.qmd\n    - chapter-one.qmd\n    - chapter-two.qmd\n    - references.qmd\n  appendices:\n    - appendices/checklist.qmd\nbibliography: references.bib\n",
        encoding="utf-8",
    )
    for source in LOCAL["sources"].values():
        path = book / source["path"]
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(f"# {path.stem}\n", encoding="utf-8")
    sync_project_releases(root)


def main():
    document_failure(
        "defaults-schema",
        "defaults schema_version",
        mutate_defaults=lambda value: value.update(schema_version=2),
    )
    document_failure(
        "book-schema",
        "book releases schema_version",
        mutate_local=lambda value: value.update(schema_version=2),
    )
    document_failure(
        "unknown-source",
        "unknown source",
        mutate_local=lambda value: value["profiles"]["preview"]["chapters"].append("missing"),
    )
    document_failure(
        "duplicate-selection",
        "unique array",
        mutate_local=lambda value: value["profiles"]["preview"]["chapters"].append("one"),
    )
    document_failure(
        "private-selection",
        "non-release source",
        mutate_local=lambda value: value["profiles"]["preview"]["chapters"].append("private"),
    )
    document_failure(
        "incomplete-full",
        "select every source",
        mutate_local=lambda value: value["profiles"]["full"]["chapters"].remove("two"),
    )
    document_failure(
        "same-identifier",
        "distinct identifiers",
        mutate_local=lambda value: value["profiles"]["preview"]["metadata"].update(
            identifier=value["profiles"]["full"]["metadata"]["identifier"]
        ),
    )
    document_failure(
        "unsafe-url",
        "use HTTPS",
        mutate_local=lambda value: value["profiles"]["preview"]["presentation"].update(
            purchase_url="http://example.com"
        ),
    )
    document_failure(
        "too-many-preview-chapters",
        "one or two",
        mutate_local=lambda value: (
            value["sources"].update(
                three={"path": "chapter-three.qmd", "role": "chapter", "availability": "release"}
            ),
            value["profiles"]["full"]["chapters"].append("three"),
            value["profiles"]["preview"]["chapters"].extend(["two", "three"]),
        ),
    )

    resolved, first = release_outputs(encoded(DEFAULTS), encoded(LOCAL))
    _again, second = release_outputs(encoded(DEFAULTS), encoded(LOCAL))
    if first != second:
        raise RuntimeError("error: release adapters are not deterministic")
    if resolved["profiles"]["preview"]["preview"]["watermark"]["text"] != "SAMPLE":
        raise RuntimeError("error: partial preview presentation did not inherit defaults")

    with tempfile.TemporaryDirectory(prefix="alkahest-release-fixture.") as temporary:
        root = Path(temporary)
        write_project(root)
        validate_project_releases(root)
        staged = stage_project_release(root, "preview")
        stage = staged["stage"]
        if (
            not (stage / "chapter-one.qmd").is_symlink()
            or (stage / "chapter-two.qmd").exists()
            or (stage / "private").exists()
            or "chapter-two.qmd" in (stage / "_quarto.yml").read_text(encoding="utf-8")
            or "appendices:" in (stage / "_quarto.yml").read_text(encoding="utf-8")
        ):
            raise RuntimeError("error: preview staging did not enforce its allowlist")
        (root / "book/generated/release-profile-manifest.json").write_text(
            "stale\n", encoding="utf-8"
        )
        expect_failure(
            "stale-adapter",
            "missing or stale",
            lambda: sync_project_releases(root, check=True),
        )
        sync_project_releases(root)
        (root / "book/unregistered.qmd").write_text("# Missing\n", encoding="utf-8")
        expect_failure(
            "unregistered-manuscript",
            "does not exactly cover",
            lambda: validate_project_releases(root),
        )
    print(
        "ok: release-profile fixtures "
        "(inheritance, determinism, and isolated staging; "
        "9 schema and 2 stale/coverage failures rejected)"
    )


def test_contract():
    result = main()
    assert result in (None, 0)
