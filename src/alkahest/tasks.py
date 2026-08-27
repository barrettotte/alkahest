"""Small task inventory for the reference engine."""

from __future__ import annotations

import sys
from dataclasses import dataclass
from pathlib import Path

from .process import run_process

ROOT = Path(__file__).resolve().parents[2]


@dataclass(frozen=True)
class Task:
    """One Python module with optional locked-image execution."""

    name: str
    module: str
    description: str
    locked: bool = False
    arguments: tuple[str, ...] = ()


SOURCE_TASKS = (
    Task("editorial", "alkahest.checks.editorial", "links, IDs, and alternatives"),
    Task("citations", "alkahest.checks.citations", "bibliography and citation calls"),
    Task("glossary", "alkahest.checks.glossary", "glossary registry and references"),
    Task("icons", "alkahest.checks.icons", "semantic icon assets and calls"),
    Task("index", "alkahest.checks.index", "subject and person index"),
)

ARTIFACT_TASKS = (
    Task("writing", "alkahest.checks.writing", "spelling and prose", True, ("all",)),
    Task("glyphs", "alkahest.checks.glyph_coverage", "font glyph coverage", True),
    Task(
        "accessibility",
        "alkahest.checks.suites",
        "rendered HTML accessibility",
        True,
        ("accessibility",),
    ),
    Task(
        "publication",
        "alkahest.checks.suites",
        "links, EPUB, and Typst PDF",
        True,
        ("publication",),
    ),
)

TASKS = {task.name: task for task in (*SOURCE_TASKS, *ARTIFACT_TASKS)}


def run_task(task: Task) -> int:
    """Run one task locally or through the pinned Python tool boundary."""
    if task.locked:
        command = [str(ROOT / "scripts/python-tools.sh"), "--read-only", "-m", task.module]
    else:
        command = [sys.executable, "-m", task.module]
    return run_process([*command, *task.arguments], cwd=ROOT, check=False).returncode
