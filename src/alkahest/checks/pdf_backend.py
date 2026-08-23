"""Validate the scored PDF-backend decision and its operational default."""

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
BOOK = ROOT / "book"
REGISTRY = BOOK / "pdf-backends.json"
BACKENDS = ("typst", "lualatex")
PROFILES = {"typst": "typst", "lualatex": "latex"}
DISPLAY_NAMES = {"typst": "Typst", "lualatex": "LuaLaTeX"}
CRITERIA = {
    "required-feature-fidelity": 25,
    "typography-page-control": 20,
    "reliability-diagnostics": 15,
    "template-maintainability": 15,
    "accessibility-pdf-standards": 10,
    "build-speed": 5,
    "technical-ecosystem-fit": 5,
    "long-term-portability": 5,
}


def fail(message):
    raise SystemExit(f"error: {message}")


def load_registry():
    try:
        data = json.loads(REGISTRY.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        fail(f"cannot load {REGISTRY.relative_to(ROOT)}: {error}")
    required = {
        "version",
        "decision",
        "backends",
        "measurement",
        "criteria",
        "weighted_scores",
    }
    if set(data) != required or data["version"] != 1:
        fail("pdf-backends.json has an unsupported top-level contract")
    return data


def check_decision(data):
    decision = data["decision"]
    required = {
        "date",
        "default",
        "secondary_backend",
        "policy",
        "review_triggers",
    }
    if set(decision) != required:
        fail("backend decision fields do not match the version 1 contract")
    if decision["default"] not in BACKENDS:
        fail("default PDF backend is unknown")
    if decision["secondary_backend"] not in BACKENDS:
        fail("secondary PDF backend is unknown")
    if decision["default"] == decision["secondary_backend"]:
        fail("default and secondary PDF backends must differ")
    if not re.fullmatch(r"20\d{2}-\d{2}-\d{2}", decision["date"]):
        fail("backend decision date must use YYYY-MM-DD")
    if len(decision["policy"].split()) < 8:
        fail("backend policy is not substantive")
    triggers = decision["review_triggers"]
    if not isinstance(triggers, list) or len(triggers) < 3:
        fail("backend decision needs at least three review triggers")
    if any(not isinstance(trigger, str) or len(trigger.split()) < 6 for trigger in triggers):
        fail("backend review triggers must be substantive strings")

    backends = data["backends"]
    if set(backends) != set(BACKENDS):
        fail("backend registry must contain exactly Typst and LuaLaTeX")
    default = decision["default"]
    for backend in BACKENDS:
        expected_status = "default" if backend == default else "supported-secondary"
        expected = {"profile": PROFILES[backend], "status": expected_status}
        if backends[backend] != expected:
            fail(f"{backend} profile/status is inconsistent with the decision")


def check_measurement(data):
    measurement = data["measurement"]
    required = {"captured", "toolchain_image", "method", *BACKENDS}
    if set(measurement) != required:
        fail("backend measurement fields do not match the version 1 contract")
    toolchain = (ROOT / "scripts/toolchain.sh").read_text(encoding="utf-8")
    match = re.search(r'ALKAHEST_TOOLCHAIN_IMAGE="([^"]+)"', toolchain)
    if not match or measurement["toolchain_image"] != match.group(1):
        fail("backend measurement does not name the current toolchain image")
    if not re.fullmatch(r"20\d{2}-\d{2}-\d{2}", measurement["captured"]):
        fail("backend measurement date must use YYYY-MM-DD")
    if "sequential" not in measurement["method"].lower():
        fail("backend measurement must document sequential execution")
    for backend in BACKENDS:
        result = measurement[backend]
        if set(result) != {"seconds", "warnings", "pages", "bytes", "tagged"}:
            fail(f"{backend} measurement fields are incomplete")
        if not isinstance(result["seconds"], (int, float)) or result["seconds"] <= 0:
            fail(f"{backend} duration must be positive")
        for field in ("warnings", "pages", "bytes"):
            if not isinstance(result[field], int) or result[field] < 0:
                fail(f"{backend} {field} must be a nonnegative integer")
        if result["pages"] == 0 or result["bytes"] == 0:
            fail(f"{backend} measurement must describe a nonempty PDF")
        if not isinstance(result["tagged"], bool):
            fail(f"{backend} tagged result must be boolean")


def check_scores(data):
    criteria = data["criteria"]
    if not isinstance(criteria, list) or len(criteria) != len(CRITERIA):
        fail("backend scorecard has the wrong number of criteria")
    seen = set()
    totals = {backend: 0 for backend in BACKENDS}
    for criterion in criteria:
        required = {"id", "label", "weight", "scores", "rationale"}
        if set(criterion) != required:
            fail("backend criterion fields do not match the version 1 contract")
        identifier = criterion["id"]
        if identifier in seen or identifier not in CRITERIA:
            fail(f"unknown or duplicate backend criterion: {identifier}")
        seen.add(identifier)
        if criterion["weight"] != CRITERIA[identifier]:
            fail(f"backend criterion has incorrect weight: {identifier}")
        if set(criterion["scores"]) != set(BACKENDS):
            fail(f"backend criterion scores are incomplete: {identifier}")
        if len(criterion["label"].split()) < 2 or len(criterion["rationale"].split()) < 10:
            fail(f"backend criterion lacks a substantive explanation: {identifier}")
        for backend, score in criterion["scores"].items():
            if not isinstance(score, int) or not 1 <= score <= 5:
                fail(f"{identifier} score for {backend} must be an integer from 1 to 5")
            totals[backend] += criterion["weight"] * score
    if seen != set(CRITERIA) or sum(CRITERIA.values()) != 100:
        fail("backend criteria or weights are incomplete")
    calculated = {backend: round(totals[backend] / 100, 2) for backend in BACKENDS}
    if data["weighted_scores"] != calculated:
        fail(f"weighted backend scores do not match the scorecard: {calculated}")
    if calculated[data["decision"]["default"]] < calculated[data["decision"]["secondary_backend"]]:
        fail("default backend scores below the secondary backend")


def check_repository_integration(data):
    makefile = (ROOT / "Makefile").read_text(encoding="utf-8")
    render = (ROOT / "src/alkahest/rendering/pipeline.py").read_text(encoding="utf-8")
    ci = (ROOT / "src/alkahest/ci.py").read_text(encoding="utf-8")
    tasks = (ROOT / "src/alkahest/tasks.py").read_text(encoding="utf-8")
    quarto = (BOOK / "_quarto.yml").read_text(encoding="utf-8")
    documentation = (ROOT / "docs/publication-profiles.md").read_text(encoding="utf-8")
    required_make = (
        "check-%:",
        "render-%:",
        "$(ALK) check $*",
        "$(ALK) render $*",
    )
    if any(marker not in makefile for marker in required_make):
        fail("Makefile does not expose the backend decision and default PDF commands")
    default = data["decision"]["default"]
    expected_call = f'DEFAULT_PDF_PROFILE = "{PROFILES[default]}"'
    if expected_call not in render:
        fail("render pipeline does not map the PDF command to the selected default")
    if '"pdf-backend", "@alkahest.checks.pdf_backend"' not in tasks:
        fail("task registry does not include the PDF backend decision")
    if "alkahest check" not in ci or "python3 -m alkahest check --source" not in quarto:
        fail("source policy dispatcher is not integrated into CI and rendering")
    scores = data["weighted_scores"]
    for marker in (
        f"{DISPLAY_NAMES[default]} is the default PDF backend",
        f"{scores['typst']:.2f}",
        f"{scores['lualatex']:.2f}",
        "Known exceptions",
        "Switching backends",
    ):
        if marker not in documentation:
            fail(f"backend decision documentation is missing: {marker}")
    for adapter in (
        BOOK / "typst/typst-show.typ",
        BOOK / "latex/book-layout.tex",
        BOOK / "latex/title.tex",
        BOOK / "latex/before-body.tex",
    ):
        if not adapter.is_file():
            fail(f"backend adapter is missing: {adapter.relative_to(ROOT)}")

    raw_backend = re.compile(r"\{=(?:latex|typst)\}|```\{(?:latex|typst)\}")
    for source in sorted(BOOK.rglob("*.qmd")):
        if raw_backend.search(source.read_text(encoding="utf-8")):
            fail(
                f"backend-specific raw markup leaked into manuscript source: {source.relative_to(ROOT)}"
            )


def main():
    data = load_registry()
    check_decision(data)
    check_measurement(data)
    check_scores(data)
    check_repository_integration(data)
    scores = data["weighted_scores"]
    print(
        "ok: PDF backend decision "
        f"(Typst default {scores['typst']:.2f}; "
        f"LuaLaTeX secondary {scores['lualatex']:.2f}; "
        "8 weighted criteria; reversible neutral-source policy)"
    )


if __name__ == "__main__":
    main()
