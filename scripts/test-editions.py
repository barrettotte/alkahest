"""Exercise valid, invalid, and staged whole-book edition contracts."""

import copy
import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR / "lib"))

from alkahest.common import ContractError
from alkahest.editions import load_editions
from alkahest.preview import validate_preview_presentation


BASE = json.loads((SCRIPT_DIR.parent / "book" / "editions.json").read_text(encoding="utf-8"))


def validate(registry):
    with tempfile.NamedTemporaryFile("w", suffix=".json", encoding="utf-8") as handle:
        json.dump(registry, handle)
        handle.flush()
        return load_editions(handle.name)


def expect_failure(name, expected, mutate):
    registry = copy.deepcopy(BASE)
    mutate(registry)
    try:
        validate(registry)
    except ContractError as error:
        if expected not in str(error):
            raise RuntimeError(f"error: edition fixture {name} missed diagnostic '{expected}': {error}")
    else:
        raise RuntimeError(f"error: edition fixture {name} unexpectedly passed")


def preview_fixture(root):
    for relative in (
        "book/_quarto.yml",
        "book/_quarto-preview.yml",
        "book/index.qmd",
        "book/filters/preview.lua",
        "scripts/render.sh",
    ):
        target = root / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(SCRIPT_DIR.parent / relative, target)


def replace(path, old, new):
    text = path.read_text(encoding="utf-8")
    if old not in text:
        raise RuntimeError(f"error: preview fixture cannot find {old!r}")
    path.write_text(text.replace(old, new, 1), encoding="utf-8")


def expect_preview_failure(parent, name, expected, mutate):
    root = parent / name
    preview_fixture(root)
    mutate(root)
    try:
        validate_preview_presentation(root)
    except ContractError as error:
        if expected not in str(error):
            raise RuntimeError(
                f"error: preview fixture {name} missed diagnostic '{expected}': {error}"
            ) from error
    else:
        raise RuntimeError(f"error: preview fixture {name} unexpectedly passed")


def main():
    validate(copy.deepcopy(BASE))
    expect_failure("missing-edition", "editions must be exactly", lambda r: r["editions"].pop("abridged"))
    expect_failure("drifted-format", "edition 'print' has invalid formats", lambda r: r["editions"]["print"].update(formats=["latex"]))
    expect_failure("unknown-source", "references unknown source 'missing'", lambda r: r["structures"]["preview"]["chapters"][1]["sources"].__setitem__(0, "missing"))
    expect_failure("duplicate-source", "repeats source 'reference'", lambda r: r["structures"]["full"]["chapters"][2]["sources"].append("reference"))
    expect_failure("private-leak", "public edition 'abridged' includes private source", lambda r: r["sources"]["reference"].update(availability="private"))
    def online_in_full(registry):
        registry["sources"]["online-lab-notes"]["formats"] = ["html", "epub", "typst", "latex"]
        registry["structures"]["full"]["appendices"][1]["sources"].append("online-lab-notes")
    expect_failure("online-in-full", "structure 'full' does not select exactly", online_in_full)
    expect_failure("supplemental-in-web", "structure 'web' does not select exactly", lambda r: r["structures"]["web"]["appendices"][2]["sources"].__setitem__(0, "supplemental-workbook"))
    expect_failure("long-preview", "preview structure must contain one or two", lambda r: r["structures"]["preview"]["chapters"][1]["sources"].append("math"))
    expect_failure("complete-abridged", "structure 'abridged' must be a nonempty proper subset", lambda r: r["structures"].__setitem__("abridged", copy.deepcopy(r["structures"]["full"])))
    with tempfile.TemporaryDirectory(prefix="alkahest-preview-presentation.") as directory:
        parent = Path(directory)
        valid = parent / "valid"
        preview_fixture(valid)
        presentation = validate_preview_presentation(valid)
        if presentation != {
            "identifier": "urn:uuid:551be2aa-8be0-4078-b9dc-3f29e1088092",
            "links": 0,
            "watermark": "PREVIEW",
        }:
            raise RuntimeError("error: preview presentation fixture returned wrong facts")
        expect_preview_failure(
            parent,
            "missing-placeholder",
            "one edition-preview presentation placeholder",
            lambda root: replace(
                root / "book/index.qmd",
                "alkahest-preview-placeholder",
                "missing-preview-placeholder",
            ),
        )
        expect_preview_failure(
            parent,
            "unsafe-url",
            "must be empty or an absolute HTTPS URL",
            lambda root: replace(
                root / "book/_quarto-preview.yml",
                'full-edition-url: ""',
                'full-edition-url: "http://example.com/book"',
            ),
        )
        expect_preview_failure(
            parent,
            "disabled-presentation",
            "preview presentation must be enabled",
            lambda root: replace(
                root / "book/_quarto-preview.yml",
                "    enabled: true",
                "    enabled: false",
            ),
        )
        expect_preview_failure(
            parent,
            "unsafe-watermark",
            "short uppercase display text",
            lambda root: replace(
                root / "book/_quarto-preview.yml",
                '      text: "PREVIEW"',
                '      text: "Preview #unsafe"',
            ),
        )
    for edition in ("public", "private", "preview", "abridged"):
        subprocess.run(
            [sys.executable, str(SCRIPT_DIR / "stage-edition.py"), edition],
            check=True,
            stdout=subprocess.DEVNULL,
        )
    stage_parent = SCRIPT_DIR.parent / "book" / "_build" / "staging" / "editions"
    if (stage_parent / "public" / "private").exists():
        raise RuntimeError("error: public stage exposes private source directory")
    if not (stage_parent / "private" / "private" / "working-notes.qmd").is_file():
        raise RuntimeError("error: private stage omits selected private source")
    if (stage_parent / "preview" / "math.qmd").exists():
        raise RuntimeError("error: preview stage contains omitted main chapter")
    if (stage_parent / "abridged" / "layout-stress.qmd").exists():
        raise RuntimeError("error: abridged stage contains omitted main chapter")
    print("ok: edition fixtures (valid registries and preview presentation; 13 invalid contracts rejected; staged public/private and reduced-book isolation)")


if __name__ == "__main__":
    try:
        main()
    except (ContractError, OSError, RuntimeError, subprocess.CalledProcessError) as error:
        print(error, file=sys.stderr)
        raise SystemExit(1)
