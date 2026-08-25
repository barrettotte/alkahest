# Reusable template engine

Alkahest delivers its reusable presentation engine inside the locked rootless
container image. A generated book selects that image with its `Containerfile`;
it does not copy engine source, invoke host Python, or carry a separate engine
archive.

The image copies the canonical implementation directly from this repository:

- semantic Quarto extensions and portable Lua filters;
- shared Quarto, theme, and release defaults;
- HTML and EPUB themes;
- Typst and LuaLaTeX presentation adapters;
- the concise author command and its Python runtime; and
- the locked fonts and external publishing tools.

Book manuscripts, metadata, excerpt selections, references, assets, and stable
publication identities remain in each book repository. Reference-specimen
fixtures, maintainer orchestration, tests, and release artifacts remain in this
engine repository.

## Verification boundary

`make bootstrap` builds the local engine image from the canonical files. The
locked author-guide integration test then creates a fresh twelve-file book,
builds its derived rootless image, and compiles both its full and excerpt
workspaces through the same author-facing commands:

```sh
make bootstrap
make test-author-guide
```

The exhaustive reference book separately exercises the extensions and output
adapters across HTML, EPUB, Typst, and LuaLaTeX. This gives the engine one
delivery mechanism and avoids maintaining a second manifest, archive builder,
checksum layer, and extraction test for bytes that books never consume.

The engine remains an unreleased, provisional contract and may be changed
directly until its first public release. The eventual public template should
pin a released GHCR image by digest rather than duplicating this repository.
