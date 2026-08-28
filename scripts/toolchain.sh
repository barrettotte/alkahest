#!/usr/bin/env bash
# Define the shared toolchain image lock and repository path helper.

# Bootstrap replaces this development image with the current local toolchain.
readonly ALKAHEST_TOOLCHAIN_IMAGE="localhost/alkahest-publishing:development"

alkahest_repo_root() {
  local script_dir
  # Resolve from this library's location so commands work from any directory.
  script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
  cd "${script_dir}/.." && pwd
}
