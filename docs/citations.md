# Citations and bibliography

Alkahest uses one BibTeX registry, one authored `# References` location, and
Pandoc citeproc for HTML, EPUB, Typst, and LuaLaTeX. Keeping CSL processing in
one engine avoids backend-specific interpretations of narrative citations,
locators, sorting, and author suppression.

## House style and override

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
./scripts/quarto render book --profile citation-numeric,html
./scripts/quarto render book --profile citation-numeric,typst
```

`make render-citation-smoke` builds both numeric acceptance editions in
`book/_build/smoke/citations/numeric/`. A future book-specific profile may
select another reviewed, vendored CSL file the same way; do not reference a
mutable remote style during a build.

## Authoring contract

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

## Versioned CSL sources

| Role | Source identity | SHA-256 |
|---|---|---|
| Default author–date | `default.csl` bundled with the locked Pandoc 3.10.0 binary; Chicago Manual of Style 17th edition (author-date) | `91fa1fe9787e737dff0c15d7cf8254c9f2bab4ebb4dccf4553a1f991ebddb7d1` |
| Numeric override | Citation Style Language styles repository, commit `1f32ca7259171b3c35b008ef41613df1215dad75`, `ieee.csl` | `b4c7619fc16c45a31e4cc3271eab94ffe83192d3b4c7fc729470a3b459448de3` |

Both files retain their upstream author, contributor, and rights metadata.
They are licensed under Creative Commons Attribution-ShareAlike 3.0; the
official CSL styles repository is <https://github.com/citation-style-language/styles>.
An intentional style update must review output changes, update the locked hash
in `scripts/check-citations.py`, and rerun the default and numeric acceptance set.

## Acceptance coverage

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
