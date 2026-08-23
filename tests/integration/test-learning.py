"""Exercise valid and deliberately invalid semantic learning contracts."""

import copy
import json
import re
import shutil
import sys
import tempfile
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR.parents[1] / "src"))

from alkahest.common import ContractError
from alkahest.learning import validate_learning


FIXTURE = SCRIPT_DIR.parents[1] / "tests" / "learning" / "base"


def new_case(name):
    temporary = tempfile.TemporaryDirectory(prefix=f"alkahest-learning-{name}-")
    root = Path(temporary.name)
    shutil.copytree(FIXTURE, root, dirs_exist_ok=True)
    registry = json.loads((FIXTURE / "registry.json").read_text(encoding="utf-8"))
    return temporary, root, registry


def edit(root, source, pattern, replacement):
    path = root / source
    content = path.read_text(encoding="utf-8")
    changed, count = re.subn(pattern, replacement, content, count=1)
    if count != 1:
        raise RuntimeError(f"error: learning fixture edit did not match {pattern}")
    path.write_text(changed, encoding="utf-8")


def expect_failure(name, expected, mutate):
    temporary, root, registry = new_case(name)
    try:
        mutate(root, registry)
        try:
            validate_learning(root, registry)
        except ContractError as error:
            if expected not in str(error):
                raise RuntimeError(f"error: learning fixture '{name}' missed '{expected}': {error}")
        else:
            raise RuntimeError(f"error: learning fixture '{name}' unexpectedly passed")
    finally:
        temporary.cleanup()


def main():
    temporary, root, registry = new_case("valid")
    try:
        validate_learning(root, registry)
    finally:
        temporary.cleanup()
    cases = (
        ("missing-role", "has no objectives specimen", lambda r, _: edit(r, "lesson.qmd", r" \.learning-objectives", "")),
        ("wrong-prefix", "objectives block needs a stable 'obj-...' ID", lambda r, _: edit(r, "lesson.qmd", r"#obj-fixture", "#wrong-fixture")),
        ("multiple-roles", "multiple learning roles", lambda r, _: edit(r, "lesson.qmd", r" \.learning-objectives", " .learning-objectives .learning-summary")),
        ("direct-callout-identity", "must use a neutral wrapper", lambda r, _: edit(r, "lesson.qmd", r"\.learning-objectives\}", ".learning-objectives .callout-tip}")),
        ("missing-title", "must contain exactly one visible H2 title", lambda r, _: edit(r, "lesson.qmd", r"## Learning objectives\n", "")),
        ("invalid-time", "invalid expected-time", lambda r, _: edit(r, "lesson.qmd", 'expected-time="10 minutes"', 'expected-time="brief"')),
        ("invalid-difficulty", "invalid difficulty", lambda r, _: edit(r, "lesson.qmd", 'difficulty="foundational"', 'difficulty="easy"')),
        ("hidden-metadata", "expected time must remain visible", lambda r, _: edit(r, "lesson.qmd", r"Expected time: 10 minutes\.", "Expected time varies.")),
        ("solution-without-pair", "solution block needs a data-for= relationship", lambda r, _: edit(r, "lesson.qmd", ' data-for="exr-fixture"', "")),
        ("wrong-hint-target", "hint 'hint-fixture' must target a review question", lambda r, _: edit(r, "lesson.qmd", 'data-for="rev-fixture"', 'data-for="exr-fixture"')),
        ("invalid-answer-policy", "must declare answer=private or answer=none", lambda r, _: edit(r, "lesson.qmd", 'answer="private"', 'answer="sometimes"')),
        ("missing-answer", "requires a private answer-key entry", lambda r, _: edit(r, "private/answers.qmd", 'data-for="rev-fixture"', 'data-for="exr-fixture"')),
        ("public-answer-source", "must have private availability", lambda _, reg: reg["sources"]["answers"].update(availability="core")),
        ("public-answer-selection", "public edition 'public' selects answer-key source", lambda _, reg: reg["structures"]["full"]["chapters"].append({"source": "answers"})),
    )
    for name, expected, mutate in cases:
        expect_failure(name, expected, mutate)
    print("ok: learning fixtures (valid contract; 14 invalid role, structure, metadata, pairing, and privacy contracts rejected)")


if __name__ == "__main__":
    try:
        main()
    except (ContractError, OSError, RuntimeError) as error:
        print(error, file=sys.stderr)
        raise SystemExit(1)
