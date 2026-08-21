#!/usr/bin/env bash
# Run the complete provider-neutral publishing validation pipeline.
set -euo pipefail

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Keep CI policy here rather than in provider YAML so this exact sequence is
# runnable locally. Bootstrap is the sole networked stage; every later wrapper
# explicitly launches its container with networking disabled.
"${script_dir}/bootstrap.sh"
"${script_dir}/quarto.sh" check
"${script_dir}/toolchain-report.sh"
"${script_dir}/check-writing-toolchain.sh"
python3 "${script_dir}/test-writing-overrides.py"
python3 "${script_dir}/test-writing-quality.py"
"${script_dir}/check-writing.sh"
"${script_dir}/check-glyph-coverage.sh"
python3 "${script_dir}/check-source.py"
"${script_dir}/check-epub-accessibility.sh" test
python3 "${script_dir}/check-source.py" --tests
"${script_dir}/render.sh" complete
"${script_dir}/check-accessibility.sh"
"${script_dir}/check-epub-accessibility.sh"
"${script_dir}/check-publication.sh"
"${script_dir}/check-pdf-profiles.sh"
