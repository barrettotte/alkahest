"""Unit tests for the consolidated Alkahest command surface."""

from pathlib import Path

import pytest

from alkahest import cli
from alkahest import tasks as task_module
from alkahest.cli import main, parser
from alkahest.operations import OPERATIONS
from alkahest.tasks import (
    CHECKS,
    GENERATORS,
    PACKAGERS,
    SOURCE_CHECKS,
    ScriptTask,
    by_name,
    script_path,
)


def test_registered_names_are_unique() -> None:
    assert len(by_name(SOURCE_CHECKS)) == len(SOURCE_CHECKS)
    assert len(CHECKS) == len(set(CHECKS))
    assert len(GENERATORS) == len(set(GENERATORS))
    assert len(PACKAGERS) == len(set(PACKAGERS))


@pytest.mark.parametrize(
    "tasks",
    (
        SOURCE_CHECKS,
        tuple(CHECKS.values()),
        tuple(GENERATORS.values()),
        tuple(PACKAGERS.values()),
    ),
)
def test_registered_scripts_exist(tasks) -> None:
    for task in tasks:
        if task.script.startswith(":"):
            assert task.script.removeprefix(":") in OPERATIONS, task
        elif task.script.startswith("@"):
            relative = (
                Path("src").joinpath(*task.script.removeprefix("@").split(".")).with_suffix(".py")
            )
            assert relative.is_file(), task
        else:
            assert script_path(task).is_file(), task


def test_parser_exposes_small_command_surface() -> None:
    help_text = parser().format_help()
    for command in (
        "check",
        "test",
        "render",
        "generate",
        "package",
        "report",
        "quality",
        "security",
    ):
        assert command in help_text


def test_list_is_generated_from_registry(capsys) -> None:
    assert main(["list"]) == 0
    output = capsys.readouterr().out
    assert "source checks:" in output
    assert "glossary" in output
    assert "render profiles:" in output


def test_bare_check_uses_source_registry(monkeypatch) -> None:
    observed = []

    def record(tasks, _label):
        observed.extend(tasks)
        return 0

    monkeypatch.setattr(cli, "_run_many", record)
    assert main(["check"]) == 0
    assert observed == list(SOURCE_CHECKS)


def test_accessibility_test_adds_the_locked_browser_fixture(monkeypatch) -> None:
    commands = []

    def run(command, **_options):
        commands.append(command)
        return type("Result", (), {"returncode": 0})()

    monkeypatch.setattr(cli, "run_process", run)
    assert cli._run_tests(["accessibility"]) == 0
    assert str(commands[0][-1]).endswith("test_accessibility_policy.py")
    assert commands[1][-2:] == ["alkahest.checks.suites", "browser-fixture"]


def test_require_onix_is_forwarded_only_to_metadata(monkeypatch, capsys) -> None:
    observed = {}

    def record(task, arguments=()):
        observed.update(task=task, arguments=arguments)
        return 0

    monkeypatch.setattr(cli, "run_task", record)
    assert main(["generate", "publication-metadata", "--require-onix"]) == 0
    assert observed == {
        "task": GENERATORS["publication-metadata"],
        "arguments": ("--require-onix",),
    }
    assert main(["generate", "graphs", "--require-onix"]) == 2
    assert "applies only" in capsys.readouterr().err


def test_locked_direct_operation_uses_container_wrapper(monkeypatch, tmp_path) -> None:
    observed = {}

    def run(command, **options):
        observed.update(command=command, options=options)
        return type("Result", (), {"returncode": 7})()

    monkeypatch.setattr(task_module, "ROOT", tmp_path)
    monkeypatch.setattr(task_module, "run_process", run)
    task = ScriptTask("covers", ":generate-covers", "cover artifacts", True, writes_workspace=True)
    assert task_module.run_task(task) == 7
    assert observed["command"][-3:] == [
        "-m",
        "alkahest.operations",
        "generate-covers",
    ]


def test_locked_check_uses_read_only_workspace(monkeypatch, tmp_path) -> None:
    observed = {}

    def run(command, **options):
        observed.update(command=command, options=options)
        return type("Result", (), {"returncode": 0})()

    monkeypatch.setattr(task_module, "ROOT", tmp_path)
    monkeypatch.setattr(task_module, "run_process", run)
    task = ScriptTask("assets", ":check-release-assets", "release assets", True)
    assert task_module.run_task(task) == 0
    assert "--read-only" in observed["command"]


def test_new_book_calls_library_directly(monkeypatch, capsys, tmp_path) -> None:
    destination = tmp_path / "book"
    observed = {}

    def create(_root, requested, **values):
        observed.update(destination=requested, **values)
        return {
            "destination": destination,
            "files": 13,
            "options": {
                "id": "small-book",
                "epub_identifier": "urn:uuid:00000000-0000-0000-0000-000000000001",
            },
        }

    monkeypatch.setattr(cli, "create_new_book", create)
    assert (
        main(
            [
                "new-book",
                "--destination",
                str(destination),
                "--title",
                "Small Book",
                "--author",
                "Example Author",
            ]
        )
        == 0
    )
    assert observed["destination"] == str(destination)
    assert observed["title"] == "Small Book"
    assert "created:" in capsys.readouterr().out
