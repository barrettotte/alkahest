# Reusable book contracts

`config/template/book-contracts.json` is the closed inventory of book-specific
facts that must survive engine upgrades. The engine owns each JSON Schema; a
book owns its matching record; generated adapters, when present, are disposable
outputs rebuilt from that record. This fixed order prevents reference-specimen
authors, identifiers, rights, or claims from leaking into a new book.

All schemas use JSON Schema draft 2020-12 and are bundled into the template
engine. `make check-book-contracts` performs dependency-free structural
validation, while the domain validator named below enforces deeper file,
render, and cross-record rules. Records use replacement composition: copy or
create the whole record for a book, rather than merging factual metadata with
the laboratory book.

## Stable IDs {#contract-stable-ids}

- Schema: `config/metadata/identities.schema.json`
- Book record: `book/identities.json`
- Deep validator: `scripts/check-identities.py`

Stable IDs, languages, registry paths, and explicit migrations belong to the
book. They must never be regenerated just because the engine is upgraded.

## Edition manifests {#contract-edition-manifests}

- Schema: `config/metadata/editions.schema.json`
- Book record: `book/editions.json`
- Deep validator: `scripts/check-editions.py`

Source availability, structures, formats, and access rules form a book-owned
allowlist. Engine profiles consume the manifest but do not add chapters to it.

## Publishing metadata {#contract-publishing-metadata}

- Schema: `config/metadata/publication.schema.json`
- Book record: `book/publication.json`
- Deep validator: `scripts/check-publication-metadata.py`

Work identity, contributors, publication facts, rights summaries, accessibility
discovery data, and provenance remain canonical here. The replaceable
`book/generated/metadata.yml` adapter is derived from those facts.

## Rights records {#contract-rights-records}

- Schema: `config/metadata/rights.schema.json`
- Book record: `book/assets.json`
- Deep validator: `scripts/check-asset-rights.py`

The book owns every permission, license, credit, provenance statement, and
distribution decision. `book/_build/release/rights-credits.json` is evidence,
not an override input.

## Accessibility metadata {#contract-accessibility-metadata}

- Schema: `config/metadata/accessibility.schema.json`
- Book record: `book/epub-accessibility.json`
- Deep validator: `scripts/check-epub-accessibility-policy.py`

Discovery metadata and conformance status are explicit book facts. Engine
capability never creates a conformance claim; manual review evidence remains
necessary where the selected standard requires it.

## Cover parameters {#contract-cover-parameters}

- Schema: `config/metadata/covers.schema.json`
- Book record: `config/covers/cover-policy.json`
- Deep validator: `scripts/check-covers.py`

Trim relationships, binding, paper, bleed, safe areas, finish, and vendor
status belong to the product. Generic development values cannot become
press-ready merely through inheritance.

## Localized labels {#contract-localized-labels}

- Schema: `config/metadata/localized-labels.schema.json`
- Book record: `config/localization/locales.json`
- Deep validator: `scripts/check-localization.py`

Locale tags, directions, translated labels, scripts, and toolchain requirements
are selected by the book. An engine upgrade may add support, but it cannot
silently add a language or claim translated content.

## Using the bundled contracts

Generated books receive the inventory as `book/.alkahest/book-contracts.json`
and the seven schemas under `book/.alkahest/schemas/`. These are engine evidence
and may be replaced during an engine upgrade. Book records remain outside that
directory and are never overwritten. Advanced records can be adopted one
domain at a time; `book/publication.json` is already present in every generated
book, and its generated adapter remains disposable.
