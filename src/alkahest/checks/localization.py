"""Validate locale profiles, language spans, scripts, and font policy."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path, PurePosixPath

ROOT = Path(__file__).resolve().parents[3]
DEFAULT_POLICY = ROOT / "config" / "localization" / "locales.json"
BCP47 = re.compile(r"[A-Za-z]{2,3}(?:-[A-Za-z0-9]{2,8})*")
LANGUAGE_SPAN = re.compile(r"\[(?P<text>.*?)\]\{(?P<attrs>[^{}]*\blang=[^{}]+)\}", re.DOTALL)
LANG_ATTRIBUTE = re.compile(r"\blang=(?:\"(?P<quoted>[^\"]+)\"|(?P<plain>[^\s}]+))")
DIR_ATTRIBUTE = re.compile(r"\bdir=(?:\"(?P<quoted>[^\"]+)\"|(?P<plain>[^\s}]+))")
SCRIPT_RANGES = {
    "Greek": ((0x0370, 0x03FF), (0x1F00, 0x1FFF)),
    "Cyrillic": ((0x0400, 0x052F),),
    "Hebrew": ((0x0590, 0x05FF),),
    "Arabic": ((0x0600, 0x06FF), (0x0750, 0x077F), (0x08A0, 0x08FF)),
    "CJK": (
        (0x3040, 0x30FF),
        (0x3400, 0x4DBF),
        (0x4E00, 0x9FFF),
        (0xAC00, 0xD7AF),
    ),
    "Indic": ((0x0900, 0x0D7F),),
}


class LocalizationError(RuntimeError):
    """Report an invalid localization policy or source contract."""


def fail(message):
    raise LocalizationError(message)


def arguments():
    parser = argparse.ArgumentParser(
        description="Validate localization policy and manuscript language scopes."
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


def indexed(items, label):
    if not isinstance(items, list) or not items:
        fail(f"{label} must be a nonempty array")
    result = {}
    for item in items:
        if not isinstance(item, dict) or not isinstance(item.get("tag"), str):
            fail(f"{label} entries need a language tag")
        tag = item["tag"]
        if not BCP47.fullmatch(tag):
            fail(f"{label} contains invalid language tag '{tag}'")
        if tag in result:
            fail(f"{label} contains duplicate language tag '{tag}'")
        result[tag] = item
    return result


def script_for(character):
    codepoint = ord(character)
    for script, ranges in SCRIPT_RANGES.items():
        if any(start <= codepoint <= end for start, end in ranges):
            return script
    return None


def attribute(match, name):
    value = match.group("quoted") or match.group("plain")
    if not value:
        fail(f"empty {name} attribute")
    return value


def validate_language_spans(root, policy, languages, document_languages):
    source_contract = policy["source_contract"]
    pattern = source_contract.get("manuscript_glob")
    if not isinstance(pattern, str) or not pattern:
        fail("source contract needs manuscript_glob")
    canonical = policy["canonical_locale"]
    paths = {
        path: canonical
        for path in root.glob(pattern)
        if "_build" not in path.parts and ".quarto" not in path.parts
    }
    paths.update(document_languages)
    if not paths:
        fail("localization policy found no manuscript sources")

    observed = set()
    script_counts: dict[str, int] = {}
    unsupported = set(policy["unsupported_scripts"])
    for path, document_language in sorted(paths.items()):
        content = path.read_text(encoding="utf-8")
        scopes = []
        for span in LANGUAGE_SPAN.finditer(content):
            language_match = LANG_ATTRIBUTE.search(span.group("attrs"))
            if not language_match:
                continue
            tag = attribute(language_match, "lang")
            if tag not in languages:
                fail(f"{path.relative_to(root)} uses undeclared language tag '{tag}'")
            direction_match = DIR_ATTRIBUTE.search(span.group("attrs"))
            direction = attribute(direction_match, "dir") if direction_match else "ltr"
            expected_direction = languages[tag]["direction"]
            if direction != expected_direction:
                fail(
                    f"{path.relative_to(root)} language {tag} needs "
                    f"dir={expected_direction}; found {direction}"
                )
            observed.add(tag)
            scopes.append((span.start(), span.end(), tag))

        for offset, character in enumerate(content):
            script = script_for(character)
            if script is None:
                continue
            if script in unsupported:
                fail(
                    f"{path.relative_to(root)} uses unsupported {script} script "
                    f"at U+{ord(character):04X}"
                )
            containing = [tag for start, end, tag in scopes if start <= offset < end]
            if not containing:
                if script in languages[document_language]["scripts"]:
                    script_counts[script] = script_counts.get(script, 0) + 1
                    continue
                fail(
                    f"{path.relative_to(root)} has unscoped {script} character "
                    f"U+{ord(character):04X}"
                )
            tag = containing[-1]
            if script not in languages[tag]["scripts"]:
                fail(
                    f"{path.relative_to(root)} scopes {script} text as {tag}, "
                    f"which declares {languages[tag]['scripts']}"
                )
            script_counts[script] = script_counts.get(script, 0) + 1

    missing = sorted(set(languages) - observed)
    if missing:
        fail(f"inline language fixtures are missing: {', '.join(missing)}")
    return len(paths), observed, script_counts


def validate(policy, root):
    if not isinstance(policy, dict) or policy.get("schema_version") != 1:
        fail("localization policy must use schema_version 1")
    locales = indexed(policy.get("locales"), "locales")
    languages = indexed(policy.get("inline_languages"), "inline_languages")
    canonical = policy.get("canonical_locale")
    if canonical not in locales or canonical not in languages:
        fail("canonical_locale must exist in locales and inline_languages")
    if sum(locale.get("mode") == "canonical" for locale in locales.values()) != 1:
        fail("localization policy must declare exactly one canonical locale")
    if locales[canonical].get("mode") != "canonical":
        fail("canonical_locale must identify the canonical locale entry")
    font_family = policy.get("font_family")
    if not isinstance(font_family, str) or not font_family.strip():
        fail("localization policy needs a font_family")
    unsupported_scripts = policy.get("unsupported_scripts")
    if not isinstance(unsupported_scripts, list):
        fail("localization policy needs unsupported_scripts")
    unknown_unsupported = set(unsupported_scripts) - set(SCRIPT_RANGES)
    if unknown_unsupported:
        fail(f"unsupported_scripts contains unknown scripts: {sorted(unknown_unsupported)}")

    canonical_root = repo_path(root, locales[canonical].get("root"), "canonical locale root")
    canonical_sources = {
        str(path.relative_to(canonical_root).as_posix())
        for path in canonical_root.rglob("*.qmd")
        if "_build" not in path.parts and ".quarto" not in path.parts
    }
    if not canonical_sources:
        fail("canonical locale root contains no manuscript sources")

    allowed_modes = {"canonical", "shared-source-smoke", "translated"}
    translated_documents = {}
    for tag, locale in locales.items():
        if locale.get("mode") not in allowed_modes:
            fail(f"locale {tag} has unsupported mode '{locale.get('mode')}'")
        if locale.get("direction") not in {"ltr", "rtl"}:
            fail(f"locale {tag} needs ltr or rtl direction")
        if locale["direction"] != languages.get(tag, {}).get("direction"):
            fail(f"locale {tag} direction disagrees with inline language policy")
        profile = repo_path(root, locale.get("profile"), f"locale {tag} profile")
        if not profile.is_file():
            fail(f"locale {tag} profile does not exist: {locale.get('profile')}")
        profile_text = profile.read_text(encoding="utf-8")
        language_profile_value = locale.get("language_profile", locale.get("profile"))
        language_profile = repo_path(root, language_profile_value, f"locale {tag} language profile")
        if not language_profile.is_file():
            fail(f"locale {tag} language profile does not exist: {language_profile_value}")
        language_profile_text = language_profile.read_text(encoding="utf-8")
        combined_profile_text = profile_text
        if language_profile != profile:
            combined_profile_text += "\n" + language_profile_text
        shared_defaults = profile.parent / "alkahest-defaults.yml"
        if shared_defaults.is_file():
            combined_profile_text += "\n" + shared_defaults.read_text(encoding="utf-8")
        for marker in locale.get("required_profile_markers", []):
            if marker not in combined_profile_text:
                fail(f"locale {tag} profile is missing marker: {marker}")
        declared = re.findall(r"^lang:\s*([^\s#]+)", combined_profile_text, re.MULTILINE)
        if declared != [tag]:
            fail(f"locale {tag} profile must declare lang: {tag} exactly once")
        locale_root = repo_path(root, locale.get("root"), f"locale {tag} root")
        if not locale_root.is_dir():
            fail(f"locale {tag} root does not exist: {locale.get('root')}")
        if locale["mode"] == "shared-source-smoke" and locale["root"] != locales[canonical]["root"]:
            fail(f"shared-source locale {tag} must use the canonical source root")
        if locale["mode"] == "translated":
            try:
                locale_root.relative_to(canonical_root)
            except ValueError:
                pass
            else:
                fail(f"translated locale {tag} root must be outside the canonical root")
            manifest = locale.get("translation_sources")
            if not isinstance(manifest, list) or not manifest:
                fail(f"translated locale {tag} needs a translation_sources manifest")
            if len(manifest) != len(set(manifest)):
                fail(f"translated locale {tag} has duplicate translation sources")
            missing_manifest = sorted(canonical_sources - set(manifest))
            if missing_manifest:
                fail(
                    f"translated locale {tag} manifest is incomplete; missing: "
                    f"{', '.join(missing_manifest)}"
                )
            for source in manifest:
                translated = repo_path(locale_root, source, f"locale {tag} translation")
                if not translated.is_file():
                    fail(f"translated locale {tag} is missing source: {source}")
                translated_documents[translated] = tag

    packages = set()
    supported_scripts = set()
    for tag, language in languages.items():
        if language.get("direction") not in {"ltr", "rtl"}:
            fail(f"inline language {tag} needs ltr or rtl direction")
        scripts = language.get("scripts")
        if not isinstance(scripts, list) or not scripts:
            fail(f"inline language {tag} needs at least one script")
        unknown = set(scripts) - set(SCRIPT_RANGES) - {"Latin"}
        if unknown:
            fail(f"inline language {tag} declares unknown scripts: {sorted(unknown)}")
        supported_scripts.update(scripts)
        declared_packages = language.get("toolchain_packages")
        if not isinstance(declared_packages, list) or not declared_packages:
            fail(f"inline language {tag} needs toolchain_packages")
        packages.update(declared_packages)
    if supported_scripts & set(unsupported_scripts):
        fail("supported and unsupported script policies overlap")

    contract = policy.get("source_contract")
    if not isinstance(contract, dict):
        fail("localization policy needs source_contract")
    containerfile = repo_path(root, contract.get("containerfile"), "containerfile")
    report = repo_path(root, contract.get("toolchain_report"), "toolchain report")
    toolchain_text = containerfile.read_text(encoding="utf-8") + report.read_text(encoding="utf-8")
    for package in sorted(packages):
        if package not in toolchain_text:
            fail(f"localization toolchain does not lock package {package}")

    typst = repo_path(root, contract.get("typst_template"), "Typst template")
    typst_text = typst.read_text(encoding="utf-8")
    if "fallback: false" not in typst_text:
        fail("Typst localization policy must disable automatic font fallback")
    canonical_profile = repo_path(root, locales[canonical]["profile"], "canonical profile")
    canonical_config = canonical_profile.read_text(encoding="utf-8")
    shared_defaults = canonical_profile.parent / "alkahest-defaults.yml"
    if shared_defaults.is_file():
        canonical_config += "\n" + shared_defaults.read_text(encoding="utf-8")
    if "babel-otherlangs: []" not in canonical_config:
        fail("canonical profile must enable on-demand Babel languages")
    for theme_key in ("html_theme", "epub_theme"):
        theme = repo_path(root, contract.get(theme_key), theme_key)
        theme_text = theme.read_text(encoding="utf-8")
        if "hyphens: auto" not in theme_text:
            fail(f"{theme_key} must enable language-aware automatic hyphenation")

    path_count, observed, script_counts = validate_language_spans(
        root, policy, languages, translated_documents
    )
    return locales, path_count, observed, script_counts, packages


def main():
    options = arguments()
    root = options.repo_root.resolve()
    policy_path = options.policy
    if not policy_path.is_absolute():
        policy_path = root / policy_path
    try:
        policy = json.loads(policy_path.read_text(encoding="utf-8"))
        locales, paths, languages, scripts, packages = validate(policy, root)
    except (OSError, json.JSONDecodeError, LocalizationError) as error:
        print(f"error: {error}", file=sys.stderr)
        return 1
    script_summary = ", ".join(f"{name}={count}" for name, count in sorted(scripts.items()))
    print(
        f"ok: localization source policy ({len(locales)} locales; {len(languages)} "
        f"inline languages; {paths} manuscript sources; {len(packages)} locked "
        f"language packages; scripts {script_summary})"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
