# Publishing toolchain

The publishing environment derives from the official `quarto-full` container at
Quarto 1.10.18, locked to its published image digest. It runs with Podman, which
is already present on the Bazzite host. The small local derivation installs a
locked Chrome Headless Shell so diagrams can be rendered in non-HTML outputs.
Its operating-system packages, browser archive, and TeX packages all come from
dated or versioned upstream sources declared directly in the Containerfile.

The finished image defaults to the unprivileged `alkahest` user (UID/GID 10001).
The project wrapper also uses rootless Podman and overrides that identity with
the invoking host UID/GID, preserving normal ownership for generated files in
the bind-mounted repository. The wrapper refuses to run when invoked by host
root. Root is used only in image-build layers that install operating-system and
TeX packages.

The full image is intentional: the reference book needs Quarto/Pandoc, bundled
Typst, a TeX engine, and a headless browser for print rendering of Mermaid
diagrams. Once the reference suite is stable, we can decide whether the image
size justifies maintaining a smaller custom image.

Required TeX packages are installed explicitly in the Containerfile. Quarto can
normally fetch a missing package during compilation, but offline normal builds
turn an undeclared package into a hard failure instead.
The image includes locked Babel modules and available hyphenation patterns for
the reference book's English, French, German, Greek, Russian, and Hebrew
samples.

The image also includes checksum-locked EPUBCheck 5.3.0 and its exact OpenJDK
runtime from the Ubuntu snapshot. The pinned `librsvg2-bin` package supplies
`rsvg-convert`, which Quarto uses to turn versioned SVG art into vector PDF
inputs for LuaLaTeX. `make check-publication` uses EPUBCheck plus a local HTML
target/fragment validator with container networking disabled.

## Baseline versions

The first successful build used:

| Component | Version |
|---|---|
| Quarto | 1.10.18 |
| Pandoc | 3.10.0 |
| Typst | 0.15.1 |
| TeX Live | 2026 |
| Chrome for Testing | 152.0.7977.42 |

The exact binary hashes, TeX package revisions, and baseline font identities
are recorded in `docs/toolchain-lock.md`. Run `make toolchain-report` to compare
the locally built image with that record.

The Quarto base image is immutable by digest. Chrome runtime libraries resolve
from Ubuntu snapshot `20260816T000000Z`; the Chrome for Testing archive is
versioned and checksum-verified; and TeX packages resolve from the TeX Live
daily snapshot for 2026-08-16 after its package database is checksum-verified.
Installed browser bytes, TeX revisions, and representative font files are also
asserted during the image build. Because the base image lacks GPG support for
`tlmgr`, the recorded package-database checksum—not a repository signature—is
the TeX snapshot trust anchor.

## First use

```sh
make bootstrap
make check
make check-glyph-coverage
make render
make render-locale-smoke
make check-publication
```

`make bootstrap` is the only normal command that needs network access. Rendering
runs the container with networking disabled so a successful build cannot depend
on an undeclared download.

Run `make build-report` to perform one sequential measurement of all four
primary formats. It reports wall-clock duration, captured Quarto warnings,
artifact size, and PDF page metadata without deleting existing outputs. Treat
the timing as a local comparison point rather than a cross-machine benchmark.

`make ci` is the shared local and GitHub Actions validation entry point. It
bootstraps the locked image, runs Quarto and toolchain diagnostics, renders HTML,
EPUB, and every PDF profile, then runs the publication and PDF checks. Only its
bootstrap stage has network access; all rendering and validation stages remain
offline. EPUBCheck, Java, and Poppler all run inside that image; the CI host only
provides Podman.

The private-repository workflow runs on pushes, pull requests, and manual
dispatch. It has read-only source permission, does not retain checkout
credentials, pins the checkout action to a full commit SHA, and has no release,
deployment, external publishing, or artifact-upload step.

The locked Focal Poppler emits one obsolete parser diagnostic for Typst's valid
boolean `MarkInfo/Suspects` value. The PDF checker suppresses only that exact
message for Typst output and fails on every other `pdfinfo` diagnostic; page-box
and font checks remain active. Remove this compatibility allowance when the
base image moves to a newer Poppler.

Individual primary formats are available through `make render-html`,
`make render-epub`, `make render-typst`, and `make render-latex`. The two PDF
commands produce the primary 7 x 10 inch print profile. Use
`make render-print-6x9` for both economy-trim PDFs, `make render-review` for
both US Letter review PDFs, or `make render-pdf-profiles` for all six PDF
variants. Generated artifacts go under `book/_build/` and are ignored by Git.
After rendering all PDF variants, `make check-pdf-profiles` verifies every
media box and rejects fonts that are not both embedded and subset.

`make check-glyph-coverage` rejects manuscript characters outside the declared
Libertinus Serif coverage before rendering. `make render-locale-smoke` renders
an HTML edition with `fr-FR` document metadata and generated labels; it is a
translation/locale fixture, not an independently translated manuscript.

`make check-identities` validates explicit manuscript and registry IDs against
the committed identity ledger. After an intentional addition—or after recording
an explicit rename/removal migration—use `make update-identities`, review the
lockfile diff, and rerun the check. `make test-identities` exercises the invalid
and translated fixtures; `make check-rendered-identities` checks the resulting
HTML, EPUB, edition, and locale anchors after rendering.

`make check-editions` validates the whole-book source manifest, reduced-book
reference integrity, format compatibility, and public/private isolation.
`make render-edition-smoke` builds the abridged, preview, public, private, and
supplemental HTML variants used by the rendered acceptance suite. The primary
HTML command uses the `web` structure; EPUB and PDF commands use the core
`full` structure through their format-specific editions.

Use `make clean` to remove the build directory, Quarto cache, and known leaked
intermediates left by a failed or interrupted render. Its targets are explicit;
it does not remove manuscript sources or source assets.

## Updating

Treat a Quarto update as a dependency change:

1. Change the tag and digest in the Containerfile `FROM` instruction, then
   update the derived image tag in `scripts/lib/toolchain.sh`.
2. Select and record new Ubuntu and TeX Live snapshot dates, then update the
   Chrome and EPUBCheck archive checksums, installed tool hashes, TeX revisions,
   and font hashes in the Containerfile and `docs/toolchain-lock.md`.
3. Run the complete reference-book build.
4. Compare warnings, generated intermediates, and visual fixtures.
5. Record incompatibilities or migrations before accepting the update.

Do not use a floating image tag such as `latest` in normal builds.
