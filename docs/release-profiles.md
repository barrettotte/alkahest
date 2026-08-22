# Full and preview release profiles

Alkahest separates reusable release behavior from book-specific editorial
choices. In a minimal generated book, authors select one or two excerpt chapter
filenames in `book.toml`; numbered full chapters are discovered automatically,
and `make build` or `make excerpt` creates every profile and allowlist only in
ignored workspace state. The direct JSON workflow below remains the exhaustive
specimen and advanced engine contract.

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
`make excerpt` for the public HTML, EPUB, and Typst excerpt.

## Book-local contract

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

## Generated profiles and isolation

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
