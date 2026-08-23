# Generated publication metadata

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

## ONIX boundary

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
