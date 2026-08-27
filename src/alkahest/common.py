"""Small structured-data helpers shared by publishing validators."""

import json
from collections.abc import Callable, Hashable
from pathlib import Path
from typing import Never, cast

import yaml
from yaml.constructor import ConstructorError
from yaml.nodes import MappingNode, Node


class ContractError(RuntimeError):
    """A user-facing publishing contract violation."""


def fail(message: str) -> Never:
    """Raise one user-facing contract error."""
    raise ContractError(f"error: {message}")


type DataValue = str | int | float | bool | None | list[DataValue] | dict[str, DataValue]


def structured_value(value: object, label: str) -> DataValue:
    """Validate recursively typed JSON-compatible data."""
    if value is None or isinstance(value, str | int | float | bool):
        return value
    if isinstance(value, list):
        return [structured_value(item, label) for item in cast(list[object], value)]
    if isinstance(value, dict):
        mapping = cast(dict[object, object], value)
        if any(not isinstance(key, str) for key in mapping):
            fail(f"{label} mappings must use string keys")
        return {cast(str, key): structured_value(item, label) for key, item in mapping.items()}

    fail(f"{label} contains unsupported structured data")


def load_json(path: str | Path, label: str) -> DataValue:
    """Load recursively typed JSON data."""
    path = Path(path)
    try:
        value = cast(object, json.loads(path.read_text(encoding="utf-8")))
    except (OSError, UnicodeError) as error:
        fail(f"cannot read {label} '{path}': {error}")
    except json.JSONDecodeError as error:
        fail(f"invalid {label} JSON in {path}: {error}")
    return structured_value(value, label)


class _UniqueKeyLoader(yaml.SafeLoader):
    """Load safe YAML while rejecting keys that would otherwise be overwritten."""

    def construct_mapping(self, node: MappingNode, deep: bool = False) -> dict[Hashable, object]:
        """Build one mapping while rejecting duplicate keys."""
        self.flatten_mapping(node)
        mapping: dict[Hashable, object] = {}
        pairs = cast(list[tuple[Node, Node]], node.value)
        construct = cast(Callable[[Node, bool], object], self.construct_object)

        for key_node, value_node in pairs:
            key_value = construct(key_node, deep)
            if not isinstance(key_value, Hashable):
                raise ConstructorError(
                    "while constructing a mapping",
                    node.start_mark,
                    "found an unhashable key",
                    key_node.start_mark,
                )
            key = key_value
            duplicate = key in mapping
            if duplicate:
                raise ConstructorError(
                    "while constructing a mapping",
                    node.start_mark,
                    f"found duplicate key {key!r}",
                    key_node.start_mark,
                )
            mapping[key] = construct(value_node, deep)
        return mapping


def load_yaml(path: str | Path, label: str) -> dict[str, DataValue]:
    """Load a typed top-level YAML mapping with unique keys."""
    path = Path(path)
    try:
        content = path.read_text(encoding="utf-8")
    except (OSError, UnicodeError) as error:
        fail(f"cannot read {label} '{path}': {error}")

    loader = _UniqueKeyLoader(content)
    try:
        value = cast(object, loader.get_single_data())
    except yaml.YAMLError as error:
        fail(f"invalid {label} YAML in {path}: {error}")
    finally:
        loader.dispose()

    data = structured_value(value, label)
    if not isinstance(data, dict):
        fail(f"{label} in {path} must contain a top-level mapping")
    return data


def qmd_sources(root: str | Path) -> list[Path]:
    """Find authored Quarto Markdown outside generated directories."""
    root = Path(root)
    return sorted(path for path in root.rglob("*.qmd") if "_build" not in path.parts and ".quarto" not in path.parts)
