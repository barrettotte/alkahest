# Publication manifestations and identifiers

`book/manifestations.json` records product-level differences that do not belong
in the canonical work record. Its closed version 1 contract is
`config/metadata/manifestations.schema.json`.

A manifestation is one separately identifiable product or distribution form.
The current registry includes full web and EPUB outputs, two PDF sizes, an
internal review PDF, two planned print products, isolated HTML/EPUB/PDF preview
specimens, and private translation and supplemental web specimens. Planned
records may reserve an intent and dimensions, but cannot claim an artifact,
publication date, price, or availability.

Typst and LuaLaTeX outputs are renditions of the same manifestation when their
product metadata is identical. They remain independently tested PDF backends,
but they do not receive duplicate product records or identifiers. If a vendor,
accessibility treatment, file format, or edition later changes identifiers,
dimensions, cover, dates, pricing, or availability, add a manifestation rather
than hiding the difference in a rendition.

## Record contract

Every manifestation declares:

- a stable local ID, label, output format, variant, edition, language, and
  lifecycle status;
- typed publication identifiers;
- physical dimensions for PDF and print, with dimensions forbidden on
  reflowable web and EPUB records;
- an optional checksum-locked cover role and source path;
- announcement, publication, and withdrawal dates;
- zero or more currency/territory prices stored as exact two-decimal strings;
- availability status, territories, and distribution channels;
- the production profile, expected artifact path, and media type; and
- a typed relationship for previews, translations, review derivatives,
  supplemental products, and print interiors.

Relations must resolve without self-reference or cycles. A translation changes
language without changing format, a preview retains the full manifestation's
format, a PDF preview also retains its trim, and a print product points to a
dimension-matched PDF interior. Artifacts cannot be reused across records. The
validator also reconciles editions, locales, reproducible artifacts, primary
PDF preflight dimensions, and the distinct full/preview EPUB UUIDs with their
existing policies.

## Typed identifiers

Supported schemes are ISBN-10, ISBN-13, lowercase UUID URNs, lowercase DOI
names, and canonical HTTPS URLs. ISBN values use digits without punctuation
(with a final `X` permitted for ISBN-10), valid prefixes, and valid checksums.
If both ISBN forms are recorded, the conversion must identify the same product.
Identifier types cannot repeat within a manifestation, and the same typed
identifier cannot be reused by two manifestations. ISBNs are limited to EPUB,
PDF, and print products.

The development specimen intentionally has no ISBN, DOI, public URL, price, or
publication date. Stable, distinct UUID URNs identify its full and preview EPUB
packages for reproducible development builds. Add retail identifiers only when
a specific product has been selected; never copy one ISBN between print, EPUB,
PDF, or preview products.

Preview product presentation is separate from work-level metadata. The preview
profile overrides the product subtitle, description, and edition statement;
configures optional full-edition and purchase links; and controls a decorative
watermark. The current development manifestation leaves both URLs empty rather
than publishing placeholder destinations. Its cover field also remains null:
the profile supplies a clear title/notice treatment, while physical or
storefront cover files belong to the later dimension-aware cover pipeline.

The schema checks currency and territory code shape but does not claim that a
code is current. The later release/ONIX contract will pin external code-list
versions and map these internal values for distributors.

## Lifecycle and maintenance

The lifecycle and availability pairs are explicit:

| Lifecycle | Allowed availability |
|---|---|
| Planned | Unavailable |
| Development | Unavailable or private |
| Forthcoming | Unavailable or `preorder` |
| Published | Available |
| Withdrawn | Withdrawn |

`preorder` and available records require at least one channel. Private,
unavailable, and withdrawn records cannot carry channels; prices are allowed
only for `preorder` or available products. Publication and withdrawal dates must
agree with lifecycle state and remain chronologically valid.

After changing a manifestation, run:

```sh
make check-manifestations
make test-manifestations
```

Both targets use the shared source dispatcher and therefore also run during
ordinary renders and CI. The preview, French localization, and supplemental
records currently describe private acceptance specimens, not publishable
editions; later roadmap items add their release profiles and privacy gates.
