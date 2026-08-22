#!/usr/bin/env bash
# Validate the isolated preview products with the locked offline toolchain.
set -euo pipefail

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=scripts/lib/toolchain.sh
source "${script_dir}/lib/toolchain.sh"
repo_root="$(alkahest_repo_root)"
invoking_uid="$(id -u)"
invoking_gid="$(id -g)"

if [[ "${invoking_uid}" -eq 0 ]]; then
  echo "error: preview checks must be run as a non-root host user" >&2
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

# Keep artifact inspection read-only, rootless, and disconnected from the network.
exec podman run --rm \
  --pull=never \
  --network=none \
  --userns=keep-id \
  --user "${invoking_uid}:${invoking_gid}" \
  --security-opt label=disable \
  --tmpfs /tmp:rw,size=512m,mode=1777 \
  --env HOME=/tmp \
  --volume "${repo_root}:/workspace:ro" \
  --workdir /workspace \
  --entrypoint bash \
  "${ALKAHEST_TOOLCHAIN_IMAGE}" \
  -ec '
    python3 scripts/check-editions.py
    python3 scripts/check-html-links.py book/_build/smoke/editions/preview/html
    java -jar "${EPUBCHECK_JAR}" book/_build/smoke/editions/preview/epub/Alkahest-Reference-Book.epub
    python3 scripts/check-preview.py
  '
