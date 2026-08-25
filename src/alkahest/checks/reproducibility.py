"""Check and repeat the exact publication-artifact reproducibility contract."""

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path

from alkahest.process import run_process
from alkahest.reproducibility import (
    ReproducibilityError,
    compare_snapshots,
    read_policy,
    snapshot,
)

DEFAULT_ROOT = Path(__file__).resolve().parents[3]


def parse_arguments():
    parser = argparse.ArgumentParser()
    parser.add_argument("--artifacts", action="store_true")
    parser.add_argument("--repeat", choices=("quick", "full"))
    parser.add_argument("--snapshot", type=Path)
    parser.add_argument("--compare", type=Path)
    return parser.parse_args()


def load_snapshot(path):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise ReproducibilityError(f"error: cannot load snapshot {path}: {error}") from error


def main():
    arguments = parse_arguments()
    root = Path(os.environ.get("ALKAHEST_REPRO_ROOT", str(DEFAULT_ROOT))).resolve()
    policy = read_policy(root)

    requested = sum(
        bool(value)
        for value in (
            arguments.artifacts,
            arguments.repeat,
            arguments.snapshot,
            arguments.compare,
        )
    )
    if requested > 1:
        raise ReproducibilityError("error: choose one artifact operation")

    if arguments.repeat:
        key = "quick_repeat" if arguments.repeat == "quick" else "full_repeat"
        identifiers = policy["verification"][key]
        before = snapshot(root, policy, identifiers)
        artifacts = {item["id"]: item for item in policy["contract"]["artifacts"]}
        for identifier in identifiers:
            run_process(
                [
                    sys.executable,
                    "-m",
                    "alkahest",
                    "render",
                    artifacts[identifier]["render_target"],
                ],
                cwd=root,
                check=True,
            )
        after = snapshot(root, policy, identifiers)
        compare_snapshots(before, after)
        print(
            f"ok: reproducible repeated build ({len(identifiers)} exact artifacts; "
            f"mode {arguments.repeat})"
        )
        return

    current = None
    if arguments.artifacts or arguments.snapshot or arguments.compare:
        current = snapshot(root, policy)
    if arguments.snapshot:
        arguments.snapshot.write_text(
            json.dumps(current, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )
    if arguments.compare:
        if current is None:
            raise RuntimeError(
                "cannot compare reproducibility artifacts without a current snapshot"
            )
        compare_snapshots(load_snapshot(arguments.compare), current)
    if current:
        print(
            f"ok: reproducible artifacts ({len(current['artifacts'])} exact fingerprints; "
            f"epoch {policy['source_date_utc']})"
        )
    else:
        print(
            f"ok: reproducibility policy ({len(policy['contract']['artifacts'])} exact artifacts; "
            "frozen dates, identifier, toolchain, and diagnostic variation)"
        )


if __name__ == "__main__":
    try:
        main()
    except (ReproducibilityError, subprocess.CalledProcessError) as error:
        print(str(error), file=sys.stderr)
        sys.exit(1)
