# Canonical publication metadata

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

## Work and manifestation boundary

This record describes the intellectual work and facts shared by its outputs. A
manifestation is a particular HTML site, EPUB, PDF, print trim, preview,
translation, or other product. ISBNs and other product identifiers, dimensions,
covers, dates, prices, availability, and format-specific accessibility claims
belong to the records defined in [`manifestations.md`](manifestations.md), not
this work record. That separation prevents one ISBN or price from leaking
across unlike products.

The reference specimen remains in `development` status. Its publication date,
publisher, imprint, copyright year, source URL, and publication-text license
are therefore null or explicitly undecided rather than filled with plausible
but false values. A forthcoming or published work must supply the applicable
date and publisher; a published work must also supply its copyright year.

## Generated adapters

The deterministic generator now supplies facts consumed by the toolchain:

- Quarto title, subtitle, author, and language;
- EPUB language, accessibility discovery terms, summary, standard, and review
  status; and
- PDF title and author expectations in the release-asset policy.

The EPUB identifier is typed in the manifestation registry and checked against
the reproducibility policy. The generated `alkahest` map supplies print and
reflowable publication-data pages without duplicating work facts in
`_quarto.yml`. [`metadata-generation.md`](metadata-generation.md) documents the
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
