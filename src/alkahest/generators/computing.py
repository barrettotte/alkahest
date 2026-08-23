"""Generate deterministic portable SVG computing diagrams from versioned JSON."""

import argparse
import json
from html import escape
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_INPUT = REPO_ROOT / "book" / "figures" / "data" / "computing-diagrams.json"
DEFAULT_OUTPUT_DIR = REPO_ROOT / "book" / "figures" / "generated"

INK = "#111827"
MUTED = "#475569"
LIGHT = "#e2e8f0"
PALE = "#f8fafc"


class Svg:
    """Build a small self-contained SVG with stable accessible metadata."""

    def __init__(self, width, height, title, description):
        self.width = width
        self.height = height
        self.items = [
            "<?xml version='1.0' encoding='UTF-8'?>",
            (
                f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {height}" '
                'role="img" aria-labelledby="title desc">'
            ),
            f'<title id="title">{escape(title)}</title>',
            f'<desc id="desc">{escape(description)}</desc>',
            "<defs>",
            '<marker id="arrow" viewBox="0 0 10 10" refX="9" refY="5" '
            'markerWidth="7" markerHeight="7" orient="auto-start-reverse">',
            f'<path d="M 0 0 L 10 5 L 0 10 z" fill="{INK}"/>',
            "</marker>",
            "</defs>",
            f'<rect width="{width}" height="{height}" fill="#ffffff"/>',
        ]

    def line(self, x1, y1, x2, y2, *, stroke=INK, width=2, dash=None, arrow=False):
        attributes = ""
        if dash:
            attributes += f' stroke-dasharray="{dash}"'
        if arrow:
            attributes += ' marker-end="url(#arrow)"'
        self.items.append(
            f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" '
            f'stroke="{stroke}" stroke-width="{width}"{attributes}/>'
        )

    def polyline(self, points, *, stroke=INK, width=2, dash=None, arrow=False, fill="none"):
        coordinates = " ".join(f"{x},{y}" for x, y in points)
        attributes = ""
        if dash:
            attributes += f' stroke-dasharray="{dash}"'
        if arrow:
            attributes += ' marker-end="url(#arrow)"'
        self.items.append(
            f'<polyline points="{coordinates}" fill="{fill}" stroke="{stroke}" '
            f'stroke-width="{width}" stroke-linejoin="round"{attributes}/>'
        )

    def path(self, data, *, stroke=INK, width=2, fill="none", dash=None):
        attributes = f' stroke-dasharray="{dash}"' if dash else ""
        self.items.append(
            f'<path d="{data}" fill="{fill}" stroke="{stroke}" '
            f'stroke-width="{width}" stroke-linejoin="round"{attributes}/>'
        )

    def rect(self, x, y, width, height, *, fill="#ffffff", stroke=INK, radius=0, line_width=2):
        self.items.append(
            f'<rect x="{x}" y="{y}" width="{width}" height="{height}" rx="{radius}" '
            f'fill="{fill}" stroke="{stroke}" stroke-width="{line_width}"/>'
        )

    def text(self, x, y, value, *, size=20, anchor="middle", weight="normal", fill=INK):
        lines = str(value).split("\n")
        self.items.append(
            f'<text x="{x}" y="{y}" text-anchor="{anchor}" font-family="sans-serif" '
            f'font-size="{size}" font-weight="{weight}" fill="{fill}">'
        )
        for index, line in enumerate(lines):
            dy = "0" if index == 0 else str(round(size * 1.15, 1))
            self.items.append(f'<tspan x="{x}" dy="{dy}">{escape(line)}</tspan>')
        self.items.append("</text>")

    def finish(self):
        return "\n".join(self.items + ["</svg>", ""])


def render_timing(specification):
    title = specification["title"]
    description = (
        "Four timing lanes show a clock, an active-high read signal, address 0x2A, "
        "and returned data 0xC7. The address becomes valid before the data."
    )
    svg = Svg(1000, 470, title, description)
    svg.text(500, 38, title, size=25, weight="bold")
    x_start = 190
    slot_width = 88
    slots = specification["slots"]
    y_start = 105
    row_height = 76

    for slot in range(slots + 1):
        x = x_start + slot * slot_width
        svg.line(x, 75, x, 402, stroke=LIGHT, width=1)
        if slot < slots:
            svg.text(x + slot_width / 2, 430, str(slot), size=15, fill=MUTED)

    for row, signal in enumerate(specification["signals"]):
        y = y_start + row * row_height
        svg.text(x_start - 28, y + 8, signal["name"], size=19, anchor="end", weight="bold")
        if signal["kind"] == "digital":
            values = signal["values"]
            if len(values) != slots:
                raise ValueError(f"timing signal {signal['name']} must contain {slots} values")
            high = y - 20
            low = y + 20
            points = []
            for index, value in enumerate(values):
                level = high if value else low
                left = x_start + index * slot_width
                right = left + slot_width
                if points and points[-1][1] != level:
                    points.append((left, points[-1][1]))
                points.extend([(left, level), (right, level)])
            svg.polyline(points, width=3)
        elif signal["kind"] == "bus":
            svg.line(x_start, y, x_start + slots * slot_width, y, stroke=MUTED, width=1, dash="6 5")
            for span in signal["spans"]:
                left = x_start + span["start"] * slot_width
                right = x_start + span["end"] * slot_width
                points = [
                    (left, y),
                    (left + 14, y - 21),
                    (right - 14, y - 21),
                    (right, y),
                    (right - 14, y + 21),
                    (left + 14, y + 21),
                    (left, y),
                ]
                svg.polyline(points, fill=PALE, width=2)
                svg.text((left + right) / 2, y + 7, span["label"], size=18)
        else:
            raise ValueError("unknown timing signal kind: " + signal["kind"])

    for annotation in specification["annotations"]:
        x = x_start + annotation["slot"] * slot_width
        svg.line(x, 62, x, 83, width=1, arrow=True)
        svg.text(x, 55, annotation["label"], size=14, fill=MUTED)
    svg.text(500, 456, "half-cycle slot", size=15, fill=MUTED)
    return svg.finish()


def render_logic(specification):
    title = specification["title"]
    description = (
        "Inputs A and B each branch to an XOR gate producing SUM and an AND gate "
        "producing CARRY."
    )
    svg = Svg(1000, 390, title, description)
    svg.text(500, 40, title, size=25, weight="bold")
    input_positions = {"A": 120, "B": 270}
    gate_inputs = {"sum": (115, 165), "carry": (235, 285)}

    for name, y in input_positions.items():
        svg.text(70, y + 7, name, size=22, weight="bold")
        svg.line(95, y, 250, y, width=3)
        svg.items.append(f'<circle cx="250" cy="{y}" r="5" fill="{INK}"/>')

    for name, source_y in input_positions.items():
        target_sum = gate_inputs["sum"][0 if name == "A" else 1]
        target_carry = gate_inputs["carry"][0 if name == "A" else 1]
        svg.polyline([(250, source_y), (330, source_y), (330, target_sum), (415, target_sum)], width=2)
        svg.polyline([(250, source_y), (295, source_y), (295, target_carry), (420, target_carry)], width=2)

    svg.path("M 430 88 Q 505 88 560 140 Q 505 192 430 192 Q 458 140 430 88 Z", fill=PALE, width=3)
    svg.path("M 418 88 Q 446 140 418 192", width=3)
    svg.text(490, 147, "XOR", size=17, weight="bold")
    svg.line(560, 140, 850, 140, width=3, arrow=True)
    svg.text(890, 147, "SUM", size=20, weight="bold")

    svg.path("M 430 215 L 480 215 A 55 55 0 0 1 480 325 L 430 325 Z", fill=PALE, width=3)
    svg.text(480, 277, "AND", size=17, weight="bold")
    svg.line(535, 270, 850, 270, width=3, arrow=True)
    svg.text(900, 277, "CARRY", size=20, weight="bold")
    return svg.finish()


def render_layout(specification):
    title = specification["title"]
    description = (
        "A sixteen-bit address space is divided into four equal regions: ROM, RAM, "
        "reserved space, and memory-mapped input/output. A sixteen-bit instruction "
        "is divided into opcode, mode, destination, source, and immediate fields."
    )
    svg = Svg(1000, 540, title, description)
    svg.text(500, 40, title, size=25, weight="bold")
    svg.text(245, 82, "16-bit address space", size=20, weight="bold")
    x = 120
    y = 105
    width = 270
    height = 78
    regions = specification["regions"]
    maximum = 2 ** specification["address_bits"] - 1
    expected_start = 0
    for index, region in enumerate(regions):
        if region["start"] != expected_start or region["end"] < region["start"]:
            raise ValueError("memory regions must be contiguous and ordered")
        fill = PALE if index % 2 == 0 else "#eef2f7"
        top = y + index * height
        svg.rect(x, top, width, height, fill=fill, line_width=2)
        svg.text(x + width / 2, top + 35, region["name"], size=18, weight="bold")
        svg.text(
            x + width / 2,
            top + 61,
            f"0x{region['start']:04X}–0x{region['end']:04X}",
            size=18,
            fill=MUTED,
        )
        expected_start = region["end"] + 1
    if expected_start != maximum + 1:
        raise ValueError("memory regions must cover the complete address space")

    fields = specification["fields"]
    bits = specification["instruction_bits"]
    if sum(field["width"] for field in fields) != bits:
        raise ValueError("instruction field widths must sum to instruction_bits")
    svg.text(720, 120, "16-bit instruction word", size=20, weight="bold")
    left = 495
    top = 165
    total_width = 450
    field_height = 105
    bit_cursor = bits - 1
    for index, field in enumerate(fields):
        field_width = total_width * field["width"] / bits
        fill = PALE if index % 2 == 0 else "#eef2f7"
        svg.rect(left, top, field_width, field_height, fill=fill, line_width=2)
        svg.text(left + field_width / 2, top + 48, field["name"], size=19, weight="bold")
        low_bit = bit_cursor - field["width"] + 1
        bit_label = str(bit_cursor) if bit_cursor == low_bit else f"{bit_cursor}:{low_bit}"
        svg.text(left + field_width / 2, top + 79, bit_label, size=17, fill=MUTED)
        left += field_width
        bit_cursor = low_bit - 1
    svg.text(720, 310, "field width follows bit count", size=15, fill=MUTED)
    svg.text(500, 505, "Addresses and bit positions are explicit; area carries no semantic meaning alone.", size=16, fill=MUTED)
    return svg.finish()


def edge_points(source, target, route, route_index):
    source_right = (source["x"] + source["width"], source["y"] + source["height"] / 2)
    target_left = (target["x"], target["y"] + target["height"] / 2)
    if route == "bottom":
        route_y = 310 + route_index * 42
        return [
            (source["x"] + source["width"] / 2, source["y"] + source["height"]),
            (source["x"] + source["width"] / 2, route_y),
            (target["x"] + target["width"] / 2, route_y),
            (target["x"] + target["width"] / 2, target["y"] + target["height"]),
        ]
    if route == "control-right":
        return [
            (source["x"] + source["width"], source["y"] + source["height"] / 2),
            (565, source["y"] + source["height"] / 2),
            (565, target["y"] + target["height"] / 2),
            (target["x"], target["y"] + target["height"] / 2),
        ]
    if source["x"] == target["x"]:
        return [
            (source["x"] + source["width"] / 2, source["y"] + source["height"]),
            (target["x"] + target["width"] / 2, target["y"]),
        ]
    middle_x = (source_right[0] + target_left[0]) / 2
    return [source_right, (middle_x, source_right[1]), (middle_x, target_left[1]), target_left]


def render_architecture(specification):
    title = specification["title"]
    description = (
        "A program counter addresses instruction memory. Instruction fields feed "
        "decode and the register file; control selects registers and the ALU operation. "
        "The ALU accesses data memory, with load data and next-PC feedback paths."
    )
    svg = Svg(1000, 450, title, description)
    svg.text(500, 34, title, size=25, weight="bold")
    nodes = {node["id"]: node for node in specification["nodes"]}
    bottom_route_index = 0
    for edge in specification["edges"]:
        if edge["from"] not in nodes or edge["to"] not in nodes:
            raise ValueError("architecture edge references an unknown node")
        route = edge.get("route")
        points = edge_points(nodes[edge["from"]], nodes[edge["to"]], route, bottom_route_index)
        if route == "bottom":
            bottom_route_index += 1
        control = edge.get("kind") == "control"
        svg.polyline(points, width=2, dash="7 5" if control else None, arrow=True)
        label_width = max(46, len(edge["label"]) * 9 + 12)
        svg.rect(
            edge["label_x"] - label_width / 2,
            edge["label_y"] - 14,
            label_width,
            18,
            fill="#ffffff",
            stroke="#ffffff",
            line_width=0,
        )
        svg.text(edge["label_x"], edge["label_y"], edge["label"], size=18, fill=MUTED)

    for node in specification["nodes"]:
        svg.rect(node["x"], node["y"], node["width"], node["height"], fill=PALE, radius=8, line_width=2)
        line_count = len(node["label"].split("\n"))
        baseline = node["y"] + node["height"] / 2 - (9 if line_count > 1 else -6)
        svg.text(node["x"] + node["width"] / 2, baseline, node["label"], size=20, weight="bold")
    svg.text(500, 434, "solid = data/address path · dashed = control path", size=17, fill=MUTED)
    return svg.finish()


def load_specification(path):
    data = json.loads(path.read_text(encoding="utf-8"))
    if data.get("version") != 1:
        raise ValueError("computing diagram specification must use version 1")
    for key in ("timing", "logic", "layout", "architecture"):
        if key not in data:
            raise ValueError("computing diagram specification is missing: " + key)
    return data


def generate(input_path, output_dir):
    specification = load_specification(input_path)
    output_dir.mkdir(parents=True, exist_ok=True)
    outputs = {
        "read-cycle-timing.svg": render_timing(specification["timing"]),
        "half-adder-gates.svg": render_logic(specification["logic"]),
        "memory-instruction-layout.svg": render_layout(specification["layout"]),
        "processor-datapath.svg": render_architecture(specification["architecture"]),
    }
    for name, content in outputs.items():
        (output_dir / name).write_text(content, encoding="utf-8")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    args = parser.parse_args()
    generate(args.input.resolve(), args.output_dir.resolve())


if __name__ == "__main__":
    main()
