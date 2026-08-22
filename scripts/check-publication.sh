#!/usr/bin/env bash
# Run publication conformance and cross-format artifact checks offline.
set -euo pipefail

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=scripts/lib/toolchain.sh
source "${script_dir}/lib/toolchain.sh"
repo_root="$(alkahest_repo_root)"
invoking_uid="$(id -u)"
invoking_gid="$(id -g)"

if [[ "${invoking_uid}" -eq 0 ]]; then
  echo "error: publication checks must be run as a non-root host user" >&2
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

# Keep publication validation reproducible: outputs are read-only, the
# container has no network, and all temporary checker state lives in /tmp.
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
    python3 scripts/check-html-links.py book/_build/html
    python3 scripts/check-html-links.py book/_build/locale/fr/html
    for edition in abridged preview public private supplemental; do
      python3 scripts/check-html-links.py "book/_build/smoke/editions/${edition}/html"
    done
    scripts/check-rendered-notes.sh
    scripts/check-rendered-identities.sh
    scripts/check-rendered-index.sh
    scripts/check-rendered-lists.sh
    python3 scripts/check-rendered-localization.py
    for epub in \
      book/_build/epub/Alkahest-Reference-Book.epub \
      book/_build/smoke/editions/preview/epub/Alkahest-Reference-Book.epub; do
      java -jar "${EPUBCHECK_JAR}" "${epub}"
    done
    python3 scripts/check-release-assets.py
    python3 scripts/check-rights-report.py
    python3 scripts/check-publication-contract.py
  '
