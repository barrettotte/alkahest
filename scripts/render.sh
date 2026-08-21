#!/usr/bin/env bash
# Render selected publication formats through the locked toolchain.
set -euo pipefail

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
repo_root="$(cd "${script_dir}/.." && pwd)"
target="${1:-all}"

render_edition_profile() {
  local edition="$1"
  local profile="$2"
  local output_dir="$3"
  local -a stage_arguments=("${edition}")
  local stage_root="${repo_root}/book/_build/staging/editions/${edition}"
  local staged_output="${stage_root}/_rendered"
  local canonical_output="${repo_root}/book/${output_dir}"

  # Only HTML needs Quarto to discover raw poster/track resources. Other
  # formats keep the media directory linked and avoid copying large web assets.
  case ",${profile}," in
    *,html,*) stage_arguments+=(--html-resources) ;;
  esac
  python3 "${script_dir}/stage-edition.py" "${stage_arguments[@]}" >/dev/null
  "${script_dir}/quarto.sh" render "book/_build/staging/editions/${edition}" \
    --profile "edition-${edition},${profile}" \
    --output-dir _rendered

  # Preserve requested PDF backend sources alongside the completed artifact;
  # staging would otherwise strand keep-typ/keep-tex intermediates.
  if [[ -f "${stage_root}/index.typ" ]]; then
    cp "${stage_root}/index.typ" \
      "${staged_output}/Alkahest-Reference-Book.typ"
  fi
  if [[ -f "${stage_root}/index.tex" ]]; then
    cp "${stage_root}/index.tex" \
      "${staged_output}/Alkahest-Reference-Book.tex"
  fi

  # Quarto warns when a project writes outside its root. Promote only a fully
  # successful staged render into the canonical artifact tree.
  case "${canonical_output}" in
    "${repo_root}/book/_build/"*) ;;
    *)
      echo "error: unsafe canonical render path: ${canonical_output}" >&2
      return 1
      ;;
  esac
  test -e "${staged_output}"
  mkdir -p "$(dirname "${canonical_output}")"
  rm -rf -- "${canonical_output}"
  mv -- "${staged_output}" "${canonical_output}"
  if [[ -d "${canonical_output}/theme/fonts" \
    && -d "${repo_root}/book/theme/fonts/licenses" ]]
  then
    mkdir -p "${canonical_output}/theme/fonts/licenses"
    cp -a "${repo_root}/book/theme/fonts/licenses/." \
      "${canonical_output}/theme/fonts/licenses/"
  fi
}

render_profile() {
  case "$1" in
    html)
      render_edition_profile web html _build/html
      ;;
    epub)
      render_edition_profile epub epub _build/epub
      python3 "${script_dir}/finalize-epub.py"
      ;;
    typst)
      render_edition_profile print typst _build/print/7x10/typst
      ;;
    latex)
      render_edition_profile print latex _build/print/7x10/latex
      ;;
    typst-6x9)
      render_edition_profile print typst-6x9 _build/print/6x9/typst
      ;;
    latex-6x9)
      render_edition_profile print latex-6x9 _build/print/6x9/latex
      ;;
    typst-review)
      render_edition_profile print typst-review _build/review/letter/typst
      ;;
    latex-review)
      render_edition_profile print latex-review _build/review/letter/latex
      ;;
  esac
}

# Profiles share source-directory intermediates, so render them sequentially.
# Parallel profile builds can overwrite each other's generated Typst/TeX files.
render_pdf_profiles() {
  render_profile typst
  render_profile latex
  render_profile typst-6x9
  render_profile latex-6x9
  render_profile typst-review
  render_profile latex-review
}

render_locale_smoke() {
  render_edition_profile web locale-fr,html _build/locale/fr/html
}

render_citation_smoke() {
  render_edition_profile web citation-numeric,html \
    _build/smoke/citations/numeric/html
  render_edition_profile print citation-numeric,typst \
    _build/smoke/citations/numeric/typst
}

render_edition_smoke() {
  render_edition_profile abridged html _build/smoke/editions/abridged/html
  render_edition_profile preview html _build/smoke/editions/preview/html
  render_edition_profile public html _build/smoke/editions/public/html
  render_edition_profile private html _build/smoke/editions/private/html
  render_edition_profile supplemental html \
    _build/smoke/editions/supplemental/html
}

render_notes_smoke() {
  render_edition_profile web html,notes-chapter \
    _build/smoke/notes/chapter/html
  render_edition_profile web html,notes-book \
    _build/smoke/notes/book/html
  render_edition_profile web html,notes-sidenote \
    _build/smoke/notes/sidenote/html
  # Use one complete Typst profile: Quarto treats format declarations from
  # composed profiles as separate render targets rather than map overrides.
  render_edition_profile print notes-sidenote-typst \
    _build/smoke/notes/sidenote/typst
}

render_pdf_accessibility_smoke() {
  local status=0
  "${BASH_SOURCE[0]}" pdf-ua-typst || status=$?
  "${BASH_SOURCE[0]}" pdf-ua-latex || status=$?
  return "${status}"
}

case "${target}" in
  html|epub|typst|latex|typst-6x9|latex-6x9|typst-review|latex-review)
    render_profile "${target}"
    ;;
  pdf)
    # The scored backend decision names Typst as the reversible default.
    render_profile typst
    ;;
  print-6x9)
    render_profile typst-6x9
    render_profile latex-6x9
    ;;
  review)
    render_profile typst-review
    render_profile latex-review
    ;;
  pdf-profiles)
    render_pdf_profiles
    ;;
  locale-smoke)
    render_locale_smoke
    ;;
  citation-smoke)
    render_citation_smoke
    ;;
  edition-smoke)
    render_edition_smoke
    ;;
  notes-smoke)
    render_notes_smoke
    ;;
  pdf-ua-typst)
    render_edition_profile print typst,pdf-ua-typst \
      _build/smoke/pdf-accessibility/typst
    ;;
  pdf-ua-latex)
    render_edition_profile print latex,pdf-ua-latex \
      _build/smoke/pdf-accessibility/lualatex
    ;;
  pdf-accessibility-smoke)
    render_pdf_accessibility_smoke
    ;;
  all)
    render_profile html
    render_profile epub
    render_profile typst
    render_profile latex
    ;;
  complete)
    # CI's complete publication set: both reflowable outputs and all six PDFs.
    render_profile html
    render_profile epub
    render_pdf_profiles
    render_locale_smoke
    render_citation_smoke
    render_edition_smoke
    render_notes_smoke
    ;;
  *)
    echo "usage: $0 [all|complete|html|epub|pdf|typst|latex|print-6x9|review|pdf-profiles|locale-smoke|citation-smoke|edition-smoke|notes-smoke|pdf-accessibility-smoke|pdf-ua-typst|pdf-ua-latex]" >&2
    exit 2
    ;;
esac
