#!/usr/bin/env bash
# Exercise valid and deliberately invalid semantic-note source contracts.
set -euo pipefail

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
repo_root="$(cd "${script_dir}/../.." && pwd)"
edit="${repo_root}/tests/integration/replace-text.py"
base_fixture="${repo_root}/tests/notes/base"
test_root="$(mktemp -d /tmp/alkahest-note-tests.XXXXXX)"

cleanup() {
  rm -rf -- "${test_root}"
}
trap cleanup EXIT

prepare_case() {
  cp -R "${base_fixture}" "$1"
}

run_validator() {
  ALKAHEST_NOTES_BOOK_ROOT="$1" \
    PYTHONPATH="${repo_root}/src${PYTHONPATH:+:${PYTHONPATH}}" \
    python3 -m alkahest.checks.notes
}

expect_failure() {
  local name="$1"
  local expected="$2"
  local mutation="$3"
  local case_root="${test_root}/${name}"
  local output
  local status

  prepare_case "${case_root}"
  "${mutation}" "${case_root}"
  set +e
  output="$(run_validator "${case_root}" 2>&1)"
  status=$?
  set -e
  if [[ "${status}" -eq 0 ]]; then
    echo "error: notes fixture ${name} unexpectedly passed" >&2
    return 1
  fi
  if [[ "${output}" != *"${expected}"* ]]; then
    echo "error: notes fixture ${name} missed expected diagnostic: ${expected}" >&2
    echo "${output}" >&2
    return 1
  fi
}

missing_definition() {
  python3 "${edit}" --regex '\n\[\^source-order\]:.*?\n' '\n' "$1/components.qmd"
}

duplicate_definition() {
  python3 "${edit}" --regex '(\[\^page-geometry\]:[^\n]+\n)' '\1\1' "$1/reference.qmd"
}

unregistered_definition() {
  python3 "${edit}" --all 'source-order' 'extra-note' "$1/components.qmd"
}

unknown_reference() {
  python3 "${edit}" 'First reference.[^page-geometry]' 'First reference.[^missing]' \
    "$1/reference.qmd"
}

forbidden_repeat() {
  python3 "${edit}" 'repeat: reuse' 'repeat: once' "$1/notes.yml"
}

reference_count_drift() {
  python3 "${edit}" 'references: 2' 'references: 3' "$1/notes.yml"
}

wrong_source() {
  python3 "${edit}" 'source: reference.qmd' 'source: components.qmd' "$1/notes.yml"
}

wrong_marker() {
  python3 "${edit}" 'note-page-geometry' 'note-wrong' "$1/reference.qmd"
}

inline_note() {
  python3 "${edit}" 'First reference' 'Inline^[unregistered note]. First reference' \
    "$1/reference.qmd"
}

missing_placeholder() {
  python3 "${edit}" $'::: {.alkahest-book-notes-placeholder}\n:::\n' '' \
    "$1/glossary-backmatter.qmd"
}

duplicate_placeholder() {
  python3 "${edit}" $'::: {.alkahest-book-notes-placeholder}\n:::\n' $'::: {.alkahest-book-notes-placeholder}\n:::\n\n::: {.alkahest-book-notes-placeholder}\n:::\n' \
    "$1/glossary-backmatter.qmd"
}

missing_order_entry() {
  python3 "${edit}" $'  - source-order\n' '' "$1/notes.yml"
}

valid_root="${test_root}/valid"
prepare_case "${valid_root}"
run_validator "${valid_root}" >/dev/null
expect_failure missing-definition "note reference has no registered definition: source-order" missing_definition
expect_failure duplicate-definition "duplicate note definition: page-geometry" duplicate_definition
expect_failure unregistered-definition "unregistered note definition: extra-note" unregistered_definition
expect_failure unknown-reference "note reference has no registered definition: missing" unknown_reference
expect_failure forbidden-repeat "uses repeat=once with more than one reference" forbidden_repeat
expect_failure reference-count "registry expects 3" reference_count_drift
expect_failure wrong-source "expected components.qmd" wrong_source
expect_failure wrong-marker "note marker must be #note-page-geometry" wrong_marker
expect_failure inline-note "uses an inline note" inline_note
expect_failure missing-placeholder "expected exactly one book-notes placeholder; found 0" missing_placeholder
expect_failure duplicate-placeholder "expected exactly one book-notes placeholder; found 2" duplicate_placeholder
expect_failure missing-order "order and mapping contain different entry counts" missing_order_entry

echo "ok: semantic-note fixtures (valid contract; 12 invalid contracts rejected)"
