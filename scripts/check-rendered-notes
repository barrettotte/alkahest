#!/usr/bin/env bash
# Verify native, chapter, book, and sidenote structures in rendered smoke editions.
set -euo pipefail

require_literal() {
  local needle="$1"
  local file="$2"
  local label="$3"
  if ! grep -Fq "${needle}" "${file}"; then
    echo "error: ${label} is missing required text: ${needle}" >&2
    exit 1
  fi
}

reject_literal() {
  local needle="$1"
  local file="$2"
  local label="$3"
  if grep -Fq "${needle}" "${file}"; then
    echo "error: ${label} contains forbidden text: ${needle}" >&2
    exit 1
  fi
}

chapter_root="book/_build/smoke/notes/chapter/html"
book_root="book/_build/smoke/notes/book/html"
sidenote_root="book/_build/smoke/notes/sidenote/html"
typst_root="book/_build/smoke/notes/sidenote/typst"

python3 scripts/check-html-links.py "${chapter_root}"
python3 scripts/check-html-links.py "${book_root}"
python3 scripts/check-html-links.py "${sidenote_root}"

chapter_reference="${chapter_root}/reference.html"
chapter_components="${chapter_root}/components.html"
require_literal 'class="footnotes footnotes-end-of-document" role="doc-endnotes"' \
  "${chapter_reference}" "chapter endnotes"
require_literal 'data-note-id="page-geometry" data-note-occurrence="1"' \
  "${chapter_reference}" "chapter endnotes"
require_literal 'data-note-id="page-geometry" data-note-occurrence="2"' \
  "${chapter_reference}" "chapter repeated note"
require_literal 'href="#fnref1" class="footnote-back" role="doc-backlink"' \
  "${chapter_reference}" "chapter endnote backlink"
require_literal 'data-note-id="source-order" data-note-occurrence="1"' \
  "${chapter_components}" "second chapter endnote"

book_reference="${book_root}/reference.html"
book_components="${book_root}/components.html"
book_apparatus="${book_root}/glossary-backmatter.html"
reject_literal 'class="footnote-ref"' "${book_reference}" "book endnote references"
require_literal 'id="note-ref-page-geometry-1" class="book-endnote-reference"' \
  "${book_reference}" "first book endnote reference"
require_literal 'id="note-ref-page-geometry-2" class="book-endnote-reference"' \
  "${book_reference}" "reused book endnote reference"
require_literal 'data-note-number="1"' "${book_reference}" "book note number reuse"
require_literal 'id="note-ref-source-order-1" class="book-endnote-reference"' \
  "${book_components}" "cross-chapter book endnote reference"
require_literal 'class="level2 generated-book-notes" data-note-count="2"' \
  "${book_apparatus}" "generated book notes"
require_literal 'id="book-note-page-geometry" class="book-endnote"' \
  "${book_apparatus}" "first generated book note"
require_literal 'data-note-number="1"' "${book_apparatus}" \
  "reused book note number"
require_literal 'data-note-backlinks="2"' "${book_apparatus}" \
  "reused book note backlinks"
require_literal 'href="./reference.html#note-ref-page-geometry-1"' \
  "${book_apparatus}" "first book note backlink"
require_literal 'href="./reference.html#note-ref-page-geometry-2"' \
  "${book_apparatus}" "second book note backlink"
require_literal 'id="book-note-source-order" class="book-endnote"' \
  "${book_apparatus}" "second generated book note"
require_literal 'href="./components.html#note-ref-source-order-1"' \
  "${book_apparatus}" "cross-chapter book note backlink"

sidenote_reference="${sidenote_root}/reference.html"
require_literal 'class="no-row-height column-margin column-container"' \
  "${sidenote_reference}" "HTML sidenotes"
require_literal 'data-note-id="page-geometry" data-note-occurrence="1"' \
  "${sidenote_reference}" "first HTML sidenote"
require_literal 'data-note-id="page-geometry" data-note-occurrence="2"' \
  "${sidenote_reference}" "reused HTML sidenote"
reject_literal 'footnotes-end-of-document' "${sidenote_reference}" \
  "HTML sidenotes"

typst_pdf="${typst_root}/Alkahest-Reference-Book.pdf"
typst_source="${typst_root}/Alkahest-Reference-Book.typ"
test -f "${typst_pdf}"
test -f "${typst_source}"
require_literal '#show footnote: it => column-sidenote(it.body)' \
  "${typst_source}" "Typst sidenote show rule"
require_literal '#footnote[A useful footnote should not depend on the geometry of a printed page.]' \
  "${typst_source}" "Typst repeated sidenote"
typst_text="$(mktemp)"
typst_bbox="$(mktemp)"
typst_bbox_stderr="$(mktemp)"
trap 'rm -f -- "${typst_text}" "${typst_bbox}" "${typst_bbox_stderr}"' EXIT
# Normalize reading-order text so a legal sidenote line wrap cannot weaken the
# content assertion. One repeated note may interleave with its anchor paragraph,
# while its second occurrence must still expose the complete note text.
pdftotext "${typst_pdf}" - \
  | python3 scripts/text-normalize.py pdf \
  >"${typst_text}"
require_literal 'A useful footnote should not depend on the' \
  "${typst_text}" "Typst sidenote PDF"
require_literal 'Semantic notes remain in manuscript source order' \
  "${typst_text}" "Typst cross-chapter sidenote PDF"

# Content can exist in a PDF text stream while still falling beyond trim. Check
# every positioned word against the physical page that contains it.
pdftotext -bbox "${typst_pdf}" "${typst_bbox}" 2>"${typst_bbox_stderr}"
if grep -Fvqx 'no word list' "${typst_bbox_stderr}"; then
  echo "error: positioned-text extraction reported an unexpected diagnostic" >&2
  sed 's/^/  /' "${typst_bbox_stderr}" >&2
  exit 1
fi
if ! python3 scripts/check-text-contract.py bbox "${typst_bbox}"
then
  echo "error: Typst sidenote text crosses the physical page" >&2
  exit 1
fi

echo "ok: rendered semantic notes (native chapter backlinks; consolidated book apparatus; HTML and Typst sidenotes)"
