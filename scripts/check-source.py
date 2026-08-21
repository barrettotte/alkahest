"""Run semantic source checks or their fixture suites through one dispatcher."""

import argparse
import os
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
SCRIPTS = ROOT / "scripts"
LOCKED_PYTHON = Path("/opt/alkahest/tools/bin/python")

CHECKS = (
    ("execution-policy", "check-execution-policy.py", False),
    ("graphs", "check-graphs.py", False),
    ("circuits", "check-circuits.py", True),
    ("chemistry", "check-chemistry.py", True),
    ("computing-diagrams", "check-computing-diagrams.py", False),
    ("physics-diagrams", "check-physics-diagrams.py", False),
    ("rich-media", "check-rich-media.py", False),
    ("pdf-backend", "check-pdf-backend-decision.py", False),
    ("pdf-accessibility-policy", "check-pdf-accessibility-policy.py", False),
    ("editorial-integrity", "check-editorial-integrity.py", False),
    ("identities", "check-identities.py", False),
    ("editions", "check-editions.py", False),
    ("learning", "check-learning.py", False),
    ("companions", "check-companions.py", False),
    ("reuse", "check-reuse.py", False),
    ("citations", "check-citations.py", False),
    ("glossary", "check-glossary.py", False),
    ("generated-lists", "check-generated-lists.py", False),
    ("icons", "check-icons.py", False),
    ("index", "check-index.py", False),
    ("notes", "check-notes.py", False),
)

TESTS = (
    ("execution-policy", "test-execution-policy.py", False),
    ("pdf-accessibility-policy", "test-pdf-accessibility-policy.py", False),
    ("editorial-integrity", "test-editorial-integrity.py", False),
    ("identities", "test-identities.sh", False),
    ("editions", "test-editions.py", False),
    ("learning", "test-learning.py", False),
    ("companions", "test-companions.py", False),
    ("reuse", "test-reuse.py", False),
    ("citations", "test-citations.sh", False),
    ("generated-lists", "test-generated-lists.sh", False),
    ("glossary", "test-glossary.sh", False),
    ("index", "test-index.sh", False),
    ("notes", "test-notes.sh", False),
)


def command(script, needs_locked_python, test_mode=False):
    path = SCRIPTS / script
    if test_mode and path.suffix != ".py":
        return [str(path)]
    if not needs_locked_python:
        return [sys.executable, str(path)]
    configured = os.environ.get("ALKAHEST_LOCKED_PYTHON")
    if configured:
        return [configured, str(path)]
    if ROOT == Path("/workspace") and LOCKED_PYTHON.is_file():
        return [str(LOCKED_PYTHON), str(path)]
    return [str(SCRIPTS / "python-tools.sh"), str(path.relative_to(ROOT))]


def parse_arguments():
    parser = argparse.ArgumentParser(
        description="Run all semantic source checks or selected check groups."
    )
    parser.add_argument("checks", nargs="*", help="optional check group names")
    parser.add_argument(
        "--tests",
        action="store_true",
        help="run source-policy fixture suites instead of source checks",
    )
    parser.add_argument(
        "--list", action="store_true", help="list available check groups and exit"
    )
    return parser.parse_args()


def main():
    arguments = parse_arguments()
    groups = TESTS if arguments.tests else CHECKS
    by_name = {name: (script, locked) for name, script, locked in groups}
    if arguments.list:
        for name, script, _ in groups:
            print(f"{name:<22} {script}")
        return 0
    requested = arguments.checks or list(by_name)
    unknown = [name for name in requested if name not in by_name]
    if unknown:
        kind = "test" if arguments.tests else "check"
        print(f"error: unknown source {kind} group: {', '.join(unknown)}", file=sys.stderr)
        list_command = (
            "check-source.py --tests --list"
            if arguments.tests
            else "check-source.py --list"
        )
        print(f"run {list_command} to see valid names", file=sys.stderr)
        return 2
    if len(requested) != len(set(requested)):
        print("error: source check groups must not be duplicated", file=sys.stderr)
        return 2
    for name in requested:
        script, locked = by_name[name]
        result = subprocess.run(
            command(script, locked, arguments.tests), cwd=ROOT, check=False
        )
        if result.returncode:
            kind = "test" if arguments.tests else "check"
            print(
                f"error: source {kind} group '{name}' failed with status "
                f"{result.returncode}",
                file=sys.stderr,
            )
            return result.returncode
    if arguments.tests:
        suite_label = "fixture suite" if len(requested) == 1 else "fixture suites"
        print(f"ok: source policy tests ({len(requested)} {suite_label})")
    else:
        group_label = "check group" if len(requested) == 1 else "check groups"
        print(f"ok: source policy ({len(requested)} {group_label})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
