"""Stage locked webfonts before Quarto renders."""

from __future__ import annotations

import argparse
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
WEBFONT_SOURCE = Path("/opt/alkahest/fonts/web")
FONT_LICENSE_SOURCE = Path("/usr/local/share/doc/fonts")

LIBERTINUS_FACES = (
    "LibertinusSerif-Regular.woff2",
    "LibertinusSerif-Italic.woff2",
    "LibertinusSerif-Bold.woff2",
    "LibertinusSerif-BoldItalic.woff2",
    "LibertinusSerifDisplay-Regular.woff2",
    "LibertinusSans-Regular.woff2",
    "LibertinusSans-Italic.woff2",
    "LibertinusSans-Bold.woff2",
)
SOURCE_CODE_PRO_FACES = (
    "SourceCodePro-Regular.otf.woff2",
    "SourceCodePro-It.otf.woff2",
    "SourceCodePro-Bold.otf.woff2",
    "SourceCodePro-BoldIt.otf.woff2",
)


class StagingError(RuntimeError):
    """Report an unavailable or failed staging input."""


def copy_if_changed(source: Path, destination: Path) -> None:
    """Copy one locked asset only when its bytes differ."""
    if not source.is_file():
        raise StagingError(f"locked webfont asset is missing: {source}")
    if destination.is_file() and source.read_bytes() == destination.read_bytes():
        return
    shutil.copyfile(source, destination)
    destination.chmod(0o644)


def stage_webfonts() -> None:
    """Stage locked WOFF2 faces and their license notices."""
    if not WEBFONT_SOURCE.is_dir():
        raise StagingError("locked webfonts are unavailable; render through alkahest render")

    destination = ROOT / "book" / "theme" / "fonts"
    (destination / "licenses").mkdir(parents=True, exist_ok=True)
    for face in LIBERTINUS_FACES:
        copy_if_changed(WEBFONT_SOURCE / "libertinus" / face, destination / face)
    for face in SOURCE_CODE_PRO_FACES:
        copy_if_changed(WEBFONT_SOURCE / "source-code-pro" / face, destination / face)

    copy_if_changed(
        FONT_LICENSE_SOURCE / "libertinus" / "OFL.txt",
        destination / "licenses" / "Libertinus-OFL.txt",
    )
    copy_if_changed(
        FONT_LICENSE_SOURCE / "source-code-pro" / "OFL.md",
        destination / "licenses" / "Source-Code-Pro-OFL.md",
    )


def main(arguments: list[str] | None = None) -> int:
    """Stage one class of Quarto render inputs."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("kind", choices=("webfonts",))
    parser.parse_args(arguments)
    try:
        stage_webfonts()
    except (OSError, StagingError) as error:
        print(f"error: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
