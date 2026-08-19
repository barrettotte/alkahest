"""Generate deterministic SVG chart specimens from versioned source data."""

import argparse
import csv
from pathlib import Path


SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parent
DEFAULT_DATA = REPO_ROOT / "book" / "figures" / "data" / "response-time.csv"
DEFAULT_OUTPUT = REPO_ROOT / "book" / "figures" / "generated" / "response-time.svg"


def load_rows(path):
    with path.open(encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        if reader.fieldnames != ["load_percent", "response_ms"]:
            raise RuntimeError("response-time CSV must have load_percent,response_ms columns")
        rows = []
        for number, row in enumerate(reader, 2):
            try:
                load = int(row["load_percent"])
                response = int(row["response_ms"])
            except (TypeError, ValueError):
                raise RuntimeError("response-time CSV row " + str(number) + " must contain integers")
            if not 0 <= load <= 100 or not 0 <= response <= 80:
                raise RuntimeError("response-time CSV row " + str(number) + " is outside the chart domain")
            rows.append((load, response))
    if len(rows) < 2 or rows != sorted(rows) or len({load for load, _ in rows}) != len(rows):
        raise RuntimeError("response-time CSV loads must be unique, sorted, and contain at least two rows")
    return rows


def render_svg(rows):
    left, top, width, height = 110, 45, 620, 330

    def x_position(value):
        return left + value * width / 100

    def y_position(value):
        return top + height - value * height / 80

    lines = [
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 800 460" role="img" aria-labelledby="title desc">',
        '  <title id="title">Response time by system load</title>',
        '  <desc id="desc">A line chart with five measured points. Response time rises from 18 milliseconds at zero percent load to 71 milliseconds at full load, with the steepest increase above 75 percent.</desc>',
        '  <metadata>Generated deterministically from figures/data/response-time.csv by scripts/generate-graphs.py; original Alkahest fixture, CC0 1.0.</metadata>',
        '  <rect width="800" height="460" fill="#ffffff"/>',
        '  <g font-family="Libertinus Sans, sans-serif" font-size="16" fill="#20262e">',
    ]
    for tick in range(0, 81, 20):
        y = y_position(tick)
        lines.append('    <line x1="110" y1="{:.1f}" x2="730" y2="{:.1f}" stroke="#c5cbd3" stroke-width="1"/>'.format(y, y))
        lines.append('    <text x="94" y="{:.1f}" text-anchor="end" dominant-baseline="middle">{}</text>'.format(y, tick))
    for tick in range(0, 101, 25):
        x = x_position(tick)
        lines.append('    <line x1="{:.1f}" y1="375" x2="{:.1f}" y2="382" stroke="#20262e" stroke-width="2"/>'.format(x, x))
        lines.append('    <text x="{:.1f}" y="407" text-anchor="middle">{}</text>'.format(x, tick))
    points = " ".join("{:.1f},{:.1f}".format(x_position(load), y_position(response)) for load, response in rows)
    lines.extend(
        [
            '    <line x1="110" y1="45" x2="110" y2="375" stroke="#20262e" stroke-width="2"/>',
            '    <line x1="110" y1="375" x2="730" y2="375" stroke="#20262e" stroke-width="2"/>',
            '    <polyline points="{}" fill="none" stroke="#1f5d8f" stroke-width="5" stroke-linejoin="round" stroke-linecap="round"/>'.format(points),
        ]
    )
    for load, response in rows:
        lines.append('    <circle cx="{:.1f}" cy="{:.1f}" r="7" fill="#ffffff" stroke="#1f5d8f" stroke-width="4"/>'.format(x_position(load), y_position(response)))
    lines.extend(
        [
            '    <text x="420" y="446" text-anchor="middle" font-weight="700">System load (%)</text>',
            '    <text x="28" y="210" text-anchor="middle" font-weight="700" transform="rotate(-90 28 210)">Response time (ms)</text>',
            '  </g>',
            '</svg>',
            '',
        ]
    )
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--data", type=Path, default=DEFAULT_DATA)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    arguments = parser.parse_args()
    output = arguments.output.resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(render_svg(load_rows(arguments.data.resolve())), encoding="utf-8")
    print("generated " + str(output))


if __name__ == "__main__":
    try:
        main()
    except (OSError, RuntimeError) as error:
        raise SystemExit("error: " + str(error))
