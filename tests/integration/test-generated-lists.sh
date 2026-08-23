#!/usr/bin/env bash
# Exercise valid, invalid, and empty generated-list registry contracts.
set -euo pipefail

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
repo_root="$(cd "${script_dir}/../.." && pwd)"
edit="${repo_root}/tests/integration/replace_text.py"
fixture_root="${repo_root}/tests/generated-lists/base"

run_valid() {
  local root="$1"
  ALKAHEST_GENERATED_LISTS_BOOK_ROOT="${root}" \
    PYTHONPATH="${repo_root}/src${PYTHONPATH:+:${PYTHONPATH}}" \
      python3 -m alkahest.checks.generated_lists >/dev/null
}

run_invalid() {
  local root="$1"
  local expected="$2"
  local output
  if output="$(ALKAHEST_GENERATED_LISTS_BOOK_ROOT="${root}" \
      PYTHONPATH="${repo_root}/src${PYTHONPATH:+:${PYTHONPATH}}" \
        python3 -m alkahest.checks.generated_lists 2>&1)"
  then
    echo "error: invalid generated-list fixture unexpectedly passed: ${expected}" >&2
    exit 1
  fi
  if [[ "${output}" != *"${expected}"* ]]; then
    echo "error: invalid generated-list fixture missed diagnostic: ${expected}" >&2
    printf '%s\n' "${output}" >&2
    exit 1
  fi
}

copy_fixture() {
  local destination="$1"
  cp -a "${fixture_root}" "${destination}"
}

valid_root="$(mktemp -d)"
trap 'rm -rf -- "${valid_root}" "${case_root:-}"' EXIT
copy_fixture "${valid_root}/book"
run_valid "${valid_root}/book"

case_root="$(mktemp -d)"
copy_fixture "${case_root}/book"
python3 "${edit}" $'  - figures\n' $'  - figures\n  - figures\n' \
  "${case_root}/book/generated-lists.yml"
run_invalid "${case_root}/book" "duplicate list in order"
rm -rf -- "${case_root}"

case_root="$(mktemp -d)"
copy_fixture "${case_root}/book"
python3 "${edit}" $'  - figures\n' $'  - absent\n' \
  "${case_root}/book/generated-lists.yml"
run_invalid "${case_root}/book" "unknown list in order"
rm -rf -- "${case_root}"

case_root="$(mktemp -d)"
copy_fixture "${case_root}/book"
python3 "${edit}" $'  - algorithms\n' '' "${case_root}/book/generated-lists.yml"
run_invalid "${case_root}/book" "missing from order"
rm -rf -- "${case_root}"

case_root="$(mktemp -d)"
copy_fixture "${case_root}/book"
python3 "${edit}" 'source: terms' 'source: external' \
  "${case_root}/book/generated-lists.yml"
run_invalid "${case_root}/book" "unsupported source"
rm -rf -- "${case_root}"

case_root="$(mktemp -d)"
copy_fixture "${case_root}/book"
python3 "${edit}" 'prefix: tbl' 'prefix: fig' "${case_root}/book/generated-lists.yml"
run_invalid "${case_root}/book" "duplicate cross-reference prefix"
rm -rf -- "${case_root}"

case_root="$(mktemp -d)"
copy_fixture "${case_root}/book"
python3 "${edit}" $'    prefix: fig\n' '' "${case_root}/book/generated-lists.yml"
run_invalid "${case_root}/book" "invalid prefix"
rm -rf -- "${case_root}"

case_root="$(mktemp -d)"
copy_fixture "${case_root}/book"
python3 "${edit}" $'  - id: fig-sample\n    title: Sample figure\n' $'  - id: fig-sample\n    title: Sample figure\n  - id: fig-sample\n    title: Sample figure\n' \
  "${case_root}/book/generated-lists.yml"
run_invalid "${case_root}/book" "duplicate generated-list object"
rm -rf -- "${case_root}"

case_root="$(mktemp -d)"
copy_fixture "${case_root}/book"
python3 "${edit}" $'  - id: fig-sample\n    title: Sample figure\n' '' \
  "${case_root}/book/generated-lists.yml"
run_invalid "${case_root}/book" "missing from generated-lists.yml"
rm -rf -- "${case_root}"

case_root="$(mktemp -d)"
copy_fixture "${case_root}/book"
python3 "${edit}" 'fig-sample' 'fig-absent' "${case_root}/book/generated-lists.yml"
run_invalid "${case_root}/book" "target does not exist"
rm -rf -- "${case_root}"

case_root="$(mktemp -d)"
copy_fixture "${case_root}/book"
python3 "${edit}" 'id: fig-sample' 'id: vid-sample' \
  "${case_root}/book/generated-lists.yml"
run_invalid "${case_root}/book" "no configured cross-reference list owns"
rm -rf -- "${case_root}"

case_root="$(mktemp -d)"
copy_fixture "${case_root}/book"
python3 "${edit}" 'list: symbols' 'list: figures' "${case_root}/book/generated-lists.yml"
run_invalid "${case_root}/book" "unknown terms list"
rm -rf -- "${case_root}"

case_root="$(mktemp -d)"
copy_fixture "${case_root}/book"
python3 "${edit}" 'target: eq-sample' 'target: eq-absent' \
  "${case_root}/book/generated-lists.yml"
run_invalid "${case_root}/book" "targets unknown object"
rm -rf -- "${case_root}"

case_root="$(mktemp -d)"
copy_fixture "${case_root}/book"
python3 "${edit}" 'display: I' "display: '\$I\$'" \
  "${case_root}/book/generated-lists.yml"
run_invalid "${case_root}/book" "without dollar delimiters"
rm -rf -- "${case_root}"

case_root="$(mktemp -d)"
copy_fixture "${case_root}/book"
python3 "${edit}" $'    alt: capital I, electric current\n' '' \
  "${case_root}/book/generated-lists.yml"
run_invalid "${case_root}/book" "term current has no alt"
rm -rf -- "${case_root}"

case_root="$(mktemp -d)"
copy_fixture "${case_root}/book"
python3 "${edit}" 'lang: en-US' 'lang: english_US' \
  "${case_root}/book/generated-lists.yml"
run_invalid "${case_root}/book" "BCP 47"
rm -rf -- "${case_root}"

case_root="$(mktemp -d)"
copy_fixture "${case_root}/book"
python3 "${edit}" 'alkahest-generated-lists-placeholder' 'not-a-placeholder' \
  "${case_root}/book/generated-lists.qmd"
run_invalid "${case_root}/book" "placeholder; found 0"
rm -rf -- "${case_root}"

case_root="$(mktemp -d)"
copy_fixture "${case_root}/book"
cp "${case_root}/book/generated-lists.qmd" "${case_root}/book/second-lists.qmd"
run_invalid "${case_root}/book" "placeholder; found 2"
rm -rf -- "${case_root}"

case_root="$(mktemp -d)"
copy_fixture "${case_root}/book"
printf '\\listoffigures\n' >>"${case_root}/book/chapter.qmd"
run_invalid "${case_root}/book" "backend-specific list command"
rm -rf -- "${case_root}"

case_root="$(mktemp -d)"
copy_fixture "${case_root}/book"
python3 "${edit}" $'  algorithms:\n    title: List of algorithms\n    source: crossref\n    prefix: alg\n' $'  algorithms:\n    title: List of algorithms\n    source: glossary-acronyms\n' \
  "${case_root}/book/generated-lists.yml"
run_invalid "${case_root}/book" "at most one glossary-acronyms list"

echo "ok: generated-list fixtures (seven populated kinds plus empty omission; 19 invalid contracts rejected)"
