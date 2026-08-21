#!/usr/bin/env bash
# Run Quarto in the pinned rootless publishing container.
set -euo pipefail

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=scripts/lib/toolchain.sh
source "${script_dir}/lib/toolchain.sh"
repo_root="$(alkahest_repo_root)"
invoking_uid="$(id -u)"
invoking_gid="$(id -g)"

if [[ "${invoking_uid}" -eq 0 ]]; then
  echo "error: the publishing toolchain must be run as a non-root host user" >&2
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

# Map the invoking identity into the rootless container so bind-mounted outputs
# retain normal host ownership. Ephemeral caches make undeclared dependencies
# visible, while --network=none guarantees renders cannot download them.
exec podman run --rm \
  --pull=never \
  --network=none \
  --userns=keep-id \
  --user "${invoking_uid}:${invoking_gid}" \
  --security-opt label=disable \
  --tmpfs /tmp:rw,size=2g,mode=1777 \
  --env HOME=/tmp \
  --env JAVA_TOOL_OPTIONS=-Duser.home=/tmp \
  --env TEXMFCACHE=/tmp \
  --env TEXMFVAR=/tmp \
  --env XDG_CACHE_HOME=/tmp/cache \
  --volume "${repo_root}:/workspace:rw" \
  --workdir /workspace \
  "${ALKAHEST_TOOLCHAIN_IMAGE}" \
  quarto "$@"
