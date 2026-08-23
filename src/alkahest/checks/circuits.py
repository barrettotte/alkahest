"""Validate circuit sources and the deterministic portable SVG derivative."""

import subprocess
import sys
import tempfile
from pathlib import Path

from defusedxml import ElementTree as ET

from alkahest.process import run_process

REPO_ROOT = Path(__file__).resolve().parents[3]
BOOK_ROOT = REPO_ROOT / "book"
SVG_PATH = BOOK_ROOT / "figures" / "generated" / "voltage-divider.svg"
CIRCUITIKZ_PATH = BOOK_ROOT / "figures" / "candidates" / "voltage-divider-circuitikz.tex"
ZAP_PATH = BOOK_ROOT / "figures" / "candidates" / "voltage-divider-zap.typ"


def fail(message):
    raise RuntimeError("error: " + message)


def check_derivative():
    if not SVG_PATH.is_file():
        fail("missing generated circuit; run make generate-circuits")
    with tempfile.TemporaryDirectory(prefix="alkahest-circuits.") as directory:
        candidate = Path(directory) / "voltage-divider.svg"
        result = run_process(
            [
                sys.executable,
                "-m",
                "alkahest.generators.circuits",
                "--output",
                str(candidate),
            ],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            encoding="utf-8",
        )
        if result.returncode != 0:
            fail("circuit regeneration failed: " + result.stdout.strip())
        if candidate.read_bytes() != SVG_PATH.read_bytes():
            fail("generated circuit drifted; run make generate-circuits and review the derivative")


def check_svg():
    text = SVG_PATH.read_text(encoding="utf-8")
    lowered = text.lower()
    if "<script" in lowered or "<image" in lowered or "href=" in lowered:
        fail("generated circuit must be self-contained and script-free")
    try:
        root = ET.fromstring(text)
    except ET.ParseError as error:
        fail("generated circuit is invalid SVG: " + str(error))
    if root.get("role") != "img" or root.get("aria-labelledby") != "title desc":
        fail("generated circuit must declare the image role and accessible name")
    viewbox = root.get("viewBox", "").split()
    if len(viewbox) != 4 or float(viewbox[2]) <= 0 or float(viewbox[3]) <= 0:
        fail("generated circuit must declare a positive four-value viewBox")
    namespace = "{http://www.w3.org/2000/svg}"
    title = root.find(namespace + "title")
    description = root.find(namespace + "desc")
    if title is None or title.get("id") != "title" or not title.text:
        fail("generated circuit must contain a titled accessibility node")
    if description is None or description.get("id") != "desc" or not description.text:
        fail("generated circuit must contain a descriptive accessibility node")
    text_elements = root.findall(".//" + namespace + "text")
    if not text_elements or any(
        element.get("font-family") != "Libertinus Sans" for element in text_elements
    ):
        fail("generated circuit labels must use the locked Libertinus Sans family")
    labels = " ".join("".join(element.itertext()) for element in text_elements)
    for marker in ("9 V", "1 kΩ", "2 kΩ", "6 V", "3 mA"):
        if marker not in labels:
            fail("generated circuit is missing electrical label: " + marker)
    if len(root.findall(".//" + namespace + "path")) < 8:
        fail("generated circuit is missing expected vector geometry")


def check_candidates():
    circuitikz = CIRCUITIKZ_PATH.read_text(encoding="utf-8")
    for marker in ("\\usepackage[europeanresistors]{circuitikz}", "V_s=9", "R_1=1", "R_2=2"):
        if marker not in circuitikz:
            fail("CircuitikZ candidate is missing contract marker: " + marker)
    zap = ZAP_PATH.read_text(encoding="utf-8")
    for marker in (
        '#import "@preview/zap:0.6.0"',
        'vsource("source"',
        'resistor("r1"',
        'resistor("r2"',
    ):
        if marker not in zap:
            fail("Zap candidate is missing contract marker: " + marker)


def check_manuscript():
    figures = (BOOK_ROOT / "figures.qmd").read_text(encoding="utf-8")
    for marker in (
        "#sec-circuit-workflow-evaluation",
        "#fig-voltage-divider",
        'fig-pos="H"',
        "figures/generated/voltage-divider.svg",
        "figures/candidates/voltage-divider-circuitikz.tex",
        "figures/candidates/voltage-divider-zap.typ",
    ):
        if marker not in figures:
            fail("figures.qmd is missing circuit contract marker: " + marker)


def main():
    check_derivative()
    check_svg()
    check_candidates()
    check_manuscript()
    print(
        "ok: electrical-circuit specimen "
        "(Schemdraw 0.23; deterministic accessible SVG; evaluated CircuitikZ and Zap sources)"
    )


if __name__ == "__main__":
    try:
        main()
    except (OSError, RuntimeError, ValueError) as error:
        print(
            str(error) if isinstance(error, RuntimeError) else "error: " + str(error),
            file=sys.stderr,
        )
        sys.exit(1)
