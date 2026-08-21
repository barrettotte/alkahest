#!/usr/bin/env bash
# Reject manuscript characters not covered by the declared primary text face.
set -euo pipefail

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=scripts/lib/toolchain.sh
source "${script_dir}/lib/toolchain.sh"
repo_root="$(alkahest_repo_root)"

if [[ "${ALKAHEST_GLYPH_CHECK_IN_CONTAINER:-0}" != "1" ]]; then
  invoking_uid="$(id -u)"
  invoking_gid="$(id -g)"

  if [[ "${invoking_uid}" -eq 0 ]]; then
    echo "error: glyph checks must be run as a non-root host user" >&2
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
    --env ALKAHEST_GLYPH_CHECK_IN_CONTAINER=1 \
    --volume "${repo_root}:/workspace:ro" \
    --workdir /workspace \
    --entrypoint /workspace/scripts/check-glyph-coverage.sh \
    "${ALKAHEST_TOOLCHAIN_IMAGE}"
fi

for required_command in fc-list python3; do
  if ! command -v "${required_command}" >/dev/null 2>&1; then
    echo "error: ${required_command} is required for glyph coverage checks" >&2
    exit 1
  fi
done

codepoints="$(mktemp)"
find "${repo_root}/book" -type f \
  \( -name "*.qmd" -o -name "*.bib" -o -name "*.yml" -o -name "*.yaml" \) \
  -exec python3 "${repo_root}/scripts/list-codepoints.py" {} + \
  | sort -u >"${codepoints}"

failed=0
while IFS= read -r codepoint; do
  if ! fc-list ":charset=${codepoint}" --format '%{family[0]}\n' \
    | grep -Fxq "Libertinus Serif"
  then
    printf 'error: U+%s is not covered by Libertinus Serif\n' "${codepoint}" >&2
    failed=1
  fi
done <"${codepoints}"
rm "${codepoints}"

if [[ "${failed}" -ne 0 ]]; then
  echo "add a locked, licensed locale font before publishing this manuscript" >&2
  exit 1
fi

echo "ok: manuscript glyphs are covered by the declared Libertinus Serif family"
