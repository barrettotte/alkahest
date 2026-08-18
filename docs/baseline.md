# Baseline build report

- Date: 2026-08-16
- Source: initial three-chapter reference book
- Toolchain: `localhost/alkahest-publishing:quarto-1.10.18-v5`
- Result: all four target formats build from the same `.qmd` sources

## Artifacts

| Target | Result | Size | Initial observations |
|---|---|---:|---|
| HTML | pass | 3,992,132 bytes across 24 files | Multi-page output; no render warnings |
| EPUB | pass | 80,217 bytes | EPUBCheck 5.3.0 passes EPUB 3.3 with no messages |
| Typst PDF | pass | 142,547 bytes, 11 pages | 7 x 10 in, PDF 1.7, tagged; one tool fallback warning |
| LuaLaTeX PDF | pass | 94,189 bytes, 12 pages | 7 x 10 in, PDF 1.7, not tagged; no render warnings |

All generated artifacts are owned by the invoking host user. Normal rendering
runs without container networking.

## Local build measurement

`make build-report` performed one sequential run per format with fresh
ephemeral container caches. The image was already present locally; existing
artifacts were overwritten in place. These values are a regression baseline
for this host, not a cross-machine performance claim.

- Captured: 2026-08-16 16:23 EDT
- Podman: 5.8.4
- Host logical CPUs: 32

| Target | Wall time | Captured warnings |
|---|---:|---:|
| HTML | 7.52 s | 0 |
| EPUB | 5.74 s | 0 |
| Typst PDF | 4.15 s | 1 |
| LuaLaTeX PDF | 11.69 s | 0 |

The Typst warning is the known `typst-gather` incompatibility with Ubuntu
20.04/glibc 2.31. Quarto stages all bundled Typst packages as its fallback and
successfully compiles the PDF. LuaLaTeX also generated its font-name database
inside the ephemeral cache; this was informational output, not a warning.

## Findings

1. The default Typst and LaTeX book formats do not yet form a fair visual
   comparison. They use different page sizes, typography, and book templates.
2. The Typst PDF is tagged by default in this baseline; the LuaLaTeX PDF is not.
   Tag presence alone is not proof of accessible structure, but it is an early
   backend difference worth testing.
3. The pinned upstream image uses Ubuntu 20.04/glibc 2.31, while Quarto 1.10.18's
   bundled `typst-gather` helper requires a newer glibc. Quarto falls back to
   staging all bundled Typst packages and the PDF still compiles. This warning
   should be removed by moving to a compatible base or an upstream image fix.
4. The upstream `quarto-full` image does not include Chrome libraries or the TeX
   packages needed by this small book. The local Containerfile now declares the
   browser runtime, KOMA-Script, English Babel data, and `caption` package.
5. Quarto format profiles must be rendered sequentially because project builds
   share source-directory intermediates.

## Checks performed

- Quarto completed each target with the intended output filename.
- `file` recognized HTML, EPUB, and both PDFs.
- `unzip -t` found no compressed-data errors in the EPUB.
- The offline HTML validator resolved 98 local page, resource, and fragment
  targets across three documents; five external targets were deliberately not
  fetched by the reproducible check.
- EPUBCheck 5.3.0 validated the book with EPUB 3.3 rules and reported zero
  fatals, errors, warnings, or informational messages.
- `pdfinfo` confirmed page count, page size, PDF version, and tag status.
- Shell scripts pass `bash -n`; the working diff passes `git diff --check`.

## Missing features and checks

- Tests in actual EPUB reader applications.
- HTML semantics, accessibility, and online availability of external URLs.
- PDF structural accessibility and print preflight.
- Visual comparison or regression testing.
- Repeated build-time measurements and deterministic artifact comparison.
- Production typography, unified HTML/EPUB/PDF theming, and final font choices.
- Final code-overflow policy, broader math/diagram fixtures, glossary,
  appendices, preview editions, and the other authoring features tracked in the
  roadmap.
