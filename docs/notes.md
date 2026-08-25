# Semantic notes contract

Ordinary Pandoc named footnotes need no registry and remain native footnotes in
every output. Register a note only when it needs stable repeat policy or
configurable placement as a footnote, chapter endnote, consolidated whole-book
endnote, or sidenote. Do not copy note text into a backend file or create
separate definitions for different outputs.

## Authoring syntax

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

## Placement profiles

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

## Validation and acceptance

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
