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

Named after the theoretical “universal solvent” in Renaissance alchemy.
