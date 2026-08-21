# Cross-format visual theme

Alkahest uses one restrained visual vocabulary across web, EPUB, Typst, and
LuaLaTeX. Equivalence means the same hierarchy, font roles, color roles, and
component relationships—not forcing a responsive page or e-reader to imitate
fixed print geometry.

## Semantic tokens

| Role | Value | Use |
|---|---|---|
| Ink | `#20262e` | Body text and local detail headings |
| Slate | `#334155` | Primary headings, links, active navigation, strong rules |
| Muted | `#64748b` | Captions, numbers, and secondary navigation |
| Line | `#cbd5e1` | Rules and component borders |
| Mist | `#f1f5f9` | Code and quiet component backgrounds |
| Paper | `#ffffff` | Default page background |
| Copper | `#9a4f12` | Focus, hover, and warning accents |

The source contract is `book/_brand.yml`, which makes its colors available to
Typst. Quarto 1.10.18 duplicates color-scheme link IDs when Brand is
auto-applied to this HTML book, does not expose all named values to its custom
Sass layer, and does not apply Brand styling to EPUB or LuaLaTeX. The HTML
profile therefore disables automatic Brand processing, and all three adapters
repeat the literal values visibly. Tests require representative tokens in
built artifacts so accidental drift is detectable. Color reinforces structure
but never supplies the only meaning; links remain underlined and code/table
boundaries retain shape and contrast.

## Typography and components

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
than imitating CSS geometry. See [`math.md`](math.md) for the authoring and
fallback contract.

Figures keep vector artwork at the available reading width, use sans-serif
muted captions, and display source/license credit on a separate subdued line in
reflowable formats. Comparison panels retain individual subcaptions. The web
adapter lets explicitly full-width art exceed the prose measure without
entering navigation columns; EPUB and print retain their live content width.
See [`figures.md`](figures.md) for the asset, attribution, and variant contract.

Tables use restrained rules, sans-serif headers, top-aligned cells, and explicit
column proportions where narrow pages need predictable wrapping. Instructional
blocks retain visible titles and source order: notes and projects use slate,
labs use a guidance accent, and warnings use copper. Color reinforces the
written category but never replaces it. See [`components.md`](components.md)
for the authoring and fallback contract.

Semantic icons use original monochrome SVGs at a one-em inline size. HTML and
EPUB apply an explicit baseline offset, retain canonical identity and fallback
metadata, and hide the decorative span from assistive technology to prevent a
duplicate announcement. Both PDF engines consume the same vectors. Visible
adjacent text remains the primary carrier of meaning. See
[`icons.md`](icons.md) for the registry and authoring contract.

HTML keeps generous paragraph spacing, a readable content measure, responsive
heading sizes, distinct sans-serif navigation, and horizontally scrollable
source. EPUB uses first-line indents, avoids fixed widths, permits reader
overrides, and wraps long code to protect narrow viewports. PDF wraps long code
inside the live area while retaining the baseline, mirrored margins, running
furniture, and recto rules already defined for print. See
[`code-blocks.md`](code-blocks.md) for the complete component contract.

## Offline font packaging

The locked toolchain contains WOFF2 files from the same releases as the PDF
OTF faces. Before each render, `scripts/stage-webfonts` copies only the selected
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
See [`localization.md`](localization.md) for the coverage boundary.

## Backend adapters

- `book/theme/alkahest.scss` controls the Bootstrap web book and responsive
  behavior; `alkahest-fonts.css` contains local `@font-face` declarations.
- `book/theme/alkahest-epub.css` favors conservative EPUB CSS and references
  fonts explicitly embedded by the EPUB profile.
- `book/typst/typst-show.typ` consumes Brand colors and styles headings, links,
  captions, and code blocks around the orange-book base.
- `book/latex/book-layout.tex` defines matching xcolor tokens, KOMA-Script
  heading/caption roles, link colors, and the code background.

Automated checks resolve HTML links, run EPUBCheck, require all web/EPUB font
assets, verify theme markers, and retain the six PDF font and structure checks.
Visual review covers a desktop web page, a phone-width web page, the EPUB CSS
at a narrow viewport, and corresponding Typst/LuaLaTeX specimen pages.
