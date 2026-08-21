# Publication profiles

The template has three page-layout profiles. They are production intentions,
not vendor-specific final files: a printer or publisher can still require a
different trim, margins, color space, PDF standard, or supplied cover.

| Profile | Size | Initial margins (inside / outside / top / bottom) | Purpose |
|---|---:|---:|---|
| Primary print | 7 x 10 in | 0.85 / 0.70 / 0.70 / 0.80 in | Technical books with code, equations, and diagrams |
| Economy print | 6 x 9 in | 0.80 / 0.65 / 0.65 / 0.75 in | Lower-cost, more portable edition |
| Review | US Letter | 1 / 1 / 1 / 1 in | Editorial markup and office printing only |

The print profiles use mirrored inside/outside margins and right-hand chapter
openings. Their PDFs are exactly the trim dimensions, with no bleed area. All
interior content must therefore remain inside the live area. A later preflight
step will check embedded fonts, effective image resolution, color space, and
PDF standard before any release is called print-ready.

The shared body rhythm, paragraph treatment, and running-page furniture are
defined in [`typography.md`](typography.md). Both PDF backends implement that
contract while retaining profile-specific page geometry.
Title and division-page sequencing is defined in
[`page-system.md`](page-system.md).
Heading depth, numbering, contents, and reference wording are defined in
[`headings-and-references.md`](headings-and-references.md).
Shared color roles, reflowable styles, and PDF theme adapters are defined in
[`theme.md`](theme.md).
Locale profiles, semantic language spans, and font-coverage boundaries are
defined in [`localization.md`](localization.md).

Interior artwork should remain understandable in grayscale even when a digital
edition uses color. Do not encode meaning by color alone. We are not forcing
the generated PDFs to grayscale yet because that would hide source-art and
contrast problems that should instead fail a deliberate preflight check.

## Commands and artifacts

| Command | Outputs |
|---|---|
| `make render` | HTML, EPUB, and both primary 7 x 10 PDFs |
| `make render-pdf` | Default primary 7 x 10 Typst PDF |
| `make render-print-6x9` | Typst and LuaLaTeX 6 x 9 PDFs |
| `make render-review` | Typst and LuaLaTeX US Letter PDFs |
| `make render-pdf-profiles` | All six PDF variants |
| `make render-locale-smoke` | French-locale HTML fixture |
| `make check-pdf-profiles` | Verify all six page sizes, selected faces, font packaging, and page-system markers |

Artifacts are grouped under `book/_build/print/7x10/`,
`book/_build/print/6x9/`, and `book/_build/review/letter/` by PDF backend.
Typst is the scored default; LuaLaTeX remains a tested compatibility and
diagnostic backend. The decision and reversal policy follow below.

## PDF backend decision

Typst is the default PDF backend. LuaLaTeX remains a supported compatibility
and diagnostic backend; ordinary renders and CI continue building both so the
fallback cannot decay unnoticed. The machine-readable scorecard is
`book/pdf-backends.json`.

| Criterion | Weight | Typst | LuaLaTeX |
|---|---:|---:|---:|
| Required-feature fidelity | 25% | 5 | 4 |
| Typography and page control | 20% | 4 | 5 |
| Reliability and diagnostics | 15% | 3 | 4 |
| Template maintainability | 15% | 4 | 3 |
| Accessibility and PDF standards | 10% | 3 | 1 |
| Build speed | 5% | 5 | 2 |
| Specialist ecosystem fit | 5% | 4 | 5 |
| Long-term portability | 5% | 3 | 5 |
| **Weighted result** | **100%** | **4.00** | **3.75** |

Typst leads on the evaluated feature path, direct SVG consumption, tagged
output, maintainability, and iteration speed. LuaLaTeX retains more mature page
composition, specialist packages, archival history, and publisher familiarity.
The margin is intentionally reversible rather than a reason to remove either
backend.

### Known exceptions

- Quarto's bundled `typst-gather` needs a newer glibc than the pinned base
  image, so Quarto uses its offline fallback and emits one known warning.
- Typst and its Quarto integration are younger and require locks plus regression
  coverage against upstream change.
- Ordinary LuaLaTeX output remains untagged and its clean-container render is
  slower; the experimental PDF/UA profile is evaluated separately.
- Neither backend is yet certified for a printer or publisher workflow. PDF/UA
  automation passes, but human review remains pending in
  [`accessibility.md`](accessibility.md#pdf-and-pdfua).

### Migration and reversal

Canonical chapters remain neutral Quarto Markdown. Backend code stays in
`book/typst/`, `book/latex/`, profiles, filters, and asset adapters. A production
blocker can switch the default alias to LuaLaTeX without rewriting content.

Review the decision when a publisher requires backend-specific source or PDF
features, accessibility evidence changes, a required feature fails, or a
toolchain upgrade materially changes fidelity or reliability. Reversal updates
the registry, render alias, scorecard, and evidence while stable content IDs and
authoring syntax remain unchanged.

`make check-pdf-backend-decision` validates score arithmetic, operational
default, adapters, documentation markers, and neutral manuscript source.

The initial 2026-08-16 validation confirmed 504 x 720 point media boxes for
7 x 10, 432 x 648 for 6 x 9, and 612 x 792 for Letter. All fonts in all six
specimen PDFs were embedded and subset. Typst produced tagged PDFs; the current
LuaLaTeX path did not, which remains an accessibility evaluation item rather
than a print-trim failure.

A visual check of the tightest 6 x 9 layout confirmed the mirrored margins and
showed that the specimen diagram and table remain legible. It also exposed a
deliberately long raw-code line overflowing the original LuaLaTeX live area.
Phase 3 resolved that blocker with continuation-safe LuaLaTeX wrapping and a
hard-token fallback in Typst; the PDF validator now rejects text outside the
physical page. The trim did not need to grow to accommodate source code.

## Publishing boundary

The interior and cover are separate products. Cover width, spine width, bleed,
barcode safe area, and finish depend on the chosen printer, binding, paper, and
final page count, so the template must not guess them. Generate the cover only
after those values are fixed for a specific edition.

The primary profile is compatible in principle with current KDP and
IngramSpark trim menus, but vendor requirements must be rechecked at release
time:

- [KDP paperback and hardcover trim, bleed, and margin guidance](https://kdp.amazon.com/en_US/help/topic/GVBQ3CMEQW3W2VL6/)
- [KDP print options and trim-size tables](https://kdp.amazon.com/en_US/help/topic/G201834180)
- [IngramSpark file creation guide](https://www.ingramspark.com/hubfs/downloads/ingramspark-guide-download.pdf)

Traditional publishers may request their own source or production files. The
canonical Markdown remains independent of these profiles so a publisher's
house trim can be added without rewriting the manuscript. A clean DOCX review
export remains a useful later interoperability target.
