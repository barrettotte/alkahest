#!/usr/bin/env bash
# Build the pinned publishing toolchain container image.
set -euo pipefail

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=scripts/toolchain.sh
source "${script_dir}/toolchain.sh"

if ! command -v podman >/dev/null 2>&1; then
  echo "error: Podman is required but was not found" >&2
  exit 1
fi

repo_root="$(alkahest_repo_root)"

# Always re-resolve the digest-pinned base manifest. Build layers remain cached,
# while a missing or withdrawn upstream digest fails instead of falling back to
# an unrelated local tag.
podman build \
  --pull=always \
  --file "${repo_root}/Containerfile" \
  --tag "${ALKAHEST_TOOLCHAIN_IMAGE}" \
  "${repo_root}"
