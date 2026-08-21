#!/usr/bin/env bash
# Run WCAG policy checks and pinned axe-core over rendered HTML or fixtures.
set -euo pipefail

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=scripts/lib/toolchain.sh
source "${script_dir}/lib/toolchain.sh"
repo_root="$(alkahest_repo_root)"
invoking_uid="$(id -u)"
invoking_gid="$(id -g)"
mode="${1:-check}"

case "${mode}" in
  check | test) ;;
  *)
    echo "usage: $0 [check|test]" >&2
    exit 2
    ;;
esac

if [[ "${invoking_uid}" -eq 0 ]]; then
  echo "error: accessibility checks must run as a non-root host user" >&2
  exit 1
fi

if [[ "${mode}" == "check" ]]; then
  python3 "${script_dir}/check-accessibility-policy.py"
  if [[ ! -d "${repo_root}/book/_build/html" ]]; then
    echo "error: missing rendered HTML; run make render-html first" >&2
    exit 1
  fi
else
  python3 "${script_dir}/test-accessibility-policy.py"
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

node_script="scripts/check-accessibility-browser.mjs"
if [[ "${mode}" == "test" ]]; then
  node_script="scripts/test-accessibility-browser.mjs"
fi

podman run --rm \
  --pull=never \
  --network=none \
  --userns=keep-id \
  --user "${invoking_uid}:${invoking_gid}" \
  --security-opt label=disable \
  --tmpfs /tmp:rw,size=512m,mode=1777 \
  --env HOME=/tmp \
  --volume "${repo_root}:/workspace:ro" \
  --workdir /workspace \
  "${ALKAHEST_TOOLCHAIN_IMAGE}" \
  node "${node_script}"
