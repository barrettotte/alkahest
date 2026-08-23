"""Exercise golden-page policy, marker, PNG, and pixel-diff contracts."""

import copy
import json
import tempfile
from pathlib import Path

from alkahest.golden_pages import (
    GoldenPageError,
    baseline_name,
    compare_pixels,
    expected_baselines,
    read_png,
    resolve_marker_page,
    validate_baseline_coverage,
    validate_policy,
    visual_digest,
    write_rgb_png,
)


ROOT = Path(__file__).resolve().parent.parent.parent
POLICY = json.loads((ROOT / "config/pdf/golden-pages.json").read_text(encoding="utf-8"))


def expect_failure(name, expected, operation):
    try:
        operation()
    except GoldenPageError as error:
        if expected not in str(error):
            raise RuntimeError(
                f"golden-page fixture '{name}' missed diagnostic '{expected}': {error}"
            )
        return
    raise RuntimeError(f"invalid golden-page fixture unexpectedly passed: {name}")


def changed_policy(mutate):
    policy = copy.deepcopy(POLICY)
    mutate(policy)
    return policy


def main():
    validate_policy(copy.deepcopy(POLICY))
    expect_failure(
        "rasterizer-drift",
        "rasterizer must match",
        lambda: validate_policy(
            changed_policy(lambda policy: policy["rasterizer"].__setitem__("dpi", 72))
        ),
    )
    expect_failure(
        "duplicate-backend",
        "backend is invalid or duplicated",
        lambda: validate_policy(
            changed_policy(lambda policy: policy["profiles"][1].__setitem__("backend", "typst"))
        ),
    )
    expect_failure(
        "unsafe-artifact",
        "artifact is unsafe or duplicated",
        lambda: validate_policy(
            changed_policy(
                lambda policy: policy["profiles"][0].__setitem__("artifact", "/tmp/untrusted.pdf")
            )
        ),
    )
    expect_failure(
        "weak-rationale",
        "rationale is not substantive",
        lambda: validate_policy(
            changed_policy(lambda policy: policy["pages"][0].__setitem__("rationale", "Too short"))
        ),
    )
    if resolve_marker_page("first\fcontains stable marker\fthird\f", "stable marker") != 2:
        raise RuntimeError("golden marker resolved to the wrong page")
    expect_failure(
        "missing-marker",
        "found 0",
        lambda: resolve_marker_page("first\fsecond\f", "absent marker"),
    )
    expect_failure(
        "duplicate-marker",
        "found 2",
        lambda: resolve_marker_page("marker here\fmarker again\f", "marker"),
    )

    with tempfile.TemporaryDirectory(prefix="alkahest-golden-page-tests.") as directory:
        root = Path(directory)
        baseline_directory = root / "tests/golden-pages"
        baseline_directory.mkdir(parents=True)
        first_pixels = bytes((255, 255, 255, 10, 20, 30, 40, 50, 60, 0, 0, 0))
        second_pixels = bytes((255, 255, 255, 10, 20, 30, 40, 55, 60, 0, 0, 0))
        first_path = root / "first.png"
        second_path = root / "second.png"
        diff_path = root / "diff.png"
        write_rgb_png(first_path, 2, 2, first_pixels)
        write_rgb_png(second_path, 2, 2, second_pixels)
        first = read_png(first_path)
        second = read_png(second_path)
        if visual_digest(first) == visual_digest(second):
            raise RuntimeError("different fixture pixels produced the same visual digest")
        exact = compare_pixels(first, first)
        if exact["changed_pixels"] != 0:
            raise RuntimeError("identical fixture pixels did not compare exactly")
        changed = compare_pixels(first, second)
        if changed["changed_pixels"] != 1 or changed["max_channel_delta"] != 5:
            raise RuntimeError("pixel comparison reported the wrong regression metrics")
        write_rgb_png(diff_path, 2, 2, changed["diff_pixels"])
        if read_png(diff_path)["pixels"] != changed["diff_pixels"]:
            raise RuntimeError("visual diff PNG did not round-trip")

        for name in expected_baselines(POLICY):
            write_rgb_png(baseline_directory / name, 1, 1, b"\xff\xff\xff")
        if validate_baseline_coverage(root, POLICY) != 10:
            raise RuntimeError("baseline coverage returned the wrong count")
        extra = baseline_directory / "unregistered.png"
        write_rgb_png(extra, 1, 1, b"\xff\xff\xff")
        expect_failure(
            "extra-baseline",
            "unregistered golden-page baselines",
            lambda: validate_baseline_coverage(root, POLICY),
        )
        extra.unlink()
        missing_name = baseline_name(POLICY["profiles"][0], POLICY["pages"][0])
        (baseline_directory / missing_name).unlink()
        expect_failure(
            "missing-baseline",
            "missing golden-page baselines",
            lambda: validate_baseline_coverage(root, POLICY),
        )

    print(
        "ok: golden-page fixtures (policy, semantic markers, PNG decoding, exact "
        "pixels, visual diffs, and baseline coverage)"
    )


def test_contract():
    result = main()
    assert result in (None, 0)
