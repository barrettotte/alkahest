"""Generate deterministic portable SVG physics diagrams from versioned JSON."""

import argparse
import json
import math
from html import escape
from pathlib import Path


SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parent
DEFAULT_INPUT = REPO_ROOT / "book" / "figures" / "data" / "physics-diagrams.json"
DEFAULT_OUTPUT_DIR = REPO_ROOT / "book" / "figures" / "generated"

INK = "#111827"
MUTED = "#475569"
LIGHT = "#cbd5e1"
PALE = "#f8fafc"


def number(value):
    """Format computed coordinates without platform-sensitive excess precision."""
    if abs(value - round(value)) < 0.000_001:
        return str(int(round(value)))
    return f"{value:.2f}".rstrip("0").rstrip(".")


class Svg:
    """Build a self-contained SVG with stable accessible metadata."""

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
            '<marker id="small-arrow" viewBox="0 0 10 10" refX="9" refY="5" '
            'markerWidth="5" markerHeight="5" orient="auto-start-reverse">',
            f'<path d="M 0 0 L 10 5 L 0 10 z" fill="{INK}"/>',
            "</marker>",
            "</defs>",
            f'<rect width="{width}" height="{height}" fill="#ffffff"/>',
        ]

    def line(self, x1, y1, x2, y2, *, stroke=INK, width=2, dash=None, arrow=None):
        attributes = f' stroke-dasharray="{dash}"' if dash else ""
        if arrow:
            attributes += f' marker-end="url(#{arrow})"'
        self.items.append(
            f'<line x1="{number(x1)}" y1="{number(y1)}" '
            f'x2="{number(x2)}" y2="{number(y2)}" stroke="{stroke}" '
            f'stroke-width="{number(width)}"{attributes}/>'
        )

    def path(self, data, *, stroke=INK, width=2, fill="none", dash=None):
        attributes = f' stroke-dasharray="{dash}"' if dash else ""
        self.items.append(
            f'<path d="{data}" fill="{fill}" stroke="{stroke}" '
            f'stroke-width="{number(width)}"{attributes}/>'
        )

    def circle(self, x, y, radius, *, fill="#ffffff", stroke=INK, width=2):
        self.items.append(
            f'<circle cx="{number(x)}" cy="{number(y)}" r="{number(radius)}" '
            f'fill="{fill}" stroke="{stroke}" stroke-width="{number(width)}"/>'
        )

    def text(self, x, y, value, *, size=20, anchor="middle", weight="normal", fill=INK):
        self.items.append(
            f'<text x="{number(x)}" y="{number(y)}" text-anchor="{anchor}" '
            f'font-family="sans-serif" font-size="{size}" font-weight="{weight}" '
            f'fill="{fill}">{escape(str(value))}</text>'
        )

    def finish(self):
        return "\n".join(self.items + ["</svg>", ""])


def unit_symbol(data, measurement):
    return data["units"][measurement["unit"]]["symbol"]


def render_vector(data):
    specification = data["vector"]
    components = specification["components"]
    derived = specification["derived"]
    x_value = components["x"]["value"]
    y_value = components["y"]["value"]
    title = specification["title"]
    description = (
        "A velocity vector points up and right. Dashed projections label its horizontal "
        "component as 20.0 meters per second and vertical component as 15.0 meters per "
        "second; the magnitude is 25.0 meters per second at 36.9 degrees."
    )
    svg = Svg(1000, 540, title, description)
    svg.text(500, 40, title, size=26, weight="bold")

    origin_x = 170
    origin_y = 430
    scale = 22
    tip_x = origin_x + x_value * scale
    tip_y = origin_y - y_value * scale
    svg.line(105, origin_y, 890, origin_y, width=2, arrow="arrow")
    svg.line(origin_x, 475, origin_x, 75, width=2, arrow="arrow")
    svg.text(975, origin_y + 8, "v_x (m/s)", size=24, anchor="end")
    svg.text(origin_x - 8, 65, "v_y (m/s)", size=24, anchor="end")

    for tick in range(5, 31, 5):
        x = origin_x + tick * scale
        svg.line(x, origin_y - 6, x, origin_y + 6, width=1)
        svg.text(x, origin_y + 31, str(tick), size=20, fill=MUTED)
    for tick in range(5, 16, 5):
        y = origin_y - tick * scale
        svg.line(origin_x - 6, y, origin_x + 6, y, width=1)
        svg.text(origin_x - 14, y + 7, str(tick), size=20, anchor="end", fill=MUTED)

    svg.line(origin_x, tip_y, tip_x, tip_y, stroke=MUTED, width=2, dash="8 6")
    svg.line(tip_x, origin_y, tip_x, tip_y, stroke=MUTED, width=2, dash="8 6")
    svg.line(origin_x, origin_y, tip_x, tip_y, width=4, arrow="arrow")

    velocity_unit = unit_symbol(data, components["x"])
    angle_unit = data["units"][derived["angle"]["unit"]]["symbol"]
    svg.text((origin_x + tip_x) / 2, tip_y - 19, f"v_x = {components['x']['display']} {velocity_unit}", size=24)
    svg.text(tip_x + 18, (origin_y + tip_y) / 2, f"v_y = {components['y']['display']} {velocity_unit}", size=24, anchor="start")
    svg.text(385, 170, f"|v| = {derived['magnitude']['display']} {velocity_unit}", size=26, weight="bold")

    angle = math.atan2(y_value, x_value)
    radius = 78
    arc_start_x = origin_x + radius
    arc_end_x = origin_x + radius * math.cos(angle)
    arc_end_y = origin_y - radius * math.sin(angle)
    svg.path(
        f"M {number(arc_start_x)} {number(origin_y)} A {radius} {radius} 0 0 0 "
        f"{number(arc_end_x)} {number(arc_end_y)}",
        width=2,
    )
    svg.text(origin_x + 120, origin_y - 48, f"theta = {derived['angle']['display']}{angle_unit}", size=22)
    svg.text(500, 510, "Displayed precision is preserved explicitly in the versioned source.", size=20, fill=MUTED)
    return svg.finish()


def field_samples(specification):
    step = specification["step"]["value"]
    x_count = round((specification["x_max"] - specification["x_min"]) / step)
    y_count = round((specification["y_max"] - specification["y_min"]) / step)
    for y_index in range(y_count + 1):
        y = specification["y_min"] + y_index * step
        for x_index in range(x_count + 1):
            x = specification["x_min"] + x_index * step
            radius = math.hypot(x, y)
            if radius <= specification["exclusion_radius"]["value"]:
                continue
            yield x, y, radius


def render_field(data):
    specification = data["field"]
    title = specification["title"]
    description = (
        "Twenty-four arrows sampled on a one-meter grid point inward toward an "
        "excluded central source. Arrow length and line weight show inverse-square "
        "relative field strength, with no color encoding."
    )
    svg = Svg(1000, 620, title, description)
    svg.text(500, 36, title, size=26, weight="bold")
    left = 210
    top = 105
    plot_size = 430
    x_span = specification["x_max"] - specification["x_min"]
    y_span = specification["y_max"] - specification["y_min"]

    def map_x(value):
        return left + (value - specification["x_min"]) / x_span * plot_size

    def map_y(value):
        return top + (specification["y_max"] - value) / y_span * plot_size

    for tick in range(-2, 3):
        x = map_x(tick)
        y = map_y(tick)
        svg.line(x, top, x, top + plot_size, stroke=LIGHT, width=1)
        svg.line(left, y, left + plot_size, y, stroke=LIGHT, width=1)
        svg.text(x, top + plot_size + 28, str(tick), size=20, fill=MUTED)
        svg.text(left - 15, y + 7, str(tick), size=20, anchor="end", fill=MUTED)

    svg.line(left, map_y(0), left + plot_size + 35, map_y(0), width=2, arrow="arrow")
    svg.line(map_x(0), top + plot_size, map_x(0), top - 25, width=2, arrow="arrow")
    svg.text(left + plot_size + 50, map_y(0) + 8, "x (m)", size=24, anchor="start")
    svg.text(map_x(0) - 8, top - 38, "y (m)", size=24, anchor="end")

    reference_radius = specification["reference_radius"]["value"]
    for x, y, radius in field_samples(specification):
        strength = (reference_radius / radius) ** 2
        length = 12 + 30 * min(strength, 1)
        half = length / 2
        direction_x = -x / radius
        direction_y = -y / radius
        center_x = map_x(x)
        center_y = map_y(y)
        start_x = center_x - direction_x * half
        start_y = center_y + direction_y * half
        end_x = center_x + direction_x * half
        end_y = center_y - direction_y * half
        svg.line(
            start_x,
            start_y,
            end_x,
            end_y,
            width=1.4 + 1.8 * min(strength, 1),
            arrow="small-arrow",
        )

    svg.circle(map_x(0), map_y(0), 13, fill=PALE, width=3)
    svg.text(map_x(0), map_y(0) + 7, "S", size=20, weight="bold")
    svg.text(800, 150, "Model", size=26, weight="bold")
    svg.text(800, 185, "g/g_ref = (r_ref/r)^2", size=22)
    svg.text(800, 225, f"r_ref = {specification['reference_radius']['display']} m", size=22)
    svg.text(800, 260, f"grid = {specification['step']['display']} m", size=22)
    svg.text(800, 295, f"exclude r <= {specification['exclusion_radius']['display']} m", size=22)
    svg.line(730, 350, 780, 350, width=3.2, arrow="small-arrow")
    svg.text(800, 357, "stronger", size=21, anchor="start")
    svg.line(730, 390, 756, 390, width=1.7, arrow="small-arrow")
    svg.text(800, 397, "weaker", size=21, anchor="start")
    svg.text(500, 580, "Arrow direction and geometry carry meaning; color does not.", size=20, fill=MUTED)
    return svg.finish()


def generate(input_path, output_dir):
    data = json.loads(input_path.read_text(encoding="utf-8"))
    output_dir.mkdir(parents=True, exist_ok=True)
    outputs = {
        "velocity-vector.svg": render_vector(data),
        "inverse-square-field.svg": render_field(data),
    }
    for name, content in outputs.items():
        (output_dir / name).write_text(content, encoding="utf-8")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    arguments = parser.parse_args()
    generate(arguments.input, arguments.output_dir)


if __name__ == "__main__":
    main()
