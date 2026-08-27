"""Unit tests for the compact maintainer CLI."""

from types import SimpleNamespace

from alkahest import cli


def test_parser_exposes_only_maintainer_commands() -> None:
    help_text = cli.parser().format_help()
    for command in ("bootstrap", "doctor", "check", "test", "quality", "security", "render", "ci"):
        assert command in help_text
    for removed in ("new-book", "generate", "package", "report"):
        assert f"\n    {removed} " not in help_text


def test_unknown_check_is_rejected() -> None:
    assert cli.main(["check", "missing"]) == 2


def test_default_check_runs_the_source_tasks(monkeypatch) -> None:
    observed = []

    def fake(task):
        observed.append(task.name)
        return 0

    monkeypatch.setattr(cli, "run_task", fake)
    assert cli.main(["check"]) == 0
    assert observed == [task.name for task in cli.SOURCE_TASKS]


def test_quality_stops_after_failure(monkeypatch) -> None:
    observed = []

    def fake(command, **_kwargs):
        observed.append(command)
        if command[0] == "mypy":
            raise cli.subprocess.CalledProcessError(1, command)
        return SimpleNamespace(returncode=0)

    monkeypatch.setattr(cli, "run_process", fake)
    assert cli.quality() == 1
    assert [command[0] for command in observed] == ["ruff", "ruff", "mypy"]
