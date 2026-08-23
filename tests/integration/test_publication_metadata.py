"""Exercise canonical publication metadata and adapter-parity contracts."""

import copy
import json
import tempfile
from pathlib import Path

from alkahest.metadata_generation import quarto_metadata
from alkahest.publication_metadata import (
    ContractError,
    validate_record,
    validate_repository,
    validate_schema,
)

ROOT = Path(__file__).resolve().parent.parent.parent
RECORD = json.loads((ROOT / "book/publication.json").read_text(encoding="utf-8"))
SCHEMA = json.loads((ROOT / "config/metadata/publication.schema.json").read_text(encoding="utf-8"))


def changed(value, mutate):
    result = copy.deepcopy(value)
    mutate(result)
    return result


def expect_failure(name, message, operation):
    try:
        operation()
    except ContractError as error:
        if message not in str(error):
            raise RuntimeError(f"metadata fixture {name!r} missed diagnostic {message!r}: {error}")
        return
    raise RuntimeError(f"invalid publication metadata fixture passed: {name}")


def write_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8")


def integration_root(directory):
    root = Path(directory)
    (root / "book").mkdir(parents=True)
    (root / "scripts").mkdir()
    (root / "src/alkahest").mkdir(parents=True)
    (root / "docs").mkdir()
    (root / "book/_quarto.yml").write_text(
        "metadata-files:\n  - generated/metadata.yml\nbook:\n  chapters: []\n",
        encoding="utf-8",
    )
    generated = root / "book/generated/metadata.yml"
    generated.parent.mkdir()
    generated.write_bytes(quarto_metadata(RECORD))
    epub = {
        "standard": RECORD["accessibility"]["review"]["standard"],
        "language": RECORD["work"]["language"]["primary"],
        "claim_status": RECORD["accessibility"]["review"]["status"],
        "discovery": {
            "accessibility_features": RECORD["accessibility"]["features"],
            "accessibility_hazards": RECORD["accessibility"]["hazards"],
            "accessibility_summary": RECORD["accessibility"]["summary"],
        },
    }
    assets = {
        "artifact_contract": {
            "expected_pdf_title": RECORD["work"]["title"],
            "expected_pdf_author": "Barrett Otte",
            "expected_pdf_subject": RECORD["work"]["descriptions"]["long"],
            "expected_pdf_keywords": ", ".join(RECORD["work"]["keywords"]),
        }
    }
    write_json(root / "book/epub-accessibility.json", epub)
    write_json(root / "book/assets.json", assets)
    write_json(root / "book/reproducibility.json", {"schema_version": 1})
    (root / "Makefile").write_text(
        "check-%:\n\ttest -n '$*'\ntest-%:\n\ttest -n '$*'\n", encoding="utf-8"
    )
    (root / "src/alkahest/tasks.py").write_text(
        'ScriptTask("publication-metadata", ":check-publication-metadata")\n',
        encoding="utf-8",
    )
    (root / "docs/publication-metadata.md").write_text(
        "book/publication.json config/metadata/publication.schema.json work-level manifestation\n",
        encoding="utf-8",
    )
    return root


def main():
    validate_schema(copy.deepcopy(SCHEMA))
    validate_record(ROOT, copy.deepcopy(RECORD))
    expect_failure(
        "schema-role-drift",
        "roles drifted",
        lambda: validate_schema(
            changed(
                SCHEMA,
                lambda schema: schema["$defs"]["contributor"]["properties"]["roles"]["items"][
                    "enum"
                ].append("unknown-role"),
            )
        ),
    )
    cases = [
        (
            "extra-top-level-field",
            "publication metadata fields",
            lambda record: record.update({"unknown": True}),
        ),
        (
            "placeholder-title",
            "non-placeholder",
            lambda record: record["work"].update({"title": "[Book title]"}),
        ),
        (
            "weak-description",
            "short description",
            lambda record: record["work"]["descriptions"].update({"short": "Brief"}),
        ),
        (
            "date-order",
            "cannot precede",
            lambda record: record["work"]["dates"].update({"modified": "2026-01-01"}),
        ),
        (
            "published-without-date",
            "needs a publication date",
            lambda record: record["work"].update({"status": "published"}),
        ),
        (
            "mixed-world-territory",
            "WORLD cannot",
            lambda record: record["work"].update({"territories": ["WORLD", "US"]}),
        ),
        (
            "duplicate-subject",
            "subject scheme/code pairs",
            lambda record: record["work"]["subjects"].append(
                copy.deepcopy(record["work"]["subjects"][0])
            ),
        ),
        (
            "duplicate-keyword",
            "keywords values must be unique",
            lambda record: record["work"]["keywords"].append("BOOK TEMPLATE"),
        ),
        (
            "duplicate-contributor",
            "contributor ids",
            lambda record: record["contributors"].append(copy.deepcopy(record["contributors"][0])),
        ),
        (
            "missing-author-role",
            "author role",
            lambda record: record["contributors"][0].update({"roles": ["editor"]}),
        ),
        (
            "invalid-orcid-checksum",
            "invalid check digit",
            lambda record: record["contributors"][0].update(
                {"orcid": "https://orcid.org/0000-0000-0000-0000"}
            ),
        ),
        (
            "imprint-without-publisher",
            "imprint requires",
            lambda record: record["publication"]["imprint"].update({"name": "Example imprint"}),
        ),
        (
            "selected-license-without-expression",
            "needs an SPDX expression",
            lambda record: record["rights"]["licenses"][0].update({"status": "selected"}),
        ),
        (
            "contradictory-hazards",
            "cannot be combined",
            lambda record: record["accessibility"].update({"hazards": ["none", "flashing"]}),
        ),
        (
            "public-repository-without-url",
            "must be an HTTPS URL",
            lambda record: record["provenance"]["repository"].update({"visibility": "public"}),
        ),
        (
            "unsafe-policy-path",
            "safe repository policy path",
            lambda record: record["provenance"]["policies"].update({"rights": "../assets.json"}),
        ),
    ]
    for name, message, mutate in cases:
        expect_failure(
            name,
            message,
            lambda mutate=mutate: validate_record(ROOT, changed(RECORD, mutate)),
        )

    with tempfile.TemporaryDirectory(prefix="alkahest-publication-metadata.") as directory:
        root = integration_root(directory)
        policies = validate_record(root, copy.deepcopy(RECORD))
        validate_repository(root, copy.deepcopy(RECORD), policies)
        epub_path = root / "book/epub-accessibility.json"
        epub = json.loads(epub_path.read_text(encoding="utf-8"))
        epub["discovery"]["accessibility_features"].append("displayTransformability")
        write_json(epub_path, epub)
        expect_failure(
            "adapter-drift",
            "accessibility_features drifted",
            lambda: validate_repository(root, copy.deepcopy(RECORD), policies),
        )

    print(
        "ok: publication metadata fixtures "
        f"({len(cases) + 2} schema, work, contributor, rights, accessibility, "
        "provenance, and adapter failures rejected)"
    )


def test_contract():
    result = main()
    assert result in (None, 0)
