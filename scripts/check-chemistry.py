"""Validate chemistry sources and the deterministic portable SVG derivative."""

import subprocess
import sys
import tempfile
import xml.etree.ElementTree as ET
from pathlib import Path

from rdkit import rdBase


SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parent
BOOK_ROOT = REPO_ROOT / "book"
SVG_PATH = BOOK_ROOT / "figures" / "generated" / "fischer-esterification.svg"
CHEMFIG_PATH = BOOK_ROOT / "figures" / "candidates" / "fischer-esterification-chemfig.tex"
TYPED_SMILES_PATH = (
    BOOK_ROOT / "figures" / "candidates" / "fischer-esterification-typed-smiles.typ"
)


def fail(message):
    raise RuntimeError("error: " + message)


def check_runtime():
    if rdBase.rdkitVersion != "2026.03.5":
        fail("expected RDKit 2026.03.5, found " + rdBase.rdkitVersion)


def check_derivative():
    if not SVG_PATH.is_file():
        fail("missing generated chemistry diagram; run make generate-chemistry")
    with tempfile.TemporaryDirectory(prefix="alkahest-chemistry.") as directory:
        candidate = Path(directory) / "fischer-esterification.svg"
        result = subprocess.run(
            [sys.executable, str(SCRIPT_DIR / "generate-chemistry.py"), "--output", str(candidate)],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            encoding="utf-8",
        )
        if result.returncode != 0:
            fail("chemistry regeneration failed: " + result.stdout.strip())
        if candidate.read_bytes() != SVG_PATH.read_bytes():
            fail("generated chemistry diagram drifted; regenerate and review the derivative")


def check_svg():
    text = SVG_PATH.read_text(encoding="utf-8")
    if not text.startswith("<?xml version='1.0' encoding='UTF-8'?>\n"):
        fail("generated chemistry diagram must declare EPUB-compatible UTF-8 XML")
    lowered = text.lower()
    if "<script" in lowered or "<image" in lowered or "href=" in lowered:
        fail("generated chemistry diagram must be self-contained and script-free")
    try:
        root = ET.fromstring(text)
    except ET.ParseError as error:
        fail("generated chemistry diagram is invalid SVG: " + str(error))
    if root.get("role") != "img" or root.get("aria-labelledby") != "title desc":
        fail("generated chemistry diagram must declare an accessible image name")
    if root.get("viewBox") != "0 0 1000 260":
        fail("generated chemistry diagram must retain its reviewed fixed viewBox")
    namespace = "{http://www.w3.org/2000/svg}"
    title = root.find(namespace + "title")
    description = root.find(namespace + "desc")
    if title is None or title.get("id") != "title" or title.text != "Fischer esterification reaction":
        fail("generated chemistry diagram has an unexpected accessibility title")
    if description is None or description.get("id") != "desc" or not description.text:
        fail("generated chemistry diagram must contain an accessibility description")
    paths = root.findall(".//" + namespace + "path")
    if len(paths) < 25:
        fail("generated chemistry diagram is missing expected vector geometry")
    classes = " ".join(element.get("class", "") for element in paths)
    for marker in ("bond-0", "atom-2", "atom-3"):
        if marker not in classes:
            fail("generated chemistry diagram is missing RDKit geometry marker: " + marker)


def check_candidates():
    chemfig = CHEMFIG_PATH.read_text(encoding="utf-8")
    for marker in ("\\usepackage{chemfig}", "\\schemestart", "CH_3-CH_2-OH", "H_2O"):
        if marker not in chemfig:
            fail("Chemfig candidate is missing contract marker: " + marker)
    typed_smiles = TYPED_SMILES_PATH.read_text(encoding="utf-8")
    for marker in (
        '#import "@preview/typed-smiles:0.10.0"',
        'smiles("CC(=O)O")',
        'smiles("CCO")',
        'smiles("CCOC(=O)C")',
        'ce("H2O")',
    ):
        if marker not in typed_smiles:
            fail("typed-smiles candidate is missing contract marker: " + marker)


def check_manuscript():
    figures = (BOOK_ROOT / "figures.qmd").read_text(encoding="utf-8")
    for marker in (
        "#sec-chemistry-workflow-evaluation",
        "#fig-fischer-esterification",
        'fig-pos="H"',
        "figures/generated/fischer-esterification.svg",
        "figures/candidates/fischer-esterification-chemfig.tex",
        "figures/candidates/fischer-esterification-typed-smiles.typ",
    ):
        if marker not in figures:
            fail("figures.qmd is missing chemistry contract marker: " + marker)


def main():
    check_runtime()
    check_derivative()
    check_svg()
    check_candidates()
    check_manuscript()
    print(
        "ok: chemistry specimen "
        "(RDKit 2026.03.5; deterministic accessible SVG; evaluated Chemfig and typed-smiles)"
    )


if __name__ == "__main__":
    try:
        main()
    except (OSError, RuntimeError, ValueError) as error:
        print(str(error) if isinstance(error, RuntimeError) else "error: " + str(error), file=sys.stderr)
        sys.exit(1)
