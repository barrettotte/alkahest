"""Validate the dependency-free JSON Schema subset used by book contracts."""

import json
import re
from datetime import date

from .common import fail


SUPPORTED = {
    "$id",
    "$schema",
    "$ref",
    "$defs",
    "title",
    "description",
    "type",
    "const",
    "enum",
    "properties",
    "required",
    "additionalProperties",
    "items",
    "minItems",
    "maxItems",
    "uniqueItems",
    "minLength",
    "pattern",
    "minimum",
    "maximum",
    "exclusiveMinimum",
    "format",
    "oneOf",
}


def _type_matches(value, expected):
    if expected == "object":
        return isinstance(value, dict)
    if expected == "array":
        return isinstance(value, list)
    if expected == "string":
        return isinstance(value, str)
    if expected == "integer":
        return isinstance(value, int) and not isinstance(value, bool)
    if expected == "number":
        return isinstance(value, (int, float)) and not isinstance(value, bool)
    if expected == "boolean":
        return isinstance(value, bool)
    if expected == "null":
        return value is None
    fail(f"unsupported JSON Schema type {expected!r}")


def _resolve(schema, reference):
    if not isinstance(reference, str) or not reference.startswith("#/"):
        fail("book-contract schemas may use only local JSON Pointer references")
    value = schema
    for token in reference[2:].split("/"):
        token = token.replace("~1", "/").replace("~0", "~")
        if not isinstance(value, dict) or token not in value:
            fail(f"book-contract schema has unresolved reference {reference!r}")
        value = value[token]
    return value


def _validate_schema_node(node, label):
    if not isinstance(node, dict):
        fail(f"{label} must be an object")
    unknown = set(node) - SUPPORTED
    if unknown:
        fail(f"{label} uses unsupported keywords: {', '.join(sorted(unknown))}")
    for key in ("properties", "$defs"):
        if key in node:
            if not isinstance(node[key], dict):
                fail(f"{label} {key} must be an object")
            for name, child in node[key].items():
                _validate_schema_node(child, f"{label} {key}/{name}")
    if "items" in node:
        _validate_schema_node(node["items"], f"{label} items")
    for key in ("oneOf",):
        if key in node:
            if not isinstance(node[key], list) or not node[key]:
                fail(f"{label} {key} must be a nonempty array")
            for index, child in enumerate(node[key]):
                _validate_schema_node(child, f"{label} {key}/{index}")


def validate_schema(schema, label="book-contract schema"):
    """Check that a schema stays within the portable supported subset."""
    _validate_schema_node(schema, label)
    if schema.get("$schema") != "https://json-schema.org/draft/2020-12/schema":
        fail(f"{label} must declare JSON Schema draft 2020-12")
    if not isinstance(schema.get("$id"), str) or not schema["$id"].startswith(
        "urn:alkahest:schema:"
    ):
        fail(f"{label} must have an Alkahest schema URN")


def _display(path):
    return "$" + "".join(
        f"[{part}]" if isinstance(part, int) else f".{part}" for part in path
    )


def _instance_error(path, message):
    fail(f"book-contract record {_display(path)} {message}")


def _validate(instance, node, schema, path):
    if "$ref" in node:
        _validate(instance, _resolve(schema, node["$ref"]), schema, path)
        return
    if "oneOf" in node:
        matches = 0
        for option in node["oneOf"]:
            try:
                _validate(instance, option, schema, path)
            except RuntimeError:
                continue
            matches += 1
        if matches != 1:
            _instance_error(path, "must match exactly one permitted shape")
        return
    expected = node.get("type")
    if expected is not None:
        choices = expected if isinstance(expected, list) else [expected]
        if not choices or not any(_type_matches(instance, item) for item in choices):
            _instance_error(path, f"must have type {' or '.join(choices)}")
    if "const" in node and instance != node["const"]:
        _instance_error(path, f"must equal {node['const']!r}")
    if "enum" in node and instance not in node["enum"]:
        _instance_error(path, "has a value outside the allowed enumeration")
    if isinstance(instance, dict):
        required = node.get("required", [])
        for name in required:
            if name not in instance:
                _instance_error(path, f"is missing required property {name!r}")
        properties = node.get("properties", {})
        if node.get("additionalProperties") is False:
            extra = set(instance) - set(properties)
            if extra:
                _instance_error(
                    path, f"has unexpected properties: {', '.join(sorted(extra))}"
                )
        for name, child in properties.items():
            if name in instance:
                _validate(instance[name], child, schema, path + (name,))
    if isinstance(instance, list):
        if len(instance) < node.get("minItems", 0):
            _instance_error(path, "has too few items")
        if "maxItems" in node and len(instance) > node["maxItems"]:
            _instance_error(path, "has too many items")
        if node.get("uniqueItems"):
            serialized = [
                json.dumps(item, sort_keys=True, separators=(",", ":"))
                for item in instance
            ]
            if len(serialized) != len(set(serialized)):
                _instance_error(path, "must contain unique items")
        if "items" in node:
            for index, value in enumerate(instance):
                _validate(value, node["items"], schema, path + (index,))
    if isinstance(instance, str):
        if len(instance) < node.get("minLength", 0):
            _instance_error(path, "is shorter than permitted")
        if "pattern" in node and re.fullmatch(node["pattern"], instance) is None:
            _instance_error(path, f"does not match {node['pattern']!r}")
        if node.get("format") == "date":
            if re.fullmatch(r"[0-9]{4}-[0-9]{2}-[0-9]{2}", instance) is None:
                _instance_error(path, "must be an ISO date")
            try:
                date.fromisoformat(instance)
            except ValueError:
                _instance_error(path, "must be an ISO date")
    if isinstance(instance, (int, float)) and not isinstance(instance, bool):
        if "minimum" in node and instance < node["minimum"]:
            _instance_error(path, "is below the minimum")
        if "maximum" in node and instance > node["maximum"]:
            _instance_error(path, "is above the maximum")
        if "exclusiveMinimum" in node and instance <= node["exclusiveMinimum"]:
            _instance_error(path, "is not above the exclusive minimum")


def validate_instance(instance, schema):
    """Validate one record against the supported JSON Schema subset."""
    validate_schema(schema)
    _validate(instance, schema, schema, ())


__all__ = ["validate_instance", "validate_schema"]
