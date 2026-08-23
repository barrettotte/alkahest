# Alkahest

Alkahest is a development reference for a reusable technical-book publishing
system. It exercises one canonical Quarto manuscript across HTML, EPUB, Typst
PDF, and LuaLaTeX PDF while testing math, code, citations, diagrams,
accessibility, editions, generated back matter, and publication policy.

This repository is currently the toolkit laboratory and exhaustive specimen,
not the author-facing book scaffold. `make new-book` now generates a thirteen-
file repository centered on `book.toml` and numbered manuscripts; the complete
engine is pinned as one managed archive and expands only into ignored build
space.

## Common commands

```sh
make                 # Show the concise workflow.
make list            # List every specialist task and render profile.
make bootstrap       # Build the pinned rootless publishing image.
make doctor          # Diagnose the publishing toolchain.
make check           # Validate all semantic source policies.
make test            # Run all semantic fixture suites.
make quality         # Run Ruff, formatting, mypy, and unit tests.
make security        # Scan Python source and dependencies.
make render          # Build HTML, EPUB, and both primary PDFs.
make preview         # Build the curated public preview.
make new-book DEST=../my-book TITLE="My Book" AUTHOR="Author Name" # Create a book.
make ci              # Run the complete rendering and validation pipeline.
```

Specialist commands use regular patterns. For example, `make check-icons`,
`make test-citations`, `make render-epub`, `make generate-theme`, and
`make package-template-engine` remain available. Recovery and release work uses
`make package-source-archive` and `make generate-release-profiles`. Run `make list`
for the complete index.

Normal rendering and validation are offline after `make bootstrap`. Generated
artifacts are written below `book/_build/` and ignored by Git.

## Repository roles

- `book/` is the exhaustive reference manuscript and its format adapters.
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

- [Content architecture](docs/content-architecture.md) covers identities,
  editions, controlled reuse, companions, generated lists, and learning roles.
- [Media workflows](docs/media-workflows.md) covers generated diagrams, charts,
  circuits, chemistry, computing, physics, and rich-media fallbacks.
- [Accessibility](docs/accessibility.md) covers HTML, EPUB, reader review, and
  PDF/UA evidence without making premature conformance claims.
- [Source and writing quality](docs/quality.md) covers integrity checks, the
  static-only execution boundary, spelling, terminology, and overrides.
- [Publication profiles](docs/publication-profiles.md) covers page geometry and
  the Typst/LuaLaTeX backend decision.
- [Publication metadata](docs/publication-metadata.md) defines canonical
  work-level facts; [manifestations](docs/manifestations.md) define product
  variants, relations, availability, and typed identifiers; [metadata
  generation](docs/metadata-generation.md) feeds all formats, the release
  manifest, and optional pinned ONIX 3.1 output.
- [Toolchain](docs/toolchain.md) covers the rootless offline environment and
  links to its exact lock record.
- [Private source archives](docs/archives.md) covers deterministic recovery
  packages, dependency inventory, history continuity, and restoration tests.
- [Reusable template engine](docs/template-engine.md) defines the extracted
  presentation boundary and what remains book-local.
- [Creating a new book](docs/new-book.md) covers safe scaffold generation,
  independent metadata, engine provenance, and the starter author workflow.
- [Shared defaults and book themes](docs/theme-overrides.md) explains the
  versioned baseline, small per-book overrides, and generated format adapters.
- [Full and preview releases](docs/release-profiles.md) covers per-book chapter
  allowlists, product metadata overrides, and isolated public staging.
- [Extension APIs](docs/extension-apis.md) defines stable author syntax,
  book-local registries, engine hooks, filters, and deterministic generators.
- [Reusable book contracts](docs/book-contracts.md) defines the schemas,
  ownership, and override boundary for book-specific facts.
Named after the theoretical “universal solvent” in Renaissance alchemy.
