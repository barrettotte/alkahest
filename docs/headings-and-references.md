# Headings, numbering, references, and contents

Alkahest keeps the authored hierarchy deliberately shallow. Structural depth
communicates organization; font size or an unnecessarily long decimal number
must not substitute for reorganizing a chapter.

## Authored heading contract

| Markdown | Book role | Numbered | Listed in contents |
|---|---|---:|---:|
| `#` | Chapter or explicitly unnumbered major division | Yes by default | Yes |
| `##` | Section | Yes | Yes |
| `###` | Subsection | Yes | Yes |
| `####` | Local detail heading | No | No |
| `#####` / `######` | Reserved for semantic components | No | No |

H1 is reserved for the chapter title in chapter files. Authors should not use a
deeper heading merely to obtain smaller text. If H4 is insufficient, split the
material, use a list, or introduce a named semantic component once that syntax
exists.

Prefaces, references, acknowledgements, and similar divisions may use
`.unnumbered`. Add `.unlisted` only when the heading would not help a reader
navigate; the two classes solve different problems.

## Stable identifiers and references

Every structural heading uses one explicit, durable identifier. Ordinary
manuscript headings use lowercase hyphenated `sec-` names, for example:

```markdown
## Clock domains {#sec-clock-domains}

See @sec-clock-domains.
```

Headings that supply a semantic block's visible title inherit the enclosing
theorem, callout, exercise, solution, project, or lab ID instead of declaring a
second anchor. The same stable-ID rule applies to `fig-`, `tbl-`, `eq-`, and
`lst-` objects.
Do not place underscores in IDs, encode a displayed number in an ID, or rename
an ID merely because wording changes.

The checked ledger, glossary/index namespaces, companion-asset IDs, translation
parity, edition behavior, and explicit migration workflow are defined in
[`content-architecture.md`](content-architecture.md#persistent-identities).

References may cross chapter, part, back-matter, and appendix boundaries in
either direction without different syntax. The renderer supplies the correct
relative link in HTML/EPUB and the internal destination in PDF; authors continue
to write only `@stable-id`.

Quarto supplies the localized prefix, number, link, and punctuation for a
reference. Write `@fig-waveform`, not `Figure @fig-waveform`, because the latter
renders a duplicated label. Use `[-@fig-waveform]` only when surrounding prose
deliberately provides the label.

The English specimen uses unabbreviated locale-provided labels: Chapter,
Section, Figure, Table, Equation, Listing, and Appendix. Figures, tables,
equations, listings, theorems, callouts, exercises, and solutions are numbered
within chapters. Inside an appendix, the appendix letter replaces the chapter
number, so independent first objects render as Figure A.1, Table A.1, Equation
A.1, and so on. Typst surrounds an equation number in a prose reference with
parentheses; that backend-native punctuation does not change its identity or
counter. Changing `lang` should select another locale rather than requiring
manuscript rewrites.

Equation, theorem, and proof authoring conventions are defined separately in
[`math.md`](math.md). Figure and subfigure conventions are defined in
[`figures.md`](figures.md). Table, callout, exercise, solution, project, and lab
identifiers are defined in [`components.md`](components.md).

The document-level and inline language contracts, including the French locale
smoke edition, are defined in [`localization.md`](localization.md).

## Contents contract

All outputs call the main outline “Contents.” It contains parts where supported,
chapters, H2 sections, and H3 subsections. H4 detail headings stay local. The
contents also retains useful unnumbered major divisions such as the preface and
references.

HTML provides the same depth in its page outline and book navigation. EPUB
retains chapters, sections, subsections, and appendices but omits part dividers
because Quarto does not currently support EPUB parts. PDF contents pages start
recto as defined by the page system.

## Backend normalization

Quarto 1.10.18 does not apply one `number-depth` value identically across the
current HTML, Typst, and chapter-based LuaLaTeX paths. The author-facing
configuration uses Markdown depth three. The Typst partial explicitly removes
numbering from H4–H6, and the LuaLaTeX partial caps KOMA-Script at subsection
depth. These are backend adapters, not manuscript conventions.

Automated checks require the H2/H3 numbers, localized reference labels,
contents title, and absence of an H4 decimal number in all six PDFs and both
reflowable outputs.
