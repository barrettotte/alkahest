#!/usr/bin/env bash
# Run a Python publishing tool in the locked rootless container environment.
set -euo pipefail

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=scripts/toolchain.sh
source "${script_dir}/toolchain.sh"
repo_root="$(alkahest_repo_root)"
invoking_uid="$(id -u)"
invoking_gid="$(id -g)"
workspace_mode="rw"

if [[ "${1:-}" == "--read-only" ]]; then
  workspace_mode="ro"
  shift
fi
if (($# == 0)); then
  echo "usage: $0 [--read-only] PYTHON_ARGS..." >&2
  exit 2
fi

if [[ "${invoking_uid}" -eq 0 ]]; then
  echo "error: Python publishing tools must run as a non-root host user" >&2
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

# The environment is preinstalled during bootstrap; disable networking and map
# the invoking identity so generated derivatives retain normal host ownership.
exec podman run --rm \
  --pull=never \
  --network=none \
  --userns=keep-id \
  --user "${invoking_uid}:${invoking_gid}" \
  --security-opt label=disable \
  --tmpfs /tmp:rw,size=1g,mode=1777 \
  --env HOME=/tmp \
  --env PYTHONPATH=/workspace/src \
  --volume "${repo_root}:/workspace:${workspace_mode}" \
  --workdir /workspace \
  "${ALKAHEST_TOOLCHAIN_IMAGE}" \
  /opt/alkahest/tools/bin/python "$@"
