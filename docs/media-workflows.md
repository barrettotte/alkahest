# Media workflows

Alkahest publishes one reviewed, deterministic derivative across HTML, EPUB,
Typst, and LuaLaTeX. Editable text or data remains the canonical source;
generated SVG is committed, byte-checked, self-contained, and never hand
edited. Backend-native packages remain evaluation candidates unless they solve
a requirement the shared derivative cannot satisfy.

## Selected workflows

| Domain | Canonical source | Generator | Publication derivatives | Check |
|---|---|---|---|---|
| Graphs and charts | CSV, JSON, Mermaid, or DOT under `book/figures/data/` and `book/figures/source/` | `alkahest.generators.graphs` and the computing generator | Dependency graph, response-time chart, and half-adder SVGs | `make check-graphs` |
| Electrical circuits | Diagram construction in `alkahest.generators.circuits` | Schemdraw 0.23 through the locked `uv` environment | `voltage-divider.svg` | `make check-circuits` |
| Chemistry | Reaction data in `alkahest.generators.chemistry` | RDKit 2026.03.5 through the locked `uv` environment | `fischer-esterification.svg` | `make check-chemistry` |
| Computing | `computing-diagrams.json` | Standard-library Python | Timing, gates, memory/instruction, and datapath SVGs | `make check-computing-diagrams` |
| Physics | `physics-diagrams.json` | Standard-library Python | Vector and inverse-square-field SVGs | `make check-physics-diagrams` |
| Rich media | `book/media.json` plus local assets | Registry filter and one deterministic audio generator | Native HTML enhancement plus SVG/text fallbacks | `make check-rich-media` |

Every generator runs offline. The check command validates source schema and
domain invariants, regenerates into a disposable directory, and requires byte
equality with the committed derivative. Version, runtime, package, and binary
hashes belong in the root `uv.lock`, the container lock, and
`docs/toolchain-lock.md`; duplicating them in prose makes documentation stale.

## Candidate decisions

- Mermaid and Graphviz remain useful text sources for automatic layouts, but
  Quarto currently loses their `fig-alt` values in the Typst PDF/UA path.
  Publication therefore uses committed accessible SVG derivatives.
- Vega-Lite remains an inert evaluated candidate until an offline static
  compiler and its license payload are locked.
- CircuitikZ and Zap compile viable electrical diagrams but would create
  separate LaTeX and Typst implementations. Schemdraw supplies one shared SVG.
- Chemfig and typed-smiles remain viable native chemistry candidates. RDKit is
  selected because one validated reaction source produces a shared derivative.
- WaveDrom is well suited to timing and register fields, but its second browser
  renderer remains deferred. Strict candidate JSON stays versioned and inert.
- Matplotlib, PGFPlots, and native drawing packages remain options for future
  needs that exceed the small deterministic physics fixtures.

Candidate sources live under `book/figures/candidates/`. They are evidence of
evaluated alternatives, not dependencies of an ordinary publication render.

## Derivative contract

A publication SVG must have a fixed reviewed view box, monochrome-safe vector
geometry, no scripts or external resources, and an ARIA-associated title and
description. Text remains selectable when the domain renderer permits it;
path-based chemistry labels instead rely on the manuscript alternative and
description. The manuscript always owns the stable figure ID, caption,
`fig-alt`, visible long description when needed, source, and rights statement.

HTML and EPUB embed SVG directly. Typst consumes it directly; LuaLaTeX uses the
locked librsvg vector conversion. Review both 6 x 9 PDFs for line weights,
labels, collisions, caption separation, and grayscale meaning. Generated
diagrams are explanatory evidence, not simulation, standards certification,
scientific review, PCB layout, or chip-layout results.

Domain review remains mandatory:

- circuits: topology, polarity, values, current direction, and safety claims;
- chemistry: structures, stereochemistry, conditions, mechanisms, and yields;
- computing: timing, active levels, truth behavior, ranges, bit order, and
  architecture arrows;
- physics: model, coordinates, units, precision, uncertainty, sampling, and
  provenance; and
- charts: axes, transformations, source data, scales, and statistical claims.

## Rich media

Rich media is an optional HTML enhancement, never the only instructional path.
Each `media-...` entry in `book/media.json` records locked source and fallback
bytes, description, transcript, provenance, license, distribution decision,
and exactly one semantic manuscript reference:

```markdown
{{< alk-media media-reference-tone >}}
```

HTML receives local native controls or a tightly sandboxed local frame. Media
must not autoplay with sound; video needs captions, animation needs pause and
reduced-motion behavior, and interaction needs keyboard operation, a visible
label, programmatic state, and a text result. EPUB and both PDF backends receive
the registered SVG fallback, description, and transcript instead of scripts or
playback. The fallback must teach the same point as the enhancement.

`make check-publication` verifies HTML delivery and static-only EPUB packaging;
`make check-pdf-profiles` verifies fallback prose in every print profile.

## Rights and distribution

The reference data, generators, and selected derivatives are original Alkahest
fixtures dedicated under CC0 1.0 unless their registry says otherwise.
Third-party tools retain their own licenses but are not copied into generated
SVGs. Real externally sourced data or media must record creator, source and
version, acquisition or calculation method, processing, date, license or
permission, and limitations before public distribution.

`book/assets.json` consolidates the release decision and imports the complete
file/checksum inventory from `book/media.json`. `make check-asset-rights`
rejects missing rights, unregistered bytes, private distribution decisions, and
removable metadata; `make check-release-assets` proves that HTML and EPUB carry
only approved derivatives and fallbacks.
