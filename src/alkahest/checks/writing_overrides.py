"""Enforce narrow, balanced, and justified writing-check overrides."""

import argparse
import json
import re
import sys
from pathlib import Path

REPOSITORY_ROOT = Path(__file__).resolve().parents[3]

from .writing_sources import writing_sources

CSPELL_DIRECTIVE = re.compile(r"cspell\s*:\s*([A-Za-z-]+)(?:\s+(.*?))?", re.I)
HTML_COMMENT = re.compile(r"<!--[ \t]*(.*?)[ \t]*-->", re.S)
REASON = re.compile(r"writing-override\s*:\s*(.+)", re.I)
VALE_RULE = re.compile(
    r"vale\s+([A-Za-z][A-Za-z0-9-]*\.[A-Za-z][A-Za-z0-9-]*)"
    r"(?:\s*(\[.*\]))?\s*=\s*(NO|YES)",
    re.I,
)
FENCE_OPEN = re.compile(r"^[ \t]{0,3}(`{3,}|~{3,})")
INLINE_CODE = re.compile(r"(`+)[^\n]*?\1")
CONFIG_REASON = re.compile(r"#[ \t]*writing-override\s*:\s*(.+)", re.I)
VALE_CONFIG_DISABLE = re.compile(
    r"^([A-Za-z][A-Za-z0-9-]*\.[A-Za-z][A-Za-z0-9-]*)\s*=\s*NO\s*$",
    re.I,
)


def fail(message):
    raise RuntimeError("error: " + message)


def substantive_reason(reason):
    words = re.findall(r"[\w'-]+", reason, re.UNICODE)
    return len(reason.strip()) >= 16 and len(words) >= 4


def mask_line(line):
    return INLINE_CODE.sub(lambda match: " " * len(match.group(0)), line)


def mask_code(text):
    output = []
    fence_character = None
    fence_length = 0
    for line in text.splitlines(keepends=True):
        body = line.rstrip("\r\n")
        ending = line[len(body) :]
        if fence_character is not None:
            closing = re.match(
                rf"^[ \t]{{0,3}}{re.escape(fence_character)}{{{fence_length},}}[ \t]*$",
                body,
            )
            output.append(" " * len(body) + ending)
            if closing:
                fence_character = None
                fence_length = 0
            continue
        opening = FENCE_OPEN.match(body)
        if opening:
            fence_character = opening.group(1)[0]
            fence_length = len(opening.group(1))
            output.append(" " * len(body) + ending)
            continue
        output.append(mask_line(body) + ending)
    return "".join(output)


def mask_comments(text):
    return HTML_COMMENT.sub(
        lambda match: re.sub(r"[^\n]", " ", match.group(0)),
        text,
    )


def line_number(text, offset):
    return text.count("\n", 0, offset) + 1


def source_paths(root):
    relative_paths = writing_sources(root)
    if not relative_paths:
        fail("no canonical writing sources found")
    return [root / relative for relative in relative_paths]


def rejected_terms(root):
    path = root / "config/writing/terminology.json"
    try:
        registry = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        fail(f"cannot load rejected terminology for override policy: {error}")
    terms = registry.get("rejected_terms")
    if not isinstance(terms, list):
        fail("terminology registry has no rejected_terms list")
    return {
        item["term"].casefold()
        for item in terms
        if isinstance(item, dict) and isinstance(item.get("term"), str)
    }


def parse_match_selector(selector, location):
    if selector is None:
        return None
    try:
        matches = json.loads(selector)
    except json.JSONDecodeError as error:
        fail(f"{location}: invalid Vale match selector: {error.msg}")
    if not isinstance(matches, list) or not matches:
        fail(f"{location}: Vale match selector must be a nonempty JSON array")
    if any(not isinstance(item, str) or not item.strip() for item in matches):
        fail(f"{location}: Vale match selector entries must be nonempty strings")
    return tuple(matches)


def token_occurrences(masked_sources, token):
    pattern = re.compile(rf"(?<!\w){re.escape(token)}(?!\w)", re.I)
    return {
        path: len(pattern.findall(text))
        for path, text in masked_sources.items()
        if pattern.search(text)
    }


def require_reason(comments, index, used_reasons, location):
    if index == 0:
        fail(f"{location}: broad override needs an immediately preceding writing-override reason")
    previous = comments[index - 1]
    reason_match = REASON.fullmatch(previous["body"])
    if not reason_match or previous["line"] + 1 != comments[index]["line"]:
        fail(f"{location}: broad override needs an immediately preceding writing-override reason")
    reason = reason_match.group(1).strip()
    if not substantive_reason(reason):
        fail(f"{previous['location']}: writing-override reason must contain at least four words")
    used_reasons.add(index - 1)


def check_source(path, root, masked_sources, rejected):
    text = path.read_text(encoding="utf-8")
    masked = mask_code(text)
    relative = path.relative_to(root).as_posix()
    comments = []
    for match in HTML_COMMENT.finditer(masked):
        line = line_number(masked, match.start())
        comments.append(
            {
                "body": match.group(1).strip(),
                "line": line,
                "location": f"{relative}:{line}",
            }
        )

    used_reasons = set()
    cspell_disabled = None
    vale_disabled = {}
    override_count = 0
    broad_count = 0

    for index, comment in enumerate(comments):
        body = comment["body"]
        location = comment["location"]
        if REASON.fullmatch(body):
            continue

        cspell = CSPELL_DIRECTIVE.fullmatch(body)
        if cspell:
            command = cspell.group(1).lower()
            argument = (cspell.group(2) or "").strip()
            if command == "disable":
                if argument:
                    fail(f"{location}: cspell:disable does not accept an argument")
                if cspell_disabled is not None:
                    fail(f"{location}: nested cspell:disable is not supported")
                require_reason(comments, index, used_reasons, location)
                cspell_disabled = location
                broad_count += 1
            elif command == "enable":
                if argument:
                    fail(f"{location}: cspell:enable does not accept an argument")
                if cspell_disabled is None:
                    fail(f"{location}: cspell:enable has no matching disable")
                cspell_disabled = None
            elif command in {"disable-line", "disable-next-line"}:
                if argument:
                    fail(f"{location}: cspell:{command} does not accept an argument")
                require_reason(comments, index, used_reasons, location)
                broad_count += 1
            elif command in {"ignore", "words"}:
                tokens = argument.split()
                if not tokens:
                    fail(f"{location}: cspell:{command} needs at least one token")
                if len(tokens) != len(set(token.casefold() for token in tokens)):
                    fail(f"{location}: cspell:{command} contains duplicate tokens")
                if any(token.casefold() in rejected for token in tokens):
                    require_reason(comments, index, used_reasons, location)
                for token in tokens:
                    occurrences = token_occurrences(masked_sources, token)
                    total = sum(occurrences.values())
                    if total == 0:
                        fail(f"{location}: '{token}' does not appear in checked prose")
                    if command == "ignore" and total > 1:
                        fail(
                            f"{location}: '{token}' recurs; use cspell:words for one-file "
                            "vocabulary or the narrowest dictionary"
                        )
                    if command == "words" and len(occurrences) > 1:
                        fail(
                            f"{location}: '{token}' appears in multiple files; add it to "
                            "the narrowest book or shared dictionary"
                        )
                override_count += len(tokens)
            else:
                fail(
                    f"{location}: unsupported CSpell override '{command}'; use a documented "
                    "narrow mechanism"
                )
            continue

        if body.lower() in {"vale off", "vale on"}:
            fail(f"{location}: blanket Vale off/on overrides are not allowed")

        vale = VALE_RULE.fullmatch(body)
        if vale:
            rule = vale.group(1)
            selector = parse_match_selector(vale.group(2), location)
            enabled = vale.group(3).upper() == "YES"
            key = (rule.casefold(), selector)
            if not enabled:
                if key in vale_disabled:
                    fail(f"{location}: Vale override is already disabled: {rule}")
                if selector is None:
                    require_reason(comments, index, used_reasons, location)
                    broad_count += 1
                else:
                    if any(item.casefold() in rejected for item in selector):
                        require_reason(comments, index, used_reasons, location)
                    override_count += len(selector)
                vale_disabled[key] = location
            else:
                if key not in vale_disabled:
                    fail(f"{location}: Vale rule enable has no matching disable: {rule}")
                del vale_disabled[key]
            continue

        if body.lower().startswith(("cspell", "spell-checker", "spellchecker", "vale")):
            fail(f"{location}: malformed or unsupported writing-check directive")

    if cspell_disabled is not None:
        fail(f"{cspell_disabled}: cspell:disable is not restored with cspell:enable")
    if vale_disabled:
        rule, location = next((key[0], value) for key, value in vale_disabled.items())
        fail(f"{location}: Vale rule override is not restored with YES: {rule}")
    for index, comment in enumerate(comments):
        if REASON.fullmatch(comment["body"]) and index not in used_reasons:
            fail(f"{comment['location']}: writing-override reason is not attached to an override")
    return override_count, broad_count


def check_cspell_config(root):
    path = root / "cspell.json"
    try:
        config = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        fail(f"cannot validate cspell.json override policy: {error}")
    forbidden = {"enabled", "ignoreWords", "words"}
    found = forbidden & set(config)
    if found:
        fields = ", ".join(sorted(found))
        fail(
            f"cspell.json uses top-level {fields}; put accepted terminology in the "
            "registry or use a documented source-local directive"
        )
    for index, override in enumerate(config.get("overrides", []), start=1):
        found = forbidden & set(override)
        if found:
            fields = ", ".join(sorted(found))
            fail(
                f"cspell.json override {index} uses {fields}; put accepted terminology in "
                "the registry or use a documented source-local directive"
            )


def check_vale_config(root):
    path = root / ".vale.ini"
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except OSError as error:
        fail(f"cannot validate .vale.ini override policy: {error}")
    for index, line in enumerate(lines):
        match = VALE_CONFIG_DISABLE.fullmatch(line.strip())
        if not match or match.group(1).casefold() == "vale.spelling":
            continue
        if index == 0:
            fail(f".vale.ini:{index + 1}: disabled rule needs a writing-override reason")
        reason = CONFIG_REASON.fullmatch(lines[index - 1].strip())
        if not reason or not substantive_reason(reason.group(1)):
            fail(
                f".vale.ini:{index + 1}: disabled rule needs an immediately preceding, "
                "substantive writing-override reason"
            )


def main():
    parser = argparse.ArgumentParser(description="Validate writing-check override policy.")
    parser.add_argument(
        "--root",
        type=Path,
        default=REPOSITORY_ROOT,
        help="repository root to validate (defaults to this checkout)",
    )
    args = parser.parse_args()
    root = args.root.resolve()
    paths = source_paths(root)
    rejected = rejected_terms(root)
    masked_sources = {
        path: mask_comments(mask_code(path.read_text(encoding="utf-8"))) for path in paths
    }
    check_cspell_config(root)
    check_vale_config(root)
    overrides = 0
    broad = 0
    for path in paths:
        local_overrides, broad_overrides = check_source(path, root, masked_sources, rejected)
        overrides += local_overrides
        broad += broad_overrides
    print(
        f"ok: writing override policy ({len(paths)} sources; "
        f"{overrides} token/match overrides; {broad} justified broad suppressions)"
    )


if __name__ == "__main__":
    try:
        main()
    except (OSError, UnicodeDecodeError, RuntimeError) as error:
        print(str(error), file=sys.stderr)
        sys.exit(1)
