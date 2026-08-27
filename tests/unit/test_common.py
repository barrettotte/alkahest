"""Unit tests for shared structured-data loaders."""

from pathlib import Path

import pytest

from alkahest.common import ContractError, load_yaml


def test_yaml_loader_reads_safe_mappings(tmp_path: Path) -> None:
    """Load nested safe YAML values."""
    path = tmp_path / "registry.yml"
    path.write_text("version: 1\nitems:\n  sample: true\n", encoding="utf-8")

    assert load_yaml(path, "fixture") == {"version": 1, "items": {"sample": True}}


def test_yaml_loader_rejects_duplicate_keys(tmp_path: Path) -> None:
    """Reject duplicate YAML mapping keys."""
    path = tmp_path / "registry.yml"
    path.write_text("items:\n  sample: one\n  sample: two\n", encoding="utf-8")

    with pytest.raises(ContractError, match="found duplicate key 'sample'"):
        load_yaml(path, "fixture")


def test_yaml_loader_rejects_unsafe_tags(tmp_path: Path) -> None:
    """Reject constructors outside safe YAML."""
    path = tmp_path / "registry.yml"
    path.write_text("value: !!python/object/new:tuple []\n", encoding="utf-8")

    with pytest.raises(ContractError, match="invalid fixture YAML"):
        load_yaml(path, "fixture")
