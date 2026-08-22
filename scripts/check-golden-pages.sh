#!/usr/bin/env bash
# Compare semantic PDF pages with committed visual baselines in the locked image.
set -euo pipefail

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=scripts/lib/toolchain.sh
source "${script_dir}/lib/toolchain.sh"
repo_root="$(alkahest_repo_root)"

if [[ "${ALKAHEST_GOLDEN_IN_CONTAINER:-0}" != "1" ]]; then
  invoking_uid="$(id -u)"
  invoking_gid="$(id -g)"
  if [[ "${invoking_uid}" -eq 0 ]]; then
    echo "error: golden-page checks must be run as a non-root host user" >&2
    exit 1
  fi
  if ! command -v podman >/dev/null 2>&1; then
    echo "error: Podman is required but was not found" >&2
    exit 1
  fi
  if ! podman image exists "${ALKAHEST_TOOLCHAIN_IMAGE}"; then
    echo "error: publishing image is not available locally" >&2
    echo "run ./scripts/bootstrap.sh once while connected to the network" >&2
    exit 1
  fi

  # Poppler 0.86.1 is pinned inside this image. Keep the mount writable only
  # for ignored QA output and the explicit baseline-update operation.
  exec podman run --rm \
    --pull=never \
    --network=none \
    --userns=keep-id \
    --user "${invoking_uid}:${invoking_gid}" \
    --security-opt label=disable \
    --env ALKAHEST_GOLDEN_IN_CONTAINER=1 \
    --volume "${repo_root}:/workspace:rw" \
    --workdir /workspace \
    --entrypoint /workspace/scripts/check-golden-pages.sh \
    "${ALKAHEST_TOOLCHAIN_IMAGE}" \
    "$@"
fi

if (($# == 0)); then
  set -- --artifacts
fi
exec python3 "${script_dir}/check-golden-pages.py" "$@"
