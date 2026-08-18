# Typography foundation

This document fixes the shared body-text and running-page rules for the PDF
backends. Font families are defined in `font-selection.md`, display-page design
in `page-system.md`, structural depth in `headings-and-references.md`, and the
cross-format color and component system in `theme.md`. Language-aware line
breaking and nonbreaking-space conventions are defined in
[`localization.md`](localization.md).

## Body rhythm

The print and review profiles use 10 pt body text on a 13 pt baseline. Thirteen
points is the reference unit for vertical rhythm; half-unit spacing is allowed
around compact components. This is a soft baseline rather than a mechanically
forced grid: code, mathematics, tables, figures, and accessible line breaking
may interrupt it when keeping every line in phase would harm legibility.

Ordinary prose is justified and uses a 1 em first-line indent with no extra
space between paragraphs. The first paragraph after a heading or another
structural break begins flush left. Lists, quotations, captions, code, and
other block components may define their own internal rhythm, but should return
cleanly to the body rhythm afterward.

Fixed-layout paragraphs must not leave a single first line at the foot of one
page or a single last line at the top of the next. LuaLaTeX enforces this with
maximum widow, club, and display-widow penalties. Typst explicitly retains its
nonzero widow and orphan costs. Headings use each backend's keep-with-next
behavior. These settings may produce a slightly loose page bottom; avoiding a
stranded line or heading takes precedence over mechanically full pages.

Typst receives the values as profile metadata and applies them after the
orange-book defaults. LuaLaTeX applies the same treatment from
`book/latex/book-layout.tex`. The families used within that rhythm are defined
in [`font-selection.md`](font-selection.md).

Reflowable formats use the same families and hierarchy without copying fixed
page geometry. Their medium-specific paragraph and component rules are defined
in [`theme.md`](theme.md).

## Page furniture

Normal body pages use a thin rule above the running head. The folio sits at the
outside edge; the chapter mark occupies the inside position on verso pages and
the current section mark occupies it on recto pages. Display pages and chapter
openings omit running furniture, but still count in pagination. Front matter
uses its backend's conventional numbering until the main matter begins.

Running furniture is navigation, not decoration. It stays smaller than body
text, avoids color-dependent meaning, and contains no manuscript-authored
content. An unusually long chapter or section mark may wrap compactly inside
the reserved header area, but it must not collide with the folio, cross the
rule, or enter the body area. The complete canonical heading remains available
on its opening page, in the contents, and in document navigation.

## Acceptance evidence

The reference chapter contains three consecutive paragraphs so flush-first and
indented-following treatment can be inspected directly. The dedicated layout
stress chapter supplies labeled boundary paragraphs and long headings. All six
PDF profiles must continue to pass trim-size, font-packaging, page-count,
division-parity, blank-verso, and cross-page-fixture checks. Visual review
should compare at least one chapter opening, verso page, recto page, dense
technical page, boundary paragraph, and the 6 x 9 profile before these rules
change. See [`layout-stress.md`](layout-stress.md) for the review contract.
