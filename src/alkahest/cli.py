"""Command-line interface for the Alkahest engine repository."""

from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
from collections.abc import Sequence

from .process import run_process
from .rendering.pipeline import PLANS
from .rendering.pipeline import main as render_main
from .tasks import ROOT, SOURCE_TASKS, TASKS, Task, run_task


def run_many(tasks: Sequence[Task]) -> int:
    """Stop at the first failed task."""
    for task in tasks:
        status = run_task(task)
        if status:
            print(f"error: check '{task.name}' failed with status {status}", file=sys.stderr)
            return status
    print(f"ok: check ({len(tasks)} tasks)")
    return 0


def quality() -> int:
    """Run local static analysis and tests."""
    for command in (
        ["ruff", "check", "src", "scripts", "tests"],
        ["ruff", "format", "--check", "src", "scripts", "tests"],
        ["mypy"],
        ["pytest", "-m", "not locked"],
    ):
        try:
            run_process(command, cwd=ROOT, check=True)
        except (OSError, subprocess.CalledProcessError) as error:
            print(f"error: quality command failed: {error}", file=sys.stderr)
            return 1
    return 0


def security() -> int:
    """Run the source and dependency security checks."""
    audit = shutil.which("pip-audit")
    if audit is None:
        print("error: install the security dependency group first", file=sys.stderr)
        return 2
    for command in (["ruff", "check", "--select", "S", "src/alkahest"], [audit, "--local"]):
        if run_process(command, cwd=ROOT, check=False).returncode:
            return 1
    return 0


def tests(names: Sequence[str]) -> int:
    """Run all tests or focused integration modules."""
    if not names:
        return run_process(
            [sys.executable, "-m", "pytest", ROOT / "tests", "-m", "not locked"],
            cwd=ROOT,
            check=False,
        ).returncode
    for name in names:
        path = ROOT / "tests/integration" / f"test_{name.replace('-', '_')}.py"
        if not path.is_file():
            print(f"error: unknown test: {name}", file=sys.stderr)
            return 2
        if run_process([sys.executable, "-m", "pytest", path], cwd=ROOT, check=False).returncode:
            return 1
    return 0


def parser() -> argparse.ArgumentParser:
    """Build the compact maintainer parser."""
    command = argparse.ArgumentParser(prog="alkahest", description=__doc__)
    actions = command.add_subparsers(dest="command", required=True)
    actions.add_parser("list", help="list checks and render formats")
    actions.add_parser("bootstrap", help="build the rootless publishing image")
    actions.add_parser("doctor", help="verify the pinned Quarto container")
    actions.add_parser("quality", help="run lint, formatting, typing, and tests")
    actions.add_parser("security", help="scan source and dependencies")
    actions.add_parser("ci", help="run the complete validation pipeline")
    check = actions.add_parser("check", help="run source or rendered checks")
    check.add_argument("names", nargs="*")
    test = actions.add_parser("test", help="run tests")
    test.add_argument("names", nargs="*")
    render = actions.add_parser("render", help="render HTML, EPUB, or Typst")
    render.add_argument("profile", nargs="?", default="all", choices=tuple(PLANS))
    return command


def main(arguments: Sequence[str] | None = None) -> int:
    """Run one maintainer command."""
    values = parser().parse_args(arguments)
    if values.command == "list":
        print("checks:")
        for task in TASKS.values():
            print(f"  {task.name:<16} {task.description}")
        print("\nrenders: " + ", ".join(PLANS))
        return 0
    if values.command == "bootstrap":
        return run_process([ROOT / "scripts/bootstrap.sh"], cwd=ROOT, check=False).returncode
    if values.command == "doctor":
        return run_process(
            [ROOT / "scripts/quarto.sh", "--version"], cwd=ROOT, check=False
        ).returncode
    if values.command == "quality":
        return quality()
    if values.command == "security":
        return security()
    if values.command == "ci":
        from .ci import run

        return run()
    if values.command == "check":
        selected = (
            SOURCE_TASKS
            if not values.names
            else tuple(TASKS[name] for name in values.names if name in TASKS)
        )
        unknown = set(values.names) - set(TASKS)
        if unknown:
            print(f"error: unknown check: {min(unknown)}", file=sys.stderr)
            return 2
        return run_many(selected)
    if values.command == "test":
        return tests(values.names)
    if values.command == "render":
        return render_main([values.profile])
    raise RuntimeError(f"unhandled command: {values.command}")


if __name__ == "__main__":
    raise SystemExit(main())
