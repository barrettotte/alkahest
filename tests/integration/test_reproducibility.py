"""Exercise reproducibility policy, metadata, and exact-fingerprint failures."""

import json
import os
import shutil
import subprocess
import sys
import tempfile
import zipfile
from datetime import UTC, datetime
from pathlib import Path

from alkahest.markup import canonicalize_markup
from alkahest.process import run_process

SCRIPT_DIR = Path(__file__).resolve().parent
ROOT = SCRIPT_DIR.parents[1]
VALIDATOR = ("-m", "alkahest.checks.reproducibility")


def policy(root):
    return json.loads((root / "book/reproducibility.json").read_text(encoding="utf-8"))


def write_policy(root, data):
    (root / "book/reproducibility.json").write_text(
        json.dumps(data, indent=2) + "\n", encoding="utf-8"
    )


def write_epub(path, data):
    epoch = data["source_date_epoch"]
    stamp = datetime.fromtimestamp(epoch, UTC)
    date_time = (stamp.year, stamp.month, stamp.day, stamp.hour, stamp.minute, stamp.second)
    opf = (
        "<package><metadata>"
        f"<identifier>{data['epub_identifier']}</identifier>"
        f"<date>{data['source_date_utc']}</date>"
        f"<modified>{data['source_date_utc']}</modified>"
        "</metadata></package>"
    ).encode()
    path.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(path, "w") as archive:
        mimetype = zipfile.ZipInfo("mimetype", date_time)
        mimetype.compress_type = zipfile.ZIP_STORED
        archive.writestr(mimetype, b"application/epub+zip")
        content = zipfile.ZipInfo("EPUB/content.opf", date_time)
        content.compress_type = zipfile.ZIP_DEFLATED
        archive.writestr(content, opf)


def create_fixture(root):
    for relative in (
        "book/reproducibility.json",
        "book/_quarto-epub.yml",
    ):
        target = root / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(ROOT / relative, target)
    data = policy(root)
    for artifact in data["contract"]["artifacts"]:
        path = root / artifact["path"]
        if artifact["kind"] == "directory":
            path.mkdir(parents=True)
            (path / "index.html").write_text(
                "<!doctype html><title>Fixture</title>\n", encoding="utf-8"
            )
        elif artifact["kind"] == "epub":
            write_epub(path, data)
        else:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(b"%PDF-1.7\n<</CreationDate(D:20260821000000Z)>>\n%%EOF\n")


def run(root, *arguments):
    environment = os.environ.copy()
    environment["ALKAHEST_REPRO_ROOT"] = str(root)
    return run_process(
        [sys.executable, *VALIDATOR, *arguments],
        env=environment,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        encoding="utf-8",
        check=False,
    )


def expect_failure(parent, name, expected, mutate, *arguments):
    root = parent / name
    create_fixture(root)
    mutate(root)
    result = run(root, *arguments)
    if result.returncode == 0:
        raise RuntimeError(f"invalid reproducibility fixture unexpectedly passed: {name}")
    if expected not in result.stdout:
        raise RuntimeError(
            f"reproducibility fixture '{name}' missed diagnostic '{expected}':\n{result.stdout}"
        )


def mutate_policy(root, mutate):
    data = policy(root)
    mutate(data)
    write_policy(root, data)


def mutate_epub_timestamp(root):
    policy(root)
    path = root / "book/_build/epub/Alkahest-Reference-Book.epub"
    with zipfile.ZipFile(path) as archive:
        opf = archive.read("EPUB/content.opf")
    with zipfile.ZipFile(path, "w") as archive:
        archive.writestr("mimetype", b"application/epub+zip")
        archive.writestr("EPUB/content.opf", opf)


def main():
    first = '<span id="term" class="entry" data-z="last" data-a="first">Text</span>'
    second = '<span id="term" class="entry" data-a="first" data-z="last">Text</span>'
    if canonicalize_markup(first) != canonicalize_markup(second):
        raise RuntimeError("markup canonicalizer did not stabilize attribute order")
    aria_first = '<div class="entry" role="definition" aria-labelledby="term" lang="en">'
    aria_second = '<div class="entry" lang="en" aria-labelledby="term" role="definition">'
    if canonicalize_markup(aria_first) != canonicalize_markup(aria_second):
        raise RuntimeError("markup canonicalizer did not stabilize ARIA attribute order")
    script = "<script>const sample = \"<span data-z='2' data-a='1'>\";</script>"
    if canonicalize_markup(script) != script:
        raise RuntimeError("markup canonicalizer changed raw script content")

    with tempfile.TemporaryDirectory(prefix="alkahest-reproducibility-tests.") as directory:
        parent = Path(directory)
        valid = parent / "valid"
        create_fixture(valid)
        result = run(valid, "--artifacts")
        if result.returncode != 0:
            raise RuntimeError("valid reproducibility fixture failed:\n" + result.stdout)

        expect_failure(
            parent,
            "date-mismatch",
            "source_date_utc does not match source_date_epoch",
            lambda root: mutate_policy(
                root, lambda data: data.__setitem__("source_date_utc", "2026-08-22T00:00:00Z")
            ),
        )
        expect_failure(
            parent,
            "identifier-drift",
            "does not declare the locked publication identifier",
            lambda root: (root / "book/_quarto-epub.yml").write_text(
                (root / "book/_quarto-epub.yml")
                .read_text(encoding="utf-8")
                .replace("f6757ec7", "a6757ec7"),
                encoding="utf-8",
            ),
        )
        expect_failure(
            parent,
            "epub-timestamp",
            "non-reproducible member timestamps",
            mutate_epub_timestamp,
            "--artifacts",
        )
        expect_failure(
            parent,
            "pdf-timestamp",
            "does not retain the reproducible creation timestamp",
            lambda root: (
                root / "book/_build/print/7x10/typst/Alkahest-Reference-Book.pdf"
            ).write_bytes(b"%PDF-1.7\n<</CreationDate(D:20260822000000Z)>>\n%%EOF\n"),
            "--artifacts",
        )
        expect_failure(
            parent,
            "missing-artifact",
            "missing artifact file",
            lambda root: (
                root / "book/_build/review/letter/latex/Alkahest-Reference-Book.pdf"
            ).unlink(),
            "--artifacts",
        )

        comparison = parent / "comparison"
        create_fixture(comparison)
        baseline = comparison / "baseline.json"
        result = run(comparison, "--snapshot", str(baseline))
        if result.returncode != 0:
            raise RuntimeError("snapshot fixture failed:\n" + result.stdout)
        (comparison / "book/_build/html/index.html").write_text(
            "<!doctype html><title>Changed</title>\n", encoding="utf-8"
        )
        result = run(comparison, "--compare", str(baseline))
        if result.returncode == 0 or "changed exact artifact content: html" not in result.stdout:
            raise RuntimeError("exact-comparison fixture missed HTML drift:\n" + result.stdout)

    print(
        "ok: reproducibility fixtures (canonical markup and exact artifacts accepted; "
        "6 policy, metadata, missing-output, and content-drift failures rejected)"
    )


def test_contract():
    result = main()
    assert result in (None, 0)
