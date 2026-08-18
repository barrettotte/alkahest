# Semantic icon contract

`book/icons.qmd` is the acceptance specimen for reusable inline markers.
Authors invoke the repository-owned `alk-icon` shortcode; they do not choose an
SVG filename, icon font, Unicode character, or backend command.

## Authoring

Use the canonical semantic name followed immediately by visible prose that
states the same meaning:

```markdown
{{< alk-icon equipment >}} **Equipment required.** Gather the listed tools.
{{< alk-icon warning >}} **Warning.** Check the stated limits.
```

The initial canonical names are `equipment`, `warning`, `danger`, `idea`,
`experiment`, and `optional-material`. The central registry at
`book/_extensions/alkahest-icons/registry.lua` records each stable name,
default label, asset, and accepted aliases. For example, `stop` resolves to
`danger`; generated markup always records the canonical identity.

Use a `label` override only when the default fallback label is too general:

```markdown
{{< alk-icon stop label="Stop; stored energy remains" >}} **Stop.** Remove power.
```

The adjacent visible text remains mandatory editorial content and must begin on
the same source line as the shortcode. The registry label must be short,
specific, and nonempty; it supports validation, conversion, and image
alternatives but does not replace the surrounding explanation.

## Registry and assets

Add a new meaning only when it will recur across books and is not merely a
synonym for an existing entry. A registry addition has:

1. a lowercase, hyphenated canonical name;
2. a concise default label;
3. an original or license-compatible monochrome SVG in `book/icons`;
4. only necessary, nonconflicting aliases.

The initial SVGs are original Alkahest assets under the repository's MIT
license. They share a 24 by 24 view box, contain no embedded text, use the
book's ink color, and remain recognizable without color. SVG filenames are
implementation details and may change without rewriting manuscripts.

## Output behavior

The shortcode emits ordinary Pandoc image and span nodes rather than raw
backend markup. HTML and EPUB retain the canonical `data-icon`, registry label,
image alternative, and semantic classes, but mark the complete icon span
`aria-hidden="true"`. Because equivalent visible wording is mandatory, this
keeps the icon decorative in the accessibility tree and avoids announcing the
same meaning twice. Typst consumes the canonical SVG directly. Before
rendering, `scripts/stage-icons` deterministically derives a PDF vector from
each SVG for LuaLaTeX, whose callout-title path does not run Quarto's normal SVG
conversion. The derivative remains an ignored build input, not a second
artwork source. Both PDF backends use a one-em inline size. Adjacent visible
prose carries the meaning in PDF text extraction and when images are
unavailable.

## Side blurbs and notice blocks

Use the same shortcode at the start of a native callout title and add the
`.icon-notice` class to the block. Keep Quarto's unrelated built-in icon off so
the output never displays two symbols:

```markdown
::: {.callout-warning .icon-notice appearance="simple" icon=false}
## {{< alk-icon warning >}} Disconnect power before changing leads

De-energize the fixture and verify that stored energy is gone.
:::
```

The same pattern applies to `.margin-note`, project, lab, and optional-material
blocks. Notice-title adapters use a slightly smaller 0.95-em icon, a stable
trailing gap, and a tuned baseline while retaining the original one-em inline
behavior in prose. EPUB keeps side blurbs inline; roomy HTML may float a
`.margin-note`, and compact PDF profiles keep every notice in source order.

Quarto callout color remains a secondary category cue. Every icon asset is
already monochrome, so grayscale and one-color output use the same repository
vector rather than an output-specific substitute.

## Narrow-layout acceptance

`book/icons.qmd` contains an 18-rem accessibility specimen with a deliberately
long warning. It exercises the approximate measure of a phone or narrow EPUB
reader in every HTML build. At viewports up to 480 pixels, notice-title text may
wrap while the icon retains its fixed inline size. The 6 x 9 profile is the
corresponding compact print acceptance target for both PDF engines; text must
remain inside the physical page even if image alternatives are unavailable.

## Validation

`make check-icons` rejects missing required entries, duplicate names or
aliases, unsafe or missing asset paths, nonconforming SVGs, unknown manuscript
calls, empty labels, unexpected arguments, icon-only calls, and malformed
`.icon-notice` titles. It runs before every Quarto render and explicitly in
`make ci`. Publication validators additionally check that every canonical icon,
fallback label, SVG, decorative accessibility state, and adjacent visible text
survives HTML and EPUB; narrow CSS and the visible acceptance specimen must
survive every PDF profile.
