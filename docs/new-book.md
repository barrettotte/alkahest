# Creating and writing a book

The new-book command creates a small author repository backed by the tested
Alkahest engine. It commits twelve files: one `book.toml`, three starter
manuscripts, a bibliography, two short directory guides, the writer Makefile
and README, Git ignore rules, one tiny `Containerfile`, and a scaffold identity
record. It does not contain an engine ZIP, Python launcher, extracted engine
tree, generated adapter, empty registry, or backend configuration.

The closed generator contract lives in `config/template/new-book.json`. Create
a project with:

```sh
uv run --locked alkahest new-book \
  --destination ../my-book \
  --title "My Book" \
  --author "Author Name"
```

The destination's parent must already exist, and the command will not overwrite
an existing path. The equivalent convenience target is:

```sh
make new-book DEST=../my-book TITLE="My Book" AUTHOR="Author Name"
```

## The author surface

```text
my-book/
├── book.toml
├── manuscript/
│   ├── index.qmd
│   ├── chapters/01-first-chapter.qmd
│   ├── appendices/README.md
│   └── references.qmd
├── assets/README.md
├── references.bib
├── Containerfile
├── Makefile
├── README.md
└── .alkahest/scaffold.json    managed identity; do not edit
```

Write in `manuscript/`. Numbered chapter and appendix filenames determine their
order, so there is no second table of contents to maintain. `book.toml` is the
single author configuration source for title, author, language, excerpt
selection, and optional theme changes. The stable work/product identifiers,
creation date, and conventional content locations are managed in
`.alkahest/scaffold.json`, so writers do not maintain publishing machinery.
TOML keeps that author-owned surface compact and unambiguous.

The normal workflow is:

```sh
make bootstrap
make chapter TITLE="The First Computers"
make doctor
make draft
make check
make build
make excerpt
```

`bootstrap` creates the tiny book-facing rootless container from the complete
Alkahest runtime. While this repository is private, build that base image once
with `make bootstrap` in the source toolkit first; the later public template will
pin a released GHCR digest. `chapter` creates the next
`NN-kebab-case.qmd` file automatically. `doctor` validates author inputs and
the renderer inside the container. `draft` builds full HTML. The routine
`build` creates full HTML, EPUB, and the production Typst PDF. The advanced
`build-all` command additionally creates the slower secondary LuaLaTeX PDF.
`excerpt` creates HTML, EPUB, and Typst products containing only the one or two
chapters selected in `book.toml`, plus front and back matter. Successful
renders show one concise progress/result pair per format; if a renderer fails,
its complete diagnostics remain visible. `clean` removes all disposable
output.

The generated `book.toml` is intentionally short. To change colors or display
type, uncomment the optional `[theme.colors]` or `[theme.typography]` examples.
The fixed manuscript layout and generated identifiers are not author settings.

## Managed compilation

The committed `Containerfile` supplies the engine command while the Makefile
mounts only the book at `/book`. Commands run as the host user, with no network,
and write into an ignored workspace under `_build/.work/`; finished products
use the shorter `_build/full/` and `_build/excerpt/` paths:

- Quarto profiles and format adapters;
- full/excerpt allowlists and product metadata;
- theme adapters;
- empty optional semantic registries; and
- engine extensions, filters, and PDF templates.

These files are implementation details and are recreated on every check or
build. Authors never synchronize publication JSON, release JSON, Quarto YAML,
or backend-specific theme files by hand. The engine image owns that behavior
without cluttering the writing repository or requiring host Python, uv,
Quarto, Typst, or TeX.

If an advanced feature needs a glossary, index, notes, media, companion, or
reuse registry, an author may add that named registry at the repository root;
otherwise the compiler supplies an empty one automatically.

`make check-new-book` creates two independent tiny books, proves that their
author facts differ while their exact engine image is shared, runs both full
and excerpt compilation, checks deterministic scaffold bytes, and enforces the
compact configuration plus routine/advanced build split.
`make test-new-book` covers unsafe input, overwrite attempts, image drift,
automatic chapter creation, and filesystem failures. `make test-author-guide`
renders the checked-in guide's full and excerpt HTML, EPUB, and Typst outputs in
the locked rootless toolchain, including a native named-footnote regression.

The repository's `guide/` directory is a checked-in internal book using this
author surface through a tiny book-facing container derived from the complete
rootless engine image. It intentionally does not commit a generated engine
archive or require host Python and uv. Its manuscript is the practical user
guide, so changes to the workflow are tested against both synthetic fixtures
and the instructions future authors will read.
