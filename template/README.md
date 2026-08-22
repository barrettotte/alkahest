# Alkahest book template engine

This package contains the reusable Alkahest presentation engine: semantic
Quarto extensions, Lua filters, shared brand and theme adapters, and Typst and
LuaLaTeX book partials.

It intentionally excludes specimen chapters and assets, per-book metadata,
book-specific edition allowlists, generated fonts, maintainer orchestration,
tests, and release artifacts. A new-book command builds the minimal repository
around this package, while shared defaults and the bundled theme and release
synchronizers support small book-local overrides. The release engine generates
full/preview profiles and stages only each book's explicit source allowlist.
The package also includes a consolidated extension API reference and exact
machine inventory; generated books install both without reference-manuscript
content. It also bundles seven JSON Schemas and an ownership inventory for
book-specific identities, editions, publication facts, rights, accessibility,
cover parameters, and localized labels.

`MANIFEST.json` records every source-to-package mapping and checksum.
`SHA256SUMS` verifies all package files. The engine is licensed under the MIT
License included in this package; individual generated books retain their own
text and asset rights.
