"""Enforce static-only manuscript builds and the locked execution policy."""

import json
import os
import re
import sys
from pathlib import Path
from typing import Any

EXPECTED_POLICY: dict[str, Any] = {
    "schema_version": 1,
    "publication": {
        "normal": "static-only",
        "ci": "static-only",
        "release": "static-only",
        "declarative_cells": ["dot", "mermaid"],
    },
    "verification": {
        "enabled": False,
        "network": "disabled",
        "source_mount": "read-only",
        "output_mount": "disposable",
        "dependencies": "locked",
        "cache": "disabled-until-verifier-exists",
        "outputs": "committed-and-drift-checked",
    },
}

EXECUTABLE_FENCE = re.compile(
    r"^[ \t]*(?:`{3,}|~{3,})[ \t]*\{[ \t]*([A-Za-z][A-Za-z0-9_.+-]*)\b",
    re.MULTILINE,
)
FORBIDDEN_SOURCE_KEY = re.compile(
    r"^[ \t]*(jupyter|engine|execute|cache|freeze)[ \t]*:", re.MULTILINE
)
FORBIDDEN_ENGINE_KEY = re.compile(r"^[ \t]*(jupyter|engine)[ \t]*:", re.MULTILINE)
POLICY_KEY = re.compile(r"^[ \t]*(execute|cache|freeze)[ \t]*:", re.MULTILINE)
STATIC_EXECUTE_BLOCK = re.compile(
    r"^execute:[ \t]*\n"
    r"  enabled:[ \t]*false[ \t]*\n"
    r"  cache:[ \t]*false[ \t]*\n"
    r"  freeze:[ \t]*false[ \t]*$",
    re.MULTILINE,
)
SHARED_DEFAULT = re.compile(
    r"^[ \t]*-[ \t]*(alkahest-defaults\.yml|\.alkahest/quarto\.yml)[ \t]*$",
    re.MULTILINE,
)


def fail(message):
    raise RuntimeError("error: " + message)


def read_text(path):
    try:
        return path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        fail("source is not valid UTF-8: " + str(path))


def front_matter(text):
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        return ""
    for index in range(1, len(lines)):
        if lines[index].strip() in {"---", "..."}:
            return "\n".join(lines[1:index])
    fail("unterminated YAML front matter")


def relative(path, root):
    return path.relative_to(root).as_posix()


def check_policy(root):
    policy_path = root / "execution-policy.json"
    if not policy_path.is_file():
        fail("missing execution-policy.json")
    try:
        policy = json.loads(read_text(policy_path))
    except json.JSONDecodeError as error:
        fail("invalid execution-policy.json: " + str(error))
    if policy != EXPECTED_POLICY:
        fail("execution-policy.json does not match the static publication contract")


def check_configs(root):
    canonical = root / "_quarto.yml"
    if not canonical.is_file():
        fail("missing _quarto.yml")

    configs = sorted(root.glob("_quarto*.yml")) + sorted(root.glob("_quarto*.yaml"))
    for config in configs:
        text = read_text(config)
        match = FORBIDDEN_ENGINE_KEY.search(text)
        if match:
            fail(
                "configuration "
                + relative(config, root)
                + " declares forbidden execution engine key '"
                + match.group(1)
                + "'"
            )
        if config != canonical and POLICY_KEY.search(text):
            fail(
                "profile "
                + relative(config, root)
                + " may not override execute, cache, or freeze policy"
            )

    canonical_text = read_text(canonical)
    policy_text = canonical_text
    shared = SHARED_DEFAULT.findall(canonical_text)
    if shared:
        if len(shared) != 1:
            fail("_quarto.yml must include exactly one shared Alkahest defaults file")
        shared_path = root / shared[0]
        if not shared_path.is_file():
            fail("_quarto.yml shared Alkahest defaults file is missing")
        policy_text = read_text(shared_path)
        match = FORBIDDEN_ENGINE_KEY.search(policy_text)
        if match:
            fail("shared Alkahest defaults declare a forbidden execution engine")
    if not STATIC_EXECUTE_BLOCK.search(policy_text):
        fail("_quarto.yml must disable execution, cache, and freeze")
    for key in ("execute", "cache", "freeze"):
        count = len(re.findall(r"^[ \t]*" + key + r"[ \t]*:", policy_text, re.MULTILINE))
        if count != 1:
            fail("effective Quarto defaults must declare exactly one '" + key + "' policy key")


def registered_notebooks(root):
    registry_path = root / "editions.json"
    if not registry_path.is_file():
        return []
    try:
        registry = json.loads(read_text(registry_path))
    except json.JSONDecodeError as error:
        fail("invalid editions.json: " + str(error))
    sources = registry.get("sources", {})
    if not isinstance(sources, dict):
        return []
    notebooks = []
    for source in sources.values():
        if not isinstance(source, dict):
            continue
        source_path = source.get("path")
        if isinstance(source_path, str) and Path(source_path).suffix.lower() in {
            ".ipynb",
            ".rmd",
            ".rmarkdown",
        }:
            notebooks.append(source_path)
    return notebooks


def check_sources(root):
    for source_path in registered_notebooks(root):
        fail("registered manuscript source uses an executable notebook format: " + source_path)

    checked = 0
    for path in sorted(root.rglob("*")):
        if not path.is_file() or path.suffix.lower() not in {".qmd", ".md"}:
            continue
        if any(part in {"_build", ".quarto"} for part in path.parts):
            continue
        text = read_text(path)
        source_name = relative(path, root)
        for match in EXECUTABLE_FENCE.finditer(text):
            if match.group(1) not in EXPECTED_POLICY["publication"]["declarative_cells"]:
                fail(
                    "source "
                    + source_name
                    + " uses executable cell syntax '{"
                    + match.group(1)
                    + "}'; use a static language class such as '{."
                    + match.group(1)
                    + "}'"
                )
        yaml = front_matter(text)
        forbidden_match = FORBIDDEN_SOURCE_KEY.search(yaml)
        if forbidden_match:
            fail(
                "source "
                + source_name
                + " overrides forbidden execution key '"
                + forbidden_match.group(1)
                + "'"
            )
        checked += 1
    return checked


def main():
    default_root = Path(__file__).resolve().parents[3] / "book"
    root = Path(os.environ.get("ALKAHEST_EXECUTION_BOOK_ROOT", str(default_root))).resolve()
    if not root.is_dir():
        fail("book root is not a directory: " + str(root))
    check_policy(root)
    check_configs(root)
    checked = check_sources(root)
    print(
        "ok: execution policy ("
        + str(checked)
        + " static Markdown sources; normal, CI, and release builds inert; cache and freeze disabled)"
    )


if __name__ == "__main__":
    try:
        main()
    except RuntimeError as error:
        print(str(error), file=sys.stderr)
        sys.exit(1)
