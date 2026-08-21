#!/usr/bin/env bash
# Generate LuaLaTeX PDF vectors from the canonical semantic-icon SVG sources.
set -euo pipefail

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
repo_root="$(cd "${script_dir}/.." && pwd)"
icon_root="${repo_root}/book/icons"

if ! command -v rsvg-convert >/dev/null 2>&1; then
  echo "error: rsvg-convert is required to stage semantic icon derivatives" >&2
  exit 1
fi

for source_path in "${icon_root}"/*.svg; do
  destination_path="${source_path%.svg}.pdf"
  if [[ ! -f "${destination_path}" || "${source_path}" -nt "${destination_path}" ]]; then
    rsvg-convert --format=pdf --output "${destination_path}" "${source_path}"
  fi
done
