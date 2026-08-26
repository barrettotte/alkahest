# Subject and person index contract

`book/index.yml` is the single editorial registry for subject and person index
identity, display text, sorting, nesting, aliases, locators, ranges, and
`see`/`see also` relationships. Manuscript source places invisible stable
markers with the `alk-index` shortcode. Authors never type page numbers,
backend index commands, or a second HTML-only index.

## Registry schema

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

## Manuscript markers

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

## Generated output

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

## Validation and acceptance

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
