# Reusable template engine

The first reusable-template boundary is a small, versioned engine package built
directly from the proven reference specimen. It contains presentation and
semantic behavior, not book content. Keeping the specimen files canonical and
generating the package from an explicit mapping avoids a second checked-in copy
that could silently drift.

`config/template/template-package.json` selects five complete reusable source
trees—Quarto extensions, Lua filters, LuaLaTeX adapters, web/EPUB themes, and
the Typst adapter—plus the shared brand, package README, and MIT license. It
maps 45 source files to standalone package-relative paths. Installed fonts are
excluded because they are locked build dependencies rather than template
source; a generated book obtains them through the existing toolchain. The
package also carries shared Quarto defaults, shared theme defaults, and the
small deterministic theme synchronizer used by generated repositories.

Run:

```sh
make check-template-engine
make test-template-engine
make package-template-engine
make check-template-package
```

The 0.1.0 package and its outer checksum are written beneath
`book/_build/template/` and ignored by Git. The deterministic stored ZIP has a
fixed timestamp, regular-file mode, sorted path order, a source-to-package
`MANIFEST.json`, and internal `SHA256SUMS`. Validation requires exact source and
destination coverage, rejects symlinks, duplicate mappings, unsafe members,
specimen-specific content, local paths, stale bytes, and unrecognized output.
A fresh extraction must contain all eight extension manifests plus the critical
theme, filter, Typst, and LuaLaTeX entry points.

## Deliberate boundary

This package includes:

- semantic shortcodes and filters for companions, generated lists, glossary,
  icons, indexes, media, notes, and controlled reuse;
- portable preview, PDF-metadata, math-alternative, and HTML-cleanup filters;
- the shared visual brand and HTML/EPUB theme adapters; and
- Typst and LuaLaTeX title, page, typography, and component behavior; and
- versioned Quarto/theme defaults and the cross-format theme synchronizer.

It deliberately excludes reference-book chapters and fixtures, book metadata,
identities, rights decisions, edition allowlists, release profiles, source
assets, generated fonts, maintainer scripts, and tests. Those do not belong in
a reusable presentation engine. The generated-book and per-book theme layers
now surround this package; subsequent roadmap items add reusable full/preview
profiles, schemas, upgrade migrations, and compatibility policy.

The reference specimen remains the exhaustive acceptance consumer in this
repository. Packaging from its canonical engine files proves extraction, and
the [new-book command](new-book.md) now installs those same verified members
into a minimal repository without copying specimen content or metadata. A later
multi-book phase will establish shared upgrade behavior without maintaining
engine files between book repositories by hand.
