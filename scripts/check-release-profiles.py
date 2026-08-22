"""Validate reusable release profiles and exact book-local adapters."""

import copy
import json
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR / "lib"))

from alkahest.release_profiles import (
    ReleaseProfileError,
    release_outputs,
    validate_project_releases,
)


ROOT = SCRIPT_DIR.parent


def validate_integration():
    files = {
        "makefile": ROOT / "Makefile",
        "dispatcher": ROOT / "scripts/check-source.py",
        "ci": ROOT / "scripts/ci.sh",
        "readme": ROOT / "README.md",
        "documentation": ROOT / "docs/release-profiles.md",
        "template_policy": ROOT / "config/template/template-package.json",
        "new_book_policy": ROOT / "config/template/new-book.json",
    }
    texts = {name: path.read_text(encoding="utf-8") for name, path in files.items()}
    for marker in (
        "generate-release-profiles:",
        "check-release-profiles:",
        "test-release-profiles:",
    ):
        if marker not in texts["makefile"]:
            raise ReleaseProfileError(f"error: Makefile is missing target {marker}")
    for marker in (
        '("release-profiles", "check-release-profiles.py", False)',
        '("release-profiles", "test-release-profiles.py", False)',
    ):
        if marker not in texts["dispatcher"]:
            raise ReleaseProfileError(f"error: source dispatcher is missing {marker}")
    if 'sync-release-profiles.py" --check' not in texts["ci"]:
        raise ReleaseProfileError("error: CI is missing release-profile verification")
    if "make generate-release-profiles" not in texts["readme"]:
        raise ReleaseProfileError("error: README is missing the release author command")
    for marker in (
        "book/releases.json",
        "full",
        "preview",
        "chapter allowlist",
        "metadata overrides",
        "isolated",
    ):
        if marker not in texts["documentation"]:
            raise ReleaseProfileError(
                f"error: release-profile documentation is missing {marker!r}"
            )
    for marker in (
        '"destination": "defaults/releases.json"',
        '"destination": "scripts/sync-release-profiles.py"',
        '"destination": "scripts/stage-release.py"',
    ):
        if marker not in texts["template_policy"]:
            raise ReleaseProfileError(f"error: template package is missing {marker}")
    for marker in (
        '".alkahest/alkahest-book-template-engine-0.2.0.zip"',
        '"book.toml"',
        '"scripts/author.py"',
    ):
        if marker not in texts["new_book_policy"]:
            raise ReleaseProfileError(f"error: new-book policy is missing {marker}")


def main():
    validate_integration()
    result = validate_project_releases(ROOT)
    defaults = (ROOT / "book/alkahest-release-defaults.json").read_bytes()
    local = json.loads((ROOT / "book/releases.json").read_text(encoding="utf-8"))
    overridden = copy.deepcopy(local)
    overridden["profiles"]["preview"]["metadata"]["subtitle"] = "Selected sample"
    overridden["profiles"]["preview"]["presentation"].update(
        {"full_edition_url": "https://example.com/full", "watermark": {"text": "SAMPLE"}}
    )
    content = (json.dumps(overridden, sort_keys=True) + "\n").encode("utf-8")
    first_resolved, first = release_outputs(defaults, content)
    second_resolved, second = release_outputs(defaults, content)
    if first != second or first_resolved != second_resolved:
        raise ReleaseProfileError("error: release profile adapters are not deterministic")
    preview = first["_quarto-release-preview.yml"]
    for marker in (
        b"Selected sample",
        b"https://example.com/full",
        b"SAMPLE",
        overridden["profiles"]["preview"]["metadata"]["identifier"].encode("utf-8"),
    ):
        if marker not in preview:
            raise ReleaseProfileError("error: book-local override did not reach preview")
    profiles = result["resolved"]["profiles"]
    print(
        "ok: reusable release profiles "
        f"({len(result['resolved']['sources'])} registered sources; "
        f"full {len(profiles['full']['chapters']) + len(profiles['full']['appendices'])}; "
        f"preview {len(profiles['preview']['chapters']) + len(profiles['preview']['appendices'])}; "
        f"{result['outputs']} exact adapters)"
    )


if __name__ == "__main__":
    try:
        main()
    except (OSError, ReleaseProfileError, UnicodeError) as error:
        print(error, file=sys.stderr)
        raise SystemExit(1)
