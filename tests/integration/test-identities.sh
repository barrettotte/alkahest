#!/usr/bin/env bash
# Exercise valid, invalid, translated, and editioned identity inventories.
set -euo pipefail

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
repo_root="$(cd "${script_dir}/../.." && pwd)"
edit="${repo_root}/tests/integration/replace_text.py"
fixture_root="${repo_root}/tests/identities/base"
case_parent="$(mktemp -d)"
trap 'rm -rf "${case_parent}"' EXIT

new_case() {
  local name="$1"
  local root="${case_parent}/${name}"
  mkdir -p "${root}"
  cp -R "${fixture_root}/book" "${root}/book"
  printf '%s\n' "${root}/book"
}

run_check() {
  ALKAHEST_IDENTITY_BOOK_ROOT="$1" \
    PYTHONPATH="${repo_root}/src${PYTHONPATH:+:${PYTHONPATH}}" \
    python3 -m alkahest check --source identities
}

expect_failure() {
  local root="$1"
  local expected="$2"
  local output
  if output="$(run_check "${root}" 2>&1)"; then
    echo "error: identity fixture unexpectedly passed: ${root}" >&2
    exit 1
  fi
  if [[ "${output}" != *"${expected}"* ]]; then
    echo "error: identity fixture missed expected diagnostic: ${expected}" >&2
    echo "${output}" >&2
    exit 1
  fi
}

run_check "${fixture_root}/book" >/dev/null

case_root="$(new_case implicit-heading)"
python3 "${edit}" ' {#sec-stable-section}' '' "${case_root}/en/chapter.qmd"
expect_failure "${case_root}" "every heading must have exactly one explicit persistent ID"

case_root="$(new_case setext-heading)"
python3 "${edit}" '## Stable section {#sec-stable-section}' $'Stable section\n--------------' \
  "${case_root}/en/chapter.qmd"
expect_failure "${case_root}" "Setext headings cannot carry the required explicit ID"

case_root="$(new_case duplicate-content)"
python3 "${edit}" 'sec-stable-section' 'sec-identity-fixture' "${case_root}/en/chapter.qmd"
expect_failure "${case_root}" "duplicate content identity 'sec-identity-fixture'"

case_root="$(new_case semantic-title-id)"
python3 "${edit}" '## Fixture exercise' '## Fixture exercise {#sec-redundant-title}' \
  "${case_root}/en/chapter.qmd"
expect_failure "${case_root}" "semantic block title must use its enclosing 'exr-identity-sample' identity"

case_root="$(new_case translation-drift)"
python3 "${edit}" 'sec-stable-section' 'sec-section-traduite' "${case_root}/fr/chapitre.qmd"
expect_failure "${case_root}" "translation 'fr-FR' is missing content identity 'sec-stable-section'"

case_root="$(new_case translated-glossary-drift)"
python3 "${edit}" 'stable-term:' 'terme-stable:' "${case_root}/fr/glossary.yml"
expect_failure "${case_root}" "translation 'fr-FR' is missing glossary identity 'stable-term'"

case_root="$(new_case coordinated-rename)"
python3 "${edit}" --all 'sec-stable-section' 'sec-renamed-section' \
  "${case_root}/en/chapter.qmd" "${case_root}/fr/chapitre.qmd"
run_check "${case_root}" >/dev/null

case_root="$(new_case missing-companion)"
mv "${case_root}/companion/sample.txt" "${case_root}/companion/not-sample.txt"
expect_failure "${case_root}" "references missing file 'companion/sample.txt'"

case_root="$(new_case missing-reusable-content)"
mv "${case_root}/reuse/fixture-notice.md" "${case_root}/reuse/not-fixture.md"
expect_failure "${case_root}" "references missing fragment 'reuse/fixture-notice.md'"

case_root="$(new_case edition-drift)"
python3 "${edit}" 'chapter.qmd' 'missing.qmd' "${case_root}/editions.json"
expect_failure "${case_root}" "must resolve to one persistently identified chapter"

echo "ok: identity fixtures (explicit IDs, uniqueness, coordinated renames, translations, editions, companion assets, and reusable content)"
