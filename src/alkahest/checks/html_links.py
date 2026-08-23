"""Validate local links, anchors, and files in rendered HTML."""

import html
import re
import sys
from pathlib import Path
from urllib.parse import unquote


def main():
    root_arg = sys.argv[1] if len(sys.argv) > 1 else "book/_build/html"
    if len(sys.argv) > 2:
        raise RuntimeError(f"usage: {sys.argv[0]} [HTML_ROOT]")
    root = Path(root_arg).resolve()
    if not root.is_dir():
        raise RuntimeError(f"error: missing HTML output directory: {root_arg}")
    documents = sorted(
        path
        for path in root.rglob("*")
        if path.is_file() and path.suffix.lower() in {".html", ".htm"}
    )
    if not documents:
        raise RuntimeError(f"error: no HTML documents found below {root_arg}")
    tag_pattern = re.compile(r"<([A-Za-z][A-Za-z0-9:-]*)\b([^>]*)>", re.S)
    anchors, errors = {}, []
    for document in documents:
        values = set()
        contents = document.read_text(encoding="utf-8", errors="replace")
        for tag in tag_pattern.finditer(contents):
            for match in re.finditer(
                r"""(?:\A|\s)(?:id|name)\s*=\s*(["'])(.*?)\1""", tag.group(2), re.I | re.S
            ):
                anchor = html.unescape(match.group(2))
                if anchor in values:
                    errors.append(f"{document.relative_to(root)} has duplicate anchor #{anchor}")
                values.add(anchor)
        anchors[document] = values
    local_targets = external_targets = 0
    eligible = {"a", "audio", "iframe", "img", "link", "script", "source", "track", "video"}
    for document in documents:
        contents = document.read_text(encoding="utf-8", errors="replace")
        for tag in tag_pattern.finditer(contents):
            if tag.group(1).lower() not in eligible:
                continue
            for match in re.finditer(
                r"""(?:\A|\s)(href|poster|src)\s*=\s*(["'])(.*?)\2""", tag.group(2), re.I | re.S
            ):
                raw = match.group(3)
                target = html.unescape(raw).strip()
                if not target:
                    continue
                if re.match(r"^(?:[A-Za-z][A-Za-z0-9+.-]*:|//)", target):
                    external_targets += 1
                    continue
                local_targets += 1
                before, separator, fragment = target.partition("#")
                path_value = unquote(before.split("?", 1)[0])
                fragment = unquote(fragment) if separator else None
                if not path_value:
                    resolved = document
                elif path_value.startswith("/"):
                    resolved = root.joinpath(*filter(None, path_value.split("/")))
                else:
                    resolved = document.parent.joinpath(*filter(None, path_value.split("/")))
                if resolved.is_dir():
                    resolved /= "index.html"
                if not resolved.is_file():
                    errors.append(f"{document.relative_to(root)} -> {raw} (missing target)")
                    continue
                resolved = resolved.resolve()
                try:
                    resolved.relative_to(root)
                except ValueError:
                    errors.append(
                        f"{document.relative_to(root)} -> {raw} (target escapes publication root)"
                    )
                    continue
                if (
                    fragment
                    and resolved.suffix.lower() in {".html", ".htm"}
                    and fragment not in anchors.get(resolved, set())
                ):
                    errors.append(f"{document.relative_to(root)} -> {raw} (missing fragment)")
    if errors:
        print("error: HTML publication validation failed", file=sys.stderr)
        for error in errors:
            print(f"  {error}", file=sys.stderr)
        raise SystemExit(1)
    print(
        f"ok: HTML links ({len(documents)} documents; {local_targets} local targets; {external_targets} external targets skipped offline)"
    )


if __name__ == "__main__":
    try:
        main()
    except (OSError, RuntimeError) as error:
        print(error, file=sys.stderr)
        raise SystemExit(1)
