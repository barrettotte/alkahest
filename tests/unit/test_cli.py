"""Unit tests for the compact maintainer CLI."""

import subprocess

import pytest

from alkahest import cli
from alkahest.tasks import SOURCE_TASKS, Task


def test_parser_exposes_only_maintainer_commands() -> None:
    """Expose the deliberately small maintainer command surface."""
    help_text = cli.parser().format_help()
    commands = "{list,bootstrap,doctor,quality,security,ci,check,test,render}"
    assert commands in help_text


def test_unknown_check_is_rejected() -> None:
    """Reject a check name outside the task inventory."""
    assert cli.main(["check", "missing"]) == 2


def test_default_check_runs_the_source_tasks(monkeypatch: pytest.MonkeyPatch) -> None:
    """Run every source task when no check is named."""
    observed: list[str] = []

    def fake(task: Task) -> int:
        """Record one selected source task."""
        observed.append(task.name)
        return 0

    monkeypatch.setattr(cli, "run_task", fake)
    assert cli.main(["check"]) == 0
    assert observed == [task.name for task in SOURCE_TASKS]


def test_quality_stops_after_failure(monkeypatch: pytest.MonkeyPatch) -> None:
    """Stop the quality pipeline at its first failed command."""
    observed: list[list[str]] = []

    def fake(command: list[str], **_kwargs: object) -> subprocess.CompletedProcess[str]:
        """Fail the type-analysis command after recording it."""
        observed.append(command)
        if command[0] == "basedpyright":
            raise subprocess.CalledProcessError(1, command)
        return subprocess.CompletedProcess(command, 0)

    monkeypatch.setattr(cli, "run_process", fake)
    assert cli.quality() == 1
    assert [command[0] for command in observed] == ["ruff", "ruff", "basedpyright"]
