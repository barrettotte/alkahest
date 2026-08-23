"""Run the shell integration fixtures through pytest."""

import subprocess
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[2]
FIXTURES = Path(__file__).resolve().parent
SHELL_CASES = (
    "citations",
    "generated-lists",
    "glossary",
    "identities",
    "index",
    "notes",
)


@pytest.mark.parametrize("name", SHELL_CASES, ids=lambda name: name.replace("-", "_"))
def test_shell_contract(name: str) -> None:
    script = FIXTURES / f"test-{name}.sh"
    result = subprocess.run(
        [script],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    assert result.returncode == 0, result.stdout + result.stderr
