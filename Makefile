.DEFAULT_GOAL := help

PUBLIC_TARGETS := bootstrap check render render-html render-epub render-pdf \
	render-typst render-latex render-preview render-all check-source check-preview \
	package-companion-bundles check-companion-bundles generate-covers \
	check-cover-artifacts generate-rights-report check-rights-report \
	package-template-engine check-template-package new-book generate-theme \
	check-theme-defaults generate-release-profiles check-release-profiles \
	check-extension-apis check-book-contracts \
	package-source-archive \
	check-source-archive check-writing ci clean help-all

.PHONY: bootstrap build-report check check-accessibility check-archive-policy check-asset-rights check-book-contracts check-companion-bundles check-cover-artifacts check-covers check-epub-accessibility check-epub-review check-extension-apis check-golden-pages check-manifestations check-metadata-generation check-new-book check-publication-metadata check-pdf-accessibility-policy check-pdf-preflight check-preview check-release-assets check-release-profiles check-reproducibility check-rights-report check-source check-source-archive check-template-engine check-template-package check-theme-defaults check-chemistry check-circuits check-computing-diagrams check-physics-diagrams check-rich-media check-pdf-backend-decision check-execution-policy check-graphs check-editions check-editorial-integrity check-learning check-companions check-reuse check-citations check-generated-lists check-glossary check-glyph-coverage check-icons check-identities check-index check-localization check-notes check-rendered-identities check-rendered-index check-rendered-lists check-rendered-localization check-rendered-notes check-publication check-pdf-profiles check-prose check-spelling check-writing check-writing-overrides check-writing-terminology check-writing-toolchain ci clean generate-chemistry generate-circuits generate-computing-diagrams generate-covers generate-metadata generate-physics-diagrams generate-publication-metadata generate-release-profiles generate-rich-media-fixtures generate-graphs generate-rights-report generate-theme generate-writing-terminology new-book package-companion-bundles package-source-archive package-template-engine prepare-epub-review render render-all render-preview test-accessibility test-asset-rights test-book-contracts test-companion-bundles test-covers test-epub-accessibility test-epub-review test-extension-apis test-golden-pages test-manifestations test-metadata-generation test-new-book test-preview test-publication-metadata test-release-profiles test-rights-report test-source-archive test-template-engine test-theme-defaults test-localization test-pdf-accessibility-policy test-pdf-preflight test-reproducibility test-source test-execution-policy test-editions test-editorial-integrity test-learning test-companions test-reuse test-citations test-generated-lists test-glossary test-identities test-index test-notes test-writing-overrides test-writing-quality update-golden-pages update-identities verify-reproducibility \
	render-html render-epub render-pdf render-typst render-latex render-print-6x9 render-review \
	render-pdf-profiles render-locale-smoke render-citation-smoke render-edition-smoke render-notes-smoke render-pdf-accessibility-smoke toolchain-report help help-all

bootstrap: ## Build the pinned local publishing container.
	./scripts/bootstrap.sh

build-report: ## Measure primary builds, warnings, and artifact sizes.
	./scripts/build-report.sh

check: ## Report Quarto and publishing-toolchain diagnostics.
	./scripts/quarto.sh check

check-source: ## Validate every configured semantic source policy.
	python3 scripts/check-source.py

test-source: ## Exercise every semantic source-policy fixture suite.
	python3 scripts/check-source.py --tests

check-execution-policy: ## Reject executable manuscript cells and policy overrides.
	python3 scripts/check-source.py execution-policy

test-execution-policy: ## Exercise static-only source and execution-policy contracts.
	python3 scripts/check-source.py --tests execution-policy

check-reproducibility: ## Validate exact fingerprints and stable artifact metadata.
	python3 scripts/check-reproducibility.py --artifacts

test-reproducibility: ## Exercise policy, metadata, and exact-fingerprint failures.
	python3 scripts/check-source.py --tests reproducibility

verify-reproducibility: ## Rebuild and byte-compare every distributable artifact.
	python3 scripts/check-reproducibility.py --repeat full

check-golden-pages: ## Compare fragile PDF pages with committed visual baselines.
	./scripts/check-golden-pages.sh

test-golden-pages: ## Exercise golden policy, PNG, pixel, and coverage contracts.
	python3 scripts/check-source.py --tests golden-pages

update-golden-pages: ## Deliberately replace golden pages from current primary PDFs.
	./scripts/check-golden-pages.sh --update

check-publication-metadata: ## Validate canonical work metadata and current adapter parity.
	python3 scripts/check-source.py publication-metadata

test-publication-metadata: ## Exercise metadata schema, semantics, and adapter drift fixtures.
	python3 scripts/check-source.py --tests publication-metadata

check-manifestations: ## Validate product variants, relations, and typed identifiers.
	python3 scripts/check-source.py manifestations

test-manifestations: ## Exercise ISBN, product metadata, and adapter drift fixtures.
	python3 scripts/check-source.py --tests manifestations

check-covers: ## Validate cover geometry inputs and manifestation relationships.
	python3 scripts/check-source.py covers

test-covers: ## Exercise invalid cover policies, geometry, and stale artifacts.
	python3 scripts/check-source.py --tests covers

generate-covers: ## Generate wrap templates, thumbnails, and geometry manifests.
	./scripts/python-tools.sh scripts/generate-covers.py

check-cover-artifacts: ## Verify cover geometry against selected interior PDFs.
	./scripts/python-tools.sh scripts/check-cover-artifacts.py

generate-publication-metadata: ## Regenerate shared output and release metadata adapters.
	python3 scripts/generate-publication-metadata.py

generate-metadata: generate-publication-metadata ## Regenerate publication metadata (short alias).

check-metadata-generation: ## Reject stale adapters and drifting pinned ONIX mappings.
	python3 scripts/check-source.py metadata-generation

test-metadata-generation: ## Exercise deterministic output and ONIX mapping fixtures.
	python3 scripts/check-source.py --tests metadata-generation

generate-graphs: ## Regenerate committed graph/chart derivatives from source data.
	python3 scripts/generate-graphs.py

check-graphs: ## Validate diagram sources and deterministic chart derivatives.
	python3 scripts/check-source.py graphs

generate-circuits: ## Regenerate committed electrical-circuit SVG derivatives.
	./scripts/python-tools.sh scripts/generate-circuits.py

check-circuits: ## Validate circuit candidates and deterministic SVG derivatives.
	python3 scripts/check-source.py circuits

generate-chemistry: ## Regenerate committed chemistry SVG derivatives.
	./scripts/python-tools.sh scripts/generate-chemistry.py

check-chemistry: ## Validate chemistry candidates and deterministic SVG derivatives.
	python3 scripts/check-source.py chemistry

generate-computing-diagrams: ## Regenerate committed computing-diagram SVG derivatives.
	python3 scripts/generate-computing-diagrams.py

check-computing-diagrams: ## Validate computing-diagram data, candidates, and SVG derivatives.
	python3 scripts/check-source.py computing-diagrams

generate-physics-diagrams: ## Regenerate committed physics-diagram SVG derivatives.
	python3 scripts/generate-physics-diagrams.py

check-physics-diagrams: ## Validate physics data, units, precision, provenance, and SVG derivatives.
	python3 scripts/check-source.py physics-diagrams

generate-rich-media-fixtures: ## Regenerate the deterministic rich-media audio fixture.
	python3 scripts/generate-rich-media-fixtures.py

check-rich-media: ## Validate rich-media assets, accessibility, rights, and fallbacks.
	python3 scripts/check-source.py rich-media

check-asset-rights: ## Validate asset rights, checksums, coverage, and source privacy.
	python3 scripts/check-source.py asset-rights

test-asset-rights: ## Exercise rights, metadata, package, and privacy failures.
	python3 scripts/check-source.py --tests asset-rights

generate-rights-report: ## Build deterministic human and machine rights reports.
	python3 scripts/generate-rights-report.py

check-rights-report: ## Verify release rights, credits, coverage, and report bytes.
	python3 scripts/check-rights-report.py

test-rights-report: ## Exercise rights inventory and stale-report failures.
	python3 scripts/check-source.py --tests rights-report

check-archive-policy: ## Validate private source-archive selection and history policy.
	python3 scripts/check-source.py source-archive

package-source-archive: ## Build a deterministic private recovery source ZIP.
	python3 scripts/package-source-archive.py

check-source-archive: ## Verify exact source ZIP bytes and a fresh restoration smoke.
	python3 scripts/check-source-archive.py

test-source-archive: ## Exercise source-archive policy, drift, and safety failures.
	python3 scripts/check-source.py --tests source-archive

check-template-engine: ## Validate the reusable template-engine extraction boundary.
	python3 scripts/check-source.py template-engine

package-template-engine: ## Build the deterministic reusable template-engine ZIP.
	python3 scripts/package-template-engine.py

check-template-package: ## Verify exact template-engine bytes and extracted structure.
	python3 scripts/check-template-package.py

test-template-engine: ## Exercise template extraction, drift, and safety failures.
	python3 scripts/check-source.py --tests template-engine

new-book: ## Create a minimal independent book (set DEST, TITLE, and AUTHOR).
	@test -n "$(DEST)" || { printf '%s\n' 'error: DEST is required' >&2; exit 2; }
	@test -n "$(TITLE)" || { printf '%s\n' 'error: TITLE is required' >&2; exit 2; }
	@test -n "$(AUTHOR)" || { printf '%s\n' 'error: AUTHOR is required' >&2; exit 2; }
	python3 scripts/new-book.py --destination "$(DEST)" --title "$(TITLE)" --author "$(AUTHOR)" $(if $(BOOK_ID),--book-id "$(BOOK_ID)") $(if $(SUBTITLE),--subtitle "$(SUBTITLE)") $(if $(LANGUAGE),--language "$(LANGUAGE)") $(if $(CREATED),--created "$(CREATED)")

check-new-book: ## Validate and smoke-test deterministic book creation.
	python3 scripts/check-source.py new-book

test-new-book: ## Exercise new-book metadata, input, overwrite, and drift fixtures.
	python3 scripts/check-source.py --tests new-book

generate-theme: ## Resolve shared defaults and book-local theme overrides.
	python3 scripts/sync-theme.py

check-theme-defaults: ## Verify shared theme policy and exact format adapters.
	python3 scripts/check-source.py theme-defaults

test-theme-defaults: ## Exercise theme inheritance, schema, and stale-output failures.
	python3 scripts/check-source.py --tests theme-defaults

generate-release-profiles: ## Resolve reusable full/preview profiles and book overrides.
	python3 scripts/sync-release-profiles.py

check-release-profiles: ## Verify release allowlists, metadata, and exact profiles.
	python3 scripts/check-source.py release-profiles

test-release-profiles: ## Exercise release schema, isolation, and stale-output failures.
	python3 scripts/check-source.py --tests release-profiles

check-extension-apis: ## Validate the shipped extension API inventory and reference.
	python3 scripts/check-source.py extension-apis

test-extension-apis: ## Exercise extension API schema, path, and coverage failures.
	python3 scripts/check-source.py --tests extension-apis

check-book-contracts: ## Validate reusable schemas and book-owned override layers.
	python3 scripts/check-source.py book-contracts

test-book-contracts: ## Exercise contract inventory, schema, and record failures.
	python3 scripts/check-source.py --tests book-contracts

check-pdf-backend-decision: ## Validate the scored PDF default and compatibility policy.
	python3 scripts/check-source.py pdf-backend

check-editions: ## Validate whole-book manifests, sources, privacy, and references.
	python3 scripts/check-source.py editions

test-editions: ## Exercise valid, invalid, and staged edition contracts.
	python3 scripts/check-source.py --tests editions

check-editorial-integrity: ## Validate source links, alternatives, IDs, and references.
	python3 scripts/check-source.py editorial-integrity

test-editorial-integrity: ## Exercise valid and invalid editorial-integrity contracts.
	python3 scripts/check-source.py --tests editorial-integrity

check-learning: ## Validate learning roles, metadata, pairings, and private answers.
	python3 scripts/check-source.py learning

test-learning: ## Exercise invalid learning-role, pairing, and privacy contracts.
	python3 scripts/check-source.py --tests learning

check-companions: ## Validate companion metadata, checksums, delivery, and references.
	python3 scripts/check-source.py companions

test-companions: ## Exercise invalid companion registry, file, and reference contracts.
	python3 scripts/check-source.py --tests companions

package-companion-bundles: ## Build deterministic versioned companion ZIP packages.
	python3 scripts/package-companion-bundles.py

check-companion-bundles: ## Verify companion ZIP contents, licenses, and checksums.
	python3 scripts/check-companion-bundles.py

test-companion-bundles: ## Exercise deterministic and stale companion package fixtures.
	python3 scripts/test-companion-bundles.py

check-reuse: ## Validate reusable fragments, parameters, contexts, and use sites.
	python3 scripts/check-source.py reuse

test-reuse: ## Exercise invalid reusable-content and dependency contracts.
	python3 scripts/check-source.py --tests reuse

check-citations: ## Validate citation styles, bibliography keys, and manuscript calls.
	python3 scripts/check-source.py citations

test-citations: ## Exercise valid and invalid citation contracts.
	python3 scripts/check-source.py --tests citations

check-generated-lists: ## Validate configured reference and terminology lists.
	python3 scripts/check-source.py generated-lists

test-generated-lists: ## Exercise valid and invalid generated-list contracts.
	python3 scripts/check-source.py --tests generated-lists

check-glossary: ## Validate glossary entries, aliases, forms, and references.
	python3 scripts/check-source.py glossary

test-glossary: ## Exercise valid and invalid glossary contracts.
	python3 scripts/check-source.py --tests glossary

check-glyph-coverage: ## Reject manuscript glyphs outside the declared font stack.
	./scripts/check-glyph-coverage.sh

check-localization: ## Validate locale profiles, scripts, glyphs, and language behavior.
	python3 scripts/check-source.py localization
	./scripts/check-glyph-coverage.sh

test-localization: ## Exercise localization source and rendered-output contracts.
	python3 scripts/check-source.py --tests localization

check-icons: ## Validate semantic icon names, assets, aliases, and calls.
	python3 scripts/check-source.py icons

check-identities: ## Validate persistent IDs, variants, assets, and the identity lock.
	python3 scripts/check-source.py identities

test-identities: ## Exercise identity uniqueness, translation, edition, and migration rules.
	python3 scripts/check-source.py --tests identities

update-identities: ## Lock intentional identity additions and recorded migrations.
	python3 scripts/update-identities.py

check-index: ## Validate subject/person index entries, markers, ranges, and relations.
	python3 scripts/check-source.py index

test-index: ## Exercise valid and invalid subject/person index contracts.
	python3 scripts/check-source.py --tests index

check-notes: ## Validate semantic note definitions, repeats, and placements.
	python3 scripts/check-source.py notes

test-notes: ## Exercise valid and invalid semantic-note contracts.
	python3 scripts/check-source.py --tests notes

check-rendered-notes: ## Verify rendered chapter, book, and sidenote behavior.
	./scripts/check-rendered-notes.sh

check-rendered-identities: ## Verify IDs survive rendered editions and locales.
	./scripts/check-rendered-identities.sh

check-rendered-index: ## Verify linked reflowable and page-resolved print indexes.
	./scripts/check-rendered-index.sh

check-rendered-lists: ## Verify generated lists, links, numbering, and empty omission.
	./scripts/check-rendered-lists.sh

check-rendered-localization: ## Verify HTML/EPUB languages, RTL, labels, and hyphenation.
	python3 scripts/check-rendered-localization.py

check-release-assets: ## Verify release rights coverage and reject private metadata.
	./scripts/check-release-assets.sh

check-publication: ## Verify links, editions, IDs, assets, privacy, and numbering.
	./scripts/check-publication.sh

check-preview: ## Validate preview privacy, metadata, navigation, and formats.
	./scripts/check-preview.sh

test-preview: ## Exercise preview artifact and privacy validation failures.
	python3 scripts/test-preview.py

check-accessibility: ## Gate rendered HTML against WCAG 2.2 A/AA automation.
	./scripts/check-accessibility.sh

test-accessibility: ## Exercise accessibility policy and browser-rule fixtures.
	./scripts/check-accessibility.sh test

check-epub-accessibility: ## Gate EPUB structure, accessibility automation, and review policy.
	./scripts/check-epub-accessibility.sh

test-epub-accessibility: ## Exercise EPUB semantics, automation, and manual-review fixtures.
	./scripts/check-epub-accessibility.sh test

check-epub-review: ## Validate the manual EPUB reader matrix and evidence ledger.
	python3 scripts/check-epub-reading-system-review.py

test-epub-review: ## Exercise manual EPUB evidence and conformance-claim contracts.
	python3 scripts/test-epub-reading-system-review.py

prepare-epub-review: ## Bind a clean revision and rendered EPUB to manual review evidence.
	python3 scripts/prepare-epub-review.py

check-pdf-profiles: ## Verify PDF layout, content, and print-preflight contracts.
	./scripts/check-pdf-profiles.sh

check-pdf-preflight: ## Check PDF boxes, fonts, resolution, and color spaces.
	./scripts/check-pdf-preflight.sh

test-pdf-preflight: ## Exercise valid and invalid PDF preflight fixtures.
	python3 scripts/test-pdf-preflight.py

check-pdf-accessibility-policy: ## Validate PDF/UA evidence and prevent premature claims.
	python3 scripts/check-source.py pdf-accessibility-policy

test-pdf-accessibility-policy: ## Exercise PDF/UA evidence and claim-state fixtures.
	python3 scripts/check-source.py --tests pdf-accessibility-policy

check-writing-toolchain: ## Verify pinned Vale and CSpell tools offline and rootless.
	./scripts/check-writing-toolchain.sh

check-writing: ## Gate spelling/terminology and report subjective prose warnings.
	./scripts/check-writing.sh

check-spelling: ## Gate CSpell findings in canonical authored sources.
	./scripts/check-writing.sh spelling

check-prose: ## Gate rejected terms and report subjective Vale warnings.
	./scripts/check-writing.sh prose

check-writing-terminology: ## Validate accepted words and generated rejected-term rules.
	python3 scripts/generate-writing-terminology.py --check

check-writing-overrides: ## Validate narrow, balanced, and justified writing overrides.
	python3 scripts/check-writing-overrides.py

test-writing-overrides: ## Exercise valid and invalid writing-override policy fixtures.
	python3 scripts/test-writing-overrides.py

test-writing-quality: ## Exercise pinned positive and negative writing fixtures.
	python3 scripts/test-writing-quality.py

generate-writing-terminology: ## Regenerate CSpell and Vale terminology derivatives.
	python3 scripts/generate-writing-terminology.py

ci: ## Run the complete local/CI publishing validation pipeline.
	./scripts/ci.sh

toolchain-report: ## Report immutable sources, exact tools, font packages, and hashes.
	./scripts/toolchain-report.sh

clean: ## Remove generated books, intermediates, and Quarto caches.
	podman unshare rm -rf \
		book/.quarto \
		book/_build \
		book/index_files \
		book/reference_files \
		book/references_files \
		book/icons/*.pdf \
		book/site_libs \
		book/theme/fonts \
		book/Alkahest-Reference-Book.epub \
		book/Alkahest-Reference-Book.pdf \
		book/Alkahest-Reference-Book.tex \
		book/index.html \
		book/index.log \
		book/index.tex \
		book/index.typ \
		book/reference.html \
		book/references.html

render: ## Render HTML, EPUB, and both primary 7 x 10 PDFs.
	./scripts/render.sh all

render-all: ## Render the complete publication and smoke-profile suite.
	./scripts/render.sh complete

render-html: ## Render the HTML web book.
	./scripts/render.sh html

render-epub: ## Render the reflowable EPUB book.
	./scripts/render.sh epub

render-pdf: ## Render the default primary 7 x 10 Typst PDF.
	./scripts/render.sh pdf

render-typst: ## Render the primary 7 x 10 PDF with Typst.
	./scripts/render.sh typst

render-latex: ## Render the primary 7 x 10 PDF with LuaLaTeX.
	./scripts/render.sh latex

render-print-6x9: ## Render both 6 x 9 economy-print PDFs.
	./scripts/render.sh print-6x9

render-review: ## Render both US Letter review PDFs.
	./scripts/render.sh review

render-preview: ## Render the curated HTML, EPUB, and PDF preview products.
	./scripts/render.sh preview

render-pdf-profiles: ## Render every Typst and LuaLaTeX PDF profile.
	./scripts/render.sh pdf-profiles

render-locale-smoke: ## Render the French-locale HTML smoke edition.
	./scripts/render.sh locale-smoke

render-citation-smoke: ## Render numeric-citation HTML and Typst smoke editions.
	./scripts/render.sh citation-smoke

render-edition-smoke: ## Render reduced HTML editions plus HTML, EPUB, and PDF previews.
	./scripts/render.sh edition-smoke

render-notes-smoke: ## Render chapter, book, and sidenote placement editions.
	./scripts/render.sh notes-smoke

render-pdf-accessibility-smoke: ## Render separate Typst PDF/UA-1 and LuaLaTeX PDF/UA-2 evaluations.
	./scripts/render.sh pdf-accessibility-smoke

help: ## Show the common author workflow commands.
	@printf 'Common author commands:\n'
	@for target in $(PUBLIC_TARGETS); do \
		awk -v target="$$target" 'BEGIN { FS = ":.*## " } $$1 == target { printf "  %-30s %s\n", $$1, $$2 }' $(MAKEFILE_LIST); \
	done
	@printf '\nRun make help-all for maintainer, fixture, and specialist commands.\n'

help-all: ## Show every available Make target and its description.
	@awk 'BEGIN { FS = ":.*## " } /^[[:alnum:]_-]+:.*## / { printf "  %-30s %s\n", $$1, $$2 }' $(MAKEFILE_LIST)
