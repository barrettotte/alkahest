# Cross-format design

Theme ownership, typography, page systems, fonts, layout stress, and small book-level overrides.

## Cross-format visual theme {#doc-theme}

Alkahest uses one restrained visual vocabulary across web, EPUB, Typst, and
LuaLaTeX. Equivalence means the same hierarchy, font roles, color roles, and
component relationships—not forcing a responsive page or e-reader to imitate
fixed print geometry.

### Semantic tokens

| Role | Value | Use |
|---|---|---|
| Ink | `#20262e` | Body text and local detail headings |
| Slate | `#334155` | Primary headings, links, active navigation, strong rules |
| Muted | `#64748b` | Captions, numbers, and secondary navigation |
| Line | `#cbd5e1` | Rules and component borders |
| Mist | `#f1f5f9` | Code and quiet component backgrounds |
| Paper | `#ffffff` | Default page background |
| Copper | `#9a4f12` | Focus, hover, and warning accents |

The source contract is the versioned `book/alkahest-theme-defaults.json` layer
plus the small book-local `book/theme.json` override. `scripts/sync-theme.py`
resolves them into `_brand.yml` and exact HTML, EPUB, Typst-metadata, and
LuaLaTeX adapters. Quarto 1.10.18 duplicates color-scheme link IDs when Brand
is auto-applied to this HTML book, so that profile still disables automatic
Brand processing and consumes the generated CSS adapter instead. Typst uses
the generated Brand directly; EPUB and LuaLaTeX use their generated bridges.
Tests require exact adapter bytes and representative tokens so drift is
detectable. Color reinforces structure but never supplies the only meaning;
links remain underlined and code/table boundaries retain shape and contrast.
See [`design.md`](#doc-theme-overrides) for the author workflow and
closed override schema.

### Typography and components

All formats use Libertinus Serif for prose, Libertinus Serif Display for major
division titles, Libertinus Sans for headings and navigation, and Source Code
Pro for code. The role mapping is identical even where exact line breaking and
font sizing are medium-specific.

The theme gives H1 a quiet display treatment, H2 a strong slate title plus a
thin rule in reflowable output, H3 a compact sans-serif title, and H4 an
ink-colored local heading. Code blocks use a mist field and defined boundary;
reflowable output and Typst add a slate leading rule. Tables use a strong top
rule, light internal structure, and sans-serif headings. Captions are smaller
and muted. Reflowable content links use slate plus an underline; keyboard focus
uses a three-pixel copper outline in HTML. A first-focus skip link bypasses
repeated navigation, breadcrumb targets retain a 24-pixel minimum height, and
actually overflowing code and math regions enter the ordinary keyboard order.
The reduced-motion query suppresses nonessential theme animation and
transitions while the media-specific adapter preserves its static state.

Display equations retain their normal mathematical size and use a local
horizontal scroll region only when a reflowable viewport is too narrow.
Theorem and proof blocks share a slate leading rule, while the theorem receives
a quiet mist field and italic statement text. Generated labels use the
sans-serif role. Print uses each typesetter's native theorem treatment rather
than imitating CSS geometry. See [`authoring.md`](authoring.md#doc-math) for the authoring and
fallback contract.

Figures keep vector artwork at the available reading width, use sans-serif
muted captions, and display source/license credit on a separate subdued line in
reflowable formats. Comparison panels retain individual subcaptions. The web
adapter lets explicitly full-width art exceed the prose measure without
entering navigation columns; EPUB and print retain their live content width.
See [`authoring.md`](authoring.md#doc-figures) for the asset, attribution, and variant contract.

Tables use restrained rules, sans-serif headers, top-aligned cells, and explicit
column proportions where narrow pages need predictable wrapping. Instructional
blocks retain visible titles and source order: notes and projects use slate,
labs use a guidance accent, and warnings use copper. Color reinforces the
written category but never replaces it. See [`book-structure.md`](book-structure.md#doc-components)
for the authoring and fallback contract.

Semantic icons use original monochrome SVGs at a one-em inline size. HTML and
EPUB apply an explicit baseline offset, retain canonical identity and fallback
metadata, and hide the decorative span from assistive technology to prevent a
duplicate announcement. Both PDF engines consume the same vectors. Visible
adjacent text remains the primary carrier of meaning. See
[`reference-material.md`](reference-material.md#doc-icons) for the registry and authoring contract.

HTML keeps generous paragraph spacing, a readable content measure, responsive
heading sizes, distinct sans-serif navigation, and horizontally scrollable
source. EPUB uses first-line indents, avoids fixed widths, permits reader
overrides, and wraps long code to protect narrow viewports. PDF wraps long code
inside the live area while retaining the baseline, mirrored margins, running
furniture, and recto rules already defined for print. See
[`authoring.md`](authoring.md#doc-code-blocks) for the complete component contract.

### Offline font packaging

The locked toolchain contains WOFF2 files from the same releases as the PDF
OTF faces. Before each render, `python3 -m alkahest.staging webfonts` copies only the selected
faces into the ignored `book/theme/fonts/` build-input directory. HTML copies
the twelve faces and standalone OFL notices. EPUB embeds the twelve faces in
its manifest and carries the copyright notices and complete SIL OFL 1.1 text
in its stylesheet. No render contacts a font service or depends on fonts
installed on a reader's device.

If a user agent disables downloadable fonts, the CSS falls back by role:
Georgia or another serif for prose, the platform sans-serif for headings, and
the platform monospace for code. Content order, labels, and meaning do not
depend on the selected face.

That reader-controlled CSS degradation is distinct from publication-time font
fallback: source glyphs outside the supported locked family fail validation.
See [`localization.md`](localization.md#doc-localization) for the coverage boundary.

### Backend adapters

- `book/theme/alkahest.scss` controls the Bootstrap web book and responsive
  behavior; `alkahest-fonts.css` contains local `@font-face` declarations, and
  `book/generated/theme-overrides.css` applies the resolved book tokens.
- `book/theme/alkahest-epub.css` favors conservative EPUB CSS and references
  fonts explicitly embedded by the EPUB profile; the same generated override
  CSS follows it in the cascade.
- `book/typst/typst-show.typ` consumes Brand colors and styles headings, links,
  captions, and code blocks around the orange-book base.
- `book/latex/book-layout.tex` defines matching xcolor tokens, KOMA-Script
  heading/caption roles, link colors, and the code background before
  `book/generated/theme-overrides.tex` applies book-local tokens.

Automated checks resolve HTML links, run EPUBCheck, require all web/EPUB font
assets, verify theme markers, and retain the six PDF font and structure checks.
Visual review covers a desktop web page, a phone-width web page, the EPUB CSS
at a narrow viewport, and corresponding Typst/LuaLaTeX specimen pages.

## Shared defaults and book themes {#doc-theme-overrides}

Alkahest separates versioned engine defaults from intentional book design.
`book/alkahest-defaults.yml` owns shared Quarto behavior such as inert code
execution, numbering, contents depth, semantic filters, default font roles, and
portable accessibility cleanup. Generated books receive the same file inside
their pinned engine image; the author compiler includes it in a disposable
workspace, so authors never fork it.

The shared palette and font-role defaults live in
`book/alkahest-theme-defaults.json`. Minimal books set only differences beneath
`[theme.colors]` or `[theme.typography]` in `book.toml`; the exhaustive specimen
keeps the equivalent `book/theme.json` per-book override contract fixture:

```json
{
  "schema_version": 1,
  "colors": {
    "primary": "#1d4ed8",
    "accent": "#b45309"
  },
  "typography": {
    "display": "Libertinus Sans"
  }
}
```

Colors use explicit `#RRGGBB` values. Font-family names accept letters, digits,
spaces, periods, underscores, plus signs, and hyphens; the fonts must already
be available in the publishing toolchain or deliberately bundled. An empty
mapping inherits every shared default, which is the initial scaffold state.
Unknown fields fail instead of being silently ignored.

Run:

```sh
make generate-theme
make check-theme-defaults
make test-theme-defaults
```

`scripts/sync-theme.py` resolves the two layers and deterministically writes
five derived files: `_brand.yml` for Quarto and Typst,
`generated/theme-metadata.yml` for shared font metadata,
`generated/theme-overrides.css` for HTML and EPUB,
`generated/theme-overrides.tex` for LuaLaTeX, and a checksum-bearing manifest.
Do not edit those generated adapters. Minimal books regenerate them inside
`_build/.work/` on every `make check`, `make draft`, or release build.

This layer keeps manuscripts and output profiles independent of presentation
choices while avoiding four drifting theme files. It intentionally limits the
first stable override contract to seven semantic colors and five font roles.
Layout geometry, page furniture, component-specific APIs, downloadable fonts,
and dark-mode palettes remain explicit future extensions rather than
unchecked free-form settings.

## Typography foundation {#doc-typography}

This document fixes the shared body-text and running-page rules for the PDF
backends. Font families are defined in `design.md`, display-page design
in `design.md`, structural depth in `authoring.md`, and the
cross-format color and component system in `design.md`. Language-aware line
breaking and nonbreaking-space conventions are defined in
[`localization.md`](localization.md#doc-localization).

### Body rhythm

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
in [`design.md`](#doc-font-selection).

Reflowable formats use the same families and hierarchy without copying fixed
page geometry. Their medium-specific paragraph and component rules are defined
in [`design.md`](#doc-theme).

### Page furniture

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

### Acceptance evidence

The reference chapter contains three consecutive paragraphs so flush-first and
indented-following treatment can be inspected directly. The dedicated layout
stress chapter supplies labeled boundary paragraphs and long headings. All six
PDF profiles must continue to pass trim-size, font-packaging, page-count,
division-parity, blank-verso, and cross-page-fixture checks. Visual review
should compare at least one chapter opening, verso page, recto page, dense
technical page, boundary paragraph, and the 6 x 9 profile before these rules
change. See [`design.md`](#doc-layout-stress) for the review contract.

## Book page system {#doc-page-system}

Alkahest uses one canonical metadata record and ordinary Quarto book structure to drive
title, publication-data, dedication, part, chapter, and appendix treatments.
Manuscripts do not contain Typst or LaTeX page commands.

### Shared metadata

Work-level facts live in `book/publication.json` under the closed contract
documented in [`publishing.md`](publishing.md#doc-publication-metadata). The
committed `book/generated/metadata.yml` adapter supplies Quarto and the
`alkahest` presentation map from that record; `_quarto.yml` retains only
authored presentation settings such as dedication and note placement. The
reference book intentionally labels itself not for publication, and canonical
nullable fields do not invent publisher or legal claims.

LuaLaTeX consumes the fields through the small `latex/title.tex` and
`latex/before-body.tex` template partials. Typst consumes the same fields in
`typst/typst-show.typ`. HTML and EPUB show them semantically on the required
`index.qmd` landing page through Quarto metadata shortcodes. The source gate
checks canonical title, author, language, description, subjects, keywords,
accessibility, and PDF expectations for drift. Exact regeneration preserves
medium-appropriate presentation while rejecting manually edited adapters.

### Print sequence

Both PDF backends use this front-matter sequence:

1. title page;
2. publication-data page;
3. optional dedication page;
4. furniture-free verso;
5. table of contents on a recto page.

Title, publication-data, dedication, part, chapter, and appendix openings omit
running heads and folios. Normal body pages retain the shared furniture defined
in `design.md`. The selected Libertinus Serif Display face is reserved for
display pages, while Libertinus Sans carries compact structural labels.

Parts and chapters start recto in both PDF profiles. Appendices use the same
chapter-opening family but switch to alphabetic labels automatically. The
reference book includes appendices A, B, and C so numbering and cross-references
are observable rather than assumed.
The hierarchy within those divisions is defined separately in
`authoring.md`; appendix grouping and exceptional-material source
policy are defined in `book-structure.md`; and their shared visual vocabulary is
defined in `design.md`.

The Typst implementation wraps only the `part`, `chapter`, and `appendices`
interfaces emitted by Quarto's bundled orange-book filter. The LuaLaTeX path
replaces Quarto's supported `title.tex` and `before-body.tex` partials and uses
KOMA-Script division styling. Backend-specific code stays outside manuscript
files.

### Reflowable behavior

HTML presents the shared front-matter data on the home page, represents a part
in navigation, and gives each appendix its own page. EPUB receives the same
landing-page metadata and alphabetic appendices. Quarto currently ignores part
dividers in EPUB, including appendix groups, so the chapters remain in reading
order without a synthetic part page. Part and group names therefore must not
carry information required to understand a chapter or appendix.

Dedicated print-like blank pages are intentionally not forced into reflowable
outputs. Their semantic content and navigation are the acceptance criteria.

### Acceptance evidence

Every PDF profile check requires a 30–50 page specimen, embedded and subset
fonts, and the expected structural text. It locates unique opening prose for
all ordinary chapters and appendices and requires each physical page number to
be odd. Physical page 4 is the stable intentional blank verso; zero extracted
text there guards against leaked folios, running heads, and placeholders.
HTML link validation and EPUBCheck cover the reflowable structures, which do
not synthesize print-only blanks. Visual review still begins at the tightest
6 x 9 trim because extraction cannot judge hierarchy, wrapping quality, or
white-space balance. The complete procedure is in
[`design.md`](#doc-layout-stress).

## Font selection {#doc-font-selection}

Alkahest uses one openly redistributable font stack for its initial visual
system. The exact release archives and installed font bytes are locked by the
Containerfile and reported by `make toolchain-report`.

| Role | Family | Required faces | Reason |
|---|---|---|---|
| Body text | Libertinus Serif | Regular, italic, bold, bold italic | Readable book face with broad Latin, Greek, Cyrillic, and Hebrew coverage |
| Display matter | Libertinus Serif Display | Regular | Optical proportions for large title and division-page text |
| Headings and navigation | Libertinus Sans | Regular, italic, bold | Coherent contrast with the serif family |
| Mathematics | Libertinus Math | Regular | Unicode math face designed to accompany Libertinus Serif |
| Code and terminal text | Source Code Pro | Regular, italic, bold, bold italic | Purpose-built code face with genuine emphasis styles and distinct technical glyphs |

Libertinus is locked to release 7.051. Source Code Pro is locked to upright
2.042, italic 1.062, and variable-font 1.026; the template uses its static OTF
faces. Both projects distribute the selected fonts under the SIL Open Font
License 1.1. Their license files are preserved in the publishing image.

The image installs OTF files for Typst and LuaLaTeX and retains WOFF2 files for
the HTML/EPUB theme. Published web packages that redistribute those font files
include the corresponding OFL notices. PDF embedding/subsetting and EPUB font
embedding remain subject to automated packaging checks.

### Backend mapping

The shared Quarto metadata names the main, display, sans, math, and monospace
families. Pandoc maps the standard main/sans/math/mono names into LuaLaTeX.
The Typst partial applies the same families to body text, headings, equations,
and raw code. `TYPST_FONT_PATHS` gives the locked OTF directory precedence over
Typst's embedded fallback fonts.

Display typography is applied to title and division pages plus reflowable H1
titles. WOFF2 packaging and browser/reader styling are implemented by the
coherent theme described in [`design.md`](#doc-theme), not an implicit dependency
on fonts installed on a reader's device.

### Coverage boundary

The baseline supports Latin, Greek, Cyrillic, and inline Hebrew with the locked
Libertinus family. Typst has automatic fallback disabled, and
`make check-glyph-coverage` rejects manuscript characters not covered by
Libertinus Serif. Arabic, CJK, and Indic writing systems therefore require an
explicitly licensed and locked per-book font addition instead of silently
selecting an environment-dependent face. Language tags, hyphenation, RTL
scope, and the extension procedure are defined in
[`localization.md`](localization.md#doc-localization).

Upstream references:

- [Libertinus project and release](https://github.com/alerque/libertinus/releases/tag/v7.051)
- [Libertinus OFL 1.1](https://github.com/alerque/libertinus/blob/v7.051/OFL.txt)
- [Source Code Pro project](https://github.com/adobe-fonts/source-code-pro)
- [Source Code Pro OFL 1.1](https://github.com/adobe-fonts/source-code-pro/blob/d3f1a5962cde503f9409c21e58527611d4a19ef1/LICENSE.md)

## Layout stress and pagination policy {#doc-layout-stress}

The Phase 2 layout corpus lives in `book/layout-stress.qmd`,
`book/page-continuity.qmd`, and `book/layout-acceptance.qmd`. It gives the page
system long chapter, section, subsection, and detail headings; labeled prose
boundaries; and several ordinary chapter transitions. The fixture is normal
Quarto Markdown and contains no manual page commands.

### Fixed-layout contract

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

### Reflowable contract

HTML and EPUB preserve the same semantic headings and full titles, but they do
not insert blank pages or claim stable recto placement. Their styles request
two-line widow and orphan minima, avoid a page break immediately after a
heading, and allow exceptionally long headings to wrap rather than widen the
viewport. Browsers and EPUB reading systems may override pagination and fonts,
so these are resilient preferences rather than fixed-sheet guarantees.

### Automated evidence

`make check-pdf-profiles` validates dimensions, font packaging, the 30-page
minimum, required text, physical parity for unique chapter and appendix opening
sentences, the empty page-4 verso, and the presence of at least one labeled
paragraph that crosses a page in every PDF. It deliberately discovers pages
from content instead of hard-coding locations that normal manuscript edits
would invalidate.

`make check-publication` verifies that the long-heading and boundary markers
survive in HTML and EPUB, that the compiled styles contain the pagination and
overflow rules, that HTML links resolve, and that EPUBCheck accepts the book.

### Visual review

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
Golden-page regression checks preserve that rule: each backend is compared
only with its own prior primary-profile baseline, never with the other backend.
