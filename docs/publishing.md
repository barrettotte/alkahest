# Publishing

Output profiles, accessibility evidence, canonical metadata, product manifestations, generated adapters, and public release staging.

## Publication profiles {#doc-publication-profiles}

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
interior content must therefore remain inside the live area. The automated
preflight described below verifies this generic interior contract, but it does
not make a printer-specific or print-ready claim.

The shared body rhythm, paragraph treatment, and running-page furniture are
defined in [`design.md`](design.md#doc-typography). Both PDF backends implement that
contract while retaining profile-specific page geometry.
Title and division-page sequencing is defined in
[`design.md`](design.md#doc-page-system).
Heading depth, numbering, contents, and reference wording are defined in
[`authoring.md`](authoring.md#doc-headings-and-references).
Shared color roles, reflowable styles, and PDF theme adapters are defined in
[`design.md`](design.md#doc-theme).
Locale profiles, semantic language spans, and font-coverage boundaries are
defined in [`localization.md`](localization.md#doc-localization).

Interior artwork should remain understandable in grayscale even when a digital
edition uses color. Do not encode meaning by color alone. The generic PDF
profiles preserve RGB/gray artwork so source-art and contrast problems remain
visible; a future vendor profile may perform a declared press conversion.

### Commands and artifacts

| Command | Outputs |
|---|---|
| `make render` | HTML, EPUB, and both primary 7 x 10 PDFs |
| `make render-pdf` | Default primary 7 x 10 Typst PDF |
| `make render-print-6x9` | Typst and LuaLaTeX 6 x 9 PDFs |
| `make render-review` | Typst and LuaLaTeX US Letter PDFs |
| `make render-pdf-profiles` | All six PDF variants |
| `make render-preview` | Curated preview HTML, EPUB, and 7 x 10 Typst PDF |
| `make check-preview` | Preview allowlist, privacy, links, EPUB, metadata, and PDF checks |
| `make generate-covers` | Development wrap SVGs, front thumbnails, and geometry manifests |
| `make check-cover-artifacts` | Recalculate cover geometry from selected interior PDFs and reject drift |
| `make render-locale-smoke` | French-locale HTML fixture |
| `make check-pdf-preflight` | Check PDF boxes, font packaging, raster resolution, color spaces, and unsafe document features |
| `make test-pdf-preflight` | Exercise valid and invalid preflight parser fixtures without rendering |
| `make check-pdf-profiles` | Run preflight plus the specimen's layout, content, and page-system checks |
| `make check-golden-pages` | Compare fragile primary-profile pages with committed backend-specific baselines |
| `make test-golden-pages` | Exercise golden-page policy, marker, PNG, comparison, and coverage fixtures |
| `make update-golden-pages` | Deliberately replace baselines after reviewing an intended layout change |

Artifacts are grouped under `book/_build/print/7x10/`,
`book/_build/print/6x9/`, and `book/_build/review/letter/` by PDF backend.
Typst is the scored default; LuaLaTeX remains a tested secondary and
diagnostic backend. The decision and reversal policy follow below.

### Print preflight

`config/pdf/preflight.json` is the machine-readable contract for all six
artifacts. `make check-pdf-preflight` runs it without network access in the
locked rootless container. It checks every page's physical size and rotation,
then checks the first, middle, and final pages' MediaBox, CropBox, BleedBox,
TrimBox, and ArtBox. All current interiors require zero bleed and identical
boxes.

Every font must be embedded and subset. Poppler inventories raster objects and
requires at least 300 effective pixels per inch for continuous-tone images and
600 for one-bit art. The current specimen intentionally remains vector-only;
the fixture suite proves rejection of low-resolution continuous-tone and
one-bit image reports. The failing diagnostic includes the page, PDF object,
measured horizontal and vertical resolution, and required threshold.

Raster images may use one- or three-component gray/RGB/ICC color models.
veraPDF independently inventories document-level vector color spaces; the
generic profile permits DeviceGray, DeviceRGB, one- or three-component ICC,
and pattern spaces. It rejects `CMYK`, spot-color families, four-component ICC,
and undeclared output intents. PDF 1.7 is required, and encrypted PDFs,
JavaScript, page rotation, or unexpected bleed fail preflight.

These are neutral RGB/gray interior rules, not a promise that one file is ready
for every press. A selected printer may require a specific `CMYK` ICC profile,
output intent, PDF/X standard, total-ink limit, or bleed geometry. Add those as
an explicit vendor profile rather than silently converting the generic files.
Cover bleed and output intent remain part of the separate cover/vendor
pipeline.

### Golden-page visual regression

The structural PDF checks catch page-box, font, text-boundary, and content
failures. The complementary golden-page gate catches subtler composition drift
in five deliberately fragile layouts: long code, aligned mathematics, a
circuit, a multipage table, and multilingual text. Semantic markers resolve
the current PDF page, so ordinary pagination changes do not require hard-coded
page numbers.

The compact baseline covers each fixture in both primary 7 x 10 backends.
Comparison is exact after decoding a pinned 96-DPI grayscale raster; Typst is
compared only with its Typst baseline and LuaLaTeX only with its LuaLaTeX
baseline. The other trim profiles retain structural and preflight coverage
without multiplying low-value image snapshots. Failures create a Markdown
report plus current and red-difference images under
`book/_build/qa/golden-pages/`. Baseline replacement is available only through
the explicit `make update-golden-pages` maintenance target.

### PDF backend decision

Typst is the default PDF backend. LuaLaTeX remains a supported secondary
and diagnostic backend; ordinary renders and CI continue building both so the
fallback cannot decay unnoticed. The following table preserves the evaluated
decision without maintaining a second executable policy for historical scores.

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

#### Known exceptions

- Quarto's bundled `typst-gather` needs a newer glibc than the pinned base
  image, so Quarto uses its offline fallback and emits one known warning.
- Typst and its Quarto integration are younger and require locks plus regression
  coverage against upstream change.
- Ordinary LuaLaTeX output remains untagged and its clean-container render is
  slower; the experimental PDF/UA profile is evaluated separately.
- Neither backend is yet certified for a printer or publisher workflow. PDF/UA
  automation passes, but human review remains pending in
  [`publishing.md`](#pdf-and-pdfua).

#### Switching backends

Canonical chapters remain neutral Quarto Markdown. Backend code stays in
`book/typst/`, `book/latex/`, profiles, filters, and asset adapters. A production
blocker can switch the default alias to LuaLaTeX without rewriting content.

Review the decision when a publisher requires backend-specific source or PDF
features, accessibility evidence changes, a required feature fails, or a
toolchain upgrade materially changes fidelity or reliability. Reversal updates
the render alias and evidence while stable content IDs and authoring syntax
remain unchanged. Behavioral render, preflight, accessibility, and golden-page
checks protect both backend paths directly.

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

### Cover pipeline and publishing boundary

The interior and cover are separate products. `config/covers/cover-policy.json`
connects the two planned print manifestations to their selected Typst interior
artifacts and declares every geometric input explicitly: printer-template ID
and revision, binding, paper and sheet caliper, page-count policy, bleed, safe
inset, minimum spine width for text, barcode reserve, finish, and color space.
The current template is deliberately generic, sRGB, and marked not press ready.
It validates the workflow without pretending to satisfy an unselected vendor.

Run `make generate-covers` only after rendering the 7 x 10 and 6 x 9 Typst
interiors. The generator reads each PDF's actual trim and page count, hashes the
selected interior, and rounds an odd page count up by one physical production
page. Spine width is production pages multiplied by half the declared sheet
caliper. It emits, for each print manifestation:

- an exact-dimension full-wrap SVG showing back, spine, front, bleed, safe
  areas, and the barcode reserve;
- a clean front-cover SVG thumbnail; and
- a machine-readable manifest recording metadata, inputs, geometry, output
  checksums, and every remaining press-readiness blocker.

`make check-cover-artifacts` recalculates all outputs from the current PDFs and
requires exact bytes, exact file/profile coverage, valid SVG, matching trim,
and no local/private markers. A changed interior page count or byte changes the
manifest and geometry, making stale covers fail. The present 73-page 7 x 10
interior becomes 74 production pages and a 0.1665-inch spine; the 81-page 6 x 9
interior becomes 82 production pages and a 0.1845-inch spine. Both fall below
the configured 0.25-inch spine-text threshold, so lettering is disabled rather
than made illegible.

These generated concepts leave the manifestation `cover` fields null. Final
artwork should populate those checksum-locked fields only after the printer,
binding, paper, page count, template, bleed, barcode, finish, identifier, and
press color profile are fixed for a specific edition.

The primary profile may fit common print-on-demand trim menus, but vendor
requirements must be rechecked at release time. The links below are research
starting points, not pinned inputs to the generic development policy:

- [KDP paperback and hardcover trim, bleed, and margin guidance](https://kdp.amazon.com/en_US/help/topic/GVBQ3CMEQW3W2VL6/)
- [KDP print options and trim-size tables](https://kdp.amazon.com/en_US/help/topic/G201834180)
- [IngramSpark file creation guide](https://www.ingramspark.com/hubfs/downloads/ingramspark-guide-download.pdf)

Traditional publishers may request their own source or production files. The
canonical Markdown remains independent of these profiles so a publisher's
house trim can be added later without rewriting the manuscript.

## Accessibility {#doc-accessibility}

Alkahest targets WCAG 2.2 Level AA for HTML, EPUB Accessibility 1.1 for EPUB
3.3, and evaluated PDF/UA output. These are targets, not current conformance
claims. Automation can establish deterministic structure and catch many
failures; it cannot judge whether reading order, alternatives, mathematics, or
interaction are useful to a reader.

### Commands and evidence

| Medium | Render | Automated gate | Human evidence |
|---|---|---|---|
| HTML | `make render-html` | `make check-accessibility` | `book/accessibility-review.json` |
| EPUB | `make render-epub` | `make check-epub-accessibility` | Reader checklist below |
| PDF | `make render-pdf-accessibility-smoke` | veraPDF during render plus `make check-pdf-accessibility-policy` | `book/pdf-accessibility.json` |

Fixture commands (`make test-accessibility`, `make test-epub-accessibility`, and
`make test-pdf-accessibility-policy`) prove that
invalid policy, metadata, semantics, evidence, and premature claims fail.

### Web

The web gate validates `config/accessibility/wcag-2.2-aa.json`, theme
safeguards, declared palette pairs, and the review ledger, then runs pinned
axe-core through pinned Chrome with networking disabled. Automated violations
fail; axe `incomplete` results remain explicit manual-review items.

The HTML adapter provides a skip link, visible focus, underlined content links,
local overflow for intrinsically wide code/math, responsive content that
supports browser zoom,
reduced-motion behavior, usable target sizing, and native landmarks. Palette
calculations and browser-computed contrast complement one another; neither
replaces forced-color, focus, diagram, or device review.

The seven manual categories are semantics/reading order, keyboard/focus,
contrast/color, reflow/zoom, reduced motion, responsive targets, and
assistive-technology behavior. Each completed result records reviewer, date,
tested revision, pages, environments, and concrete evidence.

### EPUB

The EPUB gate combines three automated layers:

1. EPUBCheck 5.3.0 for EPUB packaging and specification rules;
2. Ace by DAISY 1.4.6 for automated accessibility rules;
3. Alkahest checks for intended language, landmarks, spine/TOC order,
   headings, tables, alternatives, MathML, links, and generated semantics.

Finalization supplies explicit front/body/back-matter semantics and matching
roles, useful landmarks, language on every content document, navigable
contents, table structure, image alternatives, MathML manifest declarations,
TeX annotations, and non-focusable generated positioning anchors. Discovery
metadata comes from `book/epub-accessibility.json`; `dcterms:conformsTo` is
forbidden while review is pending.

The reference specimen declares print-equivalent page navigation not
applicable because it has several deliberately different PDF layouts. A future
production EPUB may enable `print-equivalent` only after one print edition is
frozen and every page marker, page-list link, label, order, and
`pageBreakSource` agree.

#### Reader review

When reader testing begins, use current releases of Thorium Reader, Calibre
E-book viewer, and Foliate to cover Readium/Chromium, Qt WebEngine, and
WebKitGTK. For every reader, record the exact application and engine version,
OS, screen reader, evaluator, date, tested Git revision and EPUB checksum, all
ten semantic/interaction criteria, and text-size checks at default, at least
150%, and at least 200%.

The ten criteria are navigation and landmarks, reading order, headings and
lists, table semantics, image alternatives, mathematics, links and notes,
language changes, keyboard operation, and text resizing/reflow. Keep results in
review notes until testing actually starts. Add a structured evidence record
and validator only when there are observations to preserve. Conformance still
requires every result to pass plus the exact standard string and complete
evaluator information.

### PDF and PDF/UA

The locked image includes checksum-pinned veraPDF 1.30.2. Separate experimental
profiles evaluate Typst against PDF/UA-1 and LuaLaTeX against PDF/UA-2. A tagged
flag is only an observation; the evidence policy requires a successful render,
a passing report bound to the artifact, and complete human review before any
claim.

Current automated evidence through 2026-08-21:

| Backend | Candidate | veraPDF result | State |
|---|---|---|---|
| Typst | 41-page tagged PDF 1.7, no forms | 106 rules and 239,975 checks pass | Pending manual review |
| LuaLaTeX | 84-page tagged PDF 2.0, no forms | 1,727 rules and 217,333 checks pass | Pending manual review |

The Typst accessibility profile uses native contents structure instead of
orange-book's boxed outline, annotated inline/display math, and deterministic
SVG derivatives where native Mermaid/Graphviz conversion loses `fig-alt`.

The LuaLaTeX profile uses plain code to avoid the current `fancyvrb`/`tagpdf` stack
imbalance, three settling passes for a complete ParentTree, and locked
Libertinus Sans labels in circuit derivatives. veraPDF separately logs 25
duplicate `/Group` parser warnings; Poppler also questions several structure
attributes. These remain viewer-interoperability review items even though the
selected veraPDF profile passes.

Ordinary PDFs remain negative baselines: the ordinary Typst PDF is tagged but
fails PDF/UA metadata/alternative rules, and the ordinary LuaLaTeX PDF is
untagged. Neither is a conformance artifact.

PDF human review uses at least two independent viewers and a current screen
reader. It covers reading order, headings, lists, tables, math, figures,
captions, links, notes, citations, language changes, bookmarks, keyboard/form-
free navigation, metadata, and the exact wording of any proposed claim.

### Claim boundary

All three media keep claims disabled while evidence is pending. A future claim
must identify the tested revision and artifact, cover every required criterion,
name the evaluator and environments, preserve failures rather than erase them,
and publish only the standard/version actually tested. Real users with
disabilities should participate before a public claim when practical.

Primary standards and tool references:

- WCAG 2.2: <https://www.w3.org/TR/WCAG22/>
- EPUB Accessibility 1.1: <https://www.w3.org/TR/epub-a11y-11/>
- veraPDF validation: <https://docs.verapdf.org/validation/>
- Typst accessibility: <https://typst.app/docs/guides/accessibility/>

## Canonical publication metadata {#doc-publication-metadata}

`book/publication.json` is the canonical work-level metadata record. Its
versioned contract is `config/metadata/publication.schema.json`. Keep editorial
facts here even when a current output adapter also needs them in Quarto YAML or
another policy file.

The record covers:

- title, subtitle, short and long descriptions;
- contributor display/sort names, stable local IDs, roles, affiliations, and
  optional checksum-valid researcher identifiers;
- optional series data, edition wording and number, lifecycle status, and
  created, modified, and publication dates;
- primary/original language, publication territories, subjects, keywords, and
  named audiences;
- nullable publisher and imprint records so development books do not invent
  publication claims;
- copyright holders, a rights statement, and scoped licenses whose state is
  selected, undecided, or governed by another policy;
- accessibility features, hazards, summary, standard, and review status; and
- source, repository-visibility, rights-policy, accessibility-policy, and
  reproducibility statements.

The schema is deliberately closed: unknown keys, placeholder-only text,
duplicate controlled values, impossible date order, invalid role/status
vocabulary, contradictory hazards, unsafe policy paths, and inconsistent
license states fail. `WORLD` is the internal all-territories value and cannot
be mixed with individual two-letter territory codes. External subject schemes
remain explicit strings; their versioned code-list mappings belong to the
later ONIX export contract.

### Work and manifestation boundary

This record describes the intellectual work and facts shared by its outputs. A
manifestation is a particular HTML site, EPUB, PDF, print trim, preview,
translation, or other product. ISBNs and other product identifiers, dimensions,
covers, dates, prices, availability, and format-specific accessibility claims
belong to the records defined in [`publishing.md`](#doc-manifestations), not
this work record. That separation prevents one ISBN or price from leaking
across unlike products.

The reference specimen remains in `development` status. Its publication date,
publisher, imprint, copyright year, source URL, and publication-text license
are therefore null or explicitly undecided rather than filled with plausible
but false values. A forthcoming or published work must supply the applicable
date and publisher; a published work must also supply its copyright year.

### Generated adapters

The deterministic generator now supplies facts consumed by the toolchain:

- Quarto title, subtitle, author, and language;
- EPUB language, accessibility discovery terms, summary, standard, and review
  status; and
- PDF title and author expectations in the release-asset policy.

The EPUB identifier is typed in the manifestation registry and checked against
the reproducibility policy. The generated `alkahest` map supplies print and
reflowable publication-data pages without duplicating work facts in
`_quarto.yml`. [`publishing.md`](#doc-metadata-generation) documents the
committed Quarto adapter, release manifest, ONIX readiness report, pinned code
lists, and optional fail-closed ONIX 3.1 export.

Run these before rendering after any metadata change:

```sh
make check-publication-metadata
make test-publication-metadata
make generate-metadata
make check-metadata-generation
```

Both are included in the shared source dispatcher, so ordinary rendering and
CI also enforce the contract. Update `modified` only for a meaningful
publication-content or metadata revision, not for an unrelated template or
test change.

## Publication manifestations and identifiers {#doc-manifestations}

`book/manifestations.json` records product-level differences that do not belong
in the canonical work record. Its closed version 1 contract is
`config/metadata/manifestations.schema.json`.

A manifestation is one separately identifiable product or distribution form.
The current registry includes full web and EPUB outputs, two PDF sizes, an
internal review PDF, two planned print products, isolated HTML/EPUB/PDF preview
specimens, and private translation and supplemental web specimens. Planned
records may reserve an intent and dimensions, but cannot claim an artifact,
publication date, price, or availability.

Typst and LuaLaTeX outputs are renditions of the same manifestation when their
product metadata is identical. They remain independently tested PDF backends,
but they do not receive duplicate product records or identifiers. If a vendor,
accessibility treatment, file format, or edition later changes identifiers,
dimensions, cover, dates, pricing, or availability, add a manifestation rather
than hiding the difference in a rendition.

### Record contract

Every manifestation declares:

- a stable local ID, label, output format, variant, edition, language, and
  lifecycle status;
- typed publication identifiers;
- physical dimensions for PDF and print, with dimensions forbidden on
  reflowable web and EPUB records;
- an optional checksum-locked cover role and source path;
- announcement, publication, and withdrawal dates;
- zero or more currency/territory prices stored as exact two-decimal strings;
- availability status, territories, and distribution channels;
- the production profile, expected artifact path, and media type; and
- a typed relationship for previews, translations, review derivatives,
  supplemental products, and print interiors.

Relations must resolve without self-reference or cycles. A translation changes
language without changing format, a preview retains the full manifestation's
format, a PDF preview also retains its trim, and a print product points to a
dimension-matched PDF interior. Artifacts cannot be reused across records. The
validator also reconciles editions, locales, reproducible artifacts, primary
PDF preflight dimensions, and the distinct full/preview EPUB UUIDs with their
existing policies.

### Typed identifiers

Supported schemes are ISBN-10, ISBN-13, lowercase UUID URNs, lowercase DOI
names, and canonical HTTPS URLs. ISBN values use digits without punctuation
(with a final `X` permitted for ISBN-10), valid prefixes, and valid checksums.
If both ISBN forms are recorded, the conversion must identify the same product.
Identifier types cannot repeat within a manifestation, and the same typed
identifier cannot be reused by two manifestations. ISBNs are limited to EPUB,
PDF, and print products.

The development specimen intentionally has no ISBN, DOI, public URL, price, or
publication date. Stable, distinct UUID URNs identify its full and preview EPUB
packages for reproducible development builds. Add retail identifiers only when
a specific product has been selected; never copy one ISBN between print, EPUB,
PDF, or preview products.

Preview product presentation is separate from work-level metadata. The preview
profile overrides the product subtitle, description, and edition statement;
configures optional full-edition and purchase links; and controls a decorative
watermark. The current development manifestation leaves both URLs empty rather
than publishing placeholder destinations. Its cover field also remains null:
the profile supplies a clear title/notice treatment, while physical or
storefront cover files belong to the later dimension-aware cover pipeline.

Print-cover production is separate from assigning a final manifestation cover.
`config/covers/cover-policy.json` binds each planned print record to its
dimension-matched selected PDF interior. Generated development templates remain
below `book/_build/covers/` and therefore do not populate a manifestation's
checksum-locked `cover` field or imply retail readiness. Assign that field only
after final artwork, printer geometry, identifiers, and press requirements are
approved.

The schema checks currency and territory code shape but does not claim that a
code is current. The later release/ONIX contract will pin external code-list
versions and map these internal values for distributors.

### Lifecycle and maintenance

The lifecycle and availability pairs are explicit:

| Lifecycle | Allowed availability |
|---|---|
| Planned | Unavailable |
| Development | Unavailable or private |
| Forthcoming | Unavailable or `preorder` |
| Published | Available |
| Withdrawn | Withdrawn |

`preorder` and available records require at least one channel. Private,
unavailable, and withdrawn records cannot carry channels; prices are allowed
only for `preorder` or available products. Publication and withdrawal dates must
agree with lifecycle state and remain chronologically valid.

After changing a manifestation, run:

```sh
make check-manifestations
make test-manifestations
```

Both targets use the shared source dispatcher and therefore also run during
ordinary renders and CI. The preview, French localization, and supplemental
records currently describe private acceptance specimens, not publishable
editions; later roadmap items add their release profiles and privacy gates.

## Generated publication metadata {#doc-metadata-generation}

`book/publication.json` and `book/manifestations.json` are the author-edited
sources of truth. `config/metadata/generation.json` fixes their adapters,
output paths, ONIX 3.1 release, and the exact subset of EDItEUR code-list issue 74
that Alkahest uses. Change canonical records or the mapping policy; do not
hand-edit generated values.

Run:

```sh
make generate-metadata
make check-metadata-generation
make test-metadata-generation
```

The generator writes three small, reviewable files:

- `book/generated/metadata.yml` supplies title, contributors, language,
  description, subjects, keywords, edition, rights, and development-safe publication values to
  Quarto. `_quarto.yml` includes it through top-level `metadata-files`, so HTML,
  EPUB, Typst, LuaLaTeX, and staged editions inherit one adapter.
- `book/generated/release-manifest.json` combines work and manifestation facts,
  records the reproducible source date and pinned ONIX version, and exposes
  explicit release blockers. Artifact byte hashes belong to the later release
  packaging step because the canonical manifest is generated before rendering.
- `book/generated/onix-status.json` records each product's ONIX eligibility.
  It names missing retail facts instead of creating an invalid or misleading
  distributor record.

These derived files are committed deliberately. Exact byte comparison makes a
metadata change visible in review and lets pre-render validation reject stale
adapters without relying on a locally installed YAML library.

### ONIX boundary

ONIX XML is optional and fail-closed. A product must be EPUB, PDF, or print; be
forthcoming, published, or withdrawn; have a real ISBN-13 or DOI, publisher,
publication date, mapped language, contributor roles, and audience. A historic
ISBN-10 may accompany its validated ISBN-13 but cannot make a product eligible
by itself. The development reference book satisfies none of these retail
claims, so `book/generated/onix.xml` is intentionally absent.

When publication data is complete, normal generation writes deterministic
ONIX 3.1 reference-tag XML. A release workflow can require it explicitly:

```sh
alkahest generate publication-metadata --require-onix
```

That command fails if no product is eligible. Fixtures exercise ISBN, product
form, contributor, language, audience, description, lifecycle, publisher, and
date mappings against their pinned codes. The policy links the official
[EDItEUR code-list browser](https://ns.editeur.org/onix/en); review and update
the issue number, mappings, fixtures, and documentation together rather than
silently consuming a newer quarterly list.

This generator produces descriptive and publishing metadata, not a claim that
an ONIX message meets a particular retailer's commercial feed requirements.
Retailer supply, price, territorial, and validation rules are finalized with
the release/distributor profile that will consume the file.

## Full and preview release profiles {#doc-release-profiles}

Alkahest separates reusable release behavior from book-specific editorial
choices. In a minimal generated book, authors select one or two excerpt chapter
filenames in `book.toml`; numbered full chapters are discovered automatically,
and `make build` or `make excerpt` creates the relevant profile and allowlist
only in ignored workspace state. The direct JSON workflow below remains the
exhaustive specimen and advanced engine contract.

The engine supplies the closed defaults in
`book/alkahest-release-defaults.json` (installed as
`book/.alkahest/release-defaults.json` in generated books). Each book owns only
`book/releases.json`: its manuscript registry, each full or preview chapter allowlist,
appendix allowlists, product metadata overrides, and optional
preview wording or links.

Run:

```sh
make generate-release-profiles
make check-release-profiles
make test-release-profiles
```

Minimal generated books expose `make build` for the full release and
`make excerpt` for the public HTML, EPUB, and Typst excerpt. `make build-all`
adds the secondary LuaLaTeX PDF to the normal full build.

### Book-local contract

Every publishable `.qmd` file is registered once under `sources` with a stable
ID, relative path, role, and availability:

- `release` sources must appear in the full profile and may appear in preview;
- `supplemental` and `private` sources are never selected by these public
  profiles; and
- roles distinguish front matter, ordinary chapters, back matter, and
  appendices so Quarto receives the correct structure.

The full profile must select every `release` source. The preview must be a
subset containing one or two ordinary manuscript chapters; supporting front
matter, back matter, and appendices remain explicit choices. A one-chapter
starter book may initially use the same content in both profiles, then narrow
the preview allowlist as the full manuscript grows.

Each profile provides its own subtitle, description, edition statement, and
UUID URN. This prevents a preview EPUB from inheriting the full product's
identity. Book-local presentation fields can override shared notice text,
watermark text, and HTTPS full-edition or purchase links without copying the
engine defaults. Unknown fields, unsafe paths, duplicate selections, bad URLs,
duplicate identifiers, or stale adapters fail visibly.

### Generated profiles and isolation

`scripts/sync-release-profiles.py` deterministically generates:

- `book/_quarto-release-full.yml`;
- `book/_quarto-release-preview.yml`; and
- `book/generated/release-profile-manifest.json` with input/output checksums
  and the resolved allowlists.

Treat these as derived files; edit `book/releases.json`, then regenerate. Put
the release profile first when composing Quarto profiles—for example
`--profile release-preview,epub`—because the pinned Quarto profile composition
gives that first profile precedence for product identifiers and metadata.

`scripts/stage-release.py full` and `scripts/stage-release.py preview` create an
isolated Quarto project below `book/_build/staging/releases/`. Only allowlisted
manuscript sources are linked into that project. Registered private,
supplemental, and unselected chapter roots remain absent; HTML staging also
materializes only rich-media files referenced by selected sources. This is a
source-isolation boundary, not merely a conditional display rule.

Within the exhaustive specimen, whenever a manuscript file is added, moved, or
retired, update its source record and both allowlists in the same change.
Minimal books avoid this duplicate labor through numbered-file discovery.
