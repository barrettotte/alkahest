"""Validate language metadata and localized semantics in HTML and EPUB output."""

from __future__ import annotations

import argparse
import json
import re
import sys
from html.parser import HTMLParser
from pathlib import Path, PurePosixPath
from zipfile import BadZipFile, ZipFile

ROOT = Path(__file__).resolve().parents[3]
DEFAULT_POLICY = ROOT / "config" / "localization" / "locales.json"


class RenderedLocalizationError(RuntimeError):
    """Report a rendered localization contract failure."""


class LanguageMarkup(HTMLParser):
    """Collect document and element language attributes from HTML or XHTML."""

    def __init__(self):
        super().__init__(convert_charrefs=False)
        self.root = None
        self.scopes = []

    def handle_starttag(self, tag, attrs):
        attributes = dict(attrs)
        if tag == "html" and self.root is None:
            self.root = attributes
        language = attributes.get("lang")
        if language:
            self.scopes.append((language, attributes.get("dir", "ltr")))


def fail(message):
    raise RenderedLocalizationError(message)


def arguments():
    parser = argparse.ArgumentParser(
        description="Validate localization semantics in rendered HTML and EPUB."
    )
    parser.add_argument("policy", nargs="?", type=Path, default=DEFAULT_POLICY)
    parser.add_argument("--repo-root", type=Path, default=ROOT)
    return parser.parse_args()


def repo_path(root, value, label):
    if not isinstance(value, str) or not value:
        fail(f"{label} must be a repository-relative path")
    path = PurePosixPath(value)
    if path.is_absolute() or ".." in path.parts or str(path) != value:
        fail(f"{label} must be a normalized repository-relative path")
    return root / Path(*path.parts)


def read_file(path, label):
    if not path.is_file():
        fail(f"missing {label}: {path}")
    return path.read_text(encoding="utf-8")


def parse_markup(content, label):
    parser = LanguageMarkup()
    parser.feed(content)
    parser.close()
    if parser.root is None:
        fail(f"{label} has no html root element")
    return parser


def check_root(parser, expected, label):
    language = parser.root.get("lang")
    xml_language = parser.root.get("xml:lang")
    if language != expected or xml_language != expected:
        fail(
            f"{label} must declare lang and xml:lang as {expected}; "
            f"found {language!r} and {xml_language!r}"
        )


def check_scopes(scopes, languages, label):
    allowed = {entry["tag"]: entry["direction"] for entry in languages}
    for tag, direction in scopes:
        if tag not in allowed:
            fail(f"{label} contains undeclared language tag '{tag}'")
        if direction != allowed[tag]:
            fail(
                f"{label} language {tag} needs dir={allowed[tag]}; "
                f"found {direction}"
            )
    missing = sorted(set(allowed) - {tag for tag, _ in scopes})
    if missing:
        fail(f"{label} is missing language semantics: {', '.join(missing)}")


def check_html(root, contract, policy):
    canonical = policy["canonical_locale"]
    canonical_path = repo_path(root, contract.get("canonical_html"), "canonical HTML")
    canonical_markup = parse_markup(read_file(canonical_path, "canonical HTML"), "canonical HTML")
    check_root(canonical_markup, canonical, "canonical HTML")

    specimen_path = repo_path(
        root, contract.get("language_specimen_html"), "language specimen HTML"
    )
    specimen = parse_markup(
        read_file(specimen_path, "language specimen HTML"),
        "language specimen HTML",
    )
    check_root(specimen, canonical, "language specimen HTML")
    check_scopes(specimen.scopes, policy["inline_languages"], "language specimen HTML")

    locale_count = 0
    for locale in policy["locales"]:
        if locale["mode"] == "canonical":
            continue
        locale_path = repo_path(
            root, locale.get("rendered_html"), f"locale {locale['tag']} HTML"
        )
        reference_path = repo_path(
            root,
            locale.get("rendered_reference_html"),
            f"locale {locale['tag']} reference HTML",
        )
        label = f"locale {locale['tag']} HTML"
        reference_label = f"locale {locale['tag']} reference HTML"
        locale_text = read_file(locale_path, label)
        reference_text = read_file(reference_path, reference_label)
        locale_markup = parse_markup(locale_text, label)
        reference_markup = parse_markup(reference_text, reference_label)
        check_root(locale_markup, locale["tag"], label)
        check_root(reference_markup, locale["tag"], reference_label)
        rendered = locale_text + reference_text
        for marker in locale.get("rendered_markers", []):
            if marker not in rendered:
                fail(f"locale {locale['tag']} output is missing marker: {marker}")
        locale_count += 1
    return locale_count


def check_epub(root, contract, policy):
    canonical = policy["canonical_locale"]
    epub_path = repo_path(root, contract.get("epub"), "EPUB")
    if not epub_path.is_file():
        fail(f"missing EPUB: {epub_path}")
    try:
        with ZipFile(epub_path) as archive:
            names = archive.namelist()
            opf_names = [name for name in names if name.endswith(".opf")]
            if len(opf_names) != 1:
                fail(f"EPUB must contain exactly one OPF; found {len(opf_names)}")
            opf = archive.read(opf_names[0]).decode("utf-8")
            if not re.search(
                rf"<dc:language(?:\s[^>]*)?>\s*{re.escape(canonical)}\s*</dc:language>",
                opf,
            ):
                fail(f"EPUB package metadata must declare {canonical}")

            xhtml_names = sorted(name for name in names if name.endswith(".xhtml"))
            if not xhtml_names:
                fail("EPUB contains no XHTML documents")
            scopes = []
            for name in xhtml_names:
                content = archive.read(name).decode("utf-8")
                markup = parse_markup(content, f"EPUB entry {name}")
                check_root(markup, canonical, f"EPUB entry {name}")
                scopes.extend(markup.scopes)
            check_scopes(scopes, policy["inline_languages"], "EPUB content")

            stylesheets = [name for name in names if name.endswith(".css")]
            styles = "\n".join(
                archive.read(name).decode("utf-8") for name in stylesheets
            )
            if not re.search(r"(?:^|[;{])\s*hyphens\s*:\s*auto\s*;", styles):
                fail("EPUB styles must preserve language-aware hyphens: auto")
    except (BadZipFile, KeyError, UnicodeDecodeError) as error:
        fail(f"cannot inspect EPUB: {error}")
    return len(xhtml_names)


def validate(policy, root):
    if not isinstance(policy, dict) or policy.get("schema_version") != 1:
        fail("localization policy must use schema_version 1")
    if not isinstance(policy.get("inline_languages"), list):
        fail("localization policy needs inline_languages")
    if not isinstance(policy.get("locales"), list):
        fail("localization policy needs locales")
    contract = policy.get("rendered_contract")
    if not isinstance(contract, dict):
        fail("localization policy needs rendered_contract")
    locale_count = check_html(root, contract, policy)
    xhtml_count = check_epub(root, contract, policy)
    return locale_count, xhtml_count


def main():
    options = arguments()
    root = options.repo_root.resolve()
    policy_path = options.policy
    if not policy_path.is_absolute():
        policy_path = root / policy_path
    try:
        policy = json.loads(policy_path.read_text(encoding="utf-8"))
        locale_count, xhtml_count = validate(policy, root)
    except (OSError, json.JSONDecodeError, RenderedLocalizationError) as error:
        print(f"error: {error}", file=sys.stderr)
        return 1
    print(
        "ok: rendered localization "
        f"({locale_count} locale smoke profile; {xhtml_count} EPUB XHTML files; "
        f"{len(policy['inline_languages'])} language semantics)"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
