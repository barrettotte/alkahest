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
The package also includes concise extension and book-record references plus the
publication metadata schema, without duplicating those guides in machine
inventories.
The bundled author command merges a short `book.toml` with managed project
identity and layout defaults, discovers numbered manuscript files, diagnoses
the rendering environment, and creates all Quarto, release, theme, registry,
and backend inputs in a disposable workspace. Routine builds produce HTML,
EPUB, and the production Typst PDF; an explicit advanced command also exercises
the secondary LuaLaTeX path. New repositories pin this package as one
archive instead of committing its extracted implementation files.

`MANIFEST.json` records every source-to-package mapping and checksum.
`SHA256SUMS` verifies all package files. The engine is licensed under the MIT
License included in this package; individual generated books retain their own
text and asset rights.
