"""Exercise localization source and rendered-output contracts."""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile


ROOT = Path(__file__).resolve().parent.parent.parent
SOURCE_CHECKER = ("-m", "alkahest.checks.localization")
RENDERED_CHECKER = ("-m", "alkahest.checks.rendered_localization")
LANGUAGES = (
    ("en-US", "ltr", "English"),
    ("fr-FR", "ltr", "Français"),
    ("de-DE", "ltr", "Deutsch"),
    ("el-GR", "ltr", "Ελληνικά"),
    ("ru-RU", "ltr", "Русский"),
    ("he-IL", "rtl", "עברית"),
)
PACKAGES = (
    "babel-english",
    "hyphen-english",
    "babel-french",
    "hyphen-french",
    "babel-german",
    "hyphen-german",
    "babel-greek",
    "hyphen-greek",
    "babel-russian",
    "hyphen-russian",
    "ruhyphen",
    "babel-hebrew",
)
PACKAGES_BY_TAG = {
    "en-US": ["babel-english", "hyphen-english"],
    "fr-FR": ["babel-french", "hyphen-french"],
    "de-DE": ["babel-german", "hyphen-german"],
    "el-GR": ["babel-greek", "hyphen-greek"],
    "ru-RU": ["babel-russian", "hyphen-russian", "ruhyphen"],
    "he-IL": ["babel-hebrew"],
}


def write(path, content):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def policy():
    return {
        "schema_version": 1,
        "canonical_locale": "en-US",
        "font_family": "Libertinus Serif",
        "locales": [
            {
                "tag": "en-US",
                "mode": "canonical",
                "direction": "ltr",
                "root": "book",
                "profile": "book/_quarto.yml",
                "language_profile": "book/generated/metadata.yml",
                "required_profile_markers": [
                    "lang: en-US",
                    'toc-title: "Contents"',
                ],
            },
            {
                "tag": "fr-FR",
                "mode": "shared-source-smoke",
                "direction": "ltr",
                "root": "book",
                "profile": "book/_quarto-locale-fr.yml",
                "required_profile_markers": [
                    "lang: fr-FR",
                    'toc-title: "Table des matières"',
                ],
                "rendered_html": "book/_build/locale/fr/html/index.html",
                "rendered_reference_html": ("book/_build/locale/fr/html/reference.html"),
                "rendered_markers": ["Table des matières", "Tableau&nbsp;"],
            },
        ],
        "inline_languages": [
            {
                "tag": tag,
                "direction": direction,
                "scripts": [
                    {
                        "en-US": "Latin",
                        "fr-FR": "Latin",
                        "de-DE": "Latin",
                        "el-GR": "Greek",
                        "ru-RU": "Cyrillic",
                        "he-IL": "Hebrew",
                    }[tag]
                ],
                "toolchain_packages": PACKAGES_BY_TAG[tag],
            }
            for tag, direction, _ in LANGUAGES
        ],
        "unsupported_scripts": ["Arabic", "CJK", "Indic"],
        "source_contract": {
            "manuscript_glob": "book/**/*.qmd",
            "typst_template": "book/typst/typst-show.typ",
            "html_theme": "book/theme/alkahest.scss",
            "epub_theme": "book/theme/alkahest-epub.css",
            "containerfile": "Containerfile",
            "toolchain_report": "src/alkahest/reporting.py",
        },
        "rendered_contract": {
            "canonical_html": "book/_build/html/index.html",
            "language_specimen_html": "book/_build/html/languages.html",
            "epub": "book/_build/epub/book.epub",
        },
    }


def scopes():
    return "\n".join(
        f'<span lang="{tag}"{f' dir="{direction}"' if direction == "rtl" else ""}>{text}</span>'
        for tag, direction, text in LANGUAGES
    )


def manuscript_scopes():
    return "\n".join(
        f'[{text}]{{lang="{tag}"{f' dir="{direction}"' if direction == "rtl" else ""}}}'
        for tag, direction, text in LANGUAGES
    )


def html(language, body):
    return (
        '<!doctype html><html xmlns="http://www.w3.org/1999/xhtml" '
        f'lang="{language}" xml:lang="{language}"><body>{body}</body></html>'
    )


def create_epub(path, specimen):
    with ZipFile(path, "w", ZIP_DEFLATED) as archive:
        archive.writestr(
            "EPUB/content.opf",
            '<package xmlns:dc="http://purl.org/dc/elements/1.1/">'
            "<metadata><dc:language>en-US</dc:language></metadata></package>",
        )
        archive.writestr("EPUB/nav.xhtml", html("en-US", "Contents"))
        archive.writestr("EPUB/text/ch001.xhtml", html("en-US", specimen))
        archive.writestr("EPUB/styles/book.css", "p { hyphens: auto; }")


def create_fixture(root):
    data = policy()
    write(root / "config/localization/locales.json", json.dumps(data, indent=2))
    write(
        root / "book/_quarto.yml",
        'toc-title: "Contents"\nbabel-otherlangs: []\n',
    )
    write(root / "book/generated/metadata.yml", "lang: en-US\n")
    write(
        root / "book/_quarto-locale-fr.yml",
        'lang: fr-FR\ntoc-title: "Table des matières"\n',
    )
    write(root / "book/chapter.qmd", manuscript_scopes())
    write(root / "book/typst/typst-show.typ", "fallback: false")
    write(root / "book/theme/alkahest.scss", "p { hyphens: auto; }")
    write(root / "book/theme/alkahest-epub.css", "p { hyphens: auto; }")
    package_text = "\n".join(PACKAGES)
    write(root / "Containerfile", package_text)
    write(root / "src/alkahest/reporting.py", package_text)

    write(root / "book/_build/html/index.html", html("en-US", "Contents"))
    write(root / "book/_build/html/languages.html", html("en-US", scopes()))
    write(
        root / "book/_build/locale/fr/html/index.html",
        html("fr-FR", "Table des matières"),
    )
    write(
        root / "book/_build/locale/fr/html/reference.html",
        html("fr-FR", "Tableau&nbsp; 1"),
    )
    epub = root / "book/_build/epub/book.epub"
    epub.parent.mkdir(parents=True, exist_ok=True)
    create_epub(epub, scopes())
    return data


def run(checker, root):
    command = list(checker) if isinstance(checker, tuple) else [str(checker)]
    return subprocess.run(
        [
            sys.executable,
            *command,
            "config/localization/locales.json",
            "--repo-root",
            str(root),
        ],
        cwd=root,
        check=False,
        capture_output=True,
        text=True,
    )


def mutate_file(root, path, old, new):
    target = root / path
    content = target.read_text(encoding="utf-8")
    if old not in content:
        raise AssertionError(f"fixture mutation cannot find {old!r} in {path}")
    write(target, content.replace(old, new, 1))


def source_cases():
    return (
        (
            "incorrect canonical language profile",
            lambda root, _: mutate_file(
                root, "book/generated/metadata.yml", "lang: en-US", "lang: en-GB"
            ),
            "profile is missing marker: lang: en-US",
        ),
        (
            "missing locale label",
            lambda root, _: mutate_file(
                root,
                "book/_quarto-locale-fr.yml",
                'toc-title: "Table des matières"',
                'toc-title: "Contents"',
            ),
            "profile is missing marker",
        ),
        (
            "incorrect language tag",
            lambda root, _: mutate_file(root, "book/chapter.qmd", 'lang="el-GR"', 'lang="el-CY"'),
            "undeclared language tag",
        ),
        (
            "missing RTL direction",
            lambda root, _: mutate_file(root, "book/chapter.qmd", ' dir="rtl"', ""),
            "needs dir=rtl",
        ),
        (
            "unsupported CJK",
            lambda root, _: mutate_file(root, "book/chapter.qmd", "Русский", "Русский 漢"),
            "unsupported CJK script",
        ),
        (
            "unscoped non-Latin text",
            lambda root, _: write(root / "book/unscoped.qmd", "Ω"),
            "unscoped Greek character",
        ),
        (
            "mismatched script",
            lambda root, _: mutate_file(root, "book/chapter.qmd", "Русский", "Ελληνικά"),
            "scopes Greek text as ru-RU",
        ),
        (
            "missing language package",
            lambda root, _: (
                mutate_file(root, "Containerfile", "babel-hebrew", "missing"),
                mutate_file(root, "src/alkahest/reporting.py", "babel-hebrew", "missing"),
            ),
            "does not lock package babel-hebrew",
        ),
        (
            "Typst fallback enabled",
            lambda root, _: mutate_file(
                root, "book/typst/typst-show.typ", "fallback: false", "fallback: true"
            ),
            "disable automatic font fallback",
        ),
        (
            "hyphenation disabled",
            lambda root, _: mutate_file(
                root, "book/theme/alkahest.scss", "hyphens: auto", "hyphens: none"
            ),
            "must enable language-aware automatic hyphenation",
        ),
        (
            "incomplete translation manifest",
            incomplete_translation,
            "manifest is incomplete; missing: second.qmd",
        ),
        (
            "missing translation",
            missing_translation,
            "is missing source: chapter.qmd",
        ),
    )


def configure_translation(root, data, sources):
    data["locales"][1].update(
        {
            "mode": "translated",
            "root": "translations/fr",
            "translation_sources": sources,
        }
    )
    (root / "translations/fr").mkdir(parents=True)
    write(
        root / "config/localization/locales.json",
        json.dumps(data, indent=2),
    )


def incomplete_translation(root, data):
    write(root / "book/second.qmd", "Additional canonical source.")
    configure_translation(root, data, ["chapter.qmd"])
    write(root / "translations/fr/chapter.qmd", manuscript_scopes())


def missing_translation(root, data):
    configure_translation(root, data, ["chapter.qmd"])


def valid_translation(root, data):
    configure_translation(root, data, ["chapter.qmd"])
    write(root / "translations/fr/chapter.qmd", "Manuscrit français complet.")


def rendered_cases():
    return (
        (
            "canonical root language",
            lambda root, _: mutate_file(
                root, "book/_build/html/index.html", 'lang="en-US"', 'lang="fr-FR"'
            ),
            "must declare lang and xml:lang as en-US",
        ),
        (
            "rendered RTL direction",
            lambda root, _: mutate_file(root, "book/_build/html/languages.html", ' dir="rtl"', ""),
            "needs dir=rtl",
        ),
        (
            "locale cross-reference",
            lambda root, _: mutate_file(
                root, "book/_build/locale/fr/html/reference.html", "Tableau", "Table"
            ),
            "output is missing marker",
        ),
        (
            "EPUB package language",
            lambda root, _: replace_epub(root, "<dc:language>en-US", "<dc:language>fr-FR"),
            "package metadata must declare en-US",
        ),
        (
            "EPUB RTL direction",
            lambda root, _: replace_epub(root, ' dir="rtl"', ""),
            "needs dir=rtl",
        ),
        (
            "EPUB hyphenation",
            lambda root, _: replace_epub(root, "hyphens: auto", "hyphens: none"),
            "must preserve language-aware hyphens: auto",
        ),
    )


def replace_epub(root, old, new):
    path = root / "book/_build/epub/book.epub"
    with ZipFile(path) as source:
        entries = {name: source.read(name) for name in source.namelist()}
    found = False
    with ZipFile(path, "w", ZIP_DEFLATED) as target:
        for name, content in entries.items():
            text = content.decode("utf-8")
            if old in text and not found:
                text = text.replace(old, new, 1)
                found = True
            target.writestr(name, text)
    if not found:
        raise AssertionError(f"EPUB fixture mutation cannot find {old!r}")


def exercise(checker, cases):
    with tempfile.TemporaryDirectory(prefix="alkahest-localization-") as temporary:
        valid_root = Path(temporary) / "valid"
        create_fixture(valid_root)
        valid = run(checker, valid_root)
        if valid.returncode:
            raise AssertionError(f"valid fixture failed:\n{valid.stderr}{valid.stdout}")

    count = 1
    for name, mutation, expected in cases:
        with tempfile.TemporaryDirectory(prefix="alkahest-localization-") as temporary:
            root = Path(temporary)
            data = create_fixture(root)
            mutation(root, data)
            result = run(checker, root)
            output = result.stderr + result.stdout
            if result.returncode == 0:
                raise AssertionError(f"{name}: invalid fixture passed")
            if expected not in output:
                raise AssertionError(f"{name}: expected {expected!r}; received:\n{output}")
            count += 1
    return count


def exercise_valid_translation():
    with tempfile.TemporaryDirectory(prefix="alkahest-localization-") as temporary:
        root = Path(temporary)
        data = create_fixture(root)
        valid_translation(root, data)
        result = run(SOURCE_CHECKER, root)
        if result.returncode:
            raise AssertionError(f"valid translated locale failed:\n{result.stderr}{result.stdout}")
    return 1


def main():
    source_count = exercise(SOURCE_CHECKER, source_cases())
    source_count += exercise_valid_translation()
    rendered_count = exercise(RENDERED_CHECKER, rendered_cases())
    print(f"ok: localization fixtures ({source_count} source; {rendered_count} rendered)")
    return 0


def test_contract():
    result = main()
    assert result in (None, 0)
