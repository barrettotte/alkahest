"""Validate the semantic icon registry, assets, aliases, and manuscript calls."""

import html
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]


def fail(message):
    raise RuntimeError(f"error: {message}")


def main():
    root = ROOT / "book"
    registry_path = root / "_extensions" / "alkahest-icons" / "registry.lua"
    entries, current = {}, None
    for line in registry_path.read_text(encoding="utf-8").splitlines():
        entry = re.match(r'^  (?:([a-z][a-z0-9-]*)|\["([a-z][a-z0-9-]*)"\]) = \{\s*$', line)
        if entry:
            current = entry.group(1) or entry.group(2)
            if current in entries:
                fail(f"duplicate canonical icon name: {current}")
            entries[current] = {"aliases": []}
        elif current:
            asset = re.match(r'^    asset = "([^"]+)",', line)
            label = re.match(r'^    label = "([^"]+)",', line)
            aliases = re.match(r"^    aliases = \{(.*)\},", line)
            if asset:
                entries[current]["asset"] = asset.group(1)
            elif label:
                entries[current]["label"] = label.group(1)
            elif aliases:
                entries[current]["aliases"] = re.findall(r'"([a-z][a-z0-9-]*)"', aliases.group(1))
            elif re.match(r"^  \},", line):
                current = None
    for required in ("equipment", "warning", "danger", "idea", "experiment", "optional-material"):
        if required not in entries:
            fail(f"icon registry is missing required name: {required}")
    lookup = {}
    for name in sorted(entries):
        entry = entries[name]
        if not entry.get("label"):
            fail(f"icon {name} has no default label")
        asset = entry.get("asset")
        if not asset:
            fail(f"icon {name} has no asset")
        if not re.fullmatch(r"icons/[a-z0-9-]+\.svg", asset):
            fail(f"icon {name} has an unsafe asset path: {asset}")
        svg = (root / asset).read_text(encoding="utf-8")
        if 'viewBox="0 0 24 24"' not in svg:
            fail(f"icon {name} asset must use the shared 24 by 24 SVG view box")
        if re.search(r"<text\b", svg, re.I):
            fail(f"icon {name} asset must not contain embedded text")
        for key in (name, *entry["aliases"]):
            if key in lookup:
                fail(f"duplicate icon name or alias: {key}")
            lookup[key] = name
    calls = 0
    call_pattern = re.compile(r"\{\{<\s*alk-icon\s+(.+?)\s*>\}\}")
    for source in sorted(
        path
        for path in root.rglob("*.qmd")
        if ".quarto" not in path.parts and "_build" not in path.parts
    ):
        disabled, pending = "", None
        for line_number, line in enumerate(source.read_text(encoding="utf-8").splitlines(), 1):
            if disabled:
                if re.fullmatch(re.escape(disabled) + r"\s*", line):
                    disabled = ""
                continue
            fence = re.match(r"^(`{3,}|~{3,}).*\bshortcodes=false\b", line)
            if fence:
                disabled = fence.group(1)
                continue
            if re.match(r"^:{3,}.*\.icon-notice\b", line):
                if not re.search(r"\bicon=false\b", line):
                    fail(f"{source}:{line_number}: .icon-notice must set icon=false")
                pending = line_number
                continue
            if pending is not None and line.strip():
                if not re.match(r"^#{1,6}\s+.*\{\{<\s*alk-icon\s+", line):
                    fail(
                        f"{source}:{pending}: .icon-notice must be followed by a title containing alk-icon"
                    )
                pending = None
            if re.search(r"\{\{<\s*alk-icon\s*>\}\}", line):
                fail(f"{source}:{line_number}: alk-icon is missing a registry name")
            for match in call_pattern.finditer(line):
                arguments = match.group(1)
                parsed = re.fullmatch(r"([a-z][a-z0-9-]*)(.*)", arguments)
                if not parsed:
                    fail(f"{source}:{line_number}: invalid alk-icon registry name")
                name, remainder = parsed.groups()
                if name not in lookup:
                    fail(f"{source}:{line_number}: unknown alk-icon name or alias: {name}")
                if re.search(r"""\blabel\s*=\s*(["'])\1""", remainder):
                    fail(f"{source}:{line_number}: alk-icon label must not be empty")
                remainder = re.sub(r"""\blabel\s*=\s*(?:"[^"]+"|'[^']+'|[^\s]+)""", "", remainder)
                remainder = re.sub(r"\s+", "", remainder)
                if remainder:
                    fail(f"{source}:{line_number}: unexpected alk-icon arguments: {remainder}")
                visible = line[match.end() :]
                visible = re.sub(r"\{\{<.*?>\}\}|<!--.*?-->|\{[^{}]*\}|<[^>]*>", "", visible)
                visible = html.unescape(visible)
                if not any(character.isalnum() for character in visible):
                    fail(
                        f"{source}:{line_number}: alk-icon must be followed on the same line by visible text"
                    )
                calls += 1
        if pending is not None:
            fail(f"{source}:{pending}: .icon-notice has no title")
    if not calls:
        fail("no semantic icon shortcode calls were found")
    print(
        f"ok: semantic icon registry ({len(entries)} canonical names; {len(lookup)} names and aliases; {calls} manuscript calls)"
    )


if __name__ == "__main__":
    try:
        main()
    except (OSError, UnicodeError, RuntimeError) as error:
        print(error, file=sys.stderr)
        raise SystemExit(1)
