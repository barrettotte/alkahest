# Alkahest

Alkahest is a reusable engine for writing one Quarto Markdown manuscript and
publishing it as HTML, EPUB, and a Typst PDF.

This is intentionally pre-release: a later template repo will consume the released container image.

Authors should eventually need only a small book repository containing
`book.toml`, numbered manuscript files, references, and assets.
Quarto, Typst, fonts, prose checks, and accessibility validators live in a rootless container.

The repo was named after the theoretical “universal solvent” of Renaissance alchemy.

## Prerequisites

This currently supports x86-64 Linux hosts. MacOS, Windows, and
ARM systems are not yet supported because parts of the locked container
toolchain are distributed as Linux AMD64 archives.

Maintainers need:

- GNU Make;
- [uv](https://docs.astral.sh/uv/) 0.12.5; and
- [Podman](https://podman.io/) configured for rootless containers.

`make bootstrap` requires network access to build the pinned publishing image.
Rendering and validation run without network access after that image exists.

## Maintainer commands

```sh
make help       # Show the complete command surface.
make bootstrap  # Build the pinned publishing image.
make doctor     # Inspect the publishing environment.
make check      # Validate the reference manuscript.
make test       # Run local tests.
make quality    # Run linting, formatting, typing, and tests.
make security   # Audit Python source and dependencies.
make render     # Build HTML, EPUB, and Typst output.
make ci         # Run the complete publishing pipeline.
make clean      # Remove disposable reference output.
```

After `make render`, open `book/_build/html/index.html`.
Normal rendering and validation are offline after `make bootstrap`.

## Repository map

- `book/` is the compact reference manuscript and reusable presentation layer.
- `guide/` is a real Alkahest book that documents and tests the author workflow.
- `src/alkahest/` contains the engine's Python checks and orchestration.
- `scripts/` contains the few container and external-process boundaries.
- `tests/` covers reusable logic and meaningful tool integrations.
- `docs/maintenance.md` records engine boundaries and maintenance policy.

Start with [the author guide](guide/README.md) to see the intended writing
experience.
Engine maintainers should read [the maintenance guide](docs/maintenance.md).
