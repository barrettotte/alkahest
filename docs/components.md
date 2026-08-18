# Tables and instructional-block contract

`book/components.qmd` is the acceptance specimen for compact and multipage
tables, margin notes, general callouts, warnings, exercises, solutions,
projects, and laboratory procedures. Authors use Quarto Markdown semantics;
backend-specific markup is not part of the manuscript contract.

## Tables

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

### Multipage tables

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

## Notes and callouts

Use native callouts with a visible title, `appearance="simple"`, and
`icon=false`. Add `.icon-notice` and start the title with the registered
`alk-icon` meaning when a repeated visual category helps the reader. Keep the
equivalent title wording on that same line; it, not the decorative icon or
callout color, carries the category for nonvisual reading. The complete icon
and fallback contract is documented in `docs/icons.md`.

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

## Exercises and solutions

Exercises and solutions use Quarto's built-in theorem-family identifiers:

```markdown
::: {#exr-divider-budget}
## Divider power budget

Calculate the current and resistor powers.
:::

::: {#sol-divider-budget}
## Divider power budget

The series current is ...
:::
```

Reference the exercise with `@exr-divider-budget`. The current Typst backend
numbers a solution but cannot resolve an inline `@sol-...` reference, so prose
refers to the paired exercise and the solution retains its stable `sol-`
identifier for future collection or filtering. Authors never type exercise or
solution numbers.

## Projects and labs

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

## Validation

`make check-publication` verifies the component chapter, semantic table markup,
header cells, column-width declarations, unique callout IDs, generated
references, explicit titles, project/lab classes, and EPUB validity. `make
check-pdf-profiles` checks the visible component labels, long-table continuation
and repeated headers, chapter-aware callout numbering, embedded fonts, and
physical containment in every PDF profile. Visual review starts with the
compact 6 x 9 outputs and a narrow HTML viewport.
