"""Validate computing-diagram data and deterministic portable SVG derivatives."""

import json
import subprocess
import sys
import tempfile
from pathlib import Path

from defusedxml import ElementTree as ET

REPO_ROOT = Path(__file__).resolve().parents[3]
BOOK_ROOT = REPO_ROOT / "book"
DATA_PATH = BOOK_ROOT / "figures" / "data" / "computing-diagrams.json"
GENERATED_DIR = BOOK_ROOT / "figures" / "generated"
CANDIDATE_DIR = BOOK_ROOT / "figures" / "candidates"

OUTPUTS = {
    "read-cycle-timing.svg": {
        "viewbox": "0 0 1000 470",
        "minimum_geometry": 18,
        "markers": ("Synchronous memory read cycle", "CLK", "READ", "ADDR", "DATA", "0x2A", "0xC7"),
    },
    "half-adder-gates.svg": {
        "viewbox": "0 0 1000 390",
        "minimum_geometry": 12,
        "markers": ("Half-adder gate network", "A", "B", "XOR", "AND", "SUM", "CARRY"),
    },
    "memory-instruction-layout.svg": {
        "viewbox": "0 0 1000 540",
        "minimum_geometry": 10,
        "markers": (
            "16-bit address space",
            "ROM",
            "RAM",
            "Memory-mapped I/O",
            "opcode",
            "immediate",
        ),
    },
    "processor-datapath.svg": {
        "viewbox": "0 0 1000 450",
        "minimum_geometry": 25,
        "markers": ("Program", "Instruction", "Decoder", "Register", "ALU", "Data", "next PC"),
    },
}


def fail(message):
    raise RuntimeError("error: " + message)


def load_json(path):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as error:
        fail(f"invalid JSON in {path.relative_to(REPO_ROOT)}: {error}")


def check_data():
    data = load_json(DATA_PATH)
    if data.get("version") != 1:
        fail("computing-diagrams.json must use version 1")
    timing = data.get("timing", {})
    slots = timing.get("slots")
    if not isinstance(slots, int) or slots < 2:
        fail("timing slots must be an integer of at least two")
    names = set()
    for signal in timing.get("signals", []):
        name = signal.get("name")
        if not name or name in names:
            fail("timing signal names must be present and unique")
        names.add(name)
        if signal.get("kind") == "digital" and len(signal.get("values", [])) != slots:
            fail("digital timing values must match the configured slot count")
        if signal.get("kind") == "bus":
            for span in signal.get("spans", []):
                if not (0 <= span.get("start", -1) < span.get("end", -1) <= slots):
                    fail("bus timing spans must be ordered inside the slot range")
        elif signal.get("kind") != "digital":
            fail("timing signals must be digital or bus lanes")
    if names != {"CLK", "READ", "ADDR", "DATA"}:
        fail("timing fixture must exercise clock, control, address, and data lanes")

    layout = data.get("layout", {})
    maximum = 2 ** layout.get("address_bits", 0) - 1
    expected_start = 0
    for region in layout.get("regions", []):
        if region.get("start") != expected_start or region.get("end", -1) < expected_start:
            fail("memory-map regions must be contiguous and ordered")
        expected_start = region["end"] + 1
    if expected_start != maximum + 1:
        fail("memory-map regions must cover the complete address space")
    bits = layout.get("instruction_bits")
    if sum(field.get("width", 0) for field in layout.get("fields", [])) != bits:
        fail("instruction fields must cover the complete instruction word")

    architecture = data.get("architecture", {})
    node_ids = [node.get("id") for node in architecture.get("nodes", [])]
    if not node_ids or len(node_ids) != len(set(node_ids)):
        fail("architecture node IDs must be present and unique")
    for edge in architecture.get("edges", []):
        if edge.get("from") not in node_ids or edge.get("to") not in node_ids:
            fail("architecture edges must reference known nodes")
        if not edge.get("label") or not all(key in edge for key in ("label_x", "label_y")):
            fail("architecture edges require visible labels and explicit label positions")


def check_derivatives():
    with tempfile.TemporaryDirectory(prefix="alkahest-computing.") as directory:
        candidate_dir = Path(directory)
        result = subprocess.run(  # noqa: S603 - fixed generator module
            [
                sys.executable,
                "-m",
                "alkahest.generators.computing",
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
            fail("computing-diagram regeneration failed: " + result.stdout.strip())
        for name in OUTPUTS:
            committed = GENERATED_DIR / name
            candidate = candidate_dir / name
            if not committed.is_file():
                fail("missing generated computing diagram; run make generate-computing-diagrams")
            if candidate.read_bytes() != committed.read_bytes():
                fail(f"generated computing diagram drifted: {name}")


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
        for marker in contract["markers"]:
            if marker not in visible_text:
                fail(f"{name} is missing visible marker: {marker}")
        geometry_count = sum(
            len(root.findall(".//" + namespace + element))
            for element in ("line", "polyline", "path", "rect")
        )
        if geometry_count < contract["minimum_geometry"]:
            fail(f"{name} is missing expected vector geometry")


def check_candidates():
    timing = load_json(CANDIDATE_DIR / "read-cycle-wavedrom.json")
    signals = timing.get("signal", [])
    if [signal.get("name") for signal in signals] != ["CLK", "READ", "ADDR", "DATA"]:
        fail("WaveDrom timing candidate must exercise the selected signal lanes")
    instruction = load_json(CANDIDATE_DIR / "instruction-word-wavedrom.json")
    if instruction.get("config", {}).get("bits") != 16:
        fail("WaveDrom instruction candidate must declare a 16-bit word")
    if sum(field.get("bits", 0) for field in instruction.get("reg", [])) != 16:
        fail("WaveDrom instruction fields must cover the complete word")


def check_manuscript():
    figures = (BOOK_ROOT / "figures.qmd").read_text(encoding="utf-8")
    markers = (
        "#sec-computing-diagram-workflow",
        "#fig-memory-read-cycle",
        "#fig-half-adder-gates",
        "#fig-memory-instruction-layout",
        "#fig-processor-datapath",
        "figures/candidates/read-cycle-wavedrom.json",
        "figures/candidates/instruction-word-wavedrom.json",
    )
    for marker in markers:
        if marker not in figures:
            fail("figures.qmd is missing computing-diagram marker: " + marker)


def main():
    check_data()
    check_derivatives()
    check_svgs()
    check_candidates()
    check_manuscript()
    print(
        "ok: computing diagrams "
        "(timing, logic gates, memory map, instruction fields, and processor datapath; "
        "deterministic accessible SVG; evaluated WaveDrom sources)"
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
