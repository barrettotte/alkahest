"""Run artifact-level print preflight for every configured PDF profile."""

import argparse
import json
import sys
from pathlib import Path, PurePosixPath

ROOT = Path(__file__).resolve().parents[3]

from alkahest.pdf_preflight import PreflightError, inspect_pdf

DEFAULT_POLICY = ROOT / "config" / "pdf" / "preflight.json"


def arguments():
    parser = argparse.ArgumentParser(
        description="Validate PDF boxes, fonts, raster resolution, and color models."
    )
    parser.add_argument(
        "policy",
        nargs="?",
        type=Path,
        default=DEFAULT_POLICY,
        help="preflight policy JSON (default: config/pdf/preflight.json)",
    )
    return parser.parse_args()


def repo_path(value):
    if not isinstance(value, str) or not value:
        raise PreflightError("artifact paths must be nonempty strings")
    path = PurePosixPath(value)
    if path.is_absolute() or ".." in path.parts or str(path) != value:
        raise PreflightError(f"artifact path is not normalized: {value}")
    return ROOT / Path(*path.parts)


def positive_number(value, label, allow_zero=False):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise PreflightError(f"{label} must be numeric")
    if value < 0 or (value == 0 and not allow_zero):
        boundary = "nonnegative" if allow_zero else "positive"
        raise PreflightError(f"{label} must be {boundary}")


def validate_policy(policy):
    settings = policy.get("policy")
    if not isinstance(settings, dict):
        raise PreflightError("preflight policy needs a policy object")
    positive_number(
        settings.get("geometry_tolerance_points"),
        "geometry_tolerance_points",
        allow_zero=True,
    )
    for name in ("continuous_tone_minimum_ppi", "one_bit_minimum_ppi"):
        positive_number(settings.get(name), name)
    for name in ("allowed_pdf_versions", "allowed_vector_color_families"):
        values = settings.get(name)
        if not isinstance(values, list) or not values or not all(
            isinstance(value, str) and value for value in values
        ):
            raise PreflightError(f"{name} must be a nonempty string array")
    components = settings.get("allowed_icc_components")
    if (
        not isinstance(components, list)
        or not components
        or not all(isinstance(value, int) and value > 0 for value in components)
    ):
        raise PreflightError("allowed_icc_components must be positive integers")
    if not isinstance(settings.get("permit_output_intent"), bool):
        raise PreflightError("permit_output_intent must be boolean")
    raster_models = settings.get("allowed_raster_color_models")
    if not isinstance(raster_models, list) or not raster_models:
        raise PreflightError("allowed_raster_color_models must be nonempty")
    for model in raster_models:
        if (
            not isinstance(model, dict)
            or not isinstance(model.get("name"), str)
            or not model["name"]
            or not isinstance(model.get("components"), int)
            or model["components"] < 1
        ):
            raise PreflightError("raster color models need a name and components")

    for profile in policy["profiles"]:
        if not isinstance(profile, dict):
            raise PreflightError("PDF profiles must be objects")
        if profile.get("backend") not in {"typst", "lualatex"}:
            raise PreflightError("PDF profile backend must be typst or lualatex")
        if not isinstance(profile.get("label"), str) or not profile["label"]:
            raise PreflightError("PDF profiles need nonempty labels")
        trim = profile.get("trim_points")
        if not isinstance(trim, list) or len(trim) != 2:
            raise PreflightError("PDF profiles need two trim_points")
        positive_number(trim[0], "trim width")
        positive_number(trim[1], "trim height")
        positive_number(profile.get("bleed_points"), "bleed_points", allow_zero=True)


def load_policy(path):
    try:
        policy = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise PreflightError(f"cannot read policy {path}: {error}") from error
    if policy.get("schema_version") != 1:
        raise PreflightError("preflight policy must use schema_version 1")
    if not isinstance(policy.get("profiles"), list) or not policy["profiles"]:
        raise PreflightError("preflight policy needs at least one profile")
    validate_policy(policy)
    return policy


def main():
    options = arguments()
    try:
        configured = load_policy(options.policy)
    except PreflightError as error:
        print(f"error: {error}", file=sys.stderr)
        return 1

    policy = configured.get("policy", {})
    failures = []
    totals = {"pages": 0, "fonts": 0, "images": 0}
    seen = set()
    for profile in configured["profiles"]:
        label = profile.get("label", "unnamed PDF profile")
        profile_id = profile.get("id")
        if not isinstance(profile_id, str) or not profile_id or profile_id in seen:
            failures.append(f"{label}: profile IDs must be nonempty and unique")
            continue
        seen.add(profile_id)
        try:
            path = repo_path(profile.get("artifact"))
            pages, fonts, images, color_families = inspect_pdf(path, profile, policy)
        except (KeyError, TypeError, ValueError, PreflightError) as error:
            failures.append(f"{label}: {error}")
            continue
        totals["pages"] += pages
        totals["fonts"] += fonts
        totals["images"] += images
        bleed = float(profile["bleed_points"])
        bleed_summary = "no bleed" if bleed == 0 else f"{bleed:g}-point bleed"
        print(
            f"ok: {label} ({pages} pages; {bleed_summary}; "
            f"{fonts} embedded/subset fonts; {images} raster images; "
            f"color spaces {','.join(sorted(color_families))})"
        )

    if failures:
        for failure in failures:
            print(f"error: {failure}", file=sys.stderr)
        print(
            f"error: PDF preflight failed for {len(failures)} of "
            f"{len(configured['profiles'])} profiles",
            file=sys.stderr,
        )
        return 1
    print(
        f"ok: PDF preflight ({len(configured['profiles'])} profiles; "
        f"{totals['pages']} pages; {totals['fonts']} font records; "
        f"{totals['images']} raster images)"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
