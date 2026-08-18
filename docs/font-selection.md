# Font selection

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

## Backend mapping

The shared Quarto metadata names the main, display, sans, math, and monospace
families. Pandoc maps the standard main/sans/math/mono names into LuaLaTeX.
The Typst partial applies the same families to body text, headings, equations,
and raw code. `TYPST_FONT_PATHS` gives the locked OTF directory precedence over
Typst's embedded fallback fonts.

Display typography is applied to title and division pages plus reflowable H1
titles. WOFF2 packaging and browser/reader styling are implemented by the
coherent theme described in [`theme.md`](theme.md), not an implicit dependency
on fonts installed on a reader's device.

## Coverage boundary

The baseline supports Latin, Greek, Cyrillic, and inline Hebrew with the locked
Libertinus family. Typst has automatic fallback disabled, and
`make check-glyph-coverage` rejects manuscript characters not covered by
Libertinus Serif. Arabic, CJK, and Indic writing systems therefore require an
explicitly licensed and locked per-book font addition instead of silently
selecting an environment-dependent face. Language tags, hyphenation, RTL
scope, and the extension procedure are defined in
[`localization.md`](localization.md).

Upstream references:

- [Libertinus project and release](https://github.com/alerque/libertinus/releases/tag/v7.051)
- [Libertinus OFL 1.1](https://github.com/alerque/libertinus/blob/v7.051/OFL.txt)
- [Source Code Pro project](https://github.com/adobe-fonts/source-code-pro)
- [Source Code Pro OFL 1.1](https://github.com/adobe-fonts/source-code-pro/blob/d3f1a5962cde503f9409c21e58527611d4a19ef1/LICENSE.md)
