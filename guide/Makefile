.DEFAULT_GOAL := help

PODMAN ?= podman
IMAGE ?= localhost/alkahest-author-guide:development
ALK := $(PODMAN) run --rm --pull=never --network=none \
	--userns=keep-id --user "$$(id -u):$$(id -g)" \
	--security-opt label=disable \
	--tmpfs /tmp:rw,size=2g,mode=1777 \
	--env HOME=/tmp \
	--env JAVA_TOOL_OPTIONS=-Duser.home=/tmp \
	--env TEXMFCACHE=/tmp \
	--env TEXMFVAR=/tmp \
	--env XDG_CACHE_HOME=/tmp/cache \
	--volume "$(CURDIR):/book:rw" \
	--workdir /book \
	$(IMAGE)

.PHONY: help bootstrap chapter doctor draft check build build-all excerpt clean

help: ## Show the writer workflow.
	@awk 'BEGIN {FS = ":.*## "; printf "Usage: make <target>\n\n"} /^[a-zA-Z0-9_-]+:.*## / {printf "  %-12s %s\n", $$1, $$2}' $(MAKEFILE_LIST)

bootstrap: ## Build this book's rootless container from the Alkahest engine.
	$(PODMAN) build --pull=never --file Containerfile --tag $(IMAGE) .

chapter: ## Create the next numbered chapter: make chapter TITLE="My Chapter".
	@test -n "$(TITLE)" || (echo 'error: TITLE is required' >&2; exit 2)
	$(ALK) chapter "$(TITLE)"

doctor: ## Check book inputs and the local rendering environment.
	$(ALK) doctor

draft: ## Build the full HTML draft.
	$(ALK) draft

check: ## Validate book.toml and compile disposable workspaces.
	$(ALK) check

build: ## Build full HTML, EPUB, and production Typst editions.
	$(ALK) build

build-all: ## Also build the advanced LuaLaTeX edition.
	$(ALK) build-all

excerpt: ## Build the selected public HTML, EPUB, and Typst excerpt.
	$(ALK) excerpt

clean: ## Remove disposable build output.
	$(ALK) clean
