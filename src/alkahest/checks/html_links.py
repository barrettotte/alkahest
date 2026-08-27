"""Validate local links, anchors, and files in rendered HTML."""

import html
import re
import sys
from collections.abc import Iterator
from pathlib import Path
from urllib.parse import unquote

TAG_PATTERN = re.compile(r"<([A-Za-z][A-Za-z0-9:-]*)\b([^>]*)>", re.DOTALL)
ELIGIBLE_TAGS = {"a", "audio", "iframe", "img", "link", "script", "source", "track", "video"}


def html_documents(root: Path) -> list[Path]:
    """Find rendered HTML documents below one publication root."""
    return sorted(path for path in root.rglob("*") if path.is_file() and path.suffix.lower() in {".html", ".htm"})


def collect_anchors(root: Path, documents: list[Path]) -> tuple[dict[Path, set[str]], list[str]]:
    """Collect document anchors and duplicate-anchor errors."""
    anchors: dict[Path, set[str]] = {}
    errors: list[str] = []
    for document in documents:
        values: set[str] = set()
        contents = document.read_text(encoding="utf-8", errors="replace")
        for tag in TAG_PATTERN.finditer(contents):
            for match in re.finditer(
                r"""(?:\A|\s)(?:id|name)\s*=\s*(["'])(.*?)\1""",
                tag.group(2),
                re.IGNORECASE | re.DOTALL,
            ):
                anchor = html.unescape(match.group(2))
                if anchor in values:
                    errors.append(f"{document.relative_to(root)} has duplicate anchor #{anchor}")
                values.add(anchor)
        anchors[document] = values
    return anchors, errors


def document_targets(document: Path) -> Iterator[tuple[str, str]]:
    """Yield raw and decoded targets from one HTML document."""
    contents = document.read_text(encoding="utf-8", errors="replace")
    for tag in TAG_PATTERN.finditer(contents):
        if tag.group(1).lower() not in ELIGIBLE_TAGS:
            continue
        for match in re.finditer(
            r"""(?:\A|\s)(href|poster|src)\s*=\s*(["'])(.*?)\2""",
            tag.group(2),
            re.IGNORECASE | re.DOTALL,
        ):
            raw = match.group(3)
            target = html.unescape(raw).strip()
            if target:
                yield raw, target


def resolve_target(root: Path, document: Path, path_value: str) -> Path:
    """Resolve one local target path against its document."""
    if not path_value:
        resolved = document
    elif path_value.startswith("/"):
        resolved = root.joinpath(*filter(None, path_value.split("/")))
    else:
        resolved = document.parent.joinpath(*filter(None, path_value.split("/")))
    return resolved / "index.html" if resolved.is_dir() else resolved


def local_target_error(
    root: Path,
    document: Path,
    raw: str,
    target: str,
    anchors: dict[Path, set[str]],
) -> str | None:
    """Return a diagnostic for one invalid local target."""
    before, separator, fragment = target.partition("#")
    path_value = unquote(before.split("?", 1)[0])
    decoded_fragment = unquote(fragment) if separator else None

    resolved = resolve_target(root, document, path_value)
    prefix = f"{document.relative_to(root)} -> {raw}"
    if not resolved.is_file():
        return f"{prefix} (missing target)"

    resolved = resolved.resolve()
    try:
        resolved.relative_to(root)
    except ValueError:
        return f"{prefix} (target escapes publication root)"
    if (
        decoded_fragment
        and resolved.suffix.lower() in {".html", ".htm"}
        and decoded_fragment not in anchors.get(resolved, set())
    ):
        return f"{prefix} (missing fragment)"
    return None


def validate_targets(root: Path, documents: list[Path], anchors: dict[Path, set[str]]) -> tuple[int, int, list[str]]:
    """Validate every rendered local target and count external targets."""
    local_targets = 0
    external_targets = 0
    errors: list[str] = []
    for document in documents:
        for raw, target in document_targets(document):
            if re.match(r"^(?:[A-Za-z][A-Za-z0-9+.-]*:|//)", target):
                external_targets += 1
                continue
            local_targets += 1
            error = local_target_error(root, document, raw, target, anchors)
            if error:
                errors.append(error)
    return local_targets, external_targets, errors


def main() -> None:
    """Validate local targets and fragments in rendered HTML."""
    root_arg = sys.argv[1] if len(sys.argv) > 1 else "book/_build/html"
    if len(sys.argv) > 2:
        raise RuntimeError(f"usage: {sys.argv[0]} [HTML_ROOT]")

    root = Path(root_arg).resolve()
    if not root.is_dir():
        raise RuntimeError(f"error: missing HTML output directory: {root_arg}")

    documents = html_documents(root)
    if not documents:
        raise RuntimeError(f"error: no HTML documents found below {root_arg}")

    anchors, errors = collect_anchors(root, documents)
    local_targets, external_targets, target_errors = validate_targets(root, documents, anchors)
    errors.extend(target_errors)
    if errors:
        print("error: HTML publication validation failed", file=sys.stderr)
        for error in errors:
            print(f"  {error}", file=sys.stderr)
        raise SystemExit(1) from None
    print(
        f"ok: HTML links ({len(documents)} documents; {local_targets} local targets; {external_targets} external targets skipped offline)"
    )


if __name__ == "__main__":
    try:
        main()
    except (OSError, RuntimeError) as error:
        print(error, file=sys.stderr)
        raise SystemExit(1) from None
