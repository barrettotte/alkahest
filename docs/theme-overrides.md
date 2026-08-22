# Shared defaults and book themes

Alkahest separates versioned engine defaults from intentional book design.
`book/alkahest-defaults.yml` owns shared Quarto behavior such as inert code
execution, numbering, contents depth, semantic filters, default font roles, and
portable accessibility cleanup. Generated books install the same file at
`book/.alkahest/quarto.yml`; authors include it but do not fork it.

The shared palette and font-role defaults live in
`book/alkahest-theme-defaults.json`. A generated book installs that engine file
at `book/.alkahest/theme-defaults.json`. The small `book/theme.json` file is the
per-book override layer and may name only the colors or font roles that differ:

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
Do not edit those generated adapters. The generated-book Makefile exposes the
shorter `make theme` and `make check-theme` commands, and every render refreshes
them before Quarto starts.

This layer keeps manuscripts and output profiles independent of presentation
choices while avoiding four drifting theme files. It intentionally limits the
first stable override contract to seven semantic colors and five font roles.
Layout geometry, page furniture, component-specific APIs, downloadable fonts,
and dark-mode palettes remain explicit future extensions rather than
unchecked free-form settings.
