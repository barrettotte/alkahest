# Authoring reference

Portable manuscript syntax for headings, references, mathematics, code, figures, and citations.

## Headings, numbering, references, and contents {#doc-headings-and-references}

Alkahest keeps the authored hierarchy deliberately shallow. Structural depth
communicates organization; font size or an unnecessarily long decimal number
must not substitute for reorganizing a chapter.

### Authored heading contract

| Markdown | Book role | Numbered | Listed in contents |
|---|---|---:|---:|
| `#` | Chapter or explicitly unnumbered major division | Yes by default | Yes |
| `##` | Section | Yes | Yes |
| `###` | Subsection | Yes | Yes |
| `####` | Local detail heading | No | No |
| `#####` / `######` | Reserved for semantic components | No | No |

H1 is reserved for the chapter title in chapter files. Authors should not use a
deeper heading merely to obtain smaller text. If H4 is insufficient, split the
material, use a list, or introduce a named semantic component once that syntax
exists.

Prefaces, references, acknowledgements, and similar divisions may use
`.unnumbered`. Add `.unlisted` only when the heading would not help a reader
navigate; the two classes solve different problems.

### Stable identifiers and references

Every structural heading uses one explicit, durable identifier. Ordinary
manuscript headings use lowercase hyphenated `sec-` names, for example:

```markdown
## Clock domains {#sec-clock-domains}

See @sec-clock-domains.
```

Headings that supply a semantic block's visible title inherit the enclosing
theorem, callout, exercise, solution, project, or lab ID instead of declaring a
second anchor. The same stable-ID rule applies to `fig-`, `tbl-`, `eq-`, and
`lst-` objects.
Do not place underscores in IDs, encode a displayed number in an ID, or rename
an ID merely because wording changes.

The checked inventory, glossary/index namespaces, companion-asset IDs,
translation parity, and edition behavior are defined in
[`book-structure.md`](book-structure.md#persistent-identities).

References may cross chapter, part, back-matter, and appendix boundaries in
either direction without different syntax. The renderer supplies the correct
relative link in HTML/EPUB and the internal destination in PDF; authors continue
to write only `@stable-id`.

Quarto supplies the localized prefix, number, link, and punctuation for a
reference. Write `@fig-waveform`, not `Figure @fig-waveform`, because the latter
renders a duplicated label. Use `[-@fig-waveform]` only when surrounding prose
deliberately provides the label.

The English specimen uses unabbreviated locale-provided labels: Chapter,
Section, Figure, Table, Equation, Listing, and Appendix. Figures, tables,
equations, listings, theorems, callouts, exercises, and solutions are numbered
within chapters. Inside an appendix, the appendix letter replaces the chapter
number, so independent first objects render as Figure A.1, Table A.1, Equation
A.1, and so on. Typst surrounds an equation number in a prose reference with
parentheses; that backend-native punctuation does not change its identity or
counter. Changing `lang` should select another locale rather than requiring
manuscript rewrites.

Equation, theorem, and proof authoring conventions are defined separately in
[`authoring.md`](#doc-math). Figure and subfigure conventions are defined in
[`authoring.md`](#doc-figures). Table, callout, exercise, solution, project, and lab
identifiers are defined in [`book-structure.md`](book-structure.md#doc-components).

The document-level and inline language contracts, including the French locale
smoke edition, are defined in [`localization.md`](localization.md#doc-localization).

### Contents contract

All outputs call the main outline “Contents.” It contains parts where supported,
chapters, H2 sections, and H3 subsections. H4 detail headings stay local. The
contents also retains useful unnumbered major divisions such as the preface and
references.

HTML provides the same depth in its page outline and book navigation. EPUB
retains chapters, sections, subsections, and appendices but omits part dividers
because Quarto does not currently support EPUB parts. PDF contents pages start
recto as defined by the page system.

### Backend normalization

Quarto 1.10.18 does not apply one `number-depth` value identically across the
current HTML, Typst, and chapter-based LuaLaTeX paths. The author-facing
configuration uses Markdown depth three. The Typst partial explicitly removes
numbering from H4–H6, and the LuaLaTeX partial caps KOMA-Script at subsection
depth. These are backend adapters, not manuscript conventions.

Automated checks require the H2/H3 numbers, localized reference labels,
contents title, and absence of an H4 decimal number in all six PDFs and both
reflowable outputs.

## Mathematics and formal reasoning contract {#doc-math}

`book/math.qmd` is the acceptance specimen for inline and display mathematics,
aligned systems, cases, matrices, named operators, equation references,
theorems, and proofs. Authors use portable TeX notation inside Quarto Markdown;
backend syntax does not belong in ordinary manuscript files.

### Equations

Use single dollar signs for an expression that belongs grammatically to a
sentence. Use a display for a derivation, structured notation, or any equation
that readers need to reference. Referenceable displays receive a durable
`eq-` identifier and a concise description:

```markdown
$$
E = mc^2
$$ {#eq-mass-energy alt="Mass-energy equivalence"}

As @eq-mass-energy shows, ...
```

Inline expressions use the same natural-language contract through an annotated
span:

```markdown
[$V = I R$]{.alkahest-math-alt alt="voltage equals current times resistance"}
```

The description states the equation's purpose; it is not necessarily a spoken
transcription of every symbol. Quarto uses display metadata in its Typst path;
`filters/math-alt.lua` supplies the equivalent `math.equation` alternative for
annotated inline expressions. HTML and EPUB keep native MathML, including the
original TeX annotation, while LuaLaTeX keeps tagged native math. Surrounding
prose must still define symbols and explain the mathematical claim.

Use `aligned` when several lines form one numbered relationship, `cases` for a
piecewise definition, and a standard matrix environment such as `bmatrix`.
Split notation before reducing type size if it cannot fit the 6 x 9 print
profile. Reflowable outputs preserve the normal math size and give an unusually
wide display a local horizontal scroll region.

Use `\operatorname{name}` for a named application-specific operator. This
provides correct mathematical spacing without adding a command to a LaTeX or
Typst preamble. A future registry may introduce short authoring commands only
when an operator is common enough to justify a backend-neutral extension.

### Theorems and proofs

Use Quarto's reserved `thm-` identifier on a fenced Div. Its first heading is
the visible theorem name:

```markdown
::: {#thm-sample}
## Sample result

The statement belongs here.
:::

::: {.proof}
The proof belongs here.
:::
```

Write `@thm-sample` in prose and let the renderer supply the localized theorem
label and chapter-aware number. A proof is unnumbered, begins with a generated
proof label, and stays directly after the claim it establishes. Do not type a
theorem number, `Theorem`, `Proof`, or an end-of-proof symbol into manuscript
prose. The current backends use their native theorem systems, so exact borders,
italics, and proof-end conventions may differ while structure and reading order
remain equivalent.

### Portability boundary

The baseline is TeX math that Pandoc can translate to MathML, Typst, and
LuaLaTeX. Raw MathJax, raw Typst, and raw LaTeX are allowed only as documented,
output-specific fallbacks with a portable alternative. The
`.alkahest-math-alt` span is the one template extension to ordinary inline
math; it unwraps to native math outside Typst and remains readable source.

### Validation

The source-integrity check rejects inline or display math without a nonempty
alternative. `make check-publication` requires native inline and display MathML, equation
targets, theorem/proof structure, source descriptions, and the absence of a
MathJax dependency in HTML and EPUB. `make check-pdf-profiles` requires the math
chapter, equation and theorem references, embedded Libertinus Math, recto
placement, and physical containment in all six PDFs. Visual review starts with
both 6 x 9 math chapters because they expose width and proof-flow problems
first.

## Code-block contract {#doc-code-blocks}

`book/code-blocks.qmd` is the acceptance specimen for source listings,
filenames, line numbers, callouts, long lines, patches, terminal transcripts,
and source/output pairs. These rules apply to every book using the template.

### Authoring syntax

Use a fenced code block with a language class. Line numbers are opt-in because
they add visual noise and are useful mainly when prose discusses a stable
listing:

````markdown
```{.python code-line-numbers="true"}
print("hello")
```
````

Put a filename in a semantic container so it remains visible in all four
publication paths without becoming part of copied source:

````markdown
::: {.code-with-filename}
[`example.py`]{.code-with-filename-file}

```{.python}
print("hello")
```
:::
````

Use Quarto's numbered line-callout syntax for a small number of explanations.
HTML provides interactive highlighting; EPUB and both PDF backends retain a
labeled prose fallback. Essential meaning must remain in the explanation, not
in color or marker position alone.

Use `diff` for patches and `console` for transcripts. A transcript includes a
visible prompt and output in reading order. Provide a prompt-free command
separately when readers are expected to copy it directly.

### Overflow policy

- Interactive HTML preserves source columns and scrolls horizontally.
- EPUB and browser print styles wrap at spaces and, when necessary, inside an
  unbroken token.
- LuaLaTeX uses the pinned `fvextra` package for continuation-safe wrapping.
- Typst makes highlighted token grapheme clusters breakable while preserving
  explicit source-line boundaries.

Wrapping is presentation only; it must not insert characters into copied
source or hide the beginning or end of a line. Authors should still prefer
readable source and reserve very long lines for values that must remain whole,
such as URLs or hashes.

### Executable examples

Present an executable example as a static source block followed immediately by
a visibly labeled expected-output block. Normal, CI, preview, and release
builds never run manuscript code. Use dotted language classes such as
`{.python}`; executable cells such as `{python}` and per-document execution
settings fail validation.

The only brace-style cells admitted by the machine policy are declarative
`{mermaid}` and Graphviz `{dot}` diagrams. Diagram renderers are reviewed
separately and do not imply permission to execute a general-purpose language.

`docs/quality.md` defines the trust boundary and the requirements for
any future, separate opt-in verifier. Publication caching and frozen results
are disabled. A verifier would require a pinned offline environment, locked
dependencies, read-only source, disposable output, resource limits, and drift
checks before it could be enabled.

### Validation

`make check-execution-policy` first rejects executable cells, engine or policy
overrides, and executable notebook chapters. `make check-publication` checks
the HTML/EPUB filename, numbering, annotation,
overflow, patch, terminal, and output structures. `make check-pdf-profiles`
requires the same content in all six PDFs and rejects extracted word boxes that
escape the physical page. Visual review starts with both 6 x 9 code chapters.

## Figure and visual-asset contract {#doc-figures}

`book/figures.qmd` is the acceptance specimen for standalone figures,
subfigures, captions, alternative descriptions, source credit, float behavior,
full-width art, and medium-specific variants. Figure inputs are versioned
assets; generated assets must eventually carry the same provenance record.

### A complete figure

Every substantive figure has four distinct pieces:

1. A durable `fig-` identifier that names the idea rather than a filename or
   displayed number.
2. A caption that states the figure's relevance to the argument.
3. Explicit `fig-alt` text that describes the visual evidence a reader needs.
4. Visible source/license credit plus a matching entry in the asset registry.

Use a figure Div when the caption needs structured source credit:

```markdown
::: {#fig-signal-path}

![](figures/signal-path.svg){fig-alt="Three labeled stages connected by arrows." width="100%"}

A signal moves from measurement to decision.
[Source: original diagram, CC0 1.0.]{.figure-source}
:::

See @fig-signal-path.
```

Alternative text is not the caption repeated. It describes relationships,
direction, scale, notable contrast, or other visual evidence needed to reach
the same conclusion. It should not repeat every visible label, begin with
“image of,” or depend on color names when labels and shapes convey the meaning.

### Panels and subfigures

Use a panel only for members that support one comparison. Give every member an
ID, subcaption, and alternative description, then give the enclosing panel its
own ID and shared caption:

```markdown
::: {#fig-comparison layout-ncol="2"}

![Before](figures/before.svg){#fig-before fig-alt="..."}

![After](figures/after.svg){#fig-after fig-alt="..."}

Before and after the change. [Source: ...]{.figure-source}
:::
```

The panel can be cited as `@fig-comparison`; members can be cited independently
as `@fig-before` and `@fig-after`. Empty lines are required between members so
Pandoc treats them as separate blocks.

### Full-width and medium-specific variants

Apply `.figure-full-width` to an enclosing figure Div. HTML may expand it a
small amount beyond the prose measure without entering the navigation columns;
EPUB and the one-column PDF profiles use the available reader or live-page
width. “Full-width” never means extending to the physical trim edge.

When screen and print genuinely need different rendering, keep one outer
figure and select equivalent assets inside it:

```markdown
::: {#fig-system .figure-full-width}

:::: {.content-visible when-format="html"}
![](figures/system-screen.svg){fig-alt="..." width="100%"}
::::

:::: {.content-visible unless-format="html"}
![](figures/system-print.svg){fig-alt="..." width="100%"}
::::

One caption and source line for both presentations.
:::
```

Quarto's `html` format alias includes EPUB, so the example selects the screen
asset for both reflowable editions and the print asset for Typst/LuaLaTeX. The
variants must preserve meaning, labels, reading order, view box, ID, caption,
and alternative description. A materially different claim needs a separate
figure and reference.

### Placement and asset policy

Author a figure at the document's top level, near its first reference. HTML and
EPUB preserve reading order. Typst uses native book-figure placement;
LuaLaTeX's profile-level `htbp` policy permits here, top, bottom, and float-page
positions. Exact page placement is deliberately not stable, so prose must not
say “above,” “below,” or name a page.

Prefer SVG for diagrams, plots, and line art. The locked `rsvg-convert` tool
turns SVG inputs into vector PDF assets for LuaLaTeX; Typst consumes SVG
directly. Use raster inputs only for inherently photographic or textured
subjects. `make check-pdf-preflight` rejects continuous-tone raster objects
below 300 effective pixels per inch, one-bit objects below 600, and undeclared
color models or output intents. The current specimen's PDF artwork remains
vector-only; invalid raster reports are covered by focused fixtures.

Graphs, charts, circuits, chemistry, computing, physics, and rich media share
the deterministic derivative, accessibility, provenance, and review contract
in [`media-workflows.md`](media-workflows.md#doc-media-workflows).

`book/assets.json` is the distribution and rights registry;
`book/figures/README.md` retains detailed workflow provenance. The registry
records creator/owner, origin, date, license or permission evidence,
modification history, credit wording, public-distribution status, and exact
derivative checksums. Captions cannot be baked into image pixels. Run `make
check-asset-rights` after changing figure bytes or provenance.

Quarto 1.10 duplicates `fig-alt` onto the generated figure wrapper as well as
the image. HTML/EPUB permit `alt` only on the image, so the small post-render
filter in `book/filters/strip-invalid-alt.lua` removes the invalid wrapper copy
without changing the image alternative. Delete the adapter when an upstream
render no longer produces the duplicate attribute and the regression check
still passes.

### Validation

`make check-publication` requires stable IDs, panel relationships, explicit alt
text, source spans, full-width semantics, and only the screen variant in HTML
and EPUB. EPUBCheck validates the packaged SVG resources. `make
check-pdf-profiles` requires the print variant, captions, references, source
credit, recto chapter start, embedded fonts, and physical text containment in
all six PDFs, and includes the artifact preflight. `make check-circuits` also
performs an offline regeneration and byte comparison, then checks SVG
accessibility, labels, vector geometry, and
self-containment. Visual review begins with the 6 x 9 panels, full-width
figure, voltage-divider labels and symbols, and reaction structures at the
smallest trim. `make check-chemistry` applies the equivalent deterministic,
accessible, self-contained SVG checks to the selected reaction workflow.
`make check-computing-diagrams` additionally validates bit counts, address
coverage, signal spans, node/edge references, visible labels, and deterministic
portable SVG derivatives for the computing fixtures.
`make check-physics-diagrams` validates the physics unit registry, displayed
significant figures, vector and field relationships, provenance, and two
deterministic accessible SVG derivatives.
`make check-rich-media` validates media registry coverage, checksums,
accessibility behavior, rights, transcripts, captions, and deterministic
fallbacks. Rendered checks require native enhancements only in HTML and the
complete static lesson in EPUB and PDF.

## Citations and bibliography {#doc-citations}

Alkahest uses one BibTeX registry, one authored `# References` location, and
Pandoc citeproc for HTML, EPUB, Typst, and LuaLaTeX. Keeping CSL processing in
one engine avoids backend-specific interpretations of narrative citations,
locators, sorting, and author suppression.

### House style and override

The default is Chicago Manual of Style 17th edition, author–date. It is a good
general house style for the template's history, computing, and science books:
readers see author and year without leaving the sentence, while the central
bibliography retains complete publication data.

The default is declared once in `book/_quarto.yml`:

```yaml
bibliography: references.bib
csl: citations/chicago-author-date.csl
```

Books that require numbered engineering citations compose the
`citation-numeric` profile with an output profile:

```console
./scripts/quarto.sh render book --profile citation-numeric,html
./scripts/quarto.sh render book --profile citation-numeric,typst
```

`make render-citation-smoke` builds both numeric acceptance editions in
`book/_build/smoke/citations/numeric/`. A future book-specific profile may
select another reviewed, vendored CSL file the same way; do not reference a
mutable remote style during a build.

### Authoring contract

Use stable, descriptive citekeys in `book/references.bib` and normal Pandoc
citation syntax:

```markdown
Parenthetical [@turing1936].
Narrative @turing1936.
Locator [@turing1936, pp. 230–231].
Multiple sources [@turing1936; @knuth1984].
Author named in prose: Turing [-@turing1936].
```

Place deliberately included but uncited background works in project-level
`nocite` metadata. List keys explicitly instead of using `@*`; this keeps every
central bibliography entry reviewable. Appendices cite the same registry and
must not declare local bibliographies.

`make check-citations` rejects duplicate keys, missing citation or `nocite`
keys, unused records, modified style files, backend configuration drift, and a
missing shared references division. It ignores fenced code, inline code, URLs,
email addresses, and recognized Quarto cross-reference prefixes. Use
`make test-citations` to exercise its valid and invalid fixtures.

### Versioned CSL sources

| Role | Source identity | SHA-256 |
|---|---|---|
| Default author–date | `default.csl` bundled with the locked Pandoc 3.10.0 binary; Chicago Manual of Style 17th edition (author-date) | `91fa1fe9787e737dff0c15d7cf8254c9f2bab4ebb4dccf4553a1f991ebddb7d1` |
| Numeric override | Citation Style Language styles repository, commit `1f32ca7259171b3c35b008ef41613df1215dad75`, `ieee.csl` | `b4c7619fc16c45a31e4cc3271eab94ffe83192d3b4c7fc729470a3b459448de3` |

Both files retain their upstream author, contributor, and rights metadata.
They are licensed under Creative Commons Attribution-ShareAlike 3.0; the
official CSL styles repository is <https://github.com/citation-style-language/styles>.
An intentional style update must review output changes, update the locked hash
in `alkahest.checks.citations`, and rerun the default and numeric acceptance set.

### Acceptance coverage

The reference chapter exercises parenthetical and narrative calls, page
locators, multiple sources, author suppression, repeated sources, and an
explicitly uncited work. Publication checks require equivalent citation
meaning and bibliography ordering across default HTML, EPUB, Typst, and
LuaLaTeX outputs, then repeat the contract for numeric HTML and Typst smoke
editions. DOI links remain live in HTML; print output retains the DOI text.

The pinned EPUB writer preserves citekey identity and the central anchored
bibliography entry but does not currently link every inline citation back to
that entry. This is the one accepted navigation fallback; citation text and
bibliography content remain equivalent.
