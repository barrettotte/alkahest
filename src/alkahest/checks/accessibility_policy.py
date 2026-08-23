"""Validate the WCAG target, theme safeguards, and manual-review ledger."""

import json
import os
import re
import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
EXPECTED_CATEGORIES = {
    "assistive-technology",
    "contrast-and-color",
    "keyboard-and-focus-order",
    "reduced-motion",
    "reflow-and-zoom",
    "responsive-and-target-size",
    "semantics-and-reading-order",
}
EXPECTED_TAGS = {"wcag2a", "wcag2aa", "wcag21a", "wcag21aa", "wcag22aa"}


def fail(message):
    raise RuntimeError(f"error: {message}")


def load_json(path, label):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError) as error:
        fail(f"cannot read {label} '{path}': {error}")
    except json.JSONDecodeError as error:
        fail(f"invalid {label} JSON in {path}: {error}")


def relative_luminance(color):
    channels = [int(color[index : index + 2], 16) / 255 for index in (1, 3, 5)]
    linear = [
        value / 12.92
        if value <= 0.04045
        else ((value + 0.055) / 1.055) ** 2.4
        for value in channels
    ]
    return 0.2126 * linear[0] + 0.7152 * linear[1] + 0.0722 * linear[2]


def contrast_ratio(first, second):
    lighter, darker = sorted(
        (relative_luminance(first), relative_luminance(second)), reverse=True
    )
    return (lighter + 0.05) / (darker + 0.05)


def validate_policy(policy):
    if policy.get("version") != 1:
        fail("accessibility policy version must be 1")
    if policy.get("standard") != "https://www.w3.org/TR/WCAG22/":
        fail("accessibility policy must target the normative WCAG 2.2 URL")
    if policy.get("target") != "WCAG 2.2 Level AA":
        fail("accessibility policy must target WCAG 2.2 Level AA")
    engine = policy.get("engine", {})
    if engine.get("name") != "axe-core" or engine.get("version") != "4.13.0":
        fail("accessibility engine must be pinned to axe-core 4.13.0")
    if set(engine.get("tags", [])) != EXPECTED_TAGS:
        fail("axe-core tags must cover WCAG 2.0, 2.1, and 2.2 A/AA rules")
    if engine.get("supplemental_rules") != ["tabindex"]:
        fail("axe-core supplemental rules must reject positive tabindex values")
    categories = policy.get("manual_categories", [])
    if len(categories) != len(set(categories)) or set(categories) != EXPECTED_CATEGORIES:
        fail("manual accessibility categories must match the complete policy set")
    if not re.fullmatch(r"book/_build/html", policy.get("rendered_root", "")):
        fail("accessibility rendered root must be book/_build/html")
    if not re.fullmatch(
        r"book/[A-Za-z0-9][A-Za-z0-9_.-]*\.json",
        policy.get("manual_evidence", ""),
    ):
        fail("manual accessibility evidence must be a root book JSON file")


def validate_evidence(policy, evidence):
    if evidence.get("version") != 1:
        fail("accessibility review version must be 1")
    for field in ("standard", "target"):
        if evidence.get(field) != policy[field]:
            fail(f"accessibility review {field} must match the policy")
    reviews = evidence.get("reviews")
    if not isinstance(reviews, list):
        fail("accessibility reviews must be an array")
    by_category = {}
    for review in reviews:
        category = review.get("category", "") if isinstance(review, dict) else ""
        if category in by_category:
            fail(f"manual accessibility category '{category}' is duplicated")
        by_category[category] = review
    if set(by_category) != EXPECTED_CATEGORIES:
        fail("manual accessibility evidence must cover every policy category exactly once")

    completed = 0
    for category in sorted(by_category):
        review = by_category[category]
        status = review.get("status")
        if status not in {"pending", "pass", "fail"}:
            fail(f"manual accessibility category '{category}' has invalid status")
        if status == "pending":
            rationale = review.get("rationale")
            if not isinstance(rationale, str) or len(rationale.strip()) < 30:
                fail(f"pending accessibility category '{category}' needs a rationale")
            continue
        completed += 1
        try:
            date.fromisoformat(review.get("tested_at", ""))
        except (TypeError, ValueError):
            fail(f"completed accessibility category '{category}' needs an ISO test date")
        for field in ("tester", "evidence"):
            value = review.get(field)
            if not isinstance(value, str) or len(value.strip()) < 3:
                fail(f"completed accessibility category '{category}' needs {field}")
        for field in ("pages", "environments"):
            value = review.get(field)
            if not isinstance(value, list) or not value or not all(
                isinstance(item, str) and item.strip() for item in value
            ):
                fail(f"completed accessibility category '{category}' needs {field}")

    claim = evidence.get("conformance_claim")
    if not isinstance(claim, bool):
        fail("accessibility conformance_claim must be true or false")
    statuses = {review["status"] for review in reviews}
    if claim and statuses != {"pass"}:
        fail("an accessibility conformance claim requires every manual category to pass")
    revision = evidence.get("artifact_revision")
    if (claim or completed) and not re.fullmatch(r"[0-9a-f]{7,64}", revision or ""):
        fail("completed accessibility evidence needs the tested artifact revision")
    return sum(review["status"] == "pending" for review in reviews), claim


def validate_theme(policy, theme_path, html_config, include_path, media_paths):
    theme = theme_path.read_text(encoding="utf-8")
    colors = dict(
        re.findall(r"^\$alkahest-([a-z]+):\s*(#[0-9a-fA-F]{6});\s*$", theme, re.M)
    )
    for pair in policy.get("contrast_pairs", []):
        foreground = pair.get("foreground", "")
        background = pair.get("background", "")
        if foreground not in colors or background not in colors:
            fail(f"contrast pair references unknown colors '{foreground}/{background}'")
        minimum = pair.get("minimum")
        if not isinstance(minimum, (int, float)) or minimum < 3:
            fail("contrast-pair minimum must be a WCAG threshold of at least 3")
        ratio = contrast_ratio(colors[foreground], colors[background])
        if ratio + 0.001 < minimum:
            fail(
                f"theme contrast for {pair.get('use', 'declared pair')} is "
                f"{ratio:.2f}:1; expected at least {minimum:.1f}:1"
            )

    for marker in (
        "a:focus-visible",
        "button:focus-visible",
        "input:focus-visible",
        "select:focus-visible",
        "summary:focus-visible",
        "textarea:focus-visible",
        'tabindex]:not([tabindex="-1"]):focus-visible',
        "outline: 3px solid $alkahest-copper;",
        ".alkahest-skip-link:focus",
        "@media (prefers-reduced-motion: reduce)",
        "animation-duration: 0.01ms !important;",
        "transition-duration: 0.01ms !important;",
        "overflow-x: auto;",
        "max-width: 100%;",
    ):
        if marker not in theme:
            fail(f"web theme is missing accessibility safeguard {marker!r}")
    if re.search(r"\boutline\s*:\s*(?:0|none)\b", theme):
        fail("web theme must not suppress focus outlines")

    config = html_config.read_text(encoding="utf-8")
    if "include-before-body: theme/accessibility-before-body.html" not in config:
        fail("HTML profile must include the keyboard skip link")
    if re.search(r"user-scalable\s*=\s*no|maximum-scale\s*=\s*1", config, re.I):
        fail("HTML profile must not disable browser zoom")
    include = include_path.read_text(encoding="utf-8")
    if (
        'class="alkahest-skip-link"' not in include
        or 'href="#quarto-document-content"' not in include
    ):
        fail("keyboard skip link must target the rendered main landmark")
    for marker in (
        "alkahestPrepareScrollableRegions",
        "region.scrollWidth > region.clientWidth",
        'region.setAttribute("tabindex", "0")',
    ):
        if marker not in include:
            fail(f"HTML accessibility include is missing overflow safeguard {marker!r}")
    for media_path in media_paths:
        media = media_path.read_text(encoding="utf-8")
        if "<main>" not in media or "</main>" not in media:
            fail(f"standalone media page '{media_path.name}' needs a main landmark")
    animation = next(path for path in media_paths if "orbit-animation" in path.name)
    if "prefers-reduced-motion: reduce" not in animation.read_text(encoding="utf-8"):
        fail("animation fixture must honor the reduced-motion preference")


def main():
    policy_path = Path(
        os.environ.get(
            "ALKAHEST_ACCESSIBILITY_POLICY",
            ROOT / "config" / "accessibility" / "wcag-2.2-aa.json",
        )
    )
    policy = load_json(policy_path, "accessibility policy")
    validate_policy(policy)
    evidence_path = Path(
        os.environ.get(
            "ALKAHEST_ACCESSIBILITY_EVIDENCE", ROOT / policy["manual_evidence"]
        )
    )
    evidence = load_json(evidence_path, "accessibility review")
    pending, claim = validate_evidence(policy, evidence)
    theme_path = Path(
        os.environ.get(
            "ALKAHEST_ACCESSIBILITY_THEME", ROOT / "book" / "theme" / "alkahest.scss"
        )
    )
    html_config = Path(
        os.environ.get(
            "ALKAHEST_ACCESSIBILITY_HTML_CONFIG", ROOT / "book" / "_quarto-html.yml"
        )
    )
    include_path = Path(
        os.environ.get(
            "ALKAHEST_ACCESSIBILITY_INCLUDE",
            ROOT / "book" / "theme" / "accessibility-before-body.html",
        )
    )
    media_root = Path(
        os.environ.get(
            "ALKAHEST_ACCESSIBILITY_MEDIA_ROOT", ROOT / "book" / "media"
        )
    )
    media_paths = [
        media_root / "orbit-animation.html",
        media_root / "vector-interactive.html",
    ]
    validate_theme(policy, theme_path, html_config, include_path, media_paths)
    print(
        "ok: WCAG 2.2 AA policy "
        f"(axe-core {policy['engine']['version']}; {len(EXPECTED_TAGS)} rule tags; "
        f"{len(policy['contrast_pairs'])} palette pairs; {pending} manual categories "
        f"pending; conformance claim: {'yes' if claim else 'no'})"
    )


if __name__ == "__main__":
    try:
        main()
    except (OSError, RuntimeError, UnicodeError) as error:
        print(error, file=sys.stderr)
        raise SystemExit(1)
