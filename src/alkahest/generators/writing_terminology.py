"""Validate terminology sources and generate CSpell and Vale derivatives."""

import argparse
import json
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
REGISTRY = ROOT / "config/writing/terminology.json"
CSPELL_OUTPUT = ROOT / "config/writing/cspell-terms.json"
VALID_CATEGORIES = {
    "capitalization",
    "deprecated",
    "house-style",
    "misspelling",
    "technical",
}
VALID_CHECKS = {"cspell", "vale"}


def fail(message):
    raise SystemExit(f"error: {message}")


def load_registry():
    try:
        data = json.loads(REGISTRY.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        fail(f"cannot load {REGISTRY.relative_to(ROOT)}: {error}")
    if set(data) != {"version", "scopes", "dictionaries", "rejected_terms"}:
        fail("terminology registry has unsupported top-level fields")
    if data["version"] != 1:
        fail("terminology registry version must be 1")
    return data


def safe_relative_path(value, label):
    path = Path(value)
    if path.is_absolute() or ".." in path.parts:
        fail(f"{label} must be a repository-relative path without '..'")
    return path


def read_dictionary(relative):
    path = ROOT / relative
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except OSError as error:
        fail(f"cannot read {relative}: {error}")
    words = [line.strip() for line in lines if line.strip() and not line.lstrip().startswith("#")]
    if not words:
        fail(f"accepted dictionary is empty: {relative}")
    if any(any(character.isspace() for character in word) for word in words):
        fail(f"accepted dictionary entries must be single tokens: {relative}")
    expected = sorted(words, key=lambda word: (word.casefold(), word))
    if words != expected:
        fail(f"accepted dictionary must be case-insensitively sorted: {relative}")
    folded = [word.casefold() for word in words]
    if len(folded) != len(set(folded)):
        fail(f"accepted dictionary contains case-insensitive duplicates: {relative}")
    return words


def validate(data):
    scopes = {}
    for scope in data["scopes"]:
        required = {"id", "description", "files", "vale_style"}
        if not isinstance(scope, dict) or set(scope) != required:
            fail("terminology scope fields do not match the version 1 contract")
        identifier = scope["id"]
        if not isinstance(identifier, str) or not identifier or identifier in scopes:
            fail(f"invalid or duplicate terminology scope: {identifier!r}")
        if identifier == "shared" and scope["files"] is not None:
            fail("shared terminology scope must apply globally")
        if identifier != "shared" and not isinstance(scope["files"], str):
            fail(f"book terminology scope needs a file glob: {identifier}")
        if not isinstance(scope["description"], str) or len(scope["description"].split()) < 5:
            fail(f"terminology scope needs a substantive description: {identifier}")
        if not isinstance(scope["vale_style"], str) or not scope["vale_style"].isalnum():
            fail(f"terminology scope has an invalid Vale style name: {identifier}")
        scopes[identifier] = scope
    if "shared" not in scopes:
        fail("terminology registry needs a shared scope")

    dictionaries = []
    names = set()
    accepted = {}
    accepted_owners = {}
    for dictionary in data["dictionaries"]:
        required = {"name", "scope", "path", "description", "add_words"}
        if not isinstance(dictionary, dict) or set(dictionary) != required:
            fail("accepted-dictionary fields do not match the version 1 contract")
        name = dictionary["name"]
        if not isinstance(name, str) or not name or name in names:
            fail(f"invalid or duplicate accepted dictionary: {name!r}")
        if dictionary["scope"] not in scopes:
            fail(f"accepted dictionary uses an unknown scope: {name}")
        relative = safe_relative_path(dictionary["path"], f"dictionary {name}")
        if relative.suffix != ".txt":
            fail(f"accepted dictionary must be a .txt word list: {name}")
        if not isinstance(dictionary["add_words"], bool):
            fail(f"accepted dictionary add_words must be boolean: {name}")
        if (
            not isinstance(dictionary["description"], str)
            or len(dictionary["description"].split()) < 4
        ):
            fail(f"accepted dictionary needs a substantive description: {name}")
        words = read_dictionary(relative.as_posix())
        for word in words:
            if word in accepted_owners:
                fail(
                    f"accepted term appears in both {accepted_owners[word]} "
                    f"and {dictionary['scope']}: {word}"
                )
            accepted_owners[word] = dictionary["scope"]
        accepted.setdefault(dictionary["scope"], set()).update(words)
        dictionaries.append(dictionary)
        names.add(name)
    if not dictionaries or not any(item["scope"] != "shared" for item in dictionaries):
        fail("terminology registry needs shared and per-book accepted dictionaries")

    rejected = []
    seen_terms = set()
    for item in data["rejected_terms"]:
        required = {"term", "preferred", "scope", "category", "checks", "reason"}
        if not isinstance(item, dict) or set(item) != required:
            fail("rejected-term fields do not match the version 1 contract")
        term = item["term"]
        preferred = item["preferred"]
        if not isinstance(term, str) or not term or term in seen_terms:
            fail(f"invalid or duplicate rejected term: {term!r}")
        if not isinstance(preferred, str) or not preferred or term == preferred:
            fail(f"rejected term needs a distinct preferred form: {term}")
        if item["scope"] not in scopes:
            fail(f"rejected term uses an unknown scope: {term}")
        if item["category"] not in VALID_CATEGORIES:
            fail(f"rejected term uses an unknown category: {term}")
        checks = item["checks"]
        if (
            not isinstance(checks, list)
            or checks != sorted(set(checks))
            or not set(checks) <= VALID_CHECKS
        ):
            fail(f"rejected term has invalid or unsorted checks: {term}")
        if not checks:
            fail(f"rejected term must name at least one checker: {term}")
        if not isinstance(item["reason"], str) or len(item["reason"].split()) < 4:
            fail(f"rejected term needs a substantive reason: {term}")
        active_accepted = accepted.get("shared", set()) | accepted.get(item["scope"], set())
        if "cspell" in checks and term in active_accepted:
            fail(f"term is both accepted and rejected in {item['scope']}: {term}")
        if "->" in term or "->" in preferred:
            fail(f"CSpell separator is not allowed inside terminology: {term}")
        rejected.append(item)
        seen_terms.add(term)
    scope_order = {identifier: index for index, identifier in enumerate(scopes)}
    expected = sorted(
        rejected,
        key=lambda item: (scope_order[item["scope"]], item["term"].casefold()),
    )
    if rejected != expected:
        fail("rejected terms must be sorted by scope and term")
    if not rejected:
        fail("terminology registry needs explicit rejected terms")
    return scopes, dictionaries, rejected


def relative_from_config(path):
    return Path(os.path.relpath(ROOT / path, CSPELL_OUTPUT.parent)).as_posix()


def generate_cspell(scopes, dictionaries, rejected):
    definitions = []
    for item in dictionaries:
        definitions.append(
            {
                "name": item["name"],
                "path": relative_from_config(item["path"]),
                "description": item["description"],
                "addWords": item["add_words"],
            }
        )
    output = {
        "version": "0.2",
        "globRoot": "../..",
        "dictionaryDefinitions": definitions,
        "dictionaries": [item["name"] for item in dictionaries if item["scope"] == "shared"],
        "flagWords": [
            f"{item['term']}->{item['preferred']}"
            for item in rejected
            if item["scope"] == "shared" and "cspell" in item["checks"]
        ],
    }
    overrides = []
    for identifier, scope in scopes.items():
        if identifier == "shared":
            continue
        scoped_dictionaries = [item["name"] for item in dictionaries if item["scope"] == identifier]
        scoped_flags = [
            f"{item['term']}->{item['preferred']}"
            for item in rejected
            if item["scope"] == identifier and "cspell" in item["checks"]
        ]
        override = {"filename": scope["files"]}
        if scoped_dictionaries:
            override["dictionaries"] = scoped_dictionaries
        if scoped_flags:
            override["flagWords"] = scoped_flags
        overrides.append(override)
    if overrides:
        output["overrides"] = overrides
    return json.dumps(output, indent=2, ensure_ascii=False) + "\n"


def generate_vale(scope_id, rejected):
    items = [item for item in rejected if item["scope"] == scope_id and "vale" in item["checks"]]
    lines = [
        "# Generated from config/writing/terminology.json; do not edit directly.",
        "extends: substitution",
        "message: \"Use '%s' instead of '%s'.\"",
        "level: error",
        "scope: ~frontmatter",
        "ignorecase: false",
        "swap:",
    ]
    for item in items:
        lines.append(
            f"  {json.dumps(item['term'], ensure_ascii=False)}: {json.dumps(item['preferred'], ensure_ascii=False)}"
        )
    if not items:
        lines.append("  {}")
    return "\n".join(lines) + "\n"


def derivatives(scopes, dictionaries, rejected):
    outputs = {CSPELL_OUTPUT: generate_cspell(scopes, dictionaries, rejected)}
    for identifier, scope in scopes.items():
        target = ROOT / ".vale/styles" / scope["vale_style"] / "Terminology.yml"
        outputs[target] = generate_vale(identifier, rejected)
    return outputs


def main():
    parser = argparse.ArgumentParser(
        description="Generate or check writing-terminology derivatives."
    )
    parser.add_argument(
        "--check", action="store_true", help="fail if generated derivatives are stale"
    )
    args = parser.parse_args()
    data = load_registry()
    scopes, dictionaries, rejected = validate(data)
    outputs = derivatives(scopes, dictionaries, rejected)
    if args.check:
        stale = []
        for path, expected in outputs.items():
            try:
                actual = path.read_text(encoding="utf-8")
            except OSError:
                actual = None
            if actual != expected:
                stale.append(path.relative_to(ROOT).as_posix())
        if stale:
            fail("writing-terminology derivatives are stale: " + ", ".join(stale))
        print(
            f"ok: writing terminology ({len(dictionaries)} accepted dictionaries; "
            f"{len(rejected)} rejected terms; {len(scopes)} scopes)"
        )
        return
    for path, content in outputs.items():
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
        print(f"generated {path.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
