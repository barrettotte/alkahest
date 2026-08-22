"""Exercise manifestation, relation, price, cover, and identifier contracts."""

import copy
import hashlib
import json
import sys
import tempfile
from pathlib import Path

from lib.alkahest.manifestations import (
    ContractError,
    validate_identifier,
    validate_record,
    validate_repository,
    validate_schema,
)


ROOT = Path(__file__).resolve().parent.parent
REGISTRY = json.loads((ROOT / "book/manifestations.json").read_text(encoding="utf-8"))
SCHEMA = json.loads(
    (ROOT / "config/metadata/manifestations.schema.json").read_text(encoding="utf-8")
)


def changed(value, mutate):
    result = copy.deepcopy(value)
    mutate(result)
    return result


def manifestation(registry, identifier):
    return next(item for item in registry["manifestations"] if item["id"] == identifier)


def expect_failure(name, message, operation):
    try:
        operation()
    except ContractError as error:
        if message not in str(error):
            raise RuntimeError(
                f"manifestation fixture {name!r} missed diagnostic {message!r}: {error}"
            )
        return
    raise RuntimeError(f"invalid manifestation fixture passed: {name}")


def set_identifiers(registry, identifier, values):
    manifestation(registry, identifier)["identifiers"] = values


def main():
    validate_schema(copy.deepcopy(SCHEMA))
    records = validate_record(ROOT, copy.deepcopy(REGISTRY))
    validate_identifier(
        {"scheme": "isbn-10", "value": "0306406152"}, "valid fixture"
    )
    validate_identifier(
        {"scheme": "isbn-13", "value": "9780306406157"}, "valid fixture"
    )
    validate_identifier(
        {
            "scheme": "doi",
            "value": "10.5555/alkahest.reference-book",
        },
        "valid fixture",
    )

    expect_failure(
        "schema-identifier-drift",
        "identifier schemes drifted",
        lambda: validate_schema(
            changed(
                SCHEMA,
                lambda schema: schema["$defs"]["identifier"]["properties"]["scheme"][
                    "enum"
                ].append("untyped"),
            )
        ),
    )
    cases = [
        (
            "invalid-isbn-10",
            "invalid ISBN-10",
            lambda registry: set_identifiers(
                registry,
                "pdf-full-7x10-en",
                [{"scheme": "isbn-10", "value": "0306406153"}],
            ),
        ),
        (
            "invalid-isbn-13",
            "invalid ISBN-13",
            lambda registry: set_identifiers(
                registry,
                "pdf-full-7x10-en",
                [{"scheme": "isbn-13", "value": "9780306406158"}],
            ),
        ),
        (
            "mismatched-isbn-pair",
            "identify different products",
            lambda registry: set_identifiers(
                registry,
                "pdf-full-7x10-en",
                [
                    {"scheme": "isbn-10", "value": "0131103628"},
                    {"scheme": "isbn-13", "value": "9780306406157"},
                ],
            ),
        ),
        (
            "duplicate-identifier",
            "reused across manifestations",
            lambda registry: set_identifiers(
                registry,
                "web-full-en",
                copy.deepcopy(manifestation(registry, "epub-full-en")["identifiers"]),
            ),
        ),
        (
            "web-isbn",
            "not eligible for an ISBN",
            lambda registry: set_identifiers(
                registry,
                "web-full-en",
                [{"scheme": "isbn-13", "value": "9780306406157"}],
            ),
        ),
        (
            "missing-pdf-dimensions",
            "needs physical dimensions",
            lambda registry: manifestation(registry, "pdf-full-7x10-en").update(
                {"dimensions": None}
            ),
        ),
        (
            "web-dimensions",
            "reflowable format",
            lambda registry: manifestation(registry, "web-full-en").update(
                {"dimensions": {"width": 7, "height": 10, "unit": "in"}}
            ),
        ),
        (
            "planned-artifact",
            "planned manifestation cannot claim",
            lambda registry: manifestation(registry, "print-full-7x10-en")[
                "production"
            ].update({"artifact": "book/_build/print/final.pdf"}),
        ),
        (
            "development-publication-date",
            "cannot claim a publication date",
            lambda registry: manifestation(registry, "web-full-en")["dates"].update(
                {"publication": "2026-08-21"}
            ),
        ),
        (
            "private-price",
            "cannot declare prices",
            lambda registry: manifestation(registry, "web-full-en").update(
                {
                    "prices": [
                        {
                            "currency": "USD",
                            "amount": "12.00",
                            "territories": ["WORLD"],
                            "tax_included": False,
                        }
                    ]
                }
            ),
        ),
        (
            "available-without-channel",
            "needs a distribution channel",
            lambda registry: manifestation(registry, "web-full-en")[
                "availability"
            ].update({"status": "available"}),
        ),
        (
            "preview-without-relation",
            "needs a preview-of relation",
            lambda registry: manifestation(registry, "web-preview-en").update(
                {"relation": None}
            ),
        ),
        (
            "preview-format-drift",
            "must retain its full manifestation format",
            lambda registry: manifestation(registry, "web-preview-en")["relation"].update(
                {"target": "epub-full-en"}
            ),
        ),
        (
            "preview-dimension-drift",
            "must retain its full manifestation dimensions",
            lambda registry: manifestation(registry, "pdf-preview-7x10-en").update(
                {"dimensions": {"width": 6, "height": 9, "unit": "in"}}
            ),
        ),
        (
            "translation-without-language-change",
            "translation must change language",
            lambda registry: manifestation(registry, "web-translation-fr").update(
                {"language": "en-US"}
            ),
        ),
        (
            "print-dimension-drift",
            "dimension-matched PDF",
            lambda registry: manifestation(registry, "print-full-7x10-en").update(
                {"dimensions": {"width": 6, "height": 9, "unit": "in"}}
            ),
        ),
        (
            "duplicate-artifact",
            "artifact path is reused",
            lambda registry: manifestation(registry, "pdf-full-6x9-en")[
                "production"
            ].update(
                {
                    "artifact": manifestation(registry, "pdf-full-7x10-en")[
                        "production"
                    ]["artifact"]
                }
            ),
        ),
        (
            "unsafe-artifact",
            "safe repository-relative path",
            lambda registry: manifestation(registry, "web-full-en")[
                "production"
            ].update({"artifact": "/tmp/book"}),
        ),
        (
            "duplicate-manifestation-id",
            "manifestation ids",
            lambda registry: registry["manifestations"].append(
                copy.deepcopy(registry["manifestations"][0])
            ),
        ),
        (
            "relation-cycle",
            "relations contain a cycle",
            lambda registry: manifestation(registry, "pdf-full-7x10-en").update(
                {
                    "relation": {
                        "type": "derived-from",
                        "target": "pdf-review-letter-en",
                    }
                }
            ),
        ),
    ]
    for name, message, mutate in cases:
        expect_failure(
            name,
            message,
            lambda mutate=mutate: validate_record(ROOT, changed(REGISTRY, mutate)),
        )

    with tempfile.TemporaryDirectory(prefix="alkahest-manifestation-cover.") as directory:
        root = Path(directory)
        cover_path = root / "book/covers/specimen.png"
        cover_path.parent.mkdir(parents=True)
        cover_path.write_bytes(b"deterministic cover fixture")
        cover = {
            "path": "book/covers/specimen.png",
            "sha256": hashlib.sha256(cover_path.read_bytes()).hexdigest(),
            "role": "digital",
        }
        with_cover = changed(
            REGISTRY,
            lambda registry: manifestation(registry, "web-full-en").update(
                {"cover": cover}
            ),
        )
        validate_record(root, with_cover)
        cover["sha256"] = "0" * 64
        expect_failure(
            "cover-checksum-drift",
            "cover checksum drifted",
            lambda: validate_record(
                root,
                changed(
                    REGISTRY,
                    lambda registry: manifestation(registry, "web-full-en").update(
                        {"cover": cover}
                    ),
                ),
            ),
        )

    drifted = changed(
        REGISTRY,
        lambda registry: set_identifiers(
            registry,
            "epub-full-en",
            [
                {
                    "scheme": "uuid-urn",
                    "value": "urn:uuid:00000000-0000-4000-8000-000000000000",
                }
            ],
        ),
    )
    expect_failure(
        "epub-identifier-drift",
        "UUID drifted",
        lambda: validate_repository(ROOT, drifted, validate_record(ROOT, drifted)),
    )

    print(
        "ok: manifestation fixtures "
        f"({len(cases) + 3} schema, ISBN, identifier, dimension, cover, date, "
        "price, availability, relation, artifact, and adapter failures rejected)"
    )


if __name__ == "__main__":
    try:
        main()
    except RuntimeError as error:
        print("error: " + str(error), file=sys.stderr)
        raise SystemExit(1)
