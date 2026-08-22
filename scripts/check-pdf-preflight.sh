#!/usr/bin/env bash
# Run PDF print-preflight inspection inside the locked rootless toolchain.
set -euo pipefail

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=scripts/lib/toolchain.sh
source "${script_dir}/lib/toolchain.sh"
repo_root="$(alkahest_repo_root)"

if [[ "${ALKAHEST_PDF_PREFLIGHT_IN_CONTAINER:-0}" == "1" ]]; then
  exec python3 scripts/check-pdf-preflight.py "$@"
fi

invoking_uid="$(id -u)"
invoking_gid="$(id -g)"
if [[ "${invoking_uid}" -eq 0 ]]; then
  echo "error: PDF preflight must be run as a non-root host user" >&2
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

exec podman run --rm \
  --pull=never \
  --network=none \
  --userns=keep-id \
  --user "${invoking_uid}:${invoking_gid}" \
  --security-opt label=disable \
  --env ALKAHEST_PDF_PREFLIGHT_IN_CONTAINER=1 \
  --volume "${repo_root}:/workspace:ro" \
  --workdir /workspace \
  --entrypoint /workspace/scripts/check-pdf-preflight.sh \
  "${ALKAHEST_TOOLCHAIN_IMAGE}" \
  "$@"
