"""Validate manuscript links, image alternatives, IDs, and cross-references."""

import os
import re
import sys
from pathlib import Path
from urllib.parse import unquote, urlsplit

ROOT = Path(__file__).resolve().parents[3]
ID_PATTERN = r"[A-Za-z][A-Za-z0-9_.:-]*"
CROSSREF_PREFIXES = {
    "alg",
    "ans",
    "cau",
    "cnj",
    "cor",
    "def",
    "eq",
    "exm",
    "exr",
    "fig",
    "hint",
    "imp",
    "lab",
    "lem",
    "lst",
    "nte",
    "obj",
    "plan",
    "pre",
    "project",
    "prp",
    "rem",
    "rev",
    "sec",
    "sol",
    "sum",
    "tbl",
    "thm",
    "tip",
    "wrn",
}
DIAGRAM_ENGINES = {"dot", "graphviz", "mermaid"}
IMAGE_PATTERN = re.compile(
    r"!\[([^]\n]*)\]\(\s*(<[^>\n]+>|(?:\\.|[^)\s])+)"
    r"(?:\s+(?:\"[^\"\n]*\"|'[^'\n]*'))?\s*\)(\{[^}\n]*\})?"
)
LINK_PATTERN = re.compile(
    r"(?<!!)\[([^]\n]+)\]\(\s*(<[^>\n]+>|(?:\\.|[^)\s])+)"
    r"(?:\s+(?:\"[^\"\n]*\"|'[^'\n]*'))?\s*\)"
)
INLINE_MATH_PATTERN = re.compile(
    r"(?<![$\\])\$(?!\$)(?:\\.|[^$\\\n])+(?<!\\)\$(?!\$)"
)


def fail(errors):
    print("error: editorial integrity validation failed", file=sys.stderr)
    for error in errors:
        print(f"  {error}", file=sys.stderr)
    raise SystemExit(1)


def sources_below(root):
    return sorted(
        path.resolve()
        for path in root.rglob("*.qmd")
        if "_build" not in path.parts and ".quarto" not in path.parts
    )


def strip_inline_code(line):
    return re.sub(r"(`+)(.*?)\1", "", line)


def option_value(value):
    value = value.strip()
    if len(value) >= 2 and value[0] == value[-1] and value[0] in {'"', "'"}:
        value = value[1:-1].strip()
    return value


def add_id(identities, errors, identity, source, line_number, root):
    location = f"{source.relative_to(root)}:{line_number}"
    if identity in identities:
        errors.append(
            f"{location}: duplicate ID '{identity}'; first declared at "
            f"{identities[identity][1]}"
        )
        return
    identities[identity] = (source, location)


def image_has_alternative(alt, attributes):
    if alt.strip():
        return True
    fig_alt = re.search(r'''\bfig-alt\s*=\s*(["'])(.*?)\1''', attributes)
    if fig_alt and fig_alt.group(2).strip():
        return True
    return bool(
        re.search(r"(?:^|[\s{])\.decorative(?:[\s}]|$)", attributes)
        or re.search(r'''\brole\s*=\s*(["'])presentation\1''', attributes)
        or re.search(r'''\baria-hidden\s*=\s*(["'])true\1''', attributes)
    )


def scan_sources(root, sources):
    errors = []
    identities = {}
    per_source_ids = {source: set() for source in sources}
    links = []
    references = []
    image_count = diagram_count = math_count = external_count = 0

    for source in sources:
        fence_char = None
        fence_length = 0
        diagram = None
        diagram_alt = False
        diagram_line = 0
        display_math_line = None
        for line_number, line in enumerate(
            source.read_text(encoding="utf-8").splitlines(), 1
        ):
            if fence_char:
                if re.fullmatch(
                    rf"\s*{re.escape(fence_char)}{{{fence_length},}}\s*", line
                ):
                    if diagram and not diagram_alt:
                        errors.append(
                            f"{source.relative_to(root)}:{diagram_line}: {diagram} "
                            "diagram needs a nonempty fig-alt option"
                        )
                    fence_char = None
                    diagram = None
                    continue
                if diagram:
                    option = re.match(
                        r"\s*(?:#|//|%%)\|\s*(label|fig-alt):\s*(.*?)\s*$", line
                    )
                    if option and option.group(1) == "label":
                        identity = option_value(option.group(2))
                        if re.fullmatch(ID_PATTERN, identity):
                            add_id(
                                identities,
                                errors,
                                identity,
                                source,
                                line_number,
                                root,
                            )
                            per_source_ids[source].add(identity)
                    elif option and option.group(1) == "fig-alt":
                        diagram_alt = bool(option_value(option.group(2)))
                continue

            if display_math_line is not None:
                closing = re.fullmatch(r"\s*\$\$\s*(\{[^}\n]*\})?\s*", line)
                if closing:
                    attributes = closing.group(1) or ""
                    for identity in re.findall(rf"#({ID_PATTERN})", attributes):
                        add_id(
                            identities,
                            errors,
                            identity,
                            source,
                            line_number,
                            root,
                        )
                        per_source_ids[source].add(identity)
                    alt = re.search(r'''\balt\s*=\s*(["'])(.*?)\1''', attributes)
                    if not alt or not alt.group(2).strip():
                        errors.append(
                            f"{source.relative_to(root)}:{display_math_line}: "
                            "display math needs nonempty alt text"
                        )
                    math_count += 1
                    display_math_line = None
                continue

            if re.fullmatch(r"\s*\$\$\s*", line):
                display_math_line = line_number
                continue

            opening = re.match(r"^\s*(`{3,}|~{3,})(.*)$", line)
            if opening:
                marker, info = opening.groups()
                fence_char, fence_length = marker[0], len(marker)
                engine = re.search(r"\{([A-Za-z0-9_-]+)", info)
                diagram = (
                    engine.group(1).lower()
                    if engine and engine.group(1).lower() in DIAGRAM_ENGINES
                    else None
                )
                inline_alt = re.search(
                    r'''\bfig-alt\s*=\s*(["'])(.*?)\1''', info
                )
                diagram_alt = bool(inline_alt and inline_alt.group(2).strip())
                diagram_line = line_number
                if diagram:
                    diagram_count += 1
                for identity in re.findall(rf"#({ID_PATTERN})", info):
                    add_id(
                        identities, errors, identity, source, line_number, root
                    )
                    per_source_ids[source].add(identity)
                continue

            visible = strip_inline_code(line)
            for math in INLINE_MATH_PATTERN.finditer(visible):
                annotation = None
                if math.start() > 0 and visible[math.start() - 1] == "[":
                    annotation = re.match(r"\]\{([^}\n]*)\}", visible[math.end():])
                attributes = annotation.group(1) if annotation else ""
                alt = re.search(r'''\balt\s*=\s*(["'])(.*?)\1''', attributes)
                if (
                    not re.search(r"(?:^|\s)\.alkahest-math-alt(?:\s|$)", attributes)
                    or not alt
                    or not alt.group(2).strip()
                ):
                    errors.append(
                        f"{source.relative_to(root)}:{line_number}: inline math "
                        "needs an .alkahest-math-alt span with nonempty alt text"
                    )
                math_count += 1
            for attributes in re.findall(r"\{([^}\n]*)\}", visible):
                for identity in re.findall(rf"#({ID_PATTERN})", attributes):
                    add_id(
                        identities, errors, identity, source, line_number, root
                    )
                    per_source_ids[source].add(identity)
            for identity in re.findall(
                rf'''\bid\s*=\s*["']({ID_PATTERN})["']''', visible
            ):
                add_id(identities, errors, identity, source, line_number, root)
                per_source_ids[source].add(identity)

            for image in IMAGE_PATTERN.finditer(visible):
                image_count += 1
                alt, target, attributes = image.groups()
                attributes = attributes or ""
                if not image_has_alternative(alt, attributes):
                    errors.append(
                        f"{source.relative_to(root)}:{line_number}: image '{target}' "
                        "needs nonempty alt text, fig-alt, or .decorative"
                    )
                links.append((source, line_number, target, "image"))
            without_images = IMAGE_PATTERN.sub("", visible)
            for link in LINK_PATTERN.finditer(without_images):
                links.append((source, line_number, link.group(2), "link"))

            reference_line = re.sub(r"https?://\S+", "", visible)
            reference_line = re.sub(
                r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+", "", reference_line
            )
            for match in re.finditer(
                rf"(?<![A-Za-z0-9_])@({ID_PATTERN})", reference_line
            ):
                references.append((source, line_number, match.group(1)))

        if fence_char:
            errors.append(f"{source.relative_to(root)}: unclosed fenced block")
        if display_math_line is not None:
            errors.append(
                f"{source.relative_to(root)}:{display_math_line}: unclosed display math"
            )

    source_set = set(sources)
    for source, line_number, raw_target, kind in links:
        target = raw_target[1:-1] if raw_target.startswith("<") else raw_target
        parsed = urlsplit(target.replace("\\ ", " "))
        if parsed.scheme or parsed.netloc or target.startswith("//"):
            external_count += 1
            continue
        path_value = unquote(parsed.path)
        if path_value.startswith("/"):
            resolved = root.joinpath(*filter(None, path_value.split("/")))
        elif path_value:
            resolved = source.parent / path_value
        else:
            resolved = source
        resolved = resolved.resolve()
        try:
            resolved.relative_to(root)
        except ValueError:
            errors.append(
                f"{source.relative_to(root)}:{line_number}: {kind} target "
                f"'{raw_target}' escapes the book root"
            )
            continue
        if not resolved.exists():
            html_source = resolved.with_suffix(".qmd") if resolved.suffix == ".html" else None
            if html_source and html_source in source_set:
                resolved = html_source
            else:
                errors.append(
                    f"{source.relative_to(root)}:{line_number}: {kind} target "
                    f"'{raw_target}' does not exist"
                )
                continue
        fragment = unquote(parsed.fragment)
        if fragment and resolved in source_set and fragment not in per_source_ids[resolved]:
            errors.append(
                f"{source.relative_to(root)}:{line_number}: link fragment "
                f"'#{fragment}' is not declared in {resolved.relative_to(root)}"
            )

    for source, line_number, raw_reference in references:
        reference = raw_reference
        if reference not in identities:
            reference = reference.rstrip(".,;:!?")
        prefix = reference.split("-", 1)[0]
        if prefix in CROSSREF_PREFIXES and reference not in identities:
            errors.append(
                f"{source.relative_to(root)}:{line_number}: dangling "
                f"cross-reference '@{reference}'"
            )

    return (
        errors,
        len(identities),
        len(links),
        image_count,
        diagram_count,
        math_count,
        external_count,
    )


def main():
    root = Path(
        os.environ.get(
            "ALKAHEST_EDITORIAL_BOOK_ROOT", ROOT / "book"
        )
    ).resolve()
    if not root.is_dir():
        raise RuntimeError("error: editorial book root does not exist")
    sources = sources_below(root)
    if not sources:
        raise RuntimeError("error: editorial book root contains no .qmd sources")
    errors, identities, links, images, diagrams, math, external = scan_sources(
        root, sources
    )
    if errors:
        fail(errors)
    print(
        "ok: editorial source integrity "
        f"({len(sources)} sources; {links} local/external targets; "
        f"{images} images; {diagrams} diagrams; {math} math expressions; "
        f"{identities} unique IDs; "
        f"{external} external targets skipped offline)"
    )


if __name__ == "__main__":
    try:
        main()
    except (OSError, RuntimeError, UnicodeError) as error:
        print(error, file=sys.stderr)
        raise SystemExit(1)
