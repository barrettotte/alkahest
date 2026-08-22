# Shared defaults and book themes

Alkahest separates versioned engine defaults from intentional book design.
`book/alkahest-defaults.yml` owns shared Quarto behavior such as inert code
execution, numbering, contents depth, semantic filters, default font roles, and
portable accessibility cleanup. Generated books install the same file at
inside their pinned engine archive; the author compiler includes it in a
disposable workspace, so authors never fork it.

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
