# Alkahest

Alkahest is a development reference for a reusable technical-book publishing
system. It exercises one canonical Quarto manuscript across HTML, EPUB, Typst
PDF, and LuaLaTeX PDF while testing math, code, citations, diagrams,
accessibility, editions, generated back matter, and publication policy.

This repository is currently the toolkit laboratory and exhaustive specimen,
not the eventual public template repository. `make new-book` generates a
twelve-file development book centered on `book.toml` and numbered manuscripts;
its tiny `Containerfile` uses the complete rootless engine image without
vendoring engine code or an archive.

## Common commands

```sh
make                 # Show the concise workflow.
make list            # List every specialist task and render profile.
make bootstrap       # Build the pinned rootless publishing image.
make doctor          # Diagnose the publishing toolchain.
make check           # Validate all semantic source policies.
make test            # Run all semantic fixture suites.
make quality         # Run Ruff, formatting, mypy, and non-container tests.
make security        # Scan Python source and dependencies.
make render          # Build HTML, EPUB, and both primary PDFs.
make preview         # Build the curated public preview.
make new-book DEST=../my-book TITLE="My Book" AUTHOR="Author Name" # Create a book.
make ci              # Run the complete rendering and validation pipeline.
```

Specialist commands use regular patterns. For example, `make check-icons`,
`make test-citations`, `make render-epub`, and `make generate-theme` remain
available. Release work uses
`make generate-release-profiles`. Run `make list` for the complete index.

Normal rendering and validation are offline after `make bootstrap`. Generated
artifacts are written below `book/_build/` and ignored by Git.

## Repository roles

- `book/` is the exhaustive reference manuscript and its format adapters.
- `guide/` is an internal Alkahest book that teaches and continuously tests the
  concise author workflow through the self-contained rootless engine image.
- `src/alkahest/` is the reusable Python library and central task registry;
  checks, generators, and rendered-output helpers have their own packages.
- `scripts/` contains nine boundaries that still need their own process or
  stable path: generic container wrappers, the browser check, Quarto hooks,
  and generated-book adapters. Rendering, writing checks, and CI live in the
  typed library.
- `tests/unit/` contains fast library tests; `tests/integration/` contains the
  exhaustive publishing-policy fixtures.
- `docs/` records author workflows and evaluated design decisions.
- `pyproject.toml` and `uv.lock` define the Python 3.13 development, security,
  and specialized-diagram environments; `tools/` retains non-Python locks.

## Documentation map

- [Author guide](guide/README.md) is the best starting point for writing a book
  and can be rendered as HTML, EPUB, or PDF with its own concise Makefile.
- [Authoring reference](docs/authoring.md) covers portable headings, references,
  mathematics, code, figures, and citations.
- [Book structure](docs/book-structure.md) covers identities, editions,
  appendices, reusable content, companions, and instructional components;
  [reference material](docs/reference-material.md) covers icons, glossary terms,
  indexes, and notes.
- [Cross-format design](docs/design.md) covers themes, typography, page systems,
  fonts, overrides, and layout review.
- [Media workflows](docs/media-workflows.md) covers generated diagrams, charts,
  circuits, chemistry, computing, physics, and rich-media fallbacks.
- [Localization](docs/localization.md) covers writing systems, line breaking,
  locale profiles, and multilingual QA.
- [Publishing](docs/publishing.md) covers output profiles, accessibility,
  metadata, product manifestations, generated adapters, and public previews.
- [Quality](docs/quality.md) covers integrity, reproducibility, writing checks,
  asset rights, and the static-only execution boundary.
- [Toolchain](docs/toolchain.md) covers the rootless offline environment, its
  exact lock record, updating, and baseline evidence.
- [Template engine](docs/engine.md) covers new-book generation, ownership
  boundaries, and extension APIs.
Named after the theoretical “universal solvent” in Renaissance alchemy.
