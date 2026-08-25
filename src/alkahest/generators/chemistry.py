"""Generate a deterministic portable SVG chemistry reaction with RDKit."""

import argparse
import re
from pathlib import Path
from typing import Any

from rdkit import Chem
from rdkit.Chem import rdChemReactions, rdDepictor
from rdkit.Chem.Draw import rdMolDraw2D

REPO_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_OUTPUT = REPO_ROOT / "book" / "figures" / "generated" / "fischer-esterification.svg"

REACTION_SMILES = "CC(=O)O.CCO>>CCOC(=O)C.[OH2]"
TITLE = "Fischer esterification reaction"
DESCRIPTION = (
    "Skeletal structures show acetic acid plus ethanol yielding ethyl acetate "
    "plus water, from left to right across a reaction arrow."
)


def add_accessibility(svg):
    """Add stable accessibility metadata to the generated SVG root."""
    svg = re.sub(
        r"^<\?xml[^?]*\?>",
        "<?xml version='1.0' encoding='UTF-8'?>",
        svg,
        count=1,
    )
    match = re.search(r"<svg\b[^>]*>", svg)
    if match is None:
        raise RuntimeError("RDKit output has no SVG root")
    root = re.sub(r"\s+(?:role|aria-labelledby)=(['\"]).*?\1", "", match.group(0))
    root = root[:-1] + ' role="img" aria-labelledby="title desc">'
    metadata = (
        '\n<title id="title">' + TITLE + '</title>\n<desc id="desc">' + DESCRIPTION + "</desc>"
    )
    return svg[: match.start()] + root + metadata + svg[match.end() :]


def prepare_reaction():
    """Parse the locked reaction and calculate stable two-dimensional coordinates."""
    reaction = rdChemReactions.ReactionFromSmarts(REACTION_SMILES, useSmiles=True)
    if reaction is None:
        raise RuntimeError("RDKit could not parse the reaction SMILES")
    for molecule in list(reaction.GetReactants()) + list(reaction.GetProducts()):
        Chem.SanitizeMol(molecule)
        rdDepictor.Compute2DCoords(molecule, canonOrient=True)
    return reaction


def generate(output):
    """Render the reaction to a self-contained monochrome SVG."""
    output.parent.mkdir(parents=True, exist_ok=True)
    drawer = rdMolDraw2D.MolDraw2DSVG(1000, 260)
    options: Any = drawer.drawOptions()
    options.useBWAtomPalette()
    options.bondLineWidth = 2.0
    options.padding = 0.08
    drawer.DrawReaction(prepare_reaction())
    drawer.FinishDrawing()
    svg = drawer.GetDrawingText()
    output.write_text(add_accessibility(svg).rstrip() + "\n", encoding="utf-8")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    generate(args.output.resolve())


if __name__ == "__main__":
    main()
