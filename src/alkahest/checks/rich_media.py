"""Validate rich-media assets, accessibility fallbacks, rights, and references."""

import hashlib
import json
import re
import subprocess
import sys
import tempfile
import wave
from datetime import date
from pathlib import Path

from defusedxml import ElementTree as ET

REPO_ROOT = Path(__file__).resolve().parents[3]
BOOK_ROOT = REPO_ROOT / "book"
REGISTRY_PATH = BOOK_ROOT / "media.json"
MEDIA_ROOT = BOOK_ROOT / "media"
KINDS = ("audio", "video", "animation", "interactive")
MEDIA_TYPES = {
    "audio": ("audio/wav", ".wav"),
    "video": ("video/webm", ".webm"),
    "animation": ("text/html", ".html"),
    "interactive": ("text/html", ".html"),
}
COMMON_FIELDS = {
    "kind",
    "title",
    "asset",
    "media_type",
    "sha256",
    "fallback",
    "fallback_sha256",
    "fallback_alt",
    "description",
    "transcript",
    "transcript_sha256",
    "creator",
    "origin",
    "created",
    "license",
    "public_distribution",
}
KIND_FIELDS = {
    "audio": {"duration_seconds"},
    "video": {"duration_seconds", "captions", "captions_sha256"},
    "animation": {"pause_control", "reduced_motion"},
    "interactive": {"keyboard_operable", "live_status"},
}


def fail(message):
    raise RuntimeError("error: " + message)


def load_registry():
    try:
        registry = json.loads(REGISTRY_PATH.read_text(encoding="utf-8"))
    except json.JSONDecodeError as error:
        fail(f"invalid media.json: {error}")
    if registry.get("version") != 1 or set(registry) != {"version", "items"}:
        fail("media registry version must be 1 with only version and items")
    if not isinstance(registry["items"], dict) or not registry["items"]:
        fail("media registry items must be a nonempty object")
    return registry


def safe_path(name, value):
    if not isinstance(value, str) or not value.startswith("media/"):
        fail(f"{name} must be a path under media/")
    path = Path(value)
    if path.is_absolute() or ".." in path.parts or path.as_posix() != value:
        fail(f"{name} has an unsafe path: {value!r}")
    resolved = BOOK_ROOT / path
    if not resolved.is_file():
        fail(f"{name} references missing file {value!r}")
    return resolved


def check_hash(name, path, expected):
    if not isinstance(expected, str) or not re.fullmatch(r"[0-9a-f]{64}", expected):
        fail(f"{name} has an invalid SHA-256")
    actual = hashlib.sha256(path.read_bytes()).hexdigest()
    if actual != expected:
        fail(f"{name} checksum drift: expected {expected}, found {actual}")


def check_svg(name, path):
    text = path.read_text(encoding="utf-8")
    lowered = text.lower()
    if not text.startswith('<?xml version="1.0" encoding="UTF-8"?>\n'):
        fail(f"{name} fallback must declare UTF-8 XML")
    if "<script" in lowered or "<image" in lowered or "href=" in lowered:
        fail(f"{name} fallback must be self-contained and script-free")
    try:
        root = ET.fromstring(text)
    except ET.ParseError as error:
        fail(f"{name} fallback is invalid SVG: {error}")
    namespace = "{http://www.w3.org/2000/svg}"
    if root.get("role") != "img" or root.get("aria-labelledby") != "title desc":
        fail(f"{name} fallback must expose an accessible image name")
    if root.find(namespace + "title") is None or root.find(namespace + "desc") is None:
        fail(f"{name} fallback must include title and description")
    if root.get("viewBox") is None:
        fail(f"{name} fallback must have a responsive viewBox")


def check_audio(name, path, item):
    with wave.open(str(path), "rb") as source:
        if source.getnchannels() != 1 or source.getsampwidth() != 2:
            fail(f"{name} audio must be mono 16-bit PCM")
        if source.getframerate() != 8_000:
            fail(f"{name} audio must use the reviewed 8000 Hz sample rate")
        duration = source.getnframes() / source.getframerate()
    if abs(duration - item["duration_seconds"]) > 0.001:
        fail(f"{name} audio duration does not match the registry")


def check_video(name, path, item):
    data = path.read_bytes()
    if not data.startswith(b"\x1aE\xdf\xa3") or len(data) < 1_000:
        fail(f"{name} is not the reviewed nonempty WebM fixture")
    if item["duration_seconds"] != 2.0:
        fail(f"{name} must declare the reviewed two-second duration")


def check_web_asset(name, path, item):
    text = path.read_text(encoding="utf-8")
    lowered = text.lower()
    if "<!doctype html>" not in lowered or '<meta charset="utf-8">' not in lowered:
        fail(f"{name} must be a complete UTF-8 HTML document")
    if re.search(r"(?:src|href)=[\"'](?:https?:)?//", lowered):
        fail(f"{name} must not depend on network resources")
    if '<html lang="en-us">' not in lowered or "<title>" not in lowered:
        fail(f"{name} must declare language and title")
    if item["kind"] == "animation":
        for marker in (
            "@keyframes",
            "pause animation",
            "prefers-reduced-motion",
            "animation-play-state",
        ):
            if marker not in lowered:
                fail(f"{name} animation is missing control marker {marker!r}")
        if item.get("pause_control") is not True or item.get("reduced_motion") is not True:
            fail(f"{name} animation must declare pause and reduced-motion support")
    else:
        for marker in (
            'type="range"',
            "<label",
            'aria-live="polite"',
            "addEventListener",
            "arrow keys",
        ):
            if marker.lower() not in lowered:
                fail(f"{name} interactive is missing accessibility marker {marker!r}")
        if item.get("keyboard_operable") is not True or item.get("live_status") != "polite":
            fail(f"{name} interactive must declare keyboard and live-status behavior")


def check_vtt(name, path):
    text = path.read_text(encoding="utf-8")
    if not text.startswith("WEBVTT\n\n") or text.count("-->") < 2:
        fail(f"{name} captions must contain a WEBVTT header and synchronized cues")
    if "[No speech]" not in text:
        fail(f"{name} captions must describe relevant non-speech information")


def check_registry(registry):
    kinds = {kind: 0 for kind in KINDS}
    registered_paths = set()
    for media_id, item in sorted(registry["items"].items()):
        if not re.fullmatch(r"media-[a-z0-9]+(?:-[a-z0-9]+)*", media_id):
            fail(f"invalid rich-media ID {media_id!r}")
        if not isinstance(item, dict) or item.get("kind") not in KINDS:
            fail(f"{media_id} has an unsupported kind")
        kind = item["kind"]
        expected_fields = COMMON_FIELDS | KIND_FIELDS[kind]
        if set(item) != expected_fields:
            missing = sorted(expected_fields - set(item))
            unknown = sorted(set(item) - expected_fields)
            fail(f"{media_id} fields differ from contract; missing={missing}, unknown={unknown}")
        kinds[kind] += 1
        if not isinstance(item["title"], str) or not item["title"].strip():
            fail(f"{media_id} needs a title")
        if not isinstance(item["description"], str) or len(item["description"]) < 50:
            fail(f"{media_id} needs an accessible description")
        if not isinstance(item["fallback_alt"], str) or len(item["fallback_alt"]) < 50:
            fail(f"{media_id} needs a substantive fallback alternative")
        if not all(
            isinstance(item[field], str) and item[field].strip() for field in ("creator", "origin")
        ):
            fail(f"{media_id} needs creator and origin provenance")
        try:
            date.fromisoformat(item["created"])
        except (TypeError, ValueError):
            fail(f"{media_id} created date must use ISO 8601")
        if item["license"] != "CC0-1.0" or item["public_distribution"] is not True:
            fail(f"{media_id} must record the reviewed license and public-distribution permission")

        media_type, extension = MEDIA_TYPES[kind]
        if item["media_type"] != media_type:
            fail(f"{media_id} media type does not match its kind")
        asset = safe_path(media_id + " asset", item["asset"])
        if asset.suffix != extension:
            fail(f"{media_id} asset extension does not match its media type")
        fallback = safe_path(media_id + " fallback", item["fallback"])
        transcript = safe_path(media_id + " transcript", item["transcript"])
        if fallback.suffix != ".svg" or transcript.suffix != ".md":
            fail(f"{media_id} must use SVG fallback and Markdown transcript")
        for field, path in (("asset", asset), ("fallback", fallback), ("transcript", transcript)):
            relative = path.relative_to(BOOK_ROOT).as_posix()
            if relative in registered_paths:
                fail(f"media path {relative!r} is registered more than once")
            registered_paths.add(relative)
            check_hash(
                f"{media_id} {field}",
                path,
                item[field + "_sha256"] if field != "asset" else item["sha256"],
            )
        check_svg(media_id, fallback)
        transcript_text = transcript.read_text(encoding="utf-8")
        if len(transcript_text.strip()) < 80 or "<script" in transcript_text.lower():
            fail(f"{media_id} transcript is missing or unsafe")

        if kind == "audio":
            check_audio(media_id, asset, item)
        elif kind == "video":
            check_video(media_id, asset, item)
            captions = safe_path(media_id + " captions", item["captions"])
            relative = captions.relative_to(BOOK_ROOT).as_posix()
            if relative in registered_paths:
                fail(f"media path {relative!r} is registered more than once")
            registered_paths.add(relative)
            check_hash(media_id + " captions", captions, item["captions_sha256"])
            check_vtt(media_id, captions)
        else:
            check_web_asset(media_id, asset, item)

    for kind, count in kinds.items():
        if count != 1:
            fail(f"acceptance registry must contain exactly one {kind} specimen")
    actual_paths = {
        path.relative_to(BOOK_ROOT).as_posix() for path in MEDIA_ROOT.iterdir() if path.is_file()
    }
    if registered_paths != actual_paths:
        fail(
            "media registry coverage differs from checked files; "
            f"unregistered={sorted(actual_paths - registered_paths)}, missing={sorted(registered_paths - actual_paths)}"
        )
    return kinds


def check_audio_regeneration(registry):
    item = registry["items"]["media-reference-tone"]
    with tempfile.TemporaryDirectory(prefix="alkahest-media.") as directory:
        candidate = Path(directory) / "reference-tone.wav"
        result = subprocess.run(  # noqa: S603 - fixed generator module
            [
                sys.executable,
                "-m",
                "alkahest.generators.rich_media",
                "--output",
                str(candidate),
            ],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            encoding="utf-8",
        )
        if result.returncode != 0:
            fail("rich-media audio regeneration failed: " + result.stdout.strip())
        if candidate.read_bytes() != (BOOK_ROOT / item["asset"]).read_bytes():
            fail("generated rich-media audio fixture drifted")


def check_extension_and_manuscript(registry):
    extension = BOOK_ROOT / "_extensions" / "alkahest-media"
    for relative in ("_extension.yml", "alkahest-media.lua", "registry.lua"):
        if not (extension / relative).is_file():
            fail("missing rich-media extension file: " + relative)
    lua = (extension / "alkahest-media.lua").read_text(encoding="utf-8")
    for marker in (
        "alk-media",
        "<audio",
        "<video",
        "<iframe",
        "<track",
        "sandbox",
        "rich-media-transcript",
    ):
        if marker not in lua:
            fail("rich-media shortcode is missing renderer marker: " + marker)

    references = {media_id: 0 for media_id in registry["items"]}
    pattern = re.compile(r"\{\{<\s*alk-media\s+([^\s>]+)(.*?)>\}\}")
    for source in sorted(BOOK_ROOT.rglob("*.qmd")):
        if "_build" in source.parts:
            continue
        text = source.read_text(encoding="utf-8")
        for match in pattern.finditer(text):
            media_id = match.group(1)
            if media_id not in references:
                fail(
                    f"{source.relative_to(BOOK_ROOT)} references unknown rich-media ID {media_id!r}"
                )
            if match.group(2).strip():
                fail(f"{source.relative_to(BOOK_ROOT)} uses unexpected alk-media arguments")
            references[media_id] += 1
        if re.search(r"!?\[[^\]]*\]\(media/", text) or re.search(
            r"\b(?:src|poster)=['\"]media/", text
        ):
            fail(f"{source.relative_to(BOOK_ROOT)} uses a raw media path instead of alk-media")
    for media_id, count in references.items():
        if count != 1:
            fail(f"rich-media item {media_id!r} must be referenced exactly once; found {count}")
    figures = (BOOK_ROOT / "figures.qmd").read_text(encoding="utf-8")
    if "#sec-rich-media-workflow" not in figures:
        fail("figures.qmd is missing the rich-media workflow section")


def main():
    registry = load_registry()
    kinds = check_registry(registry)
    check_audio_regeneration(registry)
    check_extension_and_manuscript(registry)
    summary = ", ".join(f"{kinds[kind]} {kind}" for kind in KINDS)
    print(
        f"ok: rich media ({summary}; captions, transcripts, descriptions, controls, "
        "rights, checksums, and deterministic static fallbacks)"
    )


if __name__ == "__main__":
    try:
        main()
    except (OSError, RuntimeError, TypeError, ValueError, wave.Error) as error:
        print(
            str(error) if isinstance(error, RuntimeError) else "error: " + str(error),
            file=sys.stderr,
        )
        raise SystemExit(1)
