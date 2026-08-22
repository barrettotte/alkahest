# Content architecture

This guide collects the durable structures that span chapters and outputs:
identities, editions, controlled reuse, companion materials, generated lists,
and learning components. Their JSON/YAML registries are authoritative; prose
documents the authoring boundary and review workflow.

## Persistent identities

Every structural heading and numbered object has an explicit lowercase,
descriptive ID independent of its current title, number, filename, edition, or
language. Use `sec-`, `fig-`, `tbl-`, `eq-`, `lst-`, `exr-`, and `sol-` for
their semantic families. Learning roles use `obj-`, `pre-`, `plan-`, `sum-`,
`rev-`, `hint-`, and `ans-`; companion assets use `asset-...`; reusable
placements use `reuse-use-...`.

`book/identities.json` defines policy, variants, editions, companion/reuse
registries, and intentional migrations. `book/identity-lock.json` is the
committed deterministic ledger of active and retired IDs. Ordinary validation
never edits it. After an intentional addition or migration, run:

```console
make update-identities
make check-identities
```

Renaming or removing an active ID requires a substantive migration record. A
retired ID is never reused. Shared-source locales retain canonical IDs;
translated variants may use different files and prose but must preserve the
same semantic identity sets.

## Editions and privacy

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

`scripts/stage-edition.py` builds a disposable project containing only selected
sources. For HTML it also materializes only rich-media files called by those
sources, so an omitted chapter cannot contribute an unused interactive page,
poster, transcript, caption, audio file, or video file. A public tree never
links a private or omitted source. Prefer whole-source selection; use
`content-visible` only for a small statement whose meaning exists solely in one
edition. Every retained reference must resolve, and required definitions,
warnings, prerequisites, and accessibility context must never exist only in
omitted content.

The reusable book product has a narrower two-profile contract documented in
[`release-profiles.md`](release-profiles.md). Its engine-owned defaults and
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

## Controlled reuse

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

## Companion materials

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

## Generated lists and notation

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

## Learning components

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

## Release boundary

Release tooling may package companion bytes, redirects, previews, and
manifest metadata, but it must consume these registries rather than infer them
from rendered prose.
