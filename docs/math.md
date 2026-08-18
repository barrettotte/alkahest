# Mathematics and formal reasoning contract

`book/math.qmd` is the acceptance specimen for inline and display mathematics,
aligned systems, cases, matrices, named operators, equation references,
theorems, and proofs. Authors use portable TeX notation inside Quarto Markdown;
backend syntax does not belong in ordinary manuscript files.

## Equations

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

The description states the equation's purpose; it is not a spoken
transcription of every symbol. Quarto currently uses this display metadata in
its Typst path. HTML and EPUB use native MathML, including the original TeX
annotation, so their mathematics remains semantic and does not require a
MathJax service. The source description is retained as the stable input for
later accessibility adapters and audits. Surrounding prose must still define
symbols and explain the mathematical claim.

Use `aligned` when several lines form one numbered relationship, `cases` for a
piecewise definition, and a standard matrix environment such as `bmatrix`.
Split notation before reducing type size if it cannot fit the 6 x 9 print
profile. Reflowable outputs preserve the normal math size and give an unusually
wide display a local horizontal scroll region.

Use `\operatorname{name}` for a named application-specific operator. This
provides correct mathematical spacing without adding a command to a LaTeX or
Typst preamble. A future registry may introduce short authoring commands only
when an operator is common enough to justify a backend-neutral extension.

## Theorems and proofs

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

## Portability boundary

The baseline is TeX math that Pandoc can translate to MathML, Typst, and
LuaLaTeX. Raw MathJax, raw Typst, and raw LaTeX are allowed only as documented,
output-specific fallbacks with a portable alternative. Inline mathematics
cannot carry per-expression descriptions through standard Pandoc Markdown;
introduce every inline symbol and its purpose in adjacent prose.

## Validation

`make check-publication` requires native inline and display MathML, equation
targets, theorem/proof structure, source descriptions, and the absence of a
MathJax dependency in HTML and EPUB. `make check-pdf-profiles` requires the math
chapter, equation and theorem references, embedded Libertinus Math, recto
placement, and physical containment in all six PDFs. Visual review starts with
both 6 x 9 math chapters because they expose width and proof-flow problems
first.
