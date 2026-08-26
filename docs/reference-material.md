# Reference material

Semantic icons, glossary terms, indexes, and notes that generate consistent back matter across formats.

## Semantic icon contract {#doc-icons}

`book/icons.qmd` is the acceptance specimen for reusable inline markers.
Authors invoke the repository-owned `alk-icon` shortcode; they do not choose an
SVG filename, icon font, Unicode character, or backend command.

### Authoring

Use the canonical semantic name followed immediately by visible prose that
states the same meaning:

```markdown
{{< alk-icon equipment >}} **Equipment required.** Gather the listed tools.
{{< alk-icon warning >}} **Warning.** Check the stated limits.
```

The initial canonical names are `equipment`, `warning`, `danger`, `idea`,
`experiment`, and `optional-material`. The central registry at
`book/_extensions/alkahest-icons/registry.lua` records each stable name,
default label, asset, and accepted aliases. For example, `stop` resolves to
`danger`; generated markup always records the canonical identity.

Use a `label` override only when the default fallback label is too general:

```markdown
{{< alk-icon stop label="Stop; stored energy remains" >}} **Stop.** Remove power.
```

The adjacent visible text remains mandatory editorial content and must begin on
the same source line as the shortcode. The registry label must be short,
specific, and nonempty; it supports validation, conversion, and image
alternatives but does not replace the surrounding explanation.

### Registry and assets

Add a new meaning only when it will recur across books and is not merely a
synonym for an existing entry. A registry addition has:

1. a lowercase, hyphenated canonical name;
2. a concise default label;
3. an original or license-compatible monochrome SVG in `book/icons`;
4. only necessary, nonconflicting aliases.

The initial SVGs are original Alkahest assets under the repository's MIT
license. They share a 24 by 24 view box, contain no embedded text, use the
book's ink color, and remain recognizable without color. SVG filenames are
implementation details and may change without rewriting manuscripts.

### Output behavior

The shortcode emits ordinary Pandoc image and span nodes rather than raw
backend markup. HTML and EPUB retain the canonical `data-icon`, registry label,
image alternative, and semantic classes, but mark the complete icon span
`aria-hidden="true"`. Because equivalent visible wording is mandatory, this
keeps the icon decorative in the accessibility tree and avoids announcing the
same meaning twice. Typst consumes the canonical SVG directly. Before
rendering, `python3 -m alkahest.staging icons` deterministically derives a PDF vector from
each SVG for LuaLaTeX, whose callout-title path does not run Quarto's normal SVG
conversion. The derivative remains an ignored build input, not a second
artwork source. Both PDF backends use a one-em inline size. Adjacent visible
prose carries the meaning in PDF text extraction and when images are
unavailable.

### Side blurbs and notice blocks

Use the same shortcode at the start of a native callout title and add the
`.icon-notice` class to the block. Keep Quarto's unrelated built-in icon off so
the output never displays two symbols:

```markdown
::: {.callout-warning .icon-notice appearance="simple" icon=false}
## {{< alk-icon warning >}} Disconnect power before changing leads

De-energize the fixture and verify that stored energy is gone.
:::
```

The same pattern applies to `.margin-note`, project, lab, and optional-material
blocks. Notice-title adapters use a slightly smaller 0.95-em icon, a stable
trailing gap, and a tuned baseline while retaining the original one-em inline
behavior in prose. EPUB keeps side blurbs inline; roomy HTML may float a
`.margin-note`, and compact PDF profiles keep every notice in source order.

Quarto callout color remains a secondary category cue. Every icon asset is
already monochrome, so grayscale and one-color output use the same repository
vector rather than an output-specific substitute.

### Narrow-layout acceptance

`book/icons.qmd` contains an 18-rem accessibility specimen with a deliberately
long warning. It exercises the approximate measure of a phone or narrow EPUB
reader in every HTML build. At viewports up to 480 pixels, notice-title text may
wrap while the icon retains its fixed inline size. The 6 x 9 profile is the
corresponding compact print acceptance target for both PDF engines; text must
remain inside the physical page even if image alternatives are unavailable.

### Validation

`make check-icons` rejects missing required entries, duplicate names or
aliases, unsafe or missing asset paths, nonconforming SVGs, unknown manuscript
calls, empty labels, unexpected arguments, icon-only calls, and malformed
`.icon-notice` titles. It runs before every Quarto render and explicitly in
`make ci`. Publication validators additionally check that every canonical icon,
fallback label, SVG, decorative accessibility state, and adjacent visible text
survives HTML and EPUB; narrow CSS and the visible acceptance specimen must
survive every PDF profile.

## Glossary source and reference contract {#doc-glossary}

`book/glossary.yml` is the single per-book source for glossary definitions and
display forms. Manuscripts use the `alk-term` shortcode and never copy a
definition, spell out an acronym independently, or handwrite a future glossary
anchor.

### Registry schema

The registry has a version and a `terms` mapping keyed by stable lowercase,
hyphenated IDs:

```yaml
version: 1
lang: en-US
terms:
  central-processing-unit:
    term: central processing unit
    plural: central processing units
    acronym: CPU
    acronym-plural: CPUs
    aliases:
      - cpu
    definition: >-
      The hardware unit that fetches, decodes, and executes instructions.
```

`lang` is required and uses a BCP 47 language tag. It describes the registry
content rather than the surrounding edition: term references and generated
entries retain `lang="en-US"`, for example, when the reference book is rendered
with the French interface smoke profile. This gives assistive technology,
hyphenation, and shaping the correct local language scope while a book is being
translated incrementally.

`term` and `definition` are required. `plural`, `acronym`,
`acronym-plural`, and `aliases` are optional, but a requested manuscript form
must have the corresponding data. Definitions use folded YAML text so they
remain readable and diffable. They may contain one paragraph of inline
Markdown; block structures belong in ordinary book content rather than a
compact glossary entry.

IDs are persistent content identity. Rename display wording without changing
an ID; add an old or familiar spelling as an alias when authors need it. An
alias selects an entry but never becomes the generated canonical identity.

### Reference syntax

Use a canonical ID or alias as the first positional argument:

```markdown
{{< alk-term central-processing-unit form=first >}}
{{< alk-term cpu form=acronym >}}
{{< alk-term matrix form=plural >}}
{{< alk-term cpu form=first case=sentence >}}
{{< alk-term matrix link=false >}}
```

The supported forms are:

| Form | Output source |
|:-----|:--------------|
| `term` | Required singular `term`; this is the default |
| `plural` | Registered `plural` |
| `acronym` | Registered `acronym` |
| `acronym-plural` | Registered `acronym-plural` |
| `first` | `term (acronym)` when an acronym exists, otherwise `term` |
| `first-plural` | `plural (acronym-plural)` when both exist, otherwise `plural` |

`case=as-written` is the default. Use `case=sentence` when a registered
lowercase term starts a sentence; the filter uppercases its first Unicode
character without changing the stored term. References link automatically in
HTML and EPUB. `link=false` is the explicit escape hatch for a context that
must retain the semantic term span and visible wording without navigation.

`first` is explicit rather than inferred. Quarto renders split HTML chapters
independently, while PDF editions assemble a complete book; hidden first-use
state would therefore produce output-dependent wording. The author places one
explicit first-use marker at the editorially correct surviving location, and
edition work can later validate or replace that marker deliberately.

### Generated back matter

`book/glossary-backmatter.qmd` owns the unnumbered Glossary division and one
empty `.alkahest-glossary-placeholder` fenced Div. A document filter replaces
that placeholder with every registry definition. Authors never duplicate or
manually order entries in the manuscript.

Entries sort case-insensitively by their displayed singular term, with the
stable ID as a deterministic tie-breaker. Each headword receives an anchor of
the form `glossary-ID`; changing an acronym or visible term therefore does not
break existing links. Headwords include the singular acronym when registered,
and a compact forms line records registered plurals.

### Output behavior

The term shortcode always emits a Pandoc span with visible text,
`glossary-term`, the canonical `data-glossary-id`, `data-glossary-form`, case
and link policies, and the registry language. HTML and EPUB wrap linked spans
in a link to the generated entry and put the definition in the link's `title`
as optional hover text. The visible term and linked glossary remain the
accessible path; the tooltip never carries unique meaning. Generated entries
use stable labelled headwords and `role="definition"` so their accessible name
does not depend on presentation or hover behavior.

Typst and LuaLaTeX keep the prose visually quiet and place a stable label at
each explicit first-use marker. Generated print entries use their engine's page
counter/reference mechanism to show `First use: p. N`, so numbers update after
reflow and are never stored in YAML. All print occurrences remain visible,
unstyled semantic text rather than depending on hyperlink support. Both
engines use the same headword, definition, forms, and page-reference hierarchy
even though their exact page breaks remain independent.

### Validation

`make check-glossary` validates the registry version and structure, required
definitions, unique display terms, unique canonical IDs and aliases, legal
shortcode arguments, case and link values, form availability, exactly one
explicit first-use marker for every referenced entry, one generated-glossary
placeholder, a valid registry language, and no unused entries. It runs before
every render and directly in CI.

`make test-glossary` copies the small two-chapter fixture under
`tests/glossary/base` into isolated temporary books. The valid fixture proves a
first use in one chapter and later references in another. Eleven mutations
must be rejected: duplicate display terms, duplicate aliases, undefined and
unused terms, duplicate and missing first uses, invalid case and link values,
unavailable forms, invalid language tags, and a missing generated placeholder.

Publication validators require every acceptance form and canonical identity in
HTML and EPUB, as well as generated anchors, default links, explicit unlinked
fallbacks, sentence casing, tooltips, language scope, and definition semantics.
The locale smoke edition proves English glossary content remains scoped inside
a French document. All PDF profiles require visible sentence-cased and later
references, definitions, four resolved page references, recto placement, and
physical containment.

## Subject and person index contract {#doc-indexes}

`book/index.yml` is the single editorial registry for subject and person index
identity, display text, sorting, nesting, aliases, locators, ranges, and
`see`/`see also` relationships. Manuscript source places invisible stable
markers with the `alk-index` shortcode. Authors never type page numbers,
backend index commands, or a second HTML-only index.

### Registry schema

The registry begins with a schema version and the language of its displayed
terms:

```yaml
version: 1
lang: en-US
entries:
  computation:
    term: computation
    kind: subject
    aliases:
      - computing
    locations:
      - reference.qmd#abstract-model
    see-also:
      - turing-alan
  instruction-set-architecture:
    term: instruction set architecture
    kind: subject
    parent: computation
    locations:
      - glossary.qmd#isa-contract
  turing-alan:
    term: Turing, Alan
    kind: person
    locations:
      - reference.qmd#turing-citation
```

Canonical IDs and aliases are lowercase hyphenated names. IDs are persistent
content identity; changing visible wording does not require changing markers.
`term` is the displayed headword. Person terms use the desired index form, such
as `Turing, Alan`. The optional `sort` field supplies an ASCII collation key
when display order should differ from a case-insensitive term sort.

`kind` is `subject` or `person`, producing separate Subject index and Name index
groups. `parent` creates nested entries and may point only to an entry of the
same kind. Nesting may be deeper than one level; validation rejects every
parent cycle. A child retains its own stable identity and locators rather than
encoding hierarchy into punctuation-heavy source syntax.

`locations` contains point declarations in `SOURCE#MARKER` form. `ranges` uses
the same form but declares a paired start/end range. Paths are project-relative
canonical `.qmd` sources; marker names are stable within their entry. Keeping
these declarations in the registry makes added, removed, or moved references
an explicit editorial change and gives the back-matter generator the targets
it needs without scanning rendered files.

Aliases select canonical identity from prose; they do not create another
headword. `see` creates a redirect entry with no locator, range, or `see-also`
data. `see-also` is a list of related canonical entries and may accompany
ordinary locators. Targets are generated links in reflowable editions and
internal links in print.

### Manuscript markers

A point marker uses a canonical ID or alias plus the declared stable marker:

```markdown
An abstract model of computation.{{< alk-index computing id=abstract-model >}}
```

The alias `computing` resolves to the canonical `computation` entry. It is
retained as `data-index-requested` in HTML/EPUB for acceptance diagnostics,
while every generated anchor uses canonical identity.

A range repeats one declared marker ID at its boundaries:

```markdown
{{< alk-index book-design id=reference-tour range=start >}}

...the indexed discussion...

{{< alk-index book-design id=reference-tour range=end >}}
```

Every range has exactly one start and one end in its declared source. Ranges do
not cross source files, because HTML and EPUB need both endpoints in one split
document and a later edition may include only one of two chapters. Use separate
point locators when a concept recurs across chapters.

Markers add no visible prose and belong immediately after the indexed phrase or
on their own line at a range boundary. They are forbidden inside code,
attributes, and URLs. Raw `\index{...}` and similar backend commands are also
forbidden: they cannot create equivalent web, EPUB, Typst, and editorial output.

### Generated output

`book/index-backmatter.qmd` owns the unnumbered Index division and exactly one
empty `.alkahest-index-placeholder`. The filter replaces it with sorted Subject
index and Name index groups, then recursively emits child entries.

HTML and EPUB point locators are numbered links to stable source anchors.
Ranges expose separate linked start and end anchors with an en dash. Relationship
links remain within the generated index. EPUB packaging rewrites the source
paths to its generated chapter filenames, so the authored registry never stores
fragile `chNNN.xhtml` names.

Typst and LuaLaTeX attach the same stable labels at manuscript markers and
resolve their logical page counters in the generated index. Point occurrences
produce page lists, paired markers produce page ranges, and relation links point
to generated headwords. Page numbers are never cached in YAML. The specimen
deliberately spans a range across two pages in both engines and requires every
supported trim/review profile to resolve it without `??` placeholders.

Quarto documents a LaTeX-only `makeidx` route for PDF books, but that source
syntax is intentionally insufficient for the shared output contract here. The
custom filter follows Quarto's supported book/custom-format extension boundary
and uses Typst's documented location-aware page counters for the second PDF
backend: [Quarto book indexes](https://quarto.org/docs/books/book-structure.html#creating-an-index),
[Quarto custom Typst formats](https://quarto.org/docs/output-formats/typst-custom.html),
and [Typst counters](https://typst.app/docs/reference/introspection/counter/).

### Validation and acceptance

`make check-index` validates schema version and language, canonical names and
aliases, kinds, optional sort keys, unique declarations, existing sources,
parent compatibility and cycles, redirects, `see-also` targets, declared point
markers, paired ranges, shortcode syntax, backend-command exclusion, and the
single generated placeholder. It runs before every render and directly in CI.

`make test-index` copies `tests/index/base` and proves a valid cross-file,
nested, aliased registry passes while fifteen mutations fail: alias collision,
unknown calls, missing/duplicate/undeclared markers, broken ranges, missing and
cyclic parents, cross-kind nesting, invalid redirects, invalid language, missing
or duplicate placeholders, and a raw LaTeX index command.

`make check-rendered-index` link-checks the HTML book, verifies generated groups,
nested entries, aliases, points, ranges, and relationship targets in HTML and
EPUB, then requires numeric two-location entries and a strictly increasing
range in both primary PDFs. The all-profile PDF validator repeats the resolved
page/range, recto opener, font, and physical-containment contract for 7 x 10,
6 x 9, and Letter output from both engines. EPUBCheck separately validates the
packaged links and document structure.

Edition filtering must never leave an index target dangling. The current
registry points only into sources retained by all standard editions, and every
HTML edition is link-checked. When conditional edition manifests are
generalized, their index policy must filter entries and locators from the same
manifest rather than weakening this invariant.

## Semantic notes contract {#doc-notes}

Ordinary Pandoc named footnotes need no registry and remain native footnotes in
every output. Register a note only when it needs stable repeat policy or
configurable placement as a footnote, chapter endnote, consolidated whole-book
endnote, or sidenote. Do not copy note text into a backend file or create
separate definitions for different outputs.

### Authoring syntax

A simple named footnote uses ordinary Markdown:

```markdown
This statement needs a short note.[^source-note]

[^source-note]: Keep the source note specific enough to verify.
```

The notes filter leaves definitions without an `.alkahest-note` marker alone.
Use the semantic form below only for a note registered in `notes.yml`.

Reference a stable lowercase, hyphenated note ID with standard named-note
syntax. Keep its one definition in the same source file and begin the
definition with the matching semantic marker:

```markdown
Page geometry is an edition concern.[^page-geometry]

A later paragraph can reuse it.[^page-geometry]

[^page-geometry]: [A useful note remains meaningful in every placement.]{#note-page-geometry .alkahest-note}
```

The marker is structural and is removed from visible output. The definition
may contain normal portable Markdown and may continue as an indented
multi-paragraph named note. Prefer prose, emphasis, links, and citations that
all target writers understand; do not put backend-specific LaTeX or Typst in a
note. Inline `^[...]` notes are forbidden because they have no persistent ID
for repeat policy, stable links, or validation.

`book/notes.yml` records the editorial contract separately from the prose:

```yaml
version: 1
order:
  - page-geometry
notes:
  page-geometry:
    source: reference.qmd
    repeat: reuse
    references: 2
```

`order` is the stable whole-book note order. Every ordered ID appears exactly
once under `notes`, has exactly one marked definition, and is referenced only
from its declared `source`. `references` is an intentional count: adding or
removing a call requires an explicit registry review rather than silently
changing the apparatus.

Use `repeat: once` for a note that must have exactly one call. Use
`repeat: reuse` when multiple passages deliberately point to the same content.
Native spatial placements produce an independently navigable occurrence at
each call. The whole-book placement instead gives every call the same note
number, emits the content once, and provides a backlink to every occurrence.

### Placement profiles

The default in `book/_quarto.yml` is `footnotes`. It leaves the semantic note
as Pandoc's native `Note`: print backends place it at the foot of the page,
HTML exposes its accessible reference/endnote navigation, and EPUB retains the
reader-compatible `noteref`/`footnote` structure. HTML emits explicit return
links; EPUB delegates return navigation to the reading system through those
standard semantic roles. This is the portability baseline.

Three composable smoke profiles exercise the alternatives:

| Placement | Profile | Behavior |
|:--|:--|:--|
| Chapter endnotes | `notes-chapter` | Native notes collected at the end of each split chapter document with native backlinks |
| Whole-book endnotes | `notes-book` | One generated `Notes` apparatus in shared back matter, stable global numbering, and one backlink per occurrence |
| Sidenotes | `notes-sidenote` | HTML notes in the margin column |
| Typst sidenotes | `notes-sidenote-typst` | A dedicated 7 x 10 Typst profile with a measured outer note column |

Run `make render-notes-smoke` to render all four alternatives and
`make check-rendered-notes` to verify their identities, repeat behavior,
backlinks, local links, content, and physical PDF containment. The dedicated
Typst profile is intentionally complete: Quarto treats format declarations
from composed profiles as separate render targets rather than merging them.
LuaLaTeX and EPUB continue to use the native-footnote fallback until a future
profile receives equivalent format-specific acceptance coverage.

The whole-book apparatus is inserted at the single empty
`.alkahest-book-notes-placeholder` in `book/glossary-backmatter.qmd`. Other
placements remove that placeholder. Its generated anchors are
`book-note-ID`; occurrence anchors are `note-ref-ID-N`. Authors never write
those destinations or visible note numbers.

This model builds on [Pandoc named notes](https://pandoc.org/demo/example2.html)
and Quarto's documented
[`reference-location` placements](https://quarto.org/docs/authoring/article-layout.html#reference-location).

### Validation and acceptance

`make check-notes` validates the reference specimen's registered semantic-note
contract: malformed registries, unsupported source paths or repeat policies,
missing and duplicate definitions, unknown calls, count drift, cross-source
calls, incorrect semantic markers, inline notes, and missing or duplicate
apparatus placeholders. It runs before every reference-specimen render and in
CI. Generated author books may also use unregistered native named footnotes.

`make test-notes` copies the minimal fixture under `tests/notes/base` and proves
the valid contract passes while twelve mutations fail. Rendered smoke checks
then prove behavior the source validator cannot: native chapter backlinks,
two independently identified native repeat occurrences, consolidated global
numbering, multiple whole-book backlinks, cross-chapter navigation, HTML margin
placement, a retained Typst show rule and note source, readable PDF text, and
no positioned word outside trim.

Presentation may differ by output, but note identity and meaning may not. If an
edition cannot support a requested spatial placement accessibly, it falls back
to native footnotes rather than dropping the note, baking a number into prose,
or requiring a second copy of its content.
