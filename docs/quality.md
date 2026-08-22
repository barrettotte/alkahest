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
