# Book structure

Whole-book organization, editions, appendices, reusable content, companions, generated lists, and instructional components.

## Content architecture {#doc-content-architecture}

This guide collects the durable structures that span chapters and outputs:
identities, editions, controlled reuse, companion materials, generated lists,
and learning components. Their JSON/YAML registries are authoritative; prose
documents the authoring boundary and review workflow.

### Persistent identities

Every structural heading and numbered object has an explicit lowercase,
descriptive ID independent of its current title, number, filename, edition, or
language. Use `sec-`, `fig-`, `tbl-`, `eq-`, `lst-`, `exr-`, and `sol-` for
their semantic families. Learning roles use `obj-`, `pre-`, `plan-`, `sum-`,
`rev-`, `hint-`, and `ans-`; companion assets use `asset-...`; reusable
placements use `reuse-use-...`.

`book/identities.json` connects the canonical manuscript, translated variants,
edition manifests, and companion/reuse registries. Validate the current source
inventory with:

```console
make check-identities
```

The check requires explicit IDs, rejects duplicates, binds edition sources to
identified chapters, and verifies that translated variants preserve the same
semantic identity sets. Avoid renaming an ID once external links or published
references depend on it; pre-release changes do not require a compatibility
ledger.

### Editions and privacy

`book/editions.json` registers every manuscript source once, then composes
named structures and output editions without copying chapters.

| Edition | Structure | Access | Purpose |
|---|---|---|---|
| `full` | `full` | public | Canonical book |
| `abridged` | `abridged` | public | Deliberately reduced book |
| `preview` | `preview` | public | HTML, EPUB, and default-PDF front matter plus one or two sample chapters |
| `print`, `epub`, `web` | format-specific | public | Medium-specific selection |
| `private` | `private` | private | Internal working material |
| `supplemental` | `supplemental` | public | Core book plus companion appendix |

The `preview` output also composes `_quarto-preview.yml`. That profile supplies
a product subtitle, description, edition statement, stable EPUB UUID, notice
text, optional full-edition and purchase URLs, and watermark settings. One
conditional placeholder in the shared preface is expanded by
`filters/preview.lua`; no preview-only manuscript copy exists. Empty URL values
emit an honest pending-links message, while assigned values must be absolute
HTTPS URLs. Set `alkahest.preview.watermark.enabled` to `false` to retain the
notice and product labeling without the decorative mark.

HTML uses a low-contrast fixed watermark, EPUB uses a conservative in-flow
mark for reader compatibility, and Typst places the mark in the page
background. All formats retain ordinary semantic notice text. The current
cover treatment is deliberately title-based—the preview subtitle and notice
distinguish it without inventing a retail cover. A later cover-pipeline item
will generate actual cover files once dimensions and publication identity are
known.

The edition staging library builds a disposable project containing only selected
sources. For HTML it also materializes only rich-media files called by those
sources, so an omitted chapter cannot contribute an unused interactive page,
poster, transcript, caption, audio file, or video file. A public tree never
links a private or omitted source. Prefer whole-source selection; use
`content-visible` only for a small statement whose meaning exists solely in one
edition. Every retained reference must resolve, and required definitions,
warnings, prerequisites, and accessibility context must never exist only in
omitted content.

The reusable book product has a narrower two-profile contract documented in
[`publishing.md`](publishing.md#doc-release-profiles). Its engine-owned defaults and
book-local `releases.json` extract the ordinary full/preview author workflow
without copying this reference specimen's abridged, private, web-only, or
supplemental acceptance structures. Both staging paths enforce physical source
isolation.

Use `make render-preview` for the standalone HTML, EPUB, and Typst-PDF product,
then `make check-preview` to enforce its exact page/chapter allowlist, private
content and path exclusions, metadata, notice and watermark, contents,
navigation, citations, cross-references, EPUB validity, PDF trim, and embedded
fonts. `make test-preview` exercises negative fixtures. The broader edition
suite remains available through `make check-editions`, `make test-editions`,
and `make render-edition-smoke`.

### Controlled reuse

`book/reusable-content.json` owns versioned fragments below `book/reuse/`.
Fragments are backend-neutral Markdown with no headings, persistent IDs, raw
backend markup, includes, or nested reuse calls. Each registry item declares a
kind, path, semantic version, SHA-256, origin, ownership scope, allowed
contexts, and complete parameter list.

```markdown
{{< alk-reuse reuse-safety-disconnect id="reuse-use-bench-safety" context="project" equipment="the breadboard" >}}
```

Parameters substitute factual values only. Each placement has its own durable
ID; the registry ID names the shared wording. Any byte change requires a new
checksum and reviewed version increment. `make check-reuse` and
`make test-reuse` validate the complete dependency and context contract.

### Companion materials

`book/companion.json` registers every file below `book/companion/` and groups
each item into exactly one versioned bundle. Each `asset-...` item records kind,
title, unique safe path, media type, semantic version, SHA-256, concrete
compatibility, accessible description, stable release path, and optional HTTPS
URL. Each `bundle-...` record adds its versioned ZIP name, entrypoint, complete
item allowlist, compatibility notes, SPDX license and checked license file,
credit text, stable release path, and optional durable URL. A URL never replaces
the offline package location.

```markdown
{{< alk-companion asset-half-adder-verilog >}}
```

HTML may enhance the title into a direct download. EPUB and PDF keep the
version, description, compatibility, checksum prefix, and package location as
visible text. The bundle entrypoint also exposes the matching bundle ID,
version, license, and release path.

`make package-companion-bundles` creates a byte-reproducible ZIP below
`book/_build/companion/`. Its single top-level directory contains the registered
files, complete license, human README, machine-readable manifest, and internal
`SHA256SUMS`; a sidecar records the ZIP's outer checksum. Run
`make check-companion-bundles` to reproduce and byte-compare the package, or
`make test-companion-bundles` for stale/missing artifact fixtures. Any byte
change requires a new digest; compatibility promises drive semantic versioning.
ZIP members are stored without Deflate so host zlib versions cannot change the
archive bytes. The current bundle has no public URL and nothing in this workflow
uploads it.

### Generated lists and notation

`book/generated-lists.yml` configures figures, tables, listings, equations,
acronyms, symbols, nomenclature, and algorithms. One placeholder in
`book/generated-lists.qmd` is replaced with ordinary semantic blocks and
cross-references, so all backends reuse the same entries.

Cross-reference objects declare an existing `id` and a concise list `title`.
Symbols and nomenclature declare a portable TeX `display` without dollar
delimiters, a natural-language `alt`, meaning, stable sort key, and target:

```yaml
terms:
  state-vector:
    list: nomenclature
    display: x_k
    alt: x sub k, system state vector at discrete step k
    meaning: system state vector at discrete step k
    sort: state vector
    target: eq-state-update
```

Acronyms come from `book/glossary.yml`; empty enabled lists are omitted. Run
`make check-generated-lists`, `make test-generated-lists`, and
`make check-rendered-lists`.

### Learning components

Learning metadata remains optional and semantic. Objectives state observable
reader outcomes; prerequisites state assumed knowledge or equipment; a study
plan records `expected-time` and `difficulty`; a summary restates established
ideas without introducing new claims. Review questions, hints, exercises,
solutions, and private answer keys use paired stable IDs rather than proximity
or typed numbers.

Public editions may contain a question and hint while omitting a private answer
source. The manifest and learning validator enforce pairing without leaking
answers. Exact visual treatment may vary by backend, but role title, order,
metadata, and relationships remain visible. Run `make check-learning` and
`make test-learning`; rendered publication checks cover output behavior.

### Release boundary

Release tooling may package companion bytes, redirects, previews, and
manifest metadata, but it must consume these registries rather than infer them
from rendered prose.

## Appendix source and grouping contract {#doc-appendices}

Appendices use ordinary Quarto Markdown and native book structure. Authors do
not write backend commands for appendix mode, letters, contents entries, group
pages, or running furniture.

### Canonical full-book structure

The `book.appendices` list in `book/_quarto.yml` groups related appendices with
the same `part` and `chapters` shape used by the main book:

```yaml
book:
  appendices:
    - part: "Production reference"
      chapters:
        - appendices/page-system-checklist.qmd
        - appendices/format-behavior.qmd
    - part: "Language reference"
      chapters:
        - appendices/language-and-script.qmd
```

Every listed file is a normal chapter-shaped `.qmd` document with exactly one
level-one heading and a stable explicit ID:

```markdown
# Page-system checklist {#sec-page-system-checklist}
```

The configuration determines that the source is an appendix; the manuscript
does not contain `\appendix`, Typst functions, manually written letters, or
hard-coded contents text. A book with only one appendix may still use one
named group so adding another appendix later does not require changing the
source convention.

HTML retains group names in navigation and breadcrumbs. Typst and LuaLaTeX
render the groups as designed part divisions and keep the following appendix
openers on recto pages. Quarto's EPUB writer omits part dividers, including
appendix groups, but retains the ordered alphabetic appendices and their
sections. This is the same documented reflowable fallback used for main-book
parts; group names must not carry information unavailable in their children.

### Edition registry

`book/editions.json` registers appendices alongside front matter, chapters, and
back matter. Appendix sources record `core`, `online-only`, or `supplemental`
availability and each whole-book structure provides its complete ordered
appendix groups. Standard render commands select `web` for HTML, `epub` for
EPUB, and `print` for PDFs. The preview retains core Appendix A, the web edition
adds online-only D, and the supplemental edition adds its own D instead.

See [Content architecture](#doc-content-architecture) for the complete
structure/edition matrix, staging
boundary, private-source policy, and reduced-book reference checks.

Quarto concatenates project arrays while merging profiles, so a profile cannot
safely remove a canonical appendix. The edition staging library instead generates a
temporary selectively symlinked project under `book/_build/staging/editions`,
replaces the complete chapter and appendix lists there, renders inside that
project, and promotes only a
successful artifact into the canonical `_build` tree. Never edit staged files;
they are disposable build products.

Each staged project composes an `edition-<name>` profile. This makes the active
edition available to Quarto conditions without copying manuscript content. For
example, a paragraph that references appendices omitted from preview can use:

```markdown
::: {.content-visible unless-profile="edition-preview"}
The full-family editions also retain @sec-format-behavior.
:::
```

Use this only when the entire statement is edition-specific. A retained claim
must never depend on a warning, definition, citation, or other required context
that was removed with an appendix.

### Optional sources

Canonical appendix sources that are intentionally absent from one or more
editions remain under `book/appendices`. They declare the exception in document
metadata rather than wrapping their prose in format conditions:

```yaml
---
alkahest-appendix:
  availability: online-only
---
```

The accepted exceptional values are `supplemental` and `online-only`.
`supplemental` means the companion edition may select the source in a suitable
format; `online-only` allows it only in the HTML web edition. The content below
that metadata remains ordinary, portable Markdown. It can later move into the
core set or appear in another compatible edition by changing the registry,
without copying the manuscript.

An omitted appendix must be genuinely optional. It cannot contain the only
safety warning, prerequisite, definition, accessible explanation, or context
needed by a retained chapter. References to optional sources must be omitted by
the same edition condition or redirected to a retained stable target.

### Validation and acceptance

`make check-editions` validates every registered source, complete on-disk
coverage, one identified H1 per source, availability and format policy, ordered
whole-book structures, cross-reference integrity, and the shared bibliography.
`make test-editions` proves malformed and leaking contracts fail and verifies
that staged reduced/public/private source trees are isolated as declared.

Rendered checks retain A–C in the full-family outputs, include online-only D in
HTML alone, and exclude all exceptional appendices from EPUB and every PDF.
The preview smoke edition proves A and A.2 retain their numbers and both link
directions while B and C references are absent. The supplemental smoke edition
proves core A–C stay stable, the supplemental source becomes D, and the
online-only source does not leak. Offline link checking covers both smoke
editions, so an omitted target cannot survive as a dangling HTML reference.

### Appendix-local numbering

Appendix sections and numbered objects use the same backend-neutral syntax as
main-matter chapters. Authors provide stable IDs and cross-references, never a
visible appendix number:

```markdown
## Measurement method {#sec-appendix-measurement}

See @fig-appendix-probe and @eq-appendix-transfer.

![Probe placement.](probe.svg){#fig-appendix-probe fig-alt="A probe connected across the test points."}

$$
H(s) = \frac{1}{1 + sRC}.
$$ {#eq-appendix-transfer}
```

The appendix letter replaces the main-matter chapter number. Sections therefore
render as A.1, A.2, and so on, while each numbered family starts its own sequence
at A.1. This applies to figures, tables, equations, listings, theorems, notes,
warnings, exercises, and solutions. Projects and labs remain deliberately titled
but unnumbered under the current component contract.

HTML, EPUB, Typst, and LuaLaTeX all generate the same letter-and-counter
identity and include numbered appendix sections in their contents or navigation.
Typst renders prose equation references as `Equation (A.1)`, while the other
current backends render `Equation A.1`; this is an accepted presentation-level
difference. Running heads, recto openers, and blank-page furniture remain owned
by the PDF page-system adapters rather than manuscript source.

The appendix acceptance fixture binds every number to a stable structural ID in
HTML and EPUB and requires the corresponding visible markers in all six PDFs.
Literal numbers may appear in that explicit acceptance matrix, but ordinary
manuscript references must always use `@id` syntax so reordering stays safe.

### Cross-references and bibliography

Chapter and appendix boundaries do not change the reference syntax. A chapter
may cite an appendix section or object, and an appendix may cite a main-matter
section or object, using the same stable `@id` form. HTML and EPUB preserve
cross-document links in both directions; PDF backends preserve generated labels
and internal destinations while allowing their normal punctuation conventions.

Appendices use the one project-level bibliography declared in
`book/_quarto.yml`. Cite sources normally—for example, `[@knuth1984]`—and place
the one generated `# References` division in the book's shared back matter. Do
not add `bibliography` metadata or a second `#refs` block to an appendix. This
keeps citekeys, formatting, deduplication, and edition filtering consistent and
prevents identical sources from appearing in several reference lists.

The appendix validator rejects local appendix bibliography metadata. Rendered
acceptance checks exercise links from a main chapter to an appendix section and
figure, links back to a main-matter section and equation, and an appendix-only
citation that appears exactly once in the central HTML and EPUB bibliographies.
The pinned EPUB writer retains the citation identity and central anchored entry
but does not currently hyperlink the inline citation; this is a documented
renderer fallback rather than a reason to duplicate bibliography source.

All backends run the selected versioned CSL file through Pandoc citeproc and use
the authored “References” heading. Chicago author–date is the default, and a
composable IEEE numeric profile demonstrates per-book overrides without
rewriting appendix content. The complete policy, syntax, style provenance, and
acceptance coverage are recorded in `docs/authoring.md`.

A truly independent supplement with its own bibliography is a separate
publication and should receive its own future edition manifest/configuration.
It is not modeled as an appendix-local exception inside one book.

## Tables and instructional-block contract {#doc-components}

`book/components.qmd` is the acceptance specimen for compact and multipage
tables, margin notes, general callouts, warnings, exercises, solutions,
projects, and laboratory procedures. Authors use Quarto Markdown semantics;
backend-specific markup is not part of the manuscript contract.

Objectives, prerequisites, expected time, difficulty, summaries, review
questions, hints, and private answer keys follow the learning contract in
[`book-structure.md`](#learning-components).

### Tables

Use pipe tables for straightforward row-and-column relationships. Every
numbered table has a concise caption, a lowercase `tbl-` identifier, real
column headers, declared units, and intentional alignment. Use
`tbl-colwidths` when prose cells need a predictable share of narrow print
pages:

```markdown
| Stage | Voltage (V) | Action |
|:------|------------:|:-------|
| Input | 0.25 | Record the quiet-state value. |

: Measurement plan {#tbl-measurement-plan tbl-colwidths="[25,20,55]"}
```

Keep units in headers, align comparable numbers consistently, and write a
caption that explains the table's purpose rather than restating its columns.
Color, shading, or position must not be the only carrier of meaning. A short
`.table-note` immediately after a table may state scope, provenance, or a
qualification that applies to the complete table.

#### Multipage tables

The current Typst backend wraps a captioned cross-reference table in an
unbreakable figure. Consequently, a numbered `tbl-` table must fit within one
page in every supported PDF profile. For a genuinely long inventory or
procedure, use an unnumbered table under a stable H4 heading. The heading stays
with the first table fragment, and both PDF engines can break the table and
repeat its header:

```markdown
#### Bench-test sequence {#test-sequence-table .table-title}

| Step | Operation | Evidence |
|-----:|:----------|:---------|
| 1 | Inspect the assembly. | Orientation marks agree. |

: {tbl-colwidths="[10,35,55]"}
```

Do not shrink text, rasterize a table, force a landscape page, or allow rows to
overlap merely to preserve a table number. If a long table must be numbered,
split it into independently captioned logical tables until the backend gains a
breakable numbered-table representation.

### Notes and callouts

Use native callouts with a visible title, `appearance="simple"`, and
`icon=false`. Add `.icon-notice` and start the title with the registered
`alk-icon` meaning when a repeated visual category helps the reader. Keep the
equivalent title wording on that same line; it, not the decorative icon or
callout color, carries the category for nonvisual reading. The complete icon
and fallback contract is documented in `docs/reference-material.md`.

```markdown
::: {#nte-range .callout-note .margin-note .icon-notice appearance="simple" icon=false}
## {{< alk-icon idea >}} Margin note: record the range

Keep the instrument range with its reading.
:::
```

A `.margin-note` becomes a compact inset on roomy HTML layouts. EPUB and all
one-column PDFs retain it inline at the same source position. This fallback is
intentional: it preserves readable type, source order, and accessibility
instead of reducing the established print body width. Use ordinary note or tip
callouts for supplementary guidance, and reserve `.callout-warning` for a real
hazard. Cross-referenceable callout IDs use Quarto's `nte-`, `tip-`, `wrn-`,
`imp-`, or `cau-` prefixes; their visible labels are generated.

### Exercises and solutions

Exercises and solutions use Quarto's built-in theorem-family identifiers:

```markdown
::: {#exr-divider-budget}
## Divider power budget

Calculate the current and resistor powers.
:::

::: {#sol-divider-budget data-for="exr-divider-budget"}
## Divider power budget

The series current is ...
:::
```

Reference the exercise with `@exr-divider-budget`. The current Typst backend
numbers a solution but cannot resolve an inline `@sol-...` reference, so prose
refers to the paired exercise and the solution retains its stable `sol-`
identifier for future collection or filtering. Authors never type exercise or
solution numbers.

### Projects and labs

A project is a titled note callout with `.project-block`; it must state an
outcome, constraints, and deliverables. A lab is a titled tip callout with
`.lab-block`; it must state prerequisites or safety boundaries, an ordered
procedure, and required evidence. Put a neutral outer anchor around either
callout when a durable link target is needed:

```markdown
::: {#project-threshold .project-anchor}
::: {.callout-note .project-block .icon-notice appearance="simple" icon=false}
## {{< alk-icon equipment >}} Project: build a threshold indicator

**Outcome.** ...

**Constraints.** ...

**Deliverables.** ...
:::
:::
```

The wrapper avoids presenting an arbitrary project or lab ID as a Quarto
cross-reference type. These blocks are linked by their stable anchors but are
not automatically numbered.

### Validation

`make check-publication` verifies the component chapter, semantic table markup,
header cells, column-width declarations, unique callout IDs, generated
references, explicit titles, project/lab classes, and EPUB validity. `make
check-pdf-profiles` checks the visible component labels, long-table continuation
and repeated headers, chapter-aware callout numbering, embedded fonts, and
physical containment in every PDF profile. Visual review starts with the
compact 6 x 9 outputs and a narrow HTML viewport.
