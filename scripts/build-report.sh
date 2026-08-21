#!/usr/bin/env bash
# Render each format and report its timing, size, warnings, and metadata.
set -euo pipefail

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=scripts/lib/toolchain.sh
source "${script_dir}/lib/toolchain.sh"
repo_root="$(alkahest_repo_root)"

# Render logs are temporary inputs to the summary; generated book artifacts stay
# in their normal output directories for inspection after the report completes.
report_tmp="$(mktemp -d)"
trap 'rm -rf "${report_tmp}"' EXIT

for required_command in awk date find grep podman sed stat; do
  if ! command -v "${required_command}" >/dev/null 2>&1; then
    echo "error: ${required_command} is required for the build report" >&2
    exit 1
  fi
done

if [[ "$(id -u)" -eq 0 ]]; then
  echo "error: the build report must be run as a non-root host user" >&2
  exit 1
fi

if ! podman image exists "${ALKAHEST_TOOLCHAIN_IMAGE}"; then
  echo "error: publishing image is not available locally" >&2
  echo "run ./scripts/bootstrap.sh once while connected to the network" >&2
  exit 1
fi

declare -a report_rows=()
declare -a warning_rows=()

pdf_metadata() {
  local artifact="$1"

  # Inspect PDFs with the same pinned Poppler used by CI. Focal Poppler emits a
  # known obsolete diagnostic for Typst MarkInfo; preserve every other message.
  podman run --rm \
    --pull=never \
    --network=none \
    --userns=keep-id \
    --user "$(id -u):$(id -g)" \
    --security-opt label=disable \
    --volume "${repo_root}:/workspace:ro" \
    --workdir /workspace \
    --entrypoint pdfinfo \
    "${ALKAHEST_TOOLCHAIN_IMAGE}" \
    "${artifact}" \
    2> >(sed '/^Syntax Error: Suspects object is wrong type (boolean)$/d' >&2)
}

measure_target() {
  local target="$1"
  local label="$2"
  local artifact="$3"
  local log_path="${report_tmp}/${target}.log"
  local start_ns
  local end_ns
  local duration
  local size
  local details
  local warning_count
  local warning

  # Time only the render. Metadata collection happens afterward and is excluded
  # so PDF inspection startup does not distort backend comparisons.
  start_ns="$(date +%s%N)"
  if ! "${script_dir}/render.sh" "${target}" >"${log_path}" 2>&1; then
    echo "error: ${label} render failed" >&2
    sed 's/^/  /' "${log_path}" >&2
    return 1
  fi
  end_ns="$(date +%s%N)"
  duration="$(awk -v start="${start_ns}" -v end="${end_ns}" 'BEGIN { printf "%.2f", (end - start) / 1000000000 }')"

  # HTML is a directory publication; the other primary targets are single
  # distributable files and can use their direct byte size.
  if [[ "${target}" == "html" ]]; then
    size="$(find "${repo_root}/${artifact}" -type f -printf '%s\n' | awk '{ total += $1 } END { print total + 0 }')"
    details="$(find "${repo_root}/${artifact}" -type f | awk 'END { print NR + 0 }') files"
  else
    size="$(stat --format='%s' "${repo_root}/${artifact}")"
    if [[ "${artifact}" == *.pdf ]]; then
      details="$(pdf_metadata "${artifact}" | awk '
        /^Pages:/ { pages = $2 }
        /^Page size:/ { size = $3 " x " $5 " pt" }
        END { print pages " pages; " size }
      ')"
    else
      details="single-file EPUB"
    fi
  fi

  # Quarto prefixes one logical warning with WARN even when its detail spans
  # multiple lines, so count and summarize only those prefix lines.
  warning_count="$(grep -c 'WARN:' "${log_path}" || true)"
  report_rows+=("| ${label} | ${duration} | ${size} | ${warning_count} | ${details} |")

  while IFS= read -r warning; do
    warning_rows+=("- ${label}: ${warning}")
  done < <(sed -n 's/^.*WARN: /WARN: /p' "${log_path}")
}

measure_target html "HTML" "book/_build/html"
measure_target epub "EPUB" "book/_build/epub/Alkahest-Reference-Book.epub"
measure_target typst "Typst PDF" "book/_build/print/7x10/typst/Alkahest-Reference-Book.pdf"
measure_target latex "LuaLaTeX PDF" "book/_build/print/7x10/latex/Alkahest-Reference-Book.pdf"

echo "# Local build report"
echo
printf -- '- Captured: %s\n' "$(date --iso-8601=seconds)"
printf -- '- Image: `%s`\n' "${ALKAHEST_TOOLCHAIN_IMAGE}"
printf -- '- Podman: %s\n' "$(podman --version)"
printf -- '- Host logical CPUs: %s\n' "$(getconf _NPROCESSORS_ONLN 2>/dev/null || echo unknown)"
echo '- Method: one sequential run per format; network disabled; fresh ephemeral container caches; existing artifacts overwritten in place'
echo
echo '| Target | Seconds | Bytes | Warnings | Details |'
echo '|---|---:|---:|---:|---|'
printf '%s\n' "${report_rows[@]}"
echo
echo '## Captured warnings'
echo
if ((${#warning_rows[@]} == 0)); then
  echo '- None.'
else
  printf '%s\n' "${warning_rows[@]}"
fi
