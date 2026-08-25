"""Finalize and validate EPUB accessibility semantics and policy."""

from __future__ import annotations

import html
import itertools
import json
import os
import posixpath
import re
import tempfile
import xml.etree.ElementTree as ET
import zipfile
from pathlib import Path
from typing import Never

from defusedxml import ElementTree as DefusedET

from .markup import canonicalize_markup

CONTAINER_NS = "urn:oasis:names:tc:opendocument:xmlns:container"
DC_NS = "http://purl.org/dc/elements/1.1/"
EPUB_NS = "http://www.idpf.org/2007/ops"
OPF_NS = "http://www.idpf.org/2007/opf"
XHTML_NS = "http://www.w3.org/1999/xhtml"
XML_NS = "http://www.w3.org/XML/1998/namespace"

PROPERTY_NAMES = {
    "access_modes": "schema:accessMode",
    "access_mode_sufficient": "schema:accessModeSufficient",
    "accessibility_features": "schema:accessibilityFeature",
    "accessibility_hazards": "schema:accessibilityHazard",
    "accessibility_summary": "schema:accessibilitySummary",
}
GENERIC_LINK_TEXT = {
    "click",
    "click here",
    "here",
    "learn more",
    "link",
    "more",
    "read more",
}
VALID_BODY_TYPES = {"frontmatter", "bodymatter", "backmatter"}
VALID_PAGINATION_MODES = {"not-applicable", "print-equivalent"}
EPUB_ROLE_MAP = {
    "appendix": "doc-appendix",
    "bibliography": "doc-bibliography",
    "chapter": "doc-chapter",
    "glossary": "doc-glossary",
    "index": "doc-index",
    "preface": "doc-preface",
}


class EpubPolicyError(RuntimeError):
    """A deterministic EPUB accessibility contract failed."""


def fail(message: str) -> Never:
    raise EpubPolicyError(f"error: {message}")


def load_policy(path: Path) -> dict:
    try:
        policy = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        fail(f"cannot read EPUB accessibility policy {path}: {error}")
    if policy.get("schema_version") != 1:
        fail("EPUB accessibility policy schema_version must be 1")
    if policy.get("standard") != "EPUB Accessibility 1.1":
        fail("EPUB accessibility policy must target EPUB Accessibility 1.1")
    language = policy.get("language")
    if not isinstance(language, str) or not re.fullmatch(
        r"[A-Za-z]{2,3}(?:-[A-Za-z0-9]{2,8})*", language
    ):
        fail("EPUB accessibility policy language must be a BCP 47 tag")
    if policy.get("claim_status") != "pending-manual-review":
        fail("EPUB conformance claims remain blocked until manual review passes")

    discovery = policy.get("discovery")
    if not isinstance(discovery, dict):
        fail("EPUB accessibility policy needs discovery metadata")
    for key in PROPERTY_NAMES:
        value = discovery.get(key)
        if key == "accessibility_summary":
            if not isinstance(value, str) or len(value.strip()) < 80:
                fail("EPUB accessibility summary needs a specific human-readable status")
            continue
        if not isinstance(value, list) or not value:
            fail(f"EPUB discovery field {key} must be a nonempty list")
        if any(not isinstance(item, str) or not item.strip() for item in value):
            fail(f"EPUB discovery field {key} contains an empty value")
        if len(value) != len(set(value)):
            fail(f"EPUB discovery field {key} contains duplicate values")
    required_features = {
        "MathML",
        "alternativeText",
        "readingOrder",
        "structuralNavigation",
        "tableOfContents",
    }
    if not required_features.issubset(discovery["accessibility_features"]):
        fail("EPUB discovery metadata omits a required reference-book feature")
    if set(discovery["accessibility_hazards"]) != {"none"}:
        fail("the static reference EPUB must explicitly declare no hazards")
    if not {"textual", "visual"}.issubset(discovery["access_modes"]):
        fail("the technical reference EPUB must declare textual and visual access modes")

    sections = policy.get("sections")
    if not isinstance(sections, list) or not sections:
        fail("EPUB accessibility policy needs semantic section mappings")
    section_ids = set()
    for section in sections:
        if not isinstance(section, dict):
            fail("EPUB section mappings must be objects")
        target = section.get("id")
        if not isinstance(target, str) or not target:
            fail("EPUB section mapping needs an id")
        if target in section_ids:
            fail(f"duplicate EPUB section mapping: {target}")
        section_ids.add(target)
        kind = section.get("epub_type")
        role = section.get("role")
        if kind is None:
            if role is not None:
                fail(f"EPUB section {target} cannot declare a role without epub_type")
        elif not isinstance(kind, str) or not kind:
            fail(f"EPUB section {target} has an invalid epub_type")
        elif EPUB_ROLE_MAP.get(kind) != role:
            fail(f"EPUB section {target} needs the DPUB-ARIA role matching {kind}")
        if section.get("body_type") not in VALID_BODY_TYPES:
            fail(f"EPUB section {target} has an invalid body_type")

    landmarks = policy.get("landmarks")
    if not isinstance(landmarks, list) or not landmarks:
        fail("EPUB accessibility policy needs landmarks")
    landmark_types = set()
    for landmark in landmarks:
        if not isinstance(landmark, dict):
            fail("EPUB landmarks must be objects")
        kind = landmark.get("type")
        if not isinstance(kind, str) or not kind:
            fail("EPUB landmark needs a type")
        if kind in landmark_types:
            fail(f"duplicate EPUB landmark type: {kind}")
        landmark_types.add(kind)
        if not isinstance(landmark.get("label"), str) or not landmark["label"].strip():
            fail(f"EPUB landmark {kind} needs a label")
        special = landmark.get("special")
        target_id = landmark.get("target_id")
        if (special in {"titlepage", "toc"}) == isinstance(target_id, str):
            fail(f"EPUB landmark {kind} must have one special or target_id destination")
    if not {"titlepage", "toc", "bodymatter"}.issubset(landmark_types):
        fail("EPUB landmarks must include titlepage, toc, and bodymatter")

    pagination = policy.get("pagination")
    if not isinstance(pagination, dict):
        fail("EPUB accessibility policy needs pagination policy")
    mode = pagination.get("mode")
    if mode not in VALID_PAGINATION_MODES:
        fail("EPUB pagination mode must be not-applicable or print-equivalent")
    if mode == "not-applicable":
        rationale = pagination.get("rationale")
        if not isinstance(rationale, str) or len(rationale.strip()) < 120:
            fail("not-applicable EPUB pagination needs a durable rationale")
        if "pages" in pagination or "page_break_source" in pagination:
            fail("not-applicable EPUB pagination cannot declare pages or a source")
    else:
        source = pagination.get("page_break_source")
        pages = pagination.get("pages")
        if not isinstance(source, str) or len(source.strip()) < 8:
            fail("print-equivalent EPUB pagination needs an identified source")
        if not isinstance(pages, list) or not pages:
            fail("print-equivalent EPUB pagination needs retained page boundaries")
        labels = set()
        anchors = set()
        for page in pages:
            if not isinstance(page, dict):
                fail("EPUB page mappings must be objects")
            label = page.get("label")
            anchor = page.get("anchor")
            if not isinstance(label, str) or not label.strip():
                fail("EPUB page mapping needs a label")
            if not isinstance(anchor, str) or not anchor.strip():
                fail(f"EPUB page {label} needs a stable anchor")
            if label in labels or anchor in anchors:
                fail("EPUB page labels and anchors must be unique")
            labels.add(label)
            anchors.add(anchor)
        if "pageNavigation" not in discovery["accessibility_features"]:
            fail("print-equivalent EPUB metadata must declare pageNavigation")
    return policy


def _read_members(epub_path: Path) -> tuple[list[zipfile.ZipInfo], dict[str, bytes]]:
    try:
        with zipfile.ZipFile(epub_path) as archive:
            infos = archive.infolist()
            members = {info.filename: archive.read(info.filename) for info in infos}
    except (OSError, zipfile.BadZipFile, KeyError) as error:
        fail(f"cannot read EPUB {epub_path}: {error}")
    if not infos or infos[0].filename != "mimetype":
        fail("EPUB mimetype must be the first archive member")
    if members.get("mimetype") != b"application/epub+zip":
        fail("EPUB mimetype member has invalid content")
    if infos[0].compress_type != zipfile.ZIP_STORED:
        fail("EPUB mimetype member must be stored without compression")
    return infos, members


def _rootfile(members: dict[str, bytes]) -> str:
    try:
        container = DefusedET.fromstring(members["META-INF/container.xml"])
    except (KeyError, ET.ParseError) as error:
        fail(f"EPUB container document is invalid: {error}")
    rootfile = container.find(f".//{{{CONTAINER_NS}}}rootfile")
    full_path = rootfile.get("full-path") if rootfile is not None else None
    if not full_path:
        fail("EPUB container has no package rootfile")
    return full_path


def _package_inventory(
    members: dict[str, bytes],
) -> tuple[str, ET.Element, str, dict[str, str], list[str]]:
    opf_path = _rootfile(members)
    try:
        package = DefusedET.fromstring(members[opf_path])
    except (KeyError, ET.ParseError) as error:
        fail(f"EPUB package document is invalid: {error}")
    base = posixpath.dirname(opf_path)
    manifest: dict[str, str] = {}
    nav_path = ""
    for item in package.findall(f".//{{{OPF_NS}}}manifest/{{{OPF_NS}}}item"):
        item_id = item.get("id")
        href = item.get("href")
        if not item_id or not href:
            fail("EPUB manifest item needs id and href")
        path = posixpath.normpath(posixpath.join(base, href.split("#", 1)[0]))
        manifest[item_id] = path
        if "nav" in (item.get("properties") or "").split():
            if nav_path:
                fail("EPUB manifest has multiple navigation documents")
            nav_path = path
    if not nav_path:
        fail("EPUB manifest has no navigation document")
    spine = []
    for itemref in package.findall(f".//{{{OPF_NS}}}spine/{{{OPF_NS}}}itemref"):
        item_id = itemref.get("idref")
        if item_id not in manifest:
            fail(f"EPUB spine references missing manifest item {item_id}")
        spine.append(manifest[item_id])
    if len(spine) != len(set(spine)) or not spine:
        fail("EPUB spine must contain a nonempty unique reading order")
    return opf_path, package, nav_path, manifest, spine


def _decode(members: dict[str, bytes], path: str) -> str:
    try:
        return members[path].decode("utf-8")
    except (KeyError, UnicodeDecodeError) as error:
        fail(f"EPUB member {path} is missing or not UTF-8: {error}")


def _find_id_files(members: dict[str, bytes], paths: list[str]) -> dict[str, str]:
    found: dict[str, str] = {}
    pattern = re.compile(r"\bid=(['\"])([^'\"]+)\1")
    for path in paths:
        for match in pattern.finditer(_decode(members, path)):
            target = match.group(2)
            found.setdefault(target, path)
    return found


def _add_attribute(tag: str, name: str, value: str) -> str:
    attribute = re.compile(rf"\s{re.escape(name)}=(['\"])(.*?)\1")
    escaped = html.escape(value, quote=True)
    if attribute.search(tag):
        return attribute.sub(f' {name}="{escaped}"', tag, count=1)
    return tag[:-1] + f' {name}="{escaped}">'


def _set_section_semantics(
    text: str, target: str, kind: str | None, role: str | None, body: str
) -> str:
    id_pattern = re.compile(
        rf"<(?P<name>[A-Za-z][\w:.-]*)(?P<attrs>[^<>]*\bid=(['\"]){re.escape(target)}\3[^<>]*)>"
    )
    match = id_pattern.search(text)
    if match is None:
        fail(f"cannot find rendered EPUB section id {target}")
    tag = match.group(0)
    if kind is not None:
        if role is None:
            fail(f"EPUB section {target} has a type without a matching role")
        tag = _add_attribute(tag, "epub:type", kind)
        tag = _add_attribute(tag, "role", role)
    text = text[: match.start()] + tag + text[match.end() :]
    body_pattern = re.compile(r"<body\b[^<>]*>")
    body_match = body_pattern.search(text)
    if body_match is None:
        fail(f"EPUB document containing {target} has no body")
    body_tag = _add_attribute(body_match.group(0), "epub:type", body)
    return text[: body_match.start()] + body_tag + text[body_match.end() :]


def _slug_page_label(label: str) -> str:
    slug = re.sub(r"[^A-Za-z0-9]+", "-", label).strip("-").lower()
    return f"page-{slug or 'location'}"


def _insert_page_marker(text: str, anchor: str, marker: str, label: str) -> str:
    tag_pattern = re.compile(rf"<[A-Za-z][\w:.-]*[^<>]*\bid=(['\"]){re.escape(anchor)}\1[^<>]*>")
    match = tag_pattern.search(text)
    if match is None:
        fail(f"cannot find rendered EPUB page anchor {anchor}")
    escaped_label = html.escape(label, quote=True)
    pagebreak = (
        f'<span id="{marker}" epub:type="pagebreak" role="doc-pagebreak" '
        f'aria-label="Page {escaped_label}"></span>'
    )
    return text[: match.start()] + pagebreak + text[match.start() :]


def _normalize_code_anchors(text: str) -> str:
    pattern = re.compile(r"<a\b(?P<attrs>[^<>]*\bhref=(['\"])#[^'\"]+\2[^<>]*)></a>")

    def replace(match: re.Match) -> str:
        tag = f"<a{match.group('attrs')}>"
        tag = _add_attribute(tag, "aria-hidden", "true")
        tag = _add_attribute(tag, "tabindex", "-1")
        return tag + "</a>"

    return pattern.sub(replace, text)


def _replace_discovery_metadata(opf: str, policy: dict) -> str:
    for property_name in [*PROPERTY_NAMES.values(), "pageBreakSource"]:
        pattern = re.compile(
            rf"\s*<meta\b[^>]*\bproperty=(['\"]){re.escape(property_name)}\1[^>]*>.*?</meta>",
            re.DOTALL,
        )
        opf = pattern.sub("", opf)
    lines = []
    discovery = policy["discovery"]
    for key, property_name in PROPERTY_NAMES.items():
        values = discovery[key] if isinstance(discovery[key], list) else [discovery[key]]
        for value in values:
            lines.append(f'    <meta property="{property_name}">{html.escape(value)}</meta>')
    if policy["pagination"]["mode"] == "print-equivalent":
        source = html.escape(policy["pagination"]["page_break_source"])
        lines.append(f'    <meta property="pageBreakSource">{source}</meta>')
    injection = "\n" + "\n".join(lines) + "\n  "
    if "</metadata>" not in opf:
        fail("EPUB package document has no metadata element")
    return opf.replace("</metadata>", injection + "</metadata>", 1)


def _landmark_href(
    landmark: dict,
    nav_path: str,
    title_path: str,
    id_files: dict[str, str],
) -> str:
    nav_base = posixpath.dirname(nav_path)
    if landmark.get("special") == "toc":
        return "#toc"
    if landmark.get("special") == "titlepage":
        target_path = title_path
        fragment = ""
    else:
        fragment = landmark["target_id"]
        target_path = id_files.get(fragment, "")
        if not target_path:
            fail(f"cannot resolve EPUB landmark target {fragment}")
    relative = posixpath.relpath(target_path, nav_base or ".")
    return relative + (f"#{fragment}" if fragment else "")


def _replace_navigation(
    nav: str,
    policy: dict,
    nav_path: str,
    title_path: str,
    id_files: dict[str, str],
    pages: list[tuple[str, str, str]],
) -> str:
    items = []
    for landmark in policy["landmarks"]:
        href = _landmark_href(landmark, nav_path, title_path, id_files)
        items.append(
            "      <li>"
            f'<a href="{html.escape(href, quote=True)}" '
            f'epub:type="{html.escape(landmark["type"], quote=True)}">'
            f"{html.escape(landmark['label'])}</a></li>"
        )
    landmarks = (
        '<nav epub:type="landmarks" id="landmarks" hidden="hidden">\n'
        "  <h1>Guide</h1>\n"
        "  <ol>\n" + "\n".join(items) + "\n  </ol>\n</nav>"
    )
    existing = re.compile(r"<nav\b[^>]*\bepub:type=(['\"])landmarks\1[^>]*>.*?</nav>", re.DOTALL)
    if existing.search(nav):
        nav = existing.sub(landmarks, nav, count=1)
    elif "</body>" in nav:
        nav = nav.replace("</body>", landmarks + "\n</body>", 1)
    else:
        fail("EPUB navigation document has no body")

    page_list_pattern = re.compile(
        r"\s*<nav\b[^>]*\bepub:type=(['\"])page-list\1[^>]*>.*?</nav>", re.DOTALL
    )
    nav = page_list_pattern.sub("", nav)
    if pages:
        page_items = []
        nav_base = posixpath.dirname(nav_path)
        for label, path, marker in pages:
            href = posixpath.relpath(path, nav_base or ".") + f"#{marker}"
            page_items.append(
                f'      <li><a href="{html.escape(href, quote=True)}">{html.escape(label)}</a></li>'
            )
        page_list = (
            '<nav epub:type="page-list" id="page-list">\n'
            "  <h1>Page list</h1>\n"
            "  <ol>\n" + "\n".join(page_items) + "\n  </ol>\n</nav>"
        )
        nav = nav.replace("</body>", page_list + "\n</body>", 1)
    return nav


def _write_members(
    epub_path: Path,
    infos: list[zipfile.ZipInfo],
    members: dict[str, bytes],
) -> None:
    with tempfile.NamedTemporaryFile(
        prefix=f".{epub_path.name}.", suffix=".tmp", dir=epub_path.parent, delete=False
    ) as temporary:
        temporary_path = Path(temporary.name)
    try:
        with zipfile.ZipFile(temporary_path, "w") as archive:
            for info in infos:
                # Quarto/Pandoc honors SOURCE_DATE_EPOCH. Reusing its ZipInfo
                # records retains that stable timestamp and the required
                # mimetype-first ordering while accessibility edits are made.
                archive.writestr(info, members[info.filename])
        os.replace(temporary_path, epub_path)
    finally:
        temporary_path.unlink(missing_ok=True)


def finalize_epub(epub_path: Path, policy_path: Path, allow_missing_sections: bool = False) -> None:
    policy = load_policy(policy_path)
    infos, members = _read_members(epub_path)
    opf_path, _package, nav_path, manifest, _spine = _package_inventory(members)
    xhtml_paths = [
        path
        for path in manifest.values()
        if path.endswith((".xhtml", ".html", ".htm")) and path != nav_path
    ]
    id_files = _find_id_files(members, xhtml_paths)
    title_candidates = [
        path
        for path in xhtml_paths
        if re.search(r"<[^>]+\bepub:type=(['\"])titlepage\1", _decode(members, path))
    ]
    if len(title_candidates) != 1:
        fail("EPUB must contain exactly one titlepage document")

    for path in xhtml_paths:
        members[path] = _normalize_code_anchors(_decode(members, path)).encode("utf-8")

    for section in policy["sections"]:
        target = section["id"]
        section_path = id_files.get(target)
        if not section_path:
            if allow_missing_sections:
                continue
            fail(f"cannot resolve EPUB semantic section {target}")
        updated = _set_section_semantics(
            _decode(members, section_path),
            target,
            section["epub_type"],
            section["role"],
            section["body_type"],
        )
        members[section_path] = updated.encode("utf-8")

    pages: list[tuple[str, str, str]] = []
    pagination = policy["pagination"]
    if pagination["mode"] == "print-equivalent":
        for page in pagination["pages"]:
            page_path = id_files.get(page["anchor"])
            if not page_path:
                fail(f"cannot resolve EPUB page anchor {page['anchor']}")
            marker = _slug_page_label(page["label"])
            members[page_path] = _insert_page_marker(
                _decode(members, page_path), page["anchor"], marker, page["label"]
            ).encode("utf-8")
            pages.append((page["label"], page_path, marker))

    members[opf_path] = _replace_discovery_metadata(_decode(members, opf_path), policy).encode(
        "utf-8"
    )
    members[nav_path] = _replace_navigation(
        _decode(members, nav_path),
        policy,
        nav_path,
        title_candidates[0],
        id_files,
        pages,
    ).encode("utf-8")
    # Pandoc's Lua attribute maps do not retain iteration order. Canonicalize
    # every XHTML member so equivalent attributes produce identical bytes.
    for path in members:
        if path.endswith((".xhtml", ".html", ".htm")):
            members[path] = canonicalize_markup(_decode(members, path)).encode("utf-8")
    _write_members(epub_path, infos, members)


def _text(element: ET.Element) -> str:
    return " ".join("".join(element.itertext()).split())


def _classes(element: ET.Element) -> set[str]:
    return set((element.get("class") or "").split())


def _resolve_href(source_path: str, href: str) -> tuple[str, str]:
    path, _, fragment = href.partition("#")
    if not path:
        resolved = source_path
    else:
        resolved = posixpath.normpath(posixpath.join(posixpath.dirname(source_path), path))
    return resolved, fragment


def _validate_metadata(package: ET.Element, policy: dict) -> None:
    package_language = package.get(f"{{{XML_NS}}}lang")
    if package_language != policy["language"]:
        fail("EPUB package xml:lang does not match accessibility policy")
    languages = [
        _text(element)
        for element in package.findall(f".//{{{OPF_NS}}}metadata/{{{DC_NS}}}language")
    ]
    if languages != [policy["language"]]:
        fail("EPUB dc:language must exactly match the publication language")
    observed: dict[str, list[str]] = {value: [] for value in PROPERTY_NAMES.values()}
    page_sources = []
    conformance = []
    for meta in package.findall(f".//{{{OPF_NS}}}metadata/{{{OPF_NS}}}meta"):
        prop = meta.get("property") or ""
        if prop in observed:
            observed[prop].append(_text(meta))
        elif prop == "pageBreakSource":
            page_sources.append(_text(meta))
        elif prop == "dcterms:conformsTo":
            conformance.append(_text(meta))
    for key, property_name in PROPERTY_NAMES.items():
        expected = policy["discovery"][key]
        expected_values = expected if isinstance(expected, list) else [expected]
        if observed[property_name] != expected_values:
            fail(f"EPUB discovery metadata {property_name} does not match policy")
    if conformance:
        fail("EPUB must not emit a conformance claim before manual review passes")
    pagination = policy["pagination"]
    expected_sources = (
        [pagination["page_break_source"]] if pagination["mode"] == "print-equivalent" else []
    )
    if page_sources != expected_sources:
        fail("EPUB pageBreakSource does not match pagination policy")


def _parse_documents(
    members: dict[str, bytes], paths: list[str], language: str
) -> tuple[dict[str, ET.Element], dict[str, dict[str, ET.Element]]]:
    documents: dict[str, ET.Element] = {}
    ids: dict[str, dict[str, ET.Element]] = {}
    for path in paths:
        try:
            root = DefusedET.fromstring(members[path])
        except (KeyError, ET.ParseError) as error:
            fail(f"EPUB content document {path} is invalid XML: {error}")
        if root.get("lang") != language or root.get(f"{{{XML_NS}}}lang") != language:
            fail(f"EPUB content document {path} must declare lang and xml:lang")
        documents[path] = root
        ids[path] = {}
        for element in root.iter():
            target = element.get("id")
            if not target:
                continue
            if target in ids[path]:
                fail(f"duplicate rendered EPUB id {target} within {path}")
            ids[path][target] = element
    return documents, ids


def _locate_id(ids: dict[str, dict[str, ET.Element]], target: str) -> tuple[str, ET.Element]:
    matches = [(path, values[target]) for path, values in ids.items() if target in values]
    if len(matches) != 1:
        fail(f"EPUB semantic target {target} must occur exactly once")
    return matches[0]


def _validate_sections(
    documents: dict[str, ET.Element],
    ids: dict[str, dict[str, ET.Element]],
    policy: dict,
) -> None:
    for section in policy["sections"]:
        target = section["id"]
        path, element = _locate_id(ids, target)
        kind = section["epub_type"]
        if kind is not None:
            if element.get(f"{{{EPUB_NS}}}type") != kind:
                fail(f"EPUB semantic section {target} has the wrong epub:type")
            if element.get("role") != section["role"]:
                fail(f"EPUB semantic section {target} has the wrong DPUB-ARIA role")
        body = documents[path].find(f".//{{{XHTML_NS}}}body")
        if body is None or body.get(f"{{{EPUB_NS}}}type") != section["body_type"]:
            fail(f"EPUB semantic section {target} has the wrong body division")


def _validate_navigation(
    nav_path: str,
    nav: ET.Element,
    ids: dict[str, dict[str, ET.Element]],
    members: dict[str, bytes],
    spine: list[str],
    policy: dict,
) -> None:
    navigations = nav.findall(f".//{{{XHTML_NS}}}nav")
    by_type = {}
    for element in navigations:
        kind = element.get(f"{{{EPUB_NS}}}type")
        if kind:
            if kind in by_type:
                fail(f"EPUB navigation document repeats {kind}")
            by_type[kind] = element
    if "toc" not in by_type or "landmarks" not in by_type:
        fail("EPUB navigation needs toc and landmarks")
    expected_landmarks = {item["type"] for item in policy["landmarks"]}
    observed_landmarks = set()
    for anchor in by_type["landmarks"].findall(f".//{{{XHTML_NS}}}a"):
        kind = anchor.get(f"{{{EPUB_NS}}}type")
        href = anchor.get("href") or ""
        if not kind or not _text(anchor):
            fail("EPUB landmark needs a type and visible label")
        observed_landmarks.add(kind)
        path, fragment = _resolve_href(nav_path, href)
        if path not in members:
            fail(f"EPUB landmark {kind} references missing document {path}")
        if (
            fragment
            and fragment not in ids.get(path, {})
            and not (path == nav_path and fragment == "toc")
        ):
            fail(f"EPUB landmark {kind} references missing fragment {fragment}")
    if observed_landmarks != expected_landmarks:
        fail("EPUB landmarks do not exactly match accessibility policy")

    spine_index = {path: index for index, path in enumerate(spine)}
    toc_positions = []
    for anchor in by_type["toc"].findall(f".//{{{XHTML_NS}}}a"):
        href = anchor.get("href") or ""
        if not _text(anchor):
            fail("EPUB table of contents contains an empty link")
        path, fragment = _resolve_href(nav_path, href)
        if path not in spine_index:
            fail(f"EPUB table of contents target is outside the spine: {path}")
        if fragment not in ids.get(path, {}):
            fail(f"EPUB table of contents references missing fragment {fragment}")
        toc_positions.append(spine_index[path])
    if not toc_positions or toc_positions != sorted(toc_positions):
        fail("EPUB table of contents order must follow the spine reading order")

    pagination = policy["pagination"]
    page_list = by_type.get("page-list")
    markers = []
    for path, path_ids in ids.items():
        for target, element in path_ids.items():
            if element.get(f"{{{EPUB_NS}}}type") == "pagebreak":
                markers.append((path, target, element))
    if pagination["mode"] == "not-applicable":
        if page_list is not None or markers:
            fail("EPUB without an identified print equivalent must not emit page navigation")
        return
    if page_list is None:
        fail("print-equivalent EPUB needs a page-list navigation")
    expected = pagination["pages"]
    links = page_list.findall(f".//{{{XHTML_NS}}}a")
    if len(links) != len(expected) or len(markers) != len(expected):
        fail("EPUB page list, markers, and pagination policy must have equal coverage")
    observed = []
    for link in links:
        label = _text(link)
        path, fragment = _resolve_href(nav_path, link.get("href") or "")
        if fragment not in ids.get(path, {}):
            fail(f"EPUB page list references missing marker {fragment}")
        marker = ids[path][fragment]
        if marker.get(f"{{{EPUB_NS}}}type") != "pagebreak":
            fail(f"EPUB page list target {fragment} is not a page break")
        if marker.get("role") != "doc-pagebreak" or not marker.get("aria-label"):
            fail(f"EPUB page marker {fragment} lacks accessible semantics")
        observed.append((label, fragment))
    expected_pairs = [(page["label"], _slug_page_label(page["label"])) for page in expected]
    if observed != expected_pairs:
        fail("EPUB page-list order or labels do not match pagination policy")


def _validate_headings(documents: dict[str, ET.Element]) -> int:
    count = 0
    for path, root in documents.items():
        levels = []
        for element in root.iter():
            local = element.tag.rsplit("}", 1)[-1]
            if re.fullmatch(r"h[1-6]", local):
                if not _text(element):
                    fail(f"EPUB heading in {path} has no text")
                levels.append(int(local[1]))
        if not levels:
            fail(f"EPUB content document {path} has no heading")
        for previous, current in itertools.pairwise(levels):
            if current > previous + 1:
                fail(f"EPUB heading outline skips a level in {path}")
        count += len(levels)
    return count


def _validate_tables(documents: dict[str, ET.Element]) -> int:
    count = 0
    for path, root in documents.items():
        parent = {child: node for node in root.iter() for child in node}
        ids = {element.get("id"): element for element in root.iter() if element.get("id")}
        for table in root.findall(f".//{{{XHTML_NS}}}table"):
            count += 1
            headers = table.findall(f".//{{{XHTML_NS}}}th")
            if not headers or any(not _text(header) for header in headers):
                fail(f"EPUB data table in {path} needs nonempty header cells")
            caption = table.find(f"{{{XHTML_NS}}}caption")
            described = False
            titled_section = False
            node = table
            while node in parent:
                node = parent[node]
                references = (node.get("aria-describedby") or "").split()
                if references and all(ref in ids and _text(ids[ref]) for ref in references):
                    described = True
                    break
                if node.tag == f"{{{XHTML_NS}}}section":
                    titled_section = any(
                        re.fullmatch(r"h[1-6]", child.tag.rsplit("}", 1)[-1]) and _text(child)
                        for child in node
                    )
            if (caption is None or not _text(caption)) and not described and not titled_section:
                fail(f"EPUB data table in {path} needs an associated caption")
    return count


def _validate_images(documents: dict[str, ET.Element]) -> int:
    count = 0
    for path, root in documents.items():
        elements = list(root.iter())
        for index, image in enumerate(elements):
            if image.tag != f"{{{XHTML_NS}}}img":
                continue
            count += 1
            alt = image.get("alt")
            if alt is None:
                fail(f"EPUB image in {path} has no alt attribute")
            if alt.strip():
                continue
            described = False
            for later in elements[index + 1 :]:
                if later.tag == f"{{{XHTML_NS}}}img":
                    break
                if "diagram-description" in _classes(later) and _text(later):
                    described = True
                    break
            if not described:
                fail(
                    f"EPUB non-text content in {path} has an empty alternative without an adjacent description"
                )
    return count


def _validate_math(
    documents: dict[str, ET.Element], manifest_root: ET.Element, manifest: dict[str, str]
) -> int:
    properties = {}
    for item in manifest_root.findall(f".//{{{OPF_NS}}}manifest/{{{OPF_NS}}}item"):
        item_id = item.get("id")
        if item_id is not None and item_id in manifest:
            properties[manifest[item_id]] = set((item.get("properties") or "").split())
    count = 0
    math_ns = "http://www.w3.org/1998/Math/MathML"
    for path, root in documents.items():
        math_elements = root.findall(f".//{{{math_ns}}}math")
        if math_elements and "mathml" not in properties.get(path, set()):
            fail(f"EPUB manifest does not declare MathML for {path}")
        for math in math_elements:
            count += 1
            annotation = math.find(f".//{{{math_ns}}}annotation")
            if annotation is None or not _text(annotation):
                fail(f"EPUB MathML in {path} needs a textual source annotation")
    if not count:
        fail("reference EPUB must exercise MathML")
    return count


def _validate_links(
    documents: dict[str, ET.Element],
    ids: dict[str, dict[str, ET.Element]],
    members: dict[str, bytes],
) -> int:
    count = 0
    for path, root in documents.items():
        for anchor in root.findall(f".//{{{XHTML_NS}}}a"):
            count += 1
            if anchor.get("aria-hidden") == "true" and anchor.get("tabindex") == "-1":
                continue
            purpose = _text(anchor) or anchor.get("aria-label") or anchor.get("title") or ""
            if not purpose.strip():
                fail(f"EPUB link in {path} has no accessible purpose")
            if purpose.strip().casefold() in GENERIC_LINK_TEXT:
                fail(f"EPUB link in {path} uses generic purpose text: {purpose}")
            href = anchor.get("href") or ""
            if not href or href.lower().startswith(("javascript:", "data:")):
                fail(f"EPUB link in {path} has an unsafe or empty destination")
            if re.match(r"^[A-Za-z][A-Za-z0-9+.-]*:", href):
                continue
            target_path, fragment = _resolve_href(path, href)
            if target_path not in members:
                fail(f"EPUB link in {path} references missing document {target_path}")
            if fragment and fragment not in ids.get(target_path, {}):
                fail(f"EPUB link in {path} references missing fragment {fragment}")
    return count


def validate_epub(epub_path: Path, policy_path: Path) -> dict[str, int]:
    policy = load_policy(policy_path)
    _, members = _read_members(epub_path)
    opf_path, package, nav_path, manifest, spine = _package_inventory(members)
    del opf_path
    _validate_metadata(package, policy)
    xhtml_paths = [path for path in manifest.values() if path.endswith((".xhtml", ".html", ".htm"))]
    documents, ids = _parse_documents(members, xhtml_paths, policy["language"])
    _validate_sections(documents, ids, policy)
    _validate_navigation(nav_path, documents[nav_path], ids, members, spine, policy)
    counts = {
        "documents": len(documents),
        "headings": _validate_headings(documents),
        "tables": _validate_tables(documents),
        "images": _validate_images(documents),
        "math": _validate_math(documents, package, manifest),
        "links": _validate_links(documents, ids, members),
    }
    return counts
