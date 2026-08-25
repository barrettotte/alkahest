"""Command-line interface for the reusable Alkahest publishing library."""

from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
from collections.abc import Sequence

from .common import ContractError
from .new_book import create_new_book
from .process import run_process
from .tasks import (
    CHECKS,
    GENERATORS,
    PACKAGERS,
    RENDER_PROFILES,
    ROOT,
    SCRIPTS,
    SOURCE_CHECKS,
    ScriptTask,
    by_name,
    run_task,
)


def _selection(
    requested: Sequence[str], tasks: dict[str, ScriptTask], kind: str
) -> list[ScriptTask]:
    unknown = [name for name in requested if name not in tasks]
    if unknown:
        choices = ", ".join(sorted(tasks))
        raise ValueError(f"unknown {kind}: {', '.join(unknown)}; choose from {choices}")
    if len(requested) != len(set(requested)):
        raise ValueError(f"duplicate {kind} requested")
    return [tasks[name] for name in requested]


def _run_many(tasks: Sequence[ScriptTask], label: str) -> int:
    for task in tasks:
        status = run_task(task)
        if status:
            print(f"error: {label} '{task.name}' failed with status {status}", file=sys.stderr)
            return status
    print(f"ok: {label} ({len(tasks)} tasks)")
    return 0


def _list_tasks() -> int:
    groups: tuple[tuple[str, Sequence[ScriptTask]], ...] = (
        ("source checks", SOURCE_CHECKS),
        ("artifact checks", tuple(CHECKS.values())),
        ("generators", tuple(GENERATORS.values())),
        ("packagers", tuple(PACKAGERS.values())),
    )
    for heading, tasks in groups:
        print(f"{heading}:")
        for task in tasks:
            print(f"  {task.name:<28} {task.description}")
        print()
    print("fixture tests:")
    print("  pytest discovery             tests/integration")
    print("  focused                      make test-NAME")
    print()
    print("render profiles:")
    for profile in RENDER_PROFILES:
        print(f"  {profile}")
    return 0


def _run_tests(names: Sequence[str]) -> int:
    root = ROOT / "tests/integration"
    if not names:
        return run_process(
            [sys.executable, "-m", "pytest", root, "-m", "not locked"],
            cwd=ROOT,
            check=False,
        ).returncode

    expanded = tuple(
        selected
        for name in names
        for selected in (
            ("accessibility-policy", "accessibility-browser")
            if name == "accessibility"
            else (name,)
        )
    )
    for name in expanded:
        normalized = name.replace("-", "_")
        python_test = root / f"test_{normalized}.py"
        shell_test = root / f"test-{name}.sh"
        if python_test.is_file():
            command = [sys.executable, "-m", "pytest", str(python_test)]
        elif name == "accessibility-browser":
            command = [
                str(SCRIPTS / "python-tools.sh"),
                "--read-only",
                "-m",
                "alkahest.checks.suites",
                "browser-fixture",
            ]
        elif shell_test.is_file():
            command = [
                sys.executable,
                "-m",
                "pytest",
                str(root / "test_process_contracts.py"),
                "-k",
                normalized,
            ]
        else:
            raise ValueError(f"unknown test: {name}; run make test for the complete suite")
        if run_process(command, cwd=ROOT, check=False).returncode:
            return 1
    return 0


def _quality() -> int:
    commands = (
        ["ruff", "check", "src", "scripts", "tests"],
        ["ruff", "format", "--check", "src", "scripts", "tests"],
        ["mypy"],
        ["pytest", "-m", "not locked"],
    )
    for command in commands:
        try:
            run_process(command, cwd=ROOT, check=True)
        except (OSError, subprocess.CalledProcessError) as error:
            print(f"error: quality command failed: {error}", file=sys.stderr)
            return 1
    return 0


def _security() -> int:
    audit = shutil.which("pip-audit")
    if audit is None:
        print(
            "error: security dependencies are absent; run uv run --group security alkahest security",
            file=sys.stderr,
        )
        return 2
    commands = (
        ["ruff", "check", "--select", "S", "src/alkahest"],
        [audit, "--local"],
    )
    for command in commands:
        try:
            run_process(command, cwd=ROOT, check=True)
        except (OSError, subprocess.CalledProcessError) as error:
            print(f"error: security command failed: {error}", file=sys.stderr)
            return 1
    return 0


def parser() -> argparse.ArgumentParser:
    """Build the complete public command parser."""
    command = argparse.ArgumentParser(prog="alkahest", description=__doc__)
    actions = command.add_subparsers(dest="command", required=True)
    actions.add_parser("list", help="list every registered specialist task")
    actions.add_parser("doctor", help="report publishing-toolchain diagnostics")
    actions.add_parser("bootstrap", help="build the pinned publishing image")
    actions.add_parser("ci", help="run the complete publishing validation pipeline")
    actions.add_parser("quality", help="run formatting, lint, typing, and unit tests")
    actions.add_parser("security", help="scan Python source and locked dependencies")

    check = actions.add_parser("check", help="run semantic or artifact checks")
    check.add_argument("names", nargs="*", help="source check names; omit for all")
    check.add_argument("--source", action="store_true", help="force source-policy checks")

    tests = actions.add_parser("test", help="run fixture suites")
    tests.add_argument("names", nargs="*", help="fixture names; omit for all")

    render = actions.add_parser("render", help="render one publication profile")
    render.add_argument("profile", nargs="?", default="all", choices=RENDER_PROFILES)

    generate = actions.add_parser("generate", help="run one deterministic generator")
    generate.add_argument("name", choices=sorted(GENERATORS))
    generate.add_argument(
        "--require-onix",
        action="store_true",
        help="require publication metadata generation to produce ONIX XML",
    )

    package = actions.add_parser("package", help="build one deterministic package")
    package.add_argument("name", choices=sorted(PACKAGERS))

    report = actions.add_parser("report", help="produce a local diagnostic report")
    report.add_argument("name", choices=("build", "toolchain"))

    new_book = actions.add_parser("new-book", help="create a minimal independent book")
    new_book.add_argument("--destination", required=True)
    new_book.add_argument("--title", required=True)
    new_book.add_argument("--author", required=True)
    new_book.add_argument("--book-id")
    new_book.add_argument("--subtitle")
    new_book.add_argument("--language")
    new_book.add_argument("--created")
    return command


def main(arguments: Sequence[str] | None = None) -> int:
    """Run the requested Alkahest command."""
    values = parser().parse_args(arguments)
    try:
        if values.command == "list":
            return _list_tasks()
        if values.command == "doctor":
            return run_process([SCRIPTS / "quarto.sh", "check"], cwd=ROOT, check=False).returncode
        if values.command == "bootstrap":
            return run_process([SCRIPTS / "bootstrap.sh"], cwd=ROOT, check=False).returncode
        if values.command == "ci":
            from .ci import run as run_ci

            return run_ci()
        if values.command == "quality":
            return _quality()
        if values.command == "security":
            return _security()
        if values.command == "check":
            source_checks = by_name(SOURCE_CHECKS)
            if not values.names:
                return _run_many(SOURCE_CHECKS, "check")
            available = source_checks if values.source else {**source_checks, **CHECKS}
            return _run_many(_selection(values.names, available, "check"), "check")
        if values.command == "test":
            return _run_tests(values.names)
        if values.command == "render":
            from .rendering.pipeline import main as render_main

            return render_main([values.profile])
        if values.command == "generate":
            if values.require_onix and values.name != "publication-metadata":
                raise ValueError("--require-onix applies only to publication-metadata")
            arguments = ("--require-onix",) if values.require_onix else ()
            return run_task(GENERATORS[values.name], arguments)
        if values.command == "package":
            return run_task(PACKAGERS[values.name])
        if values.command == "report":
            from .reporting import main as report_main

            return report_main([values.name])
        if values.command == "new-book":
            result = create_new_book(
                ROOT,
                values.destination,
                title=values.title,
                author=values.author,
                book_id=values.book_id,
                subtitle=values.subtitle,
                language=values.language,
                created=values.created,
            )
            options = result["options"]
            print(
                f"created: {result['destination']} "
                f"({result['files']} files; id {options['id']}; "
                f"{options['epub_identifier']})"
            )
            return 0
    except ValueError as error:
        print(f"error: {error}", file=sys.stderr)
        return 2
    except (ContractError, OSError, UnicodeError) as error:
        print(error, file=sys.stderr)
        return 1
    raise RuntimeError(f"unhandled command {values.command!r}")
