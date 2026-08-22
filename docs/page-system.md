# Book page system

Alkahest uses one canonical metadata record and ordinary Quarto book structure to drive
title, publication-data, dedication, part, chapter, and appendix treatments.
Manuscripts do not contain Typst or LaTeX page commands.

## Shared metadata

Work-level facts live in `book/publication.json` under the closed contract
documented in [`publication-metadata.md`](publication-metadata.md). The
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

## Print sequence

Both PDF backends use this front-matter sequence:

1. title page;
2. publication-data page;
3. optional dedication page;
4. furniture-free verso;
5. table of contents on a recto page.

Title, publication-data, dedication, part, chapter, and appendix openings omit
running heads and folios. Normal body pages retain the shared furniture defined
in `typography.md`. The selected Libertinus Serif Display face is reserved for
display pages, while Libertinus Sans carries compact structural labels.

Parts and chapters start recto in both PDF profiles. Appendices use the same
chapter-opening family but switch to alphabetic labels automatically. The
reference book includes appendices A, B, and C so numbering and cross-references
are observable rather than assumed.
The hierarchy within those divisions is defined separately in
`headings-and-references.md`; appendix grouping and exceptional-material source
policy are defined in `appendices.md`; and their shared visual vocabulary is
defined in `theme.md`.

The Typst implementation wraps only the `part`, `chapter`, and `appendices`
interfaces emitted by Quarto's bundled orange-book filter. The LuaLaTeX path
replaces Quarto's supported `title.tex` and `before-body.tex` partials and uses
KOMA-Script division styling. Backend-specific code stays outside manuscript
files.

## Reflowable behavior

HTML presents the shared front-matter data on the home page, represents a part
in navigation, and gives each appendix its own page. EPUB receives the same
landing-page metadata and alphabetic appendices. Quarto currently ignores part
dividers in EPUB, including appendix groups, so the chapters remain in reading
order without a synthetic part page. Part and group names therefore must not
carry information required to understand a chapter or appendix.

Dedicated print-like blank pages are intentionally not forced into reflowable
outputs. Their semantic content and navigation are the acceptance criteria.

## Acceptance evidence

Every PDF profile check requires a 30–50 page specimen, embedded and subset
fonts, and the expected structural text. It locates unique opening prose for
all ordinary chapters and appendices and requires each physical page number to
be odd. Physical page 4 is the stable intentional blank verso; zero extracted
text there guards against leaked folios, running heads, and placeholders.
HTML link validation and EPUBCheck cover the reflowable structures, which do
not synthesize print-only blanks. Visual review still begins at the tightest
6 x 9 trim because extraction cannot judge hierarchy, wrapping quality, or
white-space balance. The complete procedure is in
[`layout-stress.md`](layout-stress.md).
