"""Validate whole-book edition manifests, source policy, and references."""

import os
import re
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR / "lib"))

from alkahest.common import ContractError, fail, qmd_sources
from alkahest.editions import edition_source_ids, load_editions, render_book_structure


def visible_content(content, edition_name):
    pattern = rf'^:::\s+\{{\.content-visible\s+unless-profile="edition-{re.escape(edition_name)}"\}}\s*\n.*?^:::\s*$'
    return re.sub(pattern, "", content, flags=re.M | re.S)


def main():
    root = Path(os.environ.get("ALKAHEST_EDITION_BOOK_ROOT", SCRIPT_DIR.parent / "book")).resolve()
    if not root.is_dir():
        fail("edition book root does not exist")
    registry = load_editions(root / "editions.json")
    config = (root / "_quarto.yml").read_text(encoding="utf-8")
    structure_match = re.search(r"(^  chapters:\n.*?)(?=^\S)", config, re.M | re.S)
    if not structure_match:
        fail("canonical Quarto config has no book structure")
    if structure_match.group(1) != render_book_structure(registry, "full"):
        fail("canonical Quarto structure must match the full edition exactly")

    registered = {value["path"]: key for key, value in registry["sources"].items()}
    disk_sources = [path.relative_to(root).as_posix() for path in qmd_sources(root)]
    for source in sorted(disk_sources):
        if source not in registered:
            fail(f"manuscript source '{source}' is absent from editions.json")
    for source in sorted(registered):
        if not (root / source).is_file():
            fail(f"edition manifest references missing source '{source}'")
    if len(disk_sources) != len(registered):
        fail("edition manifest and manuscript tree contain different source counts")

    owners = {}
    for source in sorted(registered):
        source_id = registered[source]
        metadata = registry["sources"][source_id]
        content = (root / source).read_text(encoding="utf-8")
        front_match = re.match(r"\A---\s*\n(.*?)^---\s*$", content, re.M | re.S)
        front_matter = front_match.group(1) if front_match else None
        if front_matter and re.search(r"^bibliography\s*:", front_matter, re.M):
            fail(f"source '{source}' declares a local bibliography; use the shared book bibliography")
        headings = re.findall(r"^(# (?!#).*?)$", content, re.M)
        if len(headings) != 1 or not re.search(r"\{[^}]*#[A-Za-z][A-Za-z0-9_.:-]*", headings[0]):
            fail(f"source '{source}' must have exactly one H1 with a persistent ID")
        if metadata["availability"] == "private":
            if front_matter is None or not re.search(r"^alkahest-edition:\s*\n\s+access:\s*private\s*$", front_matter, re.M):
                fail(f"private source '{source}' must declare alkahest-edition access: private")
        elif front_matter and re.search(r"^alkahest-edition:", front_matter, re.M):
            fail(f"public source '{source}' must not declare private edition metadata")
        if metadata["role"] == "appendix":
            declared_match = re.search(r"^alkahest-appendix:\s*\n\s+availability:\s*([a-z-]+)\s*$", front_matter or "", re.M)
            declared = declared_match.group(1) if declared_match else None
            if metadata["availability"] == "core" and declared is not None:
                fail(f"core appendix '{source}' must not declare exceptional availability")
            if metadata["availability"] != "core" and declared != metadata["availability"]:
                fail(f"appendix '{source}' must declare availability '{metadata['availability']}'")
        for identity in re.findall(r"\{[^}\n]*#([A-Za-z][A-Za-z0-9_.:-]*)", content):
            if identity in owners:
                fail(f"content identity '{identity}' is declared in both '{source}' and '{owners[identity]}'")
            owners[identity] = source

    for edition_name, edition in sorted(registry["editions"].items()):
        source_ids = edition_source_ids(registry, edition_name)
        selected = {registry["sources"][item]["path"] for item in source_ids}
        for source_id in source_ids:
            source = registry["sources"][source_id]["path"]
            content = visible_content((root / source).read_text(encoding="utf-8"), edition_name)
            for target in re.findall(r"@([A-Za-z][A-Za-z0-9_.:-]*)", content):
                if target in owners and owners[target] not in selected:
                    fail(f"edition '{edition_name}' leaves dangling reference '@{target}' in '{source}'")
        if "index-backmatter.qmd" in selected:
            for line in (root / "index.yml").read_text(encoding="utf-8").splitlines():
                locator = re.fullmatch(r"\s+-\s+([A-Za-z0-9_/-]+\.qmd)#[A-Za-z0-9_.:-]+\s*", line)
                if locator and locator.group(1) not in selected:
                    fail(f"edition '{edition_name}' retains index locator into omitted '{locator.group(1)}'")
        if edition["access"] == "public":
            for source_id in source_ids:
                if registry["sources"][source_id]["availability"] == "private":
                    fail(f"public edition '{edition_name}' includes private source '{source_id}'")
    print(f"ok: whole-book editions ({len(registry['editions'])} editions; {len(registry['structures'])} reusable structures; {len(registry['sources'])} registered sources; preview, abridged, format, public/private, and reference-integrity policy)")


if __name__ == "__main__":
    try:
        main()
    except (ContractError, OSError, UnicodeError) as error:
        print(error if isinstance(error, ContractError) else f"error: {error}", file=sys.stderr)
        raise SystemExit(1)
