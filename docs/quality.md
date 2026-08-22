# Source and writing quality

Alkahest validates the earliest representation that can establish each fact,
then checks rendered artifacts where conversion can introduce regressions. All
commands use committed policy; publishing and writing tools run offline through
the pinned rootless image.

## Integrity layers

| Risk | Source gate | Rendered or isolation gate |
|---|---|---|
| Broken links/assets | `make check-editorial-integrity` | `make check-publication` |
| Missing or unused citations | `make check-citations` | Shared citeproc bibliography checks |
| Missing image/diagram alternatives | Editorial and domain-media checks | Publication and accessibility checks |
| Missing inline/display math alternatives | Editorial check | Typst PDF/UA and semantic math checks |
| Duplicate or drifting IDs | Editorial and identity checks | Rendered identity/anchor checks |
| Dangling references | Editorial and edition checks | Final HTML/EPUB link checks |
| Private edition leakage | Edition staging checks | Public-artifact canary search |
| Unlicensed or private assets | `make check-asset-rights` | `make check-release-assets` across HTML, EPUB, and six PDFs |
| Nondeterministic output | Reproducibility policy and fixed build inputs | Exact HTML-tree, EPUB, and PDF fingerprints across repeated builds |
| Fragile PDF composition | Golden-page policy and semantic markers | Exact decoded-pixel comparison with backend-specific baselines |

Use `.decorative`, `role="presentation"`, or `aria-hidden="true"` only for an
image that carries no information. Otherwise supply useful Markdown alt text
or `fig-alt`; complex diagrams may add an adjacent visible description.
External URLs remain an explicit offline boundary and are checked at release
time rather than during deterministic local builds.

`make check-source` runs every semantic source group. `make test-source` runs
their positive and negative fixture suites.

## Publication consistency

The source gates establish editorial intent; rendered gates prove that format
conversion preserved it. The complete consistency contract is:

| Concern | Source evidence | Rendered evidence |
|---|---|---|
| Cross-references and bibliography | Editorial integrity and citation checks | Link resolution, citation-style parity, one shared bibliography, and bidirectional chapter/appendix references |
| Notes | Note registry, definitions, calls, repeats, and placement policy | Native footnotes, chapter/book endnotes, backlinks, and HTML/Typst sidenotes |
| Generated lists and index | List/index registries, markers, ranges, hierarchy, and relations | Linked HTML/EPUB lists and indexes plus page-resolved Typst/LuaLaTeX numbering |
| Glossary | Entries, aliases, forms, calls, and one generated placeholder | Stable sorted anchors, links, definitions, language scope, acronyms, and print page references |
| Appendices and numbering | Appendix/edition manifests, IDs, inclusion rules, and references | Stable appendix letters, local numbering, contents, cross-references, and shared citations |
| Persistent identity | Identity ledger, migrations, namespaces, variants, and retired IDs | Anchors retained across HTML, EPUB, previews, supplemental/private editions, and locales |
| Edition variants and privacy | Whole-book manifests and staged source isolation | Inclusion/omission, grouping, numbering, links, and public/private canary checks |
| Localization | Locale modes, translation manifests, language scopes, scripts, locked packages, glyph coverage, fallback, and hyphenation policy | HTML/EPUB document languages, inline direction, localized labels and cross-references, EPUB metadata, and hyphenation |

Run `make check-source` before rendering. After `make render-all`, run `make
check-publication` for HTML, EPUB, locale, notes, and edition artifacts, then
`make check-pdf-profiles` for all six PDFs. `check-publication` includes EPUBCheck
and the rendered note, identity, index, generated-list, glossary, appendix,
citation, edition, privacy, and numbering contracts; focused `check-rendered-*`
commands remain available for diagnosis.

For a language or translation change, run `make check-localization`, render the
affected locale, and run `make check-rendered-localization`. Unsupported Arabic,
CJK, and Indic text fails explicitly until a versioned font and layout profile
extends the tested coverage boundary.

## Reproducible artifacts

`book/reproducibility.json` defines one exact-content contract for the
distributable HTML tree, EPUB, and all six PDFs. Directory fingerprints include
every relative path and file byte; EPUB and PDF fingerprints cover the complete
file. No timestamp, document ID, archive-order, or backend-metadata field is
discarded during comparison.

The rootless wrapper passes a fixed `SOURCE_DATE_EPOCH` to Pandoc, Typst, and
LuaLaTeX and enables TeX's source-date behavior. This stabilizes EPUB package
dates and member timestamps, PDF dates and IDs, and other tool-generated time
fields. A quote-aware postprocessor sorts serialized markup attributes because Lua
maps have no stable iteration order; it leaves prose and script/style bodies
unchanged and excludes checksum-locked copied media. The reference EPUB also
has a stable specimen UUID. When adapting the
template for a real publication, replace that identifier and deliberately set
the reproducibility epoch to the publication's chosen build date; do not derive
either value from the wall clock.

After `make render-all`, use `make check-reproducibility` to validate all eight
artifact fingerprints and their stable metadata. `make verify-reproducibility`
rebuilds and byte-compares the complete set. CI performs the quicker repeated
HTML, EPUB, and default-Typst comparison on every change; the full command is a
pre-release gate because rebuilding three fresh-cache LuaLaTeX profiles is
comparatively expensive. `make test-reproducibility` covers policy drift,
unstable EPUB/PDF dates, markup ordering, missing artifacts, and changed content.

`make build-report` is intentionally outside the artifact contract. Its capture
time, wall-clock duration, host CPU count, and Podman version describe the
measurement environment and therefore vary; the rendered books it measures do
not receive an exception.

## Golden-page visual regression

`config/pdf/golden-pages.json` selects five composition-sensitive fixtures by
semantic text marker: a long code line, aligned mathematics, a circuit figure,
a multipage table, and multilingual layout. Each fixture has a separate
committed baseline for the primary Typst and LuaLaTeX 7 x 10 profiles. The gate
therefore detects drift within a backend; it does not require two independently
composed backends to have identical pixels.

The locked rootless image converts the resolved pages to 96-DPI grayscale images
with its pinned Poppler version. The checker decodes the PNGs before comparing
exact pixels, so compression differences do not create false changes. A normal
check is read-only with respect to baselines:

```sh
make check-golden-pages
make test-golden-pages
```

On failure, inspect `book/_build/qa/golden-pages/report.md` together with the
current and red-difference images beside it. Only an intentional, reviewed
layout change should run `make update-golden-pages`; review every changed PNG
before committing it. CI runs the normal comparison after rendering the PDF
profiles and never updates baselines.

## Asset rights and release privacy

`book/assets.json` is the canonical rights and distribution contract. Its
collections cover figures and semantic icons directly; imported media and
companion registries retain their domain-specific file lists and inherit
complete rights defaults. Every record identifies its creator and owner,
origin, date, license, permission evidence, modifications, credit wording, and
public-distribution decision. Distributed source bytes are checksum-locked,
and coverage globs reject an asset added outside the registry. Pinned Quarto
runtime libraries and embedded fonts are separate bundles because their
upstream licenses are not book-art ownership claims.

Use the focused gates after adding or replacing an asset:

```sh
make check-asset-rights
make test-asset-rights
make check-release-assets
```

The source gate verifies 39 authored files and scans publishable bytes for
private paths, credential signatures, EXIF/XMP, editor metadata, and unwanted
audio metadata. It rejects unknown licenses, incomplete permission records,
checksum drift, and unregistered files; files marked private are excluded from
the approved distribution set. Metadata-bearing inputs fail instead of being
silently rewritten; strip and review the source deliberately, then update its
checksum.

The rendered gate proves that every copied HTML asset and every renamed EPUB
media object matches an approved source digest. It also verifies preserved
runtime/font license evidence, rejects temporary or private package entries,
scans all package bytes for local paths and secret signatures, checks the title,
author, creator, and producer metadata in all six PDFs, and forbids PDF file
attachments. The gate runs inside `make check-publication` after a complete
render.

## Static-only execution policy

Normal renders, CI, previews, and release builds display code but never execute
manuscript cells. Use a dotted language class for inert highlighted source:

````markdown
```{.python}
print("displayed, not executed")
```
````

Executable cell syntax, selected notebooks, document-level engines, and local
overrides of `execute`, `cache`, or `freeze` are rejected. Only the declarative
Mermaid and Graphviz diagram engines are allowed, offline through pinned
renderers. Notebooks may be registered companion downloads because the
publication pipeline does not open them.

A future opt-in example verifier must have a pinned runtime and dependency
lock, no network, read-only source, disposable output, declared I/O, resource
limits, deterministic state, committed expected results, and cache keys bound
to every input. Cached output is never release evidence by itself.

Run `make check-execution-policy` and `make test-execution-policy`.

## Writing commands

| Command | Role |
|---|---|
| `make check-writing` | Gate spelling and explicit terminology; report subjective prose warnings |
| `make check-spelling` | Run CSpell over canonical authored sources |
| `make check-prose` | Run Vale terminology and style rules |
| `make check-writing-terminology` | Validate dictionaries and generated terminology policy |
| `make check-writing-overrides` | Validate narrow suppressions and their reasons |
| `make test-writing-quality` | Exercise end-to-end positive and negative fixtures |

The inventory includes `README.md`, local `ROADMAP.md`, all authored book
Markdown (including private sources), and `docs/*.md`. It excludes fixtures,
agent instructions, vendored licenses, caches, dependencies, and generated
publication artifacts.

CSpell and Vale exclude parser-owned syntax—code, math, URLs, citations,
cross-reference keys, attributes, shortcodes, and raw backend spans—without
hiding adjacent captions, alternative text, visible labels, or prose.

## Vocabulary and overrides

`config/writing/terminology.json` is the canonical vocabulary registry. Shared
publishing terms live in `config/writing/dictionaries/shared.txt`; book-specific
terms live in `book/dictionaries/accepted.txt`. Rejected terms record a
preferred replacement and reason. After changing the registry, run
`make generate-writing-terminology` and review the complete writing report.

Choose the narrowest exception:

1. improve a shared syntax exclusion for parser-owned text;
2. add recurring vocabulary to the shared or book dictionary;
3. use `cspell:words` for a name intentionally confined to one file;
4. use `cspell:ignore` for one exceptional token;
5. use a Vale match-specific override for one deliberate match; and
6. disable one line/range/rule only when narrower forms cannot express it.

Broad CSpell or Vale suppressions need an adjacent `writing-override` comment
that explains the exception. Blanket Vale disable directives, unbalanced
ranges, stale reasons, repeated one-off tokens, cross-file file vocabulary,
and attempts to hide explicitly rejected terminology are invalid.

CSpell findings and explicit rejected terminology fail. Context-sensitive
grammar, repetition, readability, and house-style findings remain warnings
until fixtures demonstrate a sufficiently low false-positive rate.

## Review workflow

Run the aggregate source and writing gates before rendering. After rendering,
run publication, accessibility, and PDF-profile checks. A zero-warning tool
result is not a substitute for copyediting, subject-matter review, visual page
review, or assistive-technology testing.
