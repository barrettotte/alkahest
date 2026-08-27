"""Validate the shared bibliography and citation calls."""

from __future__ import annotations

import hashlib
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
STYLE = "citations/chicago-author-date.csl"
STYLE_SHA256 = "91fa1fe9787e737dff0c15d7cf8254c9f2bab4ebb4dccf4553a1f991ebddb7d1"
CROSS_REFERENCE_PREFIXES = {
    "cnj",
    "cor",
    "def",
    "eq",
    "exm",
    "exr",
    "fig",
    "lem",
    "lst",
    "nte",
    "prp",
    "sec",
    "tbl",
    "thm",
    "wrn",
}


def fail(message: str) -> None:
    raise RuntimeError(f"error: {message}")


def main() -> None:
    root = ROOT / "book"
    style = root / STYLE
    if hashlib.sha256(style.read_bytes()).hexdigest() != STYLE_SHA256:
        fail("the Chicago author-date citation style changed")
    config = (root / "_quarto.yml").read_text(encoding="utf-8")
    if f"csl: {STYLE}" not in config or "bibliography: references.bib" not in config:
        fail("the reference book must use its shared bibliography and citation style")
    if "citeproc: true" not in (root / "_quarto-typst.yml").read_text(encoding="utf-8"):
        fail("Typst must use Pandoc citeproc")
    keys = set(
        re.findall(
            r"^\s*@[A-Za-z]+\s*\{\s*([^,\s]+)\s*,",
            (root / "references.bib").read_text(encoding="utf-8"),
            re.MULTILINE,
        )
    )
    if not keys:
        fail("the bibliography is empty")
    calls: set[str] = set()
    for source in root.rglob("*.qmd"):
        if "_build" in source.parts:
            continue
        text = re.sub(r"```.*?```", "", source.read_text(encoding="utf-8"), flags=re.DOTALL)
        calls.update(
            call.rstrip(".,:")
            for call in re.findall(
                r"(?<![A-Za-z0-9_])@([A-Za-z0-9][A-Za-z0-9_.:+-]*)",
                text,
            )
        )
    cited = calls & keys
    nocite = (
        set(
            re.findall(
                r"@([A-Za-z0-9][A-Za-z0-9_.:+-]*)",
                config.split("nocite:", 1)[-1],
            )
        )
        if "nocite:" in config
        else set()
    )
    unknown = {
        call for call in calls - keys if call.partition("-")[0] not in CROSS_REFERENCE_PREFIXES
    }
    if unknown:
        fail(f"citation references missing bibliography key: {min(unknown)}")
    unused = keys - cited - nocite
    if unused:
        fail(f"bibliography key is neither cited nor explicitly included: {min(unused)}")
    print(f"ok: citations ({len(keys)} bibliography keys; {len(cited)} cited)")


if __name__ == "__main__":
    try:
        main()
    except (OSError, UnicodeError, RuntimeError) as error:
        print(error, file=sys.stderr)
        raise SystemExit(1) from None
