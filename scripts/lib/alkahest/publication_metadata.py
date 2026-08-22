"""Validate canonical work-level publication metadata and current adapters."""

from __future__ import annotations

import re
from datetime import date
from pathlib import Path
from urllib.parse import urlparse

from .common import ContractError, fail, load_json


ID = re.compile(r"[a-z0-9]+(?:-[a-z0-9]+)*")
LANGUAGE = re.compile(r"[a-z]{2,3}(?:-[A-Z][A-Za-z0-9]{1,7})*")
TERRITORY = re.compile(r"WORLD|[A-Z]{2}")
ORCID = re.compile(r"https://orcid\.org/(\d{4})-(\d{4})-(\d{4})-(\d{3}[\dX])")
PLACEHOLDER = re.compile(r"^\[[^]]+\]$")

WORK_STATUSES = {"development", "forthcoming", "published", "withdrawn"}
CONTRIBUTOR_ROLES = {
    "author",
    "editor",
    "translator",
    "illustrator",
    "photographer",
    "technical-reviewer",
    "foreword-author",
    "introduction-author",
    "compiler",
    "designer",
}
LICENSE_STATUSES = {"undecided", "selected", "governed-separately"}
REVIEW_STATUSES = {
    "not-started",
    "pending-manual-review",
    "conformant",
    "nonconformant",
}
VISIBILITIES = {"private", "public", "archived"}
TOP_LEVEL = {
    "schema_version",
    "work",
    "contributors",
    "publication",
    "rights",
    "accessibility",
    "provenance",
}


def exact_object(value, fields, label):
    if not isinstance(value, dict) or set(value) != set(fields):
        fail(f"{label} fields do not match the version 1 contract")
    return value


def required_text(value, label, minimum=1):
    if (
        not isinstance(value, str)
        or len(value.strip()) < minimum
        or PLACEHOLDER.fullmatch(value.strip())
    ):
        fail(f"{label} must be substantive, non-placeholder text")
    return value.strip()


def nullable_text(value, label):
    if value is None:
        return None
    return required_text(value, label)


def unique_text_list(value, label, minimum=1, item_minimum=1):
    if not isinstance(value, list) or len(value) < minimum:
        fail(f"{label} needs at least {minimum} value(s)")
    normalized = []
    for item in value:
        normalized.append(required_text(item, label, item_minimum).casefold())
    if len(normalized) != len(set(normalized)):
        fail(f"{label} values must be unique")
    return value


def iso_date(value, label):
    if not isinstance(value, str):
        fail(f"{label} must use YYYY-MM-DD")
    try:
        parsed = date.fromisoformat(value)
    except ValueError:
        fail(f"{label} must use a real YYYY-MM-DD date")
    if parsed.isoformat() != value:
        fail(f"{label} must use YYYY-MM-DD")
    return parsed


def web_url(value, label, required=False):
    if value is None and not required:
        return
    if not isinstance(value, str):
        fail(f"{label} must be an HTTPS URL")
    parsed = urlparse(value)
    if parsed.scheme != "https" or not parsed.netloc or parsed.username or parsed.password:
        fail(f"{label} must be an HTTPS URL without embedded credentials")


def validate_orcid(value, label):
    if value is None:
        return
    match = ORCID.fullmatch(value) if isinstance(value, str) else None
    if not match:
        fail(f"{label} must be a canonical HTTPS ORCID")
    characters = "".join(match.groups())
    total = 0
    for character in characters[:15]:
        total = (total + int(character)) * 2
    check = (12 - total % 11) % 11
    expected = "X" if check == 10 else str(check)
    if characters[-1] != expected:
        fail(f"{label} has an invalid check digit")


def validate_schema(schema):
    required = {"$schema", "$id", "title", "description", "type", "additionalProperties", "required", "properties", "$defs"}
    exact_object(schema, required, "publication metadata schema")
    if schema["$schema"] != "https://json-schema.org/draft/2020-12/schema":
        fail("publication metadata schema must use JSON Schema 2020-12")
    if schema["$id"] != "urn:alkahest:schema:publication-metadata:1":
        fail("publication metadata schema identifier drifted")
    if schema["type"] != "object" or schema["additionalProperties"] is not False:
        fail("publication metadata schema must define a closed object")
    if set(schema["required"]) != TOP_LEVEL or set(schema["properties"]) != TOP_LEVEL:
        fail("publication metadata schema top-level fields drifted")
    if schema["properties"].get("schema_version") != {"const": 1}:
        fail("publication metadata schema must lock schema_version 1")
    definitions = schema["$defs"]
    expected_definitions = {
        "nullableString",
        "date",
        "work",
        "contributor",
        "subject",
        "audience",
        "publication",
        "organization",
        "rights",
        "license",
        "accessibility",
        "provenance",
    }
    if not isinstance(definitions, dict) or set(definitions) != expected_definitions:
        fail("publication metadata schema definitions drifted")
    if set(definitions["contributor"]["properties"]["roles"]["items"]["enum"]) != CONTRIBUTOR_ROLES:
        fail("publication metadata contributor roles drifted from the validator")
    if set(definitions["work"]["properties"]["status"]["enum"]) != WORK_STATUSES:
        fail("publication metadata work statuses drifted from the validator")
    if set(definitions["license"]["properties"]["status"]["enum"]) != LICENSE_STATUSES:
        fail("publication metadata license statuses drifted from the validator")


def validate_work(work):
    fields = {
        "id", "status", "title", "subtitle", "descriptions", "series", "edition",
        "dates", "language", "territories", "subjects", "keywords", "audiences",
    }
    exact_object(work, fields, "work metadata")
    if not isinstance(work["id"], str) or not ID.fullmatch(work["id"]):
        fail("work id must be a lowercase kebab-case identifier")
    if work["status"] not in WORK_STATUSES:
        fail("work status is unsupported")
    required_text(work["title"], "work title")
    nullable_text(work["subtitle"], "work subtitle")
    descriptions = exact_object(work["descriptions"], {"short", "long"}, "work descriptions")
    required_text(descriptions["short"], "short description", 40)
    required_text(descriptions["long"], "long description", 100)
    if descriptions["short"] == descriptions["long"]:
        fail("short and long descriptions must differ")

    series = work["series"]
    if series is not None:
        exact_object(series, {"name", "number"}, "series metadata")
        required_text(series["name"], "series name")
        nullable_text(series["number"], "series number")
    edition = exact_object(work["edition"], {"name", "number", "statement"}, "edition metadata")
    required_text(edition["name"], "edition name")
    if edition["number"] is not None and (
        not isinstance(edition["number"], int)
        or isinstance(edition["number"], bool)
        or edition["number"] < 1
    ):
        fail("edition number must be a positive integer or null")
    required_text(edition["statement"], "edition statement")

    dates = exact_object(work["dates"], {"created", "modified", "publication"}, "work dates")
    created = iso_date(dates["created"], "created date")
    modified = iso_date(dates["modified"], "modified date")
    if modified < created:
        fail("modified date cannot precede created date")
    publication = None
    if dates["publication"] is not None:
        publication = iso_date(dates["publication"], "publication date")
        if publication < created:
            fail("publication date cannot precede created date")
    if work["status"] in {"forthcoming", "published"} and publication is None:
        fail(f"{work['status']} work needs a publication date")
    if work["status"] == "development" and publication is not None:
        fail("development work cannot claim a publication date")

    language = exact_object(work["language"], {"primary", "original"}, "language metadata")
    for field in ("primary", "original"):
        if not isinstance(language[field], str) or not LANGUAGE.fullmatch(language[field]):
            fail(f"{field} language must use the supported BCP 47 form")
    territories = work["territories"]
    if not isinstance(territories, list) or not territories:
        fail("work needs at least one territory")
    if any(not isinstance(item, str) or not TERRITORY.fullmatch(item) for item in territories):
        fail("territories must use WORLD or two-letter uppercase codes")
    if len(territories) != len(set(territories)):
        fail("territories must be unique")
    if "WORLD" in territories and len(territories) != 1:
        fail("WORLD cannot be combined with individual territories")

    subjects = work["subjects"]
    if not isinstance(subjects, list) or not subjects:
        fail("work needs at least one subject")
    subject_keys = set()
    for subject in subjects:
        exact_object(subject, {"scheme", "code", "label"}, "subject metadata")
        scheme = required_text(subject["scheme"], "subject scheme")
        code = required_text(subject["code"], "subject code")
        required_text(subject["label"], "subject label")
        key = (scheme.casefold(), code.casefold())
        if key in subject_keys:
            fail("subject scheme/code pairs must be unique")
        subject_keys.add(key)
        if scheme == "local" and not ID.fullmatch(code):
            fail("local subject codes must use lowercase kebab-case")
    unique_text_list(work["keywords"], "keywords", minimum=3, item_minimum=2)

    audiences = work["audiences"]
    if not isinstance(audiences, list) or not audiences:
        fail("work needs at least one audience")
    audience_codes = set()
    for audience in audiences:
        exact_object(audience, {"code", "label"}, "audience metadata")
        code = required_text(audience["code"], "audience code")
        if not ID.fullmatch(code) or code in audience_codes:
            fail("audience codes must be unique lowercase kebab-case identifiers")
        audience_codes.add(code)
        required_text(audience["label"], "audience label")


def validate_contributors(contributors):
    if not isinstance(contributors, list) or not contributors:
        fail("publication metadata needs at least one contributor")
    identifiers = set()
    author_count = 0
    for contributor in contributors:
        fields = {"id", "display_name", "sort_name", "roles", "affiliation", "orcid"}
        exact_object(contributor, fields, "contributor metadata")
        identifier = contributor["id"]
        if not isinstance(identifier, str) or not ID.fullmatch(identifier) or identifier in identifiers:
            fail("contributor ids must be unique lowercase kebab-case identifiers")
        identifiers.add(identifier)
        required_text(contributor["display_name"], "contributor display name")
        required_text(contributor["sort_name"], "contributor sort name")
        roles = contributor["roles"]
        if not isinstance(roles, list) or not roles or any(role not in CONTRIBUTOR_ROLES for role in roles):
            fail(f"contributor {identifier} has missing or unsupported roles")
        if len(roles) != len(set(roles)):
            fail(f"contributor {identifier} roles must be unique")
        author_count += int("author" in roles)
        nullable_text(contributor["affiliation"], "contributor affiliation")
        validate_orcid(contributor["orcid"], f"contributor {identifier} ORCID")
    if author_count == 0:
        fail("publication metadata needs at least one contributor with the author role")


def validate_organization(organization, label):
    exact_object(organization, {"name", "place", "website"}, label)
    nullable_text(organization["name"], f"{label} name")
    nullable_text(organization["place"], f"{label} place")
    web_url(organization["website"], f"{label} website")


def validate_publication(publication, work_status):
    exact_object(publication, {"publisher", "imprint"}, "publication organization metadata")
    validate_organization(publication["publisher"], "publisher")
    validate_organization(publication["imprint"], "imprint")
    publisher = publication["publisher"]
    imprint = publication["imprint"]
    if imprint["name"] is not None and publisher["name"] is None:
        fail("an imprint requires a named publisher")
    if work_status in {"forthcoming", "published"} and publisher["name"] is None:
        fail(f"{work_status} work needs a named publisher")


def validate_rights(rights, work):
    exact_object(rights, {"copyright", "statement", "licenses"}, "rights metadata")
    copyright_data = exact_object(rights["copyright"], {"year", "holders"}, "copyright metadata")
    year = copyright_data["year"]
    if year is not None and (
        not isinstance(year, int) or isinstance(year, bool) or not 1000 <= year <= 9999
    ):
        fail("copyright year must be a four-digit integer or null")
    unique_text_list(copyright_data["holders"], "copyright holders")
    required_text(rights["statement"], "rights statement", 20)
    if work["status"] == "published" and year is None:
        fail("published work needs a copyright year")

    licenses = rights["licenses"]
    if not isinstance(licenses, list) or not licenses:
        fail("rights metadata needs at least one license scope")
    scopes = set()
    for license_record in licenses:
        fields = {"scope", "status", "expression", "url", "policy"}
        exact_object(license_record, fields, "license metadata")
        scope = required_text(license_record["scope"], "license scope")
        if scope.casefold() in scopes:
            fail("license scopes must be unique")
        scopes.add(scope.casefold())
        status = license_record["status"]
        if status not in LICENSE_STATUSES:
            fail(f"license scope {scope} has an unsupported status")
        expression = nullable_text(license_record["expression"], "license expression")
        policy = nullable_text(license_record["policy"], "license policy")
        web_url(license_record["url"], "license URL")
        if status == "undecided" and any((expression, license_record["url"], policy)):
            fail(f"undecided license scope {scope} cannot declare license details")
        if status == "selected" and expression is None:
            fail(f"selected license scope {scope} needs an SPDX expression")
        if status == "governed-separately" and policy is None:
            fail(f"separately governed license scope {scope} needs a policy path")


def validate_accessibility(accessibility):
    exact_object(accessibility, {"features", "hazards", "summary", "review"}, "accessibility metadata")
    unique_text_list(accessibility["features"], "accessibility features")
    hazards = unique_text_list(accessibility["hazards"], "accessibility hazards")
    if "none" in hazards and len(hazards) != 1:
        fail("accessibility hazard 'none' cannot be combined with other hazards")
    required_text(accessibility["summary"], "accessibility summary", 40)
    review = exact_object(accessibility["review"], {"standard", "status"}, "accessibility review")
    required_text(review["standard"], "accessibility review standard")
    if review["status"] not in REVIEW_STATUSES:
        fail("accessibility review status is unsupported")


def safe_policy_path(root, value, label):
    relative = Path(value) if isinstance(value, str) else Path("/")
    if relative.is_absolute() or ".." in relative.parts or relative.suffix not in {".json", ".yml"}:
        fail(f"{label} must be a safe repository policy path")
    path = root / relative
    if not path.is_file():
        fail(f"{label} does not exist: {value}")
    return path


def validate_provenance(root, provenance):
    fields = {"source_statement", "reproducibility_statement", "repository", "policies"}
    exact_object(provenance, fields, "provenance metadata")
    required_text(provenance["source_statement"], "source statement", 40)
    required_text(provenance["reproducibility_statement"], "reproducibility statement", 40)
    repository = exact_object(provenance["repository"], {"visibility", "url"}, "source repository")
    if repository["visibility"] not in VISIBILITIES:
        fail("source repository visibility is unsupported")
    web_url(repository["url"], "source repository URL", required=repository["visibility"] == "public")
    policies = exact_object(provenance["policies"], {"reproducibility", "rights", "accessibility"}, "provenance policies")
    return {
        name: safe_policy_path(root, path, f"{name} policy")
        for name, path in policies.items()
    }


def validate_record(root, record):
    exact_object(record, TOP_LEVEL, "publication metadata")
    if record["schema_version"] != 1:
        fail("publication metadata schema_version must be 1")
    validate_work(record["work"])
    validate_contributors(record["contributors"])
    validate_publication(record["publication"], record["work"]["status"])
    validate_rights(record["rights"], record["work"])
    validate_accessibility(record["accessibility"])
    policies = validate_provenance(root, record["provenance"])
    return policies


def validate_repository(root, record, policies):
    root = Path(root)
    quarto = (root / "book/_quarto.yml").read_text(encoding="utf-8")
    work = record["work"]
    if "metadata-files:" not in quarto or not re.search(
        r"^\s+- generated/metadata\.yml\s*$", quarto, re.M
    ):
        fail("Quarto does not include the generated canonical metadata adapter")
    forbidden = (
        r"^\s{2}(?:title|subtitle|author):",
        r"^(?:title|subtitle|author|lang):",
        r"^\s{2}(?:edition|publisher|copyright-year|copyright-holder|rights-statement|identifier):",
    )
    if any(re.search(pattern, quarto, re.M) for pattern in forbidden):
        fail("Quarto config duplicates a generated publication metadata field")
    from .metadata_generation import quarto_metadata

    generated = root / "book/generated/metadata.yml"
    if not generated.is_file() or generated.read_bytes() != quarto_metadata(record):
        fail("generated Quarto metadata drifted from book/publication.json")
    expected_author = ", ".join(
        contributor["display_name"]
        for contributor in record["contributors"]
        if "author" in contributor["roles"]
    )

    epub = load_json(policies["accessibility"], "accessibility policy")
    accessibility = record["accessibility"]
    if epub.get("language") != work["language"]["primary"]:
        fail("EPUB accessibility language drifted from canonical metadata")
    discovery = epub.get("discovery", {})
    expected_discovery = {
        "accessibility_features": accessibility["features"],
        "accessibility_hazards": accessibility["hazards"],
        "accessibility_summary": accessibility["summary"],
    }
    for key, expected in expected_discovery.items():
        if discovery.get(key) != expected:
            fail(f"EPUB {key} drifted from canonical metadata")
    review = accessibility["review"]
    if epub.get("standard") != review["standard"] or epub.get("claim_status") != review["status"]:
        fail("EPUB accessibility review metadata drifted from canonical metadata")

    assets = load_json(policies["rights"], "asset-rights policy")
    contract = assets.get("artifact_contract", {})
    if contract.get("expected_pdf_title") != work["title"]:
        fail("PDF title expectation drifted from canonical metadata")
    if contract.get("expected_pdf_author") != expected_author:
        fail("PDF author expectation drifted from canonical metadata")
    if contract.get("expected_pdf_subject") != work["descriptions"]["long"]:
        fail("PDF subject expectation drifted from canonical metadata")
    if contract.get("expected_pdf_keywords") != ", ".join(work["keywords"]):
        fail("PDF keywords expectation drifted from canonical metadata")
    load_json(policies["reproducibility"], "reproducibility policy")

    integration = {
        "makefile": root / "Makefile",
        "dispatcher": root / "scripts/check-source.py",
        "documentation": root / "docs/publication-metadata.md",
    }
    texts = {name: path.read_text(encoding="utf-8") for name, path in integration.items()}
    for marker in ("check-publication-metadata:", "test-publication-metadata:"):
        if marker not in texts["makefile"]:
            fail(f"Makefile is missing publication metadata target {marker}")
    if '"publication-metadata", "check-publication-metadata.py"' not in texts["dispatcher"]:
        fail("source dispatcher does not include publication metadata")
    for marker in (
        "book/publication.json",
        "config/metadata/publication.schema.json",
        "work-level",
        "manifestation",
    ):
        if marker not in texts["documentation"]:
            fail(f"publication metadata documentation is missing {marker!r}")


def load_and_validate(root):
    root = Path(root)
    schema = load_json(root / "config/metadata/publication.schema.json", "publication metadata schema")
    record = load_json(root / "book/publication.json", "publication metadata")
    validate_schema(schema)
    policies = validate_record(root, record)
    validate_repository(root, record, policies)
    return record


__all__ = [
    "ContractError",
    "load_and_validate",
    "validate_record",
    "validate_repository",
    "validate_schema",
]
