"""Validate golden-page policy and compare decoded PNG pixels."""

from __future__ import annotations

import binascii
import hashlib
import json
import re
import struct
import zlib
from pathlib import Path
from typing import Never

PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"
EXPECTED_RASTERIZER = {
    "program": "pdftoppm",
    "version": "0.86.1",
    "dpi": 96,
    "color_mode": "grayscale-rgb",
    "text_antialiasing": True,
    "vector_antialiasing": True,
}
EXPECTED_BACKENDS = {"typst", "lualatex"}


class GoldenPageError(RuntimeError):
    """A golden-page policy, baseline, or comparison is invalid."""


def fail(message: str) -> Never:
    raise GoldenPageError("error: " + message)


def load_policy(root: Path) -> dict:
    path = root / "config/pdf/golden-pages.json"
    try:
        policy = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        fail(f"cannot load config/pdf/golden-pages.json: {error}")
    validate_policy(policy)
    return policy


def validate_policy(policy: dict) -> None:
    if not isinstance(policy, dict) or set(policy) != {
        "schema_version",
        "rasterizer",
        "profiles",
        "pages",
    }:
        fail("golden-page policy has an unsupported top-level contract")
    if policy["schema_version"] != 1:
        fail("golden-page schema_version must be 1")
    if policy["rasterizer"] != EXPECTED_RASTERIZER:
        fail("golden-page rasterizer must match the pinned version 1 contract")

    profiles = policy["profiles"]
    if not isinstance(profiles, list) or len(profiles) != 2:
        fail("golden pages must cover exactly the two primary PDF backends")
    profile_ids = set()
    backends = set()
    artifacts = set()
    for profile in profiles:
        if not isinstance(profile, dict) or set(profile) != {"id", "backend", "artifact"}:
            fail("golden-page profile fields are incomplete")
        identifier = profile["id"]
        backend = profile["backend"]
        artifact = profile["artifact"]
        if not re.fullmatch(r"[a-z0-9-]+", identifier or "") or identifier in profile_ids:
            fail(f"golden-page profile identifier is invalid or duplicated: {identifier}")
        if backend not in EXPECTED_BACKENDS or backend in backends:
            fail(f"golden-page backend is invalid or duplicated: {backend}")
        if (
            not isinstance(artifact, str)
            or not artifact.startswith("book/_build/print/7x10/")
            or not artifact.endswith(".pdf")
            or artifact in artifacts
        ):
            fail(f"golden-page artifact is unsafe or duplicated: {artifact}")
        profile_ids.add(identifier)
        backends.add(backend)
        artifacts.add(artifact)
    if backends != EXPECTED_BACKENDS:
        fail("golden pages must cover Typst and LuaLaTeX")

    pages = policy["pages"]
    if not isinstance(pages, list) or not 4 <= len(pages) <= 8:
        fail("golden-page policy needs four to eight focused pages")
    page_ids = set()
    markers = set()
    for page in pages:
        if not isinstance(page, dict) or set(page) != {"id", "marker", "rationale"}:
            fail("golden-page fields are incomplete")
        identifier = page["id"]
        marker = page["marker"]
        rationale = page["rationale"]
        if not re.fullmatch(r"[a-z0-9-]+", identifier or "") or identifier in page_ids:
            fail(f"golden-page identifier is invalid or duplicated: {identifier}")
        if not isinstance(marker, str) or len(marker) < 12 or marker in markers:
            fail(f"golden-page marker is too short or duplicated: {marker}")
        if not isinstance(rationale, str) or len(rationale.split()) < 10:
            fail(f"golden-page rationale is not substantive: {identifier}")
        page_ids.add(identifier)
        markers.add(marker)


def baseline_name(profile: dict, page: dict) -> str:
    return f"{profile['id']}--{page['id']}.png"


def expected_baselines(policy: dict) -> set[str]:
    return {
        baseline_name(profile, page) for profile in policy["profiles"] for page in policy["pages"]
    }


def validate_baseline_coverage(root: Path, policy: dict, allow_missing=False) -> int:
    directory = root / "tests/golden-pages"
    actual = {path.name for path in directory.glob("*.png")} if directory.is_dir() else set()
    expected = expected_baselines(policy)
    extra = sorted(actual - expected)
    missing = sorted(expected - actual)
    if extra:
        fail("unregistered golden-page baselines: " + ", ".join(extra))
    if missing and not allow_missing:
        fail("missing golden-page baselines: " + ", ".join(missing))
    return len(actual)


def resolve_marker_page(text: str, marker: str) -> int:
    pages = text.split("\f")
    if pages and not pages[-1].strip():
        pages.pop()
    matches = [index for index, page in enumerate(pages, start=1) if marker in page]
    if len(matches) != 1:
        fail(f"golden marker must resolve to exactly one page: {marker!r} (found {len(matches)})")
    return matches[0]


def _paeth(left: int, above: int, upper_left: int) -> int:
    prediction = left + above - upper_left
    left_distance = abs(prediction - left)
    above_distance = abs(prediction - above)
    upper_left_distance = abs(prediction - upper_left)
    if left_distance <= above_distance and left_distance <= upper_left_distance:
        return left
    if above_distance <= upper_left_distance:
        return above
    return upper_left


def read_png(path: Path) -> dict:
    try:
        data = path.read_bytes()
    except OSError as error:
        fail(f"cannot read PNG {path}: {error}")
    if not data.startswith(PNG_SIGNATURE):
        fail(f"golden image is not a PNG: {path}")
    cursor = len(PNG_SIGNATURE)
    header: tuple[int, int, int, int, int, int, int] | None = None
    compressed = bytearray()
    while cursor < len(data):
        if cursor + 12 > len(data):
            fail(f"PNG has a truncated chunk: {path}")
        length = struct.unpack(">I", data[cursor : cursor + 4])[0]
        kind = data[cursor + 4 : cursor + 8]
        payload_start = cursor + 8
        payload_end = payload_start + length
        if payload_end + 4 > len(data):
            fail(f"PNG has a truncated payload: {path}")
        payload = data[payload_start:payload_end]
        expected_crc = struct.unpack(">I", data[payload_end : payload_end + 4])[0]
        if binascii.crc32(kind + payload) & 0xFFFFFFFF != expected_crc:
            fail(f"PNG has an invalid chunk checksum: {path}")
        if kind == b"IHDR":
            header = struct.unpack(">IIBBBBB", payload)
        elif kind == b"IDAT":
            compressed.extend(payload)
        elif kind == b"IEND":
            break
        cursor = payload_end + 4
    if header is None:
        fail(f"PNG has no IHDR chunk: {path}")
    width, height, bit_depth, color_type, compression, filtering, interlace = header
    channels = {0: 1, 2: 3, 6: 4}.get(color_type)
    if bit_depth != 8 or channels is None or compression or filtering or interlace:
        fail(f"PNG uses an unsupported pixel format: {path}")
    try:
        raw = zlib.decompress(bytes(compressed))
    except zlib.error as error:
        fail(f"PNG pixel stream is invalid: {path}: {error}")
    stride = width * channels
    if len(raw) != height * (stride + 1):
        fail(f"PNG pixel stream has the wrong size: {path}")
    pixels = bytearray()
    previous = bytearray(stride)
    cursor = 0
    for _row in range(height):
        filter_type = raw[cursor]
        cursor += 1
        encoded = raw[cursor : cursor + stride]
        cursor += stride
        decoded = bytearray(stride)
        for index, value in enumerate(encoded):
            left = decoded[index - channels] if index >= channels else 0
            above = previous[index]
            upper_left = previous[index - channels] if index >= channels else 0
            if filter_type == 0:
                decoded[index] = value
            elif filter_type == 1:
                decoded[index] = (value + left) & 0xFF
            elif filter_type == 2:
                decoded[index] = (value + above) & 0xFF
            elif filter_type == 3:
                decoded[index] = (value + ((left + above) // 2)) & 0xFF
            elif filter_type == 4:
                decoded[index] = (value + _paeth(left, above, upper_left)) & 0xFF
            else:
                fail(f"PNG uses an unsupported row filter: {path}")
        pixels.extend(decoded)
        previous = decoded
    return {"width": width, "height": height, "channels": channels, "pixels": bytes(pixels)}


def visual_digest(image: dict) -> str:
    digest = hashlib.sha256()
    digest.update(struct.pack(">III", image["width"], image["height"], image["channels"]))
    digest.update(image["pixels"])
    return digest.hexdigest()


def compare_pixels(expected: dict, actual: dict) -> dict:
    shape = (expected["width"], expected["height"], expected["channels"])
    actual_shape = (actual["width"], actual["height"], actual["channels"])
    if shape != actual_shape:
        return {
            "same_shape": False,
            "expected_shape": shape,
            "actual_shape": actual_shape,
            "changed_pixels": None,
            "max_channel_delta": None,
            "diff_pixels": None,
        }
    channels = expected["channels"]
    changed = 0
    max_delta = 0
    diff_pixels = bytearray()
    for offset in range(0, len(expected["pixels"]), channels):
        deltas = [
            abs(expected["pixels"][offset + channel] - actual["pixels"][offset + channel])
            for channel in range(channels)
        ]
        delta = max(deltas)
        if delta:
            changed += 1
        max_delta = max(max_delta, delta)
        intensity = min(255, delta * 4)
        diff_pixels.extend((255, 255 - intensity, 255 - intensity))
    return {
        "same_shape": True,
        "expected_shape": shape,
        "actual_shape": actual_shape,
        "changed_pixels": changed,
        "max_channel_delta": max_delta,
        "diff_pixels": bytes(diff_pixels),
    }


def _chunk(kind: bytes, payload: bytes) -> bytes:
    return (
        struct.pack(">I", len(payload))
        + kind
        + payload
        + struct.pack(">I", binascii.crc32(kind + payload) & 0xFFFFFFFF)
    )


def write_rgb_png(path: Path, width: int, height: int, pixels: bytes) -> None:
    if len(pixels) != width * height * 3:
        fail("RGB diff pixel stream has the wrong size")
    rows = b"".join(
        b"\x00" + pixels[row * width * 3 : (row + 1) * width * 3] for row in range(height)
    )
    header = struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(
        PNG_SIGNATURE
        + _chunk(b"IHDR", header)
        + _chunk(b"IDAT", zlib.compress(rows, level=9))
        + _chunk(b"IEND", b"")
    )
