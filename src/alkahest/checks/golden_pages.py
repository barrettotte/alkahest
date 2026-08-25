"""Rasterize semantic PDF pages and compare them with committed goldens."""

from __future__ import annotations

import argparse
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

from alkahest.golden_pages import (
    GoldenPageError,
    baseline_name,
    compare_pixels,
    load_policy,
    read_png,
    resolve_marker_page,
    validate_baseline_coverage,
    visual_digest,
    write_rgb_png,
)
from alkahest.process import run_process

DEFAULT_ROOT = Path(__file__).resolve().parents[3]


def fail(message):
    raise GoldenPageError("error: " + message)


def parse_arguments():
    parser = argparse.ArgumentParser()
    operation = parser.add_mutually_exclusive_group()
    operation.add_argument("--policy-only", action="store_true")
    operation.add_argument("--artifacts", action="store_true")
    operation.add_argument("--update", action="store_true")
    return parser.parse_args()


def tool_output(arguments, cwd):
    try:
        result = run_process(
            arguments,
            cwd=cwd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=True,
        )
    except (OSError, subprocess.CalledProcessError) as error:
        detail = ""
        if isinstance(error, subprocess.CalledProcessError):
            detail = error.stderr.decode("utf-8", errors="replace").strip()
        fail(f"command failed: {' '.join(str(item) for item in arguments)}: {detail or error}")
    return result.stdout


def validate_rasterizer(policy, root):
    program = policy["rasterizer"]["program"]
    try:
        result = run_process(
            [program, "-v"],
            cwd=root,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            encoding="utf-8",
            check=True,
        )
    except (OSError, subprocess.CalledProcessError) as error:
        fail(f"cannot run pinned rasterizer {program}: {error}")
    match = re.search(r"pdftoppm version ([0-9.]+)", result.stdout)
    if not match or match.group(1) != policy["rasterizer"]["version"]:
        fail(
            f"pdftoppm version drift: expected {policy['rasterizer']['version']}; "
            f"found {match.group(1) if match else 'unknown'}"
        )


def rasterize_page(root, policy, artifact, page_number, output):
    settings = policy["rasterizer"]
    stem = output.with_suffix("")
    arguments = [
        settings["program"],
        "-f",
        str(page_number),
        "-l",
        str(page_number),
        "-singlefile",
        "-gray",
        "-r",
        str(settings["dpi"]),
        "-aa",
        "yes" if settings["text_antialiasing"] else "no",
        "-aaVector",
        "yes" if settings["vector_antialiasing"] else "no",
        "-png",
        str(artifact),
        str(stem),
    ]
    tool_output(arguments, root)
    if not output.is_file():
        fail(f"rasterizer did not create expected image: {output}")


def clean_qa_directory(root):
    qa = root / "book/_build/qa/golden-pages"
    expected = (root / "book/_build/qa/golden-pages").resolve()
    if qa.resolve() != expected or "_build/qa/golden-pages" not in qa.as_posix():
        fail("refusing unsafe golden-page QA path")
    if qa.exists():
        shutil.rmtree(qa)
    qa.mkdir(parents=True)
    return qa


def report_header(policy, operation):
    settings = policy["rasterizer"]
    return [
        "# Golden-page visual QA",
        "",
        f"- Operation: {operation}",
        f"- Rasterizer: `{settings['program']} {settings['version']}`",
        f"- Raster profile: {settings['dpi']} DPI, grayscale RGB, text/vector antialiasing enabled",
        "- Comparison: exact decoded pixels; PNG compression bytes are not compared",
        "",
        "| Backend | Fixture | PDF page | Result | Visual SHA-256 |",
        "|---|---|---:|---|---|",
    ]


def run_artifacts(root, policy, update):
    validate_rasterizer(policy, root)
    validate_baseline_coverage(root, policy, allow_missing=update)
    qa = clean_qa_directory(root)
    baseline_directory = root / "tests/golden-pages"
    baseline_directory.mkdir(parents=True, exist_ok=True)
    report = report_header(policy, "update baselines" if update else "compare")
    failures = []
    compared = 0

    with tempfile.TemporaryDirectory(prefix="alkahest-golden-pages.") as directory:
        temporary = Path(directory)
        for profile in policy["profiles"]:
            artifact = root / profile["artifact"]
            if not artifact.is_file():
                fail(f"missing golden-page PDF artifact: {profile['artifact']}")
            text = tool_output(["pdftotext", "-layout", str(artifact), "-"], root).decode(
                "utf-8", errors="strict"
            )
            for page in policy["pages"]:
                number = resolve_marker_page(text, page["marker"])
                name = baseline_name(profile, page)
                current_path = temporary / name
                baseline_path = baseline_directory / name
                rasterize_page(root, policy, artifact, number, current_path)
                current = read_png(current_path)
                digest = visual_digest(current)
                if update:
                    shutil.copyfile(current_path, baseline_path)
                    result = "updated"
                else:
                    expected = read_png(baseline_path)
                    comparison = compare_pixels(expected, current)
                    if comparison["same_shape"] and comparison["changed_pixels"] == 0:
                        result = "pass"
                    else:
                        result = "FAIL"
                        current_output = qa / "current" / name
                        current_output.parent.mkdir(parents=True, exist_ok=True)
                        shutil.copyfile(current_path, current_output)
                        if comparison["same_shape"]:
                            diff_output = qa / "diff" / name
                            write_rgb_png(
                                diff_output,
                                current["width"],
                                current["height"],
                                comparison["diff_pixels"],
                            )
                            detail = (
                                f"{comparison['changed_pixels']} changed pixels; "
                                f"maximum channel delta {comparison['max_channel_delta']}"
                            )
                        else:
                            detail = (
                                f"shape changed from {comparison['expected_shape']} "
                                f"to {comparison['actual_shape']}"
                            )
                        failures.append((profile["id"], page["id"], detail, name))
                report.append(
                    f"| {profile['backend']} | {page['id']} | {number} | {result} | `{digest}` |"
                )
                compared += 1

    if update:
        validate_baseline_coverage(root, policy)
    if failures:
        report.extend(["", "## Regressions", ""])
        for profile_id, page_id, detail, name in failures:
            report.append(
                f"- `{profile_id}/{page_id}`: {detail}. Compare "
                f"`tests/golden-pages/{name}` with `current/{name}` and `diff/{name}`."
            )
    else:
        report.extend(["", "All configured golden pages match their decoded baseline pixels."])
    (qa / "report.md").write_text("\n".join(report) + "\n", encoding="utf-8")
    if failures:
        fail(f"{len(failures)} golden pages changed; review book/_build/qa/golden-pages/report.md")
    action = "updated" if update else "matched"
    print(
        f"ok: golden-page visual regression ({compared} pages {action}; "
        f"{len(policy['profiles'])} backends; {policy['rasterizer']['dpi']} DPI)"
    )


def main():
    arguments = parse_arguments()
    root = Path(os.environ.get("ALKAHEST_GOLDEN_ROOT", str(DEFAULT_ROOT))).resolve()
    policy = load_policy(root)
    if not arguments.artifacts and not arguments.update:
        baselines = validate_baseline_coverage(root, policy)
        print(
            f"ok: golden-page policy ({len(policy['profiles'])} backends; "
            f"{len(policy['pages'])} semantic fixtures; {baselines} baselines)"
        )
        return
    run_artifacts(root, policy, arguments.update)


if __name__ == "__main__":
    try:
        main()
    except GoldenPageError as error:
        print(error, file=sys.stderr)
        raise SystemExit(1) from None
