# Compatibility, migrations, and template versions

`config/template/compatibility.json` defines the engine compatibility contract.
`config/template/releases.json` records versioned template artifacts separately
from book editions. The current 0.1.0 entry is deliberately marked
`private-development`: it has no publication date, Git tag, or release checksum,
and does not imply that this private repository has published anything.

Run `make check-compatibility` for the policy and
`make test-compatibility` for migration, stable-identity, deprecation, version,
and restoration fixtures.

## Semantic-version boundary

- Patch versions may contain compatible fixes, documentation, and corrections
  to disposable generated adapters.
- Minor versions may add backward-compatible features, optional record fields,
  or opt-in author syntax.
- Major versions may require record changes, remove previously deprecated
  syntax, or change the meaning of a book-owned contract.

Before 1.0, a minor engine version may still contain a breaking engine change,
but it must carry an explicit migration and release note. “Pre-1.0” is not an
excuse for silent source rewriting.

## Ownership during upgrades

Engine-owned files are the checksummed members recorded in a generated book's
`.alkahest/scaffold.json`; book records, manuscripts, assets, and intentional
theme/release overrides remain book-owned. An engine update may replace its
schemas, documentation, extensions, filters, and adapters. It may not overwrite
book records or stable content IDs.

The seven domains in `config/template/book-contracts.json` each declare a
current schema version, a contiguous supported-version window, protected JSON
Pointers, and an ordered migration chain. Version 1 is the initial schema for
every domain, so the canonical migration registry is currently empty. This is
intentional: no earlier generated-book contract exists to migrate.

## Migration files

When a schema changes, add
`config/template/migrations/<domain>-vN-to-vN+1.json`. Every migration must:

- advance exactly one schema version;
- contain explicit `up` and `down` object-only JSON Pointer operations;
- round-trip a representative old record byte-for-byte at the data-model level;
- preserve protected stable identities; and
- appear in its domain chain, the global registry, and the adopting template
  release.

Supported operations are `add`, `remove`, `replace`, and `rename`. They operate
on isolated copies and fail when a source is absent or a target already exists.
Identity changes do not belong in generic schema migrations: deliberate content
renames or retirements use the reasoned migration ledger in
`book/identities.json` so redirects and old references remain accountable.

## Deprecations

A deprecated surface must name its replacement, emit a warning, remain
available for at least one minor release, and declare removal in a later major
version. The registry is currently empty. Removal is rejected before its
declared version; public author syntax cannot simply disappear from a patch
release.

## Restoration and release evidence

The template engine package remains deterministic and locally checked. Its
release registry must match the package ID, version, and artifact filename.
Development entries cannot claim a publication date, Git tag, or checksum.
The private source archive restores the policy, schemas, tests, and package
inputs, then runs this compatibility group in the extracted tree. A future
public release will add real tag, date, and checksum evidence only when the
user explicitly authorizes a release.
