"""Inspect rendered PDFs against the repository's print-preflight policy."""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Never

from defusedxml import ElementTree as ET

from .process import run_process

BOX_NAMES = ("MediaBox", "CropBox", "BleedBox", "TrimBox", "ArtBox")
FONT_ROW = re.compile(
    r"^(?P<name>\S+)\s+.+\s+(?P<embedded>yes|no)\s+"
    r"(?P<subset>yes|no)\s+(?P<unicode>yes|no)\s+\d+\s+\d+$"
)
PAGE_BOX = re.compile(
    r"^Page\s+(?P<page>\d+)\s+"
    r"(?P<box>MediaBox|CropBox|BleedBox|TrimBox|ArtBox):\s+"
    r"(?P<x0>-?[\d.]+)\s+(?P<y0>-?[\d.]+)\s+"
    r"(?P<x1>-?[\d.]+)\s+(?P<y1>-?[\d.]+)$"
)
PAGE_ROTATION = re.compile(r"^Page\s+(?P<page>\d+)\s+rot:\s+(?P<rotation>-?\d+)$")
PAGE_SIZE = re.compile(
    r"^Page\s+(?P<page>\d+)\s+size:\s+"
    r"(?P<width>[\d.]+)\s+x\s+(?P<height>[\d.]+)\s+pts"
    r"(?:\s+\(.+\))?$"
)


class PreflightError(RuntimeError):
    """Report a PDF that violates the configured preflight contract."""


@dataclass(frozen=True)
class RasterImage:
    """A raster-image row reported by Poppler's pdfimages utility."""

    page: int
    number: int
    image_type: str
    width: int
    height: int
    color: str
    components: int
    bits_per_component: int
    encoding: str
    interpolated: bool
    object_number: int
    object_generation: int
    x_ppi: float
    y_ppi: float


def fail(message: str) -> Never:
    raise PreflightError(message)


def metadata_value(output: str, name: str) -> str:
    prefix = f"{name}:"
    for line in output.splitlines():
        if line.startswith(prefix):
            return line[len(prefix) :].strip()
    fail(f"pdfinfo did not report {name}")


def validate_document_metadata(output: str, allowed_versions: set[str]) -> int:
    """Validate document-level PDF facts and return the page count."""

    try:
        pages = int(metadata_value(output, "Pages"))
    except ValueError:
        fail("pdfinfo reported a nonnumeric page count")
    if pages < 1:
        fail("PDF must contain at least one page")
    if metadata_value(output, "Encrypted") != "no":
        fail("PDF must not be encrypted")
    if metadata_value(output, "JavaScript") != "no":
        fail("PDF must not contain JavaScript")
    version = metadata_value(output, "PDF version")
    if version not in allowed_versions:
        fail(
            f"PDF version {version} is outside the allowed set: "
            f"{', '.join(sorted(allowed_versions))}"
        )
    return pages


def close_enough(actual: float, expected: float, tolerance: float) -> bool:
    return abs(actual - expected) <= tolerance


def validate_page_boxes(
    output: str,
    page_count: int,
    trim_width: float,
    trim_height: float,
    bleed_points: float,
    tolerance: float,
    sampled_box_pages: set[int] | None = None,
) -> None:
    """Validate every page size/rotation and sampled explicit page boxes."""

    boxes: dict[int, dict[str, tuple[float, float, float, float]]] = {}
    rotations: dict[int, int] = {}
    sizes: dict[int, tuple[float, float]] = {}
    for line in output.splitlines():
        box_match = PAGE_BOX.match(line.strip())
        if box_match:
            values = (
                float(box_match.group("x0")),
                float(box_match.group("y0")),
                float(box_match.group("x1")),
                float(box_match.group("y1")),
            )
            boxes.setdefault(int(box_match.group("page")), {})[box_match.group("box")] = values
            continue
        rotation_match = PAGE_ROTATION.match(line.strip())
        if rotation_match:
            rotations[int(rotation_match.group("page"))] = int(rotation_match.group("rotation"))
            continue
        size_match = PAGE_SIZE.match(line.strip())
        if size_match:
            sizes[int(size_match.group("page"))] = (
                float(size_match.group("width")),
                float(size_match.group("height")),
            )

    expected_pages = set(range(1, page_count + 1))
    box_pages = sampled_box_pages if sampled_box_pages is not None else expected_pages
    if set(boxes) != box_pages:
        missing = sorted(box_pages - set(boxes))
        fail(f"pdfinfo omitted page-box data for pages {missing}")
    if set(rotations) != expected_pages:
        missing = sorted(expected_pages - set(rotations))
        fail(f"pdfinfo omitted rotation data for pages {missing}")
    if set(sizes) != expected_pages:
        missing = sorted(expected_pages - set(sizes))
        fail(f"pdfinfo omitted page-size data for pages {missing}")

    media = (0.0, 0.0, trim_width + 2 * bleed_points, trim_height + 2 * bleed_points)
    trim = (
        bleed_points,
        bleed_points,
        bleed_points + trim_width,
        bleed_points + trim_height,
    )
    expected_boxes = {
        "MediaBox": media,
        "CropBox": media,
        "BleedBox": media,
        "TrimBox": trim,
        "ArtBox": trim,
    }

    for page in sorted(expected_pages):
        if rotations[page] != 0:
            fail(f"page {page} has unsupported rotation {rotations[page]}")
        expected_size = (media[2] - media[0], media[3] - media[1])
        if not all(
            close_enough(actual, expected, tolerance)
            for actual, expected in zip(sizes[page], expected_size, strict=True)
        ):
            fail(
                f"page {page} is {sizes[page][0]} x {sizes[page][1]} points; "
                f"expected {expected_size[0]} x {expected_size[1]}"
            )

    for page in sorted(box_pages):
        if set(boxes[page]) != set(BOX_NAMES):
            missing_boxes = sorted(set(BOX_NAMES) - set(boxes[page]))
            fail(f"page {page} omits required boxes: {', '.join(missing_boxes)}")
        for box_name, expected in expected_boxes.items():
            actual = boxes[page][box_name]
            if not all(
                close_enough(actual_value, expected_value, tolerance)
                for actual_value, expected_value in zip(actual, expected, strict=True)
            ):
                fail(
                    f"page {page} {box_name} is {actual}; expected {expected} "
                    f"within {tolerance} point"
                )


def parse_font_rows(output: str) -> list[tuple[str, bool, bool]]:
    rows: list[tuple[str, bool, bool]] = []
    for line in output.splitlines()[2:]:
        if not line.strip():
            continue
        match = FONT_ROW.match(line.strip())
        if not match:
            fail(f"could not parse pdffonts row: {line.strip()}")
        rows.append(
            (
                match.group("name"),
                match.group("embedded") == "yes",
                match.group("subset") == "yes",
            )
        )
    if not rows:
        fail("PDF does not report any fonts")
    return rows


def validate_fonts(output: str) -> int:
    """Require every reported face to be embedded and subset."""

    rows = parse_font_rows(output)
    for name, embedded, subset in rows:
        if not embedded:
            fail(f"font {name} is not embedded")
        if not subset:
            fail(f"font {name} is embedded but not subset")
    return len(rows)


def parse_raster_images(output: str) -> list[RasterImage]:
    rows: list[RasterImage] = []
    for line in output.splitlines()[2:]:
        fields = line.split()
        if not fields:
            continue
        if len(fields) < 16:
            fail(f"could not parse pdfimages row: {line.strip()}")
        try:
            rows.append(
                RasterImage(
                    page=int(fields[0]),
                    number=int(fields[1]),
                    image_type=fields[2].lower(),
                    width=int(fields[3]),
                    height=int(fields[4]),
                    color=fields[5].lower(),
                    components=int(fields[6]),
                    bits_per_component=int(fields[7]),
                    encoding=fields[8].lower(),
                    interpolated=fields[9].lower() == "yes",
                    object_number=int(fields[10]),
                    object_generation=int(fields[11]),
                    x_ppi=float(fields[12]),
                    y_ppi=float(fields[13]),
                )
            )
        except ValueError as error:
            fail(f"could not parse pdfimages row: {line.strip()} ({error})")
    return rows


def validate_raster_images(
    output: str,
    allowed_color_models: set[tuple[str, int]],
    continuous_tone_minimum_ppi: float,
    one_bit_minimum_ppi: float,
) -> int:
    """Validate color models and effective resolution of primary raster images."""

    images = [image for image in parse_raster_images(output) if image.image_type == "image"]
    for image in images:
        identity = f"page {image.page}, object {image.object_number} {image.object_generation}"
        color_model = (image.color, image.components)
        if color_model not in allowed_color_models:
            fail(
                f"raster image at {identity} uses disallowed color model "
                f"{image.color}/{image.components}"
            )
        one_bit = image.color == "mono" or image.bits_per_component == 1
        minimum = one_bit_minimum_ppi if one_bit else continuous_tone_minimum_ppi
        effective = min(image.x_ppi, image.y_ppi)
        if effective < minimum:
            kind = "one-bit" if one_bit else "continuous-tone"
            fail(
                f"{kind} raster image at {identity} is "
                f"{image.x_ppi:g} x {image.y_ppi:g} PPI; minimum is {minimum:g} PPI"
            )
    return len(images)


def validate_color_spaces(
    output: str,
    allowed_families: set[str],
    allowed_icc_components: set[int],
    permit_output_intent: bool,
) -> set[str]:
    """Validate veraPDF's complete document color-space feature inventory."""

    try:
        report = ET.fromstring(output)
    except ET.ParseError as error:
        fail(f"could not parse veraPDF feature report: {error}")
    summary = report.find("./batchSummary")
    feature_reports = report.find("./batchSummary/featureReports")
    if (
        summary is None
        or summary.get("failedToParse") != "0"
        or summary.get("encrypted") != "0"
        or summary.get("veraExceptions") != "0"
        or feature_reports is None
        or feature_reports.get("failedJobs") != "0"
        or feature_reports.text != "1"
    ):
        fail("veraPDF did not produce one successful feature report")

    color_spaces = report.findall(".//featuresReport//colorSpace")
    if not color_spaces:
        fail("veraPDF did not report any document color spaces")
    families: set[str] = set()
    for color_space in color_spaces:
        family = color_space.get("family")
        if not family:
            fail("veraPDF reported a color space without a family")
        families.add(family)
        if family not in allowed_families:
            fail(f"document uses disallowed vector color-space family {family}")
        if family == "ICCBased":
            components_text = color_space.findtext("components")
            if components_text is None:
                fail("ICCBased color space does not report a component count")
            try:
                components = int(components_text)
            except (TypeError, ValueError):
                fail("ICCBased color space does not report a component count")
            if components not in allowed_icc_components:
                fail(
                    f"ICCBased color space has {components} components; "
                    "the current RGB/gray profile permits only "
                    f"{sorted(allowed_icc_components)}"
                )
    output_intents = report.findall(".//featuresReport//outputIntent")
    if output_intents and not permit_output_intent:
        fail(
            "document contains an output intent, but the generic RGB/gray "
            "profiles forbid undeclared printer conversions"
        )
    return families


def run_tool(command: list[str], allowed_stderr: set[str] | None = None) -> str:
    result = run_process(command, text=True, capture_output=True, check=False)
    if result.returncode:
        fail(f"{' '.join(command)} failed: {result.stderr.strip()}")
    diagnostics = {line.strip() for line in result.stderr.splitlines() if line.strip()}
    unexpected = diagnostics - (allowed_stderr or set())
    if unexpected:
        fail(f"{' '.join(command)} reported: {'; '.join(sorted(unexpected))}")
    return result.stdout


def inspect_pdf(path: Path, profile: dict, policy: dict) -> tuple[int, int, int, set[str]]:
    """Run Poppler inspection for one configured artifact."""

    if not path.is_file():
        fail(f"missing artifact {path}")
    allowed_stderr = set()
    if profile["backend"] == "typst":
        allowed_stderr.add("Syntax Error: Suspects object is wrong type (boolean)")

    info = run_tool(["pdfinfo", str(path)], allowed_stderr)
    page_count = validate_document_metadata(info, set(policy["allowed_pdf_versions"]))
    page_info = run_tool(["pdfinfo", "-f", "1", "-l", str(page_count), str(path)], allowed_stderr)
    sampled_pages = {1, (page_count + 1) // 2, page_count}
    box_info = "\n".join(
        run_tool(
            ["pdfinfo", "-f", str(page), "-l", str(page), "-box", str(path)],
            allowed_stderr,
        )
        for page in sorted(sampled_pages)
    )
    validate_page_boxes(
        f"{page_info}\n{box_info}",
        page_count,
        float(profile["trim_points"][0]),
        float(profile["trim_points"][1]),
        float(profile["bleed_points"]),
        float(policy["geometry_tolerance_points"]),
        sampled_pages,
    )
    font_count = validate_fonts(run_tool(["pdffonts", str(path)]))
    allowed_colors = {
        (entry["name"], int(entry["components"])) for entry in policy["allowed_raster_color_models"]
    }
    image_count = validate_raster_images(
        run_tool(["pdfimages", "-list", str(path)]),
        allowed_colors,
        float(policy["continuous_tone_minimum_ppi"]),
        float(policy["one_bit_minimum_ppi"]),
    )
    color_report = run_tool(
        [
            "verapdf",
            "--loglevel",
            "1",
            "--off",
            "--extract",
            "colorSpace,outputIntent",
            "--format",
            "xml",
            str(path),
        ]
    )
    color_families = validate_color_spaces(
        color_report,
        set(policy["allowed_vector_color_families"]),
        {int(value) for value in policy["allowed_icc_components"]},
        bool(policy["permit_output_intent"]),
    )
    return page_count, font_count, image_count, color_families
