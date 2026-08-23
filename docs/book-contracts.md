# Book-owned records

The presentation engine supplies format behavior and defaults. Each book owns
its manuscripts and factual publishing records. Generated adapters are
disposable outputs rebuilt from those sources; they are never another place an
author must keep synchronized.

The normal generated-book workflow compiles the common facts in `book.toml`
into ignored workspace records. Authors only add an advanced registry when a
book actually needs the corresponding feature.

## Stable identities and editions

`book/identities.json` owns persistent content IDs and language variants.
`book/editions.json` owns source availability, structures, formats, and privacy
rules. Validate them with `alkahest check identities` and `alkahest check
editions`.

## Publication and rights facts

`book/publication.json` is the canonical source for work identity,
contributors, rights summaries, accessibility discovery data, and provenance.
Its directly used JSON Schema is `config/metadata/publication.schema.json`.
`book/assets.json` owns permissions, licenses, credits, provenance, and public
distribution decisions. Validate them with `alkahest check
publication-metadata` and `alkahest check asset-rights`.

## Accessibility, covers, and localization

`book/epub-accessibility.json` records accessibility policy without claiming
conformance before review. `config/covers/cover-policy.json` owns trim,
binding, paper, bleed, safe-area, and vendor decisions.
`config/localization/locales.json` owns supported locales, translated labels,
scripts, and toolchain requirements. Their focused checks remain authoritative.

## Ownership rule

Template updates may replace engine defaults and generated adapters. They must
not overwrite manuscripts, `book.toml`, stable identities, publication facts,
rights decisions, edition choices, or other book-owned records. This human
guidance is intentionally the single ownership reference until a public
template release creates a need for a formal external contract.
