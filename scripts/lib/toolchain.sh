#!/usr/bin/env bash

readonly ALKAHEST_TOOLCHAIN_IMAGE="localhost/alkahest-publishing:quarto-1.10.18-v1"

alkahest_repo_root() {
  local script_dir
  script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
  cd "${script_dir}/../.." && pwd
}
