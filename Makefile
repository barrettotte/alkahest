.DEFAULT_GOAL := help

UV ?= uv
ALK := $(UV) run --locked alkahest

.PHONY: help list bootstrap doctor check check-source test test-source quality security \
	render render-all preview generate package new-book ci clean \
	build-report toolchain-report verify-reproducibility update-golden-pages \
	generate-metadata

help: ## Show the concise toolkit workflow.
	@printf 'Alkahest toolkit commands:\n'
	@awk 'BEGIN {FS = ":.*## "} /^[[:alnum:]_-]+:.*## / {printf "  %-18s %s\n", $$1, $$2}' $(MAKEFILE_LIST)
	@printf '\nUse make list for specialist check, test, render, generate, and package names.\n'

list: ## List every registered specialist task.
	$(ALK) list

bootstrap: ## Build the pinned rootless publishing image.
	$(ALK) bootstrap

doctor: ## Report publishing-toolchain diagnostics.
	$(ALK) doctor

check: ## Run all semantic source checks, or set TASK=name.
	$(ALK) check $(TASK)

check-source: check ## Run every semantic source check.

test: ## Run all semantic fixture suites, or set TASK=name.
	$(ALK) test $(TASK)

test-source: test ## Run every semantic fixture suite.

quality: ## Run Ruff, mypy, and pytest through the locked uv environment.
	$(ALK) quality

security: ## Scan Python source and dependencies; requires network access.
	$(UV) run --locked --group security alkahest security

render: ## Render primary HTML, EPUB, Typst, and LuaLaTeX outputs.
	$(ALK) render all

render-all: ## Render the complete publication and smoke-profile suite.
	$(ALK) render complete

preview: ## Render the curated public preview products.
	$(ALK) render preview

generate: ## Run a generator selected with TASK=name.
	@test -n "$(TASK)" || { printf '%s\n' 'error: TASK is required; run make list' >&2; exit 2; }
	$(ALK) generate $(TASK)

package: ## Build a package selected with TASK=name.
	@test -n "$(TASK)" || { printf '%s\n' 'error: TASK is required; run make list' >&2; exit 2; }
	$(ALK) package $(TASK)

new-book: ## Create a minimal book; set DEST, TITLE, and AUTHOR.
	@test -n "$(DEST)" || { printf '%s\n' 'error: DEST is required' >&2; exit 2; }
	@test -n "$(TITLE)" || { printf '%s\n' 'error: TITLE is required' >&2; exit 2; }
	@test -n "$(AUTHOR)" || { printf '%s\n' 'error: AUTHOR is required' >&2; exit 2; }
	$(ALK) new-book --destination "$(DEST)" --title "$(TITLE)" --author "$(AUTHOR)" $(if $(BOOK_ID),--book-id "$(BOOK_ID)") $(if $(SUBTITLE),--subtitle "$(SUBTITLE)") $(if $(LANGUAGE),--language "$(LANGUAGE)") $(if $(CREATED),--created "$(CREATED)")

ci: ## Run the complete local and CI publishing pipeline.
	$(ALK) ci

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

# Pattern targets preserve familiar specialist commands without duplicating
# their implementation or descriptions in this file.
check-%:
	$(ALK) check $*

test-%:
	$(ALK) test $*

render-%:
	$(ALK) render $*

generate-%:
	$(ALK) generate $*

package-%:
	$(ALK) package $*

build-report:
	$(ALK) report build

toolchain-report:
	$(ALK) report toolchain

verify-reproducibility:
	$(UV) run --locked python -m alkahest.checks.reproducibility --repeat full

update-golden-pages:
	./scripts/python-tools.sh -m alkahest.checks.golden_pages --update

generate-metadata:
	$(ALK) generate publication-metadata
