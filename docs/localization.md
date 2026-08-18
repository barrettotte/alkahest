# Localization and writing systems

The template separates a book's primary locale from local language changes.
Set the project-level `lang` to a BCP 47 language tag such as `en-US`; mark a
passage with Pandoc's `lang` attribute, and add `dir="rtl"` when its base
direction is right-to-left. Generated navigation and supported cross-reference
labels follow the document locale, while manuscript prose is never translated
automatically. An edition profile must supply any technical label missing from
Quarto's locale data.

## Supported baseline

The locked Libertinus 7.051 family covers the current Latin, Greek, Cyrillic,
and Hebrew specimens. The reference appendix exercises `en-US`, `fr-FR`,
`de-DE`, `el-GR`, `ru-RU`, and inline `he-IL` with right-to-left direction.
This is a tested coverage boundary, not a claim of typographic quality for
every language using those scripts.

Typst disables automatic font fallback, and `make check-glyph-coverage` checks
every non-ASCII manuscript character against Libertinus Serif. A missing glyph
fails before publication rather than selecting a different host or backend
font. CSS still names generic reader fallbacks because browsers and EPUB
readers may disable embedded fonts; meaning must not depend on a specific face.

Arabic, CJK, and Indic scripts are not supported by the baseline. A book that
needs one must add an openly licensed, versioned font with suitable language
coverage; lock its source and bytes; install OTF and WOFF2 roles; extend the
glyph checker deliberately; add any required Babel language module; and test
HTML, EPUB, Typst, and LuaLaTeX output. Full Arabic or Hebrew books also need a
dedicated RTL profile and visual, navigational, and accessibility review.

## Hyphenation and line breaking

Language tags select the relevant hyphenation and line-breaking behavior in
each backend. Tag quotations and terminology when their language differs from
the surrounding prose. Do not insert discretionary hyphens merely to repair
one edition's line ending: responsive layouts, trim profiles, and readers will
break at different places. Authored hyphens remain appropriate when they are
part of a word or compound.

The LuaLaTeX image installs locked Babel modules for English, French, German,
Greek, Russian, and Hebrew plus the available French, German, Greek, and
Russian pattern packages. HTML and EPUB request automatic hyphenation for
those tagged languages but the user agent controls the final break positions.

The LuaLaTeX profile clears Pandoc's `babel-otherlangs` class options so modern
Babel imports local span languages on demand. This preserves language-aware
font shaping and patterns while avoiding the incompatible legacy Greek/English
module sequence emitted by the current Pandoc template.

## Nonbreaking conventions

Use visible source entities so spacing intent survives review:

- `&nbsp;` for a normal nonbreaking space, such as `25&nbsp;MHz` or
  `Figure&nbsp;1`.
- `&#8239;` for a narrow nonbreaking space where a language convention calls
  for one, such as before selected French punctuation.

Avoid scattering invisible Unicode spacing characters through source files.
Automated checks require both nonbreaking forms to survive HTML and EPUB
rendering.

## Locale profiles

The default book locale is `en-US`. The `locale-fr` profile changes the full
document to `fr-FR` and supplies the French contents, table, and code-listing
labels that the current bundled locale does not cover completely. Render it
with:

```sh
make render-locale-smoke
```

Quarto profiles compose, so this command combines the HTML output profile with
the French locale profile. The fixture proves that document language metadata
and generated labels change without rewriting references in the manuscript;
it does not claim that the English prose has been translated.
