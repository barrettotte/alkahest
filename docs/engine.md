# Template engine

Creating books, separating engine and book ownership, and extending stable author-facing APIs.

## Creating and writing a book {#doc-new-book}

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

### The author surface

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

### Managed compilation

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

## Reusable template engine {#doc-template-engine}

Alkahest delivers its reusable presentation engine inside the locked rootless
container image. A generated book selects that image with its `Containerfile`;
it does not copy engine source, invoke host Python, or carry a separate engine
archive.

The image copies the canonical implementation directly from this repository:

- semantic Quarto extensions and portable Lua filters;
- shared Quarto, theme, and release defaults;
- HTML and EPUB themes;
- Typst and LuaLaTeX presentation adapters;
- the concise author command and its Python runtime; and
- the locked fonts and external publishing tools.

Book manuscripts, metadata, excerpt selections, references, assets, and stable
publication identities remain in each book repository. Reference-specimen
fixtures, maintainer orchestration, tests, and release artifacts remain in this
engine repository.

### Verification boundary

`make bootstrap` builds the local engine image from the canonical files. The
locked author-guide integration test then creates a fresh twelve-file book,
builds its derived rootless image, and compiles both its full and excerpt
workspaces through the same author-facing commands:

```sh
make bootstrap
make test-author-guide
```

The exhaustive reference book separately exercises the extensions and output
adapters across HTML, EPUB, Typst, and LuaLaTeX. This gives the engine one
delivery mechanism and avoids maintaining a second manifest, archive builder,
checksum layer, and extraction test for bytes that books never consume.

The engine remains an unreleased, provisional contract and may be changed
directly until its first public release. The eventual public template should
pin a released GHCR image by digest rather than duplicating this repository.

## Book-owned records {#doc-book-contracts}

The presentation engine supplies format behavior and defaults. Each book owns
its manuscripts and factual publishing records. Generated adapters are
disposable outputs rebuilt from those sources; they are never another place an
author must keep synchronized.

The normal generated-book workflow compiles the common facts in `book.toml`
into ignored workspace records. Authors only add an advanced registry when a
book actually needs the corresponding feature.

### Stable identities and editions

`book/identities.json` owns persistent content IDs and language variants.
`book/editions.json` owns source availability, structures, formats, and privacy
rules. Validate them with `alkahest check identities` and `alkahest check
editions`.

### Publication and rights facts

`book/publication.json` is the canonical source for work identity,
contributors, rights summaries, accessibility discovery data, and provenance.
Its directly used JSON Schema is `config/metadata/publication.schema.json`.
`book/assets.json` owns permissions, licenses, credits, provenance, and public
distribution decisions. Validate them with `alkahest check
publication-metadata` and `alkahest check asset-rights`.

### Accessibility, covers, and localization

`book/epub-accessibility.json` records accessibility policy without claiming
conformance before review. `config/covers/cover-policy.json` owns trim,
binding, paper, bleed, safe-area, and vendor decisions.
`config/localization/locales.json` owns supported locales, translated labels,
scripts, and toolchain requirements. Their focused checks remain authoritative.

### Ownership rule

Template updates may replace engine defaults and generated adapters. They must
not overwrite manuscripts, `book.toml`, stable identities, publication facts,
rights decisions, edition choices, or other book-owned records. This human
guidance is intentionally the single ownership reference until a public
template release creates a need for a formal external contract.

## Extension API reference {#doc-extension-apis}

This is the internal reference for extending an Alkahest book.
It documents source syntax and configuration that books may depend on, and it
separates those contracts from internal implementation files that may move.
This guide remains provisional before the first public release.

### Authority levels

| Level | May change it | Current stability |
|---|---|---|
| `author` | Any book author | Syntax and semantic IDs are the most stable surface. |
| `book-config` | A book maintainer | Edit the named registry and run its validator in the same change. |
| `engine-maintainer` | Template maintainers | Change through an engine update with cross-format acceptance tests. |
| `maintainer-tooling` | Template maintainers | Generated bytes are outputs; commands and source inputs are the API. |

Never edit a generated adapter or rendered artifact. Never call an extension
inside code, a URL, or an attribute. Stable semantic IDs belong in manuscript
source or book registries; filenames, emitted classes, and backend commands are
implementation details unless this document names them as an extension point.

### Components and instructional blocks {#api-components}

Use ordinary Quarto/Pandoc structures. A notice begins with a native callout,
for example `::: {.callout-note appearance="simple" icon=false}`. Add
`.project-block` or `.lab-block` only to the callout body described in
`docs/book-structure.md`; use a neutral outer anchor when a durable link is needed.
Tables, exercises (`exr-`), and solutions (`sol-`) retain Quarto semantics.

Book authors may change prose, IDs, classes documented here, and table width
hints. Layout rules in the Sass, EPUB CSS, Typst, and LuaLaTeX adapters are an
engine-maintainer surface. A new block class needs a neutral-source specimen,
all four output treatments, narrow-page acceptance, and accessibility review.

### Semantic icons {#api-semantic-icons}

Call `{{< alk-icon warning >}}` and immediately provide equivalent visible
wording. The public arguments are one canonical name or alias plus optional
`label="..."`; other named or positional arguments fail. Put the call at the
start of a title and add `.icon-notice` for a styled notice block.

Canonical semantic names are stable content API; SVG paths are not. Add a new
meaning only in the engine registry, with a reusable name, fallback label,
aliases, monochrome accessible vector, and `make check-icons` coverage.

### Icon-theme customization {#api-icon-themes}

There is no unchecked per-book icon-file override in API 0.1. Icon artwork is
checksum-recorded engine content mapped by
`book/_extensions/alkahest-icons/registry.lua`. To create an icon theme, update
that registry and the complete SVG family as one engine change, preserve the
canonical semantic names, and validate HTML, EPUB, Typst, LuaLaTeX, grayscale,
and narrow layouts with `make check-icons` and publication checks.

Colors and fonts remain book-local through `[theme.colors]` and
`[theme.typography]` in generated books' `book.toml` (the exhaustive specimen
retains `book/theme.json` as direct contract evidence), but the current
SVG strokes are engine assets rather than theme tokens. A future book-local
icon theme must gain a closed registry, rights records, deterministic PDF
derivatives, and stale-output checks before it becomes an author API.

### Glossary sources and presentation {#api-glossary}

Register terms, aliases, forms, acronyms, and definitions in
`book/glossary.yml`. Reference them with `{{< alk-term central-processing-unit
>}}`; optional public arguments are `form=`, `case=`, and `link=`. Put exactly
one `.alkahest-glossary-placeholder` in back matter.

Entries and aliases are book-config. Sorting, anchors, first-use behavior,
print page references, and emitted markup belong to the extension. Extend the
registry fields only with parser, filter, all-format, and `make check-glossary`
coverage. Presentation changes belong in the four engine adapters, not in a
second glossary manuscript.

### Appendix structure and numbering {#api-appendices}

An appendix is a numbered `.qmd` source under the generated book's configured
appendix directory. The author compiler discovers it automatically; the
exhaustive specimen registers the equivalent `role: appendix` record in
`book/releases.json` and `book/editions.json`.
The canonical Quarto shape is `book.appendices`; release staging generates that
shape from the selected appendix allowlist. Authors provide a stable H1 ID and
cross-references, never literal appendix letters or backend appendix commands.

Book configuration owns ordering, groups, and edition inclusion. Counter
format, recto behavior, running furniture, and part treatment are engine APIs.
Run `make check-editions` and release-profile checks whenever inclusion changes.

### Notes and placement {#api-notes}

Ordinary named footnotes without an `.alkahest-note` marker remain native and
need no registry. For configurable placement, use a named note call such as
`[^note-id]` and one definition whose first span has the matching ID and
`.alkahest-note`. Register its source, repeat policy, reference count, and
whole-book order in `book/notes.yml`. Inline notes are not part of the semantic
notes API.

The metadata key `alkahest.notes.placement` selects native footnotes,
chapter/book endnotes, or an accepted sidenote profile. Add a placement only
with backlinks, repeated-note behavior, reflowable fallback, PDF containment,
and `make check-notes` coverage.

### Subject and person indexes {#api-indexes}

Register concepts and relationships in `book/index.yml`, then mark a point or
range with `{{< alk-index computation id=abstract-model >}}`. Put one
`.alkahest-index-placeholder` in back matter. Stable entry IDs and locator IDs
are content identity; display terms, aliases, parents, `see`, and `see-also`
relations are book-config.

New relation types or locator semantics require registry, shortcode, generated
apparatus, HTML/EPUB link, PDF page-number, and `make check-index` coverage.

### Generated lists {#api-generated-lists}

`book/generated-lists.yml` declares ordered list types and named object titles;
glossary data supplies acronym entries. Put one
`.alkahest-generated-lists-placeholder` in front matter. Cross-reference IDs
remain in the manuscript; the `objects:` adapter supplies titles when Pandoc
cannot recover them consistently.

Adding a list source or object family is an engine change. It needs empty-list
behavior, stable ordering, links/page numbers, localization, and `make
check-generated-lists` coverage in every applicable output. Run `make check-generated-lists`
after changing the registry.

### Learning blocks {#api-learning-blocks}

Use neutral wrapper IDs and one role class: `.learning-objectives`,
`.learning-prerequisites`, `.learning-plan`, `.learning-summary`,
`.review-question`, `.question-hint`, or `.answer-key`. Exercises and solutions
use Quarto `exr-` and `sol-` IDs. Pair dependent blocks with `data-for="..."`;
declare whether a review question has a private, public, or absent answer.

Role names, identity prefixes, pairing, and private-answer isolation are stable
semantic API. Styling is engine-owned. A new role needs validation, identity,
edition privacy, theme, all-format, and accessibility behavior.

### Companion materials {#api-companions}

Register downloadable items and `bundle-...` products in `book/companion.json`.
Reference an item with `{{< alk-companion asset-id >}}`; named arguments are not
supported. Each item owns a stable ID, media type, semantic version, checksum,
compatibility, description, source path, and release path. Bundles add an
allowlist, entrypoint, license evidence, credit, and deterministic filename.

New item kinds must remain usable without the shortcode and need rights,
privacy, packaging, and `make package-companion-bundles` coverage.

### Localization {#api-localization}

Set the document BCP 47 language in metadata. Mark inline changes with
`lang="fr-FR"`; add `dir="rtl"` when the local base direction is right-to-left.
The reference contract lives in `config/localization/locales.json`, and a
profile supplies translated generated labels. Manuscript prose is never
translated automatically.

Adding a locale or script requires locked fonts and packages, glyph coverage,
hyphenation/line-breaking policy, complete translated-source manifests when
claimed, and `make check-localization` plus rendered checks. Host fallback is
not an extension mechanism.

### Rich-media fallbacks {#api-rich-media}

Register media in `book/media.json` and call `{{< alk-media media-id >}}` with
no named arguments. Every item needs a static fallback, `fallback_alt`, visible
description, transcript, checksums, provenance, license, and public-distribution
decision; video also needs captions. Interactive behavior is an HTML
enhancement, never the only source of meaning.

New kinds require a portable Pandoc fallback, selected-resource staging,
rights/privacy checks, keyboard and reduced-motion policy where applicable,
and `make check-rich-media` coverage.

### Controlled content reuse {#api-controlled-reuse}

Register a versioned fragment in `book/reusable-content.json`, including its
checksum, provenance, `allowed_contexts`, and complete parameter list. Invoke
it with `{{< alk-reuse reuse-id id="reuse-use-id" context="chapter" ... >}}`.
The use-site ID is persistent identity; every declared parameter is required
and undeclared arguments fail.

Fragments remain heading-free, backend-neutral Markdown without nested reuse
calls. New reuse kinds require a semantic wrapper treatment and `make
check-reuse` coverage; they must not become an include mechanism that hides
dependencies or edition privacy. Run `make check-reuse` after changing its
registry or fragments.

### Portable document filters {#api-filters}

The shared `filters:` order is engine-owned: math alternatives, PDF metadata,
preview presentation, then invalid nested-alt cleanup. Authors supply the
documented source hooks, including `.math-inline-alt` and one unconditional
`.alkahest-preview-placeholder`; they do not reorder filters per book.

A filter must accept ordinary Pandoc AST, be inert outside its explicit hook,
avoid filesystem/network side effects unless the contract names a registry,
preserve stable IDs, and have HTML, EPUB, Typst, and LuaLaTeX fixtures. Raw
backend output is allowed only as a contained adapter fallback.

### Deterministic generators {#api-generators}

Invoke generators through stable tasks such as `alkahest generate graphs` or
their documented Make aliases such as `make generate-graphs`; do not edit generated derivatives. Inputs, tool versions,
ordering, numeric formatting, metadata, and checksums are part of the
reproducibility boundary. A generator must operate offline after bootstrap,
write only declared outputs, and pair generation with an exact stale-output
check.

Book-generated media belongs in canonical source directories and needs rights
and accessibility records. Build reports, rendered artifacts, caches, and
packages remain ignored products rather than generator source.

### Adding or changing an API

1. Choose the lowest authority level that can safely own the change.
2. Add neutral source syntax or a closed book registry before backend code.
3. Update this reference and the relevant implementation together.
4. Add positive and negative source fixtures plus relevant rendered evidence.
5. Run the feature-specific check, source tests, and affected formats.
6. Preserve semantic IDs where they identify authored content; before the first
   public release, update the provisional API and its tests directly.

The detailed reference-specimen rationale remains in `docs/book-structure.md`,
`docs/reference-material.md`, `docs/localization.md`, and
`docs/media-workflows.md`. Those files may discuss acceptance fixtures; this
document is the portable API shipped with the template engine.
