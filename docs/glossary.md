# Glossary source and reference contract

`book/glossary.yml` is the single per-book source for glossary definitions and
display forms. Manuscripts use the `alk-term` shortcode and never copy a
definition, spell out an acronym independently, or handwrite a future glossary
anchor.

## Registry schema

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

## Reference syntax

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

## Generated back matter

`book/glossary-backmatter.qmd` owns the unnumbered Glossary division and one
empty `.alkahest-glossary-placeholder` fenced Div. A document filter replaces
that placeholder with every registry definition. Authors never duplicate or
manually order entries in the manuscript.

Entries sort case-insensitively by their displayed singular term, with the
stable ID as a deterministic tie-breaker. Each headword receives an anchor of
the form `glossary-ID`; changing an acronym or visible term therefore does not
break existing links. Headwords include the singular acronym when registered,
and a compact forms line records registered plurals.

## Output behavior

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

## Validation

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
