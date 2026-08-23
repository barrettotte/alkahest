"""Produce local build measurements and locked-toolchain inventory reports."""

from __future__ import annotations

import argparse
import hashlib
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from .author_project import TOOLCHAIN_IMAGE

ROOT = Path(__file__).resolve().parents[2]


class ReportError(RuntimeError):
    """Report a missing prerequisite or failed report command."""


@dataclass(frozen=True)
class BuildTarget:
    """One measured primary publication target."""

    profile: str
    label: str
    artifact: str


BUILD_TARGETS = (
    BuildTarget("html", "HTML", "book/_build/html"),
    BuildTarget("epub", "EPUB", "book/_build/epub/Alkahest-Reference-Book.epub"),
    BuildTarget(
        "typst",
        "Typst PDF",
        "book/_build/print/7x10/typst/Alkahest-Reference-Book.pdf",
    ),
    BuildTarget(
        "latex",
        "LuaLaTeX PDF",
        "book/_build/print/7x10/latex/Alkahest-Reference-Book.pdf",
    ),
)

SOURCE_LOCKS = (
    ("Ubuntu", "ALKAHEST_UBUNTU_SNAPSHOT"),
    ("Chrome archive", "ALKAHEST_CHROME_ARCHIVE_URL"),
    ("Chrome archive SHA-256", "ALKAHEST_CHROME_ARCHIVE_SHA256"),
    ("EPUBCheck archive", "ALKAHEST_EPUBCHECK_ARCHIVE_URL"),
    ("EPUBCheck archive SHA-256", "ALKAHEST_EPUBCHECK_ARCHIVE_SHA256"),
    ("veraPDF archive", "ALKAHEST_VERAPDF_ARCHIVE_URL"),
    ("veraPDF archive SHA-256", "ALKAHEST_VERAPDF_ARCHIVE_SHA256"),
    ("Libertinus archive", "ALKAHEST_LIBERTINUS_ARCHIVE_URL"),
    ("Libertinus archive SHA-256", "ALKAHEST_LIBERTINUS_ARCHIVE_SHA256"),
    ("Source Code Pro OTF archive", "ALKAHEST_SOURCE_CODE_PRO_OTF_ARCHIVE_URL"),
    (
        "Source Code Pro OTF archive SHA-256",
        "ALKAHEST_SOURCE_CODE_PRO_OTF_ARCHIVE_SHA256",
    ),
    ("Source Code Pro WOFF2 archive", "ALKAHEST_SOURCE_CODE_PRO_WOFF2_ARCHIVE_URL"),
    (
        "Source Code Pro WOFF2 archive SHA-256",
        "ALKAHEST_SOURCE_CODE_PRO_WOFF2_ARCHIVE_SHA256",
    ),
    ("uv archive", "ALKAHEST_UV_ARCHIVE_URL"),
    ("uv archive SHA-256", "ALKAHEST_UV_ARCHIVE_SHA256"),
    ("Node archive", "ALKAHEST_NODE_ARCHIVE_URL"),
    ("Node archive SHA-256", "ALKAHEST_NODE_ARCHIVE_SHA256"),
    ("Vale archive", "ALKAHEST_VALE_ARCHIVE_URL"),
    ("Vale archive SHA-256", "ALKAHEST_VALE_ARCHIVE_SHA256"),
    ("TeX Live", "ALKAHEST_TEXLIVE_REPOSITORY"),
    ("TeX Live database SHA-256", "ALKAHEST_TEXLIVE_TLPDB_SHA256"),
)

TEX_PACKAGES = (
    "lm",
    "lm-math",
    "babel-english",
    "babel-french",
    "babel-german",
    "babel-greek",
    "babel-hebrew",
    "babel-russian",
    "hyphen-english",
    "hyphen-french",
    "hyphen-german",
    "hyphen-greek",
    "hyphen-russian",
    "ruhyphen",
    "latex",
    "l3kernel",
    "luamml",
    "caption",
    "fvextra",
    "pgf",
    "tcolorbox",
    "tikzfill",
    "pdfcol",
    "fontawesome5",
    "latex-lab",
    "pdfmanagement",
    "tagpdf",
    "koma-script",
)

HASH_PATHS = (
    "{QUARTO_CHROMIUM}",
    "{EPUBCHECK_JAR}",
    "/opt/quarto/bin/tools/x86_64/typst",
    "/opt/quarto/bin/tools/x86_64/pandoc",
    "/usr/local/bin/uv",
    "/opt/node/bin/node",
    "/usr/local/bin/vale",
    "/opt/alkahest/writing/package-lock.json",
    "/opt/alkahest/writing/node_modules/cspell/bin.mjs",
    "/opt/alkahest/writing/node_modules/axe-core/axe.min.js",
    "/opt/alkahest/writing/node_modules/@daisy/ace-cli/bin/ace.js",
    "/opt/alkahest/tools-project/uv.lock",
    "/opt/alkahest/tools/lib/python3.13/site-packages/schemdraw/__init__.py",
    "/opt/alkahest/tools/lib/python3.13/site-packages/rdkit/Chem/rdchem.so",
    "/opt/quarto/share/formats/html/mermaid/mermaid.min.js",
    "/opt/quarto/share/js/graphviz-wasm.js",
    "/opt/quarto/share/wasm/graphvizlib.wasm",
    "/opt/TinyTeX/bin/x86_64-linux/luahbtex",
    "/usr/bin/rsvg-convert",
    "/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSansMono-Bold.ttf",
    "/opt/TinyTeX/texmf-dist/fonts/opentype/public/lm/lmroman10-regular.otf",
    "/opt/TinyTeX/texmf-dist/fonts/opentype/public/lm/lmroman10-bold.otf",
    "/opt/TinyTeX/texmf-dist/fonts/opentype/public/lm/lmroman10-italic.otf",
    "/opt/TinyTeX/texmf-dist/fonts/opentype/public/lm/lmmonolt10-bold.otf",
    "/opt/TinyTeX/texmf-dist/fonts/opentype/public/lm-math/latinmodern-math.otf",
    "/usr/local/share/fonts/alkahest/libertinus/LibertinusSerif-Regular.otf",
    "/usr/local/share/fonts/alkahest/libertinus/LibertinusSerif-Bold.otf",
    "/usr/local/share/fonts/alkahest/libertinus/LibertinusSerif-Italic.otf",
    "/usr/local/share/fonts/alkahest/libertinus/LibertinusSerif-BoldItalic.otf",
    "/usr/local/share/fonts/alkahest/libertinus/LibertinusSerifDisplay-Regular.otf",
    "/usr/local/share/fonts/alkahest/libertinus/LibertinusSans-Regular.otf",
    "/usr/local/share/fonts/alkahest/libertinus/LibertinusSans-Bold.otf",
    "/usr/local/share/fonts/alkahest/libertinus/LibertinusSans-Italic.otf",
    "/usr/local/share/fonts/alkahest/libertinus/LibertinusMath-Regular.otf",
    "/usr/local/share/fonts/alkahest/source-code-pro/SourceCodePro-Regular.otf",
    "/usr/local/share/fonts/alkahest/source-code-pro/SourceCodePro-Bold.otf",
    "/usr/local/share/fonts/alkahest/source-code-pro/SourceCodePro-It.otf",
    "/usr/local/share/fonts/alkahest/source-code-pro/SourceCodePro-BoldIt.otf",
)


def executable(name: str) -> str:
    """Resolve a required command."""
    path = shutil.which(name)
    if path is None:
        raise ReportError(f"{name} is required for this report")
    return path


def run(
    arguments: list[str], *, environment: dict[str, str] | None = None
) -> subprocess.CompletedProcess[str]:
    """Run a report command and capture its text output."""
    return subprocess.run(  # noqa: S603 - callers use resolved or fixed commands
        arguments,
        cwd=ROOT,
        env=environment,
        capture_output=True,
        text=True,
        check=False,
    )


def require_image() -> str:
    """Require a usable rootless Podman image and return Podman's path."""
    if os.geteuid() == 0:
        raise ReportError("publishing reports must be run as a non-root host user")
    podman = executable("podman")
    result = run([podman, "image", "exists", TOOLCHAIN_IMAGE])
    if result.returncode:
        raise ReportError(
            "publishing image is not available locally; run ./scripts/bootstrap.sh once "
            "while connected to the network"
        )
    return podman


def pdf_metadata(podman: str, artifact: str) -> str:
    """Read stable page metadata with the pinned Poppler."""
    result = run(
        [
            podman,
            "run",
            "--rm",
            "--pull=never",
            "--network=none",
            "--userns=keep-id",
            "--security-opt",
            "label=disable",
            "--volume",
            f"{ROOT}:/workspace:ro",
            "--workdir",
            "/workspace",
            "--entrypoint",
            "pdfinfo",
            TOOLCHAIN_IMAGE,
            artifact,
        ]
    )
    diagnostics = [
        line
        for line in result.stderr.splitlines()
        if line != "Syntax Error: Suspects object is wrong type (boolean)"
    ]
    if result.returncode or diagnostics:
        raise ReportError("pdfinfo failed: " + "\n".join(diagnostics))
    pages = re.search(r"^Pages:\s+(\d+)", result.stdout, re.MULTILINE)
    size = re.search(r"^Page size:\s+([\d.]+) x ([\d.]+) pts", result.stdout, re.MULTILINE)
    if pages is None or size is None:
        raise ReportError("pdfinfo omitted build-report metadata")
    return f"{pages.group(1)} pages; {size.group(1)} x {size.group(2)} pt"


def build_report() -> int:
    """Render primary formats and print their timing, size, and warnings."""
    podman = require_image()
    rows: list[str] = []
    warnings: list[str] = []
    with tempfile.TemporaryDirectory(prefix="alkahest-build-report-") as directory:
        for target in BUILD_TARGETS:
            log_path = Path(directory) / f"{target.profile}.log"
            start = time.monotonic_ns()
            result = run([sys.executable, "-m", "alkahest", "render", target.profile])
            duration = (time.monotonic_ns() - start) / 1_000_000_000
            log = result.stdout + result.stderr
            log_path.write_text(log, encoding="utf-8")
            if result.returncode:
                raise ReportError(f"{target.label} render failed:\n{log}")
            artifact = ROOT / target.artifact
            if target.profile == "html":
                files = [path for path in artifact.rglob("*") if path.is_file()]
                size = sum(path.stat().st_size for path in files)
                details = f"{len(files)} files"
            else:
                size = artifact.stat().st_size
                details = (
                    pdf_metadata(podman, target.artifact)
                    if artifact.suffix == ".pdf"
                    else "single-file EPUB"
                )
            target_warnings = re.findall(r"WARN: .*", log)
            rows.append(
                f"| {target.label} | {duration:.2f} | {size} | {len(target_warnings)} | {details} |"
            )
            warnings.extend(f"- {target.label}: {warning}" for warning in target_warnings)

    print("# Local build report\n")
    print(f"- Captured: {datetime.now().astimezone().isoformat(timespec='seconds')}")
    print(f"- Image: `{TOOLCHAIN_IMAGE}`")
    version = run([podman, "--version"])
    print(f"- Podman: {version.stdout.strip()}")
    print(f"- Host logical CPUs: {os.cpu_count() or 'unknown'}")
    print(
        "- Method: one sequential run per format; network disabled; fresh ephemeral "
        "container caches; existing artifacts overwritten in place\n"
    )
    print("| Target | Seconds | Bytes | Warnings | Details |")
    print("|---|---:|---:|---:|---|")
    print("\n".join(rows))
    print("\n## Captured warnings\n")
    print("\n".join(warnings) if warnings else "- None.")
    return 0


def output(arguments: list[str], *, first_line: bool = False) -> str:
    """Run an inventory command and return normalized combined output."""
    result = run(arguments)
    text = (result.stdout + result.stderr).strip()
    if result.returncode:
        raise ReportError(f"toolchain command failed ({' '.join(arguments)}): {text}")
    return text.splitlines()[0] if first_line else text


def version(label: str, arguments: list[str], pattern: str = "", *, first_line=False) -> None:
    """Print one normalized tool version."""
    value = output(arguments, first_line=first_line)
    if pattern:
        value = re.sub(pattern, "", value)
    print(f"  {label}: {value}")


def sha256(path: Path) -> str:
    """Hash one installed toolchain file."""
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def toolchain_inside() -> int:
    """Inspect the installed image from within that image."""
    print("Immutable sources")
    for label, name in SOURCE_LOCKS:
        print(f"  {label}: {os.environ.get(name, '')}")

    print("Tools")
    version("Quarto", [executable("quarto"), "--version"], first_line=True)
    version("Pandoc", [executable("quarto"), "pandoc", "--version"], r"^pandoc ", first_line=True)
    version("Typst", [executable("quarto"), "typst", "--version"], r"^typst ", first_line=True)
    version(
        "LuaHBTeX",
        [executable("lualatex"), "--version"],
        r"^This is LuaHBTeX, Version ",
        first_line=True,
    )
    version(
        "Chrome for Testing",
        [os.environ["QUARTO_CHROMIUM"], "--version"],
        r"^Google Chrome for Testing ",
        first_line=True,
    )
    version(
        "EPUBCheck",
        [executable("java"), "-jar", os.environ["EPUBCHECK_JAR"], "--version"],
        r"^EPUBCheck v",
        first_line=True,
    )
    version("veraPDF", [executable("verapdf"), "--version"], r"^veraPDF ", first_line=True)
    java = output([executable("java"), "-version"], first_line=True)
    match = re.search(r'"([^"]+)"', java)
    print(f"  OpenJDK: {match.group(1) if match else java}")
    version("Poppler", [executable("pdfinfo"), "-v"], r"^pdfinfo version ", first_line=True)
    version("Python system runtime", ["/usr/bin/python3", "--version"], r"^Python ")
    version("Python uv environment", ["/opt/alkahest/tools/bin/python", "--version"], r"^Python ")
    version("uv", [executable("uv"), "--version"], r"^uv ")
    version("Node", [executable("node"), "--version"], r"^v")
    version("npm", [executable("npm"), "--version"])
    version("Vale", [executable("vale"), "--version"], r"^vale version ")
    version("CSpell", [executable("cspell"), "--version"])
    version(
        "axe-core",
        [
            executable("node"),
            "-p",
            'require("/opt/alkahest/writing/node_modules/axe-core/package.json").version',
        ],
    )
    version("Ace by DAISY", [executable("ace-cli"), "--version"])
    version(
        "Schemdraw",
        [
            "/opt/alkahest/tools/bin/python",
            "-c",
            "import schemdraw; print(schemdraw.__version__)",
        ],
    )
    version(
        "RDKit",
        [
            "/opt/alkahest/tools/bin/python",
            "-c",
            "from rdkit import rdBase; print(rdBase.rdkitVersion)",
        ],
    )
    version("librsvg", [executable("rsvg-convert"), "--version"], r"^rsvg-convert version ")

    print("Font and TeX packages")
    for package in (
        "fonts-dejavu-core",
        "openjdk-11-jre-headless",
        "poppler-utils",
        "python3",
        "python3-minimal",
        "librsvg2-bin",
    ):
        print("  " + output([executable("dpkg-query"), "-W", package]))
    tex = output([executable("tlmgr"), "info", "--only-installed", *TEX_PACKAGES])
    for line in tex.splitlines():
        if line.startswith(("package:", "revision:", "cat-version:")):
            print(f"  {line}")

    print("Selected fonts")
    for label, face in (
        ("Body", "Libertinus Serif"),
        ("Display", "Libertinus Serif Display"),
        ("Headings", "Libertinus Sans"),
        ("Math", "Libertinus Math"),
        ("Code", "Source Code Pro"),
    ):
        value = output([executable("fc-match"), "--format", "%{family[0]} %{style[0]}\n", face])
        print(f"  {label}: {value}")

    print("SHA-256")
    values = {
        "QUARTO_CHROMIUM": os.environ["QUARTO_CHROMIUM"],
        "EPUBCHECK_JAR": os.environ["EPUBCHECK_JAR"],
    }
    for template in HASH_PATHS:
        path = Path(template.format(**values))
        print(f"{sha256(path)}  {path}")
    return 0


def toolchain_report() -> int:
    """Run the installed-image inventory offline."""
    podman = require_image()
    result = subprocess.run(  # noqa: S603 - fixed offline image inspection
        [
            podman,
            "run",
            "--rm",
            "--pull=never",
            "--network=none",
            "--security-opt",
            "label=disable",
            "--volume",
            f"{ROOT}:/workspace:ro",
            "--workdir",
            "/workspace",
            "--entrypoint",
            "/opt/alkahest/tools/bin/python",
            TOOLCHAIN_IMAGE,
            "-m",
            "alkahest.reporting",
            "toolchain",
            "--inside",
        ],
        cwd=ROOT,
        check=False,
    )
    return result.returncode


def main(arguments: list[str] | None = None) -> int:
    """Dispatch one report."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("report", choices=("build", "toolchain"))
    parser.add_argument("--inside", action="store_true", help=argparse.SUPPRESS)
    options = parser.parse_args(arguments)
    try:
        if options.report == "build":
            if options.inside:
                raise ReportError("build reports run on the host")
            return build_report()
        if options.inside:
            return toolchain_inside()
        return toolchain_report()
    except (OSError, UnicodeError, ReportError) as error:
        print(f"error: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
