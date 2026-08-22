"""Exercise extension API schema, coverage, and documentation failures."""

import copy
import json
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR / "lib"))

from alkahest.common import ContractError
from alkahest.extension_apis import validate_extension_apis


ROOT = SCRIPT_DIR.parent
BASE = json.loads(
    (ROOT / "config/template/extension-apis.json").read_text(encoding="utf-8")
)


def expect_failure(name, expected, mutate):
    document = copy.deepcopy(BASE)
    mutate(document)
    try:
        validate_extension_apis(ROOT, document)
    except ContractError as error:
        if expected not in str(error):
            raise RuntimeError(
                f"error: extension API fixture {name} missed {expected!r}: {error}"
            ) from error
    else:
        raise RuntimeError(f"error: extension API fixture {name} unexpectedly passed")


def entry(document, api_id):
    return next(item for item in document["entries"] if item["id"] == api_id)


def main():
    expect_failure(
        "schema", "schema_version must be 1", lambda value: value.update(schema_version=2)
    )
    expect_failure(
        "version", "semantic versioning", lambda value: value.update(api_version="next")
    )
    expect_failure(
        "missing-api", "IDs must be exactly", lambda value: value["entries"].pop()
    )
    expect_failure(
        "authority",
        "invalid authority",
        lambda value: entry(value, "components").update(level="public"),
    )
    expect_failure(
        "missing-path",
        "path does not exist",
        lambda value: entry(value, "components")["entrypoints"].append(
            "book/theme/missing.scss"
        ),
    )
    expect_failure(
        "documentation-marker",
        "documentation is missing",
        lambda value: entry(value, "components")["author_markers"].append(
            "not-a-documented-marker"
        ),
    )
    expect_failure(
        "extension-coverage",
        "does not exactly cover bundled extension manifests",
        lambda value: entry(value, "semantic-icons")["entrypoints"].remove(
            "book/_extensions/alkahest-icons/_extension.yml"
        ),
    )
    expect_failure(
        "filter-coverage",
        "does not exactly cover portable Lua filters",
        lambda value: entry(value, "filters")["entrypoints"].pop(),
    )
    expect_failure(
        "generator-coverage",
        "does not exactly cover deterministic Python generators",
        lambda value: entry(value, "generators")["entrypoints"].pop(),
    )
    result = validate_extension_apis(ROOT)
    if result["entries"] != 15 or result["levels"] != 4:
        raise RuntimeError("error: extension API valid fixture returned wrong facts")
    print(
        "ok: extension API fixtures "
        "(closed inventory and exact docs; 9 schema, path, and coverage failures rejected)"
    )


if __name__ == "__main__":
    try:
        main()
    except (ContractError, OSError, RuntimeError, UnicodeError) as error:
        print(error, file=sys.stderr)
        raise SystemExit(1)
