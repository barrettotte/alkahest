"""Small structured-data helpers shared by publishing validators."""

import json
from pathlib import Path
from typing import Any, Never

import yaml
from yaml.constructor import ConstructorError
from yaml.nodes import MappingNode


class ContractError(RuntimeError):
    """A user-facing publishing contract violation."""


def fail(message: str) -> Never:
    raise ContractError(f"error: {message}")


def load_json(path: str | Path, label: str) -> Any:
    path = Path(path)
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError) as error:
        fail(f"cannot read {label} '{path}': {error}")
    except json.JSONDecodeError as error:
        fail(f"invalid {label} JSON in {path}: {error}")


class _UniqueKeyLoader(yaml.SafeLoader):
    """Load safe YAML while rejecting keys that would otherwise be overwritten."""

    def construct_mapping(self, node: MappingNode, deep: bool = False) -> dict[Any, Any]:
        self.flatten_mapping(node)
        mapping: dict[Any, Any] = {}
        for key_node, value_node in node.value:
            key = self.construct_object(key_node, deep=deep)
            try:
                duplicate = key in mapping
            except TypeError as error:
                raise ConstructorError(
                    "while constructing a mapping",
                    node.start_mark,
                    "found an unhashable key",
                    key_node.start_mark,
                ) from error
            if duplicate:
                raise ConstructorError(
                    "while constructing a mapping",
                    node.start_mark,
                    f"found duplicate key {key!r}",
                    key_node.start_mark,
                )
            mapping[key] = self.construct_object(value_node, deep=deep)
        return mapping


def load_yaml(path: str | Path, label: str) -> dict[str, Any]:
    path = Path(path)
    try:
        content = path.read_text(encoding="utf-8")
    except (OSError, UnicodeError) as error:
        fail(f"cannot read {label} '{path}': {error}")
    loader = _UniqueKeyLoader(content)
    try:
        data = loader.get_single_data()
    except yaml.YAMLError as error:
        fail(f"invalid {label} YAML in {path}: {error}")
    finally:
        loader.dispose()
    if not isinstance(data, dict):
        fail(f"{label} in {path} must contain a top-level mapping")
    return data


def qmd_sources(root: str | Path) -> list[Path]:
    root = Path(root)
    return sorted(
        path
        for path in root.rglob("*.qmd")
        if "_build" not in path.parts and ".quarto" not in path.parts
    )
