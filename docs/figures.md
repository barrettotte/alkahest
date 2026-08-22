# Figure and visual-asset contract

`book/figures.qmd` is the acceptance specimen for standalone figures,
subfigures, captions, alternative descriptions, source credit, float behavior,
full-width art, and medium-specific variants. Figure inputs are versioned
assets; generated assets must eventually carry the same provenance record.

## A complete figure

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

## Panels and subfigures

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

## Full-width and medium-specific variants

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

## Placement and asset policy

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
in [`media-workflows.md`](media-workflows.md).

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

## Validation

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
