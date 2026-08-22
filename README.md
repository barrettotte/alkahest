# Alkahest

Alkahest is a development reference for a reusable technical-book publishing
system. It exercises one canonical Quarto manuscript across HTML, EPUB, Typst
PDF, and LuaLaTeX PDF while testing math, code, citations, diagrams,
accessibility, editions, generated back matter, and publication policy.

This repository is currently the toolkit laboratory and exhaustive specimen,
not the eventual minimal book scaffold. The reusable-template phase will keep
the engine, reference book, and tests here while generating much smaller book
repositories that contain primarily manuscripts, metadata, and assets.

## Common commands

```sh
make                 # Show the concise author workflow.
make bootstrap       # Build the pinned rootless publishing image.
make check-source    # Validate all semantic source policies.
make check-writing   # Run spelling, terminology, and prose checks.
make render          # Build HTML, EPUB, and both primary PDFs.
make render-html     # Build only the web book.
make render-epub     # Build only the EPUB.
make render-pdf      # Build the default Typst PDF.
make package-companion-bundles # Build versioned project-download ZIPs.
make generate-covers # Build development wrap templates and thumbnails.
make generate-rights-report # Build the release rights and credits inventory.
make package-template-engine # Build the reusable presentation-engine ZIP.
make new-book DEST=../my-book TITLE="My Book" AUTHOR="Author Name" # Create a book.
make generate-theme  # Apply book/theme.json to every output adapter.
make generate-release-profiles  # Apply full/preview allowlists and metadata.
make check-extension-apis # Verify the shipped author and maintainer API reference.
make check-book-contracts # Verify schemas and book-owned metadata layers.
make check-compatibility # Verify template versions and reversible migrations.
make package-source-archive # Build the private recovery source ZIP.
make ci              # Run the complete rendering and validation pipeline.
make help-all        # Show maintainer and specialist commands.
```

Normal rendering and validation are offline after `make bootstrap`. Generated
artifacts are written below `book/_build/` and ignored by Git.

## Repository roles

- `book/` is the exhaustive reference manuscript and its format adapters.
- `scripts/` contains the publishing orchestration and policy implementations.
- `tests/` contains negative and compatibility fixtures.
- `docs/` records author workflows and evaluated design decisions.
- `tools/` locks the Python environment used by specialized diagram checks.

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
  the reversible Typst/LuaLaTeX backend decision.
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
- [Compatibility and migrations](docs/compatibility.md) defines versioning,
  deprecations, stable-ID protection, and private template release records.

Named after the theoretical “universal solvent” in Renaissance alchemy.
