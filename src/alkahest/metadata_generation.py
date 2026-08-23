"""Generate and validate publication metadata adapters from canonical records."""

from __future__ import annotations

import json
import re
import xml.etree.ElementTree as ET
from pathlib import Path

from .common import ContractError, fail, load_json


EXPECTED_SOURCES = {
    "publication": "book/publication.json",
    "manifestations": "book/manifestations.json",
    "reproducibility": "book/reproducibility.json",
}
EXPECTED_OUTPUTS = {
    "quarto": "book/generated/metadata.yml",
    "release_manifest": "book/generated/release-manifest.json",
    "onix_status": "book/generated/onix-status.json",
    "onix": "book/generated/onix.xml",
}
EXPECTED_CODES = {
    "identifier_schemes": {
        "isbn-10": (5, "02"),
        "isbn-13": (5, "15"),
        "doi": (5, "06"),
    },
    "contributor_roles": {
        "author": (17, "A01"),
        "editor": (17, "B01"),
        "translator": (17, "B06"),
        "illustrator": (17, "A12"),
        "photographer": (17, "A13"),
        "technical-reviewer": (17, "B26"),
        "foreword-author": (17, "A23"),
        "introduction-author": (17, "A24"),
        "compiler": (17, "C01"),
        "designer": (17, "A11"),
    },
    "languages": {"en-US": (74, "eng"), "fr-FR": (74, "fre")},
    "publishing_statuses": {
        "forthcoming": (64, "02"),
        "published": (64, "04"),
        "withdrawn": (64, "08"),
    },
    "audiences": {
        "technical-authors": (28, "06"),
        "self-publishers": (28, "06"),
    },
    "fixed_codes": {
        "notification_forthcoming": (1, "02"),
        "notification_confirmed": (1, "03"),
        "product_composition": (2, "00"),
        "title_type": (15, "01"),
        "title_element_level": (149, "01"),
        "language_role": (22, "01"),
        "keywords_scheme": (27, "20"),
        "audience_code_type": (28, "01"),
        "publisher_role": (45, "01"),
        "short_description": (153, "02"),
        "long_description": (153, "03"),
        "content_audience": (154, "00"),
        "publication_date": (163, "01"),
    },
}
EXPECTED_FORMS = {
    "epub": ((150, "EA"), (175, "E101")),
    "pdf": ((150, "EA"), (175, "E107")),
    "print": ((150, "BA"), None),
}


def json_text(value):
    return json.dumps(value, ensure_ascii=False)


def json_bytes(value):
    return (json.dumps(value, ensure_ascii=False, indent=2) + "\n").encode("utf-8")


def validate_safe_path(value, label):
    path = Path(value) if isinstance(value, str) else Path("/")
    if path.is_absolute() or ".." in path.parts or not path.parts:
        fail(f"{label} must be a safe repository-relative path")
    return value


def code_pair(value, label):
    if not isinstance(value, dict) or set(value) - {"list", "code", "label", "deprecated", "notification"}:
        fail(f"ONIX {label} mapping has unsupported fields")
    if not isinstance(value.get("list"), int) or not isinstance(value.get("code"), str):
        fail(f"ONIX {label} mapping needs a code-list number and code")
    if not isinstance(value.get("label"), str) or not value["label"]:
        fail(f"ONIX {label} mapping needs a readable label")
    return value["list"], value["code"]


def validate_policy(policy):
    if not isinstance(policy, dict) or set(policy) != {"schema_version", "sources", "outputs", "onix"}:
        fail("metadata generation policy fields do not match version 1")
    if policy["schema_version"] != 1:
        fail("metadata generation policy must use schema_version 1")
    if policy["sources"] != EXPECTED_SOURCES or policy["outputs"] != EXPECTED_OUTPUTS:
        fail("metadata generation source or output paths drifted")
    for label, value in policy["sources"].items():
        validate_safe_path(value, f"{label} source")
    for label, value in policy["outputs"].items():
        validate_safe_path(value, f"{label} output")

    onix = policy["onix"]
    expected_fields = {
        "release", "code_list_issue", "reviewed", "namespace", "reference",
        "eligible_formats", "eligible_statuses", "identifier_schemes",
        "contributor_roles", "languages", "product_forms",
        "publishing_statuses", "audiences", "fixed_codes",
    }
    if not isinstance(onix, dict) or set(onix) != expected_fields:
        fail("ONIX policy fields drifted")
    if onix["release"] != "3.1" or onix["code_list_issue"] != 74:
        fail("ONIX release and code lists must remain pinned to 3.1 issue 74")
    if onix["namespace"] != "http://ns.editeur.org/onix/3.0/reference":
        fail("ONIX reference namespace drifted")
    if onix["reference"] != "https://ns.editeur.org/onix/en":
        fail("ONIX official code-list reference drifted")
    if onix["eligible_formats"] != ["epub", "pdf", "print"]:
        fail("ONIX eligible format policy drifted")
    if onix["eligible_statuses"] != ["forthcoming", "published", "withdrawn"]:
        fail("ONIX eligible lifecycle policy drifted")
    if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", onix["reviewed"]):
        fail("ONIX policy review date must use YYYY-MM-DD")

    for group, expected in EXPECTED_CODES.items():
        actual = onix[group]
        if not isinstance(actual, dict) or set(actual) != set(expected):
            fail(f"ONIX {group.replace('_', ' ')} coverage drifted")
        for name, pair in expected.items():
            if code_pair(actual[name], f"{group}.{name}") != pair:
                fail(f"ONIX {group}.{name} mapping drifted")
    if onix["identifier_schemes"]["isbn-10"].get("deprecated") is not True:
        fail("ONIX ISBN-10 mapping must remain explicitly deprecated")
    if any(
        onix["identifier_schemes"][name].get("deprecated") is not False
        for name in ("isbn-13", "doi")
    ):
        fail("current ONIX identifier mappings cannot be marked deprecated")
    forms = onix["product_forms"]
    if not isinstance(forms, dict) or set(forms) != set(EXPECTED_FORMS):
        fail("ONIX product-form coverage drifted")
    for name, (expected_form, expected_detail) in EXPECTED_FORMS.items():
        item = forms[name]
        if not isinstance(item, dict) or set(item) != {"form", "detail"}:
            fail(f"ONIX {name} product-form fields drifted")
        if code_pair(item["form"], f"product_forms.{name}.form") != expected_form:
            fail(f"ONIX {name} product-form mapping drifted")
        detail = item["detail"]
        if expected_detail is None:
            if detail is not None:
                fail(f"ONIX {name} product-form detail must be null")
        elif code_pair(detail, f"product_forms.{name}.detail") != expected_detail:
            fail(f"ONIX {name} product-form detail mapping drifted")
    return policy


def authors(publication):
    return [
        contributor["display_name"]
        for contributor in publication["contributors"]
        if "author" in contributor["roles"]
    ]


def quarto_metadata(publication):
    work = publication["work"]
    author_names = authors(publication)
    copyright_data = publication["rights"]["copyright"]
    publisher = publication["publication"]["publisher"]["name"] or "[Publisher name]"
    year = copyright_data["year"] or "[Publication year]"
    holder = ", ".join(copyright_data["holders"])
    lines = [
        "# Generated by alkahest generate publication-metadata; do not edit.",
        "book:",
        f"  title: {json_text(work['title'])}",
    ]
    if work["subtitle"] is not None:
        lines.append(f"  subtitle: {json_text(work['subtitle'])}")
    lines.extend(("  author:", *(f"    - name: {json_text(name)}" for name in author_names)))
    lines.extend(
        (
            f"  description: {json_text(work['descriptions']['long'])}",
            f"title: {json_text(work['title'])}",
        )
    )
    if work["subtitle"] is not None:
        lines.append(f"subtitle: {json_text(work['subtitle'])}")
    lines.extend(("author:", *(f"  - name: {json_text(name)}" for name in author_names)))
    lines.extend(
        (
            f"lang: {work['language']['primary']}",
            f"description: {json_text(work['descriptions']['long'])}",
            f"subject: {json_text('; '.join(subject['label'] for subject in work['subjects']))}",
            "keywords:",
            *(f"  - {json_text(keyword)}" for keyword in work["keywords"]),
            "alkahest:",
            f"  work-id: {json_text(work['id'])}",
            f"  publication-status: {json_text(work['status'])}",
            f"  edition: {json_text(work['edition']['statement'])}",
            f"  publisher: {json_text(publisher)}",
            f"  copyright-year: {json_text(str(year))}",
            f"  copyright-holder: {json_text(holder)}",
            f"  rights-statement: {json_text(publication['rights']['statement'])}",
            f"  identifier: {json_text('No retail publication identifier assigned')}",
            "",
        )
    )
    return "\n".join(lines).encode("utf-8")


def release_blockers(publication, manifestations):
    blockers = []
    work = publication["work"]
    if work["status"] not in {"forthcoming", "published"}:
        blockers.append("work lifecycle is not forthcoming or published")
    if publication["publication"]["publisher"]["name"] is None:
        blockers.append("publisher name is unassigned")
    if work["dates"]["publication"] is None:
        blockers.append("publication date is unassigned")
    text_license = next(
        (item for item in publication["rights"]["licenses"] if item["scope"] == "Publication text"),
        None,
    )
    if text_license is None or text_license["status"] != "selected":
        blockers.append("publication-text license is not selected")
    if not any(item["status"] in {"forthcoming", "published"} for item in manifestations["manifestations"]):
        blockers.append("no manifestation is forthcoming or published")
    return blockers


def release_manifest(publication, manifestations, reproducibility, policy):
    blockers = release_blockers(publication, manifestations)
    return {
        "schema_version": 1,
        "generated_from": policy["sources"],
        "source_date_utc": reproducibility["source_date_utc"],
        "onix": {
            "release": policy["onix"]["release"],
            "code_list_issue": policy["onix"]["code_list_issue"],
        },
        "release_ready": not blockers,
        "release_blockers": blockers,
        "work": publication["work"],
        "contributors": publication["contributors"],
        "publication": publication["publication"],
        "rights": publication["rights"],
        "accessibility": publication["accessibility"],
        "provenance": publication["provenance"],
        "manifestations": manifestations["manifestations"],
    }


def onix_blockers(publication, manifestation, policy):
    blockers = []
    onix = policy["onix"]
    if manifestation["format"] not in onix["eligible_formats"]:
        blockers.append("format is not an ONIX retail product")
    if manifestation["status"] not in onix["eligible_statuses"]:
        blockers.append("lifecycle is not ONIX-exportable")
    schemes = {item["scheme"] for item in manifestation["identifiers"]}
    if not schemes.intersection({"isbn-13", "doi"}):
        blockers.append("ISBN-13 or DOI is unassigned")
    if publication["publication"]["publisher"]["name"] is None:
        blockers.append("publisher name is unassigned")
    if manifestation["dates"]["publication"] is None:
        blockers.append("manifestation publication date is unassigned")
    if manifestation["language"] not in onix["languages"]:
        blockers.append("language has no pinned ONIX mapping")
    for contributor in publication["contributors"]:
        for role in contributor["roles"]:
            if role not in onix["contributor_roles"]:
                blockers.append(f"contributor role {role!r} has no pinned ONIX mapping")
    for audience in publication["work"]["audiences"]:
        if audience["code"] not in onix["audiences"]:
            blockers.append(f"audience {audience['code']!r} has no pinned ONIX mapping")
    return blockers


def eligible_manifestations(publication, manifestations, policy):
    eligible = []
    blocked = {}
    for manifestation in manifestations["manifestations"]:
        reasons = onix_blockers(publication, manifestation, policy)
        if reasons:
            blocked[manifestation["id"]] = reasons
        else:
            eligible.append(manifestation)
    return eligible, blocked


def add(parent, name, text=None):
    element = ET.SubElement(parent, name)
    if text is not None:
        element.text = str(text)
    return element


def onix_xml(publication, eligible, reproducibility, policy):
    onix = policy["onix"]
    ET.register_namespace("", onix["namespace"])
    root = ET.Element(f"{{{onix['namespace']}}}ONIXMessage", {"release": onix["release"]})
    header = add(root, "Header")
    sender = add(header, "Sender")
    add(sender, "SenderName", "Alkahest metadata generator")
    stamp = reproducibility["source_date_utc"].replace("-", "").replace(":", "")
    add(header, "SentDateTime", stamp[:-1])
    work = publication["work"]
    fixed = onix["fixed_codes"]
    for manifestation in eligible:
        product = add(root, "Product")
        add(product, "RecordReference", f"{work['id']}:{manifestation['id']}")
        status_mapping = onix["publishing_statuses"][manifestation["status"]]
        notification = (
            fixed["notification_forthcoming"]
            if manifestation["status"] == "forthcoming"
            else fixed["notification_confirmed"]
        )
        add(product, "NotificationType", notification["code"])
        for identifier in manifestation["identifiers"]:
            mapping = onix["identifier_schemes"].get(identifier["scheme"])
            if mapping is None:
                continue
            composite = add(product, "ProductIdentifier")
            add(composite, "ProductIDType", mapping["code"])
            add(composite, "IDValue", identifier["value"])
        detail = add(product, "DescriptiveDetail")
        add(detail, "ProductComposition", fixed["product_composition"]["code"])
        form = onix["product_forms"][manifestation["format"]]
        add(detail, "ProductForm", form["form"]["code"])
        if form["detail"] is not None:
            add(detail, "ProductFormDetail", form["detail"]["code"])
        title_detail = add(detail, "TitleDetail")
        add(title_detail, "TitleType", fixed["title_type"]["code"])
        title_element = add(title_detail, "TitleElement")
        add(title_element, "TitleElementLevel", fixed["title_element_level"]["code"])
        add(title_element, "TitleText", work["title"])
        if work["subtitle"]:
            add(title_element, "Subtitle", work["subtitle"])
        for sequence, contributor in enumerate(publication["contributors"], start=1):
            composite = add(detail, "Contributor")
            add(composite, "SequenceNumber", sequence)
            for role in contributor["roles"]:
                add(composite, "ContributorRole", onix["contributor_roles"][role]["code"])
            add(composite, "PersonName", contributor["display_name"])
            add(composite, "PersonNameInverted", contributor["sort_name"])
        language = add(detail, "Language")
        add(language, "LanguageRole", fixed["language_role"]["code"])
        add(language, "LanguageCode", onix["languages"][manifestation["language"]]["code"])
        subject = add(detail, "Subject")
        add(subject, "SubjectSchemeIdentifier", fixed["keywords_scheme"]["code"])
        add(subject, "SubjectHeadingText", "; ".join(work["keywords"]))
        audience_codes = []
        for audience in work["audiences"]:
            audience_code = onix["audiences"][audience["code"]]["code"]
            if audience_code in audience_codes:
                continue
            audience_codes.append(audience_code)
            composite = add(detail, "Audience")
            add(composite, "AudienceCodeType", fixed["audience_code_type"]["code"])
            add(composite, "AudienceCodeValue", audience_code)
        collateral = add(product, "CollateralDetail")
        for name, key in (("short_description", "short"), ("long_description", "long")):
            text_content = add(collateral, "TextContent")
            add(text_content, "TextType", fixed[name]["code"])
            add(text_content, "ContentAudience", fixed["content_audience"]["code"])
            add(text_content, "Text", work["descriptions"][key])
        publishing = add(product, "PublishingDetail")
        publisher = add(publishing, "Publisher")
        add(publisher, "PublishingRole", fixed["publisher_role"]["code"])
        add(publisher, "PublisherName", publication["publication"]["publisher"]["name"])
        add(publishing, "PublishingStatus", status_mapping["code"])
        publication_date = add(publishing, "PublishingDate")
        add(publication_date, "PublishingDateRole", fixed["publication_date"]["code"])
        add(publication_date, "Date", manifestation["dates"]["publication"].replace("-", ""))
    ET.indent(root, space="  ")
    return ET.tostring(root, encoding="utf-8", xml_declaration=True) + b"\n"


def output_bundle(publication, manifestations, reproducibility, policy):
    eligible, blocked = eligible_manifestations(publication, manifestations, policy)
    status = {
        "schema_version": 1,
        "generated": bool(eligible),
        "release": policy["onix"]["release"],
        "code_list_issue": policy["onix"]["code_list_issue"],
        "output": policy["outputs"]["onix"] if eligible else None,
        "eligible_manifestations": [item["id"] for item in eligible],
        "blocked_manifestations": blocked,
    }
    outputs = {
        policy["outputs"]["quarto"]: quarto_metadata(publication),
        policy["outputs"]["release_manifest"]: json_bytes(
            release_manifest(publication, manifestations, reproducibility, policy)
        ),
        policy["outputs"]["onix_status"]: json_bytes(status),
    }
    if eligible:
        outputs[policy["outputs"]["onix"]] = onix_xml(
            publication, eligible, reproducibility, policy
        )
    return outputs, status


def load_inputs(root):
    root = Path(root)
    policy = validate_policy(load_json(root / "config/metadata/generation.json", "metadata generation policy"))
    publication = load_json(root / policy["sources"]["publication"], "publication metadata")
    manifestations = load_json(root / policy["sources"]["manifestations"], "manifestation metadata")
    reproducibility = load_json(root / policy["sources"]["reproducibility"], "reproducibility metadata")
    from .manifestations import validate_record as validate_manifestations
    from .publication_metadata import validate_record as validate_publication

    validate_publication(root, publication)
    validate_manifestations(root, manifestations)
    if not isinstance(reproducibility.get("source_date_utc"), str) or not re.fullmatch(
        r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z", reproducibility["source_date_utc"]
    ):
        fail("reproducibility source_date_utc cannot feed deterministic metadata")
    return publication, manifestations, reproducibility, policy


def generate(root, require_onix=False):
    root = Path(root)
    publication, manifestations, reproducibility, policy = load_inputs(root)
    outputs, status = output_bundle(publication, manifestations, reproducibility, policy)
    if require_onix and not status["generated"]:
        fail("ONIX export was required but no manifestation is eligible")
    for relative, content in outputs.items():
        path = root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(content)
    onix_path = root / policy["outputs"]["onix"]
    if not status["generated"] and onix_path.exists():
        onix_path.unlink()
    return status


def check_generated(root):
    root = Path(root)
    publication, manifestations, reproducibility, policy = load_inputs(root)
    outputs, status = output_bundle(publication, manifestations, reproducibility, policy)
    for relative, expected in outputs.items():
        path = root / relative
        if not path.is_file():
            fail(f"generated metadata output is missing: {relative}")
        if path.read_bytes() != expected:
            fail(f"generated metadata output is stale: {relative}")
    onix_path = root / policy["outputs"]["onix"]
    if not status["generated"] and onix_path.exists():
        fail("stale ONIX XML exists although no manifestation is eligible")
    return status


def validate_repository(root):
    root = Path(root)
    policy = validate_policy(
        load_json(root / "config/metadata/generation.json", "metadata generation policy")
    )
    paths = {
        "quarto": root / "book/_quarto.yml",
        "makefile": root / "Makefile",
        "tasks": root / "src/alkahest/tasks.py",
        "documentation": root / "docs/metadata-generation.md",
    }
    texts = {name: path.read_text(encoding="utf-8") for name, path in paths.items()}
    if "metadata-files:" not in texts["quarto"] or not re.search(
        r"^\s+- generated/metadata\.yml\s*$", texts["quarto"], re.M
    ):
        fail("Quarto does not consume the generated metadata adapter")
    for marker in (
        "generate-%:",
        "check-%:",
        "test-%:",
    ):
        if marker not in texts["makefile"]:
            fail(f"Makefile is missing metadata generation target {marker}")
    for marker in (
        '"metadata-generation", ":check-metadata-generation"',
        '"metadata-generation", "test-metadata-generation.py"',
        '"publication-metadata",',
        '":generate-publication-metadata"',
    ):
        if marker not in texts["tasks"]:
            fail(f"task registry does not include metadata generation entry {marker}")
    for marker in (
        policy["outputs"]["quarto"],
        policy["outputs"]["release_manifest"],
        policy["outputs"]["onix_status"],
        "code-list issue 74",
        "--require-onix",
    ):
        if marker not in texts["documentation"]:
            fail(f"metadata generation documentation is missing {marker!r}")


__all__ = [
    "ContractError", "check_generated", "eligible_manifestations", "generate",
    "load_inputs", "onix_xml", "output_bundle", "quarto_metadata",
    "release_manifest", "validate_policy", "validate_repository",
]
