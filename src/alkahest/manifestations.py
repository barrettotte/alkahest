"""Validate product-level manifestations and typed publication identifiers."""

from __future__ import annotations

import hashlib
import re
import uuid
from datetime import date
from decimal import Decimal, InvalidOperation
from pathlib import Path
from urllib.parse import urlparse

from .common import ContractError, fail, load_json

ID = re.compile(r"[a-z0-9]+(?:-[a-z0-9]+)*")
LANGUAGE = re.compile(r"[a-z]{2,3}(?:-[A-Z][A-Za-z0-9]{1,7})*")
TERRITORY = re.compile(r"WORLD|[A-Z]{2}")
ISBN10 = re.compile(r"\d{9}[\dX]")
ISBN13 = re.compile(r"\d{13}")
UUID_URN = re.compile(r"urn:uuid:[0-9a-f]{8}(?:-[0-9a-f]{4}){3}-[0-9a-f]{12}")
DOI = re.compile(r"10\.\d{4,9}/[-._;()/:a-z0-9]+")
PRICE = re.compile(r"(?:0|[1-9][0-9]*)\.[0-9]{2}")

FORMATS = {"web", "epub", "pdf", "print", "bundle", "other"}
VARIANTS = {"full", "preview", "review", "translation", "supplemental"}
STATUSES = {"planned", "development", "forthcoming", "published", "withdrawn"}
IDENTIFIER_SCHEMES = {"isbn-10", "isbn-13", "uuid-urn", "doi", "url"}
AVAILABILITY = {"unavailable", "private", "preorder", "available", "withdrawn"}
RELATIONS = {"preview-of", "translation-of", "derived-from", "print-interior-from"}
MEDIA_TYPES = {
    "web": "text/html",
    "epub": "application/epub+zip",
    "pdf": "application/pdf",
}
MANIFESTATION_FIELDS = {
    "id",
    "label",
    "format",
    "variant",
    "edition",
    "language",
    "status",
    "identifiers",
    "dimensions",
    "cover",
    "dates",
    "prices",
    "availability",
    "production",
    "relation",
}


def exact_object(value, fields, label):
    if not isinstance(value, dict) or set(value) != set(fields):
        fail(f"{label} fields do not match the version 1 contract")
    return value


def required_text(value, label):
    if not isinstance(value, str) or not value.strip():
        fail(f"{label} must be nonempty text")
    return value.strip()


def iso_date(value, label):
    if value is None:
        return None
    if not isinstance(value, str):
        fail(f"{label} must use YYYY-MM-DD or null")
    try:
        parsed = date.fromisoformat(value)
    except ValueError:
        fail(f"{label} must use a real YYYY-MM-DD date")
    if parsed.isoformat() != value:
        fail(f"{label} must use YYYY-MM-DD")
    return parsed


def validate_territories(value, label):
    if not isinstance(value, list) or not value:
        fail(f"{label} needs at least one territory")
    if any(not isinstance(item, str) or not TERRITORY.fullmatch(item) for item in value):
        fail(f"{label} must use WORLD or two-letter uppercase codes")
    if len(value) != len(set(value)):
        fail(f"{label} territories must be unique")
    if "WORLD" in value and len(value) != 1:
        fail(f"{label} cannot combine WORLD with individual territories")
    return set(value)


def is_isbn10(value):
    if not isinstance(value, str) or not ISBN10.fullmatch(value):
        return False
    digits = [10 if character == "X" else int(character) for character in value]
    return sum((10 - index) * digit for index, digit in enumerate(digits)) % 11 == 0


def is_isbn13(value):
    if (
        not isinstance(value, str)
        or not ISBN13.fullmatch(value)
        or not value.startswith(("978", "979"))
    ):
        return False
    total = sum(
        int(character) * (1 if index % 2 == 0 else 3) for index, character in enumerate(value[:12])
    )
    return int(value[-1]) == (10 - total % 10) % 10


def isbn13_from_isbn10(value):
    stem = "978" + value[:9]
    total = sum(
        int(character) * (1 if index % 2 == 0 else 3) for index, character in enumerate(stem)
    )
    return stem + str((10 - total % 10) % 10)


def validate_url(value, label):
    parsed = urlparse(value) if isinstance(value, str) else None
    if (
        parsed is None
        or parsed.scheme != "https"
        or not parsed.netloc
        or parsed.username
        or parsed.password
        or parsed.fragment
    ):
        fail(f"{label} must be a canonical HTTPS URL without credentials or a fragment")


def validate_identifier(identifier, label):
    exact_object(identifier, {"scheme", "value"}, f"{label} identifier")
    scheme = identifier["scheme"]
    value = identifier["value"]
    if scheme not in IDENTIFIER_SCHEMES:
        fail(f"{label} uses an unsupported identifier scheme")
    required_text(value, f"{label} identifier value")
    if scheme == "isbn-10" and not is_isbn10(value):
        fail(f"{label} has an invalid ISBN-10 checksum or canonical form")
    if scheme == "isbn-13" and not is_isbn13(value):
        fail(f"{label} has an invalid ISBN-13 checksum, prefix, or canonical form")
    if scheme == "uuid-urn":
        if not UUID_URN.fullmatch(value):
            fail(f"{label} UUID must be a lowercase canonical URN")
        try:
            uuid.UUID(value[len("urn:uuid:") :])
        except ValueError:
            fail(f"{label} UUID is invalid")
    if scheme == "doi" and (not isinstance(value, str) or not DOI.fullmatch(value)):
        fail(f"{label} DOI must use its lowercase canonical form")
    if scheme == "url":
        validate_url(value, f"{label} URL identifier")
    return scheme, value


def validate_schema(schema):
    fields = {
        "$schema",
        "$id",
        "title",
        "description",
        "type",
        "additionalProperties",
        "required",
        "properties",
        "$defs",
    }
    exact_object(schema, fields, "manifestation schema")
    if schema["$schema"] != "https://json-schema.org/draft/2020-12/schema":
        fail("manifestation schema must use JSON Schema 2020-12")
    if schema["$id"] != "urn:alkahest:schema:manifestations:1":
        fail("manifestation schema identifier drifted")
    if set(schema["required"]) != {"schema_version", "work_id", "manifestations"}:
        fail("manifestation schema top-level fields drifted")
    definitions = schema.get("$defs", {})
    expected = {
        "id",
        "nullableString",
        "dateOrNull",
        "territories",
        "manifestation",
        "identifier",
        "dimensions",
        "cover",
        "dates",
        "price",
        "availability",
        "production",
        "relation",
    }
    if set(definitions) != expected:
        fail("manifestation schema definitions drifted")
    properties = definitions["manifestation"]["properties"]
    if (
        set(definitions["manifestation"]["required"]) != MANIFESTATION_FIELDS
        or set(properties) != MANIFESTATION_FIELDS
    ):
        fail("manifestation schema record fields drifted")
    enum_contracts = (
        (properties["format"]["enum"], FORMATS, "formats"),
        (properties["variant"]["enum"], VARIANTS, "variants"),
        (properties["status"]["enum"], STATUSES, "statuses"),
        (
            definitions["identifier"]["properties"]["scheme"]["enum"],
            IDENTIFIER_SCHEMES,
            "identifier schemes",
        ),
        (
            definitions["availability"]["properties"]["status"]["enum"],
            AVAILABILITY,
            "availability states",
        ),
        (definitions["relation"]["properties"]["type"]["enum"], RELATIONS, "relation types"),
    )
    for actual, expected_values, label in enum_contracts:
        if set(actual) != expected_values:
            fail(f"manifestation schema {label} drifted from the validator")


def validate_dimensions(value, manifestation_format, label):
    if value is None:
        if manifestation_format in {"pdf", "print"}:
            fail(f"{label} {manifestation_format} needs physical dimensions")
        return None
    if manifestation_format in {"web", "epub"}:
        fail(f"{label} reflowable format cannot declare physical dimensions")
    exact_object(value, {"width", "height", "unit"}, f"{label} dimensions")
    if value["unit"] not in {"in", "mm"}:
        fail(f"{label} dimensions use an unsupported unit")
    dimensions = []
    for field in ("width", "height"):
        number = value[field]
        if isinstance(number, bool):
            fail(f"{label} dimension {field} must be positive")
        try:
            decimal = Decimal(str(number))
        except (InvalidOperation, ValueError):
            fail(f"{label} dimension {field} must be positive")
        if not decimal.is_finite() or decimal <= 0:
            fail(f"{label} dimension {field} must be positive")
        dimensions.append(decimal)
    return tuple(dimensions) + (value["unit"],)


def safe_repository_path(root, value, label, required=False):
    if value is None and not required:
        return None
    relative = Path(value) if isinstance(value, str) else Path("/")
    if relative.is_absolute() or ".." in relative.parts or not relative.parts:
        fail(f"{label} must be a safe repository-relative path")
    return Path(root) / relative


def validate_cover(root, cover, label):
    if cover is None:
        return
    exact_object(cover, {"path", "sha256", "role"}, f"{label} cover")
    path = safe_repository_path(root, cover["path"], f"{label} cover", required=True)
    if cover["role"] not in {"front", "wrap", "digital"}:
        fail(f"{label} cover role is unsupported")
    if not isinstance(cover["sha256"], str) or not re.fullmatch(r"[0-9a-f]{64}", cover["sha256"]):
        fail(f"{label} cover needs a lowercase SHA-256 digest")
    if not path.is_file():
        fail(f"{label} cover file does not exist: {cover['path']}")
    if hashlib.sha256(path.read_bytes()).hexdigest() != cover["sha256"]:
        fail(f"{label} cover checksum drifted")


def validate_dates(dates, status, label):
    exact_object(dates, {"announcement", "publication", "withdrawal"}, f"{label} dates")
    announcement = iso_date(dates["announcement"], f"{label} announcement date")
    publication = iso_date(dates["publication"], f"{label} publication date")
    withdrawal = iso_date(dates["withdrawal"], f"{label} withdrawal date")
    if announcement and publication and announcement > publication:
        fail(f"{label} announcement date cannot follow publication")
    if withdrawal and (publication is None or withdrawal < publication):
        fail(f"{label} withdrawal date needs and cannot precede publication")
    if status in {"planned", "development"} and publication is not None:
        fail(f"{label} {status} status cannot claim a publication date")
    if status in {"forthcoming", "published", "withdrawn"} and publication is None:
        fail(f"{label} {status} status needs a publication date")
    if status == "withdrawn" and withdrawal is None:
        fail(f"{label} withdrawn status needs a withdrawal date")
    if status != "withdrawn" and withdrawal is not None:
        fail(f"{label} withdrawal date requires withdrawn status")


def validate_prices(prices, availability_territories, availability_status, label):
    if not isinstance(prices, list):
        fail(f"{label} prices must be a list")
    if prices and availability_status not in {"preorder", "available"}:
        fail(f"{label} cannot declare prices while unavailable or private")
    seen = set()
    for price in prices:
        exact_object(price, {"currency", "amount", "territories", "tax_included"}, f"{label} price")
        currency = price["currency"]
        amount = price["amount"]
        if not isinstance(currency, str) or not re.fullmatch(r"[A-Z]{3}", currency):
            fail(f"{label} price currency must use a three-letter uppercase code")
        if not isinstance(amount, str) or not PRICE.fullmatch(amount):
            fail(f"{label} price amount must use a nonnegative two-decimal string")
        territories = validate_territories(price["territories"], f"{label} price")
        if "WORLD" not in availability_territories and not territories.issubset(
            availability_territories
        ):
            fail(f"{label} price territory falls outside availability")
        if not isinstance(price["tax_included"], bool):
            fail(f"{label} price tax_included must be boolean")
        key = (currency, tuple(sorted(territories)))
        if key in seen:
            fail(f"{label} has duplicate price currency/territory scope")
        seen.add(key)


def validate_availability(availability, status, label):
    exact_object(availability, {"status", "territories", "channels"}, f"{label} availability")
    availability_status = availability["status"]
    if availability_status not in AVAILABILITY:
        fail(f"{label} availability status is unsupported")
    territories = validate_territories(availability["territories"], f"{label} availability")
    channels = availability["channels"]
    if not isinstance(channels, list) or any(
        not isinstance(item, str) or not item.strip() for item in channels
    ):
        fail(f"{label} availability channels must be nonempty strings")
    if len(channels) != len(set(channels)):
        fail(f"{label} availability channels must be unique")
    if availability_status in {"preorder", "available"} and not channels:
        fail(f"{label} {availability_status} availability needs a distribution channel")
    if availability_status in {"unavailable", "private", "withdrawn"} and channels:
        fail(f"{label} {availability_status} availability cannot declare channels")
    allowed = {
        "planned": {"unavailable"},
        "development": {"unavailable", "private"},
        "forthcoming": {"unavailable", "preorder"},
        "published": {"available"},
        "withdrawn": {"withdrawn"},
    }
    if availability_status not in allowed[status]:
        fail(f"{label} lifecycle and availability states are inconsistent")
    return territories, availability_status


def validate_production(root, production, manifestation_format, status, label):
    exact_object(production, {"profile", "artifact", "media_type"}, f"{label} production")
    required_text(production["profile"], f"{label} production profile")
    artifact = safe_repository_path(root, production["artifact"], f"{label} artifact")
    if status == "planned" and artifact is not None:
        fail(f"{label} planned manifestation cannot claim an artifact")
    if status != "planned" and artifact is None:
        fail(f"{label} non-planned manifestation needs an artifact path")
    if artifact is not None and not str(artifact.relative_to(root)).startswith("book/_build/"):
        fail(f"{label} artifact must remain under book/_build")
    expected_media = MEDIA_TYPES.get(manifestation_format)
    if expected_media and production["media_type"] != expected_media:
        fail(f"{label} has the wrong media type for {manifestation_format}")
    if manifestation_format == "print" and production["media_type"] is not None:
        fail(f"{label} print product cannot use a digital media type")
    if manifestation_format not in {*MEDIA_TYPES, "print"}:
        required_text(production["media_type"], f"{label} media type")
    return production["artifact"]


def validate_record(root, data):
    exact_object(data, {"schema_version", "work_id", "manifestations"}, "manifestation registry")
    if data["schema_version"] != 1:
        fail("manifestation registry schema_version must be 1")
    if not isinstance(data["work_id"], str) or not ID.fullmatch(data["work_id"]):
        fail("manifestation work_id must be lowercase kebab-case")
    manifestations = data["manifestations"]
    if not isinstance(manifestations, list) or not manifestations:
        fail("manifestation registry needs at least one record")

    records = {}
    identifiers = set()
    artifacts = set()
    dimensions = {}
    for manifestation in manifestations:
        exact_object(manifestation, MANIFESTATION_FIELDS, "manifestation")
        identifier = manifestation["id"]
        if not isinstance(identifier, str) or not ID.fullmatch(identifier) or identifier in records:
            fail("manifestation ids must be unique lowercase kebab-case identifiers")
        records[identifier] = manifestation
        label = f"manifestation {identifier}"
        required_text(manifestation["label"], f"{label} label")
        if manifestation["format"] not in FORMATS:
            fail(f"{label} format is unsupported")
        if manifestation["variant"] not in VARIANTS:
            fail(f"{label} variant is unsupported")
        if not isinstance(manifestation["edition"], str) or not ID.fullmatch(
            manifestation["edition"]
        ):
            fail(f"{label} edition must be lowercase kebab-case")
        if not isinstance(manifestation["language"], str) or not LANGUAGE.fullmatch(
            manifestation["language"]
        ):
            fail(f"{label} language must use the supported BCP 47 form")
        if manifestation["status"] not in STATUSES:
            fail(f"{label} lifecycle status is unsupported")

        typed = manifestation["identifiers"]
        if not isinstance(typed, list):
            fail(f"{label} identifiers must be a list")
        local_schemes = set()
        isbn_values = {}
        for item in typed:
            key = validate_identifier(item, label)
            if key[0].startswith("isbn-") and manifestation["format"] not in {
                "epub",
                "pdf",
                "print",
            }:
                fail(f"{label} format is not eligible for an ISBN")
            if key in identifiers:
                fail(f"publication identifier is reused across manifestations: {key[1]}")
            identifiers.add(key)
            if key[0] in local_schemes:
                fail(f"{label} repeats identifier scheme {key[0]}")
            local_schemes.add(key[0])
            if key[0].startswith("isbn-"):
                isbn_values[key[0]] = key[1]
        if (
            set(isbn_values) == {"isbn-10", "isbn-13"}
            and isbn13_from_isbn10(isbn_values["isbn-10"]) != isbn_values["isbn-13"]
        ):
            fail(f"{label} ISBN-10 and ISBN-13 identify different products")

        dimensions[identifier] = validate_dimensions(
            manifestation["dimensions"], manifestation["format"], label
        )
        validate_cover(root, manifestation["cover"], label)
        validate_dates(manifestation["dates"], manifestation["status"], label)
        territories, availability_status = validate_availability(
            manifestation["availability"], manifestation["status"], label
        )
        validate_prices(manifestation["prices"], territories, availability_status, label)
        artifact = validate_production(
            root,
            manifestation["production"],
            manifestation["format"],
            manifestation["status"],
            label,
        )
        if artifact is not None:
            if artifact in artifacts:
                fail(f"artifact path is reused across manifestations: {artifact}")
            artifacts.add(artifact)
        relation = manifestation["relation"]
        if relation is not None:
            exact_object(relation, {"type", "target"}, f"{label} relation")
            if relation["type"] not in RELATIONS:
                fail(f"{label} relation type is unsupported")
            if not isinstance(relation["target"], str) or not ID.fullmatch(relation["target"]):
                fail(f"{label} relation target is invalid")

    for identifier, manifestation in records.items():
        label = f"manifestation {identifier}"
        relation = manifestation["relation"]
        variant = manifestation["variant"]
        required_relation = {
            "preview": "preview-of",
            "translation": "translation-of",
            "review": "derived-from",
            "supplemental": "derived-from",
        }.get(variant)
        if required_relation and (relation is None or relation["type"] != required_relation):
            fail(f"{label} {variant} variant needs a {required_relation} relation")
        if manifestation["format"] == "print" and (
            relation is None or relation["type"] != "print-interior-from"
        ):
            fail(f"{label} print product needs a print-interior-from relation")
        if relation is None:
            continue
        target_id = relation["target"]
        if target_id == identifier or target_id not in records:
            fail(f"{label} relation target is missing or self-referential")
        target = records[target_id]
        if target["language"] != manifestation["language"] and relation["type"] != "translation-of":
            fail(f"{label} non-translation relation must retain language")
        if relation["type"] == "translation-of" and (
            target["language"] == manifestation["language"]
            or target["format"] != manifestation["format"]
        ):
            fail(f"{label} translation must change language within one format")
        if relation["type"] == "preview-of":
            if target["variant"] != "full":
                fail(f"{label} preview must point to a full manifestation")
            if target["format"] != manifestation["format"]:
                fail(f"{label} preview must retain its full manifestation format")
            if manifestation["format"] == "pdf" and dimensions[identifier] != dimensions[target_id]:
                fail(f"{label} PDF preview must retain its full manifestation dimensions")
        if relation["type"] == "print-interior-from" and (
            target["format"] != "pdf" or dimensions[identifier] != dimensions[target_id]
        ):
            fail(f"{label} print interior relation needs a dimension-matched PDF")

    visited = set()

    def visit(identifier, active):
        if identifier in active:
            fail("manifestation relations contain a cycle")
        if identifier in visited:
            return
        active.add(identifier)
        relation = records[identifier]["relation"]
        if relation is not None:
            visit(relation["target"], active)
        active.remove(identifier)
        visited.add(identifier)

    for identifier in records:
        visit(identifier, set())
    return records


def points_to_inches(points):
    return Decimal(str(points)) / Decimal(72)


def validate_repository(root, registry, records):
    root = Path(root)
    publication = load_json(root / "book/publication.json", "canonical publication metadata")
    if registry["work_id"] != publication.get("work", {}).get("id"):
        fail("manifestation registry work_id drifted from canonical publication metadata")
    editions = load_json(root / "book/editions.json", "edition registry").get("editions", {})
    locales = load_json(root / "config/localization/locales.json", "locale registry")
    locale_tags = {locale["tag"] for locale in locales.get("locales", [])}
    reproducibility = load_json(root / "book/reproducibility.json", "reproducibility policy")
    reproducible_artifacts = {
        artifact["path"] for artifact in reproducibility.get("contract", {}).get("artifacts", [])
    }
    preflight = load_json(root / "config/pdf/preflight.json", "PDF preflight policy")
    pdf_profiles = {profile["artifact"]: profile for profile in preflight.get("profiles", [])}

    formats = set()
    variants = set()
    for identifier, manifestation in records.items():
        label = f"manifestation {identifier}"
        formats.add(manifestation["format"])
        variants.add(manifestation["variant"])
        edition = editions.get(manifestation["edition"])
        if not isinstance(edition, dict):
            fail(f"{label} references an unknown edition")
        required_format = {
            "web": "html",
            "epub": "epub",
            "pdf": "typst",
            "print": "typst",
        }.get(manifestation["format"])
        if required_format and required_format not in edition.get("formats", []):
            fail(f"{label} edition does not permit its output format")
        if manifestation["language"] not in locale_tags:
            fail(f"{label} language is absent from the locale registry")

        artifact = manifestation["production"]["artifact"]
        if (
            manifestation["format"] in {"web", "epub", "pdf"}
            and manifestation["variant"] in {"full", "review"}
            and artifact not in reproducible_artifacts
        ):
            fail(f"{label} primary artifact is absent from the reproducibility policy")
        if manifestation["format"] == "pdf" and manifestation["variant"] in {"full", "review"}:
            profile = pdf_profiles.get(artifact)
            if not profile:
                fail(f"{label} PDF artifact is absent from preflight policy")
            expected = manifestation["dimensions"]
            width = points_to_inches(profile["trim_points"][0])
            height = points_to_inches(profile["trim_points"][1])
            if (
                expected["unit"] != "in"
                or Decimal(str(expected["width"])) != width
                or Decimal(str(expected["height"])) != height
            ):
                fail(f"{label} dimensions drifted from PDF preflight")
        for item in manifestation["identifiers"]:
            if item["scheme"] == "uuid-urn" and manifestation["format"] != "epub":
                fail(f"{label} UUID URN is reserved for EPUB manifestations")
    full_epub_uuid = next(
        (
            item["value"]
            for item in records["epub-full-en"]["identifiers"]
            if item["scheme"] == "uuid-urn"
        ),
        None,
    )
    if full_epub_uuid != reproducibility.get("epub_identifier"):
        fail("full EPUB manifestation UUID drifted from reproducibility policy")
    preview_epub_uuid = next(
        (
            item["value"]
            for item in records["epub-preview-en"]["identifiers"]
            if item["scheme"] == "uuid-urn"
        ),
        None,
    )
    preview_profile = (root / "book/_quarto-preview.yml").read_text(encoding="utf-8")
    if f'identifier: "{preview_epub_uuid}"' not in preview_profile:
        fail("preview EPUB manifestation UUID drifted from its Quarto profile")
    if preview_epub_uuid == full_epub_uuid:
        fail("full and preview EPUB manifestations need distinct UUIDs")
    if not {"web", "epub", "pdf", "print"}.issubset(formats):
        fail("reference manifestations must cover web, EPUB, PDF, and print")
    if not {"full", "preview", "review", "translation", "supplemental"}.issubset(variants):
        fail("reference manifestations must cover every supported variant")

    render = (root / "src/alkahest/rendering/pipeline.py").read_text(encoding="utf-8")
    for marker in (
        "_build/smoke/editions/preview/html",
        "_build/smoke/editions/preview/epub",
        "_build/smoke/editions/preview/typst",
        "_build/locale/fr/html",
        "_build/smoke/editions/supplemental/html",
    ):
        if marker not in render:
            fail(f"render pipeline is missing manifestation artifact {marker}")
    integration = {
        "makefile": root / "Makefile",
        "tasks": root / "src/alkahest/tasks.py",
        "documentation": root / "docs/manifestations.md",
    }
    texts = {name: path.read_text(encoding="utf-8") for name, path in integration.items()}
    for marker in ("check-%:", "test-%:"):
        if marker not in texts["makefile"]:
            fail(f"Makefile is missing manifestation target {marker}")
    for marker in ('"manifestations", ":check-manifestations"',):
        if marker not in texts["tasks"]:
            fail(f"task registry does not include manifestations entry {marker}")
    for marker in (
        "book/manifestations.json",
        "config/metadata/manifestations.schema.json",
        "ISBN-10",
        "ISBN-13",
        "rendition",
    ):
        if marker not in texts["documentation"]:
            fail(f"manifestation documentation is missing {marker!r}")


def load_and_validate(root):
    root = Path(root)
    schema = load_json(root / "config/metadata/manifestations.schema.json", "manifestation schema")
    registry = load_json(root / "book/manifestations.json", "manifestation registry")
    validate_schema(schema)
    records = validate_record(root, registry)
    validate_repository(root, registry, records)
    return registry, records


__all__ = [
    "ContractError",
    "is_isbn10",
    "is_isbn13",
    "load_and_validate",
    "validate_identifier",
    "validate_record",
    "validate_repository",
    "validate_schema",
]
