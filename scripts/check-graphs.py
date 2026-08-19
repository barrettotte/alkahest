"""Validate graph/chart sources and deterministic generated derivatives."""

import json
import subprocess
import sys
import tempfile
import xml.etree.ElementTree as ET
from pathlib import Path


SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parent
BOOK_ROOT = REPO_ROOT / "book"
DATA_PATH = BOOK_ROOT / "figures" / "data" / "response-time.csv"
VEGA_PATH = BOOK_ROOT / "figures" / "data" / "response-time.vl.json"
SVG_PATH = BOOK_ROOT / "figures" / "generated" / "response-time.svg"


def fail(message):
    raise RuntimeError("error: " + message)


def check_derivative():
    if not SVG_PATH.is_file():
        fail("missing generated chart; run make generate-graphs")
    with tempfile.TemporaryDirectory(prefix="alkahest-graphs.") as directory:
        candidate = Path(directory) / "response-time.svg"
        result = subprocess.run(
            [
                sys.executable,
                str(SCRIPT_DIR / "generate-graphs.py"),
                "--data",
                str(DATA_PATH),
                "--output",
                str(candidate),
            ],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            encoding="utf-8",
        )
        if result.returncode != 0:
            fail("chart regeneration failed: " + result.stdout.strip())
        if candidate.read_bytes() != SVG_PATH.read_bytes():
            fail("generated chart drifted; run make generate-graphs and review the derivative")


def check_svg():
    text = SVG_PATH.read_text(encoding="utf-8")
    if "<script" in text.lower() or "<image" in text.lower() or "href=" in text.lower():
        fail("generated chart must be self-contained and script-free")
    try:
        root = ET.fromstring(text)
    except ET.ParseError as error:
        fail("generated chart is invalid SVG: " + str(error))
    if root.get("viewBox") != "0 0 800 460" or root.get("role") != "img":
        fail("generated chart must declare the locked viewBox and image role")
    namespace = "{http://www.w3.org/2000/svg}"
    if root.find(namespace + "title") is None or root.find(namespace + "desc") is None:
        fail("generated chart must contain title and description elements")
    if not root.findall(".//" + namespace + "text") or len(root.findall(".//" + namespace + "circle")) != 5:
        fail("generated chart must preserve labels and five measured points")


def check_vega_candidate():
    try:
        spec = json.loads(VEGA_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        fail("invalid Vega-Lite candidate: " + str(error))
    if spec.get("$schema") != "https://vega.github.io/schema/vega-lite/v5.json":
        fail("Vega-Lite candidate must pin the v5 schema")
    values = spec.get("data", {}).get("values")
    if not isinstance(values, list) or len(values) != 5:
        fail("Vega-Lite candidate must embed the five offline measurements")
    encoding = spec.get("encoding", {})
    if encoding.get("x", {}).get("field") != "load_percent" or encoding.get("y", {}).get("field") != "response_ms":
        fail("Vega-Lite candidate must encode the shared load and response fields")


def check_manuscript():
    reference = (BOOK_ROOT / "reference.qmd").read_text(encoding="utf-8")
    figures = (BOOK_ROOT / "figures.qmd").read_text(encoding="utf-8")
    required = {
        "reference.qmd": (
            reference,
            ("```{mermaid}", "label: fig-half-adder", "fig-alt:", "Diagram description: Inputs A and B"),
        ),
        "figures.qmd": (
            figures,
            (
                "```{dot}",
                "label: fig-build-dependency-graph",
                "fig-alt:",
                "Diagram description: Manuscript source and data/assets",
                "figures/generated/response-time.svg",
                "figures/data/response-time.vl.json",
            ),
        ),
    }
    for name, (text, markers) in required.items():
        for marker in markers:
            if marker not in text:
                fail(name + " is missing graph/chart contract marker: " + marker)


def main():
    check_derivative()
    check_svg()
    check_vega_candidate()
    check_manuscript()
    print("ok: graph/chart specimens (Mermaid flow, Graphviz dependency graph, Vega-Lite candidate, deterministic Python SVG; offline source and derivative contracts)")


if __name__ == "__main__":
    try:
        main()
    except (OSError, RuntimeError) as error:
        print(str(error) if isinstance(error, RuntimeError) else "error: " + str(error), file=sys.stderr)
        sys.exit(1)
