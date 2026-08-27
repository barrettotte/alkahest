# Writing Books with Alkahest

This is both the practical user guide and an internal Alkahest book. It exercises
the concise author commands through a self-contained, rootless container while
the engine is still private. The eventual public template will pin the released
engine image instead of the local development tag used here. Read the source in
`manuscript/`, or render the book from this directory:

```sh
make bootstrap                        # Build this book's container once.
make chapter TITLE="A New Chapter"  # Create the next numbered chapter.
make doctor                          # Check whether this book is ready to build.
make draft                           # Build the full HTML draft.
make check                           # Validate configuration and content.
make build                           # Build HTML, EPUB, and the production PDF.
make excerpt                         # Build the selected public excerpt.
```

Run `make help` for the complete concise workflow. Build output is disposable
and lives under `_build/`; open `_build/full/html/index.html` after `make draft`.
This private development guide expects the parent repository's engine image to have
been built once with `make bootstrap`; normal author commands need no host
Python, uv, Quarto, or network access.
