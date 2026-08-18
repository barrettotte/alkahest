# Layout stress and pagination policy

The Phase 2 layout corpus lives in `book/layout-stress.qmd`,
`book/page-continuity.qmd`, and `book/layout-acceptance.qmd`. It gives the page
system long chapter, section, subsection, and detail headings; labeled prose
boundaries; and several ordinary chapter transitions. The fixture is normal
Quarto Markdown and contains no manual page commands.

## Fixed-layout contract

All Typst and LuaLaTeX profiles apply these invariants:

- the Phase 2 checkpoint contains 30–50 physical PDF pages; later feature
  fixtures may grow the specimen beyond that range, but never below 30 pages;
- physical page 1 is a recto, and ordinary chapter and appendix openers occur
  on odd physical pages regardless of the visible folio;
- physical page 4 is the stable intentional blank verso after the dedication
  and contains no running furniture or extractable text;
- headings stay with following content and wrap inside the live area;
- a paragraph split across pages retains more than one line on each side.

LuaLaTeX sets `\widowpenalty`, `\clubpenalty`, and
`\displaywidowpenalty` to 10000. Typst 0.15.1 prevents widows and orphans by
default; the theme explicitly sets nonzero `widow` and `orphan` text costs so
the policy does not depend on an implicit engine default. Typst headings also
retain sticky block behavior. These controls are backend theme rules rather
than author-facing markup.

## Reflowable contract

HTML and EPUB preserve the same semantic headings and full titles, but they do
not insert blank pages or claim stable recto placement. Their styles request
two-line widow and orphan minima, avoid a page break immediately after a
heading, and allow exceptionally long headings to wrap rather than widen the
viewport. Browsers and EPUB reading systems may override pagination and fonts,
so these are resilient preferences rather than fixed-sheet guarantees.

## Automated evidence

`make check-pdf-profiles` validates dimensions, font packaging, the 30-page
minimum, required text, physical parity for unique chapter and appendix opening
sentences, the empty page-4 verso, and the presence of at least one labeled
paragraph that crosses a page in every PDF. It deliberately discovers pages
from content instead of hard-coding locations that normal manuscript edits
would invalidate.

`make check-publication` verifies that the long-heading and boundary markers
survive in HTML and EPUB, that the compiled styles contain the pagination and
overflow rules, that HTML links resolve, and that EPUBCheck accepts the book.

## Visual review

Automation cannot judge composition quality. Review both 6 x 9 PDFs first,
then sample 7 x 10 and Letter. Confirm that:

1. chapter and nested headings retain their number, hierarchy, and full text;
2. no heading crosses the live area or remains alone at a page bottom;
3. running heads remain above their rule and clear of the folio and body;
4. each labeled paragraph crossing leaves at least two lines on both pages;
5. intentional blank pages have no visible furniture; and
6. loose page bottoms caused by pagination rules remain inconspicuous.

Typst and LuaLaTeX may produce different line endings and page counts. The
acceptance target is a coherent result in each backend, not pixel identity.
