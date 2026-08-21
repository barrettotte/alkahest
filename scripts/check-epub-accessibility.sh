#!/usr/bin/env bash
# Run EPUBCheck, Ace by DAISY, and deterministic EPUB accessibility policy checks.
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
  echo "error: EPUB accessibility checks must run as a non-root host user" >&2
  exit 1
fi

if [[ "${mode}" == "test" ]]; then
  python3 "${script_dir}/test-epub-accessibility.py"
  python3 "${script_dir}/test-epub-reading-system-review.py"
else
  python3 "${script_dir}/check-epub-accessibility-policy.py"
  python3 "${script_dir}/check-epub-reading-system-review.py"
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

if [[ "${mode}" == "test" ]]; then
  podman run --rm \
    --pull=never \
    --network=none \
    --userns=keep-id \
    --user "${invoking_uid}:${invoking_gid}" \
    --security-opt label=disable \
    --tmpfs /tmp:rw,size=128m,mode=1777 \
    --env HOME=/tmp \
    "${ALKAHEST_TOOLCHAIN_IMAGE}" \
    sh -lc 'test "$(ace-cli --version)" = "${ALKAHEST_ACE_VERSION}"'
  exit 0
fi

podman run --rm \
  --pull=never \
  --network=none \
  --userns=keep-id \
  --user "${invoking_uid}:${invoking_gid}" \
  --security-opt label=disable \
  --tmpfs /tmp:rw,size=1g,mode=1777 \
  --env HOME=/tmp \
  --volume "${repo_root}:/workspace:ro" \
  --workdir /workspace \
  "${ALKAHEST_TOOLCHAIN_IMAGE}" \
  sh -lc '
set -eu
epub="book/_build/epub/Alkahest-Reference-Book.epub"
java -jar "${EPUBCHECK_JAR}" "${epub}"
ace_status=0
ace-cli \
  --outdir /tmp/alkahest-ace \
  --tempdir /tmp/alkahest-ace-temp \
  --force \
  --silent \
  --exiterror2 \
  "${epub}" || ace_status=$?
python3 scripts/check-ace-report.py /tmp/alkahest-ace/report.json
test "${ace_status}" -eq 0
'
