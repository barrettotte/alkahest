"""Small standard-library helpers shared by publishing validators."""

import json
from pathlib import Path


class ContractError(RuntimeError):
    """A user-facing publishing contract violation."""


def fail(message):
    raise ContractError(f"error: {message}")


def load_json(path, label):
    path = Path(path)
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError) as error:
        fail(f"cannot read {label} '{path}': {error}")
    except json.JSONDecodeError as error:
        fail(f"invalid {label} JSON in {path}: {error}")


def qmd_sources(root):
    root = Path(root)
    return sorted(
        path
        for path in root.rglob("*.qmd")
        if "_build" not in path.parts and ".quarto" not in path.parts
    )
