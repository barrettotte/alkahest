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
python3 "${script_dir}/test-pdf-preflight.py"
"${script_dir}/check-writing.sh"
"${script_dir}/check-glyph-coverage.sh"
python3 "${script_dir}/check-source.py"
"${script_dir}/check-epub-accessibility.sh" test
python3 "${script_dir}/check-source.py" --tests
python3 "${script_dir}/package-companion-bundles.py"
python3 "${script_dir}/check-companion-bundles.py"
"${script_dir}/render.sh" complete
"${script_dir}/check-preview.sh"
"${script_dir}/python-tools.sh" scripts/generate-covers.py
"${script_dir}/python-tools.sh" scripts/check-cover-artifacts.py
# Rebuild the reflowable outputs and default PDF once, then require exact
# content equality with the complete render. The full six-PDF repeat remains a
# deliberate pre-release command because fresh LuaLaTeX caches are expensive.
python3 "${script_dir}/check-reproducibility.py" --repeat quick
"${script_dir}/check-golden-pages.sh"
"${script_dir}/check-accessibility.sh"
"${script_dir}/check-epub-accessibility.sh"
"${script_dir}/check-publication.sh"
"${script_dir}/check-pdf-profiles.sh"
