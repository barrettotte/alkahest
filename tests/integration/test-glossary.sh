#!/usr/bin/env bash
# Exercise valid and deliberately invalid glossary registries and references.
set -euo pipefail

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
repo_root="$(cd "${script_dir}/../.." && pwd)"
edit="${repo_root}/tests/integration/replace-text.py"
base_fixture="${repo_root}/tests/glossary/base"
test_root="$(mktemp -d /tmp/alkahest-glossary-tests.XXXXXX)"

cleanup() {
  rm -rf -- "${test_root}"
}
trap cleanup EXIT

run_validator() {
  ALKAHEST_GLOSSARY_BOOK_ROOT="$1" \
    PYTHONPATH="${repo_root}/src${PYTHONPATH:+:${PYTHONPATH}}" \
    python3 -m alkahest.checks.glossary
}

expect_failure() {
  local name="$1"
  local expected="$2"
  local mutation="$3"
  local case_root="${test_root}/${name}"
  local output
  local status

  cp -R "${base_fixture}" "${case_root}"
  "${mutation}" "${case_root}"
  set +e
  output="$(run_validator "${case_root}" 2>&1)"
  status=$?
  set -e
  if [[ "${status}" -eq 0 ]]; then
    echo "error: glossary fixture ${name} unexpectedly passed" >&2
    return 1
  fi
  if [[ "${output}" != *"${expected}"* ]]; then
    echo "error: glossary fixture ${name} missed expected diagnostic: ${expected}" >&2
    echo "${output}" >&2
    return 1
  fi
}

duplicate_display() {
  python3 "${edit}" 'term: matrix' 'term: central processing unit' "$1/glossary.yml"
}

duplicate_alias() {
  python3 "${edit}" '      - array' '      - cpu' "$1/glossary.yml"
}

undefined_term() {
  python3 "${edit}" 'alk-term matrix' 'alk-term missing-term' "$1/chapter-two.qmd"
}

unused_entry() {
  python3 "${edit}" --regex ' and\n+an unlinked \{\{< alk-term matrix form=first link=false >\}\} reference' ' reference' \
    "$1/chapter-two.qmd"
}

duplicate_first_use() {
  python3 "${edit}" 'examples begin here.' $'examples begin here.\n\n{{< alk-term cpu form=first >}} again.' \
    "$1/chapter-one.qmd"
}

missing_first_use() {
  python3 "${edit}" 'form=first case=sentence' 'form=term case=sentence' \
    "$1/chapter-one.qmd"
}

invalid_case() {
  python3 "${edit}" 'case=sentence' 'case=uppercase' "$1/chapter-one.qmd"
}

invalid_link() {
  python3 "${edit}" 'link=false' 'link=maybe' "$1/chapter-two.qmd"
}

unavailable_form() {
  python3 "${edit}" 'form=first link=false' 'form=acronym link=false' \
    "$1/chapter-two.qmd"
}

invalid_language() {
  python3 "${edit}" 'lang: en-US' 'lang: en_US' "$1/glossary.yml"
}

missing_placeholder() {
  python3 "${edit}" $'::: {.alkahest-glossary-placeholder}\n:::\n' '' \
    "$1/glossary-backmatter.qmd"
}

run_validator "${base_fixture}" >/dev/null
expect_failure duplicate-display "duplicate glossary display term" duplicate_display
expect_failure duplicate-alias "duplicate glossary name or alias" duplicate_alias
expect_failure undefined-term "unknown glossary name or alias" undefined_term
expect_failure unused-entry "is unused" unused_entry
expect_failure duplicate-first-use "duplicate explicit first use" duplicate_first_use
expect_failure missing-first-use "has no explicit first-use marker" missing_first_use
expect_failure invalid-case "unknown alk-term case" invalid_case
expect_failure invalid-link "alk-term link must be true or false" invalid_link
expect_failure unavailable-form "form acronym is unavailable" unavailable_form
expect_failure invalid-language "language must be a BCP 47-style tag" invalid_language
expect_failure missing-placeholder "expected exactly one generated-glossary placeholder" missing_placeholder

echo "ok: glossary fixtures (cross-chapter valid; 11 invalid contracts rejected)"
