#!/usr/bin/env bash
# Define the shared toolchain image lock and repository path helper.

# Bump this tag whenever the Containerfile's effective toolchain changes. All
# wrappers consume the same constant so stale local images fail consistently.
readonly ALKAHEST_TOOLCHAIN_IMAGE="localhost/alkahest-publishing:quarto-1.10.18-v10"

alkahest_repo_root() {
  local script_dir
  # Resolve from this library's location so commands work from any directory.
  script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
  cd "${script_dir}/../.." && pwd
}
