# Appendix source and grouping contract

Appendices use ordinary Quarto Markdown and native book structure. Authors do
not write backend commands for appendix mode, letters, contents entries, group
pages, or running furniture.

## Canonical full-book structure

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

## Edition registry

`book/editions.json` registers appendices alongside front matter, chapters, and
back matter. Appendix sources record `core`, `online-only`, or `supplemental`
availability and each whole-book structure provides its complete ordered
appendix groups. Standard render commands select `web` for HTML, `epub` for
EPUB, and `print` for PDFs. The preview retains core Appendix A, the web edition
adds online-only D, and the supplemental edition adds its own D instead.

See `docs/content-architecture.md` for the complete structure/edition matrix, staging
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

## Optional sources

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

## Validation and acceptance

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

## Appendix-local numbering

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

## Cross-references and bibliography

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
acceptance coverage are recorded in `docs/citations.md`.

A truly independent supplement with its own bibliography is a separate
publication and should receive its own future edition manifest/configuration.
It is not modeled as an appendix-local exception inside one book.
