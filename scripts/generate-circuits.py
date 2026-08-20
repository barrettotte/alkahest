"""Generate deterministic portable SVG circuit specimens with Schemdraw."""

import argparse
import re
from pathlib import Path

import schemdraw
import schemdraw.elements as elm


SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parent
DEFAULT_OUTPUT = REPO_ROOT / "book" / "figures" / "generated" / "voltage-divider.svg"

TITLE = "Nine-volt resistive voltage divider"
DESCRIPTION = (
    "A 9 volt DC source feeds a 1 kiloohm upper resistor and a 2 kiloohm "
    "lower resistor in series. The output node is between the resistors, and "
    "the lower rail returns to ground and the negative source terminal."
)


def add_accessibility(svg):
    """Add stable, self-contained accessibility metadata to Schemdraw SVG."""
    match = re.search(r"<svg\b[^>]*>", svg)
    if match is None:
        raise RuntimeError("Schemdraw output has no SVG root")
    root = match.group(0)
    root = root[:-1] + ' role="img" aria-labelledby="title desc">'
    metadata = "\n<title id=\"title\">" + TITLE + "</title>\n<desc id=\"desc\">" + DESCRIPTION + "</desc>"
    return svg[: match.start()] + root + metadata + svg[match.end() :]


def generate(output):
    output.parent.mkdir(parents=True, exist_ok=True)
    schemdraw.use("svg")
    drawing = schemdraw.Drawing(show=False, canvas="svg")
    drawing.config(unit=2.6, fontsize=13, color="#111827", lw=1.7, margin=0.18)

    source = drawing.add(elm.SourceV().up().length(5.2).label("Vₛ = 9 V", loc="top"))
    drawing.add(elm.Line().right().length(3.6))
    upper_resistor = drawing.add(elm.ResistorIEC().down().label("R₁ = 1 kΩ", loc="top"))
    drawing.add(elm.Dot().label("Vout = 6 V", loc="right"))
    drawing.add(elm.ResistorIEC().down().label("R₂ = 2 kΩ", loc="top"))
    drawing.add(elm.Line().left().tox(source.start))
    drawing.add(elm.Ground())
    drawing.add(elm.CurrentLabel().at(upper_resistor).label("I = 3 mA").reverse())

    svg = drawing.get_imagedata("svg").decode("utf-8")
    output.write_text(add_accessibility(svg).rstrip() + "\n", encoding="utf-8")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    generate(args.output.resolve())


if __name__ == "__main__":
    main()
