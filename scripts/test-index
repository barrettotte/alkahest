#!/usr/bin/env bash
# Exercise valid and invalid subject/person index registry and marker contracts.
set -euo pipefail

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
repo_root="$(cd "${script_dir}/.." && pwd)"
edit="${script_dir}/replace-text.py"
fixture_root="${repo_root}/tests/index/base"

run_valid() {
  local root="$1"
  ALKAHEST_INDEX_BOOK_ROOT="${root}" python3 "${script_dir}/check-index.py" >/dev/null
}

run_invalid() {
  local root="$1"
  local expected="$2"
  local output
  if output="$(ALKAHEST_INDEX_BOOK_ROOT="${root}" \
      python3 "${script_dir}/check-index.py" 2>&1)"
  then
    echo "error: invalid index fixture unexpectedly passed: ${expected}" >&2
    exit 1
  fi
  if [[ "${output}" != *"${expected}"* ]]; then
    echo "error: invalid index fixture missed diagnostic: ${expected}" >&2
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
python3 "${edit}" '      - system-design' '      - architecture' \
  "${case_root}/book/index.yml"
run_invalid "${case_root}/book" "duplicate index name or alias"
rm -rf -- "${case_root}"

case_root="$(mktemp -d)"
copy_fixture "${case_root}/book"
python3 "${edit}" 'alk-index system-design' 'alk-index missing' \
  "${case_root}/book/chapter.qmd"
run_invalid "${case_root}/book" "unknown index name or alias missing"
rm -rf -- "${case_root}"

case_root="$(mktemp -d)"
copy_fixture "${case_root}/book"
python3 "${edit}" --regex '^.*alk-index system-design.*\n' '' \
  "${case_root}/book/chapter.qmd"
run_invalid "${case_root}/book" "declared index point has no matching marker"
rm -rf -- "${case_root}"

case_root="$(mktemp -d)"
copy_fixture "${case_root}/book"
python3 "${edit}" '{{< alk-index system-design id=overview >}}' '{{< alk-index system-design id=overview >}}{{< alk-index system-design id=overview >}}' \
  "${case_root}/book/chapter.qmd"
run_invalid "${case_root}/book" "duplicate index point marker"
rm -rf -- "${case_root}"

case_root="$(mktemp -d)"
copy_fixture "${case_root}/book"
python3 "${edit}" --regex '^.*range=end.*\n' '' "${case_root}/book/chapter.qmd"
run_invalid "${case_root}/book" "needs exactly one start and one end"
rm -rf -- "${case_root}"

case_root="$(mktemp -d)"
copy_fixture "${case_root}/book"
python3 "${edit}" 'id=tour range=start' 'id=extra range=start' "${case_root}/book/chapter.qmd"
python3 "${edit}" 'id=tour range=end' 'id=extra range=end' \
  "${case_root}/book/chapter.qmd"
run_invalid "${case_root}/book" "declared index range needs exactly one start and one end"
rm -rf -- "${case_root}"

case_root="$(mktemp -d)"
copy_fixture "${case_root}/book"
python3 "${edit}" 'parent: systems' 'parent: absent' "${case_root}/book/index.yml"
run_invalid "${case_root}/book" "invalid parent"
rm -rf -- "${case_root}"

case_root="$(mktemp -d)"
copy_fixture "${case_root}/book"
python3 "${edit}" $'kind: subject\n    aliases:' $'kind: subject\n    parent: architecture\n    aliases:' \
  "${case_root}/book/index.yml"
run_invalid "${case_root}/book" "index parent cycle"
rm -rf -- "${case_root}"

case_root="$(mktemp -d)"
copy_fixture "${case_root}/book"
python3 "${edit}" $'hopper-grace:\n    term: Hopper, Grace\n    kind: person' $'hopper-grace:\n    term: Hopper, Grace\n    kind: person\n    parent: systems' \
  "${case_root}/book/index.yml"
run_invalid "${case_root}/book" "different kinds"
rm -rf -- "${case_root}"

case_root="$(mktemp -d)"
copy_fixture "${case_root}/book"
python3 "${edit}" 'see: architecture' 'see: absent' "${case_root}/book/index.yml"
run_invalid "${case_root}/book" "invalid see target"
rm -rf -- "${case_root}"

case_root="$(mktemp -d)"
copy_fixture "${case_root}/book"
python3 "${edit}" 'see: architecture' $'see: architecture\n    locations:\n      - chapter.qmd#redirect' \
  "${case_root}/book/index.yml"
run_invalid "${case_root}/book" "cannot have locators"
rm -rf -- "${case_root}"

case_root="$(mktemp -d)"
copy_fixture "${case_root}/book"
python3 "${edit}" 'lang: en-US' 'lang: english_US' "${case_root}/book/index.yml"
run_invalid "${case_root}/book" "BCP 47"
rm -rf -- "${case_root}"

case_root="$(mktemp -d)"
copy_fixture "${case_root}/book"
python3 "${edit}" 'alkahest-index-placeholder' 'not-an-index-placeholder' \
  "${case_root}/book/index-backmatter.qmd"
run_invalid "${case_root}/book" "expected exactly one index placeholder; found 0"
rm -rf -- "${case_root}"

case_root="$(mktemp -d)"
copy_fixture "${case_root}/book"
cp "${case_root}/book/index-backmatter.qmd" "${case_root}/book/second-index.qmd"
run_invalid "${case_root}/book" "expected exactly one index placeholder; found 2"
rm -rf -- "${case_root}"

case_root="$(mktemp -d)"
copy_fixture "${case_root}/book"
printf '\\index{systems}\n' >>"${case_root}/book/chapter.qmd"
run_invalid "${case_root}/book" "backend-specific index command"

echo "ok: index fixtures (valid hierarchy; 15 invalid contracts rejected)"
