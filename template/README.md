# Alkahest book template engine

This package contains the reusable Alkahest presentation engine: semantic
Quarto extensions, Lua filters, shared brand and theme adapters, and Typst and
LuaLaTeX book partials.

It intentionally excludes specimen chapters and assets, per-book metadata,
edition allowlists, generated fonts, maintainer orchestration, tests, and
release artifacts. A new-book command now builds the minimal repository around
this package, while shared defaults and the bundled theme synchronizer support
small book-local overrides. Reusable release profiles remain a later layer.

`MANIFEST.json` records every source-to-package mapping and checksum.
`SHA256SUMS` verifies all package files. The engine is licensed under the MIT
License included in this package; individual generated books retain their own
text and asset rights.
