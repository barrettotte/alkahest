# Creating and writing a book

The new-book command creates a small author repository backed by the tested
Alkahest engine. It commits thirteen files: one `book.toml`, three starter
manuscripts, a bibliography, two short directory guides, the writer Makefile
and README, Git ignore rules, one checksum-pinned engine archive, its tiny
bootstrap, and a scaffold identity record. It does not copy extracted engine
trees, generated adapters, empty registries, or backend configuration into the
author's working surface.

The closed generator contract lives in `config/template/new-book.json`. Create
a project with:

```sh
python3 scripts/new-book.py \
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
├── Makefile
├── README.md
└── .alkahest/                 managed; do not edit
```

Write in `manuscript/`. Numbered chapter and appendix filenames determine their
order, so there is no second table of contents to maintain. `book.toml` is the
single author configuration source for identity, title, author, language,
content locations, excerpt selection, and optional theme changes. TOML is used
because Python reads it without an extra dependency or package manager.

The normal workflow is:

```sh
make chapter TITLE="The First Computers"
make draft
make check
make build
make excerpt
```

`chapter` creates the next `NN-kebab-case.qmd` file automatically. `draft`
builds full HTML. `build` creates full HTML, EPUB, Typst PDF, and LuaLaTeX PDF.
`excerpt` creates HTML, EPUB, and Typst products containing only the one or two
chapters selected in `book.toml`, plus front and back matter. `clean` removes
all disposable output.

## Managed compilation

The committed `.alkahest` directory contains one deterministic engine ZIP and a
small `.py` bootstrap with the expected SHA-256 embedded in it. On first use,
the bootstrap verifies the archive and expands it beneath ignored
`.alkahest/cache/`. The author command then compiles `book.toml` into an ignored
workspace under `_build/.work/`; finished products use the shorter
`_build/full/` and `_build/excerpt/` paths:

- Quarto profiles and format adapters;
- full/excerpt allowlists and product metadata;
- theme adapters;
- empty optional semantic registries; and
- engine extensions, filters, and PDF templates.

These files are implementation details and are recreated on every check or
build. Authors never synchronize publication JSON, release JSON, Quarto YAML,
or backend-specific theme files by hand. The detailed schemas, extension API,
compatibility policy, and release registry remain available inside the engine
archive for advanced tooling without cluttering the writing repository.
If an advanced feature needs a glossary, index, notes, media, companion, or
reuse registry, an author may add that named registry at the repository root;
otherwise the compiler supplies an empty one automatically.

`make check-new-book` creates two independent tiny books, proves that their
author facts differ while their exact engine archive is shared, runs both full
and excerpt compilation, and checks deterministic scaffold bytes.
`make test-new-book` covers unsafe input, overwrite attempts, archive drift,
automatic chapter creation, and filesystem failures. A real HTML smoke also
renders from the compiled full and excerpt workspaces in the locked rootless
toolchain.
