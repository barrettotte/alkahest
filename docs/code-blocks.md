# Code-block contract

`book/code-blocks.qmd` is the acceptance specimen for source listings,
filenames, line numbers, callouts, long lines, patches, terminal transcripts,
and source/output pairs. These rules apply to every book using the template.

## Authoring syntax

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

## Overflow policy

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

## Executable examples

Present an executable example as a static source block followed immediately by
a visibly labeled expected-output block. Normal, CI, preview, and release
builds never run manuscript code. Use dotted language classes such as
`{.python}`; executable cells such as `{python}` and per-document execution
settings fail validation.

The only brace-style cells admitted by the machine policy are declarative
`{mermaid}` and Graphviz `{dot}` diagrams. Diagram renderers are reviewed
separately and do not imply permission to execute a general-purpose language.

`docs/execution-policy.md` defines the trust boundary and the requirements for
any future, separate opt-in verifier. Publication caching and frozen results
are disabled. A verifier would require a pinned offline environment, locked
dependencies, read-only source, disposable output, resource limits, and drift
checks before it could be enabled.

## Validation

`make check-execution-policy` first rejects executable cells, engine or policy
overrides, and executable notebook chapters. `make check-publication` checks
the HTML/EPUB filename, numbering, annotation,
overflow, patch, terminal, and output structures. `make check-pdf-profiles`
requires the same content in all six PDFs and rejects extracted word boxes that
escape the physical page. Visual review starts with both 6 x 9 code chapters.
