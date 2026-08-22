"""Exercise deterministic adapters, drift detection, and ONIX eligibility."""

import copy
import json
import tempfile
import xml.etree.ElementTree as ET
from pathlib import Path

from lib.alkahest.metadata_generation import (
    ContractError,
    check_generated,
    generate,
    load_inputs,
    output_bundle,
    validate_policy,
)


ROOT = Path(__file__).resolve().parent.parent


def changed(value, mutate):
    result = copy.deepcopy(value)
    mutate(result)
    return result


def expect_failure(name, message, operation):
    try:
        operation()
    except ContractError as error:
        if message not in str(error):
            raise RuntimeError(
                f"metadata-generation fixture {name!r} missed {message!r}: {error}"
            )
        return
    raise RuntimeError(f"invalid metadata-generation fixture passed: {name}")


def manifestation(registry, identifier):
    return next(item for item in registry["manifestations"] if item["id"] == identifier)


def write_fixture(root, publication, manifestations, reproducibility, policy):
    values = {
        "book/publication.json": publication,
        "book/manifestations.json": manifestations,
        "book/reproducibility.json": reproducibility,
        "config/metadata/generation.json": policy,
    }
    for relative, value in values.items():
        path = root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8")
    for relative in ("book/assets.json", "book/epub-accessibility.json"):
        (root / relative).write_text("{}\n", encoding="utf-8")


def retail_fixture(publication, manifestations):
    publication = copy.deepcopy(publication)
    manifestations = copy.deepcopy(manifestations)
    publication["work"]["status"] = "forthcoming"
    publication["work"]["dates"]["publication"] = "2027-01-15"
    publication["publication"]["publisher"]["name"] = "Fixture Press"
    text_license = next(
        item for item in publication["rights"]["licenses"]
        if item["scope"] == "Publication text"
    )
    text_license.update(
        {"status": "selected", "expression": "All rights reserved", "url": None, "policy": None}
    )
    epub = manifestation(manifestations, "epub-full-en")
    epub["status"] = "forthcoming"
    epub["identifiers"].append({"scheme": "isbn-13", "value": "9780306406157"})
    epub["dates"]["announcement"] = "2026-12-01"
    epub["dates"]["publication"] = "2027-01-15"
    epub["availability"] = {
        "status": "preorder", "territories": ["WORLD"], "channels": ["Fixture store"]
    }
    return publication, manifestations


def main():
    publication, manifestations, reproducibility, policy = load_inputs(ROOT)
    validate_policy(copy.deepcopy(policy))
    outputs, status = output_bundle(publication, manifestations, reproducibility, policy)
    assert status["generated"] is False
    assert policy["outputs"]["onix"] not in outputs
    assert output_bundle(publication, manifestations, reproducibility, policy)[0] == outputs

    expect_failure(
        "code-list-drift",
        "author mapping drifted",
        lambda: validate_policy(
            changed(
                policy,
                lambda value: value["onix"]["contributor_roles"]["author"].update(
                    {"code": "A02"}
                ),
            )
        ),
    )
    expect_failure(
        "code-list-issue-drift",
        "must remain pinned",
        lambda: validate_policy(
            changed(policy, lambda value: value["onix"].update({"code_list_issue": 75}))
        ),
    )

    retail_publication, retail_manifestations = retail_fixture(publication, manifestations)
    retail_outputs, retail_status = output_bundle(
        retail_publication, retail_manifestations, reproducibility, policy
    )
    assert retail_status["eligible_manifestations"] == ["epub-full-en"]
    xml = retail_outputs[policy["outputs"]["onix"]]
    document = ET.fromstring(xml)
    namespace = {"o": policy["onix"]["namespace"]}
    product = document.find("o:Product", namespace)
    assert product is not None
    expected = {
        "o:NotificationType": "02",
        "o:ProductIdentifier/o:ProductIDType": "15",
        "o:DescriptiveDetail/o:ProductForm": "EA",
        "o:DescriptiveDetail/o:ProductFormDetail": "E101",
        "o:DescriptiveDetail/o:Contributor/o:ContributorRole": "A01",
        "o:DescriptiveDetail/o:Language/o:LanguageCode": "eng",
        "o:PublishingDetail/o:PublishingStatus": "02",
        "o:PublishingDetail/o:PublishingDate/o:Date": "20270115",
    }
    for path, value in expected.items():
        assert product.findtext(path, namespaces=namespace) == value, path

    isbn10_only = copy.deepcopy(retail_manifestations)
    epub = manifestation(isbn10_only, "epub-full-en")
    epub["identifiers"] = [
        item for item in epub["identifiers"] if item["scheme"] != "isbn-13"
    ] + [{"scheme": "isbn-10", "value": "0306406152"}]
    _, isbn10_status = output_bundle(
        retail_publication, isbn10_only, reproducibility, policy
    )
    assert isbn10_status["generated"] is False
    assert "ISBN-13 or DOI is unassigned" in isbn10_status["blocked_manifestations"]["epub-full-en"]

    with tempfile.TemporaryDirectory(prefix="alkahest-metadata-generation.") as directory:
        root = Path(directory)
        write_fixture(root, publication, manifestations, reproducibility, policy)
        generate(root)
        check_generated(root)
        (root / policy["outputs"]["quarto"]).write_text("stale\n", encoding="utf-8")
        expect_failure("stale-output", "is stale", lambda: check_generated(root))
        generate(root)
        stale_onix = root / policy["outputs"]["onix"]
        stale_onix.write_text("<stale/>\n", encoding="utf-8")
        expect_failure("stale-onix", "stale ONIX XML", lambda: check_generated(root))
        stale_onix.unlink()
        expect_failure(
            "required-onix",
            "ONIX export was required",
            lambda: generate(root, require_onix=True),
        )

    print("ok: metadata generation fixtures (determinism, drift, eligibility, and ONIX mappings)")


if __name__ == "__main__":
    main()
