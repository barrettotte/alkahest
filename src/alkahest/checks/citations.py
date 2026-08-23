"""Validate citation styles, bibliography keys, calls, and uncited inclusions."""

import hashlib
import os
import re
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parents[3] / "scripts"


def fail(message):
    raise RuntimeError(f"error: {message}")


def main():
    root = Path(os.environ.get("ALKAHEST_CITATION_BOOK_ROOT", SCRIPT_DIR.parent / "book")).resolve()
    if not root.is_dir():
        fail("citation book root does not exist")
    styles = {
        "citations/chicago-author-date.csl": ("91fa1fe9787e737dff0c15d7cf8254c9f2bab4ebb4dccf4553a1f991ebddb7d1", "author-date", "Chicago Manual of Style 17th edition (author-date)"),
        "citations/ieee.csl": ("b4c7619fc16c45a31e4cc3271eab94ffe83192d3b4c7fc729470a3b459448de3", "numeric", "IEEE Reference Guide version 11.29.2023"),
    }
    for relative in sorted(styles):
        digest, citation_format, title = styles[relative]
        content = (root / relative).read_bytes()
        text = content.decode("utf-8")
        if hashlib.sha256(content).hexdigest() != digest:
            fail(f"citation style {relative} changed; review its provenance and update the locked hash")
        if f"<title>{title}</title>" not in text:
            fail(f"citation style {relative} has the wrong title")
        if f'<category citation-format="{citation_format}"/>' not in text:
            fail(f"citation style {relative} does not declare {citation_format} format")
        if not re.search(r'<rights\s+license="[^"]+">', text):
            fail(f"citation style {relative} has no declared license")
    config = (root / "_quarto.yml").read_text(encoding="utf-8")
    if not re.search(r"^bibliography:\s*references\.bib\s*$", config, re.M):
        fail("default bibliography must be references.bib")
    if not re.search(r"^csl:\s*citations/chicago-author-date\.csl\s*$", config, re.M):
        fail("default citation style must be the locked Chicago author-date file")
    numeric = (root / "_quarto-citation-numeric.yml").read_text(encoding="utf-8")
    if not re.search(r"^csl:\s*citations/ieee\.csl\s*$", numeric, re.M):
        fail("numeric profile must select the locked IEEE file")
    for profile in ("_quarto-typst.yml", "_quarto-typst-6x9.yml", "_quarto-typst-review.yml"):
        if not re.search(r"^\s+citeproc:\s*true\s*$", (root / profile).read_text(encoding="utf-8"), re.M):
            fail(f"Typst profile {profile} must run citations through Pandoc citeproc")
    if len(re.findall(r"\{#refs\}", (root / "references.qmd").read_text(encoding="utf-8"))) != 1:
        fail("expected exactly one shared references division")
    bibliography_path = root / "references.bib"
    keys, key_lines = set(), {}
    for line_number, line in enumerate(bibliography_path.read_text(encoding="utf-8").splitlines(), 1):
        match = re.match(r"^\s*@[A-Za-z]+\s*\{\s*([^,\s]+)\s*,", line)
        if not match:
            continue
        key = match.group(1)
        if key in keys:
            fail(f"{bibliography_path}:{line_number}: duplicate bibliography key {key}; first declared at line {key_lines[key]}")
        keys.add(key)
        key_lines[key] = line_number
    if not keys:
        fail("bibliography has no entries")
    nocite = set()
    block = re.search(r"^nocite:\s*\|\s*\n((?:[ \t]+.*(?:\n|\Z))*)", config, re.M)
    if block:
        nocite.update(re.findall(r"@([A-Za-z0-9][A-Za-z0-9_.:+-]*)", block.group(1)))
    nocite.update(re.findall(r'''^nocite:\s*["']?@([A-Za-z0-9][A-Za-z0-9_.:+-]*)''', config, re.M))
    if re.search(r"^nocite:", config, re.M) and not nocite:
        fail("nocite metadata must list at least one explicit bibliography key")
    for key in sorted(nocite):
        if key not in keys:
            fail(f"nocite metadata references missing bibliography key {key}")
    prefixes = {"sec", "fig", "tbl", "eq", "lst", "thm", "lem", "cor", "prp", "cnj", "def", "exm", "exr", "sol", "nte", "wrn", "tip", "imp", "cau", "rem", "alg"}
    cited, calls = set(), {}
    for source in sorted(path for path in root.rglob("*.qmd") if ".quarto" not in path.parts and "_build" not in path.parts):
        fence_char, fence_length = None, 0
        for line_number, line in enumerate(source.read_text(encoding="utf-8").splitlines(), 1):
            if fence_char:
                if re.fullmatch(rf"\s*{re.escape(fence_char)}{{{fence_length},}}\s*", line):
                    fence_char, fence_length = None, 0
                continue
            fence = re.match(r"^\s*(`{3,}|~{3,})", line)
            if fence:
                fence_char, fence_length = fence.group(1)[0], len(fence.group(1))
                continue
            line = re.sub(r"`+[^`]*`+", "", line)
            line = re.sub(r"https?://\S+", "", line)
            line = re.sub(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+", "", line)
            for key in re.findall(r"(?<![A-Za-z0-9_])@([A-Za-z0-9][A-Za-z0-9_.:+-]*)", line):
                if key in keys:
                    cited.add(key)
                    calls[key] = calls.get(key, 0) + 1
                elif key.split("-", 1)[0] not in prefixes:
                    fail(f"{source}:{line_number}: citation references missing bibliography key {key}")
    for key in sorted(keys):
        if key not in cited and key not in nocite:
            fail(f"bibliography key {key} is unused; cite it or list it explicitly in nocite metadata")
    print(f"ok: citations ({len(keys)} bibliography keys; {len(cited)} cited; {len(nocite)} explicit nocite; {len(styles)} locked styles; shared Pandoc citeproc path)")


if __name__ == "__main__":
    try:
        main()
    except (OSError, UnicodeError, RuntimeError) as error:
        print(error, file=sys.stderr)
        raise SystemExit(1)
