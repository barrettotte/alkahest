# Accessibility

Alkahest targets WCAG 2.2 Level AA for HTML, EPUB Accessibility 1.1 for EPUB
3.3, and evaluated PDF/UA output. These are targets, not current conformance
claims. Automation can establish deterministic structure and catch many
failures; it cannot judge whether reading order, alternatives, mathematics, or
interaction are useful to a reader.

## Commands and evidence

| Medium | Render | Automated gate | Human evidence |
|---|---|---|---|
| HTML | `make render-html` | `make check-accessibility` | `book/accessibility-review.json` |
| EPUB | `make render-epub` | `make check-epub-accessibility` | `book/epub-reading-system-review.json` |
| PDF | `make render-pdf-accessibility-smoke` | veraPDF during render plus `make check-pdf-accessibility-policy` | `book/pdf-accessibility.json` |

Fixture commands (`make test-accessibility`, `make test-epub-accessibility`,
`make test-epub-review`, and `make test-pdf-accessibility-policy`) prove that
invalid policy, metadata, semantics, evidence, and premature claims fail.

## Web

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

## EPUB

The EPUB gate combines four layers:

1. EPUBCheck 5.3.0 for EPUB packaging and specification rules;
2. Ace by DAISY 1.4.6 for automated accessibility rules;
3. Alkahest checks for intended language, landmarks, spine/TOC order,
   headings, tables, alternatives, MathML, links, and generated semantics; and
4. the versioned manual reader matrix and claim-state checker.

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

### Reader review

The planned matrix uses Thorium Reader, Calibre E-book viewer, and Foliate to
exercise Chromium/Readium, Qt WebEngine, and WebKitGTK rather than three shells
around one engine. Versions in the JSON ledger must be updated to the actual
tested releases.

After a clean commit and successful automation, run
`make prepare-epub-review`. It binds the exact Git revision and a canonical
EPUB digest; any meaningful content change invalidates incomplete observations.
For every reader, record application/engine, OS, screen reader, evaluator, date,
all ten semantic/interaction criteria, and text-size checks at default, at
least 150%, and at least 200%.

The ledger supports `pending-manual-review`, `reviewed-no-claim`, and
`conformant`. The last state requires every result to pass plus the exact
standard string and complete evaluator information.

## PDF and PDF/UA

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

## Claim boundary

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
