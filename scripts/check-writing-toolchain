#!/usr/bin/env bash
# Verify pinned JavaScript and prose tools run unprivileged and without network.
set -euo pipefail

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=scripts/lib/toolchain.sh
source "${script_dir}/lib/toolchain.sh"

if [[ "$(id -u)" -eq 0 ]]; then
  echo "error: writing tools must be checked as a non-root host user" >&2
  exit 1
fi

if ! command -v podman >/dev/null 2>&1; then
  echo "error: Podman is required but was not found" >&2
  exit 1
fi

if ! podman image exists "${ALKAHEST_TOOLCHAIN_IMAGE}"; then
  echo "error: publishing image is not available locally" >&2
  echo "run make bootstrap once while connected to the network" >&2
  exit 1
fi

podman run --rm \
  --pull=never \
  --network=none \
  --entrypoint sh \
  "${ALKAHEST_TOOLCHAIN_IMAGE}" \
  -lc '
set -eu

test "$(id -u)" -ne 0
test "$(node --version)" = "v${ALKAHEST_NODE_VERSION}"
test "$(npm --version)" = "${ALKAHEST_NPM_VERSION}"
test "$(vale --version)" = "vale version ${ALKAHEST_VALE_VERSION}"
test "$(cspell --version)" = "${ALKAHEST_CSPELL_VERSION}"
grep -Fq "\"version\": \"${ALKAHEST_AXE_CORE_VERSION}\"" \
  /opt/alkahest/writing/node_modules/axe-core/package.json
test "$(HOME=/tmp ace-cli --version)" = "${ALKAHEST_ACE_VERSION}"

printf "Node %s, npm %s, Vale %s, CSpell %s, axe-core %s, and Ace %s passed offline rootless validation.\n" \
  "${ALKAHEST_NODE_VERSION}" \
  "${ALKAHEST_NPM_VERSION}" \
  "${ALKAHEST_VALE_VERSION}" \
  "${ALKAHEST_CSPELL_VERSION}" \
  "${ALKAHEST_AXE_CORE_VERSION}" \
  "${ALKAHEST_ACE_VERSION}"
'
