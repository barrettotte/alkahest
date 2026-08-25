"""Validate physics data and deterministic portable SVG derivatives."""

import json
import math
import subprocess
import sys
import tempfile
from datetime import date
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any

from defusedxml import ElementTree as ET

from alkahest.process import run_process

REPO_ROOT = Path(__file__).resolve().parents[3]
BOOK_ROOT = REPO_ROOT / "book"
DATA_PATH = BOOK_ROOT / "figures" / "data" / "physics-diagrams.json"
GENERATED_DIR = BOOK_ROOT / "figures" / "generated"

OUTPUTS: dict[str, dict[str, Any]] = {
    "velocity-vector.svg": {
        "viewbox": "0 0 1000 540",
        "minimum_geometry": 16,
        "markers": (
            "Velocity vector and components",
            "v_x = 20.0 m/s",
            "v_y = 15.0 m/s",
            "|v| = 25.0 m/s",
            "theta = 36.9°",
        ),
    },
    "inverse-square-field.svg": {
        "viewbox": "0 0 1000 620",
        "minimum_geometry": 38,
        "markers": (
            "Normalized inverse-square field",
            "g/g_ref = (r_ref/r)^2",
            "r_ref = 1.00 m",
            "grid = 1.00 m",
            "exclude r &lt;= 0.50 m",
            "stronger",
            "weaker",
        ),
    },
}


def fail(message):
    raise RuntimeError("error: " + message)


def load_data():
    try:
        return json.loads(DATA_PATH.read_text(encoding="utf-8"))
    except json.JSONDecodeError as error:
        fail(f"invalid JSON in {DATA_PATH.relative_to(REPO_ROOT)}: {error}")


def significant_figures(display):
    value = str(display).strip().lower()
    mantissa = value.split("e", 1)[0].lstrip("+-")
    digits = "".join(character for character in mantissa if character.isdigit())
    digits = digits.lstrip("0")
    return len(digits)


def check_measurement(name, measurement, units):
    required = {"value", "display", "unit", "significant_figures"}
    if not required.issubset(measurement):
        fail(f"{name} must record value, display, unit, and significant_figures")
    if measurement["unit"] not in units:
        fail(f"{name} references an unknown unit")
    try:
        if Decimal(measurement["display"]) != Decimal(str(measurement["value"])):
            fail(f"{name} display does not preserve its numeric value")
    except InvalidOperation:
        fail(f"{name} display is not a decimal number")
    if significant_figures(measurement["display"]) != measurement["significant_figures"]:
        fail(f"{name} significant-figure declaration does not match its display")


def check_data(data):
    if data.get("version") != 1:
        fail("physics-diagrams.json must use version 1")
    provenance = data.get("provenance", {})
    required_provenance = {"title", "creator", "created", "origin", "method", "license"}
    if not required_provenance.issubset(provenance):
        fail("physics source must record complete provenance")
    try:
        date.fromisoformat(provenance["created"])
    except (TypeError, ValueError):
        fail("physics provenance created date must use ISO 8601")
    if provenance["origin"] != "Synthetic instructional data":
        fail("the acceptance fixture must identify its synthetic origin")
    if provenance["license"] != "CC0-1.0":
        fail("the acceptance fixture must carry its distribution license")

    units = data.get("units", {})
    if set(units) != {"velocity", "distance", "angle", "relative_field"}:
        fail("physics source must define the reviewed unit registry")
    for unit_id, unit in units.items():
        if not {"quantity", "symbol", "system"}.issubset(unit):
            fail(f"unit {unit_id} must record quantity, symbol, and system")
    if units["velocity"]["symbol"] != "m/s" or units["distance"]["symbol"] != "m":
        fail("physics fixture must use explicit SI velocity and distance units")

    vector = data.get("vector", {})
    for axis in ("x", "y"):
        check_measurement(
            f"vector component {axis}", vector.get("components", {}).get(axis, {}), units
        )
    for name in ("magnitude", "angle"):
        check_measurement(f"derived {name}", vector.get("derived", {}).get(name, {}), units)
    x_value = vector["components"]["x"]["value"]
    y_value = vector["components"]["y"]["value"]
    magnitude = vector["derived"]["magnitude"]["value"]
    angle = vector["derived"]["angle"]["value"]
    if not math.isclose(math.hypot(x_value, y_value), magnitude, abs_tol=0.05):
        fail("derived velocity magnitude is inconsistent with its components")
    if not math.isclose(math.degrees(math.atan2(y_value, x_value)), angle, abs_tol=0.05):
        fail("derived velocity angle is inconsistent with its components")
    if any(vector["components"][axis]["unit"] != "velocity" for axis in ("x", "y")):
        fail("velocity components must share the velocity unit")

    field = data.get("field", {})
    if field.get("model") != "radial-inward-inverse-square":
        fail("physics field must declare the reviewed analytic model")
    for name in ("step", "reference_radius", "exclusion_radius"):
        check_measurement(f"field {name}", field.get(name, {}), units)
        if field[name]["unit"] != "distance" or field[name]["value"] <= 0:
            fail(f"field {name} must be a positive distance")
    if field.get("field_unit") != "relative_field":
        fail("field strength must use the dimensionless relative-field unit")
    for axis in ("x", "y"):
        minimum = field.get(f"{axis}_min")
        maximum = field.get(f"{axis}_max")
        if not isinstance(minimum, (int, float)) or not isinstance(maximum, (int, float)):
            fail(f"field {axis} bounds must be numeric")
        intervals = (maximum - minimum) / field["step"]["value"]
        if minimum >= 0 or maximum <= 0 or not math.isclose(intervals, round(intervals)):
            fail(f"field {axis} bounds must straddle zero on complete grid steps")


def check_derivatives():
    with tempfile.TemporaryDirectory(prefix="alkahest-physics.") as directory:
        candidate_dir = Path(directory)
        result = run_process(
            [
                sys.executable,
                "-m",
                "alkahest.generators.physics",
                "--input",
                str(DATA_PATH),
                "--output-dir",
                str(candidate_dir),
            ],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            encoding="utf-8",
        )
        if result.returncode != 0:
            fail("physics-diagram regeneration failed: " + result.stdout.strip())
        for name in OUTPUTS:
            committed = GENERATED_DIR / name
            candidate = candidate_dir / name
            if not committed.is_file():
                fail("missing generated physics diagram; run make generate-physics-diagrams")
            if candidate.read_bytes() != committed.read_bytes():
                fail(f"generated physics diagram drifted: {name}")


def check_svgs():
    namespace = "{http://www.w3.org/2000/svg}"
    for name, contract in OUTPUTS.items():
        path = GENERATED_DIR / name
        text = path.read_text(encoding="utf-8")
        lowered = text.lower()
        if not text.startswith("<?xml version='1.0' encoding='UTF-8'?>\n"):
            fail(f"{name} must declare EPUB-compatible UTF-8 XML")
        if "<script" in lowered or "<image" in lowered or "href=" in lowered:
            fail(f"{name} must be self-contained and script-free")
        try:
            root = ET.fromstring(text)
        except ET.ParseError as error:
            fail(f"invalid SVG in {name}: {error}")
        if root.get("role") != "img" or root.get("aria-labelledby") != "title desc":
            fail(f"{name} must declare an accessible image name")
        if root.get("viewBox") != contract["viewbox"]:
            fail(f"{name} has an unexpected reviewed viewBox")
        title = root.find(namespace + "title")
        description = root.find(namespace + "desc")
        if title is None or not title.text or description is None or not description.text:
            fail(f"{name} must contain a title and description")
        visible_text = " ".join(
            "".join(element.itertext()) for element in root.findall(".//" + namespace + "text")
        )
        escaped_text = escape_xml(visible_text)
        for marker in contract["markers"]:
            if marker not in escaped_text:
                fail(f"{name} is missing visible marker: {marker}")
        geometry_count = sum(
            len(root.findall(".//" + namespace + element)) for element in ("line", "path", "circle")
        )
        if geometry_count < contract["minimum_geometry"]:
            fail(f"{name} is missing expected vector geometry")


def escape_xml(value):
    return value.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def check_manuscript():
    figures = (BOOK_ROOT / "figures.qmd").read_text(encoding="utf-8")
    markers = (
        "#sec-physics-diagram-workflow",
        "#fig-velocity-vector",
        "#fig-inverse-square-field",
        "figures/data/physics-diagrams.json",
        "alkahest.generators.physics",
    )
    for marker in markers:
        if marker not in figures:
            fail("figures.qmd is missing physics-diagram marker: " + marker)


def main():
    data = load_data()
    check_data(data)
    check_derivatives()
    check_svgs()
    check_manuscript()
    print(
        "ok: physics diagrams "
        "(vector components, inverse-square field, SI units, significant figures, "
        "synthetic-data provenance, and deterministic accessible SVG)"
    )


if __name__ == "__main__":
    try:
        main()
    except (OSError, RuntimeError, TypeError, ValueError) as error:
        print(
            str(error) if isinstance(error, RuntimeError) else "error: " + str(error),
            file=sys.stderr,
        )
        sys.exit(1)
