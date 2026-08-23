"""Validate cover inputs and build deterministic development cover templates."""

import hashlib
import html
import json
import re
import subprocess
import textwrap
from decimal import Decimal, InvalidOperation
from pathlib import Path

from defusedxml import ElementTree as ET

from .common import fail, load_json
from .manifestations import load_and_validate
from .process import run_process

ID = re.compile(r"[a-z0-9]+(?:-[a-z0-9]+)*")
DECIMAL = re.compile(r"(?:0|[1-9][0-9]*)(?:\.[0-9]+)?")
SHA256 = re.compile(r"[0-9a-f]{64}")


def _exact(value, fields, label):
    if not isinstance(value, dict) or set(value) != set(fields):
        fail(f"{label} fields do not match the version 1 contract")
    return value


def _decimal(value, label, *, positive=True, maximum=None):
    if not isinstance(value, str) or DECIMAL.fullmatch(value) is None:
        fail(f"{label} must be a nonnegative decimal string")
    try:
        number = Decimal(value)
    except InvalidOperation:
        fail(f"{label} must be a decimal string")
    if (positive and number <= 0) or (not positive and number < 0):
        fail(f"{label} is outside its allowed range")
    if maximum is not None and number > Decimal(maximum):
        fail(f"{label} is outside its allowed range")
    return number


def _publication_author(publication):
    authors = [
        contributor.get("display_name")
        for contributor in publication.get("contributors", [])
        if "author" in contributor.get("roles", [])
    ]
    if not authors or any(not isinstance(value, str) or not value for value in authors):
        fail("cover policy needs at least one canonical author")
    return ", ".join(authors)


def validate_cover_document(policy, records, publication):
    """Validate the source policy against already validated manifestation facts."""
    _exact(policy, {"schema_version", "output_root", "template", "profiles"}, "cover policy")
    if policy["schema_version"] != 1:
        fail("cover policy schema_version must be 1")
    if policy["output_root"] != "book/_build/covers":
        fail("cover outputs must remain under book/_build/covers")
    template = _exact(
        policy["template"],
        {
            "printer_template",
            "binding",
            "paper",
            "page_count_policy",
            "bleed_in",
            "safe_inset_in",
            "spine_text_minimum_in",
            "barcode_safe_area",
            "finish",
            "color_space",
            "press_ready",
        },
        "cover template",
    )
    printer = _exact(template["printer_template"], {"id", "revision", "vendor"}, "printer template")
    if not isinstance(printer["id"], str) or ID.fullmatch(printer["id"]) is None:
        fail("printer template id must be lowercase kebab-case")
    if (
        not isinstance(printer["revision"], int)
        or isinstance(printer["revision"], bool)
        or printer["revision"] < 1
    ):
        fail("printer template revision must be a positive integer")
    if not isinstance(printer["vendor"], str) or ID.fullmatch(printer["vendor"]) is None:
        fail("printer template vendor must be lowercase kebab-case")
    if template["binding"] not in {"perfect-bound", "case-bound", "saddle-stitch"}:
        fail("cover binding is unsupported")
    if template["binding"] != "perfect-bound":
        fail("cover geometry currently implements perfect-bound products")
    paper = _exact(template["paper"], {"id", "sheet_caliper_in"}, "cover paper")
    if not isinstance(paper["id"], str) or ID.fullmatch(paper["id"]) is None:
        fail("cover paper id must be lowercase kebab-case")
    _decimal(paper["sheet_caliper_in"], "paper sheet_caliper_in", maximum="0.020")
    if template["page_count_policy"] != "round-up-even":
        fail("cover page_count_policy must be round-up-even")
    _decimal(template["bleed_in"], "cover bleed_in", maximum="0.500")
    _decimal(template["safe_inset_in"], "cover safe_inset_in", maximum="1.000")
    _decimal(
        template["spine_text_minimum_in"],
        "cover spine_text_minimum_in",
        maximum="1.000",
    )
    barcode = _exact(
        template["barcode_safe_area"],
        {"width_in", "height_in", "edge_clearance_in"},
        "barcode safe area",
    )
    _decimal(barcode["width_in"], "barcode width_in", maximum="4.000")
    _decimal(barcode["height_in"], "barcode height_in", maximum="3.000")
    _decimal(
        barcode["edge_clearance_in"],
        "barcode edge_clearance_in",
        maximum="1.000",
    )
    if template["finish"] not in {"matte", "gloss", "satin", "uncoated"}:
        fail("cover finish is unsupported")
    if template["color_space"] not in {"sRGB-development", "CMYK-vendor"}:
        fail("cover color_space is unsupported")
    if not isinstance(template["press_ready"], bool):
        fail("cover press_ready must be boolean")
    if template["press_ready"] and (
        printer["vendor"] == "generic" or template["color_space"] == "sRGB-development"
    ):
        fail("generic sRGB cover templates cannot claim press readiness")

    profiles = policy["profiles"]
    if not isinstance(profiles, list) or not profiles:
        fail("cover policy needs profiles")
    seen_ids, selected_print = set(), set()
    print_records = {
        identifier
        for identifier, record in records.items()
        if record["format"] == "print" and record["variant"] == "full"
    }
    for profile in profiles:
        _exact(
            profile,
            {"id", "manifestation", "interior_manifestation"},
            "cover profile",
        )
        profile_id = profile["id"]
        if not isinstance(profile_id, str) or ID.fullmatch(profile_id) is None:
            fail("cover profile id must be lowercase kebab-case")
        if profile_id in seen_ids:
            fail(f"cover profile id is duplicated: {profile_id}")
        seen_ids.add(profile_id)
        manifestation = records.get(profile["manifestation"])
        interior = records.get(profile["interior_manifestation"])
        if manifestation is None or manifestation["format"] != "print":
            fail(f"cover profile '{profile_id}' needs a print manifestation")
        if interior is None or interior["format"] != "pdf":
            fail(f"cover profile '{profile_id}' needs a PDF interior manifestation")
        relation = manifestation.get("relation")
        if relation != {
            "type": "print-interior-from",
            "target": profile["interior_manifestation"],
        }:
            fail(f"cover profile '{profile_id}' differs from its print interior relation")
        if manifestation["dimensions"] != interior["dimensions"]:
            fail(f"cover profile '{profile_id}' trim differs from its interior")
        if manifestation["dimensions"].get("unit") != "in":
            fail(f"cover profile '{profile_id}' currently requires inch dimensions")
        if not interior["production"].get("artifact"):
            fail(f"cover profile '{profile_id}' interior has no artifact path")
        if manifestation["cover"] is not None and not template["press_ready"]:
            fail(f"cover profile '{profile_id}' development manifestation cover must remain null")
        trim_width = Decimal(str(manifestation["dimensions"]["width"]))
        trim_height = Decimal(str(manifestation["dimensions"]["height"]))
        barcode_width = Decimal(barcode["width_in"])
        barcode_height = Decimal(barcode["height_in"])
        clearance = Decimal(barcode["edge_clearance_in"])
        if (
            barcode_width + 2 * clearance >= trim_width
            or barcode_height + 2 * clearance >= trim_height
        ):
            fail(f"cover profile '{profile_id}' barcode safe area does not fit the back cover")
        selected_print.add(profile["manifestation"])
    if selected_print != print_records:
        fail("cover profiles must cover exactly the full print manifestations")

    work = publication.get("work", {})
    title = work.get("title")
    subtitle = work.get("subtitle")
    description = work.get("descriptions", {}).get("short")
    if any(not isinstance(value, str) or not value for value in (title, subtitle, description)):
        fail("cover policy needs canonical title, subtitle, and short description")
    return {
        "template": template,
        "profiles": profiles,
        "title": title,
        "subtitle": subtitle,
        "description": description,
        "author": _publication_author(publication),
        "records": records,
    }


def load_cover_policy(root):
    root = Path(root)
    policy = load_json(root / "config/covers/cover-policy.json", "cover policy")
    _registry, records = load_and_validate(root)
    publication = load_json(root / "book/publication.json", "publication metadata")
    context = validate_cover_document(policy, records, publication)
    integration = {
        "makefile": root / "Makefile",
        "tasks": root / "src/alkahest/tasks.py",
        "ci": root / "src/alkahest/ci.py",
        "documentation": root / "docs/publication-profiles.md",
    }
    texts = {name: path.read_text(encoding="utf-8") for name, path in integration.items()}
    for marker in ("check-%:", "test-%:", "generate-%:"):
        if marker not in texts["makefile"]:
            fail(f"Makefile is missing cover target {marker}")
    for marker in (
        '"covers", ":check-covers"',
        '"covers", ":generate-covers"',
        '"cover-artifacts", ":check-cover-artifacts"',
    ):
        if marker not in texts["tasks"]:
            fail(f"task registry is missing cover entry {marker}")
    for marker in ("alkahest generate covers", "alkahest check cover-artifacts"):
        if marker not in texts["ci"]:
            fail(f"CI is missing cover command {marker}")
    for marker in (
        "config/covers/cover-policy.json",
        "not press ready",
        "make generate-covers",
        "make check-cover-artifacts",
    ):
        if marker not in texts["documentation"]:
            fail(f"cover documentation is missing {marker!r}")
    context["policy"] = policy
    return context


def cover_geometry(template, dimensions, page_count):
    """Calculate wrap, spine, safe-area, and barcode geometry in inches."""
    if not isinstance(page_count, int) or isinstance(page_count, bool) or page_count < 1:
        fail("cover interior page count must be a positive integer")
    interior_pages = page_count
    production_pages = page_count + page_count % 2
    added_blank_pages = production_pages - interior_pages
    trim_width = Decimal(str(dimensions["width"]))
    trim_height = Decimal(str(dimensions["height"]))
    sheet_caliper = Decimal(template["paper"]["sheet_caliper_in"])
    bleed = Decimal(template["bleed_in"])
    safe = Decimal(template["safe_inset_in"])
    spine = Decimal(production_pages) * sheet_caliper / Decimal(2)
    wrap_width = 2 * trim_width + spine + 2 * bleed
    wrap_height = trim_height + 2 * bleed
    barcode = template["barcode_safe_area"]
    barcode_width = Decimal(barcode["width_in"])
    barcode_height = Decimal(barcode["height_in"])
    clearance = Decimal(barcode["edge_clearance_in"])
    return {
        "interior_pages": interior_pages,
        "production_pages": production_pages,
        "added_blank_pages": added_blank_pages,
        "trim_width": trim_width,
        "trim_height": trim_height,
        "sheet_caliper": sheet_caliper,
        "bleed": bleed,
        "safe_inset": safe,
        "spine_width": spine,
        "wrap_width": wrap_width,
        "wrap_height": wrap_height,
        "back_x": bleed,
        "spine_x": bleed + trim_width,
        "front_x": bleed + trim_width + spine,
        "barcode_x": bleed + trim_width - clearance - barcode_width,
        "barcode_y": bleed + trim_height - clearance - barcode_height,
        "barcode_width": barcode_width,
        "barcode_height": barcode_height,
        "spine_text_enabled": spine >= Decimal(template["spine_text_minimum_in"]),
    }


def _format(number, places=6):
    if isinstance(number, int):
        return str(number)
    value = format(number.quantize(Decimal(1).scaleb(-places)), "f")
    return value.rstrip("0").rstrip(".") or "0"


def _points(value):
    return value * Decimal(72)


def _text_elements(lines, x, y, size, color, line_height=None, anchor="start"):
    line_height = line_height or size * Decimal("1.25")
    rendered = []
    for index, line in enumerate(lines):
        rendered.append(
            f'<text x="{_format(x, 3)}" y="{_format(y + index * line_height, 3)}" '
            f'font-family="sans-serif" font-size="{_format(size, 3)}" '
            f'fill="{color}" text-anchor="{anchor}">{html.escape(line)}</text>'
        )
    return "\n  ".join(rendered)


def _wrap_svg(profile, manifestation, context, geometry):
    width = _points(geometry["wrap_width"])
    height = _points(geometry["wrap_height"])
    bleed = _points(geometry["bleed"])
    trim_width = _points(geometry["trim_width"])
    trim_height = _points(geometry["trim_height"])
    spine = _points(geometry["spine_width"])
    back_x = _points(geometry["back_x"])
    spine_x = _points(geometry["spine_x"])
    front_x = _points(geometry["front_x"])
    safe = _points(geometry["safe_inset"])
    barcode_x = _points(geometry["barcode_x"])
    barcode_y = _points(geometry["barcode_y"])
    barcode_width = _points(geometry["barcode_width"])
    barcode_height = _points(geometry["barcode_height"])
    title_lines = textwrap.wrap(context["title"], width=24) or [context["title"]]
    subtitle_lines = textwrap.wrap(context["subtitle"], width=36)[:4]
    description_lines = textwrap.wrap(context["description"], width=46)[:7]
    metadata = html.escape(
        json.dumps(
            {
                "profile": profile["id"],
                "manifestation": profile["manifestation"],
                "production_pages": geometry["production_pages"],
                "spine_width_in": _format(geometry["spine_width"]),
                "press_ready": False,
            },
            sort_keys=True,
        )
    )
    spine_content = ""
    if geometry["spine_text_enabled"]:
        center_x = spine_x + spine / 2
        center_y = bleed + trim_height / 2
        spine_content = (
            f'<text x="{_format(center_x, 3)}" y="{_format(center_y, 3)}" '
            f'transform="rotate(-90 {_format(center_x, 3)} {_format(center_y, 3)})" '
            'font-family="sans-serif" font-size="8" fill="#f8fafc" '
            f'text-anchor="middle">{html.escape(context["title"])}</text>'
        )
    else:
        spine_content = ""
    front_text_x = front_x + safe
    front_text_y = bleed + safe + Decimal(70)
    back_text_x = back_x + safe
    back_text_y = bleed + safe + Decimal(54)
    return (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{_format(geometry["wrap_width"])}in" '
        f'height="{_format(geometry["wrap_height"])}in" viewBox="0 0 {_format(width, 3)} {_format(height, 3)}" '
        'role="img" aria-labelledby="cover-title cover-description">\n'
        f'  <title id="cover-title">{html.escape(manifestation["label"])} development cover template</title>\n'
        '  <desc id="cover-description">Full wrap showing back, spine, front, bleed, safe areas, and barcode reserve; not press ready.</desc>\n'
        f"  <metadata>{metadata}</metadata>\n"
        f'  <rect width="{_format(width, 3)}" height="{_format(height, 3)}" fill="#e2e8f0"/>\n'
        f'  <rect x="{_format(back_x, 3)}" y="{_format(bleed, 3)}" width="{_format(trim_width, 3)}" height="{_format(trim_height, 3)}" fill="#f8fafc"/>\n'
        f'  <rect x="{_format(spine_x, 3)}" y="{_format(bleed, 3)}" width="{_format(spine, 3)}" height="{_format(trim_height, 3)}" fill="#334155"/>\n'
        f'  <rect x="{_format(front_x, 3)}" y="{_format(bleed, 3)}" width="{_format(trim_width, 3)}" height="{_format(trim_height, 3)}" fill="#0f172a"/>\n'
        f'  <rect x="{_format(back_x + safe, 3)}" y="{_format(bleed + safe, 3)}" width="{_format(trim_width - 2 * safe, 3)}" height="{_format(trim_height - 2 * safe, 3)}" fill="none" stroke="#2563eb" stroke-width="0.75" stroke-dasharray="5 3"/>\n'
        f'  <rect x="{_format(front_x + safe, 3)}" y="{_format(bleed + safe, 3)}" width="{_format(trim_width - 2 * safe, 3)}" height="{_format(trim_height - 2 * safe, 3)}" fill="none" stroke="#60a5fa" stroke-width="0.75" stroke-dasharray="5 3"/>\n'
        f'  <path d="M {_format(back_x, 3)} 0 V {_format(height, 3)} M {_format(spine_x, 3)} 0 V {_format(height, 3)} M {_format(front_x, 3)} 0 V {_format(height, 3)} M {_format(front_x + trim_width, 3)} 0 V {_format(height, 3)} M 0 {_format(bleed, 3)} H {_format(width, 3)} M 0 {_format(bleed + trim_height, 3)} H {_format(width, 3)}" fill="none" stroke="#dc2626" stroke-width="0.75" stroke-dasharray="4 3"/>\n'
        f"  {_text_elements(title_lines, front_text_x, front_text_y, Decimal(28), '#f8fafc', Decimal(33))}\n"
        f"  {_text_elements(subtitle_lines, front_text_x, front_text_y + Decimal(100), Decimal(11), '#cbd5e1', Decimal(15))}\n"
        f"  {_text_elements([context['author']], front_text_x, bleed + trim_height - safe - Decimal(18), Decimal(12), '#f8fafc')}\n"
        f"  {_text_elements([context['title']], back_text_x, back_text_y, Decimal(15), '#0f172a')}\n"
        f"  {_text_elements(description_lines, back_text_x, back_text_y + Decimal(30), Decimal(9), '#334155', Decimal(13))}\n"
        f'  <rect x="{_format(barcode_x, 3)}" y="{_format(barcode_y, 3)}" width="{_format(barcode_width, 3)}" height="{_format(barcode_height, 3)}" fill="#ffffff" stroke="#111827" stroke-width="1"/>\n'
        f"  {_text_elements(['BARCODE SAFE AREA', 'No ISBN assigned'], barcode_x + barcode_width / 2, barcode_y + barcode_height / 2 - Decimal(5), Decimal(8), '#111827', Decimal(12), 'middle')}\n"
        f"  {spine_content}\n"
        f'  <text x="{_format(width / 2, 3)}" y="{_format(height - bleed - Decimal(4), 3)}" font-family="sans-serif" font-size="5.5" fill="#991b1b" text-anchor="middle">DEVELOPMENT TEMPLATE — NOT PRESS READY · wrap {_format(geometry["wrap_width"])} × {_format(geometry["wrap_height"])} in · spine {_format(geometry["spine_width"])} in · spine text {"enabled" if geometry["spine_text_enabled"] else "disabled"} · {geometry["production_pages"]} production pages</text>\n'
        "</svg>\n"
    ).encode()


def _thumbnail_svg(profile, manifestation, context, geometry):
    width = _points(geometry["trim_width"])
    height = _points(geometry["trim_height"])
    title_lines = textwrap.wrap(context["title"], width=22) or [context["title"]]
    subtitle_lines = textwrap.wrap(context["subtitle"], width=34)[:4]
    return (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        f'<svg xmlns="http://www.w3.org/2000/svg" width="300" height="{_format(Decimal(300) * height / width, 3)}" '
        f'viewBox="0 0 {_format(width, 3)} {_format(height, 3)}" role="img" aria-labelledby="thumbnail-title thumbnail-description">\n'
        f'  <title id="thumbnail-title">{html.escape(manifestation["label"])} front-cover thumbnail</title>\n'
        '  <desc id="thumbnail-description">Development front-cover concept, not press-ready artwork.</desc>\n'
        f'  <rect width="{_format(width, 3)}" height="{_format(height, 3)}" fill="#0f172a"/>\n'
        f'  <rect x="28" y="28" width="{_format(width - Decimal(56), 3)}" height="{_format(height - Decimal(56), 3)}" fill="none" stroke="#334155" stroke-width="2"/>\n'
        f"  {_text_elements(title_lines, Decimal(50), Decimal(120), Decimal(28), '#f8fafc', Decimal(34))}\n"
        f"  {_text_elements(subtitle_lines, Decimal(50), Decimal(230), Decimal(11), '#cbd5e1', Decimal(15))}\n"
        f"  {_text_elements([context['author']], Decimal(50), height - Decimal(70), Decimal(12), '#f8fafc')}\n"
        f'  <text x="{_format(width / 2, 3)}" y="{_format(height - Decimal(25), 3)}" font-family="sans-serif" font-size="7" fill="#fca5a5" text-anchor="middle">DEVELOPMENT CONCEPT · {html.escape(profile["id"])}</text>\n'
        "</svg>\n"
    ).encode()


def _inspect_pdf(path, dimensions):
    try:
        result = run_process(
            ["pdfinfo", str(path)],
            check=True,
            capture_output=True,
            text=True,
        )
    except (OSError, subprocess.CalledProcessError) as error:
        fail(f"cannot inspect cover interior PDF '{path}': {error}")
    pages = re.search(r"^Pages:\s+(\d+)\s*$", result.stdout, re.MULTILINE)
    size = re.search(r"^Page size:\s+([0-9.]+) x ([0-9.]+) pts", result.stdout, re.MULTILINE)
    if pages is None or size is None:
        fail(f"cover interior PDF '{path}' lacks page count or dimensions")
    expected = (
        Decimal(str(dimensions["width"])) * Decimal(72),
        Decimal(str(dimensions["height"])) * Decimal(72),
    )
    actual = (Decimal(size.group(1)), Decimal(size.group(2)))
    if any(abs(left - right) > Decimal("0.1") for left, right in zip(actual, expected)):
        fail(f"cover interior PDF '{path}' trim differs from manifestation")
    return {
        "pages": int(pages.group(1)),
        "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
    }


def expected_cover_outputs(root, interior_facts=None):
    """Return expected files for every cover profile without writing them."""
    root = Path(root)
    context = load_cover_policy(root)
    policy = context["policy"]
    template = context["template"]
    reproduction = load_json(root / "book/reproducibility.json", "reproducibility policy")
    source_date = reproduction.get("source_date_utc")
    if not isinstance(source_date, str) or not source_date:
        fail("cover artifacts need a reproducible source date")
    outputs = {}
    for profile in context["profiles"]:
        manifestation = context["records"][profile["manifestation"]]
        interior = context["records"][profile["interior_manifestation"]]
        if interior_facts is None:
            artifact = root / interior["production"]["artifact"]
            if not artifact.is_file():
                fail(f"cover interior is missing: {interior['production']['artifact']}")
            facts = _inspect_pdf(artifact, manifestation["dimensions"])
        else:
            facts = interior_facts.get(profile["id"])
            if not isinstance(facts, dict):
                fail(f"cover fixture lacks interior facts for {profile['id']}")
            _exact(facts, {"pages", "sha256"}, f"cover interior facts for {profile['id']}")
            if not isinstance(facts["sha256"], str) or SHA256.fullmatch(facts["sha256"]) is None:
                fail(f"cover interior facts for {profile['id']} need a SHA-256 digest")
        geometry = cover_geometry(template, manifestation["dimensions"], facts["pages"])
        wrap = _wrap_svg(profile, manifestation, context, geometry)
        thumbnail = _thumbnail_svg(profile, manifestation, context, geometry)
        identifiers = manifestation["identifiers"]
        has_isbn = any(item["scheme"] == "isbn-13" for item in identifiers)
        blockers = [
            "generic printer template must be replaced or approved",
            "sRGB development color is not a vendor press profile",
            "manifestation has no assigned checksum-locked wrap cover",
        ]
        if not has_isbn:
            blockers.append("ISBN and production barcode are unassigned")
        if manifestation["status"] != "published":
            blockers.append(f"manifestation lifecycle is {manifestation['status']}")
        manifest = {
            "schema_version": 1,
            "profile": profile["id"],
            "manifestation": profile["manifestation"],
            "interior_manifestation": profile["interior_manifestation"],
            "source_date_utc": source_date,
            "metadata": {
                "title": context["title"],
                "subtitle": context["subtitle"],
                "author": context["author"],
                "language": manifestation["language"],
                "edition": manifestation["edition"],
            },
            "production": {
                "printer_template": template["printer_template"],
                "binding": template["binding"],
                "paper": template["paper"],
                "finish": template["finish"],
                "color_space": template["color_space"],
                "press_ready": template["press_ready"],
            },
            "interior": {
                "artifact": interior["production"]["artifact"],
                "sha256": facts["sha256"],
                "interior_pages": geometry["interior_pages"],
                "production_pages": geometry["production_pages"],
                "added_blank_pages": geometry["added_blank_pages"],
            },
            "geometry_inches": {
                key: _format(geometry[key])
                for key in (
                    "trim_width",
                    "trim_height",
                    "bleed",
                    "spine_width",
                    "wrap_width",
                    "wrap_height",
                    "safe_inset",
                    "barcode_x",
                    "barcode_y",
                    "barcode_width",
                    "barcode_height",
                )
            },
            "spine_text_enabled": geometry["spine_text_enabled"],
            "files": {
                "cover-template.svg": hashlib.sha256(wrap).hexdigest(),
                "front-thumbnail.svg": hashlib.sha256(thumbnail).hexdigest(),
            },
            "readiness_blockers": blockers,
        }
        manifest_bytes = (json.dumps(manifest, indent=2, sort_keys=True) + "\n").encode("utf-8")
        outputs[profile["id"]] = {
            "cover-template.svg": wrap,
            "front-thumbnail.svg": thumbnail,
            "cover-manifest.json": manifest_bytes,
        }
    return policy["output_root"], outputs


def generate_cover_artifacts(root):
    output_relative, outputs = expected_cover_outputs(root)
    output_root = Path(root) / output_relative
    output_root.mkdir(parents=True, exist_ok=True)
    for profile_id, files in outputs.items():
        directory = output_root / profile_id
        directory.mkdir(parents=True, exist_ok=True)
        for filename, content in files.items():
            (directory / filename).write_bytes(content)
    return {"profiles": len(outputs), "files": sum(len(files) for files in outputs.values())}


def check_cover_output_bytes(output_root, outputs):
    output_root = Path(output_root)
    if not output_root.is_dir():
        fail("cover artifact output directory is missing")
    actual_profiles = {path.name for path in output_root.iterdir()}
    if actual_profiles != set(outputs) or any(
        not (output_root / profile_id).is_dir() for profile_id in outputs
    ):
        fail("cover artifact profile entries are stale or incomplete")
    for profile_id, files in outputs.items():
        directory = output_root / profile_id
        actual_files = {path.name for path in directory.iterdir()}
        if actual_files != set(files) or any(
            not (directory / filename).is_file() for filename in files
        ):
            fail(f"cover artifact files are stale or incomplete for {profile_id}")
        for filename, expected in files.items():
            actual = (directory / filename).read_bytes()
            if actual != expected:
                fail(f"cover artifact is stale or changed: {profile_id}/{filename}")
            if filename.endswith(".svg"):
                try:
                    ET.fromstring(actual)
                except ET.ParseError as error:
                    fail(f"cover SVG is invalid: {profile_id}/{filename}: {error}")
            text = actual.decode("utf-8", errors="ignore")
            for marker in ("/workspace", "/home/", "Answer key: threshold evidence"):
                if marker in text:
                    fail(f"cover artifact exposes forbidden content: {marker}")


def check_cover_artifacts(root):
    output_relative, outputs = expected_cover_outputs(root)
    check_cover_output_bytes(Path(root) / output_relative, outputs)
    manifests = [json.loads(files["cover-manifest.json"]) for files in outputs.values()]
    return {
        "profiles": len(outputs),
        "files": sum(len(files) for files in outputs.values()),
        "production_pages": sum(item["interior"]["production_pages"] for item in manifests),
        "blockers": sum(len(item["readiness_blockers"]) for item in manifests),
    }
