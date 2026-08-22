# Creating a new book

The new-book command turns the tested presentation engine into a small,
independent repository. It creates only starter chapters, publication facts,
format profiles, engine files, and engine provenance; the reference book's
specimen chapters, fixtures, registries, private material, and release records
are not copied.

The closed generator contract lives in `config/template/new-book.json`. Create
a project with:

```sh
python3 scripts/new-book.py \
  --destination ../my-book \
  --title "My Book" \
  --author "Author Name"
```

The destination's parent must already exist. The command will not overwrite an
existing file or directory. It derives a lowercase work ID from the title, uses
`en-US` and the current date by default, and derives a stable EPUB UUID from the
work ID. `--book-id`, `--subtitle`, `--language`, and `--created` make every
default explicit; use a fixed `--created YYYY-MM-DD` when testing reproducible
generation. For ordinary titles and paths, the equivalent convenience target
is:

```sh
make new-book DEST=../my-book TITLE="My Book" AUTHOR="Author Name"
```

Each project gets independent publication metadata in `book/publication.json`
and a generated Quarto adapter in `book/generated/metadata.yml`. The initial
record is honestly marked as a private development edition with an undecided
publication license and no publisher. Edit those decisions for the book rather
than inheriting facts from the reference specimen.

Presentation files and versioned defaults are installed under `book/`, while
the bundled theme synchronizer lives under `scripts/`. Its license, package
README, source manifest, and checksums are retained under `.alkahest/engine/`, while
`.alkahest/scaffold.json` records the generator version, book identity, stable
EPUB identifier, and hashes for all installed engine files. Run `make help`
inside the generated project for theme/release synchronization, HTML, EPUB,
Typst PDF, LuaLaTeX PDF, preview, and clean commands. Edit only
`book/theme.json` for book-local colors and fonts; `make theme` refreshes every
format adapter without changing the installed defaults. Register new chapters
and set the full/preview allowlists and metadata overrides in
`book/releases.json`, then run `make releases`. Rendering uses an isolated
allowlisted staging project so omitted or private manuscripts are not present
in a public release stage. Empty book-local registries let every semantic extension initialize
without importing specimen data; fill them only as the manuscript needs those
features. The shipped `docs/extension-apis.md` reference identifies which
syntax is author-stable, which registries are book-local, and which changes
require an engine update. `docs/book-contracts.md`,
`book/.alkahest/book-contracts.json`, and the schemas under
`book/.alkahest/schemas/` define the matching book-owned metadata boundary;
engine upgrades may replace those evidence files but never the book records.
The profiles expect Quarto and the PDF tools on `PATH`, or the pinned
Alkahest publishing environment.

Repository validation uses `make check-new-book` for a fresh deterministic
smoke project and `make test-new-book` for unsafe input, overwrite, drift, and
metadata-isolation fixtures. The generator stages all files in a private
sibling directory, validates them, and only then gives the complete directory
its requested name.
