# Maintaining the engine

Alkahest has one job: turn a neutral Quarto manuscript into HTML, EPUB, and a
Typst PDF without asking authors to maintain publishing infrastructure. The
reference book proves the reusable engine; `guide/` proves the small interface
an eventual template repository will expose.

## Boundaries

- Authors own `book.toml`, `manuscript/`, `references.bib`, and optional
  `assets/`, `glossary.yml`, and `index.yml` files.
- The engine owns the Quarto profiles, theme, filters, extensions, fonts, and
  rendering code embedded in the container image.
- Generated workspaces and output live under `_build/` and are disposable.
- Manuscript prose stays backend-neutral. Put unavoidable Typst behavior in the
  engine template and commit diagrams as portable SVG or raster assets.

The supported author commands are deliberately small: `doctor`, `check`,
`chapter`, `draft`, `build`, `excerpt`, and `clean`. Do not add another author
command when discovery from numbered files or an existing command is adequate.

## Maintainer workflow

```sh
make bootstrap   # Build the pinned rootless image; this is the networked step.
make check       # Validate links, IDs, citations, glossary, icons, and index.
make quality     # Run Ruff, formatting, mypy, and local tests.
make render      # Build HTML, EPUB, and Typst output.
make ci          # Run the complete offline validation after bootstrap.
```

`make security` adds the dependency audit. `make doctor` verifies the pinned
Quarto container. `make help` is the complete command reference.

## Toolchain updates

Inputs downloaded by `Containerfile` are pinned by version and checksum. When
one changes:

1. update its version, URL, checksum, and installed-file assertion together;
2. update `uv.lock` or `tools/writing/package-lock.json` when applicable;
3. bump the image suffix in `scripts/toolchain.sh` and `guide/Containerfile`;
4. rebuild with `make bootstrap`; and
5. run `make ci` before committing.

Normal renders run rootless with networking disabled. The wrappers map the host
UID and GID so output remains owned by the author. The image contains Quarto,
Typst, fonts, browser accessibility tooling, EPUBCheck, Ace, CSpell, Vale,
Poppler, and the Python runtime used by engine checks.

## Writing checks and overrides

CSpell configuration lives in `cspell.json`; accepted words live in
`config/writing/dictionaries/shared.txt` and
`book/dictionaries/accepted.txt`. Vale's small set of editorial warnings is
configured in `.vale.ini`. Use native source-local comments for exceptional
quoted spellings, and add recurring terms to the narrowest dictionary.

## Tests

Keep unit tests for reusable parsing and orchestration behavior. Keep an
integration fixture only when a real external boundary or meaningful invalid
case cannot be expressed by a unit test. The reference book itself is the
primary rendering fixture; do not create a second specimen for every feature.

Accessibility checks are evidence from rendered artifacts: axe-core for HTML,
EPUBCheck and Ace for EPUB, plus source alternative-text checks. PDF preflight
checks the production Typst artifact. These automated checks do not replace
reader testing or a professional accessibility audit.

## Simplicity rule

Before adding a registry, generator, profile, task, or script, ask whether one
ordinary file or an existing tool already expresses the requirement. New
abstraction is justified only after the same stable need appears more than
once. Before the first public release, change provisional interfaces directly;
there is no legacy compatibility contract to preserve.
