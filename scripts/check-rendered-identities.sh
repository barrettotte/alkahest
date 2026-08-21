#!/usr/bin/env bash
# Verify persistent identities survive rendered editions and the locale variant.
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
lock_path="${repo_root}/book/identity-lock.json"
html_root="${repo_root}/book/_build/html"
locale_root="${repo_root}/book/_build/locale/fr/html"
preview_root="${repo_root}/book/_build/smoke/editions/preview/html"
supplemental_root="${repo_root}/book/_build/smoke/editions/supplemental/html"
private_root="${repo_root}/book/_build/smoke/editions/private/html"
epub_path="${repo_root}/book/_build/epub/Alkahest-Reference-Book.epub"

for required in "${lock_path}" "${html_root}" "${locale_root}" \
  "${preview_root}" "${supplemental_root}" "${private_root}" "${epub_path}"; do
  if [[ ! -e "${required}" ]]; then
    echo "error: rendered-identity input is missing: ${required}" >&2
    exit 1
  fi
done

require_id() {
  local file="$1"
  local id="$2"
  local label="$3"
  if ! grep -Fq "id=\"${id}\"" "${file}"; then
    echo "error: ${label} does not preserve identity '${id}'" >&2
    exit 1
  fi
}

require_literal() {
  local file="$1"
  local literal="$2"
  local label="$3"
  if ! grep -Fq "${literal}" "${file}"; then
    echo "error: ${label} does not preserve '${literal}'" >&2
    exit 1
  fi
}

identity_rows="$(mktemp)"
epub_content="$(mktemp)"
trap 'rm -f "${identity_rows}" "${epub_content}"' EXIT

python3 scripts/identity-lock-rows.py "${lock_path}" >"${identity_rows}"

unzip -p "${epub_path}" 'EPUB/text/*.xhtml' >"${epub_content}"

checked_content=0
checked_assets=0
checked_reuse=0
while IFS='|' read -r namespace kind id source; do
  if [[ "${namespace}" == "asset" ]]; then
    if [[ ! -f "${repo_root}/book/${source}" ]]; then
      echo "error: rendered contract references missing companion identity '${id}'" >&2
      exit 1
    fi
    require_id "${html_root}/companion-materials.html" "${id}" \
      "HTML companion registry"
    require_id "${locale_root}/companion-materials.html" "${id}" \
      "locale companion registry"
    require_id "${supplemental_root}/companion-materials.html" "${id}" \
      "supplemental companion registry"
    require_id "${private_root}/companion-materials.html" "${id}" \
      "private companion registry"
    checked_assets=$((checked_assets + 1))
    continue
  fi

  if [[ "${namespace}" == "reuse" ]]; then
    if [[ ! -f "${repo_root}/book/${source}" ]]; then
      echo "error: rendered contract references missing reusable-content identity '${id}'" >&2
      exit 1
    fi
    for root in "${html_root}" "${locale_root}" "${supplemental_root}" "${private_root}"; do
      require_literal "${root}/content-reuse.html" "data-reuse-id=\"${id}\"" \
        "rendered reusable-content registry"
    done
    require_literal "${epub_content}" "data-reuse-id=\"${id}\"" \
      "EPUB reusable-content registry"
    checked_reuse=$((checked_reuse + 1))
    continue
  fi

  if [[ "${namespace}" == "glossary" ]]; then
    output_id="glossary-${id}"
    require_id "${html_root}/glossary-backmatter.html" "${output_id}" "HTML glossary"
    require_id "${locale_root}/glossary-backmatter.html" "${output_id}" "locale glossary"
    continue
  fi
  if [[ "${namespace}" == "index" ]]; then
    output_id="index-entry-${id}"
    require_id "${html_root}/index-backmatter.html" "${output_id}" "HTML index"
    require_id "${locale_root}/index-backmatter.html" "${output_id}" "locale index"
    continue
  fi

  case "${kind}" in
    chapter|section|figure|table|equation|listing|exercise|solution|learning-objectives|learning-prerequisites|learning-plan|learning-summary|review-question|question-hint|answer-key|reusable-use)
      relative_html="${source%.qmd}.html"
      canonical_file=""
      for root in "${html_root}" "${supplemental_root}" "${private_root}"; do
        if [[ -f "${root}/${relative_html}" ]]; then
          canonical_file="${root}/${relative_html}"
          break
        fi
      done
      if [[ -z "${canonical_file}" ]]; then
        echo "error: no rendered edition contains active identity '${id}' from ${source}" >&2
        exit 1
      fi
      require_id "${canonical_file}" "${id}" "rendered source ${source}"
      checked_content=$((checked_content + 1))

      # A variant only owes identities for sources it includes. Shared sources
      # must never receive a locale- or edition-specific replacement anchor.
      for variant_root in "${locale_root}" "${preview_root}" "${supplemental_root}" "${private_root}"; do
        if [[ -f "${variant_root}/${relative_html}" ]]; then
          require_id "${variant_root}/${relative_html}" "${id}" \
            "rendered variant ${variant_root#${repo_root}/}"
        fi
      done
      ;;
  esac
done <"${identity_rows}"

for id in \
  sec-core-feature-specimen \
  sec-heading-hierarchy \
  fig-half-adder \
  tbl-half-adder \
  eq-ohms-law \
  lst-half-adder \
  exr-divider-budget \
  asset-half-adder-verilog \
  asset-half-adder-data \
  asset-half-adder-schematic \
  asset-half-adder-bom \
  asset-half-adder-project-pack \
  glossary-central-processing-unit \
  index-entry-technical-publishing; do
  require_id "${epub_content}" "${id}" "EPUB"
done

echo "ok: rendered identities (${checked_content} chapter/section/numbered-object/use-site IDs; ${checked_assets} companion-asset IDs; ${checked_reuse} reusable-content IDs; glossary/index IDs; HTML, EPUB, preview, supplemental, private, and locale preservation)"
