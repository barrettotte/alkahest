# Private source archives

The archival source package is a private recovery snapshot, not a public book
release. It preserves the inputs needed to understand, validate, and rebuild
the project without retaining Git internals, rendered outputs, caches, installed
dependencies, or machine-local state. Because a complete recovery snapshot
includes private manuscripts and test canaries, do not attach it to a public
release or distribute it with reader-facing formats.

`config/archive/source-package.json` is the closed package contract. It fixes
the package ID and semantic version, deterministic stored-ZIP format, output
path, exact top-level file coverage, selected source roots, exclusions,
required roles, dependency records, and restoration smoke. A new top-level
file fails validation until it is deliberately included or moved under a
governed root. Symlinks and selected entries that are not regular files are
rejected.

Run:

```sh
make check-archive-policy
make test-source-archive
make package-source-archive
make check-source-archive
```

The package and its outer SHA-256 sidecar are written to
`book/_build/archive/` and ignored by Git. Every ZIP member has the frozen
reproducibility timestamp, regular-file mode, stored compression, and sorted
path order. The rooted archive contains:

- canonical manuscripts, private sources, extensions, templates, filters, and
  source assets;
- publication metadata, manifestations, rights registries, license evidence,
  stable identities, and edition policy;
- the Containerfile, Python and writing manifests/locks, and the human
  toolchain lock record;
- build instructions, documentation, tests, changelog, redirect registry, and
  prior-edition registry;
- `.archive/DEPENDENCIES.json`, `.archive/MANIFEST.json`,
  `.archive/README.md`, and an internal `.archive/SHA256SUMS` inventory.

Generated HTML, EPUB, PDFs, covers, companion ZIPs, rights reports, installed
fonts, Quarto caches, and `node_modules` are intentionally omitted because they
are reproducible products or replaceable dependencies. Reader-facing release
artifacts have separate reproducibility, rights, accessibility, and privacy
checks.

`make check-source-archive` first reproduces the ZIP and sidecar byte-for-byte,
then validates paths, member coverage, timestamp, mode, order, compression,
manifest, and internal checksums. It extracts the package into a fresh
temporary directory, runs `make help`, and executes the configured non-mutating
semantic source groups there, including the archive policy itself. Keeping
generated package records below `.archive/` means they do not violate restored
top-level source coverage. The smoke includes the template engine, new-book
generator, reusable release-profile contracts, extension APIs, and book-record
schemas. CI performs this restoration
smoke on every run.
A full render remains a deliberate periodic recovery drill after rebuilding or
obtaining the locked container image; the archive itself never accesses the
network.

## History continuity

`CHANGELOG.md` records unreleased and reader-visible changes.
`book/redirects.json` owns durable old-to-new web paths with an effective date
and reason. `book/prior-editions.json` records each published predecessor's
edition statement, publication date, identifiers, durable archive URI, and
manifest checksum. Both registries are empty for the unreleased specimen but
are validated now so later editions cannot invent incompatible history fields.

Increment the source-package version when its recovery contract or intentionally
captured source state is designated as an archival milestone. Record a released
predecessor only after its immutable archive URI and manifest checksum exist;
do not create placeholder publication history.
