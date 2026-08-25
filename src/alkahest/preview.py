"""Validate centralized preview presentation metadata."""

import json
import re
from pathlib import Path

from .common import fail


def _quoted(text, key, indent):
    match = re.search(
        rf"^{re.escape(' ' * indent + key)}:\s*(\"(?:[^\"\\]|\\.)*\")\s*$",
        text,
        re.MULTILINE,
    )
    if not match:
        fail(f"preview profile needs quoted {key}")
    value = json.loads(match.group(1))
    return value


def _boolean(text, key, indent):
    matches = re.findall(
        rf"^{re.escape(' ' * indent + key)}:\s*(true|false)\s*$",
        text,
        re.MULTILINE,
    )
    if len(matches) != 1:
        fail(f"preview profile needs one boolean {key} at indentation {indent}")
    return matches[0] == "true"


def validate_preview_presentation(root: Path):
    book = root / "book"
    profile = (book / "_quarto-preview.yml").read_text(encoding="utf-8")
    config = (book / "_quarto.yml").read_text(encoding="utf-8")
    defaults_path = book / "alkahest-defaults.yml"
    defaults = defaults_path.read_text(encoding="utf-8") if defaults_path.is_file() else ""
    index = (book / "index.qmd").read_text(encoding="utf-8")

    if (config + "\n" + defaults).count("  - filters/preview.lua") != 1:
        fail("canonical Quarto config must register the preview filter exactly once")
    placeholder = "::: {.alkahest-preview-placeholder}\n:::"
    if index.count(placeholder) != 1 or 'when-profile="edition-preview"' in index:
        fail("shared preface must contain one unconditional preview presentation placeholder")

    book_subtitle = _quoted(profile, "subtitle", 2)
    book_description = _quoted(profile, "description", 2)
    subtitle = _quoted(profile, "subtitle", 0)
    description = _quoted(profile, "description", 0)
    identifier = _quoted(profile, "identifier", 0)
    edition = _quoted(profile, "edition", 2)
    label = _quoted(profile, "label", 4)
    message = _quoted(profile, "message", 4)
    full_label = _quoted(profile, "full-edition-label", 4)
    full_url = _quoted(profile, "full-edition-url", 4)
    purchase_label = _quoted(profile, "purchase-label", 4)
    purchase_url = _quoted(profile, "purchase-url", 4)
    pending = _quoted(profile, "links-pending", 4)
    watermark_text = _quoted(profile, "text", 6)

    if book_subtitle != subtitle or "preview" not in subtitle.casefold():
        fail("preview book and document subtitles must match and identify a preview")
    for value, name in (
        (description, "description"),
        (edition, "edition"),
        (label, "label"),
        (message, "message"),
        (full_label, "full-edition-label"),
        (purchase_label, "purchase-label"),
        (pending, "links-pending"),
    ):
        if not value.strip():
            fail(f"preview {name} must be nonempty")
    if book_description != description:
        fail("preview book and document descriptions must match")
    if "preview" not in description.casefold() or "preview" not in edition.casefold():
        fail("preview description and edition statement must identify the product")
    if not re.fullmatch(r"urn:uuid:[0-9a-f]{8}(?:-[0-9a-f]{4}){3}-[0-9a-f]{12}", identifier):
        fail("preview identifier must be a lowercase UUID URN")
    for url, name in ((full_url, "full-edition-url"), (purchase_url, "purchase-url")):
        if url and not re.fullmatch(r"https://\S+", url):
            fail(f"preview {name} must be empty or an absolute HTTPS URL")
    if not _boolean(profile, "enabled", 4):
        fail("preview presentation must be enabled")
    if not _boolean(profile, "enabled", 6):
        fail("preview watermark fixture must be enabled")
    if not re.fullmatch(r"[A-Z0-9][A-Z0-9 -]{0,39}", watermark_text):
        fail("preview watermark text must be short uppercase display text")

    return {
        "identifier": identifier,
        "links": sum(bool(url) for url in (full_url, purchase_url)),
        "watermark": watermark_text,
    }
