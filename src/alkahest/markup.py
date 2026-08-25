"""Canonicalize generated markup without reparsing or changing text content."""

import re

RAW_TEXT_ELEMENTS = {"script", "style"}
UNORDERED_ATTRIBUTES = {"dir", "epub:type", "lang", "role", "xml:lang"}


def _tag_end(text, start):
    quote = None
    for index in range(start, len(text)):
        character = text[index]
        if quote:
            if character == quote:
                quote = None
        elif character in {'"', "'"}:
            quote = character
        elif character == ">":
            return index
    return -1


def _attributes(text):
    attributes: list[tuple[int, str, int, str]] = []
    index = 0
    while index < len(text):
        while index < len(text) and text[index].isspace():
            index += 1
        if index == len(text):
            break
        start = index
        while index < len(text) and not text[index].isspace() and text[index] not in "=/":
            index += 1
        name = text[start:index]
        if not name:
            return None
        while index < len(text) and text[index].isspace():
            index += 1
        value = ""
        if index < len(text) and text[index] == "=":
            index += 1
            while index < len(text) and text[index].isspace():
                index += 1
            if index == len(text):
                return None
            if text[index] in {'"', "'"}:
                quote = text[index]
                value_start = index
                index += 1
                while index < len(text) and text[index] != quote:
                    index += 1
                if index == len(text):
                    return None
                index += 1
                value = "=" + text[value_start:index]
            else:
                value_start = index
                while index < len(text) and not text[index].isspace():
                    index += 1
                value = "=" + text[value_start:index]
        lowered = name.lower()
        unordered = lowered.startswith(("aria-", "data-")) or lowered in UNORDERED_ATTRIBUTES
        attributes.append(
            (
                1 if unordered else 0,
                lowered if unordered else "",
                len(attributes),
                name + value,
            )
        )
    return attributes


def _canonical_start_tag(raw):
    self_closing = bool(re.search(r"/\s*$", raw))
    body = re.sub(r"/\s*$", "", raw).strip() if self_closing else raw.strip()
    match = re.match(r"([^\s/>]+)(.*)$", body, re.DOTALL)
    if not match:
        return raw, ""
    tag_name = match.group(1)
    attributes = _attributes(match.group(2))
    if attributes is None:
        return raw, tag_name.lower()
    # Pandoc's built-in element attributes already have stable, meaningful
    # writer order. Only custom data-bearing attribute maps originate in Lua
    # hash tables and need canonical serialization.
    if not any(item[1].startswith(("aria-", "data-")) for item in attributes):
        return raw, tag_name.lower()
    ordered = " ".join(item[3] for item in sorted(attributes))
    suffix = " /" if self_closing else ""
    space = " " if ordered else ""
    return tag_name + space + ordered + suffix, tag_name.lower()


def canonicalize_markup(text):
    """Sort attributes in actual start tags while preserving raw-text bodies."""

    result = []
    cursor = 0
    lowered = text.lower()
    while cursor < len(text):
        start = text.find("<", cursor)
        if start < 0:
            result.append(text[cursor:])
            break
        result.append(text[cursor:start])
        if text.startswith("<!--", start):
            end = text.find("-->", start + 4)
            end = len(text) - 3 if end < 0 else end
            result.append(text[start : end + 3])
            cursor = end + 3
            continue
        if text.startswith("<![CDATA[", start):
            end = text.find("]]>", start + 9)
            end = len(text) - 3 if end < 0 else end
            result.append(text[start : end + 3])
            cursor = end + 3
            continue
        if text.startswith("<?", start):
            end = text.find("?>", start + 2)
            end = len(text) - 2 if end < 0 else end
            result.append(text[start : end + 2])
            cursor = end + 2
            continue
        end = _tag_end(text, start + 1)
        if end < 0:
            result.append(text[start:])
            break
        raw = text[start + 1 : end]
        if raw.startswith(("/", "!")):
            result.append(text[start : end + 1])
            cursor = end + 1
            continue
        canonical, tag_name = _canonical_start_tag(raw)
        result.append("<" + canonical + ">")
        cursor = end + 1
        if tag_name in RAW_TEXT_ELEMENTS:
            closing = lowered.find("</" + tag_name, cursor)
            if closing < 0:
                result.append(text[cursor:])
                break
            result.append(text[cursor:closing])
            cursor = closing
    return "".join(result)
