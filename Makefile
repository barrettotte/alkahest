.PHONY: bootstrap build-report check check-editions check-citations check-generated-lists check-glossary check-glyph-coverage check-icons check-identities check-index check-notes check-rendered-identities check-rendered-index check-rendered-lists check-rendered-notes check-publication check-pdf-profiles ci clean render render-all test-editions test-citations test-generated-lists test-glossary test-identities test-index test-notes update-identities \
	render-html render-epub render-typst render-latex render-print-6x9 render-review \
	render-pdf-profiles render-locale-smoke render-citation-smoke render-edition-smoke render-notes-smoke toolchain-report help

bootstrap: ## Build the pinned local publishing container.
	./scripts/bootstrap

build-report: ## Measure primary builds, warnings, and artifact sizes.
	./scripts/build-report

check: ## Report Quarto and publishing-toolchain diagnostics.
	./scripts/quarto check

check-editions: ## Validate whole-book manifests, sources, privacy, and references.
	./scripts/check-editions

test-editions: ## Exercise valid, invalid, and staged edition contracts.
	./scripts/test-editions

check-citations: ## Validate citation styles, bibliography keys, and manuscript calls.
	./scripts/check-citations

test-citations: ## Exercise valid and invalid citation contracts.
	./scripts/test-citations

check-generated-lists: ## Validate configured reference and terminology lists.
	./scripts/check-generated-lists

test-generated-lists: ## Exercise valid and invalid generated-list contracts.
	./scripts/test-generated-lists

check-glossary: ## Validate glossary entries, aliases, forms, and references.
	./scripts/check-glossary

test-glossary: ## Exercise valid and invalid glossary contracts.
	./scripts/test-glossary

check-glyph-coverage: ## Reject manuscript glyphs outside the declared font stack.
	./scripts/check-glyph-coverage

check-icons: ## Validate semantic icon names, assets, aliases, and calls.
	./scripts/check-icons

check-identities: ## Validate persistent IDs, variants, assets, and the identity lock.
	./scripts/check-identities

test-identities: ## Exercise identity uniqueness, translation, edition, and migration rules.
	./scripts/test-identities

update-identities: ## Lock intentional identity additions and recorded migrations.
	./scripts/update-identities

check-index: ## Validate subject/person index entries, markers, ranges, and relations.
	./scripts/check-index

test-index: ## Exercise valid and invalid subject/person index contracts.
	./scripts/test-index

check-notes: ## Validate semantic note definitions, repeats, and placements.
	./scripts/check-notes

test-notes: ## Exercise valid and invalid semantic-note contracts.
	./scripts/test-notes

check-rendered-notes: ## Verify rendered chapter, book, and sidenote behavior.
	./scripts/check-rendered-notes

check-rendered-identities: ## Verify IDs survive rendered editions and locales.
	./scripts/check-rendered-identities

check-rendered-index: ## Verify linked reflowable and page-resolved print indexes.
	./scripts/check-rendered-index

check-rendered-lists: ## Verify generated lists, links, numbering, and empty omission.
	./scripts/check-rendered-lists

check-publication: ## Validate internal HTML links and EPUB conformance.
	./scripts/check-publication

check-pdf-profiles: ## Verify PDF dimensions and embedded/subset fonts.
	./scripts/check-pdf-profiles

ci: ## Run the complete local/CI publishing validation pipeline.
	./scripts/ci

toolchain-report: ## Report immutable sources, exact tools, font packages, and hashes.
	./scripts/toolchain-report

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
	./scripts/render all

render-all: ## Render HTML, EPUB, and every PDF profile.
	./scripts/render complete

render-html: ## Render the HTML web book.
	./scripts/render html

render-epub: ## Render the reflowable EPUB book.
	./scripts/render epub

render-typst: ## Render the primary 7 x 10 PDF with Typst.
	./scripts/render typst

render-latex: ## Render the primary 7 x 10 PDF with LuaLaTeX.
	./scripts/render latex

render-print-6x9: ## Render both 6 x 9 economy-print PDFs.
	./scripts/render print-6x9

render-review: ## Render both US Letter review PDFs.
	./scripts/render review

render-pdf-profiles: ## Render every Typst and LuaLaTeX PDF profile.
	./scripts/render pdf-profiles

render-locale-smoke: ## Render the French-locale HTML smoke edition.
	./scripts/render locale-smoke

render-citation-smoke: ## Render numeric-citation HTML and Typst smoke editions.
	./scripts/render citation-smoke

render-edition-smoke: ## Render abridged, preview, public, private, and supplemental editions.
	./scripts/render edition-smoke

render-notes-smoke: ## Render chapter, book, and sidenote placement editions.
	./scripts/render notes-smoke

help: ## Show available Make targets and their descriptions.
	@awk 'BEGIN { FS = ":.*## " } /^[[:alnum:]_-]+:.*## / { printf "  %-24s %s\n", $$1, $$2 }' $(MAKEFILE_LIST)
