.DEFAULT_GOAL := help

UV ?= uv
ALK := $(UV) run --locked alkahest

.PHONY: help bootstrap doctor check test quality security render ci clean

help: ## Show the maintainer workflow.
	@awk 'BEGIN {FS = ":.*## "; printf "Usage: make <target>\n\n"} /^[a-zA-Z0-9_-]+:.*## / {printf "  %-12s %s\n", $$1, $$2}' $(MAKEFILE_LIST)

bootstrap: ## Build the pinned rootless publishing image.
	$(ALK) bootstrap

doctor: ## Verify the pinned Quarto container.
	$(ALK) doctor

check: ## Validate the reference source.
	$(ALK) check

test: ## Run the local test suite.
	$(ALK) test

quality: ## Run Ruff, BasedPyright, and pytest.
	$(ALK) quality

security: ## Scan Python source and dependencies.
	$(UV) run --locked --group security alkahest security

render: ## Build HTML, EPUB, and Typst outputs.
	$(ALK) render all

ci: ## Run the complete publishing pipeline.
	$(ALK) ci

clean: ## Remove disposable reference and guide output.
	rm -rf book/.quarto book/_build book/theme/fonts book/Alkahest-Reference-Book.tex book/index.typ \
		book/index_files book/reference_files guide/_build .pytest_cache .ruff_cache \
		.coverage htmlcov tools/.venv tools/writing/node_modules
